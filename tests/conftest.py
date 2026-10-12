"""Fixtures: an EM540 on modbus-connection's in-memory mock backend.

The register values are written as the meter encodes them: 32- and 64-bit
values least significant word first. ``SNAPSHOT_INPUT`` and
``SNAPSHOT_HOLDING`` describe one EM540 PFC on a three-phase grid connection.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest
from modbus_connection.mock import MockModbusUnit

from carlo_gavazzi_modbus import EM500Meter


def words(value: int, count: int) -> list[int]:
    """Encode ``value`` over ``count`` registers, least significant word first."""
    raw = value & ((1 << (16 * count)) - 1)
    return [(raw >> (16 * i)) & 0xFFFF for i in range(count)]


def int16(value: int) -> int:
    """Encode a signed 16-bit value as its register word."""
    return value & 0xFFFF


def ascii_words(text: str, count: int) -> list[int]:
    """Pack ASCII into ``count`` registers, two characters each (high, low)."""
    padded = text.ljust(count * 2, "\0")[: count * 2]
    return [(ord(padded[i]) << 8) | ord(padded[i + 1]) for i in range(0, count * 2, 2)]


def flatten(registers: Mapping[int, int | list[int]]) -> dict[int, int]:
    """Spread multi-register values so every address has its own entry."""
    flat: dict[int, int] = {}
    for address, value in registers.items():
        values = value if isinstance(value, list) else [value]
        for offset, word in enumerate(values):
            flat[address + offset] = word
    return flat


SERIAL = "BX12345678901"
EM540_PFC = 1763

SNAPSHOT_INPUT: dict[int, int] = flatten(
    {
        # -- measurements --
        0x0000: words(2301, 2),  # V L1-N -> 230.1 V
        0x0002: words(2312, 2),  # V L2-N -> 231.2 V
        0x0004: words(2298, 2),  # V L3-N -> 229.8 V
        0x0006: words(3985, 2),  # V L1-L2 -> 398.5 V
        0x0008: words(4001, 2),  # V L2-L3 -> 400.1 V
        0x000A: words(3979, 2),  # V L3-L1 -> 397.9 V
        0x000C: words(5432, 2),  # A L1 -> 5.432 A
        0x000E: words(1234, 2),  # A L2 -> 1.234 A
        0x0010: words(567, 2),  # A L3 -> 0.567 A
        0x0012: words(12005, 2),  # W L1 -> 1200.5 W
        0x0014: words(-2503, 2),  # W L2 -> -250.3 W (exporting)
        0x0016: words(1000, 2),  # W L3 -> 100.0 W
        0x0018: words(12500, 2),  # VA L1 -> 1250.0 VA
        0x001A: words(3002, 2),  # VA L2 -> 300.2 VA
        0x001C: words(1304, 2),  # VA L3 -> 130.4 VA
        0x001E: words(3001, 2),  # var L1 -> 300.1 var
        0x0020: words(-502, 2),  # var L2 -> -50.2 var
        0x0022: words(800, 2),  # var L3 -> 80.0 var
        0x0024: words(2304, 2),  # V L-N sys -> 230.4 V
        0x0026: words(3988, 2),  # V L-L sys -> 398.8 V
        0x0028: words(10502, 2),  # W sys -> 1050.2 W
        0x002A: words(16806, 2),  # VA sys -> 1680.6 VA
        0x002C: words(3299, 2),  # var sys -> 329.9 var
        0x002E: 960,  # PF L1 -> 0.960
        0x002F: int16(-834),  # PF L2 -> -0.834 (exporting)
        0x0030: 767,  # PF L3 -> 0.767
        0x0031: 625,  # PF sys -> 0.625
        0x0032: 1,  # phase sequence -> L1-L2-L3
        0x0033: 500,  # frequency -> 50.0 Hz
        # -- tariff energy --
        0x0046: words(12345, 2),  # kWh (+) t1 -> 1234.5 kWh
        0x0048: words(678, 2),  # kWh (+) t2 -> 67.8 kWh
        # -- power quality --
        0x0076: 1,  # L1 inductive
        0x0077: int16(-1),  # L2 capacitive
        0x0078: 1,  # L3 inductive
        0x0079: 1,  # system inductive
        0x0082: words(312, 2),  # THD A L1 -> 3.12 %
        0x0084: words(456, 2),  # THD A L2 -> 4.56 %
        0x0086: words(789, 2),  # THD A L3 -> 7.89 %
        0x008A: words(150, 2),  # THD V L1-N -> 1.50 %
        0x008C: words(160, 2),  # THD V L2-N -> 1.60 %
        0x008E: words(170, 2),  # THD V L3-N -> 1.70 %
        0x0092: words(140, 2),  # THD V L1-L2 -> 1.40 %
        0x0094: words(145, 2),  # THD V L2-L3 -> 1.45 %
        0x0096: words(155, 2),  # THD V L3-L1 -> 1.55 %
        0x0098: words(123, 2),  # An -> 0.123 A
        # -- demand --
        0x009A: words(4000, 2),  # I1 DMD -> 4.000 A
        0x009C: words(1100, 2),  # I2 DMD -> 1.100 A
        0x009E: words(500, 2),  # I3 DMD -> 0.500 A
        0x00A0: words(16000, 2),  # I1 DMD max -> 16.000 A
        0x00A2: words(9000, 2),  # I2 DMD max -> 9.000 A
        0x00A4: words(7000, 2),  # I3 DMD max -> 7.000 A
        0x00AC: words(9000, 2),  # W1 DMD -> 900.0 W
        0x00AE: words(-1000, 2),  # W2 DMD -> -100.0 W
        0x00B0: words(800, 2),  # W3 DMD -> 80.0 W
        0x00B2: words(36000, 2),  # W1 DMD max -> 3600.0 W
        0x00B4: words(20000, 2),  # W2 DMD max -> 2000.0 W
        0x00B6: words(15000, 2),  # W3 DMD max -> 1500.0 W
        0x00BE: words(8800, 2),  # W sys DMD -> 880.0 W
        0x00C0: words(52000, 2),  # W sys DMD max -> 5200.0 W
        0x00D6: words(14000, 2),  # VA sys DMD -> 1400.0 VA
        0x00D8: words(60000, 2),  # VA sys DMD max -> 6000.0 VA
        # -- status --
        0x0300: 0,  # digital input open
        0x0301: 1,  # tariff 1 active
        0x0302: 0x4302,  # firmware -> 4.3, revision 2
        0x0306: 0,  # alarm not active
        0x1105: 0,  # wiring correct
        # -- 64-bit energy counters, in Wh / varh / VAh --
        0x0500: words(12_345_678, 4),  # kWh (+) TOT -> 12345.678 kWh
        0x0504: words(2_345_678, 4),  # kvarh (+) TOT -> 2345.678 kvarh
        0x0508: words(123_456, 4),  # kWh (+) PARTIAL -> 123.456 kWh
        0x050C: words(23_456, 4),  # kvarh (+) PARTIAL -> 23.456 kvarh
        0x0510: words(5_000_000, 4),  # kWh (+) L1 -> 5000.0 kWh
        0x0514: words(4_000_000, 4),  # kWh (+) L2 -> 4000.0 kWh
        0x0518: words(3_345_678, 4),  # kWh (+) L3 -> 3345.678 kWh
        0x051C: words(2_500_000, 4),  # kWh (-) TOT -> 2500.0 kWh
        0x0520: words(25_000, 4),  # kWh (-) PARTIAL -> 25.0 kWh
        0x0524: words(345_678, 4),  # kvarh (-) TOT -> 345.678 kvarh
        0x0528: words(3_456, 4),  # kvarh (-) PARTIAL -> 3.456 kvarh
        0x052C: words(15_000_123, 4),  # kVAh TOT -> 15000.123 kVAh
        0x0530: words(150_001, 4),  # kVAh PARTIAL -> 150.001 kVAh
        0x0534: words(123_456, 2),  # run hours -> 1234.56 h
        0x0536: words(23_456, 2),  # run hours kWh (-) -> 234.56 h
        0x0538: words(1_234, 2),  # run hours partial -> 12.34 h
        0x053A: words(234, 2),  # run hours kWh (-) partial -> 2.34 h
        0x053C: words(50_000, 2),  # Hz -> 50.000 Hz (not modelled)
        0x053E: words(234_567, 2),  # run hours life -> 2345.67 h
        # -- identity --
        # The low byte of the seventh word is not part of the serial.
        0x5000: ascii_words(SERIAL + "Z", 7),
        0x5007: 2023,  # production year
        0x5012: 0,  # device state -> RUN
    }
)

SNAPSHOT_HOLDING: dict[int, int] = flatten(
    {
        0x1002: 0,  # measuring system -> 3Pn
        0x1010: words(3, 2),  # demand interval -> 15 min
        0x1101: 1,  # tariffs by command -> on
        0x1103: 2,  # measurement mode -> C (bidirectional)
        0x1104: 1,  # wrong connection detection -> on
        0x1200: 1,  # digital input -> remote status only
        0x1201: 1,  # tariff selection -> tariff 1
    }
)


def seed(unit: MockModbusUnit, model_code: int = EM540_PFC) -> None:
    """Load the snapshot into ``unit``, answering ``model_code`` at 0x000B.

    The protocol serves the model code at 0x000B to a one-register read only.
    0x000B also holds the high word of the L3-L1 voltage, so the mock answers
    the model code to a one-register read and the voltage word otherwise.
    """
    unit.input.update(SNAPSHOT_INPUT)
    unit.holding.update(SNAPSHOT_HOLDING)

    read = unit.read_input_registers

    async def read_input_registers(address: int, count: int) -> list[int]:
        values = await read(address, count)
        if address == 0x000B and count == 1:
            return [model_code]
        return values

    unit.read_input_registers = read_input_registers  # type: ignore[method-assign]


@pytest.fixture
def em540(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """The mock unit, answering as an EM540 PFC."""
    seed(mock_modbus_unit)
    return mock_modbus_unit


@pytest.fixture
def meter(em540: MockModbusUnit) -> EM500Meter:
    """An ``EM500Meter`` on the seeded mock unit."""
    return EM500Meter(em540)
