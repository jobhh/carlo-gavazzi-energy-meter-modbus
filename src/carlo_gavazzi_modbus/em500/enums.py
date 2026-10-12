"""Enumerations the EM500 series register map decodes to."""

from __future__ import annotations

from enum import IntEnum


class PhaseSequence(IntEnum):
    """The phase rotation the meter sees (register 0x0032).

    Meaningful only on a three-phase system.
    """

    L1_L3_L2 = -1
    L1_L2_L3 = 1


class LoadType(IntEnum):
    """Whether a phase, or the system, draws an inductive or capacitive load."""

    CAPACITIVE = -1
    INDUCTIVE = 1


class MeasuringSystem(IntEnum):
    """How the meter is wired (register 0x1002)."""

    THREE_PHASE_WITH_NEUTRAL = 0
    """``3Pn``: three phases and a neutral."""

    THREE_PHASE = 1
    """``3P``: three phases, no neutral."""

    TWO_PHASE = 2
    """``2P``: two phases and a neutral. Not available on MID models."""


class MeasurementMode(IntEnum):
    """How the meter accumulates energy (register 0x1103).

    MID models have this fixed by their part number suffix.
    """

    ABSOLUTE = 0
    """Mode A: energy counts up whatever its direction. Nothing counts as exported."""

    PHASE_ACCUMULATION = 1
    """Mode B: the phases are summed first, then counted as imported or exported."""

    BIDIRECTIONAL = 2
    """Mode C: each direction has its own counters."""


class DemandInterval(IntEnum):
    """The integration time for the demand (DMD) values (register 0x1010)."""

    MINUTES_1 = 0
    MINUTES_5 = 1
    MINUTES_10 = 2
    MINUTES_15 = 3
    MINUTES_20 = 4
    MINUTES_30 = 5
    MINUTES_60 = 6

    @property
    def minutes(self) -> int:
        """The interval in minutes."""
        return (1, 5, 10, 15, 20, 30, 60)[self.value]


class DigitalInputFunction(IntEnum):
    """What the digital input is used for (register 0x1200)."""

    TARIFF = 0
    """The input selects the active tariff."""

    REMOTE_STATUS = 1
    """The input is only reported. Tariffs follow the Modbus selection."""

    PARTIAL_METER = 2
    """The input enables the partial counters."""

    RESET_PARTIAL = 3
    """The input resets the partial counters."""


class Tariff(IntEnum):
    """A tariff: the one active (register 0x0301) or the one selected (0x1201)."""

    NONE = 0
    TARIFF_1 = 1
    TARIFF_2 = 2


class DeviceState(IntEnum):
    """The state the meter reports for itself (register 0x5012)."""

    RUN = 0
    FAULT = 1
    CONFIGURATION_ERROR = 2
    """The phase to terminal block assignment is inconsistent."""
