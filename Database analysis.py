#%%
import mario
import pandas as pd
import os
import json

sN = slice(None)
user = 'NG' # <--- change this to your own user name (see Paths.json)
with open('Paths.json', 'r') as file:
    paths = json.load(file)[user]

#%% Read database (expected time: 3 min)
world = mario.parse_from_txt(paths['FULFILL']+'\\2021\\flows', 'SUT', 'flows')

# %% Comparing nowcast with actual data
WB_GDP = pd.read_excel(r"Support data\GDP_WB-Exiobase.xlsx",index_col=[0])

reg = ['IT','DE','FR','LV','DK']
region = ['Italy','Germany','France','Latvia','Denmark']

cast = world.GDP().loc[reg]
actu = WB_GDP.loc[reg,'2020 [EUR@2011]'].to_frame()
actu['errore'] = (actu['2020 [EUR@2011]'] - cast['GDP']*1e6)/actu['2020 [EUR@2011]']

# %% Take the food products

sN = slice(None)

FD = 'Final consumption expenditure by households'

food_com = ['Products of meat cattle',
            'Products of meat pigs',
            'Products of meat poultry',
            'products of Vegetable oils and fats',
            'Dairy products',
            'Sugar',
            'Food products nec',
            'Beverages',
            'Fish products']

comm = [
    'Anthracite',
    'Coking Coal',
    'Other Bituminous Coal',
    'Sub-Bituminous Coal',
    'Patent Fuel',
    'Lignite/Brown Coal',
    'BKB/Peat Briquettes',
    'Peat',
    'Natural gas and services related to natural gas extraction; excluding surveying',
    'Natural Gas Liquids',
    'Other Hydrocarbons',
    'Coke Oven Coke',
    'Gas Coke',
    'Coal Tar',
    'Motor Gasoline',
    'Kerosene',
    'Gas/Diesel Oil',
    'Heavy Fuel Oil',
    'Liquefied Petroleum Gases (LPG)',
    'Biogasoline',
    'Biodiesels',
    'Other Liquid Biofuels',
    'Steam and hot water supply services'
]



Y_food = world.Y.loc[(sN,'Commodity',food_com),(reg,sN,FD)]
Y_hhd = world.Y.loc[(sN,'Commodity',comm),(sN,sN,FD)].groupby('Item').sum().T

# %% Aggregate Italian pizzas with German pizzas

cons_food_dry = Y_food.groupby(['Item']).sum()

# Consider the weight
dry_coef = pd.read_excel(r"Support data\Diets.xlsx",index_col=[0], sheet_name='dry_coeff')

# %% For loop to calculate the dry weight of the food products in household's final demand

cons_food = pd.DataFrame(0, index=cons_food_dry.index, columns=cons_food_dry.columns)

for c in cons_food.index:
    for r in cons_food.columns.get_level_values(0):
        cons_food.loc[c,r] = cons_food_dry.loc[c,r].values[0]/dry_coef.loc[c,r]

# %% Read consumption envisaged by the diets analysts of NegaWatt
        
diets = pd.read_excel(r"Support data\Diets.xlsx",index_col=[0,1,2], sheet_name='Consumption')
diets = diets.loc[diets.index.get_level_values(0) != 'sum row']
diets.index = diets.index.set_levels(diets.index.levels[2].map({'Italy': 'IT', 'France': 'FR', 'Germany': 'DE', 'Latvia': 'LV', 'Denmark': 'DK'}), level=2)
diets = diets.loc[:,2021].to_frame().unstack().groupby(['Exiobase commodity']).sum()

# %% Compare the two consumptions

food_comp = {'Database': pd.DataFrame(0, index=cons_food.index, columns=cons_food.columns.get_level_values(0)),
             'Negawatt': pd.DataFrame(0, index=cons_food.index, columns=cons_food.columns.get_level_values(0)),
             'Relative': pd.DataFrame(0, index=cons_food.index, columns=cons_food.columns.get_level_values(0)),
             'Absolute': pd.DataFrame(0, index=cons_food.index, columns=cons_food.columns.get_level_values(0))}

for c in cons_food.index:
    for r in cons_food.columns.get_level_values(0):
        food_comp['Database'].loc[c,r] = cons_food.loc[c,r].values[0]
        food_comp['Negawatt'].loc[c,r] = diets.loc[c,(2021,r)]
        food_comp['Relative'].loc[c,r] = (food_comp['Database'].loc[c,r] - food_comp['Negawatt'].loc[c,r]) / food_comp['Negawatt'].loc[c,r]
        food_comp['Absolute'].loc[c,r] = (food_comp['Database'].loc[c,r] - food_comp['Negawatt'].loc[c,r])
# %%
import matplotlib.pyplot as plt

diff = 'Relative' # <--- change this to 'Relative' to see relative differences

plt.figure(figsize=(10, 8))
im = plt.imshow(food_comp[diff], cmap='coolwarm', aspect='auto')

# Add text annotations
for i in range(len(food_comp[diff].index)):
    for j in range(len(food_comp[diff].columns)):
        if diff == 'Relative':
            text = f"{food_comp[diff].iloc[i, j]*100:.2f}%"
        else:
            text = f"{food_comp[diff].iloc[i, j]:.2f}"
        plt.text(j, i, text, ha='center', va='center', color='white')

plt.colorbar(label=f'{diff} Difference')
plt.xticks(range(len(food_comp[diff].columns)), food_comp[diff].columns, rotation=90)
plt.yticks(range(len(food_comp[diff].index)), food_comp[diff].index)
plt.xlabel('Region')
plt.ylabel('Food Commodity')
plt.title(f'{diff} Difference of Food Consumption')
plt.show()

# %% Same chart but interactive
import plotly.graph_objects as go

diff = 'Absolute' # <--- change this to 'Relative' to see relative differences

fig = go.Figure(data=go.Heatmap(
    z=food_comp[diff],
    x=food_comp[diff].columns,
    y=food_comp[diff].index,
    colorscale='tealrose'
))

# Add text annotations
for i in range(len(food_comp[diff].index)):
    for j in range(len(food_comp[diff].columns)):
        if diff == 'Relative':
            text = f"{food_comp[diff].iloc[i, j]*100:.2f}%"
        else:
            text = f"{food_comp[diff].iloc[i, j]:.2f}"
        fig.add_annotation(
            x=food_comp[diff].columns[j],
            y=food_comp[diff].index[i],
            text=text,
            showarrow=False,
            font=dict(color='white')
        )

fig.update_layout(
    title=f'{diff} Difference of Food Consumption',
    xaxis=dict(title='Region'),
    yaxis=dict(title='Food Commodity'),
    coloraxis_colorbar=dict(title=f'{diff} Difference'),
    width=800,
    height=600
)

fig.write_html(f'Output/food_consumption_{diff} difference.html')

# %%
ele_cons = world.Y.loc[(sN,'Commodity','Electricity')].groupby(['Item']).sum().loc[:,(sN,sN,'Final consumption expenditure by households')].T
# %%
