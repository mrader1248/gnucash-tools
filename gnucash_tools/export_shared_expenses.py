import datetime
import json
from pathlib import Path

import click
from pydantic_settings import BaseSettings, SettingsConfigDict

from .common import AccountType, Transaction


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    gnucash_file: str
    shared_receivable_account: str
    account_name_mapping_file: str


class App:
    def __init__(self, from_date: datetime.datetime, to_date: datetime.datetime):
        self.settings = Settings()
        self.from_date = from_date
        self.to_date = to_date

    def run(self) -> None:
        self.load_data()
        self.process_transactions()

    def load_data(self) -> None:
        self.transactions = [
            transaction
            for transaction in Transaction.load(
                self.settings.gnucash_file, self.from_date.date(), self.to_date.date()
            )
            if any(
                position.account.name == self.settings.shared_receivable_account
                for position in transaction.positions
            )
        ]

        with open(self.settings.account_name_mapping_file, "r") as file:
            self.account_name_map = json.load(file)

    def process_transactions(self) -> None:
        skipped_transactions = []

        for transaction in self.transactions:
            shared_receivable_positions = [
                p
                for p in transaction.positions
                if p.account.name == self.settings.shared_receivable_account
            ]
            expense_positions = [
                p
                for p in transaction.positions
                if p.account.type == AccountType.EXPENSE
            ]
            if (
                len(shared_receivable_positions) == 1
                and len(expense_positions) >= 1
                and all(
                    p.account.id == expense_positions[0].account.id
                    for p in expense_positions
                )
            ):
                account_name = expense_positions[0].account.name
                account_name = self.account_name_map.get(account_name, account_name)
                print(
                    f"{transaction.date},{transaction.description},"
                    f"{account_name},"
                    f"{2*shared_receivable_positions[0].amount}"
                )
            else:
                skipped_transactions.append(transaction)

        if skipped_transactions:
            print("\nThe following transactions could not be handled:\n")
            print("\n\n".join(str(t) for t in skipped_transactions))


@click.command()
@click.option("--from-date", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--to-date", required=True, type=click.DateTime(formats=["%Y-%m-%d"]))
def main(**kwargs) -> None:
    App(**kwargs).run()
