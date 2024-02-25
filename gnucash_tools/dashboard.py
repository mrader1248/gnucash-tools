import click
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.io as pio
from dash import Dash, dcc, html
from pydantic_settings import BaseSettings, SettingsConfigDict

from .common import Book


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    gnucash_file: str
    assets_account_name: str


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
    figure = go.Figure(
        go.Scatter(
            x=assets_balance_history.dates,
            y=assets_balance_history.values,
        )
    )
    figure.update_layout(template="plotly_dark", title="Vermögen")
    app.layout = dbc.Container(
        [dbc.Row([dbc.Col([dcc.Graph(figure=figure)])])],
    )
    app.run(debug=True)
