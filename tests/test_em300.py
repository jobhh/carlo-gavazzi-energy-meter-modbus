"""The EM300/ET300 series: EM330, EM340, ET330 and ET340."""

from __future__ import annotations

import pytest
from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusUnit, ReadEvent, WriteEvent

from carlo_gavazzi_energy_meter_modbus import (
    CommandNotSupportedError,
    EM300Meter,
    EM500Meter,
    Family,
    MeasuringSystem,
    PhaseSequence,
    Tariff,
    TariffSource,
    UnsupportedMeterError,
    async_detect,
)
from carlo_gavazzi_energy_meter_modbus.em300 import MeasurementMode

from .conftest import flatten, int16, words

EM340 = 341
ET340 = 345
EM330 = 331
SERIAL = "KX1234567"

# 0x0000-0x0033 match the EM500 series and are covered there; these cover
# what differs.
COMMON_INPUT: dict[int, int] = flatten(
    {
        0x0000: words(2301, 2),  # V L1-N -> 230.1 V
        0x0028: words(10502, 2),  # W sys -> 1050.2 W
        0x0031: 980,  # PF sys -> 0.980
        0x0032: 0,  # phase sequence -> L1-L2-L3
        0x0033: 500,  # frequency -> 50.0 Hz
        0x0034: words(123_457, 2),  # kWh (+) TOT -> 12345.7 kWh
        0x0036: words(23_456, 2),  # kvarh (+) TOT -> 2345.6 kvarh
        0x0038: words(8800, 2),  # W dmd -> 880.0 W
        0x003A: words(52000, 2),  # W dmd peak -> 5200.0 W
        0x003C: words(1_234, 2),  # kWh (+) PAR -> 123.4 kWh
        0x0040: words(50_000, 2),  # kWh (+) L1 -> 5000.0 kWh
        0x0046: words(12345, 2),  # kWh (+) t1 -> 1234.5 kWh
        0x0048: words(678, 2),  # kWh (+) t2 -> 67.8 kWh
        0x004E: words(25_000, 2),  # kWh (-) TOT -> 2500.0 kWh
        0x0302: 1,  # firmware version code -> B
        0x0303: 2,  # firmware revision -> 2
        0x1105: 0,  # wiring correct
        # One character in the low byte of each register.
        0x5000: [ord(c) for c in SERIAL[:7]],
    }
)

HOLDING: dict[int, int] = flatten(
    {
        0x1002: 0,  # measuring system -> 3Pn
        0x1010: words(15, 2),  # demand interval -> 15 min
        0x1101: 1,  # tariffs enabled
        0x1103: 1,  # measurement mode -> B
        0x1104: 0,  # connection help -> on
        0x1200: 1,  # tariff source -> serial
        0x1201: 1,  # tariff selection -> tariff 1
    }
)

ET_INPUT: dict[int, int] = flatten(
    {
        0x005A: words(123_456, 2),  # run hours -> 1234.56 h
        0x0060: words(1_000, 2),  # kWh (-) L1 -> 100.0 kWh
        0x0062: words(2_000, 2),  # kWh (-) L2 -> 200.0 kWh
        0x0064: words(3_000, 2),  # kWh (-) L3 -> 300.0 kWh
        0x0082: words(312, 2),  # THD A L1 -> 3.12 %
        0x0098: words(123, 2),  # An -> 0.123 A
    }
)

EM330_INPUT: dict[int, int] = flatten(
    {
        **ET_INPUT,
        0x0500: words(12_345_678, 4),  # kWh (+) TOT -> 12345.678 kWh
        0x051C: words(2_500_123, 4),  # kWh (-) TOT -> 2500.123 kWh
    }
)

EM340_INPUT: dict[int, int] = flatten(
    {
        0x0082: words(312, 2),  # THD A L1 -> 3.12 %
        0x0400: words(12345, 2),  # kWh (+) TOT, integer part
        0x0402: words(678, 2),  # kWh (+) TOT, thousandths -> 12345.678 kWh
        0x0408: words(2500, 2),  # kWh (-) TOT, integer part
        0x040A: words(123, 2),  # kWh (-) TOT, thousandths -> 2500.123 kWh
    }
)

# The blocks each model leaves out, which the mock refuses like the meter.
REFUSED: dict[int, tuple[int, ...]] = {
    EM340: (0x005A, 0x0060, 0x0098, 0x0500),
    ET340: (0x0400, 0x0500),
    EM330: (0x0060, 0x0400),
}


def seed_em300(unit: MockModbusUnit, code: int, extra: dict[int, int]) -> None:
    """Load an EM300-series meter answering ``code`` at 0x000B."""
    unit.input.update(COMMON_INPUT)
    unit.input.update(extra)
    unit.holding.update(HOLDING)
    for address in REFUSED.get(code, ()):
        unit.fail_read(address, IllegalDataAddressError(), register_type="input")
    read = unit.read_input_registers

    async def read_input_registers(address: int, count: int) -> list[int]:
        values = await read(address, count)
        if address == 0x000B and count == 1:
            return [code]
        return values

    unit.read_input_registers = read_input_registers  # type: ignore[method-assign]


@pytest.fixture
def em340(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    seed_em300(mock_modbus_unit, EM340, EM340_INPUT)
    return mock_modbus_unit


@pytest.fixture
def et340(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    seed_em300(mock_modbus_unit, ET340, ET_INPUT)
    return mock_modbus_unit


@pytest.fixture
def em330(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    seed_em300(mock_modbus_unit, EM330, EM330_INPUT)
    return mock_modbus_unit


async def test_detect_returns_the_em300_meter(em340: MockModbusUnit) -> None:
    meter = await async_detect(em340)

    assert isinstance(meter, EM300Meter)
    assert meter.model is not None
    assert meter.model.family is Family.EM340
    assert meter.model.name == "EM340"
    assert meter.model.mid is None
    assert meter.serial_number == SERIAL[:7]
    assert meter.firmware_version == "B2"


async def test_em500_meter_refuses_an_em300_code(em340: MockModbusUnit) -> None:
    with pytest.raises(UnsupportedMeterError):
        await EM500Meter(em340).async_ensure_setup()


async def test_em340_reads_and_optional_blocks(em340: MockModbusUnit) -> None:
    meter = EM300Meter(em340)
    await meter.async_update()

    assert meter.measurements.voltage_l1_n == pytest.approx(230.1)
    assert meter.measurements.active_power == pytest.approx(1050.2)
    assert meter.measurements.power_factor == pytest.approx(0.98)
    assert meter.measurements.phase_sequence is PhaseSequence.L1_L2_L3
    assert meter.energy.energy_imported == pytest.approx(12345.7)
    assert meter.energy.energy_exported == pytest.approx(2500.0)
    assert meter.energy.energy_imported_l1 == pytest.approx(5000.0)
    assert meter.demand.active_power_demand_max == pytest.approx(5200.0)
    assert meter.tariff_energy.energy_imported_tariff_2 == pytest.approx(67.8)

    assert meter.run_hours is None
    assert meter.exported_per_phase is None
    assert meter.energy_wh is None
    assert meter.energy_precise is not None
    assert meter.energy_precise.energy_imported == 12345.678
    assert meter.energy_precise.energy_exported == 2500.123
    assert meter.best_energy() is meter.energy_precise
    assert meter.power_quality is not None
    assert meter.power_quality.thd_current_l1 == pytest.approx(3.12)
    assert meter.power_quality.neutral_current is None


async def test_et340_serves_run_hours_and_export_per_phase(
    et340: MockModbusUnit,
) -> None:
    meter = EM300Meter(et340)
    await meter.async_update()

    assert meter.run_hours is not None
    assert meter.run_hours.run_hours == pytest.approx(1234.56)
    assert meter.exported_per_phase is not None
    assert meter.exported_per_phase.energy_exported_l3 == pytest.approx(300.0)
    assert meter.power_quality is not None
    assert meter.power_quality.neutral_current == pytest.approx(0.123)
    assert meter.energy_wh is None
    assert meter.energy_precise is None
    assert meter.best_energy() is meter.energy


async def test_em330_serves_the_64_bit_counters(em330: MockModbusUnit) -> None:
    meter = EM300Meter(em330)
    await meter.async_update()

    assert meter.energy_wh is not None
    assert meter.energy_wh.energy_imported == pytest.approx(12345.678)
    assert meter.energy_wh.energy_exported == pytest.approx(2500.123)
    assert meter.best_energy() is meter.energy_wh
    assert meter.run_hours is not None
    assert meter.exported_per_phase is None


async def test_an_older_em340_without_the_precise_counters(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    seed_em300(mock_modbus_unit, EM340, EM340_INPUT)
    mock_modbus_unit.fail_read(0x0400, IllegalDataAddressError(), register_type="input")
    meter = EM300Meter(mock_modbus_unit)
    await meter.async_update()

    assert meter.energy_precise is None
    assert meter.best_energy() is meter.energy


async def test_optional_blocks_are_only_probed_for_models_that_may_have_them(
    em340: MockModbusUnit,
) -> None:
    await EM300Meter(em340).async_ensure_setup()

    probed = {e.address for e in em340.read_events if e.register_type == "input"}
    assert 0x0400 in probed
    assert 0x0082 in probed
    assert probed.isdisjoint({0x005A, 0x0060, 0x0500})


async def test_identity_reads(em340: MockModbusUnit) -> None:
    await EM300Meter(em340).async_ensure_setup()

    assert em340.read_events[:3] == [
        ReadEvent("input", 0x000B, 1),
        ReadEvent("input", 0x0302, 2),
        ReadEvent("input", 0x5000, 7),
    ]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param(0, PhaseSequence.L1_L2_L3, id="correct"),
        pytest.param(1, PhaseSequence.L1_L3_L2, id="reversed-per-protocol"),
        pytest.param(int16(-1), PhaseSequence.L1_L3_L2, id="reversed-per-victron"),
    ],
)
async def test_phase_sequence(
    em340: MockModbusUnit, raw: int, expected: PhaseSequence
) -> None:
    em340.input[0x0032] = raw
    meter = EM300Meter(em340)
    await meter.async_update_readings()

    assert meter.measurements.phase_sequence is expected


async def test_settings(em340: MockModbusUnit) -> None:
    meter = EM300Meter(em340)
    await meter.async_update()

    settings = meter.settings
    assert settings.measuring_system is MeasuringSystem.THREE_PHASE_WITH_NEUTRAL
    assert settings.demand_interval == 15
    assert settings.tariffs_enabled is True
    assert settings.measurement_mode is MeasurementMode.BIDIRECTIONAL
    assert settings.wrong_connection_detection is True
    assert settings.tariff_source is TariffSource.SERIAL
    assert settings.tariff_selection is Tariff.TARIFF_1
    assert meter.phases == 3
    assert meter.has_neutral is True
    assert meter.measures_export is True
    assert meter.status.wrong_connection is False


async def test_wrong_connection_flags(em340: MockModbusUnit) -> None:
    em340.input[0x1105] = 0b0100
    meter = EM300Meter(em340)
    await meter.async_update_readings()

    assert meter.status.wrong_connection is True


def _record(unit: MockModbusUnit) -> list[WriteEvent]:
    events: list[WriteEvent] = []
    unit.on_write(events.append)
    return events


@pytest.mark.parametrize(
    ("command", "register"),
    [
        pytest.param("async_reset_partial_counters", 0x4000, id="partial"),
        pytest.param("async_reset_total_counters", 0x4001, id="totals"),
        pytest.param("async_reset_run_hours", 0x4002, id="run-hours"),
    ],
)
async def test_commands(et340: MockModbusUnit, command: str, register: int) -> None:
    meter = EM300Meter(et340)
    await meter.async_ensure_setup()
    writes = _record(et340)

    await getattr(meter, command)()

    assert writes == [WriteEvent("holding", register, [1], 0x06)]


async def test_run_hours_reset_needs_a_run_hour_meter(em340: MockModbusUnit) -> None:
    meter = EM300Meter(em340)
    await meter.async_ensure_setup()

    with pytest.raises(CommandNotSupportedError):
        await meter.async_reset_run_hours()


async def test_select_tariff(em340: MockModbusUnit) -> None:
    meter = EM300Meter(em340)
    writes = _record(em340)

    await meter.async_select_tariff(Tariff.TARIFF_2)

    assert writes == [WriteEvent("holding", 0x1201, [2], 0x06)]
    with pytest.raises(ValueError):
        await meter.async_select_tariff(Tariff.NONE)
