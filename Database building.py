#%% Importing packages
import mario
import pandas as pd
import os
import json
from Support import add_new_supply_chains


sN = slice(None)
user = 'WS' # <--- change this to your own user name (see Paths.json)
with open('Paths.json', 'r') as file:
    paths = json.load(file)[user]

Out_Db = 'Full Scale' # Can be "Conceptual" or "Full Scale"

#%% Importing Hybrid Exiobase 3.3.18: https://zenodo.org/records/10148587
world = mario.parse_from_txt(paths['Exiobase']+'\\flows', 'SUT', 'flows')

#%% In case you want to use the conceptual database
# world = mario.parse_from_txt(paths[f'{Out_Db} FULFILL']+f'\\flows', 'SUT', 'flows')

#%% Aggregating Electricities into one, dropping unused satellite accounts and aggregating consumption categories
# world.get_aggregation_excel(r"Aggregations\agg.xlsx")
world_aggr = world.aggregate(f"Aggregations\{Out_Db} aggregation.xlsx", ignore_nan=True, inplace=False)

#%% Export the aggregated database
world_aggr.to_txt(paths[f'{Out_Db} FULFILL'])

#%% Parse the aggregated database
world_aggr = mario.parse_from_txt(paths[f'{Out_Db} FULFILL']+'\\flows', 'SUT', 'flows')

#%% Adding new activities and commodities
paths_new_supply_chains = {
    'Map': paths['Add sectors']+'\\'+Out_Db+'\\'+'Mapping new processes - '+Out_Db+'.xlsx',
    'commodities': paths['Add sectors']+'\\'+Out_Db+'\\'+'Add commodities.xlsx',
    'activities': paths['Add sectors']+'\\'+Out_Db+'\\'+'Add activities.xlsx',
    'values': paths['Add sectors']+'\\'+Out_Db+'\\'+'Add values.xlsx',
    'export_path': paths[f'{Out_Db} FULFILL']
    }

add_new_supply_chains(
    paths = paths_new_supply_chains, 
    main_sheet='Main', 
    world=world_aggr,
    Y_categories = ['Households final consumption'],
    sat_EY=['Carbon dioxide, fossil','CH4','N2O'],
    add_sectors_template=True,
    )

# %% Re-parse the database
world = mario.parse_from_txt(paths[f'{Out_Db} FULFILL']+"/flows", 'SUT', 'flows')

#%% Add extension related to air transport extra emissions
import copy
# E_airtransport = world.E.loc['Carbon dioxide, fossil',:]
E_airtransport = copy.deepcopy(world.E.loc['Carbon dioxide, fossil',:])
all_activities = world.get_index('Activity')
all_activities.remove(world.search('Activity', 'Air transport')[0])

E_airtransport.loc[(slice(None),slice(None),all_activities)] = 0
E_airtransport = E_airtransport.to_frame().T
E_airtransport.index = ['Air transport extra emissions']
units_E = pd.DataFrame(['tonnes'], index=['Air transport extra emissions'], columns=['unit'])

world.add_extensions(io=E_airtransport, matrix='E', units=units_E, inplace=True)

world.E.loc['Carbon dioxide, fossil',:].sum().sum()

#%% Re-export the database
world.to_txt(paths[f'{Out_Db} FULFILL'])

# %%
