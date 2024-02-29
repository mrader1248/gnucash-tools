from functools import reduce

import click
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.io as pio
from dash import Dash, dcc, html
from pydantic_settings import BaseSettings, SettingsConfigDict

from .common import Account, AccountType, Book


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    gnucash_file: str


def create_asset_allocation_sunburst(book: Book) -> go.Sunburst:
    asset_accounts = [
        account
        for account in book.accounts
        if account.type not in {AccountType.INCOME, AccountType.EXPENSE}
        and not account.is_root_account
        and len(total_balance_history := account.total_balance_history) > 0
        and total_balance_history.values[-1] > 0
    ]
    labels = [account.name for account in asset_accounts]
    parents = [
        (account.parent_account.name if account.parent_account_id is not None else "")
        for account in asset_accounts
    ]
    values = [account.total_balance_history.values[-1] for account in asset_accounts]

    return go.Sunburst(
        labels=labels[1:],
        parents=parents[1:],
        values=values[1:],
        branchvalues="total",
        textinfo="label+percent entry+value",
        hoverinfo="label+percent entry+value",
        maxdepth=3,
        insidetextorientation="horizontal",
    )


def create_equity_over_time_plot(book: Book):
    equity = reduce(
        lambda x, y: x + y,
        (
            account.total_balance_history
            for root_account in book.accounts
            if root_account.parent_account_id is None
            for account in root_account.child_accounts
            if account.type
            not in {AccountType.INCOME, AccountType.EXPENSE, AccountType.EQUITY}
        ),
    )
    return go.Scatter(
        x=equity.dates,
        y=equity.values,
    )


@click.command()
def main(**kwargs) -> None:
    settings = Settings()
    book = Book.load(settings.gnucash_file)

    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
        # external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP]
    )
    FIGURE_TEMPLATE = "plotly_white"

    equity_over_time_figure = go.Figure(create_equity_over_time_plot(book))
    equity_over_time_figure.update_layout(
        template=FIGURE_TEMPLATE,
        yaxis_title="Equity",
        margin=dict(t=0, l=0, r=0, b=0),
    )

    asset_allocation_figure = go.Figure(create_asset_allocation_sunburst(book))
    asset_allocation_figure.update_layout(
        template=FIGURE_TEMPLATE,
        title="Asset allocation",
        margin=dict(t=0, l=0, r=0, b=0),
    )

    app.layout = dbc.Container(  # html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(figure=equity_over_time_figure)),
                    dbc.Col(dcc.Graph(figure=asset_allocation_figure), width=4),
                ]
            )
        ],
    )
    app.run(debug=True)
