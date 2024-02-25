import click
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.io as pio
from dash import Dash, dcc, html
from pydantic_settings import BaseSettings, SettingsConfigDict

from .common import Book
from .common.account import Account


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    gnucash_file: str
    assets_account_name: str


def create_asset_allocation_sunburst(account: Account) -> go.Sunburst:
    def get_labels_parents_values(account: Account) -> tuple[list, list, list]:
        labels = [account.name]
        parents = [account.parent_account.name]
        values = [account.total_balance_history.values[-1]]
        for child_account in account.child_accounts:
            labels_to_add, parents_to_add, values_to_add = get_labels_parents_values(
                child_account
            )
            labels += labels_to_add
            parents += parents_to_add
            values += values_to_add
        return labels, parents, values

    labels, parents, values = get_labels_parents_values(account)
    return go.Sunburst(
        labels=labels[1:],
        parents=parents[1:],
        values=values[1:],
        branchvalues="total",
        textinfo="label+percent entry",
    )


@click.command()
def main(**kwargs) -> None:
    settings = Settings()
    book = Book.load(settings.gnucash_file)

    assets_account = next(
        account
        for account in book.accounts
        if account.name == settings.assets_account_name
    )
    assets_balance_history = assets_account.total_balance_history

    app = Dash(__name__, external_stylesheets=[dbc.themes.CYBORG, dbc.icons.BOOTSTRAP])

    assets_over_time_figure = go.Figure(
        go.Scatter(
            x=assets_balance_history.dates,
            y=assets_balance_history.values,
        )
    )
    assets_over_time_figure.update_layout(template="plotly_dark", title="Assets")

    asset_allocation_figure = go.Figure(
        create_asset_allocation_sunburst(assets_account)
    )
    asset_allocation_figure.update_layout(
        template="plotly_dark",
        title="Asset allocation",
        margin=dict(t=0, l=0, r=0, b=0),
    )

    app.layout = html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(dcc.Graph(figure=assets_over_time_figure)),
                    dbc.Col(dcc.Graph(figure=asset_allocation_figure), width=4),
                ]
            )
        ],
    )
    app.run(debug=True)
