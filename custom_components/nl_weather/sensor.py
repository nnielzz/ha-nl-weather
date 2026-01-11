from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import UnitOfLength
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import Alert
from . import KNMIDirectConfigEntry, DOMAIN
from .coordinator import NLWeatherUpdateCoordinator, NLWeatherEDRCoordinator
from homeassistant.core import HomeAssistant


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: KNMIDirectConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    obs_coordinator = config_entry.runtime_data.obs_coordinator
    for subentry_id, subentry in config_entry.subentries.items():
        coordinator = config_entry.runtime_data.coordinators[subentry_id]

        async_add_entities(
            [
                NLWeatherAlertSensor(coordinator, config_entry, subentry),
                NLWeatherAlertLevelSensor(coordinator, config_entry, subentry),
                NLObservationStationDistanceSensor(
                    obs_coordinator, config_entry, subentry
                ),
                NLObservationStationNameSensor(obs_coordinator, config_entry, subentry),
                NLObservationTimeSensor(obs_coordinator, config_entry, subentry),
            ],
            config_subentry_id=subentry_id,
        )


# TODO: Clean up sensor creation using a base class


_ALERT_PRIORITY = {
    Alert.NONE: 0,
    Alert.YELLOW: 1,
    Alert.ORANGE: 2,
    Alert.RED: 3,
}


def _alert_level_from_payload(alert: dict) -> Alert:
    for key in ("alertLevel", "level", "alert_level", "color"):
        if key not in alert:
            continue
        level = alert[key]
        if isinstance(level, str):
            normalized = level.lower()
            if normalized == "green":
                return Alert.NONE
            try:
                return Alert(normalized)
            except ValueError:
                continue
        if isinstance(level, int):
            return {
                0: Alert.NONE,
                1: Alert.YELLOW,
                2: Alert.ORANGE,
                3: Alert.RED,
            }.get(level, Alert.NONE)
    return Alert.NONE


def _highest_alert(alerts: list[dict]) -> dict | None:
    if not alerts:
        return None
    return max(
        alerts, key=lambda alert: _ALERT_PRIORITY[_alert_level_from_payload(alert)]
    )


class NLWeatherAlertSensor(CoordinatorEntity[NLWeatherUpdateCoordinator], SensorEntity):
    def __init__(
        self, coordinator, config_entry: KNMIDirectConfigEntry, subentry: ConfigSubentry
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_alert"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.subentry_id}")},
        )
        self._attr_has_entity_name = True
        self.entity_description = SensorEntityDescription(
            key="alert",
            icon="mdi:weather-cloudy-alert",
            translation_key="weather_alert",
        )

    @property
    def native_value(self):
        alert = _highest_alert(self.coordinator.data["alerts"])
        if alert is None:
            return "none"
        return alert.get("description", "none")


class NLWeatherAlertLevelSensor(
    CoordinatorEntity[NLWeatherUpdateCoordinator], SensorEntity
):
    def __init__(
        self, coordinator, config_entry: KNMIDirectConfigEntry, subentry: ConfigSubentry
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{config_entry.entry_id}_{subentry.subentry_id}_alert_level"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.subentry_id}")},
        )
        self._attr_has_entity_name = True
        self.entity_description = SensorEntityDescription(
            key="alert_level",
            options=[a.value for a in Alert],
            icon="mdi:alert-box",
            translation_key="weather_alert_level",
            device_class=SensorDeviceClass.ENUM,
        )

    @property
    def native_value(self):
        alert = _highest_alert(self.coordinator.data["alerts"])
        if alert is None:
            return Alert.NONE
        return _alert_level_from_payload(alert)


class NLObservationStationDistanceSensor(
    CoordinatorEntity[NLWeatherEDRCoordinator], SensorEntity
):
    def __init__(
        self, coordinator, config_entry: KNMIDirectConfigEntry, subentry: ConfigSubentry
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{config_entry.entry_id}_{subentry.subentry_id}_station_distance"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.subentry_id}")},
        )
        self._attr_has_entity_name = True
        self.entity_description = SensorEntityDescription(
            key="station_distance",
            translation_key="observations_station_distance",
        )
        self.device_class = SensorDeviceClass.DISTANCE
        self._subentry_id = subentry.subentry_id
        self.native_unit_of_measurement = UnitOfLength.KILOMETERS
        self.suggested_display_precision = 1

    @property
    def native_value(self):
        return self.coordinator.data[self._subentry_id]["distance"]


class NLObservationStationNameSensor(
    CoordinatorEntity[NLWeatherEDRCoordinator], SensorEntity
):
    def __init__(
        self, coordinator, config_entry: KNMIDirectConfigEntry, subentry: ConfigSubentry
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{config_entry.entry_id}_{subentry.subentry_id}_station_name"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.subentry_id}")},
        )
        self._attr_has_entity_name = True
        self.entity_description = SensorEntityDescription(
            key="station_name",
            translation_key="observations_station_name",
        )
        self._subentry_id = subentry.subentry_id

    @property
    def native_value(self):
        return self.coordinator.data[self._subentry_id]["station_name"]


class NLObservationTimeSensor(CoordinatorEntity[NLWeatherEDRCoordinator], SensorEntity):
    def __init__(
        self, coordinator, config_entry: KNMIDirectConfigEntry, subentry: ConfigSubentry
    ) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{config_entry.entry_id}_{subentry.subentry_id}_observation_time"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.subentry_id}")},
        )
        self._attr_has_entity_name = True
        self.entity_description = SensorEntityDescription(
            key="time",
            translation_key="observations_time",
        )
        self.device_class = SensorDeviceClass.TIMESTAMP
        self._subentry_id = subentry.subentry_id

    @property
    def native_value(self):
        return self.coordinator.data[self._subentry_id]["datetime"]
