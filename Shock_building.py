#%%
import mario
import pandas as pd
import json
from Support import change_market_shares,coeffs_change,change_in_consumption,commodity_demand,eemix,meals_demand,sat_coeffs_change,null_demand,all_coeffs_change

sN = slice(None)
user = 'WS' # <--- change this to your own user name (see Paths.json)
with open('Paths.json', 'r') as file:
    paths = json.load(file)[user]

Out_Db = 'Full Scale' # Can be "Conceptual" or "Full Scale"
ending = Out_Db[:4] # can be Full or Conc
scenario = 'REF' 
year = 2020

#%% Importing database
world = mario.parse_from_txt(paths[f'{Out_Db} FULFILL']+'\\flows', 'SUT', 'flows',name='world')

#%%
other_parameters = {
    'cons_var': {
        'cons_category': ['Households final consumption', 'Other final consumption'],
        'commodity':'all',
    },
    'flying-less_Y': {
        'cons_category': ['Households final consumption'],
        'commodity':'Air transport services (62)',
    },
    'flying-less_z': {
        'commodity':'Air transport services (62)',
        # 'activity':'all',
    },
    'car-eff': {
        'database': world.meta.name,
        'acts_coms': {
            "Diesel and gasoline car":"Liquid fuels",
            "LPG car":"Liquefied Petroleum Gases (LPG)",
            "Methane car":"Natural gas and services related to natural gas extraction; excluding surveying",
            "Hydrogen car":"Chemicals nec",
            "Full electric car":"Electricity",
        }
    },
    'hs-eff': {
        'database': world.meta.name,
        'acts_coms': {
            "Other fossil heating system":"Coal and peat",
            "Solid biomass heating system":"Products of forestry; logging and related services (02)",
            "Heavy fuel oil heating system":"Heavy Fuel Oil",
            "Methane heating system":"Natural gas and services related to natural gas extraction; excluding surveying",
            "Electric heating system":"Electricity",
            "District heating network":"Steam and hot water supply services",
            "Heat pump system":"Electricity",
        }
    },
    'hous': {
        'database': world.meta.name,
        'acts_coms': {
            "Electricity need": 'Electricity',
            "Heating need": 'Heating services',
        },
        'target_act': 'Housing',
        'com_only_domestic':['Heating services'],
    },
    'car-mix': {
        'commodity': 'Car mobility',
    },
    'diet': {
        'commodity': 'Meals',
    },
    'hs-mix': {
        'commodity': 'Heating services',
    },
    'ele-mix': {
        'commodity': 'Electricity',
    },
    'meals_dem': {
        'commodity': 'Meals',
        'cons_category': 'Households final consumption',
    },
    'mvkm': {
        'commodity': 'Car mobility',
        'cons_category': 'Households final consumption',
        'population_path':f"{paths['Support data']}\\{Out_Db}\\cons_var_{ending}.xlsx",
        'shock_type': 'Update',
    },
    'wash-mac': {
        'commodity': 'Machinery and equipment n.e.c. (29)',
        'cons_category': 'Households final consumption',
        'population_path':f"{paths['Support data']}\\{Out_Db}\\cons_var_{ending}.xlsx",
        'shock_type': 'Absolute',
    },
    'wash-ee': {
        'commodity': 'Electricity',
        'cons_category': 'Households final consumption',
        'population_path':f"{paths['Support data']}\\{Out_Db}\\cons_var_{ending}.xlsx",
        'shock_type': 'Absolute',
    },
    'm2pc': {
        'commodity': 'Housing services',
        'cons_category': 'Households final consumption',
        'population_path':f"{paths['Support data']}\\{Out_Db}\\cons_var_{ending}.xlsx",
        'shock_type': 'Update',
    },

}

#%%
def get_shock_file(
        background,
        measure,
        year,
        shockmap,
        Out_Db,
        database,
        other_parameters,
        shock_template,
        ):
    
    shock_set = shockmap.loc[:,(background,measure)].to_frame()
    shock_set.columns = ['sheet_name']
    shock_set.reset_index(inplace=True)

    shock_set.sort_values(by='sorting', inplace=True)
    shock_set.set_index('sorting',inplace=True)

    for i, row in shock_set.iterrows():

        output = row['output']
        function = row['function']
        shock = row['shocks']
        print(background, measure, year, shock)

        sheet_name = row['sheet_name']
        oth_par_list = row['other_parameters'].split(',')
        additional_parameters = ''
        
        if oth_par_list != ['None']:
            for par in oth_par_list:
                value = other_parameters[shock][par]
                if par == 'commodity':
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'meals_dem' and par == 'cons_category':
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'm2pc' and par == 'cons_category' or par == 'commodity' or par == 'shock_type':
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'wash-mac' and par == 'cons_category' or par == 'commodity' or par == 'shock_type':
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'wash-ee' and par == 'cons_category' or par == 'commodity' or par == 'shock_type':
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'mvkm' and par == 'cons_category' or par == 'commodity' or par == 'shock_type':
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'm2pc' and par == 'population_path':
                    additional_parameters += f"{par}=r'{value}',"
                elif shock == 'wash-mac' and par == 'population_path':
                    additional_parameters += f"{par}=r'{value}',"
                elif shock == 'wash-ee' and par == 'population_path':
                    additional_parameters += f"{par}=r'{value}',"
                elif shock == 'mvkm' and par == 'population_path':
                    additional_parameters += f"{par}=r'{value}',"
                elif shock == 'hous' and par == 'target_act':
                    additional_parameters += f"{par}='{value}',"
                else:
                    additional_parameters += f"{par}={value},"
        
        if function == 'eemix':
            excel_path = paths['Support data']+f"\\{Out_Db}\\{row['excel_path']}{background}_{Out_Db[:4]}.xlsx"
            sheet_name = str(year)
        else:
            excel_path = paths['Support data']+f"\\{Out_Db}\\{row['excel_path']}_{Out_Db[:4]}.xlsx"


        expression = f"{function}(excel_path=r'{excel_path}',sheet_name='{sheet_name}',year={year}"
        expression += f",{additional_parameters})"


        if output == 'z':
            shock_template['z'] = pd.concat([shock_template['z'],eval(expression)],axis=0)
        if output == 'Y':
            shock_template['Y'] = pd.concat([shock_template['Y'],eval(expression)],axis=0)
        if output == 'e':
            shock_template['e'] = pd.concat([shock_template['e'],eval(expression)],axis=0)

    Y_null = null_demand(
        cons_category='Households final consumption',
        commodities='Involved commodities',
        regions='Involved regions',
        )

    shock_template['Y'] = pd.concat([shock_template['Y'],Y_null],axis=0)

    return shock_template

#%%
measure = [
    'All',
    'F',
    'D',
    'S',
    'M',
    'P',
    'F',
    'B',
    0,
    ] 
background = [
    'REF',
    'NZE',
    ] # Reference: REF - Net Zero Emissions: NZE
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

shockmap = pd.read_excel(paths['Shocks']+"\\ShockMap.xlsx",index_col=[0,1,2,3,4,5],header=[0,1])
world.get_shock_excel(paths['Shocks']+"\\template.xlsx")

for b in background:
    for m in measure:
        for y in years:

            template = pd.read_excel(paths['Shocks']+"\\template.xlsx",sheet_name=None)

            shock_file = get_shock_file(
                b,
                m,
                y,
                shockmap,
                Out_Db,
                world,
                other_parameters,
                template
                )

            with pd.ExcelWriter(paths['Shocks']+f"\\{Out_Db}\\{b}_{m}_{y}.xlsx") as writer:
                for key in shock_file.keys():
                    shock_file[key].to_excel(writer, sheet_name=key,index=False)

#%%  diet mix
# measure='D'
# z_diet = change_market_shares(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\diet_{ending}.xlsx",
#     sheet_name=f'diet {measure}',
#     year=year,
#     commodity='Meals',
#     )

# #%%  cars mix
# z_cars = change_market_shares(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\car-mix_{ending}.xlsx",
#     sheet_name=f'car_mix {scenario}',
#     year=year,
#     commodity='Car mobility',
#     )

# #%%  hs mix
# z_hs = change_market_shares(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\hs-mix_{ending}.xlsx",
#     sheet_name=f'hs-mix {scenario}',
#     year=year,
#     commodity='Heating services',
#     )

# #%% fuel economies
# measure = 'M'
# cars_fuels ={
#     "Diesel and gasoline car":"Liquid fuels",
#     "LPG car":"Liquefied Petroleum Gases (LPG)",
#     "Methane car":"Natural gas and services related to natural gas extraction; excluding surveying",
#     "Hydrogen car":"Chemicals nec",
#     "Full electric car":"Electricity",
#     }

# z_cars_fuels = coeffs_change(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\car-eff_{ending}.xlsx",
#     year=year,
#     sheet_name = f"car-eff {measure} - clustering",
#     database=world,
#     acts_coms=cars_fuels,
#     )

# #%% heating systems
# hs_fuels ={
#     "Other fossil heating system":"Coal and peat",
#     "Solid biomass heating system":"Products of forestry; logging and related services (02)",
#     "Heavy fuel oil heating system":"Heavy Fuel Oil",
#     "Methane heating system":"Natural gas and services related to natural gas extraction; excluding surveying",
#     "Electric heating system":"Electricity",
#     "District heating network":"Steam and hot water supply services",
#     "Heat pump system":"Electricity",
#     }

# z_hs_fuels = coeffs_change(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\hs-eff_{ending}.xlsx",
#     year=year,
#     sheet_name = f"hs-eff",
#     database=world,
#     acts_coms=hs_fuels,
#     )

# #%% house needs
# needs_fuels ={
#     "Electricity need": 'Electricity',
#     "Heating need": 'Heating services',
#     }

# z_house_needs = coeffs_change(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\hous_{ending}.xlsx",
#     year=year,
#     sheet_name = f"hous",
#     database=world,
#     acts_coms=needs_fuels,
#     target_act='Housing',
#     com_only_domestic=['Heating services']
#     )

# #%% heating systems
# e_hs_fuels = sat_coeffs_change(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\hs-eff_{ending}.xlsx",
#     year=year,
#     sheet_name = f"hs-emi",
#     )

# #%% change in consumption
# # NOTE: clusters 'all' for commodities and regions to be defined when calc shock
# Y_cons = change_in_consumption(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\cons_var_{ending}.xlsx",
#     year=year,
#     cons_category=['F1','F2'],
#     sheet_name='Change in consumption',
#     )  

# #%% km demand
# Y_km = commodity_demand(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\mvkm_{ending}.xlsx",
#     year=year,
#     sheet_name = 'mvkm',
#     cons_category='F1',
#     commodity='Car mobility',
#     )  

# #%% housing demand
# measure = '0'
# Y_housing = commodity_demand(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\m2pc_{ending}.xlsx",
#     year=year,
#     sheet_name = f'm2pc {measure}',
#     cons_category='F1',
#     commodity='Housing services',
#     population_path = paths['Support data']+f"\\{Out_Db}\\cons_var_{ending}.xlsx",
#     )  

# #%% km demand
# Y_null = null_demand(
#     commodities='Involved commodities',
#     regions='Involved regions',
#     cons_category='F1',
#     )  

# #%% electricity mix
# scenario = 'REF'
# z_ee = eemix(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\ele_mix{scenario}_{ending}.xlsx",
#     sheet_name=year,
#     year=year,
#     commodity='Electricity'
#     )

# # %% meals demand
# Y_meals = meals_demand(
#     excel_path=paths['Support data']+f"\\{Out_Db}\\cons_var_{ending}.xlsx" ,
#     sheet_name='Number of meals',
#     year=year,
#     cons_category='F1',
#     commodity='Meals',
#     ) 




# # %%

# %%
