"""What the meter is asked: how wide each read is, and where it lands."""

from __future__ import annotations

from modbus_connection.mock import MockModbusUnit

from carlo_gavazzi_modbus import EM500Meter
from carlo_gavazzi_modbus.em500 import MAX_REGISTERS_PER_READ

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


def _documented(address: int) -> bool:
    return any(low <= address <= high for low, high in DOCUMENTED)


async def _poll_everything(meter: EM500Meter) -> None:
    await meter.async_update()
    await meter.async_read_raw()


async def test_no_read_exceeds_the_documented_width(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await _poll_everything(meter)

    assert em540.read_events
    assert all(e.count <= MAX_REGISTERS_PER_READ for e in em540.read_events)


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

    # Measurements 3, power quality 2, demand 3, energy 4, tariffs 1, status 4.
    assert len(em540.read_events) == 17
    assert {e.register_type for e in em540.read_events} == {"input"}


async def test_settings_are_read_from_the_holding_space(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()
    em540.read_events.clear()

    await meter.async_update_settings()

    assert {e.register_type for e in em540.read_events} == {"holding"}
