"""Support for GoXLR Utility binary sensors."""
from __future__ import annotations

from typing import Any

from goxlrutilityapi.const import MUTED_STATE, NAME_MAP
from goxlrutilityapi.models.map_item import MapItem
from goxlrutilityapi.models.status import FaderStatus, Mixer

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GoXLRUtilityDataUpdateCoordinator
from .entity import GoXLRUtilityBinarySensorEntityDescription, GoXLRUtilityEntity


def get_muted(
    data: Mixer,
    fader_key: str,
) -> bool:
    """Get muted state for a fader."""
    fader: FaderStatus = getattr(data.fader_status, fader_key)
    if fader is None:
        return False

    return fader.mute_state == MUTED_STATE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up GoXLR Utility sensor based on a config entry."""
    coordinator: GoXLRUtilityDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    binary_sensor_descriptions = []

    # Button press sensors
    for key in vars(coordinator.data.button_down):
        map_item: MapItem | None = NAME_MAP.get(key)
        binary_sensor_descriptions.append(
            GoXLRUtilityBinarySensorEntityDescription(
                key=f"button_{key}",
                name=f"{map_item.name if map_item else key} pressed",
                icon=map_item.icon if map_item else "mdi:button-pointer",
                entity_category=EntityCategory.DIAGNOSTIC,
                value=lambda data, item_key=key: data.button_down.__dict__.get(
                    item_key, None
                ),
            )
        )

    # Mute state sensors for each fader
    faders = {
        "a": coordinator.data.fader_status.a,
        "b": coordinator.data.fader_status.b,
        "c": coordinator.data.fader_status.c,
        "d": coordinator.data.fader_status.d,
    }

    for fader_key, fader in faders.items():
        map_item: MapItem | None = NAME_MAP.get(fader.channel)
        channel_name = map_item.name if map_item else fader.channel
        binary_sensor_descriptions.append(
            GoXLRUtilityBinarySensorEntityDescription(
                key=f"mute_{fader.channel}",
                name=f"{channel_name} muted",
                icon="mdi:volume-off",
                value=lambda data, fk=fader_key: get_muted(data, fk),
            )
        )

    entities = []
    for description in binary_sensor_descriptions:
        entities.append(
            GoXLRUtilitySensor(
                coordinator,
                description,
                entry.data.copy(),
            )
        )

    async_add_entities(entities)


class GoXLRUtilitySensor(GoXLRUtilityEntity, BinarySensorEntity):
    """Define a GoXLR Utility sensor."""

    entity_description: GoXLRUtilityBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: GoXLRUtilityDataUpdateCoordinator,
        description: GoXLRUtilityBinarySensorEntityDescription,
        entry_data: dict[str, Any],
    ) -> None:
        """Initialize."""
        super().__init__(
            coordinator,
            entry_data,
            description.key,
            description.name,
        )
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value(self.coordinator.data)
