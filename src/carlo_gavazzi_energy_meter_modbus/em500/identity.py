"""Model code, firmware version and serial number. Read once, at setup."""

from __future__ import annotations

from modbus_connection.model import integer, raw_register, string

from .base import EM500Component

ID_CODE_REGISTER = 0x000B


class Identity(EM500Component):
    """What the meter is.

    The protocol limits the model code and the firmware version to a
    one-register read. The model code's address also falls inside the L3-L1
    voltage, a two-register value at 0x000A. The ranges keep each read as
    narrow as the meter requires.
    """

    register_ranges = (
        (ID_CODE_REGISTER, ID_CODE_REGISTER),
        (0x0302, 0x0302),
        (0x5000, 0x5007),
    )

    code = integer(ID_CODE_REGISTER, signed=False)
    """The Carlo Gavazzi identification code of the model."""

    _firmware = raw_register(0x0302)
    _serial = string(0x5000, 7)

    production_year = integer(0x5007, signed=False)

    @property
    def firmware_version(self) -> str | None:
        """The firmware version as ``major.minor.revision``."""
        word = self._firmware
        if word is None:
            return None
        major = (word >> 12) & 0x0F
        minor = (word >> 8) & 0x0F
        revision = word & 0xFF
        return f"{major}.{minor}.{revision}"

    @property
    def serial_number(self) -> str | None:
        """The 13-character serial number.

        The serial fills seven registers, but the low byte of the last one is
        not part of it.
        """
        serial = self._serial
        if serial is None:
            return None
        return serial[:13].strip("\x00 ") or None
