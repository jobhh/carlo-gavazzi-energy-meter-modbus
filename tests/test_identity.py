"""Identifying the meter: model code, serial number and firmware."""

from __future__ import annotations

import pytest
from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusUnit, ReadEvent

from carlo_gavazzi_modbus import (
    MODELS,
    EM500Meter,
    Family,
    Series,
    UnsupportedMeterError,
    Variant,
    async_identify,
    model_for_code,
)

from .conftest import SERIAL, seed


async def test_setup_identifies_the_meter(meter: EM500Meter) -> None:
    await meter.async_ensure_setup()

    assert meter.model is not None
    assert meter.model.code == 1763
    assert meter.model.part_number == "EM540DINAV23XS1PFC"
    assert meter.model.family is Family.EM540
    assert meter.model.variant is Variant.PFC
    assert meter.model.name == "EM540 PFC"
    assert meter.model.mid is True
    assert meter.serial_number == SERIAL
    assert meter.firmware_version == "4.3.2"
    assert meter.identity.production_year == 2023


async def test_setup_reads_single_word_registers_one_at_a_time(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    await meter.async_ensure_setup()

    setup_reads = [e for e in em540.read_events if e.register_type == "input"]
    assert setup_reads == [
        ReadEvent("input", 0x000B, 1),
        ReadEvent("input", 0x0302, 1),
        ReadEvent("input", 0x5000, 8),
        ReadEvent("input", 0x0500, 64),  # the wide-read probe
    ]


async def test_async_identify_costs_one_read(em540: MockModbusUnit) -> None:
    model = await async_identify(em540)

    assert model.part_number == "EM540DINAV23XS1PFC"
    assert em540.read_events == [ReadEvent("input", 0x000B, 1)]


async def test_unknown_model_code_is_rejected(mock_modbus_unit: MockModbusUnit) -> None:
    seed(mock_modbus_unit, model_code=1234)

    with pytest.raises(UnsupportedMeterError) as err:
        await EM500Meter(mock_modbus_unit).async_ensure_setup()
    assert err.value.code == 1234

    with pytest.raises(UnsupportedMeterError):
        await async_identify(mock_modbus_unit)


async def test_a_device_without_the_register_propagates_the_modbus_error(
    mock_modbus_unit: MockModbusUnit,
) -> None:
    mock_modbus_unit.fail_read(0x000B, IllegalDataAddressError(), register_type="input")

    with pytest.raises(IllegalDataAddressError):
        await async_identify(mock_modbus_unit)


async def test_setup_is_retried_after_a_failure(em540: MockModbusUnit) -> None:
    meter = EM500Meter(em540)
    em540.fail_read(0x5000, IllegalDataAddressError(), register_type="input")
    with pytest.raises(IllegalDataAddressError):
        await meter.async_ensure_setup()
    assert meter.model is None

    em540.fail_read(0x5000, None, register_type="input")
    await meter.async_ensure_setup()
    assert meter.serial_number == SERIAL


def test_standard_model_is_not_mid() -> None:
    model = model_for_code(1760)
    assert model is not None
    assert model.part_number == "EM540DINAV23XS1X"
    assert model.name == "EM540"
    assert model.mid is False


def test_model_table_matches_part_numbers() -> None:
    em500 = {c: m for c, m in MODELS.items() if m.series is Series.EM500}
    assert len(em500) == 13
    for code, model in em500.items():
        assert model.code == code
        assert model.part_number.startswith(str(model.family))
        assert model.part_number.endswith(str(model.variant))
        assert model.mid is (model.variant is not Variant.X)


def test_em300_codes_do_not_tell_the_variant() -> None:
    em300 = {c: m for c, m in MODELS.items() if m.series is Series.EM300}
    assert sorted(em300) == [331, 332, 335, 336, 341, 345, 346, 355]
    for code, model in em300.items():
        assert model.code == code
        assert model.part_number.startswith(str(model.family))
        assert model.variant is None
        assert model.mid is None
        assert model.name == str(model.family)
    assert model_for_code(340) is None  # engineering sample, other word order


def test_unknown_code_has_no_model() -> None:
    assert model_for_code(0) is None
    assert model_for_code(1748) is None  # a gap in the EM530 codes
