# Historical study and database preparation

The original artifacts are retained byte-for-byte:

1. `1. Database building.ipynb`: raw EXIOBASE parsing, aggregation, additional
   service activities and extra aviation account.
2. `2. Shock building.ipynb`: the original map/function-driven shock generator.
3. `3. Model run.ipynb`: the full study loop and detailed export/aggregation.
4. `_support.py`, `_environment.yml`, `Database modifications/`,
   `Shocks/ShockMap.xlsx`, `Shocks/template.xlsx`, `Outputs/sets.xlsx`, all 192
   saved scenario workbooks.

The [original README](paper-original-readme.md) is retained for provenance.
These notebooks describe how the database and study were prepared; the new
quick start uses the verified ready-made SUT so users can work on scenarios.

## Execute historical instructions

From a repository checkout with the new isolated environment:

```bash
fulfill reproduce --background NZE --measure All --year 2050 \
  --air-transport-extra --output Outputs/runs/paper-example
```

This loads the exact selected workbook and the matching background-only file;
it preserves duplicate Updates and known recipe/file differences. These XLSX
files live in the checkout (`--reference` selects a different directory);
the Python wheel includes the eight BAU_0 background workbooks, not all 192 files.

For all original cases, explicitly request:

```bash
fulfill batch --paper-grid --frozen --air-transport-extra \
  --output Outputs/runs/paper-grid
```

This runs the original instructions on the full prepared SUT, with the new
account/production export. It does **not** regenerate every paper figure or the
original Power BI processing. The historical full export has additional `F/f`
footprint calculations and mappings. The complete scenario grid has not been
rerun during this update; the original eight-hour estimate includes the old
calculation/export pipeline.

## Two database account variants

The ready-made public ZIP contains 32 satellite accounts. The archived study
database contains 33, adding `Air transport extra emissions`. This row exactly
copies fossil CO2 from air transport and is zero for other activities, matching
step 5 of notebook 1. The archived result files include it, and `Outputs/sets.xlsx`
assigns it a characterization factor of one.

`--air-transport-extra` applies that documented operation at load time, without
editing the downloaded database. The run manifest records whether it was
present. Omitting the flag preserves the public ZIP's accounts. Do not compare
total characterized GHG values across these variants without accounting for
the extra row. Other GWP choices remain those of the relevant figure pipeline;
the quick export preserves raw account values and units.

## Limits of rebuilding from raw EXIOBASE

The historical notebook 1 calls `read_add_sectors_excel` and no-argument
`add_sectors`, APIs from the authors' development version that are not in the
released MARIO 0.3.5. It also reads modifications from `Data/Database modifications`,
whereas the version-controlled originals live in `Database modifications`.
The new environment therefore does not promise that executing this notebook
unchanged will rebuild the database from scratch. Porting that preparation to
a current MARIO inventory API needs a separate numerical migration check.

The original notebook 2 cannot rebuild all BAU cases using just the public ZIP;
the new layer uses the corresponding already-public BAU_0 instructions for the
five missing background blocks. It does not publish the private archive sheets.
Notebook 3's optional merge cell references undefined `paths` and `Out_Db`
variables; use the new exported CSVs or repair that historical post-processing
in a separately reviewed change. None of these limitations block running the
verified prepared model or the frozen historical shock files.

For published reference results, download **Extended results.zip** explicitly
from [the fixed release](https://doi.org/10.5281/zenodo.15341618). It is about
1.8 GB and is deliberately outside the automatic quick-start download.
