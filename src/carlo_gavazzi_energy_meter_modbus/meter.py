"""What every meter offers beyond its register map, whatever its series."""

from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

from modbus_connection.model import Component, Device, Raw, RegisterField

SERIAL_REGISTERS = range(0x5000, 0x5007)
"""The registers holding the serial number, on both series."""


@dataclass(frozen=True, kw_only=True)
class Snapshot:
    """Every sub-system a meter serves, read whole, for diagnostics."""

    values: dict[str, dict[str, Any] | None]
    """Each sub-system's decoded fields, or ``None`` where it is not served."""

    raw: Raw
    """The registers behind them, without the serial number's."""


def component_values(component: Component) -> dict[str, Any]:
    """Every decoded field and computed value of a component, by name."""
    names = {
        name
        for klass in type(component).__mro__
        if issubclass(klass, Component) and klass is not Component
        for name, attribute in vars(klass).items()
        if not name.startswith("_") and isinstance(attribute, (RegisterField, property))
    }
    return {name: getattr(component, name) for name in sorted(names)}


def _serves(component: Component, field: str) -> bool:
    """Whether a component reads ``field``, or computes it from what it reads."""
    if field in component.declared_fields:
        return field in component.resolved_fields
    return isinstance(getattr(type(component), field, None), property)


class MeterBase(Device):
    """The parts of a meter that do not depend on its series."""

    SOURCES: ClassVar[tuple[str, ...]]
    """Every sub-system, the preferred source of a field first."""

    def source(self, field: str) -> str | None:
        """Return the sub-system ``field`` is read from on this meter, if any.

        Where several serve it, such as the energy totals on an EM330, this is
        the one with the finest resolution. Meaningful once set up, since the
        optional sub-systems are settled then.
        """
        for name in self.SOURCES:
            component = getattr(self, name)
            if component is not None and _serves(component, field):
                return name
        return None

    def restrict_reads(self, wanted: Mapping[str, Collection[str]]) -> None:
        """Read only the ``wanted`` fields of each sub-system, where that saves reads.

        Only a sub-system mapped as separate ranges is cut down: it is read one
        range at a time, so dropping fields drops whole reads. Any other is read
        as one block, which cutting fields out of would split. A sub-system
        that computes a wanted value from other fields is left whole too.
        Cutting down cannot be undone; build a new meter to read everything.
        """
        for name, fields in wanted.items():
            component = getattr(self, name)
            if (
                component is not None
                and fields
                and component.register_ranges is not None
                and set(fields) <= component.resolved_fields.keys()
            ):
                component.restrict_fields(fields)

    def values(
        self, names: Iterable[str] | None = None
    ) -> dict[str, dict[str, Any] | None]:
        """Return what the named sub-systems last read, decoded.

        ``None`` stands for a sub-system this meter does not serve.
        """
        return {
            name: None
            if (component := getattr(self, name)) is None
            else component_values(component)
            for name in (self.SOURCES if names is None else names)
        }

    async def async_read_snapshot(self) -> Snapshot:
        """Read every sub-system whole, decoded and raw, for diagnostics.

        The raw registers leave the serial number out; the decoded identity
        still carries it.

        Fresh copies are read, so a sub-system cut down by ``restrict_reads``
        is still read in full. Raises modbus-connection's ``ModbusError``
        subclasses if a read fails.
        """
        await self.async_ensure_setup()
        values: dict[str, dict[str, Any] | None] = {}
        raw: Raw = {}
        for name in self.SOURCES:
            if (component := getattr(self, name)) is None:
                values[name] = None
                continue
            fresh = type(component)(self.modbus_unit)
            await fresh.async_update()
            values[name] = component_values(fresh)
            for space, registers in (await fresh.async_read_raw()).items():
                raw.setdefault(space, {}).update(registers)
        for registers in raw.values():
            for address in SERIAL_REGISTERS:
                registers.pop(address, None)
        return Snapshot(values=values, raw=raw)
