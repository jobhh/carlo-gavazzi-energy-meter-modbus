"""The top-level object for an EM530 or EM540 energy meter."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Final

from modbus_connection.model import Device, Raw, UpdateReport

from ..exceptions import CommandNotSupportedError, UnsupportedMeterError
from ..models import MeterModel, Series, model_for_code
from .demand import Demand
from .energy import Energy, TariffEnergy
from .enums import MeasurementMode, MeasuringSystem, Tariff
from .identity import ID_CODE_REGISTER, Identity
from .measurements import Measurements
from .power_quality import PowerQuality
from .settings import Settings
from .status import Status

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

READINGS: Final = (
    "measurements",
    "power_quality",
    "demand",
    "energy",
    "tariff_energy",
    "status",
)
"""The sub-systems ``async_update_readings()`` refreshes."""

SETTINGS: Final = ("settings",)
"""The sub-systems ``async_update_settings()`` refreshes."""

ALL: Final = ("identity", *READINGS, *SETTINGS)
"""Every sub-system, as ``async_read_raw()`` reads them by default."""

# A command register acts when 1 is written to it, and always reads back 0.
_COMMAND_RESET_TOTALS: Final = 0x4003
_COMMAND_RESET_PARTIAL: Final = 0x4004
_COMMAND_RESET_DEMAND: Final = 0x4005
_COMMAND_RESET_TARIFFS: Final = 0x4006
_COMMAND_EXECUTE: Final = 1

_EXPORT_MODES: Final = frozenset(
    {MeasurementMode.PHASE_ACCUMULATION, MeasurementMode.BIDIRECTIONAL}
)


def _supported(code: int | None) -> MeterModel:
    """The model for ``code``, or ``UnsupportedMeterError``."""
    model = model_for_code(code) if code is not None else None
    if model is None or model.series is not Series.EM500:
        raise UnsupportedMeterError(code)
    return model


async def async_identify(unit: ModbusUnit) -> MeterModel:
    """Read the model code alone and return the model it belongs to.

    This costs a single one-register read, which suits a quick probe such as
    a config flow. Raises ``UnsupportedMeterError`` for a code this library
    does not know, and modbus-connection's ``ModbusError`` subclasses if the
    read fails.
    """
    [code] = await unit.read_input_registers(ID_CODE_REGISTER, 1)
    return _supported(code)


class EM500Meter(Device):
    """An EM530 or EM540 reached through a ``ModbusUnit``.

    Setup runs on the first poll, or explicitly through
    ``async_ensure_setup()``. It reads the identity and the settings, and
    raises ``UnsupportedMeterError`` if the device is not an EM530 or EM540.
    """

    def __init__(self, unit: ModbusUnit) -> None:
        super().__init__(unit)
        self.identity = Identity(unit)
        self.measurements = Measurements(unit)
        self.power_quality = PowerQuality(unit)
        self.demand = Demand(unit)
        self.energy = Energy(unit)
        self.tariff_energy = TariffEnergy(unit)
        self.status = Status(unit)
        self.settings = Settings(unit)
        self._model: MeterModel | None = None

    async def _async_setup(self) -> None:
        """Read the identity, check the model, and read the settings."""
        await self.identity.async_update()
        self._model = _supported(self.identity.code)
        await self.settings.async_update()

    # -- identity --------------------------------------------------------

    @property
    def model(self) -> MeterModel | None:
        """The meter model, once setup has run."""
        return self._model

    @property
    def serial_number(self) -> str | None:
        """The 13-character serial number."""
        return self.identity.serial_number

    @property
    def firmware_version(self) -> str | None:
        """The firmware version as ``major.minor.revision``."""
        return self.identity.firmware_version

    # -- what the settings imply ------------------------------------------

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
        """Whether the exported energy counters move.

        In measurement mode A the meter counts every direction as imported, so
        the exported counters stay at zero.
        """
        mode = self.settings.measurement_mode
        if mode is None:
            return None
        return mode in _EXPORT_MODES

    # -- polling -----------------------------------------------------------

    async def async_update_readings(self) -> UpdateReport:
        """Refresh what the meter measures and reports about itself."""
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

    # -- commands ------------------------------------------------------------

    async def async_select_tariff(self, tariff: Tariff) -> None:
        """Select tariff 1 or 2 over Modbus.

        The meter follows the selection only while
        ``settings.tariffs_by_command`` is on and the digital input does not
        select the tariff.
        """
        await self.settings.write("tariff_selection", tariff)

    async def async_reset_partial_counters(self) -> None:
        """Reset the partial energy counters and the partial run hours."""
        await self._async_command(_COMMAND_RESET_PARTIAL)

    async def async_reset_demand(self) -> None:
        """Reset the demand values and their maxima."""
        await self._async_command(_COMMAND_RESET_DEMAND)

    async def async_reset_tariff_counters(self) -> None:
        """Reset the tariff energy counters."""
        await self._async_command(_COMMAND_RESET_TARIFFS)

    async def async_reset_total_counters(self) -> None:
        """Reset the lifetime energy counters and run hours.

        This also clears the partial counters and any counter offsets. The
        lifetime hour counter is kept. Raises ``CommandNotSupportedError`` on a
        MID-certified meter, which never resets these counters.
        """
        await self.async_ensure_setup()
        if self._model is not None and self._model.mid:
            raise CommandNotSupportedError(
                f"{self._model.name} is MID certified; its totals cannot be reset"
            )
        await self._async_command(_COMMAND_RESET_TOTALS)

    async def _async_command(self, register: int) -> None:
        await self.modbus_unit.write_register(register, _COMMAND_EXECUTE)
