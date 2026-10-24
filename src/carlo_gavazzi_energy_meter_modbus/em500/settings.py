"""Configuration the meter reports, and the tariff selection it accepts."""

from __future__ import annotations

from modbus_connection.model import boolean, enum

from .base import EM500Component
from .enums import (
    DemandInterval,
    DigitalInputFunction,
    MeasurementMode,
    MeasuringSystem,
    Tariff,
)


def _selectable_tariff(value: Tariff) -> Tariff:
    """Accept tariff 1 or 2. ``NONE`` is only ever reported, never selected."""
    tariff = Tariff(value)
    if tariff is Tariff.NONE:
        raise ValueError("only tariff 1 or 2 can be selected")
    return tariff


class Settings(EM500Component):
    """How the meter is configured.

    Only the tariff selection is writable here. The other settings change
    how the meter measures, and belong to whoever installs it.
    """

    register_space = "holding"
    register_ranges = (
        (0x1002, 0x1002),
        (0x1010, 0x1011),
        (0x1101, 0x1101),
        (0x1103, 0x1104),
        (0x1200, 0x1201),
    )

    measuring_system = enum(0x1002, MeasuringSystem)

    demand_interval = enum(0x1010, DemandInterval, count=2, word_order="little")
    """The integration time of the demand values."""

    tariffs_by_command = boolean(0x1101)
    """Whether a tariff selected over Modbus takes effect.

    It is ignored while ``digital_input_function`` is ``TARIFF``.
    """

    measurement_mode = enum(0x1103, MeasurementMode)

    wrong_connection_detection = boolean(0x1104)

    digital_input_function = enum(0x1200, DigitalInputFunction)

    tariff_selection = enum(0x1201, Tariff, writable=_selectable_tariff)
    """The tariff selected over Modbus."""
