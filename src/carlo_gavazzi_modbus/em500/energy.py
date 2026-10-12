"""Energy counters and run hours.

The lifetime and partial counters come from the 64-bit block at 0x0500, which
counts in Wh rather than the 0.1 kWh of the 32-bit copies at 0x0034. The
tariff counters exist only as 32-bit values, so they have their own component.
"""

from __future__ import annotations

from modbus_connection.model import NumberField, int32

from .base import EM500Component, counter, measured


def _tariff_counter(address: int) -> NumberField[float]:
    """A 32-bit tariff counter in 0.1 kWh, least significant word first."""
    return int32(address, scale=0.1, word_order="little", unit="kWh")


class Energy(EM500Component):
    """Lifetime and partial energy counters, and run hours.

    The exported counters only move in measurement mode B or C. In mode A the
    meter counts every direction as imported.
    """

    energy_imported = counter(0x0500, "kWh")
    reactive_energy_imported = counter(0x0504, "kvarh")
    energy_imported_partial = counter(0x0508, "kWh")
    reactive_energy_imported_partial = counter(0x050C, "kvarh")

    energy_imported_l1 = counter(0x0510, "kWh")
    energy_imported_l2 = counter(0x0514, "kWh")
    energy_imported_l3 = counter(0x0518, "kWh")

    energy_exported = counter(0x051C, "kWh")
    energy_exported_partial = counter(0x0520, "kWh")
    reactive_energy_exported = counter(0x0524, "kvarh")
    reactive_energy_exported_partial = counter(0x0528, "kvarh")

    apparent_energy = counter(0x052C, "kVAh")
    apparent_energy_partial = counter(0x0530, "kVAh")

    run_hours = measured(0x0534, 0.01, "h")
    """Hours the current exceeded the run hour counter's start-up threshold."""

    run_hours_exported = measured(0x0536, 0.01, "h")
    """Hours the meter measured an export."""

    run_hours_partial = measured(0x0538, 0.01, "h")
    run_hours_exported_partial = measured(0x053A, 0.01, "h")

    run_hours_lifetime = measured(0x053E, 0.01, "h")
    """Hours the meter has been powered. No reset clears this one."""


class TariffEnergy(EM500Component):
    """Imported energy per tariff."""

    energy_imported_tariff_1 = _tariff_counter(0x0046)
    energy_imported_tariff_2 = _tariff_counter(0x0048)
