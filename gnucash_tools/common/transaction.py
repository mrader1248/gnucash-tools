import datetime
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from ..util import _fraction_string_to_decimal, _get_child_by_tag_name
from .account import Account


@dataclass
class Transaction:
    id: UUID
    date: datetime.date
    description: str
    positions: list["TransactionPosition"]
    book: "Book | None" = None

    def __post_init__(self):
        if sum(p.value for p in self.positions) != 0:
            raise ValueError(f"Sum of transaction position amount is not zero")
        for position in self.positions:
            position.transaction = self

    def __str__(self) -> str:
        def equalize_lens(strings: list[str], pad="<") -> list[str]:
            max_len = max(len(s) for s in strings)
            return [f"{s:{pad}{max_len}}" for s in strings]

        def format_block(
            positions: list["TransactionPosition"], factor: int
        ) -> list[str]:
            names = equalize_lens([p.account.name for p in positions])
            amounts = equalize_lens(
                [f"{p.value * factor:.2f}" for p in positions], pad=">"
            )
            return [f"{name} {x}" for name, x in zip(names, amounts)]

        left_strings = format_block(
            [p for p in self.positions if p.value >= 0], factor=1
        )
        right_strings = format_block(
            [p for p in self.positions if p.value < 0], factor=-1
        )

        n_lines = max(len(left_strings), len(right_strings))
        left_strings += [" " * len(left_strings[0])] * (n_lines - len(left_strings))
        right_strings += [" " * len(right_strings[0])] * (n_lines - len(right_strings))
        seperator_line = "-" * (len(left_strings[0]) + len(right_strings[0]) + 3)

        return (
            f"Transaction {self.id}\n{self.date} {self.description}\n{seperator_line}\n"
            + "\n".join(f"{s1} | {s2}" for s1, s2 in zip(left_strings, right_strings))
        )

    @staticmethod
    def from_xml_element(transaction_element: ET.Element) -> "Transaction":
        split_elements = _get_child_by_tag_name(transaction_element, "splits")
        positions = [
            TransactionPosition(
                account_id=UUID(_get_child_by_tag_name(split_element, "account").text),
                value=_fraction_string_to_decimal(
                    _get_child_by_tag_name(split_element, "value").text
                ),
                quantity=_fraction_string_to_decimal(
                    _get_child_by_tag_name(split_element, "quantity").text
                ),
            )
            for split_element in split_elements
        ]

        return Transaction(
            id=UUID(_get_child_by_tag_name(transaction_element, "id").text),
            date=datetime.date.fromisoformat(
                _get_child_by_tag_name(
                    _get_child_by_tag_name(transaction_element, "date-posted"), "date"
                ).text[:10]
            ),
            description=_get_child_by_tag_name(transaction_element, "description").text,
            positions=positions,
        )

    @staticmethod
    def load(
        path: Path,
        from_date: datetime.date | None = None,
        to_date: datetime.date | None = None,
    ) -> list["Transaction"]:
        return [
            transaction
            for transaction in Book.load(path).transactions
            if (from_date is None or transaction.date >= from_date)
            and (to_date is None or transaction.date <= to_date)
        ]


@dataclass
class TransactionPosition:
    account_id: Account
    value: Decimal
    quantity: Decimal
    transaction: Transaction | None = None

    @property
    def account(self) -> Account:
        return self.transaction.book.accounts_by_id[self.account_id]
