"""Errors raised by this library on top of modbus-connection's."""

from __future__ import annotations


class CarloGavazziError(Exception):
    """Base class for the errors this library raises itself.

    Errors on the link or from the device are modbus-connection's
    ``ModbusError`` subclasses, and propagate unchanged.
    """


class UnsupportedMeterError(CarloGavazziError):
    """The device answers, but not with a model code this library knows."""

    def __init__(self, code: int | None) -> None:
        self.code = code
        super().__init__(f"Unsupported meter identification code: {code}")


class CommandNotSupportedError(CarloGavazziError):
    """The meter model does not offer the command.

    For example, a MID-certified meter does not reset its lifetime counters.
    """
