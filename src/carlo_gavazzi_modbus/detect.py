"""Tell the series of a meter from its model code, and build its device object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .em300 import EM300Meter
from .em500 import EM500Meter
from .em500.identity import ID_CODE_REGISTER
from .exceptions import UnsupportedMeterError
from .models import MeterModel, Series, model_for_code

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

type Meter = EM500Meter | EM300Meter
"""A device object of any series this library supports."""


async def async_identify(unit: ModbusUnit) -> MeterModel:
    """Read the model code alone and return the model, of either series.

    Both series serve the code at 0x000B to a one-register read, so this costs
    a single read. Raises ``UnsupportedMeterError`` for an unknown code, and
    modbus-connection's ``ModbusError`` subclasses if the read fails.
    """
    [code] = await unit.read_input_registers(ID_CODE_REGISTER, 1)
    model = model_for_code(code)
    if model is None:
        raise UnsupportedMeterError(code)
    return model


def create_meter(unit: ModbusUnit, model: MeterModel) -> Meter:
    """The device object for ``model``, not yet set up."""
    if model.series is Series.EM300:
        return EM300Meter(unit)
    return EM500Meter(unit)


async def async_detect(unit: ModbusUnit) -> Meter:
    """Identify the meter on ``unit`` and return its device object, set up."""
    meter = create_meter(unit, await async_identify(unit))
    await meter.async_ensure_setup()
    return meter
