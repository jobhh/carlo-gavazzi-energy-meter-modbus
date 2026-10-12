"""How a poll behaves when part of the meter, or all of it, does not answer."""

from __future__ import annotations

import pytest
from modbus_connection import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusUnit

from carlo_gavazzi_modbus import EM500Meter


async def test_a_refused_sub_system_leaves_the_others_updated(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()
    em540.fail_read(0x0098, IllegalDataAddressError(), register_type="input")

    report = await meter.async_update_readings()

    assert set(report.failed) == {"power_quality"}
    assert "measurements" in report.updated
    assert meter.measurements.voltage_l1_n == 230.1
    assert meter.power_quality.neutral_current is None


async def test_a_silent_meter_raises_a_timeout(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()
    em540.fail_requests(ModbusTimeoutError())

    with pytest.raises(ModbusTimeoutError):
        await meter.async_update_readings()


async def test_a_dead_link_raises_at_once(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()
    em540.read_events.clear()
    em540.fail_requests(ModbusConnectionError())

    with pytest.raises(ModbusConnectionError):
        await meter.async_update_readings()

    # The first read hit it; nothing after it was tried.
    assert len(em540.read_events) == 1


async def test_the_meter_recovers_when_it_answers_again(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()
    em540.fail_requests(ModbusTimeoutError())
    with pytest.raises(ModbusTimeoutError):
        await meter.async_update_readings()

    em540.fail_requests(None)
    report = await meter.async_update_readings()

    assert report.complete
    assert meter.energy.energy_imported == 12345.678
