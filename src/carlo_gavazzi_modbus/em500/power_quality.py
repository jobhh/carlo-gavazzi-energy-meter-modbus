"""Load type, harmonic distortion and neutral current, registers 0x0076 to 0x0099."""

from __future__ import annotations

from modbus_connection.model import enum

from .base import EM500Component, measured
from .enums import LoadType


class PowerQuality(EM500Component):
    """Whether the load is inductive or capacitive, THD, and the neutral current.

    A load type of 0 is outside the protocol's +1/-1. It decodes to ``None``,
    as it would for a phase with no load to classify.
    """

    load_type_l1 = enum(0x0076, LoadType, signed=True, nan=0)
    load_type_l2 = enum(0x0077, LoadType, signed=True, nan=0)
    load_type_l3 = enum(0x0078, LoadType, signed=True, nan=0)
    load_type = enum(0x0079, LoadType, signed=True, nan=0)
    """The system load type."""

    thd_current_l1 = measured(0x0082, 0.01, "%")
    thd_current_l2 = measured(0x0084, 0.01, "%")
    thd_current_l3 = measured(0x0086, 0.01, "%")

    thd_voltage_l1_n = measured(0x008A, 0.01, "%")
    thd_voltage_l2_n = measured(0x008C, 0.01, "%")
    thd_voltage_l3_n = measured(0x008E, 0.01, "%")

    thd_voltage_l1_l2 = measured(0x0092, 0.01, "%")
    thd_voltage_l2_l3 = measured(0x0094, 0.01, "%")
    thd_voltage_l3_l1 = measured(0x0096, 0.01, "%")

    neutral_current = measured(0x0098, 0.001, "A")
