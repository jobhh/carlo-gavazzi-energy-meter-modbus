"""Replay register dumps captured from real meters with ``script/query.py``.

Each ``tests/captures/*.json`` file is one meter. The checks do not know the
values the meter read. They check that independent registers agree with each
other, which a wrong word order or scale would break.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pytest
from modbus_connection.mock import MockModbusUnit

from carlo_gavazzi_modbus import EM500Meter, MeasuringSystem

CAPTURES = sorted((Path(__file__).parent / "captures").glob("*.json"))

# What script/query.py writes in place of the meter's serial number.
REDACTED_SERIAL = "XX0000000000X"


def load(unit: MockModbusUnit, capture: dict[str, Any]) -> None:
    """Load a capture into ``unit``.

    The dump merges every read by address, so 0x000B holds the L3-L1 voltage's
    high word. The model code a one-register read returned is kept apart, and
    answered here the same way the meter does.
    """
    raw: dict[str, dict[int, int]] = {
        space: {int(address): value for address, value in registers.items()}
        for space, registers in capture["raw"].items()
    }
    # The wide probes also read registers the library does not, such as the
    # 32-bit counter copies. Add them where the poll left a gap.
    probes = capture.get("probes", {})
    for name in ("read_125_registers", "read_120_registers"):
        for offset, word in enumerate(probes.get(name, {}).get("words", [])):
            raw.setdefault("input", {}).setdefault(offset, word)
    # Function 03h and 04h read the same data on this meter, and it has no
    # coils, so both register stores get every register.
    unit.holding.update({**raw.get("input", {}), **raw.get("holding", {})})
    unit.input.update(unit.holding)
    model_code = capture["model"]["code"]
    read = unit.read_input_registers

    async def read_input_registers(address: int, count: int) -> list[int]:
        if address == 0x000B and count == 1:
            return [model_code]
        return await read(address, count)

    unit.read_input_registers = read_input_registers  # type: ignore[method-assign]


def close(a: float | None, b: float | None, *, rel: float, abs_: float) -> bool:
    assert a is not None and b is not None
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_)


def replay(path: Path, unit: MockModbusUnit) -> EM500Meter:
    """An ``EM500Meter`` on ``unit``, answering as the captured meter did."""
    load(unit, json.loads(path.read_text()))
    return EM500Meter(unit)


each_capture = pytest.mark.parametrize("path", CAPTURES, ids=lambda p: p.stem)


@each_capture
async def test_capture_decodes_completely(
    path: Path, mock_modbus_unit: MockModbusUnit
) -> None:
    captured = replay(path, mock_modbus_unit)
    report = await captured.async_update()

    assert report.complete, report.failed
    assert captured.model is not None


@each_capture
async def test_capture_holds_no_real_serial_number(
    path: Path, mock_modbus_unit: MockModbusUnit
) -> None:
    captured = replay(path, mock_modbus_unit)
    await captured.async_ensure_setup()

    assert captured.serial_number == REDACTED_SERIAL


@each_capture
async def test_phase_powers_add_up_to_the_system_power(
    path: Path, mock_modbus_unit: MockModbusUnit
) -> None:
    captured = replay(path, mock_modbus_unit)
    await captured.async_update()
    m = captured.measurements

    for name in ("active_power", "apparent_power", "reactive_power"):
        phases = [getattr(m, f"{name}_l{n}") for n in (1, 2, 3)]
        total = getattr(m, name)
        if name == "apparent_power":
            # Apparent power is not signed, so the phases bound it from above.
            assert total is not None and total <= sum(phases) + 1.0, name
        else:
            assert close(sum(phases), total, rel=0.01, abs_=2.0), (name, phases, total)


@each_capture
async def test_voltages_agree(path: Path, mock_modbus_unit: MockModbusUnit) -> None:
    captured = replay(path, mock_modbus_unit)
    await captured.async_update()
    m = captured.measurements

    assert m.frequency is not None and 45 <= m.frequency <= 65
    if captured.settings.measuring_system is MeasuringSystem.THREE_PHASE_WITH_NEUTRAL:
        for n in (1, 2, 3):
            voltage = getattr(m, f"voltage_l{n}_n")
            assert voltage is not None and 180 <= voltage <= 270, (n, voltage)
        assert m.voltage_l_n is not None
        assert close(m.voltage_l_l, m.voltage_l_n * math.sqrt(3), rel=0.05, abs_=0)


@each_capture
async def test_apparent_power_bounds_active_and_reactive(
    path: Path, mock_modbus_unit: MockModbusUnit
) -> None:
    captured = replay(path, mock_modbus_unit)
    await captured.async_update()
    m = captured.measurements

    for n in (1, 2, 3):
        p = getattr(m, f"active_power_l{n}")
        q = getattr(m, f"reactive_power_l{n}")
        s = getattr(m, f"apparent_power_l{n}")
        # Harmonics only add to the apparent power, never take from it.
        assert s >= math.hypot(p, q) * 0.95 - 5.0, (n, p, q, s)


@each_capture
async def test_counter_copies_agree(
    path: Path, mock_modbus_unit: MockModbusUnit
) -> None:
    """The 64-bit Wh counters match their 32-bit 0.1 kWh copies at 0x0034."""
    captured = replay(path, mock_modbus_unit)
    await captured.async_update()
    unit = captured.modbus_unit
    words = await unit.read_input_registers(0x0034, 2)
    if words == [0, 0]:
        pytest.skip("the capture holds no 32-bit copy (no wide probe succeeded)")
    copy = (words[1] << 16 | words[0]) / 10

    assert close(captured.energy.energy_imported, copy, rel=0, abs_=0.1)
