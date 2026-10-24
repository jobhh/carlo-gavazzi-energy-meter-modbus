"""Commands: counter resets and tariff selection."""

from __future__ import annotations

import pytest
from modbus_connection.mock import MockModbusUnit, WriteEvent

from carlo_gavazzi_energy_meter_modbus import (
    CommandNotSupportedError,
    EM500Meter,
    Tariff,
)

from .conftest import seed


def _record(unit: MockModbusUnit) -> list[WriteEvent]:
    events: list[WriteEvent] = []
    unit.on_write(events.append)
    return events


@pytest.mark.parametrize(
    ("command", "register"),
    [
        ("async_reset_partial_counters", 0x4004),
        ("async_reset_demand", 0x4005),
        ("async_reset_tariff_counters", 0x4006),
    ],
)
async def test_reset_writes_1_to_its_command_register(
    meter: EM500Meter, em540: MockModbusUnit, command: str, register: int
) -> None:
    writes = _record(em540)

    await getattr(meter, command)()

    assert writes == [WriteEvent("holding", register, [1], 0x06)]


async def test_a_mid_meter_refuses_to_reset_its_totals(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    writes = _record(em540)

    with pytest.raises(CommandNotSupportedError):
        await meter.async_reset_total_counters()

    assert writes == []


async def test_a_standard_meter_resets_its_totals(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    seed(mock_modbus_unit, model_code=1760)  # EM540DINAV23XS1X
    meter = EM500Meter(mock_modbus_unit)
    writes = _record(mock_modbus_unit)

    await meter.async_reset_total_counters()

    assert writes == [WriteEvent("holding", 0x4003, [1], 0x06)]


async def test_select_tariff(meter: EM500Meter, em540: MockModbusUnit) -> None:
    writes = _record(em540)

    await meter.async_select_tariff(Tariff.TARIFF_2)

    assert writes == [WriteEvent("holding", 0x1201, [2], 0x06)]
    await meter.async_update_settings()
    assert meter.settings.tariff_selection is Tariff.TARIFF_2


async def test_tariff_none_cannot_be_selected(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    writes = _record(em540)

    with pytest.raises(ValueError):
        await meter.async_select_tariff(Tariff.NONE)

    assert writes == []
