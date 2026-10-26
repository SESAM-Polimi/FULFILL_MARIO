# Installation

Use a dedicated Python 3.12 environment. The existing `_environment.yml` is
retained as the historical macOS/ARM environment, not as a portable installer.

```bash
conda create -n fulfill-model python=3.12 pip
conda activate fulfill-model
python -m pip install -e '.[model,notebook]'
python -m ipykernel install --user --name fulfill-model --display-name 'FULFILL model'
```

Or use Python 3.12's `venv`, as shown in the README, and select that environment
as the notebook kernel. Do not share the environment with PV-HLCA, GCAM–MARIO
or a current MARIO development checkout: FULFILL deliberately pins `mariopy==0.3.5`,
`numpy==2.1.1`, `pandas==2.2.3`, `openpyxl==3.1.0`.

`pip install -e .` without extras is enough for planning and inspection.
`[model]` installs the historical solver, `[notebook]` notebook support,
and `[test]` verification tools. The ready-made model needs several GB of memory;
the 16,082 × 16,082 legacy dense matrix is much larger than the data ZIP.

```bash
fulfill download --only shocks       # 1.75 MB: enough for planning
fulfill download                     # about 129.6 MB: also fetch the full SUT
fulfill download --offline           # verify existing files, never fetch
fulfill catalog
```

Downloads resume interrupted transfers and verify published size/MD5 plus
SHA-256 of extracted files. They select only the required ZIP members. Original
EXIOBASE and the 1.8 GB extended-results archive are not downloaded by default.

After the first download, `--offline` works with `plan`, `run`, `reproduce` and
`batch`. A changed input cache fails verification; use a separate copy and
`--inputs` for intentional changes to shock workbooks.

Validation on a fresh environment:

```bash
python -m pip install -e '.[model,test]'
fulfill download --only shocks
python -m pytest -q
python tools/verify_paper_shocks.py
```

The last two commands inspect assumptions and test a tiny native MARIO SUT.
They do not launch the 192-case calculation.
