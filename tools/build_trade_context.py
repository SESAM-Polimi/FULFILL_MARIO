"""Regenerate the small planning context from the full published flow matrices."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import pandas as pd
from fulfill_model.planning import RESOURCES
from fulfill_model.runtime import EU27


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',type=Path,default=Path('Data/MARIO database/flows'))
    parser.add_argument('--output',type=Path,default=RESOURCES)
    args=parser.parse_args()
    recipe=json.loads((RESOURCES/'recipe.json').read_text())
    commodities=[]
    for step in recipe['steps']:
        parameters=step['parameters']
        for commodity in parameters.get('acts_coms',{}).values():
            if commodity not in parameters.get('com_only_domestic',[]) and commodity not in commodities:
                commodities.append(commodity)
    y=pd.read_csv(args.database/'Y.txt',header=[0,1,2],index_col=[0,1,2])
    blocks=[]
    for chunk in pd.read_csv(args.database/'Z.txt',header=[0,1,2],index_col=[0,1,2],chunksize=128):
        selected=chunk.loc[(chunk.index.get_level_values(1)=='Commodity') & chunk.index.get_level_values(2).isin(commodities)]
        if len(selected):
            blocks.append(selected.loc[:,selected.columns.get_level_values(1)=='Activity'].T.groupby(level=0,sort=False).sum().T)
    u=pd.concat(blocks)
    rows=[]
    for commodity in commodities:
        cy=y.loc[(slice(None),slice(None),commodity),:]
        cu=u.loc[(slice(None),slice(None),commodity),:]
        for consumer in sorted(EU27):
            values=cy.loc[:,(consumer,slice(None),slice(None))].sum(axis=1)
            basis='final_demand'
            if values.sum()==0:
                values=values+cu[consumer]
                basis='final_plus_intermediate_demand'
            if values.sum()==0:
                rows.append(dict(commodity=commodity,consumer=consumer,supplier=consumer,share=0.0,basis='no_baseline_market'))
                continue
            for (supplier,_,_),share in (values/values.sum()).items():
                if share!=0:
                    rows.append(dict(commodity=commodity,consumer=consumer,supplier=supplier,share=share,basis=basis))
    args.output.mkdir(parents=True,exist_ok=True)
    frame=pd.DataFrame(rows)
    path=args.output/'paper_trade_weights.csv'
    frame.to_csv(path,index=False,float_format='%.17g')
    digest=lambda path:hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
    manifest=dict(zenodo_record=15341618,database_archive_md5='1f5203990b8647c08ce0215b1303fa40',
                  files={p.name:digest(p) for p in args.database.glob('*.txt')},
                  trade_weights_sha256=digest(path),rows=len(frame),negative_weights=int((frame.share<0).sum()),
                  derivation='Y commodity origin shares by consumer; if household + other final demand is zero, use Y+U. No rounding, clipping or re-normalization beyond division by the observed total.')
    (args.output/'paper_context.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Context rows:',len(frame),'SHA-256:',digest(path))


if __name__=='__main__':
    main()
