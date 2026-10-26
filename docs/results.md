# Result definitions

| File | Meaning |
| --- | --- |
| `case.json` | Selected background, year, measures and adoption |
| `steps.csv` | Ordered blocks, selected source sheets and row counts |
| `shock_rows.csv` | Ordered instructions with source cells, multipliers and origin weights |
| `z.csv`, `Y.csv`, `e.csv` | Tables actually sent to MARIO |
| `diagnostics.json` | Original mix totals, signed origin weights and uncovered markets |
| `plan.json` | Source and exported-plan hashes |
| `accounts.csv` | `E`, `EY`, `V`, summed by region, retaining each original account and unit |
| `production.csv` | `X`, retaining region, Activity/Commodity, sector and unit |
| `run.json` | Engine versions, timings, aviation-account variant, code and output hashes |
| `comparison.csv` | Scenario minus same-year/background control, by matching account and region |

The full SUT retains 43 regions and 16,082 activity/commodity entries.
`E` locates emissions/resources/employment in the **production region**;
`EY` represents direct final-demand extensions. These boundaries must not be
labelled as consumption footprints. Value-added components remain separate in
`V`; employment categories retain their original units and are not added to
other satellite accounts. Production quantities mix physical and monetary units
and must not be summed across sectors indiscriminately.

`relative_difference` is `(scenario - control) / control`. It is blank when the
control is zero. Comparisons reject different accounts, region coverage or
units rather than silently dropping unmatched rows.

The original notebook exports also include `F`, `f` and detailed mappings for
the paper's figure pipeline. Those require additional footprint calculations
and aggregation choices. This quick-run export does not claim to reproduce
that complete post-processing. Use the historical notebooks and published
extended results for that layer; see the reproduction guide's limitations.
