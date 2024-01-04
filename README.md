# gnucash-tools

## Installation
Install with `poetry`:
```shell
git clone https://github.com/mrader1248/gnucash-tools.git
cd gnucash-tools
poetry install
```

## export-shared-expenses
To call the command `export-shared-expenses`, the following environment variables need to be set:
- `GNUCASH_FILE`: Path to the Gnucash file
- `SHARED_RECEIVABLE_ACCOUNT`: Name of the receivable account that is used to identify transactions to export
- `ACCOUNT_NAME_MAPPING_FILE`: Path to a JSON file that contains the mapping from Gnucash account names to output names

These environment variables can be set via a `.env` file.

The command itself can be called with:
```shell
poetry run gct-export-shared-expenses --from-date "2023-12-01" --to-date "2023-12-31"
```
