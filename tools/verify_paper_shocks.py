"""Audit the declared recipe against all historical files; preserve known differences."""
import argparse
from collections import Counter
import itertools
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd
from fulfill_model import Case, build_plan
from fulfill_model.builders import Workbooks
from fulfill_model.cases import BACKGROUNDS, MEASURES, YEARS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=Path('Data/Files for shocks'))
    parser.add_argument('--reference', type=Path, default=Path('Shocks/filled_files'))
    parser.add_argument('--report', type=Path, default=Path('verification/shock-parity.json'))
    args = parser.parse_args()
    books = Workbooks(args.inputs)
    start = time.perf_counter()
    maxima, duplicates, passed, differences = {}, Counter(), [], []
    for background, measure, year in itertools.product(BACKGROUNDS, ['0', 'All', *MEASURES], YEARS):
        case = Case.paper(background, measure, year)
        plan = build_plan(case, books=books)
        reference = pd.read_excel(args.reference / f'{case.identifier}.xlsx', sheet_name=['z', 'Y', 'e'])
        matches = True
        for matrix, got in plan.tables.items():
            want = reference[matrix]
            repeated = want.duplicated()
            assert want.loc[repeated, 'type'].eq('Update').all(), (case.identifier, 'unexpected duplicate operation')
            keys = list(got.columns[:-1])
            actual = got.drop_duplicates().set_index(keys)
            expected = want.drop_duplicates().set_index(keys)
            assert not actual.index.has_duplicates and not expected.index.has_duplicates, (case.identifier, matrix, 'conflicting selectors')
            assert actual.index.equals(expected.index), (case.identifier, matrix, 'coverage/order differs')
            delta = (actual.value - expected.value).abs()
            bad = ~np.isclose(actual.value, expected.value, rtol=1e-12, atol=1e-12)
            if bad.any():
                matches = False
                bad_keys = set(actual.index[bad])
                rows = plan.rows[plan.rows.matrix == matrix]
                changed = rows[rows.apply(lambda r: tuple(r[k] for k in keys) in bad_keys, axis=1)]
                differences.append(dict(case=case.identifier, matrix=matrix, rows=int(bad.sum()),
                                        steps=changed.step.unique().tolist(), max_abs_difference=float(delta.max())))
            maxima[matrix] = max(maxima.get(matrix, 0), float(delta.max()))
            duplicates[matrix] += int(repeated.sum())
        if matches:
            passed.append(case.identifier)
    expected_cases = {f'BAU_{m}_{y}' for m in ['D', 'P', 'F', 'B'] for y in YEARS[2:]}
    actual_cases = {r['case'] for r in differences}
    assert actual_cases == expected_cases, f'Historical difference set changed: {actual_cases ^ expected_cases}'
    assert all(set(row['steps']) <= {'car-eff', 'car-emi', 'm2pc'} for row in differences)
    report = dict(scenarios_checked=192, scenarios_matching=len(passed),
                  tolerance=dict(rtol=1e-12, atol=1e-12), max_abs_difference=maxima,
                  legacy_duplicate_update_rows=dict(duplicates), seconds=time.perf_counter()-start,
                  matching_cases=passed, mismatches=differences,
                  comparison='Equal ordered selectors and numeric instructions after removing identical Update duplicates; 24 known BAU differences preserved by frozen mode.')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(f'192 cases audited; {len(passed)} match; {len(actual_cases)} known BAU differences. No unexpected differences.')
    print(f'Report: {args.report}')


if __name__ == '__main__':
    main()
