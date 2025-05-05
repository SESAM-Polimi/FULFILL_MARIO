#%%
import pandas as pd
import pint
import mario
import typing

sN = slice(None)

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
        'database': "database",
        'acts_coms': {
            "Diesel and gasoline car":"Liquid fuels",
            "LPG car":"Liquefied Petroleum Gases (LPG)",
            "Methane car":"Natural gas and services related to natural gas extraction; excluding surveying",
            "Hydrogen car":"Chemicals nec",
            "Full electric car":"Electricity",
        }
    },
    'hs-eff': {
        'database': "database",
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
        'database': "database",
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
        'population_path': "Data/Files for shocks/cons_var_Full.xlsx",
        'shock_type': 'Update',
    },
    'wash-mac': {
        'commodity': 'Machinery and equipment n.e.c. (29)',
        'cons_category': 'Households final consumption',
        'population_path':"Data/Files for shocks/cons_var_Full.xlsx",
        'shock_type': 'Absolute',
    },
    'wash-ee': {
        'commodity': 'Electricity',
        'cons_category': 'Households final consumption',
        'population_path':"Data/Files for shocks/cons_var_Full.xlsx",
        'shock_type': 'Absolute',
    },
    'm2pc': {
        'commodity': 'Housing services',
        'cons_category': 'Households final consumption',
        'population_path':"Data/Files for shocks/cons_var_Full.xlsx",
        'shock_type': 'Update',
    },

}

def change_market_shares(
        excel_path: str,
        sheet_name: str,
        year: int,
        commodity:str,
        ):
        """This function returns a dataframe in the shape of a MARIO shock template
        Each row of the dataframe provide information on the penetration of a specific powertrain or diet
        in each scenario and year for a specific region.

        Args:
            excel_path (str): path to file excel containing all data on car mix
            year (int): year
            commodity (str, optional): name of the output commodity of all car/diet activities (car mobility or meals).

        Returns:
            pd.DataFrame(): dataframe in the shape of a MARIO shock template 
        """

        # read carmix excel
        data = pd.read_excel(excel_path, sheet_name=sheet_name, header=[0,1],index_col=[0,1])
        data = data.droplevel(0, axis=1)

        powertrains = data.index.get_level_values(1).unique()

        shock_z = pd.DataFrame()

        for region in data.columns:
            values = data.loc[(year,powertrains),region].values
            shock_z_dict = {
                'row region': [region for p in powertrains],
                'row level': ['Activity' for p in powertrains],
                'row sector': powertrains,
                'column region': [region for p in powertrains],
                'column level': ['Commodity' for p in powertrains],
                'column sector': [commodity for p in powertrains],
                'type': ['Update' for p in powertrains],
                'value': values,
                }
            shock_z = pd.concat([shock_z,pd.DataFrame(shock_z_dict)],axis=0)
        
        return shock_z


#%% 
def coeffs_change(
        excel_path:str,
        year:int,
        sheet_name:str,
        database:mario.Database,
        acts_coms:dict,
        target_act:str=None,
        com_only_domestic:list=[],
        ):
        """This function returns a dataframe in the shape of a MARIO shock template
        Each row of the dataframe provide information on the fuel economy of a specific powertrain 
        in each year for a specific region.

        Args:
            excel_path (str): path to file excel containing all data on car fuel economies
            year (int): year
            world (mario.Database): MARIO database object
            measure (str): measure code (M or S)
            cars_fuels (dict): dictionary mapping car activities to fuel commodities
        """

        # read careff excel
        data = pd.read_excel(excel_path, sheet_name=sheet_name, header=[0,1],index_col=[0,1])
        data = data.droplevel(0, axis=1)

        shock_z = pd.DataFrame()

        for region in data.columns:
            for act,com in acts_coms.items():

                if target_act==None:
                    col_sector = act
                else:
                    col_sector = target_act

                if com in com_only_domestic:
                    shock_z_dict = {
                        'row region': [region],
                        'row level': ['Commodity'],
                        'row sector': [com],
                        'column region': [region],
                        'column level': ['Activity'],
                        'column sector': [col_sector],  
                        'type': ['Update'],
                        'value': [data.loc[(year,act),region]],
                        }

                else:
                    coeff = data.loc[(year,act),region]
                    com_useY = database.Y.loc[(sN,sN,com),(region,sN,sN)]
                    if com_useY.sum().sum()==0:
                        com_useU = database.U.loc[(sN,sN,com),(region,sN,sN)]
                        u_share = (com_useY.sum(1) + com_useU.sum(1))/(com_useU.sum().sum() + com_useY.sum().sum()) * coeff

                    else:
                        u_share = com_useY.sum(1)/com_useY.sum().sum()*coeff

                    u_share = u_share.to_frame()
                    u_share.columns = ['value']
                    u_share = u_share.query('value!=0')

                    u_share = u_share.dropna()

                    if u_share.shape[0] == 0:
                        print(f"Warning: some values are missing for {com} in {region}")

                    else:
                        shock_z_dict = {
                            'row region': u_share.index.get_level_values(0).tolist(),
                            'row level': ['Commodity' for i in u_share.index],
                            'row sector': [com for i in u_share.index],
                            'column region': [region for i in u_share.index],
                            'column level': ['Activity' for i in u_share.index],
                            'column sector': [col_sector for i in u_share.index],  
                            'type': ['Update' for i in u_share.index],
                            'value': u_share.values.flatten().tolist(),
                            }
                
                shock_z = pd.concat([shock_z,pd.DataFrame(shock_z_dict)],axis=0)
                
        return shock_z

#%%
def change_in_consumption(
    excel_path:str,
    year:int,
    cons_category:typing.Union[str, list],
    commodity:str='all',
    sheet_name:str = 'Change in consumption',
    ):

    """This function returns a dataframe in the shape of a MARIO shock template
    Each row of the dataframe provide information on the the growth rate of consumption for  
    a given consumption category in a given year for a specific region.

    Args:
        excel_path (str): path to file excel containing all data on car fuel economies
        year (int): year
        cons_category (str or list): consumption category(ies) to be updated
    """

    data = pd.read_excel(excel_path, sheet_name=sheet_name, header=[0],index_col=[0])

    if isinstance(cons_category, str):
        cons_category = [cons_category]

    shock_Y = pd.DataFrame()

    for region in data.index:

        growth_rate = data.loc[region,year]
        shock_Y_dict = {
            'row region': ['all' for i in cons_category],
            'row level': ['Commodity' for i in cons_category],
            'row sector': [commodity for i in cons_category],
            'column region': [region for i in cons_category],
            'demand category': [d for d in cons_category],  
            'type': ['Percentage' for i in cons_category],
            'value': [growth_rate for i in cons_category],
            }
        
        shock_Y = pd.concat([shock_Y,pd.DataFrame(shock_Y_dict)],axis=0)

    return shock_Y

#%%
def meals_demand(
        excel_path:str,
        sheet_name:str,
        year:int,
        cons_category:str,
        commodity:str = 'Meals',
        ):
        """This function returns a dataframe in the shape of a MARIO shock template
        Each row of the dataframe provide information on the number of meals to be consumed 
        in each year for a specific region.

        Args:
            excel_path (str): path to file excel containing all data on car fuel economies
            year (int): year
            cons_category (str): name of the consumption category consuming the commodity
            commodity (str, optional): name of the meals commodity. Defaults to 'Meals'.
        """

        # read km_demand excel
        data = pd.read_excel(excel_path, sheet_name=sheet_name, header=[0],index_col=[0])

        shock_Y = pd.DataFrame()

        for region in data.index:

            meals = data.loc[region,year]
            shock_Y_dict = {
                'row region': [region],
                'row level': ['Commodity'],
                'row sector': [commodity],
                'column region': [region],
                'demand category': [cons_category],  
                'type': ['Update'],
                'value': [meals],
                }
            
            shock_Y = pd.concat([shock_Y,pd.DataFrame(shock_Y_dict)],axis=0)

        return shock_Y

#%%
def commodity_demand(
        excel_path:str,
        year:int,
        sheet_name:str,
        cons_category:str,
        commodity:str = 'Car mobility',
        population_path:str = None,
        shock_type:str = 'Update',
        ):
        """This function returns a dataframe in the shape of a MARIO shock template
        Each row of the dataframe provide information on the fuel economy of a specific powertrain 
        in each year for a specific region.

        Args:
            excel_path (str): path to file excel containing all data on car fuel economies
            year (int): year
            cons_category (str): name of the consumption category consuming the commodity
            commodity (str, optional): name of the output commodity of all car activities. Defaults to 'Car mobility'.
            population_path (str, optional): if not None, provide path to excel file where Population projections are given
        """

        # read commodity_demand excel
        data = pd.read_excel(excel_path, sheet_name=sheet_name, header=[0,1],index_col=[0,1])
        data = data.droplevel(0, axis=1)
        data = data.droplevel(1, axis=0)

        shock_Y = pd.DataFrame()

        for region in data.columns:
            
            values = data.loc[year,region]
            if population_path!=None:
                pop = pd.read_excel(population_path,sheet_name='Population_no_world',header=[0],index_col=[0]).loc[region,year]
                values *= pop

            shock_Y_dict = {
                'row region': [region],
                'row level': ['Commodity'],
                'row sector': [commodity],
                'column region': [region],
                'demand category': [cons_category],  
                'type': [shock_type],
                'value': [values],
                }
            
            shock_Y = pd.concat([shock_Y,pd.DataFrame(shock_Y_dict)],axis=0)

        return shock_Y


#%%
def null_demand(
        cons_category:str,
        commodities:str,
        regions:str,
        ):
        """This function returns a dataframe in the shape of a MARIO shock template
        Each row of the dataframe provide information on the fuel economy of a specific powertrain 
        in each year for a specific region.

        Args:
            excel_path (str): path to file excel containing all data on car fuel economies
            year (int): year
            cons_category (str): name of the consumption category consuming the commodity
            commodity (str, optional): name of the output commodity of all car activities. Defaults to 'Car mobility'.
            population_path (str, optional): if not None, provide path to excel file where Population projections are given
        """

        # read commodity_demand excel
        shock_Y = pd.DataFrame()
            
        shock_Y_dict = {
            'row region': ['all'],
            'row level': ['Commodity'],
            'row sector': commodities,
            'column region': regions,
            'demand category': [cons_category],  
            'type': ['Update'],
            'value': [0],
            }
        
        shock_Y = pd.concat([shock_Y,pd.DataFrame(shock_Y_dict)],axis=0)

        return shock_Y


#%%
def eemix(
        excel_path: str,
        sheet_name: int,
        year:int,
        commodity:str ='Electricity',
        ):
        """This function returns a dataframe in the shape of a MARIO shock template
        Each row of the dataframe provide information on the penetration of a specific power tech 
        in each scenario and year for a specific region.

        Args:
            excel_path (str): path to file excel containing all data on car mix
            scenario (str): name of the scenario
            year (int): year
            commodity (str, optional): name of the output commodity of all car activities. Defaults to 'Electricity'.

        Returns:
            pd.DataFrame(): dataframe in the shape of a MARIO shock template 
        """

        # read eemix excel
        if type(sheet_name)==int:
            sheet_name = str(sheet_name)
        data = pd.read_excel(excel_path, sheet_name=sheet_name, header=[0],index_col=[0])

        ee_techs = list(data.columns)

        shock_z = pd.DataFrame()

        for region in data.index:
            values = data.loc[region,ee_techs].values
            shock_z_dict = {
                'row region': [region for p in ee_techs],
                'row level': ['Activity' for p in ee_techs],
                'row sector': ee_techs,
                'column region': [region for p in ee_techs],
                'column level': ['Commodity' for p in ee_techs],
                'column sector': [commodity for p in ee_techs],
                'type': ['Update' for p in ee_techs],
                'value': values,
                }
            shock_z = pd.concat([shock_z,pd.DataFrame(shock_z_dict)],axis=0)
        
        return shock_z

#%%
def sat_coeffs_change(
        excel_path: str,
        sheet_name: int,
        year:int,
        ):
    
        data = pd.read_excel(excel_path, sheet_name=sheet_name, header=[0,1],index_col=[0,1,2])
        data = data.droplevel(0, axis=1)

        sat_accounts = data.index.get_level_values(0).unique()
        activities = data.index.get_level_values(2).unique()

        shock_e = pd.DataFrame()

        for region in data.columns:
            for sa in sat_accounts:
                values = data.loc[(sa,year,activities),region].values
                shock_e_dict = {
                    'row sector': [sa for p in activities],
                    'column region': [region for p in activities],
                    'column level': ['Activity' for p in activities],
                    'column sector': activities,
                    'type': ['Update' for p in activities],
                    'value': values,
                    }
                
                shock_e = pd.concat([shock_e,pd.DataFrame(shock_e_dict)],axis=0)
        
        return shock_e

#%%
def all_coeffs_change(
        excel_path: str,
        sheet_name: int,
        year:int,      
        commodity:str,
        ):   

    data = pd.read_excel(excel_path, sheet_name=sheet_name, header=[0],index_col=[0])

    activity = 'all'

    if not isinstance(activity,list):
        activity = [activity]

    shock_z = pd.DataFrame()

    for region in data.index:

        value = data.loc[region,year]
        shock_z_dict = {
            'row region': ['all' for i in activity],
            'row level': ['Commodity' for i in activity],
            'row sector': [commodity for i in activity],
            'column region': [region for i in activity],
            'column level': ['Activity' for i in activity],
            'column sector': [i for i in activity],  
            'type': ['Percentage' for i in activity],
            'value': [value for i in activity],
            }
        
        shock_z = pd.concat([shock_z,pd.DataFrame(shock_z_dict)],axis=0)

    return shock_z

#%%
def get_shock_file(
        background,
        measure,
        year,
        shockmap,
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
        if pd.isna(row['other_parameters']):
             oth_par_list = ['None']
        else:
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
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'wash-mac' and par == 'population_path':
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'wash-ee' and par == 'population_path':
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'mvkm' and par == 'population_path':
                    additional_parameters += f"{par}='{value}',"
                elif shock == 'hous' and par == 'target_act':
                    additional_parameters += f"{par}='{value}',"
                else:
                    additional_parameters += f"{par}={value},"
        
        if function == 'eemix':
            excel_path = f"Data/Files for shocks/ele-mix{background}_Full.xlsx"
            sheet_name = str(year)
        else:
            excel_path = f"Data/Files for shocks/{row['excel_path']}_Full.xlsx"


        expression = f"{function}(excel_path='{excel_path}',sheet_name='{sheet_name}',year={year}"
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
