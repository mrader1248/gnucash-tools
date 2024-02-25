import gzip
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from ..util import _get_child_by_tag_name, _get_children_by_tag_name
from .account import Account
from .commodity import Commodity, CommodityId
from .transaction import Transaction


@dataclass
class Book:
    accounts_by_id: dict[UUID, Account] = field(default_factory=dict)
    transactions: list[Transaction] = field(default_factory=list)
    commodities_by_id: dict[CommodityId, Commodity] = field(default_factory=dict)

    @property
    def accounts(self) -> list[Account]:
        return list(self.accounts_by_id.values())

    @property
    def commodities(self) -> list[Commodity]:
        return list(self.commodities_by_id.values())

    def add_commodity(self, commodity: Commodity) -> None:
        commodity.book = self
        self.commodities_by_id[commodity.id] = commodity

    def add_account(self, account: Account) -> None:
        if account.id in self.accounts_by_id.keys():
            raise ValueError(f"Account {account} already added to book")

        account.book = self
        self.accounts_by_id[account.id] = account

    def add_transaction(self, transaction: Transaction) -> None:
        transaction.book = self
        self.transactions.append(transaction)

    @staticmethod
    def load(path: Path) -> "Book":
        book = Book()

        with gzip.open(path, "r") as gnucash_file:
            tree = ET.parse(gnucash_file)
        book_element = _get_child_by_tag_name(tree.getroot(), "book")

        for commodity_element in _get_children_by_tag_name(book_element, "commodity"):
            book.add_commodity(Commodity.from_xml_element(commodity_element))

        if pricedb_element := _get_child_by_tag_name(book_element, "pricedb"):
            for price_element in _get_children_by_tag_name(pricedb_element, "price"):
                commodity_id = CommodityId.from_xml_element(
                    _get_child_by_tag_name(price_element, "commodity")
                )
                book.commodities_by_id[
                    commodity_id
                ].price_history.insert_from_xml_element(price_element)

        for account_element in _get_children_by_tag_name(book_element, "account"):
            book.add_account(Account.from_xml_element(account_element))

        for transaction_element in _get_children_by_tag_name(
            book_element, "transaction"
        ):
            book.add_transaction(Transaction.from_xml_element(transaction_element))

        return book
