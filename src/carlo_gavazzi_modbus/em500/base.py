"""The component base and field helpers shared by the EM500 series map.

The EM500 series (EM530 and EM540) stores every 32- and 64-bit value with the
least significant word first. Every helper here bakes that in, so the
component files read like the protocol document.
"""

from __future__ import annotations

from typing import Any, Final

from modbus_connection.model import Component, NumberField, RegisterSpace, int64

MAX_REGISTERS_PER_READ: Final = 20
"""The widest read the meter is documented to answer.

The protocol document states two limits: 125 registers in the text and
1 to 20 (``14h``) in the request frame tables. Reads stay within the stricter
one unless the meter answers ``WIDE_REGISTERS_PER_READ`` at setup.
"""

WIDE_REGISTERS_PER_READ: Final = 64
"""The widest read the readings plan when the meter accepts wide reads.

64 registers is the widest block the readings need: the 64-bit counters and
run hours at 0x0500-0x053F. An EM540 on firmware 1.4.3 answers reads of up to
120 registers, but refuses with an illegal data address any read that ends on
a register the map marks "n.a.". The planned blocks always end on a field.
"""

OVERFLOW_MSW: Final = 0x7FFF
"""The most significant word of a value the meter cannot measure.

The meter shows ``EEE`` on its display for such a value.
"""


class EM500Component(Component):
    """A sub-system of an EM530 or EM540.

    Functions 03h and 04h return the same data on this meter. Measurements are
    read as input registers. Settings components switch to the holding space,
    since only holding registers can be written.
    """

    register_space: RegisterSpace = "input"
    max_span = MAX_REGISTERS_PER_READ


class _Measured(NumberField[float]):
    """A signed 32-bit measurement, least significant word first.

    A most significant word of ``0x7FFF`` marks an overflow and decodes to
    ``None``.
    """

    def decode(self, words: list[int], scale_exponent: int | None = None) -> Any:
        """Decode the value, or ``None`` if the meter reports an overflow."""
        if words[-1] == OVERFLOW_MSW:
            return None
        return super().decode(words, scale_exponent)


def measured(address: int, scale: float, unit: str) -> NumberField[float]:
    """A signed 32-bit instantaneous value: ``raw * scale``."""
    return _Measured(
        address,
        count=2,
        signed=True,
        word_order="little",
        scale=scale,
        unit=unit,
    )


def counter(address: int, unit: str) -> NumberField[float]:
    """A signed 64-bit energy counter in Wh, varh or VAh, decoded in k-units."""
    return int64(address, scale=0.001, word_order="little", unit=unit)
