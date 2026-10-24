"""Instantaneous measurements, registers 0x0000 to 0x0033."""

from __future__ import annotations

from modbus_connection.model import enum, gauge

from .base import EM500Component, measured
from .enums import PhaseSequence


class Measurements(EM500Component):
    """Voltage, current, power, power factor and frequency.

    Power is signed: positive is imported, negative is exported. On a
    single-phase or two-phase system the unused phases read 0.
    """

    voltage_l1_n = measured(0x0000, 0.1, "V")
    voltage_l2_n = measured(0x0002, 0.1, "V")
    voltage_l3_n = measured(0x0004, 0.1, "V")
    voltage_l1_l2 = measured(0x0006, 0.1, "V")
    voltage_l2_l3 = measured(0x0008, 0.1, "V")
    voltage_l3_l1 = measured(0x000A, 0.1, "V")

    current_l1 = measured(0x000C, 0.001, "A")
    current_l2 = measured(0x000E, 0.001, "A")
    current_l3 = measured(0x0010, 0.001, "A")

    active_power_l1 = measured(0x0012, 0.1, "W")
    active_power_l2 = measured(0x0014, 0.1, "W")
    active_power_l3 = measured(0x0016, 0.1, "W")

    apparent_power_l1 = measured(0x0018, 0.1, "VA")
    apparent_power_l2 = measured(0x001A, 0.1, "VA")
    apparent_power_l3 = measured(0x001C, 0.1, "VA")

    reactive_power_l1 = measured(0x001E, 0.1, "var")
    reactive_power_l2 = measured(0x0020, 0.1, "var")
    reactive_power_l3 = measured(0x0022, 0.1, "var")

    voltage_l_n = measured(0x0024, 0.1, "V")
    """The system phase-to-neutral voltage."""

    voltage_l_l = measured(0x0026, 0.1, "V")
    """The system phase-to-phase voltage."""

    active_power = measured(0x0028, 0.1, "W")
    """The system active power. Negative while exporting."""

    apparent_power = measured(0x002A, 0.1, "VA")
    """The system apparent power."""

    reactive_power = measured(0x002C, 0.1, "var")
    """The system reactive power."""

    # Negative while the phase exports active power. Whether the load is
    # inductive or capacitive is in PowerQuality.
    power_factor_l1 = gauge(0x002E, 0.001)
    power_factor_l2 = gauge(0x002F, 0.001)
    power_factor_l3 = gauge(0x0030, 0.001)
    power_factor = gauge(0x0031, 0.001)
    """The system power factor. Negative while exporting."""

    phase_sequence = enum(0x0032, PhaseSequence, signed=True, nan=0)
    """The phase rotation. Meaningful only on a three-phase system.

    A value of 0 is outside the protocol's +1/-1 and decodes to ``None``.
    """

    frequency = gauge(0x0033, 0.1, unit="Hz")
