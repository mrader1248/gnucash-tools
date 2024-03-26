from decimal import Decimal
from functools import reduce
from typing import Callable

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


def create_sunburst(
    book: Book,
    select_account: Callable[Account, bool],
    get_value_from_account: Callable[Account, Decimal],
    return_total_value=False,
    additional_slice: tuple[str, Decimal] = None,
    maxdepth=3,
) -> go.Sunburst:
    accounts = [account for account in book.accounts if select_account(account)]
    labels = [account.name for account in accounts]
    parents = [
        (account.parent_account.name if account.parent_account_id is not None else "")
        for account in accounts
    ]
    values = [get_value_from_account(account) for account in accounts]

    root_index = next(j for j in range(len(accounts)) if parents[j] not in labels)

    if additional_slice is not None:
        additional_slice_label, additional_slice_value = additional_slice
        values[root_index] += additional_slice_value
        labels.append(additional_slice_label)
        parents.append(labels[root_index])
        values.append(additional_slice_value)

    sunburst = go.Sunburst(
        labels=labels[1:],
        parents=parents[1:],
        values=values[1:],
        branchvalues="total",
        textinfo="label+percent entry+value",
        hoverinfo="label+percent entry+value",
        maxdepth=maxdepth,
        insidetextorientation="horizontal",
    )
    if return_total_value:
        total_value = values[root_index]
        return sunburst, total_value
    else:
        return sunburst


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
        # external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP],
    )
    FIGURE_TEMPLATE = "plotly_white"
    # FIGURE_TEMPLATE = "plotly_dark"

    equity_over_time_figure = go.Figure(create_equity_over_time_plot(book))
    equity_over_time_figure.update_layout(
        template=FIGURE_TEMPLATE,
        margin=dict(t=0, l=0, r=0, b=0),
    )

    cashflow_in_sunburst, cashflow_in_total = create_sunburst(
        book,
        lambda account: account.type == AccountType.INCOME,
        lambda account: -account.total_balance_history.values[-1],
        return_total_value=True,
        maxdepth=3,
    )
    cashflow_out_sunburst, cashflow_out_total = create_sunburst(
        book,
        lambda account: account.type == AccountType.EXPENSE,
        lambda account: account.total_balance_history.values[-1],
        return_total_value=True,
        maxdepth=3,
    )
    if cashflow_in_total > cashflow_out_total:
        cashflow_out_sunburst = create_sunburst(
            book,
            lambda account: account.type == AccountType.EXPENSE,
            lambda account: account.total_balance_history.values[-1],
            additional_slice=("Savings", cashflow_in_total - cashflow_out_total),
            maxdepth=3,
        )
    else:
        raise NotImplementedError()

    cashflow_in_figure = go.Figure(cashflow_in_sunburst)
    cashflow_in_figure.update_layout(
        template=FIGURE_TEMPLATE,
        margin=dict(t=0, l=0, r=0, b=0),
    )

    cashflow_out_figure = go.Figure(cashflow_out_sunburst)
    cashflow_out_figure.update_layout(
        template=FIGURE_TEMPLATE,
        margin=dict(t=0, l=0, r=0, b=0),
    )

    asset_allocation_figure = go.Figure(
        create_sunburst(
            book,
            lambda account: (
                account.type not in {AccountType.INCOME, AccountType.EXPENSE}
                and not account.is_root_account
                and len(total_balance_history := account.total_balance_history) > 0
                and total_balance_history.values[-1] > 0
            ),
            lambda account: account.total_balance_history.values[-1],
        )
    )
    asset_allocation_figure.update_layout(
        template=FIGURE_TEMPLATE,
        title="Asset allocation",
        margin=dict(t=0, l=0, r=0, b=0),
    )

    app.layout = dbc.Container(  # html.Div(
        [
            dbc.Row([dbc.Col([html.H2("Equity"), html.Br()])]),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(figure=equity_over_time_figure)),
                ]
            ),
            dbc.Row([dbc.Col([html.Br(), html.Br(), html.H2("Cashflow"), html.Br()])]),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(figure=cashflow_in_figure), width=6),
                    dbc.Col(dcc.Graph(figure=cashflow_out_figure), width=6),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [html.Br(), html.Br(), html.H2("Asset allocation"), html.Br()]
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(figure=asset_allocation_figure), width=6),
                ]
            ),
        ],
    )
    app.run(debug=True)
