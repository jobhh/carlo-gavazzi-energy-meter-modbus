#!/usr/bin/env python3

"""Query an EM530 or EM540 once and print every value.

Everything this script does is a read. It never writes to the meter.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from modbus_connection import ModbusError, ModbusUnit
from modbus_connection.cli_helper import (
    CountingUnit,
    add_connection_args,
    connect_from_args,
    print_component,
)
from modbus_connection.model import Raw

from carlo_gavazzi_energy_meter_modbus import EM500Meter
from carlo_gavazzi_energy_meter_modbus.em500 import ALL

# The meter speaks RTU on its RS485 port: a serial port, an ESPHome serial
# proxy (esphome://), or a gateway that passes the frames through (tcp + rtu).
CONNECTIONS = (("serial", "rtu"), ("tcp", "rtu"))

EXAMPLES = """examples:
  # An ESPHome serial proxy (add &noise_psk=... for an encrypted device)
  python script/query.py "esphome://em540.local/?port_name=modbus" --dump em540.json
  # A USB adapter
  python script/query.py /dev/ttyUSB0 --baudrate 9600 --dump em540.json
  # An RS485-to-TCP gateway in transparent mode
  python script/query.py 192.168.1.60 --transport tcp --port 502 --dump em540.json
"""

Probe = Callable[[ModbusUnit], Awaitable[list[int]]]

# A dump is meant to be shared, so it holds this in place of the serial number.
# tests/test_captures.py checks that every capture does.
REDACTED_SERIAL = "XX0000000000X"
SERIAL_REGISTER = 0x5000


def redact_serial(raw: Raw) -> None:
    """Replace the serial number in ``raw`` with ``REDACTED_SERIAL``.

    The serial fills seven registers, two characters each, high byte first.
    The low byte of the last register is not part of it and is kept.
    """
    encoded = REDACTED_SERIAL.encode("ascii")
    for registers in raw.values():
        for offset in range(7):
            address = SERIAL_REGISTER + offset
            if address not in registers:
                continue
            high = encoded[2 * offset]
            if 2 * offset + 1 < len(encoded):
                low = encoded[2 * offset + 1]
            else:
                low = int(registers[address]) & 0xFF
            registers[address] = high << 8 | low


# Read-only questions the protocol document leaves open, answered by the meter.
PROBES: dict[str, tuple[str, Probe]] = {
    "model_code_alone": (
        "0x000B read on its own: the model code",
        lambda unit: unit.read_input_registers(0x000B, 1),
    ),
    "voltage_l3_l1_block": (
        "0x000A-0x000B read together: the L3-L1 voltage, or the model code?",
        lambda unit: unit.read_input_registers(0x000A, 2),
    ),
    "read_52_registers": (
        "0x0000-0x0033 in one read: is a read wider than 20 accepted?",
        lambda unit: unit.read_input_registers(0x0000, 52),
    ),
    "read_125_registers": (
        "0x0000-0x007C in one read: the 125 registers the text allows",
        lambda unit: unit.read_input_registers(0x0000, 125),
    ),
    "read_120_registers": (
        "0x0000-0x0077 in one read: a wide read that ends on a mapped register",
        lambda unit: unit.read_input_registers(0x0000, 120),
    ),
    "read_64_counter_registers": (
        "0x0500-0x053F in one read: all 64-bit counters and run hours",
        lambda unit: unit.read_input_registers(0x0500, 64),
    ),
    "firmware_in_block": (
        "0x0300-0x0303 in one read: is the firmware register refused in a block?",
        lambda unit: unit.read_input_registers(0x0300, 4),
    ),
    "holding_space_copy": (
        "0x0000-0x0001 as holding registers: the same as the input registers?",
        lambda unit: unit.read_holding_registers(0x0000, 2),
    ),
}


async def run_probes(unit: ModbusUnit) -> dict[str, dict[str, Any]]:
    """Run every probe, recording the words or the error each produced."""
    results: dict[str, dict[str, Any]] = {}
    for name, (question, probe) in PROBES.items():
        try:
            words = await probe(unit)
        except ModbusError as err:
            results[name] = {
                "question": question,
                "error": f"{type(err).__name__}: {err}",
            }
        else:
            results[name] = {"question": question, "words": words}
    return results


async def main() -> int:
    """Read one meter, print it, and optionally save a dump."""
    # The backend logs a failed connect with a traceback; one line is enough.
    logging.getLogger().addHandler(logging.NullHandler())

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_connection_args(parser, connections=CONNECTIONS)
    parser.add_argument("--unit", type=int, default=1, help="Modbus unit id")
    parser.add_argument(
        "--dump",
        type=Path,
        metavar="FILE",
        help="save the raw registers and the probe results to FILE, as JSON",
    )
    parser.add_argument(
        "--no-probes",
        action="store_true",
        help="skip the read-size and register-layout probes",
    )
    args = parser.parse_args()

    try:
        connection = await connect_from_args(args)
    except ModbusError as err:
        print(f"Could not connect to {args.target}: {str(err) or type(err).__name__}")
        return 1

    unit = connection.for_unit(args.unit)
    counting = CountingUnit(unit)
    meter = EM500Meter(counting)
    probes: dict[str, dict[str, Any]] = {}
    try:
        await meter.async_ensure_setup()
        setup_reads = counting.reads
        report = await meter.async_update()
        poll_reads = counting.reads - setup_reads
        raw = await meter.async_read_raw(ALL)
        if not args.no_probes:
            probes = await run_probes(unit)
    except ModbusError as err:
        print(f"Could not read the meter: {str(err) or type(err).__name__}")
        return 1
    finally:
        await connection.close()

    model = meter.model
    assert model is not None  # setup succeeded
    print(f"Model           {model.name} ({model.part_number}, code {model.code})")
    print(f"Serial number   {meter.serial_number}")
    print(f"Firmware        {meter.firmware_version}")
    print(f"Phases          {meter.phases}, neutral: {meter.has_neutral}")
    print(f"Measures export {meter.measures_export}")
    print(f"Wide reads      {meter.wide_reads}")
    for name in ALL:
        print()
        print_component(getattr(meter, name), title=name)
    if report.failed:
        print("\nFailed to read:")
        for name, error in report.failed.items():
            print(f"  {name}: {str(error) or type(error).__name__}")
    if probes:
        print("\nProbes")
        for name, result in probes.items():
            outcome = result.get("error") or f"{len(result['words'])} registers"
            print(f"  {name:28} {outcome}")
    print(f"\n{setup_reads} reads to set up, {poll_reads} reads per poll")

    if args.dump is not None:
        redact_serial(raw)
        dump = {
            "model": {"code": model.code, "part_number": model.part_number},
            "firmware": meter.firmware_version,
            "unit": args.unit,
            "wide_reads": meter.wide_reads,
            "raw": raw,
            "probes": probes,
        }
        args.dump.write_text(json.dumps(dump, indent=2) + "\n")
        print(f"Saved the dump to {args.dump}")
    return 0


raise SystemExit(asyncio.run(main()))
