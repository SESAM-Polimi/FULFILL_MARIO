# Data sources and integrity

The downloader pins **Zenodo 15341618, v2.3**, rather than following a moving
“latest” link. [Fixed release](https://doi.org/10.5281/zenodo.15341618).
`resources/data_manifest.json` records published archive sizes/MD5 and SHA-256
of each required extracted member.

| Archive | Download | Use |
| --- | --- | --- |
| Files for shocks.zip | 1,747,256 bytes | Scenario assumptions, default download |
| MARIO database.zip | 127,819,701 bytes | Prepared hybrid SUT, default full-model download |
| Exiobase v3.3.18 - MARIO format.zip | 94,444,465 bytes | Historical raw preparation, manual only |
| Extended results.zip | 1,800,012,551 bytes | Published results, manual only |

The original notebooks point to v2.2 (15308822). All shock-workbook payloads in
v2.2 and v2.3 are byte-identical; ZIP packaging differs. The local extracted
inputs and full prepared database have been checked against the public release.
The downloader checks payloads before extraction and verifies the extracted
files before reusing them.

## Missing BAU inputs and public background instructions

The public shock workbooks omit these sheets required by `Shocks/ShockMap.xlsx`:

| Workbook | Missing sheet |
| --- | --- |
| hs-eff_Full.xlsx | hs-eff BAU |
| hs-eff_Full.xlsx | hs-emi BAU |
| hous_Full.xlsx | hous BAU |
| car-mix_Full.xlsx | car_mix BAU |
| hs-mix_Full.xlsx | hs-mix BAU - clustering |

For these five background blocks the model selects the corresponding rows from
**the already-public BAU_0_<year>.xlsx files in this repository**, pinned to
commit cf8a79bc99d61713ae8ff9b4e864cd3e51cde9ef. The wheel includes only these
eight existing background workbooks. Their checksums and public URLs are in
`resources/public_backgrounds.json`.

The adapter copies the published coefficients directly, retaining the source
workbook/sheet/cell. It does not claim to recover the missing original physical
assumptions. `steps.csv` marks `source_mode=published-instructions` for these
blocks; other blocks continue to read the raw assumptions. Modified workbooks
missing a BAU sheet must provide it explicitly instead of inheriting a fallback.

The authors' private archive was useful for diagnosing the missing sheets, but
its tables and workbook contents are kept local and are not included in this
PR. New users need only the public release and the published repository.

## Derived trade context

`paper_trade_weights.csv` makes planning possible without loading a 16,082-square
matrix. It is derived from the verified full prepared database, not fitted or
fictional data. For each required commodity and EU consumer region, origin
weights follow the original `coeffs_change`: use total final demand by origin;
when its total is zero, use final plus intermediate demand. See the source
matrix hashes and derivation in `paper_context.json` and regenerate with
`tools/build_trade_context.py`.

The underlying net-flow data produce **90 signed origin weights**, and natural
gas has no baseline market in CY/MT. These limitations are recorded in every
composable plan. No clipping, extra supplier or zero-denominator epsilon is
introduced. Where no baseline market exists, the original recipe does not
allocate a requirement. The old generator repeats a previous Update block in
those cases; the new one omits that redundant repetition.

Supply shares are also preserved as supplied. For example, NZE 2050's car mix
totals 1.0292533844 in CY/MT. Diagnostics expose all totals; they are not silently
renormalized. A future strictly conservative mix operation needs an explicit
policy for legacy inputs rather than changing these data behind the scenes.

The public dataset's license is CC BY 4.0, as recorded by Zenodo. The repository
code license remains Apache 2.0. This update does not reassign a blanket license to external data.
