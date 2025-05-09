import numpy as np
import pandas as pd
import json
from copy import deepcopy

def load_data():
    with open('Data/BONSAI/bonsai_footprints.json', 'r') as f:
        footprints = pd.DataFrame(json.load(f))

    with open('Data/BONSAI/bonsai_activity-names.json', 'r') as f:
        activities = pd.DataFrame(json.load(f))

    with open('Data/BONSAI/bonsai_recipes.json', 'r') as f:
        recipes = pd.DataFrame(json.load(f))

    with open('Data/BONSAI/bonsai_locations.json', 'r') as f:
        locations = pd.DataFrame(json.load(f))

    version = 'v1.0.0'

    mask = (footprints['version']==version) & (footprints['unit_reference']=='tonnes')
    footprints = footprints[mask]

    mask = (recipes['version']==version)
    recipes = recipes[mask]

    agribalyse = pd.read_csv('Data/agribalyse_data.csv')
    bigclimatedata = pd.read_csv('Data/bigclimatedb.csv')
    
    return agribalyse, footprints, recipes, activities, locations, bigclimatedata


agribalyse, footprints, recipes, activities, locations, bigclimatedata = load_data()
activity_dict = {activities.iloc[i,0]:activities.iloc[i,2] for i in range(activities.shape[0])}
region_dict = {locations.iloc[i,0]:locations.iloc[i,1] for i in range(locations.shape[0])}
unit_dict = {'Meuro':'Million EUR', 'tonnes': 'Tonnes', 'items':'Units', 'TJ':'Trillion Joules', 'ha*year':'Hectare per year'}


def check_product_availability(product_name, country):
    """Check if a product has MARKET data for a specific country."""
    # ONLY check BONSAI MARKET data
    try:
        product_code = activities[(activities['description'] == product_name) & 
                            (activities['flow_type'] == 'market')]['code'].iloc[0]
        region_code = locations[locations['name'] == country]['code'].iloc[0]
        filtered_footprints = footprints[(footprints['flow_code'] == product_code) & 
                                    (footprints['region_code'] == region_code)]
        if filtered_footprints.shape[0] > 0:
            return True
    except:
        pass
    
    # Check BigClimateDB
    filtered_data = bigclimatedata[bigclimatedata['Name'] == product_name]
    if filtered_data.shape[0] > 0:
        filtered_data = filtered_data[filtered_data['region'] == country]
        if filtered_data.shape[0] > 0:
            return True
    
    # Agribalyse is only for France, so if country is France, check Agribalyse
    if country == "France":
        try:
            filtered_data = agribalyse[agribalyse['product_name'] == product_name]
            if filtered_data.shape[0] > 0:
                return True
        except:
            pass
    
    return False


def get_bonsai_data(target_description, target_type, target_region, grams=1000,
                    footprints=footprints, recipes=recipes, activities=activities, locations=locations,
                    activity_dict=activity_dict, region_dict=region_dict, unit_dict=unit_dict,
                    use_fallback=True):
    
    try:
        product_code = activities[(activities['description'] == target_description) & 
                            (activities['flow_type'] == target_type)]['code'].iloc[0]
    except:
        return f"No {'production' if target_type=='product' else target_type} data available for '{target_description}' in BONSAI database\n"

    try:
        region_code = locations[locations['name'] == target_region]['code'].iloc[0]
        filtered_footprints = footprints[(footprints['flow_code'] == product_code) & 
                                    (footprints['region_code'] == region_code)]
        if filtered_footprints.shape[0]==0:
            raise Exception("No data for this region")
        
        # Use the specific region's data
        impact = filtered_footprints['value'].iloc[0]
        result_final = f"BONSAI database results for '{target_description}' in {target_region}:\n"
        result_final += f"Impact for {grams} grams: {round_to_sig_figs(impact*grams/1000)} kg co2-eq\n"
    except Exception as e:
        # For product data, don't do fallback
        if target_type == 'product' or not use_fallback:
            return f"No {target_type} data available for '{target_description}' in {target_region} in BONSAI database\n"
        
        # Only do fallback for market data
        if target_type == 'market':
            # Get all available regions for this market
            all_footprints = footprints[footprints['flow_code'] == product_code]
            if all_footprints.shape[0] > 0:
                # Calculate average impact across all regions
                avg_impact = all_footprints['value'].mean()
                region_names = [region_dict.get(code, "Unknown") for code in all_footprints['region_code'].tolist()]
                region_str = ", ".join(region_names[:3])
                if len(region_names) > 3:
                    region_str += f" and {len(region_names)-3} other regions"
                
                # Clearly indicate using average data from multiple regions
                result_final = f"BONSAI database results for '{target_description}' (AVERAGE DATA FROM MULTIPLE REGIONS: {region_str}, NOT {target_region}):\n"
                result_final += f"Impact for {grams} grams: {round_to_sig_figs(avg_impact*grams/1000)} kg co2-eq\n"
                
                # Use the first available region's code for recipe lookup
                filtered_footprints = pd.DataFrame([{
                    'region_code': all_footprints['region_code'].iloc[0],
                    'value': avg_impact
                }])
            else:
                return f"No {target_type} data available for '{target_description}' in any region in BONSAI database\n"

    filtered_recipes = recipes[(recipes['flow_reference'] == product_code) & 
                            (recipes['region_reference'] == filtered_footprints['region_code'].iloc[0])]
    recipe_details = filtered_recipes[['flow_input', 'region_inflow', 'value_inflow', 'value_emission', 'unit_inflow']]

    if recipe_details.shape[0]==0:
        recipe_results = f"No {target_type} recipe available for '{target_description}' in {region_dict.get(filtered_footprints['region_code'].iloc[0], 'Unknown')} in BONSAI database\n"
    else:
        recipe_details.loc[:,'value_emission'] = recipe_details['value_emission'].apply(lambda x: x*grams/1000)
        recipe_details = recipe_details.map(lambda x: round_to_sig_figs(x) if isinstance(x, (int, float)) else x)
        recipe_details['unit_inflow'] = recipe_details['unit_inflow'].apply(lambda x: unit_dict[x] if x in unit_dict.keys() else x)
        recipe_details['value_inflow'] = recipe_details['value_inflow'].astype(str) + ' ' + recipe_details['unit_inflow']
        recipe_details = recipe_details.drop('unit_inflow',axis=1)

        recipe_details['flow_input'] = recipe_details['flow_input'].apply(lambda x: activity_dict[x].capitalize() if x in activity_dict.keys() else x)
        recipe_details['region_inflow'] = recipe_details['region_inflow'].apply(lambda x: region_dict[x] if x in region_dict.keys() else x)

        try:
            direct_process_emissions = recipe_details[[item=='direct' for item in recipe_details['flow_input']]]['value_emission'].iloc[0]
            recipe_details = recipe_details[[item!='direct' for item in recipe_details['flow_input']]]
        except:
            direct_process_emissions = None

        other_row = recipe_details[[item=='other' for item in recipe_details['flow_input']]]
        recipe_details = recipe_details[[item!='other' for item in recipe_details['flow_input']]]
        recipe_details = recipe_details.sort_values('value_emission',ascending=False)
        recipe_details = pd.concat([recipe_details, other_row])
        recipe_details = recipe_details.replace({np.nan: None}).to_dict('records')

        recipe_results = ""
        if direct_process_emissions is not None:
            recipe_results += f"Direct process emissions: {direct_process_emissions} kg co2-eq\n"
        else:
            recipe_results += "No direct process emissions\n"
        if target_type=='market':
            for rcp  in recipe_details:
                flow_inp,region_inf,value_inf,value_ems = rcp.values()
                if flow_inp=='other':
                    recipe_results += f"Other Market Impact for {grams} grams: {value_ems} kg co2-eq\n"
                else:
                    recipe_results += f"Market share for {region_inf}: {value_inf}, Impact for {grams} grams: {value_ems} kg co2-eq\n"

    return result_final+recipe_results


def get_agribalyse_data(product, agribalyse=agribalyse, grams=100):
    try:
        filtered_data = agribalyse[agribalyse['product_name'] == product]
        result = filtered_data.iloc[0].to_dict()
    except:
        return f"No data available for '{product}' in Agribalyse database"

    total_impact = result['total']*grams/1000

    # Always clearly indicate this is French data
    result_final = f"Agribalyse database results for '{product}' (DATA FROM FRANCE):\n"
    result_final += f"Impact for {grams} grams: {round_to_sig_figs(total_impact)} kg co2-eq\n"
    result_final += f"Data quality rating: {result['dqr']}\n"
    phases = ['agriculture', 'processing', 'packaging', 'transportation', 'retail', 'consumption']
    for phase in phases:
        result_final += f"{phase.title()} impact for {grams} grams: {round_to_sig_figs(result[phase]*total_impact)} kq co2-eq, Percentage: {result[phase]*100:.1f}%\n"

    return result_final


def get_bigclimate_data(product, region, bigclimatedata=bigclimatedata, grams=1000, use_fallback=True):
    filtered_data = bigclimatedata[bigclimatedata['Name'] == product]
    if filtered_data.shape[0]==0:
        return f"No data available for '{product}' in BigClimateDatabase"
    
    filtered_by_region = filtered_data[filtered_data['region'] == region]
    if filtered_by_region.shape[0]==0:
        if use_fallback:
            # Use average of all available regions as fallback
            avg_impact = filtered_data['Total kg CO2-eq/kg'].mean()
            region_list = filtered_data['region'].unique().tolist()
            region_str = ", ".join(region_list[:3])
            if len(region_list) > 3:
                region_str += f" and {len(region_list)-3} other regions"
                
            result_final = f"BigClimateDatabase results for '{product}' (AVERAGE DATA FROM MULTIPLE REGIONS: {region_str}, NOT {region}):\n"
            result_final += f"Impact for {grams} grams: {round_to_sig_figs(avg_impact*grams/1000)} kg co2-eq\n"
            
            # Use first region for detailed breakdown
            result = filtered_data.iloc[0].to_dict()
        else:
            return f"No data available for '{product}' for {region} in BigClimateDatabase"
    else:
        result_final = f"BigClimateDatabase results for '{product}' in {region}:\n"
        result = filtered_by_region.iloc[0].to_dict()
        avg_impact = result['Total kg CO2-eq/kg']
        result_final += f"Impact for {grams} grams: {round_to_sig_figs(avg_impact*grams/1000)} kg co2-eq\n"

    total_impact = avg_impact*grams/1000
    phases = ['Agriculture', 'iLUC', 'Food processing', 'Packaging', 'Transport', 'Retail']
    for phase in phases:
        phase_name = 'Indirect Land Use Change' if phase=='iLUC' else phase
        try:
            phase_impact = result[phase] * (total_impact / result['Total kg CO2-eq/kg'])
            phase_percentage = (phase_impact / total_impact) * 100
            result_final += f"{phase_name} impact for {grams} grams: {round_to_sig_figs(phase_impact)} kq co2-eq, Percentage: {phase_percentage:.1f}%\n"
        except:
            continue

    return result_final


def round_to_sig_figs(x, sig_figs=3):
    if isinstance(x, (int, float)):
        if np.isnan(x) or x == 0:
            return x
        else:
            return f"{x:.{sig_figs}g}"
    else:
        return x
    

def get_similar_items(search_top_k, ingredients_list, encoder, vector_database, target_country="Netherlands"):
    """Get similar items for each ingredient and check availability in target country."""
    search_query = deepcopy(ingredients_list)
    ingredient_options = {}
    
    for cur_ingredients in search_query:
        query, grams = cur_ingredients.values()
        top_k_results = search_top_k(encoder, vector_database, query, 3)
        
        all_options = []
        options_with_availability = {}
        
        for source, items in top_k_results.items():
            for item in items:
                has_country_data = check_product_availability(item, target_country)
                all_options.append(item)
                options_with_availability[item.lower()] = has_country_data
            
        ingredient_options[query] = {
            'amount': grams,
            'options': all_options,
            'sources': top_k_results,
            'availability': options_with_availability
        }
    
    return ingredient_options


def get_results(selected_items, ingredients_options, country):
    search_query = []
    
    for (ingredient, data), selections in zip(ingredients_options.items(), selected_items):
        cur_ingredient = {
            'query': ingredient,
            'grams': data['amount'],
            'results': f"Results for selected most similar items to '{ingredient}':\n\n"
        }
        
        if not selections:
            cur_ingredient['results'] += f"No data available in all data sources for {ingredient}"
        else:
            # Clean the selections (remove asterisks if present)
            cleaned_selections = [s.split(" *")[0] for s in selections]
            
            filtered_results = {
                source: [item for item in items if any(s.lower() == item.lower() for s in cleaned_selections)]
                for source, items in data['sources'].items()
            }
            
            for source, name_list in filtered_results.items():
                for product_name in name_list:
                    if source == 'BONSAI':
                        cur_ingredient['results'] += get_bonsai_data(product_name, 'product', country, grams=data['amount'], use_fallback=False)
                        cur_ingredient['results'] += "\n"
                        cur_ingredient['results'] += get_bonsai_data(product_name, 'market', country, grams=data['amount'], use_fallback=True)
                    elif source == 'Agribalyse':
                        cur_ingredient['results'] += get_agribalyse_data(product_name, grams=data['amount'])
                    else:
                        cur_ingredient['results'] += get_bigclimate_data(product_name, country, grams=data['amount'], use_fallback=True)
                    cur_ingredient['results'] += "\n"
        
        search_query.append(cur_ingredient)
    
    results_text = ""
    for cur_dict in search_query:
        results_text += cur_dict['results']
    
    return search_query, results_text