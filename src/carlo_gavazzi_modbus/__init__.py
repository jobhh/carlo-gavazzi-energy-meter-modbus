"""Read Carlo Gavazzi energy meters over Modbus, as typed Python objects.

``EM500Meter`` covers the EM530 and EM540, ``EM300Meter`` the EM330, EM340,
ET330 and ET340. ``async_detect()`` reads the model code and returns the
right one.
"""

from modbus_connection.model import UpdateReport

from .detect import Meter, async_detect, async_identify, create_meter
from .em300 import EM300Meter, TariffSource
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
)
from .exceptions import (
    CarloGavazziError,
    CommandNotSupportedError,
    UnsupportedMeterError,
)
from .models import MODELS, Family, MeterModel, Series, Variant, model_for_code

__all__ = [
    "MODELS",
    "CarloGavazziError",
    "CommandNotSupportedError",
    "DemandInterval",
    "DeviceState",
    "DigitalInputFunction",
    "EM300Meter",
    "EM500Meter",
    "Family",
    "LoadType",
    "MeasurementMode",
    "MeasuringSystem",
    "Meter",
    "MeterModel",
    "PhaseSequence",
    "Series",
    "Tariff",
    "TariffSource",
    "UnsupportedMeterError",
    "UpdateReport",
    "Variant",
    "async_detect",
    "async_identify",
    "create_meter",
    "model_for_code",
]
