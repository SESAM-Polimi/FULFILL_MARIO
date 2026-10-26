import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from fulfill_model import Case, build_plan
from fulfill_model.builders import Workbooks, TradeWeights
from fulfill_model.planning import frozen_plan

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def books():
    path = ROOT / "Data/Files for shocks"
    if not path.exists():
        pytest.skip("Run fulfill download --only shocks for input-based tests")
    return Workbooks(path)


@pytest.mark.parametrize("kwargs", [dict(year=2024), dict(year=2050.0), dict(background="made-up"),
    dict(measures=["D", "D"]), dict(measures=["X"]), dict(measures="D"),
    dict(adoption={"F": -0.1}), dict(adoption={"F": float("nan")}),
    dict(adoption={"F": True}), dict(measures=["D"], adoption={"F": .5})])
def test_invalid_case_is_rejected(kwargs):
    with pytest.raises(ValueError):
        Case(**kwargs)


def test_unknown_json_fields_rejected(tmp_path):
    path = tmp_path / "case.json"
    path.write_text('{"yeer": 2050}')
    with pytest.raises(ValueError, match="Unknown"):
        Case.from_json(path)


def test_case_copies_and_seals_adoption():
    adoption = {"D": .5}
    case = Case(measures=("D",), adoption=adoption)
    adoption["D"] = 2
    assert case.strength("D") == .5
    with pytest.raises(TypeError):
        case.adoption["D"] = 2


def test_composite_only_changes_selected_blocks(books):
    control = build_plan(Case(measures=()), books=books)
    custom = build_plan(Case(measures=("D", "F")), books=books)
    for step in custom.steps.step:
        a = control.rows.loc[control.rows.step == step, "value"].reset_index(drop=True)
        b = custom.rows.loc[custom.rows.step == step, "value"].reset_index(drop=True)
        if step not in ("diet", "flying-less_Y", "flying-less_z"):
            pd.testing.assert_series_equal(a, b)
        else:
            assert not a.equals(b)
    assert custom.steps.order.tolist() == list(range(1, 19))
    assert custom.tables["Y"].iloc[-1]["row sector"] == "Involved commodities"


@pytest.mark.parametrize("measure", list("DSMPFB"))
def test_adoption_interpolates_instructions_and_keeps_endpoints(books, measure):
    no = build_plan(Case(measures=()), books=books)
    yes = build_plan(Case(measures=(measure,)), books=books)
    half = build_plan(Case(measures=(measure,), adoption={measure: .5}), books=books)
    zero = build_plan(Case(measures=(measure,), adoption={measure: 0}), books=books)
    for key in no.tables:
        pd.testing.assert_frame_equal(zero.tables[key], no.tables[key])
        a,b,c = (p.tables[key] for p in (no,yes,half))
        assert a.drop(columns="value").equals(b.drop(columns="value"))
        assert a.drop(columns="value").equals(c.drop(columns="value"))
        np.testing.assert_allclose(c.value, a.value + .5*(b.value-a.value), rtol=1e-14, atol=1e-12)


def test_input_cells_population_and_trade_are_traceable(books):
    plan = build_plan(Case.paper(), books=books)
    demand = plan.rows[(plan.rows.step == "mvkm") & (plan.rows["column region"] == "IT")].iloc[0]
    assert demand.value == demand.input_value * demand.population
    assert demand.input_cell.startswith("'vkm pc B'!")
    fuel = plan.rows[(plan.rows.step == "car-eff") & (plan.rows["column region"] == "IT")].iloc[0]
    assert fuel.value == fuel.input_value * fuel.trade_share
    assert fuel.trade_basis == "final_demand"


def test_supply_mix_diagnostics_keep_original_values(books):
    plan = build_plan(Case.paper(), books=books)
    total = next(r["total"] for r in plan.diagnostics["supply_mix_totals"] if r["step"] == "car-mix" and r["region"] == "CY")
    assert total == pytest.approx(1.0292533844032423)
    assert plan.diagnostics["negative_origin_weights"] == 90
    assert len(plan.diagnostics["no_baseline_market"]) == 2


def test_bau_background_uses_only_named_public_instructions(books):
    plan = build_plan(Case.paper("BAU"), books=books)
    published = [name for name in plan.sources["workbooks"] if name.startswith("published-backgrounds/")]
    assert published == ["published-backgrounds/BAU_0_2050.xlsx"]
    assert plan.steps.source_mode.eq("published-instructions").sum() == 5
    assert plan.tables["z"].shape[0] > 7000


def test_frozen_plan_keeps_original_rows_and_hash():
    plan = frozen_plan(Case.paper("BAU", "D", 2050), ROOT / "Shocks/filled_files")
    expected = pd.read_excel(ROOT / "Shocks/filled_files/BAU_D_2050.xlsx", sheet_name="z")
    pd.testing.assert_frame_equal(plan.tables["z"], expected)
    assert expected.duplicated().sum() == 71


def test_plan_save_is_protected_and_roundtrips(books, tmp_path):
    plan = build_plan(Case.paper(), books=books)
    plan.save(tmp_path / "plan", excel=True)
    with pytest.raises(FileExistsError):
        plan.save(tmp_path / "plan")
    saved = pd.read_excel(tmp_path / "plan/shock.xlsx", sheet_name="Y")
    np.testing.assert_allclose(saved.value, plan.tables["Y"].value)
    manifest = json.loads((tmp_path / "plan/plan.json").read_text())
    assert "shock_rows.csv" in manifest["outputs"]


def test_bad_trade_coverage_is_rejected():
    frame = pd.DataFrame([dict(commodity="fuel", consumer="A", supplier="A", share=.8, basis="final_demand")])
    with pytest.raises(ValueError, match="sum to one"):
        TradeWeights(frame)


def test_custom_workbook_cannot_silently_use_published_bau(books, tmp_path):
    import shutil
    source = books.directory / "hs-eff_Full.xlsx"
    target = tmp_path / source.name
    shutil.copyfile(source, target)
    with target.open("ab") as handle:
        handle.write(b"custom-workbook")
    with pytest.raises(ValueError, match="Custom workbook"):
        custom_books = Workbooks(tmp_path)
        from fulfill_model.builders import build_step
        from fulfill_model.planning import RESOURCES
        step = next(s for s in json.loads((RESOURCES / "recipe.json").read_text())["steps"] if s["id"] == "hs-eff")
        build_step(step, "hs-eff BAU", 2050, custom_books, None, "BAU")
