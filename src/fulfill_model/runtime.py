"""Run an inspected plan through the paper's pinned MARIO engine."""
import importlib.metadata
import json
from pathlib import Path
import time
import numpy as np
import pandas as pd

from .builders import sha256

EU27 = ["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK", "IT"]
REPLACED_COMMODITIES = ["Products of meat cattle", "Products of meat pigs", "Products of meat poultry", "Dairy products", "Fish products", "Vegetables; fruit; nuts", "Food products nec", "products of Vegetable oils and fats", "Beverages", "Sugar", "Liquid fuels", "Liquefied Petroleum Gases (LPG)", "Natural gas and services related to natural gas extraction; excluding surveying", "Chemicals nec", "Electricity"]


def load_database(directory="Data", *, air_transport_extra=False, progress=print):
    import mario
    if mario.__version__ != "0.3.5":
        raise RuntimeError(f"FULFILL's paper profile requires mariopy==0.3.5; found {mario.__version__}. Use a dedicated environment.")
    path = Path(directory) / "MARIO database/flows"
    progress(f"Loading the full published SUT: {path.resolve()}")
    start = time.perf_counter()
    db = mario.parse_from_txt(str(path), table="SUT", mode="flows", calc_all=False)
    # Optional operation copied from notebook 1, step 5. The ready-made public
    # ZIP does not contain this extra account; it must not appear silently.
    if air_transport_extra and "Air transport extra emissions" not in db.E.index:
        air = db.E.loc[["Carbon dioxide, fossil"]].copy()
        activities = db.search("Activity", "Air transport")
        if len(activities) != 1:
            raise ValueError(f"Expected exactly one air transport activity, found {activities}")
        air.loc[:, air.columns.get_level_values(2) != activities[0]] = 0
        air.index = ["Air transport extra emissions"]
        db.add_extensions(io=air, matrix="E", units=pd.DataFrame({"unit": ["tonnes"]}, index=air.index), inplace=True)
    progress(f"Loaded {len(db.get_index('Region'))} regions in {time.perf_counter() - start:.1f} s")
    return db


def clusters(db):
    return {"Commodity": {"all": db.get_index("Commodity"), "Involved commodities": REPLACED_COMMODITIES},
            "Activity": {"all": db.get_index("Activity")},
            "Region": {"all": db.get_index("Region"), "Involved regions": EU27},
            "Consumption category": {"all": db.get_index("Consumption category")}}


def _unit(db, account_type, account):
    key = "Satellite account" if account_type != "V" else "Factor of production"
    try:
        value = db.units[key].loc[account, "unit"]
        return str(value) if pd.notna(value) else "unspecified in published database"
    except KeyError:
        return "unspecified in published database"


def account_results(db, scenario):
    """Production accounts and direct final-demand accounts, in original units.

    This does not label production-region totals as consumption footprints.
    No value-added components or employment categories are silently summed.
    """
    rows = []
    for matrix in ("E", "EY", "V"):
        frame = db.query(matrices=[matrix], scenarios=[scenario])
        if not np.isfinite(frame.to_numpy()).all():
            raise ValueError(f"Nonfinite model result: {matrix}")
        totals = frame.T.groupby(level=0, sort=False).sum().T
        for account, values in totals.iterrows():
            for region, value in values.items():
                rows.append(dict(scenario=scenario, matrix=matrix, account=account,
                                 region=region, value=value, unit=_unit(db, matrix, account),
                                 boundary="production region" if matrix != "EY" else "direct final-demand region"))
    return pd.DataFrame(rows)


def run_plan(db, plan, directory, *, overwrite=False, excel=False, keep_scenario=False, progress=print):
    directory = Path(directory)
    plan.save(directory, overwrite=overwrite, excel=excel)
    scenario = plan.case.identifier
    if scenario in db.matrices:
        raise ValueError(f"Scenario already exists in this database: {scenario}")
    start = time.perf_counter()
    progress(f"Running {scenario} on the full SUT (MARIO 0.3.5)")
    # MARIO 0.3.5's dictionary adapter expects uppercase keys, although its
    # Excel adapter reads lowercase z/e sheets. The instruction columns match.
    native = {"Z": plan.tables["z"], "Y": plan.tables["Y"], "E": plan.tables["e"]}
    db.shock_calc(io=native, z=True, Y=True, e=True, scenario=scenario, **clusters(db))
    solved = time.perf_counter() - start
    results = account_results(db, scenario)
    results.to_csv(directory / "accounts.csv", index=False)
    # Export each production quantity with its sector and unit: adding these
    # together would mix tonnes, TJ, meals, mobility and monetary services.
    production = db.query(matrices=["X"], scenarios=[scenario]).copy()
    production.columns = ["value"]
    production.index.names = ["region", "level", "sector"]
    production = production.reset_index()
    production["unit"] = [_sector_unit(db, level, sector) for level, sector in zip(production.level, production.sector)]
    production.to_csv(directory / "production.csv", index=False)
    record = dict(case=plan.case.to_dict(), solve_seconds=solved, total_seconds=time.perf_counter() - start,
                  engine=importlib.metadata.version("mariopy"), numpy=np.__version__, pandas=pd.__version__,
                  database="Published prepared FULFILL SUT, Zenodo 15341618",
                  air_transport_extra="Air transport extra emissions" in db.E.index,
                  scope="One scenario starting from the published 2011 baseline. Compare with the same background/year and no measures, not with unprojected 2011.",
                  results="E/V by production region, EY by final-demand region, X by sector. Not the paper's full figure pipeline or consumption footprints.",
                  code={p.name: sha256(p) for p in Path(__file__).parent.glob("*.py")},
                  outputs={p.name: sha256(p) for p in directory.iterdir() if p.is_file() and p.name != "run.json"})
    (directory / "run.json").write_text(json.dumps(record, indent=2) + "\n")
    if not keep_scenario:
        del db.matrices[scenario]
    progress(f"Saved {scenario}: {directory.resolve()} (solve {solved:.1f} s)")
    return results


def _sector_unit(db, level, sector):
    try:
        unit = db.units[level].loc[sector, "unit"]
        return str(unit) if pd.notna(unit) else "unspecified in published database"
    except KeyError:
        return "unspecified in published database"


def compare_accounts(control, scenario):
    keys = ["matrix", "account", "region", "unit", "boundary"]
    result = control.drop(columns="scenario").rename(columns={"value": "control_value"}).merge(
        scenario.drop(columns="scenario").rename(columns={"value": "scenario_value"}), on=keys,
        how="outer", indicator=True, validate="one_to_one")
    if not result["_merge"].eq("both").all():
        raise ValueError("Control and scenario accounts/regions/units do not match")
    result = result.drop(columns="_merge")
    result["difference"] = result.scenario_value - result.control_value
    denominator = result.control_value.replace(0, np.nan)
    result["relative_difference"] = result.difference / denominator
    return result
