"""The top-level object for an EM330, EM340, ET330 or ET340 energy meter."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Final

from modbus_connection.model import Device, Raw, UpdateReport, read_optional

from ..em500.enums import MeasuringSystem, Tariff
from ..exceptions import CommandNotSupportedError, UnsupportedMeterError
from ..models import Family, MeterModel, Series, model_for_code
from .components import (
    Demand,
    Energy,
    EnergyPrecise,
    EnergyWh,
    ExportedPerPhase,
    Identity,
    Measurements,
    PowerQuality,
    RunHours,
    Settings,
    Status,
    TariffEnergy,
)
from .enums import MeasurementMode

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

READINGS: Final = (
    "measurements",
    "energy",
    "energy_wh",
    "energy_precise",
    "demand",
    "tariff_energy",
    "exported_per_phase",
    "run_hours",
    "power_quality",
    "status",
)
"""The sub-systems ``async_update_readings()`` refreshes, where present."""

SETTINGS: Final = ("settings",)

ALL: Final = ("identity", *READINGS, *SETTINGS)

# A command register acts when 1 is written to it.
_COMMAND_RESET_PARTIAL: Final = 0x4000
_COMMAND_RESET_TOTALS: Final = 0x4001
_COMMAND_RESET_RUN_HOURS: Final = 0x4002
_COMMAND_EXECUTE: Final = 1

_ET: Final = frozenset({Family.ET330, Family.ET340})
_EM330: Final = frozenset({Family.EM330, Family.EM331})
_EM340: Final = frozenset({Family.EM340, Family.EM341})


class EM300Meter(Device):
    """An EM330, EM340, ET330 or ET340 reached through a ``ModbusUnit``.

    Setup identifies the model, reads the settings, and probes the blocks only
    some models and production years serve: run hours, power quality,
    per-phase export, and the higher-resolution energy counters.
    """

    def __init__(self, unit: ModbusUnit) -> None:
        super().__init__(unit)
        self.identity = Identity(unit)
        self.measurements = Measurements(unit)
        self.energy = Energy(unit)
        self.demand = Demand(unit)
        self.tariff_energy = TariffEnergy(unit)
        self.status = Status(unit)
        self.settings = Settings(unit)
        self.energy_wh: EnergyWh | None = None
        self.energy_precise: EnergyPrecise | None = None
        self.exported_per_phase: ExportedPerPhase | None = None
        self.run_hours: RunHours | None = None
        self.power_quality: PowerQuality | None = None
        self._model: MeterModel | None = None

    async def _async_setup(self) -> None:
        """Identify the model and settle which optional blocks it serves."""
        await self.identity.async_update()
        code = self.identity.code
        model = model_for_code(code) if code is not None else None
        if model is None or model.series is not Series.EM300:
            raise UnsupportedMeterError(code)
        await self.settings.async_update()

        unit = self.modbus_unit
        if model.family in _ET:
            self.exported_per_phase = await read_optional(ExportedPerPhase(unit))
        if model.family in _ET | _EM330:
            self.run_hours = await read_optional(RunHours(unit))
        if model.family in _EM330:
            self.energy_wh = await read_optional(EnergyWh(unit))
        if model.family in _EM340:
            self.energy_precise = await read_optional(EnergyPrecise(unit))
        power_quality = PowerQuality(unit)
        if model.family not in _ET | _EM330:
            # The neutral current is ET and EM330 only.
            power_quality.restrict_fields(
                [n for n in PowerQuality.declared_fields if n != "neutral_current"]
            )
        self.power_quality = await read_optional(power_quality)
        self._model = model

    @property
    def model(self) -> MeterModel | None:
        """The meter model, once setup has run."""
        return self._model

    @property
    def serial_number(self) -> str | None:
        """The serial number."""
        return self.identity.serial_number

    @property
    def firmware_version(self) -> str | None:
        """The firmware as version letter and revision, such as ``B2``."""
        return self.identity.firmware_version

    @property
    def phases(self) -> int | None:
        """How many phases the meter measures: 3, or 2 on a ``2P`` system."""
        system = self.settings.measuring_system
        if system is None:
            return None
        return 2 if system is MeasuringSystem.TWO_PHASE else 3

    @property
    def has_neutral(self) -> bool | None:
        """Whether a neutral is connected, so phase-to-neutral values exist."""
        system = self.settings.measuring_system
        if system is None:
            return None
        return system is not MeasuringSystem.THREE_PHASE

    @property
    def measures_export(self) -> bool | None:
        """Whether the exported energy counters move (measurement mode B)."""
        mode = self.settings.measurement_mode
        if mode is None:
            return None
        return mode is MeasurementMode.BIDIRECTIONAL

    def best_energy(self) -> Energy | EnergyWh | EnergyPrecise:
        """The highest-resolution source of the total energy counters."""
        return self.energy_wh or self.energy_precise or self.energy

    async def async_update_readings(self) -> UpdateReport:
        """Refresh what the meter measures."""
        return await self.async_poll(READINGS)

    async def async_update_settings(self) -> UpdateReport:
        """Refresh how the meter is configured."""
        return await self.async_poll(SETTINGS)

    async def async_update(self) -> UpdateReport:
        """Refresh every polled sub-system."""
        report = await self.async_poll(READINGS)
        return await self.async_poll(SETTINGS, report)

    async def async_read_raw(self, names: Iterable[str] = ALL) -> Raw:
        """Every register this meter reads, undecoded, for diagnostics."""
        return await super().async_read_raw(names)

    async def async_select_tariff(self, tariff: Tariff) -> None:
        """Select tariff 1 or 2. Works while the tariff source is the serial port."""
        if tariff is Tariff.NONE:
            raise ValueError("only tariff 1 or 2 can be selected")
        await self.settings.write("tariff_selection", tariff)

    async def async_reset_partial_counters(self) -> None:
        """Reset the partial and tariff counters, the demand and its peak.

        The meter resets all of these with one command.
        """
        await self.modbus_unit.write_register(_COMMAND_RESET_PARTIAL, _COMMAND_EXECUTE)

    async def async_reset_run_hours(self) -> None:
        """Reset the run hour meter. ET models and the EM330 only."""
        if self.run_hours is None:
            raise CommandNotSupportedError("this meter has no run hour meter")
        await self.modbus_unit.write_register(
            _COMMAND_RESET_RUN_HOURS, _COMMAND_EXECUTE
        )

    async def async_reset_total_counters(self) -> None:
        """Reset the lifetime energy counters. Refused by MID-certified meters.

        The model code does not tell a MID meter from a standard one, so the
        meter itself decides; a MID meter answers with a Modbus exception.
        """
        await self.modbus_unit.write_register(_COMMAND_RESET_TOTALS, _COMMAND_EXECUTE)
