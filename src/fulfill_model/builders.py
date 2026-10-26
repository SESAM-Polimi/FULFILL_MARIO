"""Small, explicit shock builders. Values keep the paper's native hybrid units."""
from pathlib import Path
import hashlib
import json
from importlib.resources import files
import numpy as np
import pandas as pd

Z_COLUMNS = ["row region", "row level", "row sector", "column region", "column level", "column sector", "type", "value"]
Y_COLUMNS = ["row region", "row level", "row sector", "column region", "demand category", "type", "value"]
E_COLUMNS = ["row sector", "column region", "column level", "column sector", "type", "value"]
COLUMNS = {"z": Z_COLUMNS, "Y": Y_COLUMNS, "e": E_COLUMNS}


class MissingSourceSheet(ValueError):
    pass


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def column_name(number):
    value = ""
    while number:
        number, rem = divmod(number - 1, 26)
        value = chr(65 + rem) + value
    return value


class Workbooks:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.cache = {}
        self.hashes = {}
        self.source_keys = {}
        self.background_cache = {}

    def read(self, filename, sheet, depth=1, indices=1):
        key = (filename, str(sheet), depth, indices)
        if key not in self.cache:
            path = self.directory / filename
            if not path.is_file():
                raise FileNotFoundError(f"Missing {path}; run fulfill download or select --inputs")
            self.hashes.setdefault(filename, sha256(path))
            with pd.ExcelFile(path) as book:
                if str(sheet) in book.sheet_names:
                    frame = pd.read_excel(book, sheet_name=str(sheet),
                                          header=list(range(depth)), index_col=list(range(indices)))
                    self.source_keys[(filename, str(sheet))] = filename
                else:
                    raise MissingSourceSheet(f"Missing sheet {sheet!r} in {filename}")
            if frame.index.has_duplicates or frame.columns.has_duplicates:
                raise ValueError(f"Duplicate input labels: {filename}, sheet {sheet}")
            self.cache[key] = frame
        return self.cache[key]

    def published_background(self, step, year):
        """Reuse only already-public instructions when raw BAU sheets are absent."""
        manifest = json.loads((files("fulfill_model") / "resources/public_backgrounds.json").read_text())
        entry = manifest["files"][str(year)]
        key = f"published-backgrounds/{entry['filename']}"
        if year not in self.background_cache:
            path = Path(str(files("fulfill_model") / "resources/paper-backgrounds" / entry["filename"]))
            if not path.exists():
                path = Path(__file__).resolve().parents[2] / "Shocks/filled_files" / entry["filename"]
            if sha256(path) != entry["sha256"]:
                raise ValueError(f"Published background checksum mismatch: {path.name}")
            self.background_cache[year] = pd.read_excel(path, sheet_name=["z", "e"])
            self.hashes[key] = entry["sha256"]
        matrix = step["matrix"]
        table = self.background_cache[year][matrix]
        if step["id"] in ("hs-eff", "hous"):
            selected = pd.Series(False, index=table.index)
            for activity, commodity in step["parameters"]["acts_coms"].items():
                target = step["parameters"].get("target_act", activity)
                selected |= ((table["row level"] == "Commodity") & (table["column level"] == "Activity") &
                             (table["row sector"] == commodity) & (table["column sector"] == target))
        elif step["id"] in ("car-mix", "hs-mix"):
            selected = ((table["row level"] == "Activity") & (table["column level"] == "Commodity") &
                        (table["column sector"] == step["parameters"]["commodity"]))
        elif step["id"] == "hs-emi":
            z = self.background_cache[year]["z"]
            heating = z.loc[(z["row level"] == "Activity") & (z["column sector"] == "Heating services"), "row sector"].unique()
            selected = table["column sector"].isin(heating)
        else:
            raise ValueError(f"No published background adapter for {step['id']}")
        result = table.loc[selected].drop_duplicates().copy()
        if result.empty:
            raise ValueError(f"Empty published background block: {step['id']}")
        result["input_file"] = key
        result["input_cell"] = [f"'{matrix}'!{column_name(len(COLUMNS[matrix]))}{i+2}" for i in result.index]
        result["input_value"] = result.value
        result["transformation"] = "unchanged published BAU background instruction; raw source sheet absent"
        return result.reset_index(drop=True)

    def value(self, filename, sheet, row, column, depth=1, indices=1):
        frame = self.read(filename, sheet, depth, indices)
        try:
            value = float(frame.loc[row, column])
            ri, ci = frame.index.get_loc(row), frame.columns.get_loc(column)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Missing or nonnumeric input: {filename}, {sheet}, {row}, {column}") from exc
        if not np.isfinite(value):
            raise ValueError(f"Nonfinite input: {filename}, {sheet}, {row}, {column}")
        return value, f"'{sheet}'!{column_name(ci + indices + 1)}{ri + depth + 1}"


class TradeWeights:
    def __init__(self, frame):
        required = {"commodity", "consumer", "supplier", "share", "basis"}
        if not required <= set(frame):
            raise ValueError("Trade context has missing columns")
        if frame.duplicated(["commodity", "consumer", "supplier"]).any():
            raise ValueError("Duplicate trade weights")
        if not np.isfinite(frame.share).all():
            raise ValueError("Nonfinite trade weights")
        totals = frame.groupby(["commodity", "consumer"]).share.sum()
        zero_keys = set(map(tuple, frame.loc[frame.basis == "no_baseline_market", ["commodity", "consumer"]].values))
        normal = totals.loc[[key for key in totals.index if key not in zero_keys]]
        if not np.allclose(normal, 1, rtol=0, atol=1e-12) or any(totals.loc[key] != 0 for key in zero_keys):
            raise ValueError("Trade weights must sum to one for each commodity/consumer")
        self.frame = frame.copy()

    def select(self, commodity, consumer):
        rows = self.frame[(self.frame.commodity == commodity) & (self.frame.consumer == consumer)]
        if rows.empty:
            raise ValueError(f"No import-origin weights for {commodity} in {consumer}")
        return rows

    @classmethod
    def from_database(cls, db, commodities):
        rows = []
        y, u = db.Y, db.U
        for commodity in commodities:
            cy = y.loc[(slice(None), slice(None), commodity), :]
            cu = u.loc[(slice(None), slice(None), commodity), :]
            for consumer in db.get_index("Region"):
                value = cy.loc[:, (consumer, slice(None), slice(None))].sum(axis=1)
                basis = "final_demand"
                if value.sum() == 0:
                    value = value + cu.loc[:, (consumer, slice(None), slice(None))].sum(axis=1)
                    basis = "final_plus_intermediate_demand"
                if value.sum() == 0:
                    rows.append(dict(commodity=commodity, consumer=consumer, supplier=consumer,
                                     share=0.0, basis="no_baseline_market"))
                    continue
                for (supplier, _, _), share in (value / value.sum()).items():
                    if share != 0:
                        rows.append(dict(commodity=commodity, consumer=consumer, supplier=supplier, share=share, basis=basis))
        return cls(pd.DataFrame(rows))


def _z(region, row, column, value, *, row_region=None, row_level="Commodity", column_level="Activity", kind="Update", **trace):
    return dict(zip(Z_COLUMNS, [row_region or region, row_level, row, region, column_level, column, kind, value]), **trace)


def _y(region, commodity, category, value, *, row_region=None, kind="Update", **trace):
    return dict(zip(Y_COLUMNS, [row_region or region, "Commodity", commodity, region, category, kind, value]), **trace)


def build_step(step, sheet, year, books, trade, background):
    """Return ordered MARIO rows with source-cell and transformation information."""
    fn = step["archetype"]
    filename = step["workbook"]
    p = step["parameters"]
    if fn == "electricity_mix":
        filename, sheet = f"ele-mix{background}_Full.xlsx", str(year)
    rows = []
    try:
        if fn in ("supply_mix", "technical_requirement", "per_capita_demand"):
            data = books.read(filename, sheet, 2, 2)
        elif fn == "satellite_intensity":
            data = books.read(filename, sheet, 2, 3)
        else:
            data = books.read(filename, sheet)
    except MissingSourceSheet:
        published = json.loads((files("fulfill_model") / "resources/data_manifest.json").read_text())
        if books.hashes[filename] != published["groups"]["shocks"]["files"][filename]["sha256"]:
            raise ValueError(f"Custom workbook {filename} is missing {sheet!r}; add it explicitly instead of falling back to published instructions")
        if background != "BAU":
            raise
        return books.published_background(step, year)

    def value(row, column, depth=1, indices=1):
        number, cell = books.value(filename, sheet, row, column, depth, indices)
        return number, dict(input_file=books.source_keys[(filename, str(sheet))], input_cell=cell, input_value=number,
                            transformation="direct")

    if fn in ("supply_mix", "electricity_mix"):
        if fn == "supply_mix":
            activities = data.index.get_level_values(1).unique()
            for column in data.columns:
                region = column[-1]
                for activity in activities:
                    number, trace = value((year, activity), column, 2, 2)
                    if number < 0:
                        raise ValueError(f"Negative supply share: {filename}, {sheet}")
                    rows.append(_z(region, activity, p["commodity"], number,
                                   row_level="Activity", column_level="Commodity", **trace))
        else:
            for region in data.index:
                for activity in data.columns:
                    number, trace = value(region, activity)
                    if number < 0:
                        raise ValueError(f"Negative supply share: {filename}, {sheet}")
                    rows.append(_z(region, activity, p["commodity"], number,
                                   row_level="Activity", column_level="Commodity", **trace))
    elif fn == "technical_requirement":
        for column in data.columns:
            region = column[-1]
            for activity, commodity in p["acts_coms"].items():
                number, trace = value((year, activity), column, 2, 2)
                target = p.get("target_act", activity)
                if commodity in p.get("com_only_domestic", []):
                    rows.append(_z(region, commodity, target, number, **trace))
                else:
                    for weight in trade.select(commodity, region).itertuples():
                        result = number * weight.share
                        if result != 0:
                            rows.append(_z(region, commodity, target, result, row_region=weight.supplier,
                                           **(trace | dict(trade_share=weight.share, trade_basis=weight.basis,
                                                          transformation="input_value * baseline_origin_share"))))
    elif fn == "per_capita_demand":
        matching = [key for key in data.index if key[0] == year]
        if len(matching) != 1:
            raise ValueError(f"Expected one per-capita row for {year}: {filename}, {sheet}")
        for column in data.columns:
            region = column[-1]
            number, trace = value(matching[0], column, 2, 2)
            pop, cell = books.value("cons_var_Full.xlsx", "Population_no_world", region, year)
            trace.update(population=pop, population_cell=cell, population_file="cons_var_Full.xlsx",
                         transformation="input_value * population")
            rows.append(_y(region, p["commodity"], p["cons_category"], number * pop,
                           kind=p["shock_type"], **trace))
    elif fn == "total_service_demand":
        for region in data.index:
            number, trace = value(region, year)
            rows.append(_y(region, p["commodity"], p["cons_category"], number, **trace))
    elif fn == "scale_final_demand":
        categories = p["cons_category"]
        if isinstance(categories, str):
            categories = [categories]
        for region in data.index:
            number, trace = value(region, year)
            for category in categories:
                rows.append(_y(region, p["commodity"], category, number, row_region="all",
                               kind="Percentage", **trace))
    elif fn == "scale_intermediate_use":
        for region in data.index:
            number, trace = value(region, year)
            rows.append(_z(region, p["commodity"], "all", number, row_region="all",
                           kind="Percentage", **trace))
    elif fn == "satellite_intensity":
        accounts = data.index.get_level_values(0).unique()
        activities = data.index.get_level_values(2).unique()
        for column in data.columns:
            region = column[-1]
            for account in accounts:
                for activity in activities:
                    number, trace = value((account, year, activity), column, 2, 3)
                    rows.append(dict(zip(E_COLUMNS, [account, region, "Activity", activity, "Update", number]), **trace))
    else:
        raise ValueError(f"Unknown archetype {fn}")
    result = pd.DataFrame(rows)
    if result.empty or not np.isfinite(result.value).all():
        raise ValueError(f"Empty or nonfinite shock: {step['id']}")
    return result
