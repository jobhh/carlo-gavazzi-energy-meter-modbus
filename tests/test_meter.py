"""What both series offer beyond their register maps."""

from __future__ import annotations

import pytest
from modbus_connection.mock import MockModbusUnit

from carlo_gavazzi_energy_meter_modbus import EM300Meter, EM500Meter
from carlo_gavazzi_energy_meter_modbus.meter import SERIAL_REGISTERS

from .conftest import SERIAL
from .test_em300 import (
    EM330,
    EM330_INPUT,
    EM340,
    EM340_INPUT,
    ET340,
    ET_INPUT,
    seed_em300,
)

EM300_UNITS = {
    "em330": (EM330, EM330_INPUT),
    "em340": (EM340, EM340_INPUT),
    "et340": (ET340, ET_INPUT),
}


async def _em300(unit: MockModbusUnit, model: str) -> EM300Meter:
    """An EM300 series meter of ``model``, set up."""
    seed_em300(unit, *EM300_UNITS[model])
    meter = EM300Meter(unit)
    await meter.async_ensure_setup()
    return meter


@pytest.mark.parametrize(
    ("field", "source"),
    [
        ("active_power", "measurements"),
        ("energy_imported", "energy"),
        ("run_hours", "energy"),
        ("wrong_connection", "status"),
        ("measurement_mode", "settings"),
        ("not_a_field", None),
    ],
)
async def test_em540_sources(meter: EM500Meter, field: str, source: str | None) -> None:
    await meter.async_ensure_setup()
    assert meter.source(field) == source


@pytest.mark.parametrize(
    ("unit", "field", "source"),
    [
        # The finest counters a model serves win.
        ("em330", "energy_imported", "energy_wh"),
        ("em330", "energy_imported_l1", "energy_wh"),
        ("em340", "energy_imported", "energy_precise"),
        # The precise counters are only totals.
        ("em340", "energy_imported_partial", "energy"),
        ("et340", "energy_imported", "energy"),
        ("et340", "run_hours", "run_hours"),
        # Computed rather than read.
        ("em340", "wrong_connection", "status"),
        # Optional blocks the model does not serve.
        ("em340", "run_hours", None),
        ("em340", "neutral_current", None),
    ],
)
async def test_em300_sources(
    mock_modbus_unit: MockModbusUnit, unit: str, field: str, source: str | None
) -> None:
    meter = await _em300(mock_modbus_unit, unit)
    assert meter.source(field) == source


async def test_restrict_reads_drops_ranges(
    em540: MockModbusUnit, meter: EM500Meter
) -> None:
    await meter.async_ensure_setup()
    meter.restrict_reads({"status": {"alarm"}, "measurements": {"active_power"}})
    em540.read_events.clear()

    await meter.async_poll(("status", "measurements"))

    status_reads = {e.address for e in em540.read_events if e.address >= 0x0300}
    assert status_reads == {0x0306}
    assert meter.status.alarm is not None
    assert meter.status.device_state is None
    # One block across the measurements is read whole, not split.
    assert meter.measurements.voltage_l1_n is not None


async def test_restrict_reads_keeps_computed_values(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    meter = await _em300(mock_modbus_unit, "em340")
    # The wiring flag is computed from a raw register, not read as a field.
    meter.restrict_reads({"status": {"wrong_connection"}})
    await meter.async_update()
    assert meter.status.wrong_connection is not None


async def test_values(meter: EM500Meter) -> None:
    await meter.async_update()

    values = meter.values()

    assert values["identity"] is not None
    assert values["identity"]["serial_number"] == SERIAL
    assert values["measurements"] is not None
    assert values["measurements"]["active_power"] == pytest.approx(1050.2)
    assert meter.values(["status"]).keys() == {"status"}


async def test_values_of_a_block_not_served(mock_modbus_unit: MockModbusUnit) -> None:
    meter = await _em300(mock_modbus_unit, "em340")
    assert meter.values()["run_hours"] is None


async def test_snapshot_reads_whole_without_the_serial(
    em540: MockModbusUnit, meter: EM500Meter
) -> None:
    await meter.async_ensure_setup()
    meter.restrict_reads({"status": {"alarm"}})

    snapshot = await meter.async_read_snapshot()

    status = snapshot.values["status"]
    assert status is not None
    assert status["device_state"] is not None
    assert not set(SERIAL_REGISTERS) & snapshot.raw["input"].keys()
    assert 0x0000 in snapshot.raw["input"]
