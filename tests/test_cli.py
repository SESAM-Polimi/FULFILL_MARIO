from pathlib import Path
import pandas as pd

from fulfill_model import cli, runtime


def test_reproduce_uses_frozen_file_without_downloading_assumptions(tmp_path, monkeypatch):
    calls = {}
    monkeypatch.setattr(cli, "ensure_data", lambda directory, **kwargs: calls.update(data=kwargs))
    monkeypatch.setattr(runtime, "load_database", lambda *args, **kwargs: object())
    def run(db, plan, directory, **kwargs):
        calls["plan"] = plan
    monkeypatch.setattr(runtime, "run_plan", run)
    root = Path(__file__).resolve().parents[1]
    assert cli.main(["reproduce", "--background", "BAU", "--measure", "D", "--year", "2050",
                     "--no-control", "--reference", str(root / "Shocks/filled_files"),
                     "--output", str(tmp_path / "run")]) == 0
    assert calls["data"]["groups"] == ["database"]
    assert "frozen_workbook" in calls["plan"].sources
    expected = pd.read_excel(root / "Shocks/filled_files/BAU_D_2050.xlsx", sheet_name="Y")
    pd.testing.assert_frame_equal(calls["plan"].tables["Y"], expected)
