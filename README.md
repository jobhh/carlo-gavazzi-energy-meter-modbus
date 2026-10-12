# carlo-gavazzi-modbus

Read Carlo Gavazzi energy meters over Modbus, as typed Python objects.

The library covers the EM500 series: the **EM530** and the **EM540**,
including the MID-certified variants. Victron Energy sells the EM540 as its
three-phase grid meter, so a Victron EM540 works the same way.

It is built on
[modbus-connection](https://github.com/home-assistant-libs/modbus-connection).
The library never opens a connection. You hand it a `ModbusUnit`, and it reads
and writes registers through that unit. This keeps it independent of the
backend and the transport: RS485 through a USB adapter, an RS485-to-TCP
gateway, or the in-memory mock in tests.

## Install

```bash
pip install carlo-gavazzi-modbus
```

## Example

```python
import asyncio

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from carlo_gavazzi_modbus import EM500Meter


async def main() -> None:
    # An RS485-to-TCP gateway in transparent mode carries RTU frames.
    connection = ModbusConnection(
        ModbusTcpParams(host="192.168.1.50", port=502, framer="rtu")
    )
    try:
        meter = EM500Meter(connection.for_unit(1))
        await meter.async_update()

        print(meter.model.name, meter.serial_number, meter.firmware_version)
        print("Power:", meter.measurements.active_power, "W")
        print("Imported:", meter.energy.energy_imported, "kWh")
        if meter.measures_export:
            print("Exported:", meter.energy.energy_exported, "kWh")
    finally:
        await connection.close()


asyncio.run(main())
```

## What it reads

Each sub-system is a component on `EM500Meter`:

| Attribute | Contents |
| --- | --- |
| `identity` | Model code, serial number, production year, firmware version. Read once, at setup. |
| `measurements` | Voltage (L-N, L-L), current, active, apparent and reactive power per phase and for the system, power factor, phase sequence, frequency. |
| `power_quality` | Inductive or capacitive load per phase, THD of current and voltage, neutral current. |
| `demand` | Current, active power and apparent power demand, with their maxima. |
| `energy` | Imported and exported energy (total, partial, per phase), reactive and apparent energy, run hours. |
| `tariff_energy` | Imported energy per tariff. |
| `status` | Digital input, active tariff, alarm, wiring error, device state. |
| `settings` | Measuring system, measurement mode, demand interval, tariff and digital input configuration. |

Units: V, A, W, VA, var, Hz, %, h, and kWh, kvarh and kVAh for energy. The
energy counters come from the meter's 64-bit Wh registers, so they keep full
resolution.

`async_update_readings()` refreshes everything except the settings, and
`async_update_settings()` refreshes the settings. Each returns an
`UpdateReport`: a sub-system the meter refuses lands in `report.failed`, and
the others still refresh.

## Commands

| Method | Effect |
| --- | --- |
| `async_reset_partial_counters()` | Resets the partial energy counters and partial run hours. |
| `async_reset_demand()` | Resets the demand values and their maxima. |
| `async_reset_tariff_counters()` | Resets the tariff energy counters. |
| `async_reset_total_counters()` | Resets the lifetime counters. Raises `CommandNotSupportedError` on a MID meter. |
| `async_select_tariff(tariff)` | Selects tariff 1 or 2 over Modbus. |

## Notes on the meter

- The meter stores 32- and 64-bit values with the least significant word first.
- A 32-bit value whose high word is `0x7FFF` is an overflow (`EEE` on the
  display). It decodes to `None`.
- The model code (0x000B) and the firmware version (0x0302) answer only a
  one-register read. The library reads them alone.
- The protocol document gives two maximum read sizes: 125 registers in the
  text, and 20 in the request frame tables. The library reads at most 20.
- In measurement mode A, the meter counts every direction as imported, and
  the exported counters stay at zero. `EM500Meter.measures_export` tells you
  which mode is set.

The register map follows the *EM530/EM540 Modbus communication protocol*,
version 1.9 (October 2024).

## Develop

```bash
uv sync
uv run pytest
uv run ruff format --check . && uv run ruff check . && uv run mypy
```

The tests run against modbus-connection's in-memory mock. No meter is needed.
See [RELEASING.md](RELEASING.md) to publish a release.

## License

Apache License 2.0. This project is not affiliated with Carlo Gavazzi or
Victron Energy.
