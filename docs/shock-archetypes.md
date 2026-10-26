# FULFILL as a catalogue of MARIO shock archetypes

FULFILL separates a behavioural choice from the technological representation
of the service that fulfils it. This is broader than replacing supply mixes.
A meal, a vehicle-kilometre, housing space and a washing service provide a useful
intermediate layer between behaviour and individual IO cells.

## Operations found in the implementation

| Meaning | FULFILL examples | Matrix effect | Contract to make explicit |
| --- | --- | --- | --- |
| Scale existing final demand | Consumption growth, household flights | Multiply selected Y by 1 + change | Categories, origins, reference state, order |
| Set total service demand | Number of meals | Replace selected Y with a total | Service unit, population already included, domestic provision |
| Set service demand per person | Car kilometres, housing space | Per-capita driver × population → replacement Y | Driver unit, population year/region, origin rule |
| Add a per-capita demand change | Shared machines and washing electricity | Signed per-capita delta × population → additive Y | Difference vs total; cannot be interpreted as replacement |
| Replace suppliers of a service | Diet, vehicle, heating and electricity mixes | Replace activity shares supplying a commodity (s) | Coverage, share totals, retained suppliers, geography/trade |
| Set technical input requirement | Fuel economy, heating efficiency, housing energy | Replace u using a target requirement and origin weights | Input/output units, trade basis, zero coverage, independent requirements |
| Set direct satellite intensity | Vehicle/heating emissions | Replace selected e coefficients | Account/output unit, consistency with fuel changes |
| Scale intermediate service use | Business/intermediate air transport | Multiply selected u by 1 + change | Consumers included, origins, reference state |
| Replace direct purchases with a service representation | Meals, housing and car mobility | Clear the household purchases now embedded in activities | Required service expansion, affected categories, double-counting prevention |

These are semantic operations. `Update`, `Percentage` and `Absolute` describe
how a number is written into a matrix, but cannot tell a user whether the number
is a total service demand, a per-capita delta or a technology share.

## Compound measures are first-class objects

Some measures require linked operations:

* Car downsizing changes fuel requirements **and** tailpipe intensities. An
  independent emissions toggle could count the same physical change twice or
  leave fuel use and emissions inconsistent.
* Shared washing machines change equipment purchases **and** electricity. One
  measure selects both deltas and uses the same adoption control.
* Reduced aviation touches household Y **and** air transport used by activities.
  “Reduce final demand” alone does not represent the implemented measure.
* The service representations require removing the old household purchases.
  Clearing demand independently of adding service demand would remove needs
  rather than change how they are met.

The model layer introduced here keeps those bundles together and exposes the
ordered primitive instructions. It also makes the reference explicit: partial
adoption moves from the same-year background assumption to the selected target,
not from an arbitrary current mutable matrix state.

## Relationship to update_supply_mixes

`update_supply_mixes` addresses one row of this catalogue. It is a useful
primitive for choosing who supplies a commodity, but it does not specify how
much service people need, how much input a technology needs per service, or
which direct emissions accompany that input.

A service mix and a technical requirement also have different conservation
questions. A normalized supply mix should preserve the chosen total. A reduced
fuel requirement intentionally changes an input total while preserving the
functional output. A demand delta intentionally changes the requested output.
The API should ask for the quantity to preserve rather than apply one generic
normalization rule to every operation.

## Requirements demonstrated by this repository

1. **A plan before execution.** Inspect targeted labels, values, sources, units,
   scope and order before a matrix is modified. Keep the compiled cell changes
   available for debugging and exact reproduction.
2. **Reference-state semantics.** Separate changes relative to baseline, changes
   relative to a projected control and changes relative to a previous operation.
   Percentages and replacements are not generally commutative.
3. **Coverage and balancing policies.** Missing baseline markets, signed net
   flows and incomplete/non-unit mixes need explicit policies. Here the legacy
   values are preserved and diagnosed; a new strict operation should not inherit
   these exceptions implicitly.
4. **Units attached to drivers.** Distinguish MJ/km from km/person, tonnes/person
   from tonnes of added demand, and emissions/service from absolute emissions.
   Population scaling should occur exactly once.
5. **Dependencies and conflicting writes.** Define which operations belong to
   a measure, which service expansion they require, and whether overlapping
   writes are intentional overrides or errors.
6. **Inspectable composite controls.** An adoption parameter should identify
   the assumptions it changes, and the model should be recalculated. It should
   not interpolate final footprints.
7. **A reproducibility profile.** Historical files can remain executable even
   when their assumptions conflict with a clearer recipe. Keep their identity
   and report differences rather than altering published inputs silently.

## Suggested next discussion

Start from two concrete reusable objects: a **service-demand change** (total,
per-capita or additive) and a **technical requirement change** (with a declared
origin-allocation rule). Combine them with supply-mix changes and satellite
intensities in an ordered scenario plan. Use FULFILL's car, housing, diets and
product-sharing cases as acceptance examples before naming a general MARIO API.

This is a design input, not a proposed finalized core API. No MARIO core files
are changed in this PR; migration from the historical full-Z SUT representation
to current native u/s/Yc structures is a separate task.
