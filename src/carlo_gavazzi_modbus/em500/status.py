"""Digital input, tariff, alarm and fault states."""

from __future__ import annotations

from modbus_connection.model import boolean, enum

from .base import EM500Component
from .enums import DeviceState, Tariff


class Status(EM500Component):
    """What the meter reports about its own state.

    The registers are spread over the map. The firmware version at 0x0302 sits
    between them and answers only a one-register read, so the ranges keep the
    planner from reading across it.
    """

    register_ranges = (
        (0x0300, 0x0301),
        (0x0306, 0x0306),
        (0x1105, 0x1105),
        (0x5012, 0x5012),
    )

    digital_input = boolean(0x0300)
    """Whether the digital input is closed."""

    active_tariff = enum(0x0301, Tariff)

    alarm = boolean(0x0306)
    """Whether the configured alarm is active. Its delay does not count as active."""

    wrong_connection = boolean(0x1105)
    """Whether the meter detects a wiring error.

    Detection can be switched off in ``Settings.wrong_connection_detection``.
    """

    device_state = enum(0x5012, DeviceState)
