import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID

from ..util import ValueHistory, _get_child_by_tag_name
from .commodity import CommodityId


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
    parent_account_id: UUID | None
    commodity_id: "CommodityId"
    book: "Book | None" = None

    @property
    def parent_account(self) -> "Account | None":
        return self.book.accounts_by_id.get(self.parent_account_id)

    @property
    def child_accounts(self) -> list["Account"]:
        return [
            account
            for account in self.book.accounts_by_id.values()
            if account.parent_account_id == self.id
        ]

    @property
    def transactions(self) -> list["Transaction"]:
        return [
            transaction
            for transaction in self.book.transactions
            if any(position.account_id == self.id for position in transaction.positions)
        ]

    @property
    def commodity(self) -> "Commodity":
        return self.book.commodities_by_id[self.commodity_id]

    @staticmethod
    def from_xml_element(account_element: ET.Element) -> "Account":
        parent_element = _get_child_by_tag_name(account_element, "parent")
        parent_account_id = (
            UUID(parent_element.text) if parent_element is not None else None
        )
        return Account(
            id=UUID(_get_child_by_tag_name(account_element, "id").text),
            name=_get_child_by_tag_name(account_element, "name").text,
            type=AccountType.from_name(
                _get_child_by_tag_name(account_element, "type").text
            ),
            parent_account_id=parent_account_id,
            commodity_id=CommodityId.from_xml_element(
                _get_child_by_tag_name(account_element, "commodity")
            ),
        )

    def __repr__(self) -> str:
        return f"Account {self.name} ({self.id}, {self.type})"

    @property
    def quantity_change_by_date(self) -> "ValueHistory":
        quantity_change_by_date = ValueHistory()
        for date, quantity in (
            (transaction.date, position.quantity)
            for transaction in self.transactions
            for position in transaction.positions
            if position.account.id == self.id
        ):
            if date not in quantity_change_by_date:
                quantity_change_by_date[date] = Decimal(0)
            quantity_change_by_date[date] += quantity
        return quantity_change_by_date

    @property
    def quantity_history(self) -> "ValueHistory":
        return self.quantity_change_by_date.balance_history_from_changes

    @property
    def balance_history(self) -> "ValueHistory":
        quantity_history = self.quantity_history
        if len(quantity_history) == 0:
            return quantity_history

        if self.commodity_id == CommodityId("CURRENCY", "EUR"):
            return quantity_history

        price_history = self.commodity.price_history
        dates = sorted(
            set(quantity_history.dates)
            | set(
                date
                for date in price_history.dates
                if date >= quantity_history.dates[0]
            )
        )
        balances = [quantity_history[date] * price_history[date] for date in dates]
        return ValueHistory(dates, balances)

    @property
    def balance_change_by_date(self) -> "ValueHistory":
        return self.balance_history.balance_changes_from_history

    @property
    def total_balance_change_by_date(self) -> "ValueHistory":
        balance_change_by_date = self.balance_change_by_date
        for child_account in self.child_accounts:
            for date, change in child_account.total_balance_change_by_date.items():
                if date not in balance_change_by_date:
                    balance_change_by_date[date] = Decimal(0)
                balance_change_by_date[date] += change
        return balance_change_by_date

    @property
    def total_balance_history(self) -> "ValueHistory":
        return self.total_balance_change_by_date.balance_history_from_changes
