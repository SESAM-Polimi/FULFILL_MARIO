# Verification and known differences

## Shock instructions

`tools/verify_paper_shocks.py` checks all 3 backgrounds × 8 measure selections ×
8 years against the 192 version-controlled workbooks. It checks selectors and
numeric values, after removing only identical historical `Update` duplicates.
The tolerance is rtol=1e-12, atol=1e-12 to accommodate Excel/CSV serialization.

**168 cases match the declared recipe.** The remaining **24 cases** are
BAU × {D, P, F, B} × {2025, 2030, 2035, 2040, 2045, 2050}. Their historical
files differ in `car-eff`, `car-emi` and `m2pc`, adding car/housing assumptions
beyond the declared single-measure selection. This difference is preserved in
`reproduce`/`--frozen`; the composable recipe does not import those extra changes.
The machine-readable audit is `verification/shock-parity.json`.

Each historical z table also includes 71 duplicate Update rows, from the old
generator retaining a previous block when no origin market exists. The new
recipe omits those repeated writes. The audit verifies there are no conflicting
duplicate selectors; it does not drop arbitrary percentage operations.

## Full model

Both new notebooks executed from a wheel installed in a fresh isolated
environment. The full notebook calculated NZE_0_2050 and NZE_All_2050 with the
extra aviation row enabled, using the public inputs and notebook 1's public
formula. Their solves took 122.8 and 115.1 seconds. Outputs retain explicit
production-account boundaries; no complete figure-pipeline reproduction is
claimed.

Private reference exports and recovered archival tables remain local. The
public package includes only already-published inputs and background workbooks.

The 5,523-row trade context regenerates byte-for-byte from the public database.
The live downloader test resumed at byte 131,072 with HTTP 206, verified all 16
shock workbooks and then reused them offline; see `verification/download-live.json`.

The final public-input integration check compares BAU_All_2050 from the explicit
recipe with the unchanged published BAU_All_2050 workbook. Its report is
`verification/full-model.json`. All 3182 E/EY/V account-region totals matched
within the declared tolerance (maximum relative difference 2.5914062179549534e-08).
The two solves took 120.7 and 126.0 seconds. Dependency versions are recorded in
`verification/validated-environment.txt`.

## Automated checks

The tests cover parameter rejection, paired effects, adoption endpoints and
midpoints, provenance, population/origin transformations, the public BAU adapter,
output protection, resumable checked downloads and a native MARIO SUT solve
that preserves its baseline. CI also checks the full shock audit and executes
the lightweight exploration notebook. The full SUT solve is a recorded local
integration check, not a CI job or a synthetic test dressed as a paper result.

## Remaining scientific/migration work

* No 192-case rerun or regeneration of every paper figure is claimed.
* The ready-made ZIP and reconstructed aviation-account variant remain explicit.
* Negative origin weights, uncovered natural-gas markets and non-unit original
  supply mixes are diagnosed, not silently normalized or repaired.
* The raw database-building notebook uses an unreleased historical inventory
  API. A current-MARIO database-preparation migration remains separate.
* Scenario adoption interpolation is a new exploratory control, not an adoption
  process calibrated in the paper.
