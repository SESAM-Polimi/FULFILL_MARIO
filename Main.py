#%% Importing packages
import mario
import pandas as pd
import os
import json
import time

sN = slice(None)
user = 'WS' # <--- change this to your own user name (see Paths.json)
with open('Paths.json', 'r') as file:
    paths = json.load(file)[user]

Out_Db = 'Full Scale' # Can be "Conceptual" or "Full Scale"
db = Out_Db[:4]

#%% Importing Hybrid Exiobase 3.3.18: https://zenodo.org/records/10148587
world = mario.parse_from_txt(paths[f'{Out_Db} FULFILL']+'\\flows', 'SUT', 'flows',name='world')
meal_act = world.search('Activity','meal')
mob_act = world.search('Activity','car')
heat_act = world.search('Activity','heating') + ['Solar thermal system','Heat pump system']

#%% Defining scemarios (combination of scenarios and years)

# Inputs
background = ['REF'] # Reference: REF - Net Zero Emissions: NZE
measure = ['0', 'D'] # No sufficiency: 0 - Diets: D - Sharing spaces: S - Moderate car sizing: M
years = ['2011','2040'] # 5 year steps from 2020 to 2050 (pass list of strings)

# Scenario definition
scenario = [b + '_' + m for m in measure for b in background]
scemario = [s + '_' + str(y) for s in scenario for y in years]

#%% Preparing shock calculation
inv_commodities = ['Products of meat cattle','Products of meat pigs','Products of meat poultry',
                   'Dairy products','Fish products','Vegetables; fruit; nuts','Food products nec',
                   'products of Vegetable oils and fats','Beverages','Sugar','Liquid fuels',
                   'Liquefied Petroleum Gases (LPG)','Natural gas and services related to natural gas extraction; excluding surveying',
                   'Chemicals nec','Electricity']

inv_regions = {'Full Scale':['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR', 'HR', 'HU', 'IE', 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK', 'IT'],
               'Conceptual': ['EU', 'Italy']}


# Defining the clusters
clusters = {
'Commodity':{
    'all':world.get_index('Commodity'),
    'Involved commodities': inv_commodities,
    },
'Activity':{
    'all':world.get_index('Activity'),
    },
'Region':{
    'all':world.get_index('Region'),
    'Involved regions': inv_regions[Out_Db],
    },
'Consumption category':{'all':world.get_index('Consumption category')},
}

# Structuring the export of the results
U_cols = ['Region_from','drop','Commodity','Activity', 'drop','Region_to']
S_cols = ['Region_from','drop','Activity','Commodity', 'drop','Region_to']
Y_cols = ['Region_from','drop','Commodity','Consumption category', 'drop','Region_to']
EY_cols = ['Satellite account','Consumption category','drop','Region_to']
E_cols = ['Satellite account','Activity','drop','Region_to']
F_cols = ['Satellite account','Commodity','drop','Region_to']
V_cols = ['Factor of production','Activity','drop','Region_to']
X_cols = ['Region_from','drop','Activity']
Q_cols = ['Region_from','drop','Commodity']

Res_map = {
        # 'U': {'col_names':U_cols, 'exp_name': 'U'},
        # 'u': {'col_names':U_cols, 'exp_name': 'u'},
        # 'S': {'col_names':S_cols, 'exp_name': 'V'},
        # 's': {'col_names':S_cols, 'exp_name': 'v'},
        'V': {'col_names':V_cols, 'exp_name': 'VA'},
        # 'v': {'col_names':V_cols, 'exp_name': 'va'},
        'F': {'col_names':F_cols, 'exp_name': 'R_e'},
        # 'Y': {'col_names':Y_cols, 'exp_name': 'Y'},
        'e': {'col_names':E_cols, 'exp_name': 'rr'},
        'E': {'col_names':E_cols, 'exp_name': 'R'},
        'EY': {'col_names':EY_cols, 'exp_name': 'R_hh'},
        'f': {'col_names':E_cols, 'exp_name': 'r_ee'},
        'Q': {'col_names':Q_cols, 'exp_name': 'Q'},
        'X': {'col_names':X_cols, 'exp_name': 'X'}
        }

#%% Shock calculation and results extraction

# Defining the matrices to be exported
ex_mat = [
    'V',
    'F',
    # 'Y',
    'e',
    'E',
    'EY',
    'f',
    'Q',
    'X'
    ]

# Updating inputs
background = [
    'REF'
    ] # Reference: REF - Net Zero Emissions: NZE
measure = [
    0,
    'D',
    'S',
    'M',
    'P',
    'F',
    'B',
    'All',
    ] 

years = [
    '2011',
    '2020',
    '2025',
    '2030',
    '2035',
    '2040',
    '2045',
    '2050',
    ] # 5 year steps from 2020 to 2050 (pass list of strings)

calc = True
export = True
forget = True

res_agg = pd.read_excel(paths['Sets'], sheet_name=None) # Da finire per aggregare

for y in years:
    for b in background:
        for m in measure:
            
            start = time.time()

            if calc:
                if forget:
                    scemario = 'SCEMARIO'
                else:
                    scemario = f'{b}_{m}_{y}'

                world.shock_calc(
                f"Shocks\{Out_Db}\{b}_{m}_{y}.xlsx",
                z=True,
                Y=True,
                e=True,
                scenario=scemario,
                force_rewrite=True,
                **clusters,
                )

                end = time.time()
                print(f"Scemario {b}_{m}_{y} calculated in {round(end-start, 2)} seconds.")

                # calc_matrices = list(Res_map.keys())
                # calc_matrices.remove('Q')

                # world.calc_all(calc_matrices)
            
            if export:
                for mat in ex_mat:
                    if mat==ex_mat[-1]:    
                        print(mat)              
                    else:
                        print(mat,end=" ")              

                    if not os.path.exists(f"{paths['Results']}\\{Out_Db}\\{Res_map[mat]['exp_name']}"):
                        os.makedirs(f"{paths['Results']}\\{Out_Db}\\{Res_map[mat]['exp_name']}")
                    if mat not in ['X','Q']:
                        data = world.get_data(matrices=[mat], scenarios=[scemario])[scemario][0].stack().stack().stack()
                    else:
                        if mat == 'X':
                            data = world.get_data(matrices=['X'], scenarios=[scemario])[scemario][0].loc[(slice(None),"Activity",slice(None)),:]
                        if mat == 'Q':
                            data = world.get_data(matrices=['X'], scenarios=[scemario])[scemario][0].loc[(slice(None),"Commodity",slice(None)),:]

                    data.index.names = Res_map[mat]['col_names']
                    drop_levels = [i for i, name in enumerate(data.index.names) if name == 'drop']
                    data = data.reset_index(level=drop_levels, drop=True)
                    if mat not in ['X','Q']:
                        data = data.to_frame().reset_index()
                        data = data.rename(columns={0: 'Value'})
                    else:
                        data = data.rename(columns={'production': 'Value'})
                                    
                    # Aggregating the results for visualization
                    if 'Activity' in data.columns:
                        cols_dict = dict(zip(res_agg['_set_ACTIVITIES']['Activity name'], res_agg['_set_ACTIVITIES']['Activity_PBI']))
                        data['Activity'] = data['Activity'].map(cols_dict)
                        data.set_index('Activity', inplace=True, append=True)

                    if 'Commodity' in data.columns:
                        cols_dict = dict(zip(res_agg['_set_COMMODITIES']['Commodity name'], res_agg['_set_COMMODITIES']['Commodity_PBI']))
                        data['Commodity'] = data['Commodity'].map(cols_dict)
                        data.set_index('Commodity', inplace=True, append=True)

                    # if 'Region_from' in data.columns:
                    #     cols_dict = dict(zip(res_agg['_set_REGIONS']['Region code'], res_agg['_set_REGIONS']['Region_PBI']))
                    #     data['Region_from'] = data['Region_from'].map(cols_dict)
                    #     data.set_index('Region_from', inplace=True, append=True)

                    # if 'Region_to' in data.columns:
                    #     cols_dict = dict(zip(res_agg['_set_REGIONS']['Region code'], res_agg['_set_REGIONS']['Region_PBI']))
                    #     data['Region_to'] = data['Region_to'].map(cols_dict)
                    #     data.set_index('Region_to', inplace=True, append=True)
                    
                    data.set_index([col for col in data.columns if col != 'Value'], inplace=True, append=True)
                    data = data.groupby(level=list(range(data.index.nlevels))).sum().reset_index()

                    data['Year'] = y
                    data['Scenario'] = f'{b}_{m}'
                    if mat not in ['X','Q']:
                        data = data.drop('level_0', axis=1)

                    mat_file = f"{paths['Results']}\\{Out_Db}\\{Res_map[mat]['exp_name']}\\{b}_{m}_{y}.txt"
                    data.to_csv(mat_file, index=False, sep='\t')

                    end = time.time()
                    print(f"Scemario {b}_{m}_{y}: {mat} exported in {round(end-start, 2)} seconds.")


print('Finished!')

#%% Merge results
# Checking if the folder exists
results_folder = f"{paths['Results']}\\{Out_Db}\\Merged"
if not os.path.exists(results_folder):
    os.makedirs(results_folder)

for mat, names in Res_map.items():

    if mat not in ['U','S']:

        files = os.listdir(f"{paths['Results']}\\{Out_Db}\\{names['exp_name']}")
        # Placeholder code
        dataframes = []
        for file in files:
            if file.endswith('.txt'):
                file_path = f"{paths['Results']}\\{Out_Db}\\{names['exp_name']}\\{file}"
                df = pd.read_csv(file_path, sep='\t')
                dataframes.append(df)

        merged_df = pd.concat(dataframes, axis=0)
        merged_df.to_csv(f"{results_folder}\\{names['exp_name']}.txt", sep='\t', index=False)
        print(f'{mat} exported ')


#%%