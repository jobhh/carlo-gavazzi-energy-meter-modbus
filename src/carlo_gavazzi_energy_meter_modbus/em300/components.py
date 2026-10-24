"""The EM300/ET300 series register map: EM330, EM340, ET330 and ET340.

From the EM300 and ET300 series communication protocol, version 2 revision 17
(July 2021). Like the EM500 series, 32- and 64-bit values are least
significant word first, and functions 03h and 04h read the same data.

The addresses up to 0x0051 are served by every model. The rest depend on the
model and its production date, so the device object reads them as optional
components.
"""

from __future__ import annotations

from modbus_connection.model import (
    NumberField,
    RegisterSpace,
    boolean,
    enum,
    gauge,
    int32,
    integer,
    raw_register,
    string,
    uint32,
)

from ..em500.base import EM500Component, counter, measured
from ..em500.enums import MeasuringSystem, PhaseSequence, Tariff
from .enums import MeasurementMode, TariffSource

# Victron's GX driver reads 0 as the right rotation and -1 as the wrong one.
# The protocol document gives 1 for the wrong one. Both decode as reversed.
_PHASE_SEQUENCE = {
    0: PhaseSequence.L1_L2_L3,
    1: PhaseSequence.L1_L3_L2,
    0xFFFF: PhaseSequence.L1_L3_L2,
}


def _energy(address: int, unit: str = "kWh") -> NumberField[float]:
    """A 32-bit counter in 0.1 kWh (or kvarh), least significant word first."""
    return int32(address, scale=0.1, word_order="little", unit=unit)


class EM300Component(EM500Component):
    """A sub-system of an EM300 or ET300 series meter."""


class Measurements(EM300Component):
    """Voltage, current, power, power factor and frequency (0x0000-0x0033).

    The same addresses and scales as the EM500 series. Power is negative while
    exporting.
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
    voltage_l_l = measured(0x0026, 0.1, "V")
    active_power = measured(0x0028, 0.1, "W")
    apparent_power = measured(0x002A, 0.1, "VA")
    reactive_power = measured(0x002C, 0.1, "var")

    power_factor_l1 = gauge(0x002E, 0.001)
    power_factor_l2 = gauge(0x002F, 0.001)
    power_factor_l3 = gauge(0x0030, 0.001)
    power_factor = gauge(0x0031, 0.001)

    phase_sequence: NumberField[PhaseSequence] = NumberField(
        0x0032, signed=False, convert=_PHASE_SEQUENCE
    )
    """The phase rotation. Meaningful only on a three-phase system."""

    frequency = gauge(0x0033, 0.1, unit="Hz")


class Energy(EM300Component):
    """Energy counters in 0.1 kWh steps (0x0034-0x0051), on every model.

    The exported counters only move in measurement mode B.
    """

    energy_imported = _energy(0x0034)
    reactive_energy_imported = _energy(0x0036, "kvarh")
    energy_imported_partial = _energy(0x003C)
    reactive_energy_imported_partial = _energy(0x003E, "kvarh")
    energy_imported_l1 = _energy(0x0040)
    energy_imported_l2 = _energy(0x0042)
    energy_imported_l3 = _energy(0x0044)
    energy_exported = _energy(0x004E)
    reactive_energy_exported = _energy(0x0050, "kvarh")


class Demand(EM300Component):
    """Active power demand and its peak (0x0038-0x003B)."""

    active_power_demand = measured(0x0038, 0.1, "W")
    active_power_demand_max = measured(0x003A, 0.1, "W")


class TariffEnergy(EM300Component):
    """Imported energy per tariff (0x0046-0x0049)."""

    energy_imported_tariff_1 = _energy(0x0046)
    energy_imported_tariff_2 = _energy(0x0048)


class ExportedPerPhase(EM300Component):
    """Exported energy per phase (0x0060-0x0065). ET models only."""

    energy_exported_l1 = _energy(0x0060)
    energy_exported_l2 = _energy(0x0062)
    energy_exported_l3 = _energy(0x0064)


class RunHours(EM300Component):
    """The run hour meter (0x005A). ET models and the EM330 only."""

    run_hours = measured(0x005A, 0.01, "h")


class PowerQuality(EM300Component):
    """THD and neutral current (0x0082-0x0099). Not every model serves them."""

    thd_current_l1 = measured(0x0082, 0.01, "%")
    thd_current_l2 = measured(0x0084, 0.01, "%")
    thd_current_l3 = measured(0x0086, 0.01, "%")
    thd_voltage_l1_n = measured(0x008A, 0.01, "%")
    thd_voltage_l2_n = measured(0x008C, 0.01, "%")
    thd_voltage_l3_n = measured(0x008E, 0.01, "%")
    neutral_current = measured(0x0098, 0.001, "A")
    """ET models and the EM330 only."""


class EnergyWh(EM300Component):
    """64-bit counters in Wh (0x0500-0x052B). EM330 units from October 2018.

    Where present, these replace the 0.1 kWh counters of ``Energy``.
    """

    energy_imported = counter(0x0500, "kWh")
    reactive_energy_imported = counter(0x0504, "kvarh")
    energy_imported_partial = counter(0x0508, "kWh")
    reactive_energy_imported_partial = counter(0x050C, "kvarh")
    energy_imported_l1 = counter(0x0510, "kWh")
    energy_imported_l2 = counter(0x0514, "kWh")
    energy_imported_l3 = counter(0x0518, "kWh")
    energy_exported = counter(0x051C, "kWh")
    reactive_energy_exported = counter(0x0524, "kvarh")


class EnergyPrecise(EM300Component):
    """Totals to 1 Wh (0x0400-0x040F). EM340 units from October 2018.

    Each total is a pair of 32-bit registers: the integer kWh and the
    thousandths.
    """

    _imported = int32(0x0400, word_order="little")
    _imported_fraction = int32(0x0402, word_order="little")
    _reactive_imported = int32(0x0404, word_order="little")
    _reactive_imported_fraction = int32(0x0406, word_order="little")
    _exported = int32(0x0408, word_order="little")
    _exported_fraction = int32(0x040A, word_order="little")
    _reactive_exported = int32(0x040C, word_order="little")
    _reactive_exported_fraction = int32(0x040E, word_order="little")

    @staticmethod
    def _join(whole: int | None, fraction: int | None) -> float | None:
        if whole is None or fraction is None:
            return None
        return round(whole + fraction / 1000, 3)

    @property
    def energy_imported(self) -> float | None:
        """Imported energy in kWh."""
        return self._join(self._imported, self._imported_fraction)

    @property
    def reactive_energy_imported(self) -> float | None:
        """Imported reactive energy in kvarh."""
        return self._join(self._reactive_imported, self._reactive_imported_fraction)

    @property
    def energy_exported(self) -> float | None:
        """Exported energy in kWh. Zero in measurement mode A."""
        return self._join(self._exported, self._exported_fraction)

    @property
    def reactive_energy_exported(self) -> float | None:
        """Exported reactive energy in kvarh."""
        return self._join(self._reactive_exported, self._reactive_exported_fraction)


class Status(EM300Component):
    """Whether the meter detects a wiring error (0x1105)."""

    register_ranges = ((0x1105, 0x1105),)

    _wrong_connection = raw_register(0x1105)

    @property
    def wrong_connection(self) -> bool | None:
        """Whether any wiring error flag is set.

        The bits tell a wrong phase sequence, inverted phases or swapped
        phases apart; the meter only reports them while its connection help
        is on.
        """
        flags = self._wrong_connection
        return None if flags is None else flags != 0


class Settings(EM300Component):
    """How the meter is configured. Only the tariff selection is writable."""

    register_space: RegisterSpace = "holding"
    register_ranges = (
        (0x1002, 0x1002),
        (0x1010, 0x1011),
        (0x1101, 0x1101),
        (0x1103, 0x1104),
        (0x1200, 0x1201),
    )

    measuring_system = enum(0x1002, MeasuringSystem)

    demand_interval = uint32(0x1010, word_order="little", unit="min")
    """The demand integration time in minutes, 1 to 30."""

    tariffs_enabled = boolean(0x1101)

    measurement_mode = enum(0x1103, MeasurementMode)

    _connection_help_off = boolean(0x1104)

    tariff_source = enum(0x1200, TariffSource)

    tariff_selection = enum(0x1201, Tariff, writable=True)
    """The tariff selected over Modbus. Writable only while the tariff source
    is the serial port."""

    @property
    def wrong_connection_detection(self) -> bool | None:
        """Whether the wrong-connection help is on (0x1104 is 0 when on)."""
        off = self._connection_help_off
        return None if off is None else not off


class Identity(EM300Component):
    """Model code, firmware and serial number. Read once, at setup."""

    register_ranges = (
        (0x000B, 0x000B),
        (0x0302, 0x0303),
        (0x5000, 0x5006),
    )

    code = integer(0x000B, signed=False)
    _version = integer(0x0302, signed=False)
    _revision = integer(0x0303, signed=False)
    _serial = string(0x5000, 7)

    @property
    def firmware_version(self) -> str | None:
        """The firmware as version letter and revision, such as ``B2``."""
        version, revision = self._version, self._revision
        if version is None or revision is None:
            return None
        return f"{chr(ord('A') + version)}{revision}"

    @property
    def serial_number(self) -> str | None:
        """The serial number.

        These meters put one character in the low byte of each register, and
        a zero in the high byte. Victron's GX driver strips the zeros the same
        way, which also reads the EM500 layout of two characters a register.
        """
        serial = self._serial
        if serial is None:
            return None
        return serial.replace("\x00", "").strip() or None
