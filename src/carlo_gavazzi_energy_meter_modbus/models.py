"""The meter models this library knows, keyed by their identification code."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class Family(StrEnum):
    """A meter model family."""

    EM530 = "EM530"
    EM540 = "EM540"
    EM330 = "EM330"
    EM331 = "EM331"
    EM340 = "EM340"
    EM341 = "EM341"
    ET330 = "ET330"
    ET340 = "ET340"


class Series(StrEnum):
    """A register map, shared by the families in it."""

    EM500 = "EM500"
    """The EM530 and EM540."""

    EM300 = "EM300"
    """The EM330, EM340, ET330 and ET340, with their single-tariff variants."""


class Variant(StrEnum):
    """The part number suffix: the standard device or a MID-certified one."""

    X = "X"
    """The standard device. Its counters can be reset."""

    PFA = "PFA"
    """MID certified, absolute counters (measurement mode A)."""

    PFB = "PFB"
    """MID certified, measurement mode B."""

    PFC = "PFC"
    """MID certified, measurement mode C."""

    PFD = "PFD"
    """MID certified, bidirectional, similar to PFB."""

    PFE = "PFE"
    """MID certified, bidirectional, similar to PFC."""


@dataclass(frozen=True, slots=True)
class MeterModel:
    """One orderable meter model."""

    code: int
    """The Carlo Gavazzi identification code the meter reports."""

    part_number: str
    family: Family
    variant: Variant | None
    """The variant, or ``None`` where the code is shared by several variants."""

    series: Series = Series.EM500

    @property
    def name(self) -> str:
        """A short display name, such as ``EM540`` or ``EM540 PFC``."""
        if self.variant is None or self.variant is Variant.X:
            return str(self.family)
        return f"{self.family} {self.variant}"

    @property
    def mid(self) -> bool | None:
        """Whether the model is MID certified, or ``None`` if the code cannot tell.

        A MID model keeps its lifetime counters: they cannot be reset.
        """
        if self.variant is None:
            return None
        return self.variant is not Variant.X


def _model(code: int, part_number: str, variant: Variant) -> tuple[int, MeterModel]:
    family = Family(part_number[:5])
    return code, MeterModel(code, part_number, family, variant)


def _em300(code: int, part_number: str) -> tuple[int, MeterModel]:
    # The EM300 codes are shared by the standard and the MID variants.
    family = Family(part_number[:5])
    return code, MeterModel(code, part_number, family, None, Series.EM300)


MODELS: Final = MappingProxyType(
    dict(
        (
            _model(1744, "EM530DINAV53XS1X", Variant.X),
            _model(1745, "EM530DINAV53XS1PFA", Variant.PFA),
            _model(1746, "EM530DINAV53XS1PFB", Variant.PFB),
            _model(1747, "EM530DINAV53XS1PFC", Variant.PFC),
            _model(1749, "EM530DINAV53XS1PFD", Variant.PFD),
            _model(1750, "EM530DINAV53XS1PFE", Variant.PFE),
            _model(1856, "EM530DINMV53XS1X", Variant.X),
            _model(1760, "EM540DINAV23XS1X", Variant.X),
            _model(1761, "EM540DINAV23XS1PFA", Variant.PFA),
            _model(1762, "EM540DINAV23XS1PFB", Variant.PFB),
            _model(1763, "EM540DINAV23XS1PFC", Variant.PFC),
            _model(1765, "EM540DINAV23XS1PFD", Variant.PFD),
            _model(1766, "EM540DINAV23XS1PFE", Variant.PFE),
            _em300(331, "EM330DINAV63"),
            _em300(332, "EM330DINAV53"),
            _em300(335, "ET330DINAV53"),
            _em300(336, "ET330DINAV63"),
            _em300(341, "EM340DINAV23"),
            _em300(345, "ET340DINAV23"),
            _em300(346, "EM341DINAV23"),
            _em300(355, "EM331DINAV53"),
        )
    )
)
"""Every known model by identification code.

The EM500 codes come from the EM530/EM540 protocol v1.9, the EM300 codes from
the EM300/ET300 protocol v2 revision 17. Code 340, an EM340 engineering
sample with the opposite word order, is left out on purpose.
"""


def model_for_code(code: int) -> MeterModel | None:
    """The model an identification code belongs to, or ``None`` if unknown."""
    return MODELS.get(code)
