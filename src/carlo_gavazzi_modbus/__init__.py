"""Read Carlo Gavazzi energy meters over Modbus, as typed Python objects."""

from modbus_connection.model import UpdateReport

from .em500 import (
    DemandInterval,
    DeviceState,
    DigitalInputFunction,
    EM500Meter,
    LoadType,
    MeasurementMode,
    MeasuringSystem,
    PhaseSequence,
    Tariff,
    async_identify,
)
from .exceptions import (
    CarloGavazziError,
    CommandNotSupportedError,
    UnsupportedMeterError,
)
from .models import MODELS, Family, MeterModel, Variant, model_for_code

__all__ = [
    "MODELS",
    "CarloGavazziError",
    "CommandNotSupportedError",
    "DemandInterval",
    "DeviceState",
    "DigitalInputFunction",
    "EM500Meter",
    "Family",
    "LoadType",
    "MeasurementMode",
    "MeasuringSystem",
    "MeterModel",
    "PhaseSequence",
    "Tariff",
    "UnsupportedMeterError",
    "UpdateReport",
    "Variant",
    "async_identify",
    "model_for_code",
]
