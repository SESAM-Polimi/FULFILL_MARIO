"""Opt-in full SUT comparison: composable BAU_All_2050 vs its published workbook."""
import argparse
import json
from pathlib import Path
import numpy as np
from fulfill_model import Case, build_plan
from fulfill_model.builders import sha256
from fulfill_model.data import ensure_data
from fulfill_model.planning import frozen_plan
from fulfill_model.runtime import load_database, run_plan, compare_accounts

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--data',type=Path,default=Path('Data'))
parser.add_argument('--reference',type=Path,default=Path('Shocks/filled_files'))
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--report',type=Path,default=Path('verification/full-model.json'))
parser.add_argument('--offline',action='store_true')
args=parser.parse_args()
if args.output.exists() and any(args.output.iterdir()):
    raise FileExistsError('Choose a new --output directory')
ensure_data(args.data,offline=args.offline)
case=Case.paper('BAU','All',2050)
recipe=build_plan(case,inputs=args.data/'Files for shocks')
frozen=frozen_plan(case,args.reference)
db=load_database(args.data,air_transport_extra=True)
a=run_plan(db,recipe,args.output/'recipe')
b=run_plan(db,frozen,args.output/'published-workbook')
comparison=compare_accounts(b,a)
assert np.allclose(comparison.scenario_value,comparison.control_value,rtol=1e-7,atol=1e-6)
comparison.to_csv(args.output/'comparison.csv',index=False)
relative=(comparison.difference.abs()/comparison.control_value.abs().replace(0,np.nan))
runs=[json.loads((args.output/p/'run.json').read_text()) for p in ['recipe','published-workbook']]
report=dict(validation_date='2026-10-26',case=case.to_dict(),scope='Full 43-region SUT, composed recipe vs unchanged already-public BAU_All_2050 workbook; E/EY/V account totals',
            source_workbook='BAU_All_2050.xlsx',source_sha256=sha256(args.reference/'BAU_All_2050.xlsx'),
            account_region_totals=len(comparison),max_abs_difference_native_units=float(comparison.difference.abs().max()),
            max_relative_difference=float(relative.max()),tolerance=dict(rtol=1e-7,atol=1e-6),
            solve_seconds=[m['solve_seconds'] for m in runs],air_transport_extra=True,
            engine=runs[0]['engine'],numpy=runs[0]['numpy'],pandas=runs[0]['pandas'],executed_code=runs[0]['code'],
            output_hashes_verified=all(sha256(args.output/folder/name)==digest for folder,run in zip(['recipe','published-workbook'],runs) for name,digest in run['outputs'].items()))
args.report.parent.mkdir(parents=True,exist_ok=True)
args.report.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
