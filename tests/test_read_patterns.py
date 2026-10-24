"""What the meter is asked: how wide each read is, and where it lands."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from modbus_connection import (
    IllegalDataAddressError,
    IllegalDataValueError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusUnit, ReadEvent

from carlo_gavazzi_energy_meter_modbus import EM500Meter
from carlo_gavazzi_energy_meter_modbus.em500 import (
    MAX_REGISTERS_PER_READ,
    WIDE_REGISTERS_PER_READ,
)

# The addresses the EM540 (AV2) documents, from the protocol document v1.9.
# A read outside them is answered with an illegal data address. Function 03h
# and 04h return the same data, so one map covers both spaces.
DOCUMENTED: tuple[tuple[int, int], ...] = (
    (0x0000, 0x00DB),  # instantaneous variables, grouped by type
    (0x00F6, 0x01B5),  # the same, grouped by phase
    (0x0300, 0x0303),  # digital input, tariff, firmware, reserved
    (0x0305, 0x0306),  # reserved, alarm
    (0x0310, 0x0310),  # reserved
    (0x04FE, 0x053F),  # 64-bit counters and run hours
    (0x1000, 0x1000),  # password
    (0x1002, 0x1002),  # measuring system
    (0x1010, 0x1021),  # demand interval, alarm configuration
    (0x1101, 0x1101),  # tariff enabling
    (0x1103, 0x1105),  # measurement mode, wrong connection
    (0x1109, 0x110C),  # wizard, hour counter threshold
    (0x1150, 0x1158),  # phase to terminal block
    (0x1200, 0x1201),  # digital input function, tariff selection
    (0x1600, 0x1604),  # pages, screen saver, backlight
    (0x1610, 0x162A),  # page filters
    (0x2000, 0x2004),  # serial port
    (0x2200, 0x2200),  # module revision
    (0x5000, 0x5019),  # serial number, name, secondary address, state
)

# Registers the protocol limits to a one-register read.
SINGLE_WORD = (0x000B, 0x0302, 0x0303, 0x0310)


Reader = Callable[[int, int], Awaitable[list[int]]]


def _documented(address: int) -> bool:
    return any(low <= address <= high for low, high in DOCUMENTED)


async def _poll_everything(meter: EM500Meter) -> None:
    await meter.async_update()
    await meter.async_read_raw()


def refuse_wide_reads(unit: MockModbusUnit, error: Exception) -> None:
    """Make ``unit`` raise ``error`` for any read wider than 20 registers.

    A refused read is not recorded in ``read_events``.
    """
    for method in ("read_input_registers", "read_holding_registers"):
        read: Reader = getattr(unit, method)

        async def narrow(address: int, count: int, read: Reader = read) -> list[int]:
            if count > MAX_REGISTERS_PER_READ:
                raise error
            return await read(address, count)

        setattr(unit, method, narrow)


async def test_wide_reads_stay_within_the_wide_width(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await _poll_everything(meter)

    assert meter.wide_reads
    assert max(e.count for e in em540.read_events) == WIDE_REGISTERS_PER_READ


@pytest.mark.parametrize(
    "error", [IllegalDataValueError(), ModbusTimeoutError()], ids=["refused", "timeout"]
)
async def test_a_meter_refusing_wide_reads_is_read_20_at_a_time(
    em540: MockModbusUnit, error: Exception
) -> None:
    refuse_wide_reads(em540, error)
    meter = EM500Meter(em540)

    await _poll_everything(meter)

    assert not meter.wide_reads
    assert em540.read_events
    assert all(e.count <= MAX_REGISTERS_PER_READ for e in em540.read_events)


async def test_a_retried_setup_learns_the_read_width_again(
    em540: MockModbusUnit,
) -> None:
    meter = EM500Meter(em540)
    em540.fail_read(0x1002, IllegalDataAddressError(), register_type="holding")
    with pytest.raises(IllegalDataAddressError):
        await meter.async_ensure_setup()
    assert meter.wide_reads

    em540.fail_read(0x1002, None, register_type="holding")
    refuse_wide_reads(em540, IllegalDataValueError())
    em540.read_events.clear()
    await _poll_everything(meter)

    assert not meter.wide_reads
    assert all(e.count <= MAX_REGISTERS_PER_READ for e in em540.read_events)


async def test_the_measurements_are_read_in_one_block(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()
    em540.read_events.clear()

    await meter.measurements.async_update()

    # The phase powers and their total come from the same instant.
    assert em540.read_events == [ReadEvent("input", 0x0000, 52)]


async def test_every_read_stays_inside_the_documented_map(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await _poll_everything(meter)

    for event in em540.read_events:
        for address in range(event.address, event.address + event.count):
            assert _documented(address), f"{event} reads undocumented {address:#06x}"


async def test_single_word_registers_are_read_alone(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await _poll_everything(meter)

    for event in em540.read_events:
        covered = range(event.address, event.address + event.count)
        for address in SINGLE_WORD:
            if address in covered and address != 0x000B:
                assert event.count == 1, f"{event} reads {address:#06x} in a block"


async def test_the_model_code_is_read_alone(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()

    reads = [e for e in em540.read_events if e.address == 0x000B]
    assert [e.count for e in reads] == [1]


async def test_a_readings_poll_costs_a_fixed_number_of_reads(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()
    em540.read_events.clear()

    await meter.async_update_readings()

    # Measurements 1, power quality 1, demand 2, energy 1, tariffs 1, status 4.
    assert len(em540.read_events) == 10
    assert {e.register_type for e in em540.read_events} == {"input"}


async def test_a_narrow_readings_poll_costs_a_fixed_number_of_reads(
    em540: MockModbusUnit,
) -> None:
    refuse_wide_reads(em540, IllegalDataValueError())
    meter = EM500Meter(em540)
    await meter.async_ensure_setup()
    em540.read_events.clear()

    await meter.async_update_readings()

    # Measurements 3, power quality 2, demand 3, energy 4, tariffs 1, status 4.
    assert len(em540.read_events) == 17


async def test_settings_are_read_from_the_holding_space(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()
    em540.read_events.clear()

    await meter.async_update_settings()

    assert {e.register_type for e in em540.read_events} == {"holding"}
