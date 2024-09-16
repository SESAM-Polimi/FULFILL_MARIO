#%%
import pandas as pd
import pint
import mario
import typing

sN=slice(None)

def get_new_sets(set_map,main_sheet,db):
    
    new_activities = list(set(set_map[main_sheet]['Activity']))
    new_commodities = list(set(set_map[main_sheet]['Commodity']))

    # listing parented activities
    parented_activities = []
    for act in new_activities:
        parent = set_map[main_sheet].query("Activity==@act")["Parent"].values[0]
        if type(parent)==str:
            parented_activities += [act]
    
    # excluding already existing activities    
    new_activities = [x for x in new_activities if x not in db.get_index('Activity')]

    # excluding parented activities    
    for act in parented_activities:
        new_activities.remove(act)

    # excluding already existing commodities            
    new_commodities = [x for x in new_commodities if x not in db.get_index('Commodity')]
    
    return new_activities,new_commodities,parented_activities
    

def fill_units(path,item,new_items,set_map,main_sheet):

    template = pd.read_excel(path,sheet_name='units')
    new_units = set_map[main_sheet].query("Commodity==@new_items").loc[:,[item,'FU_unit']].set_index(item).to_dict()
    template['unit'] = template[list(template.columns)[0]].map(new_units['FU_unit'])
    template.set_index(list(template.columns)[0],inplace=True)
    template.index.names = ['']
    
    with pd.ExcelWriter(path, mode='a', engine='openpyxl',if_sheet_exists='replace') as writer:
        template.to_excel(writer,sheet_name='units')

def parent_parented(db,set_map,main_sheet,parented_activities):
    
    z=db.z
    v=db.v
    e=db.e
    
    for pa in parented_activities:
        parent = set_map[main_sheet].query("Activity==@pa")['Parent'].values[0]
        region = set_map[main_sheet].query("Activity==@pa")['Region'].values[0]
        
        z.loc[:,(region,sN,pa)] = z.loc[:,(region,sN,parent)].values
        v.loc[:,(region,sN,pa)] = v.loc[:,(region,sN,parent)].values
        e.loc[:,(region,sN,pa)] = e.loc[:,(region,sN,parent)].values

    db.update_scenarios('baseline',z=z,v=v,e=e)
    db.reset_to_coefficients('baseline')

def remove_non_empty(all_activities,set_map,main_sheet):
    
    empty_activities = set_map[main_sheet].query("Empty == True")['Activity']
    non_empty_activities = list(set(empty_activities) ^ set(all_activities))

    return non_empty_activities


def fill_u(activities,set_map,main_sheet,db,world,region_maps,sheet_to_fill):
    
    for act in activities:
        act_sheets = set_map[main_sheet].query("Activity==@act")['Sheet_name'].to_list()
        
        for sheet in act_sheets:

            inventory_indices = list(set_map[sheet].columns)
            inventory_indices.remove('quantity') 
    
            inventory = set_map[sheet].loc[set_map[sheet].Item=='Commodity']
            inventory['conv_quantity'] = ""

            # convert units
            ureg = pint.UnitRegistry()
            for i in inventory.index:
                if inventory.loc[i,'unit'] == inventory.loc[i,f'{db} unit']:  # if units are the same as the database
                    pass
                elif ureg(inventory.loc[i,'unit']).is_compatible_with(inventory.loc[i,f'{db} unit']): # if units are compatible with pint by defualt
                    inventory.loc[i,'conv_quantity'] = inventory.loc[i,'quantity']*ureg(inventory.loc[i,'unit']).to(inventory.loc[i,f'{db} unit']).magnitude
                else: # if units are not compatible with pint by defualt
                    print(f"Unit {inventory.loc[i,'unit']} conversion not possible for {inventory.loc[i,'Commodity']} in {inventory.loc[i,'Region']}")
                    break

            # check in which region the activity should be added 
            act_region = set_map[main_sheet].query("Activity==@act & Sheet_name==@sheet")['Region'].values[0]
            if act_region not in world.get_index('Region'):
                regions = region_maps[act_region] # take a list from region_maps (if missing, should raise an error)
            else:
                regions = [act_region] # make it a list to iterate over even if it's just one region

            for reg_act in regions:  # for each region in which the activity must be added
                
                # region import share 
                regions_db = list(set(inventory[f"{db} Region"]).intersection(world.get_index('Region')))  # find all regions that are also in database
                inputs_db = inventory.query(f"`{db} Region` == @regions_db") # keep inventory rows that can be used as is in the database
                inputs_non_db = inventory.query(f"`{db} Region` != @regions_db") # keep inventory rows that need to be converted to database regions
                
                for i in inputs_non_db.index:
                    commodity = inputs_non_db.loc[i,f"{db} Commodity"]
                    region = inputs_non_db.loc[i,f"{db} Region"]
                    
                    com_use = world.U.loc[(region_maps[region],sN,commodity),(reg_act,sN,sN)]   # da aggiornare se chenery
                    u_share = com_use.sum(1)/com_use.sum().sum()*inputs_non_db.loc[i,'conv_quantity']
                        
                    idb = {}
                    for col in inputs_non_db.columns:
                        idb[col] = [inputs_non_db.loc[i,col] for r in u_share.index]
                        if col == f"{db} Region":
                            idb[col] = list(u_share.index.get_level_values('Region'))
                        if col == 'conv_quantity':
                            idb[col] = u_share.values.tolist()               
                    inputs_db = pd.concat([inputs_db,pd.DataFrame(idb)],axis=0)
            
                u = {
                    'row region': inputs_db[f'{db} Region'],
                    'row level': ['Commodity' for r in inputs_db.index],
                    'row sector': inputs_db[f'{db} Commodity'],
                    # 'column region': [set_map[main_sheet].query("Activity==@act & Sheet_name==@sheet")['Region'].values[0] for r in inputs_db.index],
                    'column level': ['Activity' for r in inputs_db.index],
                    'column sector': [act for r in inputs_db.index],
                    'type': [inputs_db.iloc[r,list(inputs_db.columns).index('Type')] for r in inputs_db.index],
                    'value': inputs_db['conv_quantity'],
                    }
                
                u['column region'] = []
                for r in inputs_db.index:
                    u['column region'] += [reg_act]
                    
                sheet_to_fill = pd.concat([sheet_to_fill, pd.DataFrame(u)],axis=0)
        
    return sheet_to_fill


def fill_e(activities,set_map,main_sheet,db,world,region_maps,sheet_to_fill):
    
    for act in activities:
        act_sheets = set_map[main_sheet].query("Activity==@act")['Sheet_name'].to_list()
        
        for sheet in act_sheets:
                    
            inventory_indices = list(set_map[sheet].columns)
            inventory_indices.remove('quantity') 
    
            inventory = set_map[sheet].loc[set_map[sheet].Item=='Satellite account']
            inventory['conv_quantity'] = ""

            # convert units
            ureg = pint.UnitRegistry()
            for i in inventory.index:
                if inventory.loc[i,'unit'] == inventory.loc[i,f'{db} unit']:  # if units are the same as the database
                    pass
                elif ureg(inventory.loc[i,'unit']).is_compatible_with(inventory.loc[i,f'{db} unit']): # if units are compatible with pint by defualt
                    inventory.loc[i,'conv_quantity'] = inventory.loc[i,'quantity']*ureg(inventory.loc[i,'unit']).to(inventory.loc[i,f'{db} unit']).magnitude
                else: # if units are not compatible with pint by defualt
                    print(f"Unit {inventory.loc[i,'unit']} conversion not possible for {inventory.loc[i,'Commodity']} in {inventory.loc[i,'Region']}")
                    break

            # check in which region the activity should be added 
            act_region = set_map[main_sheet].query("Activity==@act & Sheet_name==@sheet")['Region'].values[0]
            if act_region not in world.get_index('Region'):
                regions = region_maps[act_region] # take a list from region_maps (if missing, should raise an error)
            else:
                regions = [act_region] # make it a list to iterate over even if it's just one region

            for reg_act in regions:  # for each region in which the activity must be added
                regions_db = list(set(inventory[f"{db} Region"]).intersection(world.get_index('Region')))  # find all regions that are also in database
                inputs_db = inventory.query(f"`{db} Region` == @regions_db") # keep inventory rows that can be used as is in the database
                inputs_non_db = inventory.query(f"`{db} Region` != @regions_db") # keep inventory rows that need to be converted to database regions

                e = {
                    'row sector': inputs_db[f'{db} Commodity'],
                    'column region': [reg_act for r in inputs_db.index],
                    'column level': ['Activity' for r in inputs_db.index],
                    'column sector': [act for r in inputs_db.index],
                    'type': inputs_db['Type'].to_list(),
                    'value': inputs_db['quantity'],
                    }
            
                sheet_to_fill = pd.concat([sheet_to_fill, pd.DataFrame(e)], axis=0)
    
    return sheet_to_fill


def null_Y(activities,set_map,main_sheet,Y_categories,db,world,region_maps,sheet_to_fill):

    for act in activities:
        act_sheets = set_map[main_sheet].query("Activity==@act")['Sheet_name'].to_list()
        involved_region = set_map[main_sheet].query("Activity==@act")['Region'].values[0]

        for sheet in act_sheets:
            involved_commodities = list(set(set_map[sheet].query("Item=='Commodity'")[f'{db} Commodity']))

            for demcat in Y_categories:
                for commodity in involved_commodities:
                    for region in world.get_index('Region'):

                        Y = {
                            'row region': [region],
                            'row level': ['Commodity'],
                            'row sector': [commodity],
                            'column region': [involved_region],
                            'demand category': [demcat],
                            'type': ['Update'],
                            'value': [0],
                            }
                
                        sheet_to_fill = pd.concat([sheet_to_fill, pd.DataFrame(Y)], axis=0)

    return sheet_to_fill


#%%
def add_new_supply_chains(
        paths, 
        main_sheet, 
        world, 
        Y_categories,
        sat_EY,
        add_sectors_template=False,
        db = 'EXIOBASE',
        scenario='new supply chains',
        add_final_demand=True,
        ):
    
    # reading map and getting sets
    Add_sectors_map = pd.read_excel(paths['Map'], sheet_name=None)
    region_maps = {k:Add_sectors_map['region_maps'][k].dropna().to_list()  for k in Add_sectors_map['region_maps'].columns}
    new_activities,new_commodities,parented_activities = get_new_sets(Add_sectors_map,main_sheet,world)    
            
    # Getting excel templates to add new activities and commodities
    if add_sectors_template:
        world.get_add_sectors_excel(new_sectors=new_commodities,regions=world.get_index('Region'),path=paths['commodities'], item='Commodity')
        world.get_add_sectors_excel(new_sectors=new_activities+parented_activities,regions=world.get_index('Region'),path=paths['activities'], item='Activity')
        
        # read commodity template and add units
        fill_units(path=paths['commodities'],item='Commodity',new_items=new_commodities,set_map=Add_sectors_map,main_sheet=main_sheet)
        fill_units(path=paths['activities'],item='Activity',new_items=new_activities+parented_activities,set_map=Add_sectors_map,main_sheet=main_sheet)
            
    # Adding new commodities and activities    
    world.add_sectors(io=paths['commodities'], new_sectors=new_commodities, regions=world.get_index('Region'), item= 'Commodity', inplace=True)
    world.add_sectors(io=paths['activities'], new_sectors=new_activities+parented_activities, regions=world.get_index('Region'), item= 'Activity', inplace=True )    
           
    # copy parent into parented activities
    parent_parented(world,Add_sectors_map,main_sheet,parented_activities)
    
    # filter on non empty activiies
    activities_to_add = remove_non_empty(new_activities+parented_activities,Add_sectors_map,main_sheet,)
    
    # create shock templates
    world.get_shock_excel(path=paths['values'])
    shock_sheets = pd.read_excel(paths['values'], sheet_name=None)
    
    # fill excel sheets
    shock_sheets['z'] = fill_u(
        activities=activities_to_add,
        set_map=Add_sectors_map, 
        main_sheet=main_sheet, 
        db=db, 
        world=world,
        region_maps=region_maps,
        sheet_to_fill=shock_sheets['z'])
    
    shock_sheets['e'] = fill_e(
        activities=activities_to_add,
        set_map=Add_sectors_map, 
        main_sheet=main_sheet, 
        db=db, 
        world=world,
        region_maps=region_maps,
        sheet_to_fill=shock_sheets['e'])
    
    # market_shares
    act_region = Add_sectors_map[main_sheet]['Region'].values[0]
    if act_region not in world.get_index('Region'):
        regions = region_maps[act_region] # take a list from region_maps (if missing, should raise an error)
    else:
        regions = [act_region] # make it a list to iterate over even if it's just one region

    for reg_act in regions:  # for each region in which the activity must be added
        s = {
            'row region': [reg_act for r in Add_sectors_map[main_sheet].index],
            'row level': ['Activity' for r in Add_sectors_map[main_sheet].index],
            'row sector': Add_sectors_map[main_sheet]['Activity'],
            'column region': [reg_act for r in Add_sectors_map[main_sheet].index],
            'column level': ['Commodity' for r in Add_sectors_map[main_sheet].index],
            'column sector': Add_sectors_map[main_sheet]['Commodity'],
            'type': ['Update' for r in Add_sectors_map[main_sheet].index],
            'value': Add_sectors_map[main_sheet]['Market share'],     
            }
    
        shock_sheets['z'] = pd.concat([shock_sheets['z'].fillna(0), pd.DataFrame(s)],axis=0) # Sto azzerando settori problematici
    
    if add_final_demand:
        cons_category = world.get_index('Consumption category')[0]
        added_commodities = list(set(Add_sectors_map[main_sheet]['Commodity']))
        first_region = world.get_index('Region')[0]

        Y = {
            'row region': ['all' for i in added_commodities],
            'row level': ['Commodity' for i in added_commodities],
            'row sector': added_commodities,
            'column region': [first_region for i in added_commodities],
            'demand category': [cons_category for d in added_commodities],  
            'type': ['Update' for i in added_commodities],
            'value': [1 for i in added_commodities],
            }
        
        shock_sheets['Y'] = pd.concat([shock_sheets['Y'].fillna(0), pd.DataFrame(Y)],axis=0) # Mettiamo domanda finale delle nuove commodity per non annullare le u

    with pd.ExcelWriter(paths['values']) as writer:
        for sheet,df in shock_sheets.items():
            df.to_excel(writer,sheet_name=sheet, index=False)
    writer.close()
    
    clusters = {
    'Region':{'all':world.get_index('Region')},
    }

    world.shock_calc(paths['values'],z=True,e=True,Y=True,scenario=scenario,**clusters)
    
    EY = world.get_data(['EY'],scenarios=[scenario])[scenario][0]
    EY.loc[sat_EY,(region_maps['EU27'])] *= 0

    world.update_scenarios(scenario,EY=EY)
    world.reset_to_coefficients(scenario)

    world.to_txt(paths['export_path'], scenario=scenario)


#%%
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






