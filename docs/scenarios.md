# Scenarios and controls

The model has three independent choices: background, year and sufficiency
measures. The `0` case includes the background's demographic, consumption,
technology and efficiency assumptions; it is not a stationary 2011 model.
Compare a measure with `0` at the same background/year.

The original codes are preserved. In particular, `M` is car downsizing through
fuel economy and tailpipe emissions, not a generic mobility toggle; `B` changes
car kilometres through increased cycling. `P` applies both washing-machine
purchases and washing electricity changes.

`Case` composes the measure-specific blocks in the paper's fixed order.
Background requirements and the final cleanup remain present in every case.
An empty `measures` list selects the background-only case. No demand-rebound,
income-reallocation, investment, price, behavioural feedback or additional
cycling infrastructure is inferred beyond the original input assumptions.

## Adoption

For each affected instruction, with reference `b` and full-measure target `t`:

```
instruction = b + adoption * (t - b)
```

Adoption is finite and between zero and one; it may only refer to selected
measures. Zero gives the same background-only instructions, one gives the
full-measure recipe. Partial adoption requires identical instruction selectors
at both endpoints; changing coverage fails instead of inventing a missing
origin or a value. Model results must then be solved and are not interpolated.

`Percentage` is a fractional change (−0.2 means multiply by 0.8), `Update`
replaces a coefficient/demand value, and `Absolute` adds a signed quantity.
Washing-machine sheets are **additive deltas** after population scaling;
interpreting them as replacement demands would change the model.

## Custom assumptions

Copy `Data/Files for shocks` to a new directory, retain sheet names and labels,
edit the numerical assumptions, and pass `--inputs /path/to/copy`.
The existing workbook unit conventions are retained. Values are already
converted for the hybrid database; the program does not infer new conversions
from free-text unit labels.

Five BAU sheets are missing from the published files. Unchanged public workbooks
can use the corresponding published BAU_0 instructions. A modified workbook
missing one of those sheets fails: add the sheet yourself rather than inheriting
an unrelated fallback. The plan names the published source cells explicitly.

To change database regions, sectors or technology definitions, a matching trade
context and a separately validated database preparation are required. `--inputs`
changes assumptions; it does not turn this model into a parser for an arbitrary
IO database.

## Grids

```bash
fulfill batch --backgrounds REF NZE --measures 0 D F All --years 2030 2050 \
  --air-transport-extra --output Outputs/runs/selected-grid
```

This selects 16 cases. Each starts from the same 2011 prepared baseline with
its own year/background instructions. Cases do not accumulate previous years'
shocks. A solved scenario is removed from memory after export.

Existing outputs are protected. Choose a new destination, use `--overwrite`
intentionally, or use `--resume` to skip completed cases after checking the
configuration, source hashes, code hashes and saved output hashes.
