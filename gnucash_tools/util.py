import bisect
import datetime
import xml.etree.ElementTree as ET
from decimal import Decimal
from fractions import Fraction
from itertools import accumulate
from pathlib import Path
from typing import Generator


def _get_children_by_tag_name(
    element: ET.Element, tag_name: str
) -> Generator[ET.Element, None, None]:
    return (child for child in element if child.tag.endswith(tag_name))


def _get_child_by_tag_name(element: ET.Element, tag_name: str) -> ET.Element:
    return next(_get_children_by_tag_name(element, tag_name), None)


def _fraction_string_to_decimal(s: str) -> Decimal:
    x = Fraction(s)
    return Decimal(x.numerator) / Decimal(x.denominator)


class ValueHistory:
    def __init__(self, dates=[], values=[]):
        self.dates = dates
        self.values = values

    def __getitem__(self, date: datetime.date) -> Decimal:
        if len(self) == 0:
            raise KeyError("Empty price history")

        j = bisect.bisect(self.dates, date) - 1

        if j == -1:
            raise KeyError(
                f"No price available for {date}; history ranges from {self.dates[0]} "
                f"to {self.dates[-1]}"
            )

        return self.values[j]

    def __setitem__(self, date: datetime.date, value: Decimal) -> None:
        j = bisect.bisect(self.dates, date)
        if 0 < j <= len(self) and date == self.dates[j - 1]:
            self.values[j - 1] = value
        else:
            self.dates = self.dates[:j] + [date] + self.dates[j:]
            self.values = self.values[:j] + [value] + self.values[j:]

    def __contains__(self, date: datetime.date) -> bool:
        return date in self.dates

    def __len__(self) -> int:
        return len(self.dates)

    def insert_from_xml_element(self, element: ET.Element) -> None:
        date = datetime.date.fromisoformat(
            _get_child_by_tag_name(
                _get_child_by_tag_name(element, "time"), "date"
            ).text[:10]
        )
        value = _fraction_string_to_decimal(
            _get_child_by_tag_name(element, "value").text
        )
        self[date] = value

    def __repr__(self) -> str:
        return "\n".join(
            f"{date} {value}" for date, value in zip(self.dates, self.values)
        )

    def items(self) -> Generator[tuple[datetime.date, Decimal], None, None]:
        # for date, value in zip(self.dates, self.values):
        #     yield date, value

        return zip(self.dates, self.values)

    @property
    def balance_history_from_changes(self) -> "ValueHistory":
        return ValueHistory(list(self.dates), list(accumulate(self.values)))

    @property
    def balance_changes_from_history(self) -> "ValueHistory":
        if len(self) == 0:
            return self
        else:
            return ValueHistory(
                list(self.dates),
                [self.values[0]]
                + [y - x for x, y in zip(self.values[:-1], self.values[1:])],
            )

    def __add__(self, other: "ValueHistory"):
        if len(self) == 0:
            return other
        elif len(other) == 0:
            return self
        elif self.dates[0] > other.dates[0]:
            return other + self
        else:
            k = next(
                (j for j in range(len(self)) if self.dates[j] >= other.dates[0]), 0
            )
            dates1 = self.dates[:k]
            values1 = self.values[:k]
            dates2 = sorted(set(self.dates[k:]) | set(other.dates))
            values2 = [self[date] + other[date] for date in dates2]
            return ValueHistory(dates1 + dates2, values1 + values2)
