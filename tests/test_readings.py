"""Decoding the readings and settings of a seeded EM540."""

from __future__ import annotations

from modbus_connection.mock import MockModbusUnit

from carlo_gavazzi_energy_meter_modbus import (
    DemandInterval,
    DeviceState,
    DigitalInputFunction,
    EM500Meter,
    LoadType,
    MeasurementMode,
    MeasuringSystem,
    PhaseSequence,
    Tariff,
)

from .conftest import int16, words


async def test_poll_refreshes_every_sub_system(meter: EM500Meter) -> None:
    report = await meter.async_update()

    assert report.complete
    assert report.updated == {
        "measurements",
        "power_quality",
        "demand",
        "energy",
        "tariff_energy",
        "status",
        "settings",
    }


async def test_measurements(meter: EM500Meter) -> None:
    await meter.async_update_readings()
    m = meter.measurements

    assert (m.voltage_l1_n, m.voltage_l2_n, m.voltage_l3_n) == (230.1, 231.2, 229.8)
    assert (m.voltage_l1_l2, m.voltage_l2_l3, m.voltage_l3_l1) == (
        398.5,
        400.1,
        397.9,
    )
    assert (m.current_l1, m.current_l2, m.current_l3) == (5.432, 1.234, 0.567)
    assert (m.active_power_l1, m.active_power_l2, m.active_power_l3) == (
        1200.5,
        -250.3,
        100.0,
    )
    assert (m.apparent_power_l1, m.apparent_power_l2, m.apparent_power_l3) == (
        1250.0,
        300.2,
        130.4,
    )
    assert (m.reactive_power_l1, m.reactive_power_l2, m.reactive_power_l3) == (
        300.1,
        -50.2,
        80.0,
    )
    assert (m.voltage_l_n, m.voltage_l_l) == (230.4, 398.8)
    assert (m.active_power, m.apparent_power, m.reactive_power) == (
        1050.2,
        1680.6,
        329.9,
    )
    assert (m.power_factor_l1, m.power_factor_l2, m.power_factor_l3) == (
        0.96,
        -0.834,
        0.767,
    )
    assert m.power_factor == 0.625
    assert m.phase_sequence is PhaseSequence.L1_L2_L3
    assert m.frequency == 50.0


async def test_power_quality(meter: EM500Meter) -> None:
    await meter.async_update_readings()
    q = meter.power_quality

    assert (q.load_type_l1, q.load_type_l2, q.load_type_l3) == (
        LoadType.INDUCTIVE,
        LoadType.CAPACITIVE,
        LoadType.INDUCTIVE,
    )
    assert q.load_type is LoadType.INDUCTIVE
    assert (q.thd_current_l1, q.thd_current_l2, q.thd_current_l3) == (
        3.12,
        4.56,
        7.89,
    )
    assert (q.thd_voltage_l1_n, q.thd_voltage_l2_n, q.thd_voltage_l3_n) == (
        1.5,
        1.6,
        1.7,
    )
    assert (q.thd_voltage_l1_l2, q.thd_voltage_l2_l3, q.thd_voltage_l3_l1) == (
        1.4,
        1.45,
        1.55,
    )
    assert q.neutral_current == 0.123


async def test_demand(meter: EM500Meter) -> None:
    await meter.async_update_readings()
    d = meter.demand

    assert (d.current_demand_l1, d.current_demand_l2, d.current_demand_l3) == (
        4.0,
        1.1,
        0.5,
    )
    assert (
        d.current_demand_max_l1,
        d.current_demand_max_l2,
        d.current_demand_max_l3,
    ) == (16.0, 9.0, 7.0)
    assert (
        d.active_power_demand_l1,
        d.active_power_demand_l2,
        d.active_power_demand_l3,
    ) == (900.0, -100.0, 80.0)
    assert (
        d.active_power_demand_max_l1,
        d.active_power_demand_max_l2,
        d.active_power_demand_max_l3,
    ) == (3600.0, 2000.0, 1500.0)
    assert (d.active_power_demand, d.active_power_demand_max) == (880.0, 5200.0)
    assert (d.apparent_power_demand, d.apparent_power_demand_max) == (
        1400.0,
        6000.0,
    )


async def test_energy(meter: EM500Meter) -> None:
    await meter.async_update_readings()
    e = meter.energy

    assert e.energy_imported == 12345.678
    assert e.energy_exported == 2500.0
    assert e.energy_imported_partial == 123.456
    assert e.energy_exported_partial == 25.0
    assert (e.energy_imported_l1, e.energy_imported_l2, e.energy_imported_l3) == (
        5000.0,
        4000.0,
        3345.678,
    )
    assert e.reactive_energy_imported == 2345.678
    assert e.reactive_energy_imported_partial == 23.456
    assert e.reactive_energy_exported == 345.678
    assert e.reactive_energy_exported_partial == 3.456
    assert e.apparent_energy == 15000.123
    assert e.apparent_energy_partial == 150.001
    assert e.run_hours == 1234.56
    assert e.run_hours_exported == 234.56
    assert e.run_hours_partial == 12.34
    assert e.run_hours_exported_partial == 2.34
    assert e.run_hours_lifetime == 2345.67


async def test_tariff_energy(meter: EM500Meter) -> None:
    await meter.async_update_readings()

    assert meter.tariff_energy.energy_imported_tariff_1 == 1234.5
    assert meter.tariff_energy.energy_imported_tariff_2 == 67.8


async def test_status(meter: EM500Meter) -> None:
    await meter.async_update_readings()
    s = meter.status

    assert s.digital_input is False
    assert s.active_tariff is Tariff.TARIFF_1
    assert s.alarm is False
    assert s.wrong_connection is False
    assert s.device_state is DeviceState.RUN


async def test_settings(meter: EM500Meter) -> None:
    await meter.async_update_settings()
    s = meter.settings

    assert s.measuring_system is MeasuringSystem.THREE_PHASE_WITH_NEUTRAL
    assert s.demand_interval is DemandInterval.MINUTES_15
    assert s.demand_interval.minutes == 15
    assert s.tariffs_by_command is True
    assert s.measurement_mode is MeasurementMode.BIDIRECTIONAL
    assert s.wrong_connection_detection is True
    assert s.digital_input_function is DigitalInputFunction.REMOTE_STATUS
    assert s.tariff_selection is Tariff.TARIFF_1


async def test_settings_imply_phases_neutral_and_export(meter: EM500Meter) -> None:
    assert meter.phases is None  # nothing read yet

    await meter.async_ensure_setup()

    assert meter.phases == 3
    assert meter.has_neutral is True
    assert meter.measures_export is True


async def test_two_phase_system(em540: MockModbusUnit) -> None:
    em540.holding[0x1002] = MeasuringSystem.TWO_PHASE
    meter = EM500Meter(em540)
    await meter.async_ensure_setup()

    assert meter.phases == 2
    assert meter.has_neutral is True


async def test_three_phase_system_without_neutral(em540: MockModbusUnit) -> None:
    em540.holding[0x1002] = MeasuringSystem.THREE_PHASE
    meter = EM500Meter(em540)
    await meter.async_ensure_setup()

    assert meter.phases == 3
    assert meter.has_neutral is False


async def test_absolute_mode_measures_no_export(em540: MockModbusUnit) -> None:
    em540.holding[0x1103] = MeasurementMode.ABSOLUTE
    meter = EM500Meter(em540)
    await meter.async_ensure_setup()

    assert meter.measures_export is False


async def test_phase_accumulation_mode_measures_export(em540: MockModbusUnit) -> None:
    em540.holding[0x1103] = MeasurementMode.PHASE_ACCUMULATION
    meter = EM500Meter(em540)
    await meter.async_ensure_setup()

    assert meter.measures_export is True


async def test_overflow_decodes_to_none(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    # The meter shows EEE when the high word of a value is 0x7FFF.
    em540.input[0x000C] = 0x1234
    em540.input[0x000D] = 0x7FFF
    await meter.async_update_readings()

    assert meter.measurements.current_l1 is None
    assert meter.measurements.current_l2 == 1.234


async def test_large_negative_values_keep_their_sign(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    # -100 kW exported: 0xFFF0BDC0 as two words, low word first.
    em540.input.update(dict(zip((0x0028, 0x0029), words(-1_000_000, 2), strict=True)))
    await meter.async_update_readings()

    assert meter.measurements.active_power == -100000.0


async def test_out_of_spec_codes_decode_to_none(
    meter: EM500Meter, em540: MockModbusUnit
) -> None:
    em540.input[0x0032] = 0  # phase sequence on a single-phase connection
    em540.input[0x0079] = 0
    em540.input[0x0077] = int16(-1)
    await meter.async_update_readings()

    assert meter.measurements.phase_sequence is None
    assert meter.power_quality.load_type is None
    assert meter.power_quality.load_type_l2 is LoadType.CAPACITIVE
