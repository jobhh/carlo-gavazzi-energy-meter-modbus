"""The meter models this library knows, keyed by their identification code."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class Family(StrEnum):
    """A meter family. Members of one family share a register map."""

    EM530 = "EM530"
    EM540 = "EM540"


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
    variant: Variant

    @property
    def name(self) -> str:
        """A short display name, such as ``EM540`` or ``EM540 PFC``."""
        if self.variant is Variant.X:
            return str(self.family)
        return f"{self.family} {self.variant}"

    @property
    def mid(self) -> bool:
        """Whether the model is MID certified.

        A MID model keeps its lifetime counters: they cannot be reset.
        """
        return self.variant is not Variant.X


def _model(code: int, part_number: str, variant: Variant) -> tuple[int, MeterModel]:
    family = Family(part_number[:5])
    return code, MeterModel(code, part_number, family, variant)


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
        )
    )
)
"""Every known model by identification code, from the protocol document v1.9."""


def model_for_code(code: int) -> MeterModel | None:
    """The model an identification code belongs to, or ``None`` if unknown."""
    return MODELS.get(code)
