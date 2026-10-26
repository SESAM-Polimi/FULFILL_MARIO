import copy
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest

from fulfill_model.runtime import clusters, compare_accounts


def test_comparison_keeps_accounts_units_and_zero_denominators():
    control=pd.DataFrame([dict(scenario="control",matrix="E",account="CO2",region="IT",value=10,unit="tonnes",boundary="production region"),
                          dict(scenario="control",matrix="E",account="CH4",region="IT",value=0,unit="tonnes",boundary="production region")])
    scenario=control.copy();scenario["scenario"]="custom";scenario["value"]=[8,1]
    result=compare_accounts(control,scenario).set_index("account")
    assert result.loc["CO2","difference"] == -2
    assert result.loc["CO2","relative_difference"] == -.2
    assert np.isnan(result.loc["CH4","relative_difference"])


def test_native_mario_adapter_solves_and_preserves_baseline(tmp_path, monkeypatch):
    mario = pytest.importorskip("mario")
    from fulfill_model import runtime, Case
    from fulfill_model.builders import COLUMNS
    from fulfill_model.planning import Plan
    db = mario.load_test("SUT")
    original = db.Z.copy()
    tables = {
        "z": pd.DataFrame([["Italy", "Commodity", "Mining", "Italy", "Activity", "Manufacturing", "Percentage", -.1]], columns=COLUMNS["z"]),
        "Y": pd.DataFrame([["Italy", "Commodity", "Transport", "Italy", "Final Demand", "Percentage", -.2]], columns=COLUMNS["Y"]),
        "e": pd.DataFrame([["None", "Italy", "Activity", "Transport", "Update", 1.0]], columns=COLUMNS["e"]),
    }
    plan = Plan(Case(name="native-contract"), tables, pd.concat([d.assign(matrix=m) for m,d in tables.items()]), pd.DataFrame(), {}, {})
    monkeypatch.setattr(runtime, "clusters", lambda db: {})
    results = runtime.run_plan(db, plan, tmp_path / "native")
    assert not results.empty
    assert np.isfinite(results.value).all()
    pd.testing.assert_frame_equal(db.Z, original)
    assert "native-contract" not in db.matrices
    assert (tmp_path / "native/run.json").is_file()
    from fulfill_model.cli import _complete
    assert _complete(tmp_path / "native", plan, False)
    (tmp_path / "native/accounts.csv").write_text("tampered")
    with pytest.raises(ValueError, match="modified"):
        _complete(tmp_path / "native", plan, False)


def test_comparison_rejects_missing_accounts():
    rows = pd.DataFrame([dict(scenario="a",matrix="E",account="CO2",region="IT",value=1,unit="t",boundary="production region")])
    with pytest.raises(ValueError, match="do not match"):
        compare_accounts(rows, rows.iloc[:0])
