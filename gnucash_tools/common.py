import datetime
import gzip
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from pathlib import Path
from typing import Generator
from uuid import UUID


def _get_children_by_tag_name(
    element: ET.Element, tag_name: str
) -> Generator[ET.Element, None, None]:
    return (child for child in element if child.tag.endswith(tag_name))


def _get_child_by_tag_name(element: ET.Element, tag_name: str) -> ET.Element:
    return next(_get_children_by_tag_name(element, tag_name))


def _fraction_string_to_decimal(s: str) -> Decimal:
    x = Fraction(s)
    return Decimal(x.numerator) / Decimal(x.denominator)


class AccountType(Enum):
    ROOT = 0
    EQUITY = 1
    ASSET = 10
    BANK = 11
    RECEIVABLE = 12
    LIABILITY = 20
    INCOME = 30
    EXPENSE = 40
    STOCK = 50

    @staticmethod
    def from_name(name: str) -> "AccountType":
        result = next((t for t in AccountType if t.name == name), None)
        if result is not None:
            return result
        else:
            raise ValueError(f"Unknown account type '{name}'")


@dataclass
class Account:
    id: UUID
    name: str
    type: AccountType

    @staticmethod
    def from_xml_element(account_element: ET.Element) -> "Account":
        return Account(
            id=UUID(_get_child_by_tag_name(account_element, "id").text),
            name=_get_child_by_tag_name(account_element, "name").text,
            type=AccountType.from_name(
                _get_child_by_tag_name(account_element, "type").text
            ),
        )


@dataclass
class Transaction:
    id: UUID
    date: datetime.date
    description: str
    positions: list["TransactionPosition"]

    def __post_init__(self):
        if sum(p.amount for p in self.positions) != 0:
            raise ValueError(f"Sum of transaction position amount is not zero")

    def __str__(self) -> str:
        def equalize_lens(strings: list[str], pad="<") -> list[str]:
            max_len = max(len(s) for s in strings)
            return [f"{s:{pad}{max_len}}" for s in strings]

        def format_block(
            positions: list["TransactionPosition"], factor: int
        ) -> list[str]:
            names = equalize_lens([p.account.name for p in positions])
            amounts = equalize_lens(
                [f"{p.amount * factor:.2f}" for p in positions], pad=">"
            )
            return [f"{name} {x}" for name, x in zip(names, amounts)]

        left_strings = format_block(
            [p for p in self.positions if p.amount >= 0], factor=1
        )
        right_strings = format_block(
            [p for p in self.positions if p.amount < 0], factor=-1
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
    def from_xml_element(
        transaction_element: ET.Element, accounts_by_id: dict[UUID, Account]
    ) -> "Transaction":
        split_elements = _get_child_by_tag_name(transaction_element, "splits")
        positions = [
            TransactionPosition(
                account=accounts_by_id[
                    UUID(_get_child_by_tag_name(split_element, "account").text)
                ],
                amount=_fraction_string_to_decimal(
                    _get_child_by_tag_name(split_element, "value").text
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
        with gzip.open(path, "r") as gnucash_file:
            tree = ET.parse(gnucash_file)
        book = _get_child_by_tag_name(tree.getroot(), "book")

        accounts_by_id = {
            account.id: account
            for account in (
                Account.from_xml_element(account_element)
                for account_element in _get_children_by_tag_name(book, "account")
            )
        }

        return [
            transaction
            for transaction in (
                Transaction.from_xml_element(e, accounts_by_id)
                for e in _get_children_by_tag_name(book, "transaction")
            )
            if (from_date is None or transaction.date >= from_date)
            and (to_date is None or transaction.date <= to_date)
        ]


@dataclass
class TransactionPosition:
    account: Account
    amount: Decimal
