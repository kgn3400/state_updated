"""Enum extended."""

from enum import Enum
from functools import total_ordering
from typing import Self, overload


# ------------------------------------------------------
# ------------------------------------------------------
@total_ordering
class EnumExt(Enum):
    """Enum extended."""

    # ------------------------------------------------------
    def __lt__(self, other: Self | int) -> bool:
        """Lower than."""
        try:
            if isinstance(self.value, int) and isinstance(other.value, int):
                return self.value < other.value

            cls_members = self.__class__._member_names_
            return cls_members.index(self.name) < cls_members.index(other.name)

        except AttributeError:
            return self.value < other

    # ------------------------------------------------------
    def __eq__(self, other: object) -> bool:
        """Equal."""
        if isinstance(other, Enum):
            return self.value == other.value
        return self.value == other

    # ------------------------------------------------------
    def __str__(self):
        """Str."""
        return str(self.value)

    # ------------------------------------------------------
    @overload
    @classmethod
    def range(cls) -> list[Self]: ...

    # ------------------------------------------------------
    @overload
    @classmethod
    def range(cls, *, start: Self) -> list[Self]: ...

    # ------------------------------------------------------
    @overload
    @classmethod
    def range(cls, stop: Self, incl_stop: bool = False) -> list[Self]: ...

    # ------------------------------------------------------
    @overload
    @classmethod
    def range(cls, start: Self, stop: Self, incl_stop: bool = False) -> list[Self]: ...

    # ------------------------------------------------------
    @classmethod
    def range(cls, *args, **kwargs) -> list[Self]:
        """range().

        or

        range(start=start Enum).

        or

        range(stop Enum, incl_stop: bool = False).

        or

        range(start Enum, stop Enum, incl_stop: bool = False).

        Returns:
            list[Enum]

        """  # noqa: D402
        members = list(cls)
        if not members:
            return []

        start = kwargs.get("start", args[0] if len(args) > 0 else members[0])

        if len(args) == 1 and "start" not in kwargs:
            stop = args[0]
            start = members[0]
        else:
            stop = kwargs.get("stop", args[1] if len(args) > 1 else members[-1])

        has_explicit_stop = (
            (len(args) == 1 and "start" not in kwargs)
            or len(args) > 1
            or "stop" in kwargs
        )
        default_incl = not has_explicit_stop

        incl_stop = kwargs.get("incl_stop", args[2] if len(args) > 2 else default_incl)

        try:
            index_start = members.index(start)
            index_stop = members.index(stop) + (1 if incl_stop else 0)
        except ValueError as err:
            raise ValueError("Start- or stop-parameterdoes not exist") from err

        if index_start > index_stop:
            raise IndexError("start_stop must be less than stop")

        return members[index_start:index_stop]

    # ------------------------------------------------------
    def succ(self, cycle: bool = False) -> Self:
        """Succ."""
        members = list(self.__class__)
        index = members.index(self) + 1

        if index >= len(members):
            if cycle:
                return members[0]
            raise StopIteration("end of enumeration reached")

        return members[index]

    # ------------------------------------------------------
    @property
    def next(self) -> Self:
        """Next."""
        return self.succ()

    # ------------------------------------------------------
    def pred(self, cycle: bool = False) -> Self:
        """Pred."""
        members = list(self.__class__)
        index = members.index(self) - 1
        if index < 0:
            if cycle:
                return members[-1]
            raise StopIteration("beginning of enumeration reached")

        return members[index]

    # ------------------------------------------------------
    @property
    def prev(self) -> Self:
        """Prev."""
        return self.pred()
