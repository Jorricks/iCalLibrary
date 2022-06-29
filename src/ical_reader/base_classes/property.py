from typing import Dict, Optional, TYPE_CHECKING

from ical_reader.base_classes.base_class import ICalBaseClass
from ical_reader.ical_utils.lru_cache import instance_lru_cache

if TYPE_CHECKING:
    from ical_reader.base_classes.calendar_component import CalendarComponent


class Property(ICalBaseClass):
    def __init__(self, parent: "CalendarComponent", name: str, sub_properties: Optional[str], value: Optional[str]):
        self._parent: "CalendarComponent" = parent
        self._name: str = name
        self._sub_properties: Optional[str] = sub_properties
        self._value: Optional[str] = value

    @property
    def parent(self) -> "CalendarComponent":
        return self._parent

    @property
    def name(self) -> str:
        return self._name

    @property
    @instance_lru_cache()
    def sub_properties(self) -> Dict[str, str]:
        sub_properties_str = self._sub_properties or ""
        return {
            key_and_value.split("=")[0]: key_and_value.split("=")[1]
            for key_and_value in sub_properties_str.split(";")
            if key_and_value.count("=") == 1
        }

    def has_sub_property(self, key: str) -> Optional[bool]:
        return key in self.sub_properties

    def get_sub_property(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.sub_properties.get(key, default)

    def get_sub_property_default(self, key: str, default: str) -> str:
        return self.sub_properties.get(key, default)

    @property
    def value(self) -> Optional[str]:
        return self._value

    @property
    def as_original_string(self) -> str:
        add_subs = f";{self._sub_properties.strip(';')}" if self._sub_properties else ""
        return f"{self._name}{add_subs}:{self._value}"
