#%% come calcolare footprint esplosa di ciò che ci interessa

import numpy as np

vet = world.e.loc['Building stones (resource)'].to_frame()
vet_diag = pd.DataFrame(np.diag(vet.values.flatten()), index=vet.index, columns=vet.index)

f_dis = pd.DataFrame(vet_diag.values @ world.w.values, index=vet_diag.index, columns=world.w.columns)