from dataclasses import dataclass
from importlib.resources import files
import json
from pathlib import Path
import numpy as np
import pandas as pd

from .builders import COLUMNS, Workbooks, TradeWeights, build_step, sha256
from .cases import Case

RESOURCES = Path(str(files("fulfill_model") / "resources"))


@dataclass
class Plan:
    case: Case
    tables: dict
    rows: pd.DataFrame
    steps: pd.DataFrame
    sources: dict
    diagnostics: dict

    def save(self, directory, *, overwrite=False, excel=False):
        directory = Path(directory)
        if directory.exists() and any(directory.iterdir()) and not overwrite:
            raise FileExistsError(f"Output is not empty: {directory}; choose a new directory or --overwrite")
        directory.mkdir(parents=True, exist_ok=True)
        self.rows.to_csv(directory / "shock_rows.csv", index=False)
        self.steps.to_csv(directory / "steps.csv", index=False)
        for matrix, table in self.tables.items():
            table.to_csv(directory / f"{matrix}.csv", index=False)
        (directory / "case.json").write_text(json.dumps(self.case.to_dict(), indent=2) + "\n")
        (directory / "diagnostics.json").write_text(json.dumps(self.diagnostics, indent=2) + "\n")
        if excel:
            with pd.ExcelWriter(directory / "shock.xlsx") as writer:
                for matrix, table in self.tables.items():
                    table.to_excel(writer, sheet_name=matrix, index=False)
        manifest = dict(schema_version=1, case=self.case.to_dict(), sources=self.sources,
                        meaning="Ordered MARIO 0.3.5 coefficient/demand instructions; not model results",
                        outputs={f.name: sha256(f) for f in directory.iterdir() if f.is_file() and f.name != "plan.json"})
        (directory / "plan.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return directory


def _blend(reference, target, strength, matrix):
    """Interpolate instructions, never interpolate the calculated model results."""
    if strength == 1:
        return target.copy()
    if strength == 0:
        return reference.copy()
    keys = COLUMNS[matrix][:-1]
    a, b = reference.set_index(keys), target.set_index(keys)
    if a.index.has_duplicates or b.index.has_duplicates or set(a.index) != set(b.index):
        raise ValueError("Partial adoption requires matching instruction selectors; input changes cannot silently alter coverage")
    b = b.loc[a.index].copy()
    b["reference_value"] = a.value
    b["target_value"] = b.value
    b["reference_input_cell"] = a.input_cell
    b["reference_input_value"] = a.input_value
    b["value"] = a.value + strength * (b.value - a.value)
    b["transformation"] = "reference_instruction + adoption * (target_instruction - reference_instruction)"
    return b.reset_index()


def build_plan(case=None, *, inputs="Data/Files for shocks", trade=None, books=None):
    case = case or Case()
    if not isinstance(case, Case):
        raise TypeError("case must be a Case")
    recipe = json.loads((RESOURCES / "recipe.json").read_text())
    if trade is None:
        context = json.loads((RESOURCES / "paper_context.json").read_text())
        path = RESOURCES / "paper_trade_weights.csv"
        if sha256(path) != context["trade_weights_sha256"]:
            raise ValueError("Paper trade context checksum mismatch")
        trade = TradeWeights(pd.read_csv(path, float_precision="round_trip"))
        context_source = dict(kind="published_database", **context)
    else:
        context_source = dict(kind="user_supplied_trade_weights", sha256=_frame_hash(trade.frame))
    books = books or Workbooks(inputs)
    frames, summaries = [], []
    for step in sorted(recipe["steps"], key=lambda item: item["order"]):
        measure = step["measure"]
        strength = case.strength(measure) if measure else 1.0
        sheets = step["sheets"][case.background]
        reference_sheet = sheets["0"]
        target_sheet = sheets[measure] if measure else reference_sheet
        selected_sheet = target_sheet if strength else reference_sheet
        rows = build_step(step, selected_sheet, case.year, books, trade, case.background)
        if 0 < strength < 1:
            reference = build_step(step, reference_sheet, case.year, books, trade, case.background)
            rows = _blend(reference, rows, strength, step["matrix"])
        rows = rows.assign(step=step["id"], order=step["order"], matrix=step["matrix"],
                           archetype=step["archetype"], adoption=strength)
        frames.append(rows)
        summaries.append(dict(step=step["id"], order=step["order"], matrix=step["matrix"],
                              archetype=step["archetype"], measure=measure or "background",
                              adoption=strength, input_file=rows.input_file.iloc[0],
                              source_mode="published-instructions" if rows.input_file.iloc[0].startswith("published-backgrounds/") else "raw-workbook",
                              reference_sheet=reference_sheet, selected_sheet=(str(case.year) if step["archetype"] == "electricity_mix" else selected_sheet),
                              rows=len(rows)))
    # These household purchases are already represented by meals, car mobility
    # and housing services. Remove them last to avoid counting them twice.
    cleanup = pd.DataFrame([dict(zip(COLUMNS["Y"], ["all", "Commodity", "Involved commodities", "Involved regions",
                                                      "Households final consumption", "Update", 0.0]),
                                step="remove_replaced_household_purchases", order=18, matrix="Y",
                                archetype="remove_replaced_demand", adoption=1.0,
                                transformation="remove purchases represented in service activities")])
    frames.append(cleanup)
    summaries.append(dict(step="remove_replaced_household_purchases", order=18, matrix="Y",
                          archetype="remove_replaced_demand", measure="background", adoption=1.0, rows=1))
    rows = pd.concat(frames, ignore_index=True)
    tables = {key: rows.loc[rows.matrix == key, columns].reset_index(drop=True) for key, columns in COLUMNS.items()}
    for matrix, table in tables.items():
        if table.isna().any().any() or not np.isfinite(table.value).all():
            raise ValueError(f"Invalid {matrix} instructions")
    mix_rows = rows[rows.archetype.isin(["supply_mix", "electricity_mix"])]
    totals = mix_rows.groupby(["step", "column region", "column sector"], sort=False).value.sum()
    if (totals <= 0).any():
        raise ValueError("A supply mix has zero or negative total")
    diagnostics = dict(supply_mix_totals=[dict(step=k[0], region=k[1], commodity=k[2], total=float(v)) for k, v in totals.items()],
                       max_mix_deviation_from_one=float((totals - 1).abs().max()),
                       no_baseline_market=trade.frame.loc[trade.frame.basis == "no_baseline_market", ["commodity", "consumer"]].to_dict("records"),
                       negative_origin_weights=int((trade.frame.share < 0).sum()),
                       normalization="Original rounded workbook shares are preserved; not automatically normalized",
                       adoption="Linear interpolation of each affected instruction toward the selected measure's target, at the same background/year. Not a fitted adoption model.")
    sources = dict(workbooks={name: books.hashes[name] for name in sorted(set(rows.input_file.dropna()) | ({"cons_var_Full.xlsx"} if "population_file" in rows else set()))},
                   recipe_sha256=sha256(RESOURCES / "recipe.json"), trade_context=context_source)
    return Plan(case, tables, rows, pd.DataFrame(summaries), sources, diagnostics)


def _frame_hash(frame):
    import hashlib
    return hashlib.sha256(frame.to_csv(index=False, float_format="%.17g").encode()).hexdigest()


def frozen_plan(case, reference="Shocks/filled_files"):
    """Use the exact historical workbook, including its known inconsistencies.

    This entry point preserves the paper artifacts; it never silently patches a
    composable recipe to match an inconsistent historical instruction.
    """
    measure = "All" if set(case.measures) == set("DSMPFB") else (case.measures[0] if len(case.measures) == 1 else "0" if not case.measures else None)
    if measure is None or case.adoption:
        raise ValueError("Frozen paper workbooks only support the original single/All/0 presets at full adoption")
    identifier = f"{case.background}_{measure}_{case.year}"
    path = Path(reference) / f"{identifier}.xlsx"
    tables = pd.read_excel(path, sheet_name=list(COLUMNS))
    frames = []
    for matrix, columns in COLUMNS.items():
        table = tables[matrix]
        if table.columns.tolist() != columns or table.isna().any().any() or not np.isfinite(table.value).all():
            raise ValueError(f"Invalid historical {matrix} sheet: {path}")
        frames.append(table.assign(matrix=matrix, step="frozen_paper_instructions", order=0,
                                   archetype="historical_workbook", input_file=path.name,
                                   input_cell=[f"'{matrix}'!{chr(64+len(columns))}{i+2}" for i in range(len(table))],
                                   transformation="unchanged historical instruction"))
    rows = pd.concat(frames, ignore_index=True)
    summaries = pd.DataFrame([dict(step="frozen_paper_instructions", matrix=m, rows=len(t)) for m,t in tables.items()])
    return Plan(case, tables, rows, summaries, dict(frozen_workbook={path.name:sha256(path)}),
                dict(profile="Frozen paper workbook. Includes historical duplicate Updates and any inconsistencies documented in docs/verification.md."))
