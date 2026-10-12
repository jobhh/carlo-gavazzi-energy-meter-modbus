"""Demand (DMD) values and their maxima, registers 0x009A to 0x00D9.

A demand value is the average over the integration time set in
``Settings.demand_interval``. The maximum is the highest demand since the last
demand reset.
"""

from __future__ import annotations

from .base import EM500Component, measured


class Demand(EM500Component):
    """Current, active power and apparent power demand, with their maxima."""

    current_demand_l1 = measured(0x009A, 0.001, "A")
    current_demand_l2 = measured(0x009C, 0.001, "A")
    current_demand_l3 = measured(0x009E, 0.001, "A")
    current_demand_max_l1 = measured(0x00A0, 0.001, "A")
    current_demand_max_l2 = measured(0x00A2, 0.001, "A")
    current_demand_max_l3 = measured(0x00A4, 0.001, "A")

    active_power_demand_l1 = measured(0x00AC, 0.1, "W")
    active_power_demand_l2 = measured(0x00AE, 0.1, "W")
    active_power_demand_l3 = measured(0x00B0, 0.1, "W")
    active_power_demand_max_l1 = measured(0x00B2, 0.1, "W")
    active_power_demand_max_l2 = measured(0x00B4, 0.1, "W")
    active_power_demand_max_l3 = measured(0x00B6, 0.1, "W")

    active_power_demand = measured(0x00BE, 0.1, "W")
    """The system active power demand."""

    active_power_demand_max = measured(0x00C0, 0.1, "W")
    """The highest system active power demand since the last reset."""

    apparent_power_demand = measured(0x00D6, 0.1, "VA")
    """The system apparent power demand."""

    apparent_power_demand_max = measured(0x00D8, 0.1, "VA")
    """The highest system apparent power demand since the last reset."""
