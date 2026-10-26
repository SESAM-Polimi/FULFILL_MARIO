# Python API

```python
from fulfill_model import Case, build_plan
from fulfill_model.data import ensure_data

ensure_data('Data', groups=('shocks',))
case = Case(background='NZE', year=2050, measures=('D', 'F'),
            adoption={'F': 0.5}, name='my-sufficiency-case')
plan = build_plan(case)
plan.steps
plan.rows                         # instructions with source/transformation fields
plan.tables['Y']                   # exact ordered MARIO shock table
plan.save('Outputs/plans/my-case')
```

Run the full model, then its control, or reverse the order. The result must be
compared with a control at the same year/background:

```python
from fulfill_model.runtime import load_database, run_plan, compare_accounts

ensure_data('Data')
db = load_database('Data', air_transport_extra=True)
control_plan = build_plan(Case.paper(case.background, '0', case.year))
control = run_plan(db, control_plan, 'Outputs/runs/my-case/control')
scenario = run_plan(db, plan, 'Outputs/runs/my-case/scenario')
comparison = compare_accounts(control, scenario)
```

`run_plan` accepts only this pinned model runtime and does not retain the solved
scenario unless `keep_scenario=True`. Reusing a scenario name already present in
the database fails; the baseline is never overwritten.

For the exact historical XLSX instructions:

```python
from fulfill_model.planning import frozen_plan

historical = frozen_plan(Case.paper('BAU', 'D', 2050), 'Shocks/filled_files')
```

The name `Case.paper` selects the original background/measure/year codes.
`build_plan(Case.paper(...))` compiles the declared recipe; **only `frozen_plan`
loads the unchanged historical file**. This distinction matters for the 24
documented BAU cases.

`TradeWeights.from_database(db, commodities)` is available for developers
preparing a new, matching database context. The bundled context is derived from
the published prepared SUT and covers the nine required commodities in EU27
consumer regions. It is not a generic global trade model.
