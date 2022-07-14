from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union

from pendulum import Date, DateTime, Duration, Period

from ical_library.base_classes.component import Component
from ical_library.exceptions import MissingRequiredProperty
from ical_library.help_modules.lru_cache import instance_lru_cache
from ical_library.help_modules.timespan import TimespanWithParent
from ical_library.ical_properties.dt import _DTBoth, DTStamp, DTStart
from ical_library.ical_properties.pass_properties import Comment, Summary, UID
from ical_library.ical_properties.periods import EXDate, RDate
from ical_library.ical_properties.rrule import RRule


class AbstractComponentWithDuration(Component, ABC):
    """
    This class helps avoid code repetition with different :class:`Component` classes that have a duration and have
    recurring properties.

    This class is inherited by VEvent, VToDo and VJournal as these all have recurring properties like :class:`RRule`,
    :class:`RDate` and :class:`EXDate`. All properties they had in common are part of this class.
    Note: VJournal is the odd one out as these events don't have a duration.

    :param name: The actual name of this component instance. E.g. VEVENT, RRULE, VCUSTOMCOMPONENT.
    :param dtstamp: The DTStamp property. Required and must occur exactly once.
    :param uid: The UID property. Required and must occur exactly once.
    :param dtstart: The DTStart property. Optional and may occur at most once.
    :param rrule: The RRule property. Optional and may occur at most once.
    :param summary: The Summary property. Optional and may occur at most once.
    :param exdate: The EXDate property. Optional, but may occur multiple times.
    :param rdate: The RDate property. Optional, but may occur multiple times.
    :param comment: The Comment property. Optional, but may occur multiple times.
    :param parent: The Component this item is encapsulated by in the iCalendar data file.
    """

    def __init__(
        self,
        name: str,
        dtstamp: Optional[DTStamp] = None,
        uid: Optional[UID] = None,
        dtstart: Optional[DTStart] = None,
        rrule: Optional[RRule] = None,
        summary: Optional[Summary] = None,
        exdate: Optional[List[EXDate]] = None,
        rdate: Optional[List[RDate]] = None,
        comment: Optional[List[Comment]] = None,
        parent: Optional[Component] = None,
    ):
        super().__init__(name, parent=parent)

        # Required
        self._dtstamp: Optional[DTStamp] = dtstamp
        self._uid: Optional[UID] = uid

        # Optional, may only occur once
        self.dtstart: Optional[DTStart] = dtstart
        self.rrule: Optional[RRule] = rrule
        self.summary: Optional[Summary] = summary

        # Optional, may occur more than once
        self.exdate: Optional[List[EXDate]] = exdate
        self.rdate: Optional[List[RDate]] = rdate
        self.comment: Optional[List[Comment]] = comment

    @property
    def dtstamp(self) -> DTStamp:
        """A getter to ensure the required property is set."""
        if self._dtstamp is None:
            raise MissingRequiredProperty(self, "dtstamp")
        return self._dtstamp

    @dtstamp.setter
    def dtstamp(self, value: DTStamp):
        """A setter to set the required property."""
        self._dtstamp = value

    @property
    def uid(self) -> UID:
        """A getter to ensure the required property is set."""
        if self._uid is None:
            raise MissingRequiredProperty(self, "uid")
        return self._uid

    @uid.setter
    def uid(self, value: UID):
        """A setter to set the required property."""
        self._uid = value

    @property
    @abstractmethod
    def ending(self) -> _DTBoth:
        """
        As the argument for this is different in each class, we ask this to be implemented.

        :return: The ending of the :class:`Component`, except for :class:`VJournal` which returns the start.
        """
        pass

    @abstractmethod
    def get_duration(self) -> Optional[Duration]:
        """
        As the duration is not present in each of them, we ask this to be implemented by the subclasses.

        :return: The duration of the :class:`Component`.
        """
        pass

    def __eq__(self: "AbstractComponentWithDuration", other: "AbstractComponentWithDuration") -> bool:
        """Return whether the current instance and the other instance are the same."""
        if type(self) != type(other):
            return False
        return (
            self.dtstart == other.dtstart
            and self.ending == other.ending
            and self.summary == other.summary
            and self.comment == other.comment
        )

    @property
    def timespan(self) -> TimespanWithParent:
        """
        Return a timespan as a property representing the start and end of the instance.
        :return: A timespan instance with this class instance as parent.
        """
        if self.start is None or self.end is None:
            raise ValueError(f"{self.start=} and {self.end=} may not be None.")
        return TimespanWithParent(parent=self, begin=self.start, end=self.end)

    @property
    @instance_lru_cache()
    def start(self) -> Optional[Union[Date, DateTime]]:
        """Return the start of this Component as a :class:`Date` or :class:`DateTime` value."""
        return self.dtstart.datetime_or_date_value if self.dtstart else None

    @property
    @instance_lru_cache()
    def end(self) -> Optional[Union[Date, DateTime]]:
        """Return the ending of this Component as a Date or DateTime value."""
        if self.ending:
            return self.ending.datetime_or_date_value
        elif self.start and self.get_duration():
            return self.start + self.get_duration()
        return None

    @property
    @instance_lru_cache()
    def computed_duration(self: "AbstractComponentWithDuration") -> Optional[Duration]:
        """Return the duration of this Component as a :class:`Date` or :class:`DateTime` value."""
        if a_duration := self.get_duration():
            return a_duration
        elif self.end and self.start:
            result: Period = self.end - self.start
            return result
        return None


class AbstractRecurringComponentWithDuration(AbstractComponentWithDuration, ABC):
    """
    This class extends :class:`AbstractComponentWithDuration` to represent a recurring Component.

    This class is inherited by VRecurringEvent, VRecurringToDo and VRecurringJournal. When we compute the recurrence
    based on the :class:`RRule`, :class:`RDate` and :class:`EXDate` properties, we create new occurrences of that
    specific component. Instead of copying over all Properties (and using a lot of memory), this class overwrites the
    *__getattribute__* function to act like the original component for most attributes except for *start*, *end*,
    *original* and *parent*.
    """

    def __getattribute__(self, name: str) -> Any:
        """
        Overwrite this function to return the originals properties except for *start*, *end*, *original* and *parent*.

        Depending on the attributes *name* we are requesting, we either return its own properties or the original
        components properties. This way we don't need to copy over all the variables.
        :param name: Name of the attribute we are accessing.
        :return: The value of the attribute we are accessing either from the *original* or from this instance itself.
        """
        if name in ("_start", "_end", "_original", "_parent", "start", "end", "original", "parent"):
            return object.__getattribute__(self, name)
        if name in ("_name", "_extra_child_components", "_extra_properties"):
            return object.__getattribute__(self._original, name)
        if name in self._original.get_property_ical_names():
            return object.__getattribute__(self._original, name)
        return object.__getattribute__(self, name)

    def __setattr__(self, key: str, value: Any) -> None:
        """Overwrite the custom __setattr__ from Components to set it back to the standard behavior."""
        object.__setattr__(self, key, value)

    @property
    def start(self) -> DateTime:
        """Return the start of this recurring event."""
        return self._start

    @property
    def end(self) -> DateTime:
        """Return the end of this recurring event."""
        return self._end

    @property
    def original(self) -> AbstractComponentWithDuration:
        """Return the original component that created this recurring component."""
        return self._original

    @property
    def parent(self) -> Component:
        """Return the parent of the original component."""
        return self._original.parent