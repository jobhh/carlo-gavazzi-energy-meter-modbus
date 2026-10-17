"""Enumerations specific to the EM300/ET300 series."""

from __future__ import annotations

from enum import IntEnum


class MeasurementMode(IntEnum):
    """How the meter accumulates energy (register 0x1103).

    The EM300 series has two modes, where the EM500 series has three.
    """

    EASY_CONNECTION = 0
    """Mode A: energy counts up whatever its direction."""

    BIDIRECTIONAL = 1
    """Mode B: imported and exported energy have their own counters."""


class TariffSource(IntEnum):
    """What selects the active tariff (register 0x1200)."""

    DIGITAL_INPUT = 0
    SERIAL = 1
