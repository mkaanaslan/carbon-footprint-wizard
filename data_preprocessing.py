import os
import json
import requests
import pandas as pd
from tqdm import tqdm
from pathlib import Path
import time

BASE_URL = "https://lca.aau.dk"
TOKEN = "ADD TOKEN HERE"
HEADERS = {
    "Authorization": f"Token {TOKEN}",
    "Content-Type": "application/json"
}
DATA_DIR = Path("Data")
BONSAI_DIR = DATA_DIR / "BONSAI"

def ensure_directories():
    """Create necessary directories if they don't exist."""
    DATA_DIR.mkdir(exist_ok=True)
    BONSAI_DIR.mkdir(parents=True, exist_ok=True)

def check_existing_bonsai_data():
    """Check if required BONSAI files already exist."""
    required_files = [
        'bonsai_footprints.json',
        'bonsai_recipes.json',
        'bonsai_locations.json',
        'bonsai_activity-names.json'
    ]
    
    missing_files = []
    for file in required_files:
        if not (BONSAI_DIR / file).exists():
            missing_files.append(file)
            
    return missing_files

def check_existing_agribalyse_data():
    """Check if Agribalyse data file exists."""
    return not (DATA_DIR / 'agribalyse_data.csv').exists()

def check_existing_bigclimate_data():
    """Check if BigClimateDB data file exists."""
    return not (DATA_DIR / 'bigclimatedb.csv').exists()


def get_all_pages(url):
    all_results = []
    counter = 0
    total_items = 0
    pbar = tqdm(desc="Fetching pages", unit=" pages")

    while url:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            all_results.extend(data['results'])
            url = data['next']
            counter += 1
            if 'count' in data:
                total_items = data['count']
                pbar.total = total_items
            pbar.update(len(data['results']))
        else:
            print(f"\nError: {response.status_code}")
            print(response.text)
            break

    pbar.close()
    print(f"\nFetching complete. Total pages: {counter}, Total items: {len(all_results)}")
    return all_results


def get_all_non_page(url):
    all_results = []
    page = 1
    pbar = tqdm(desc="Fetching pages", unit="page")

    start_time = time.time()

    while True:
        response = requests.get(url, headers=HEADERS, params={'page': page})

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and data:
                all_results.extend(data)
                page += 1
                #pbar.update(1)

                elapsed_time = time.time() - start_time
                pages_per_second = page / elapsed_time
                pbar.set_description(f"Fetching page {page} [{elapsed_time:.0f}s, {pages_per_second:.2f}page/s]")
            else:
                print("\nReached the end of data or received unexpected response format")
        elif response.status_code == 404:
            print(response.json())
            break
        else:
            page += 1

    pbar.close()
    return all_results

def download_bonsai_data(missing_files=None):
    """Download specified BONSAI data files."""
    endpoints = {
        'bonsai_footprints.json': '/api/footprint/',
        'bonsai_recipes.json': '/api/recipes/',
        'bonsai_locations.json': '/api/locations/',
        'bonsai_activity-names.json': '/api/activity-names/'
    }
    
    files_to_download = missing_files if missing_files else endpoints.keys()
    
    for filename in files_to_download:
        if filename not in endpoints:
            print(f"Unknown file: {filename}")
            continue
            
        endpoint = endpoints[filename]
        file_path = BONSAI_DIR / filename
        name = filename.replace('bonsai_', '').replace('.json', '')
        
        print(f"\nDownloading {name}...")
        url = f"{BASE_URL}{endpoint}"
        
        if name == 'activity-names':
            response = requests.get(url, headers=HEADERS)
            data = response.json()
        elif name == 'recipes':
            data = get_all_non_page(url)
        else:
            data = get_all_pages(url)
        
        if data:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Successfully saved {file_path}")
        else:
            print(f"Failed to download {name}")
            return False
    return True

def download_agribalyse_data():
    """Download and process Agribalyse data."""
    AGRIBALYSE_COLUMNS = [
        "Groupe d'aliment",
        "Sous-groupe d'aliment",
        "LCI Name",
        "DQR",
        "Agriculture",
        "Transformation",
        "Emballage",
        "Transport",
        "Supermarché et distribution",
        "Consommation",
        "Total"
    ]

    FRENCH_TO_ENGLISH_GROUP = {
        'aides culinaires et ingrédients divers': 'culinary aids and various ingredients',
        'aliments infantiles': 'baby foods',
        'boissons': 'beverages',
        'entrées et plats composés': 'starters and composed dishes',
        'fruits, légumes, légumineuses et oléagineux': 'fruits, vegetables, legumes and oilseeds',
        'glaces et sorbets': 'ice creams and sorbets',
        'lait et produits laitiers': 'milk and dairy products',
        'matières grasses': 'fats',
        'produits céréaliers': 'cereal products',
        'produits sucrés': 'sweet products',
        'viandes, œufs, poissons': 'meats, eggs, fish'
    }

    FRENCH_TO_ENGLISH_SUB = {
        'aides culinaires': 'culinary aids',
        'algues': 'seaweed',
        'autres matières grasses': 'other fats',
        'autres produits à base de viande': 'other meat-based products',
        'beurres': 'butters',
        'boisson alcoolisées': 'alcoholic beverages',
        'boissons sans alcool': 'non-alcoholic beverages',
        'charcuteries': 'cold cuts',
        'chocolats et produits à base de chocolat': 'chocolates and chocolate-based products',
        'condiments': 'condiments',
        'confiseries non chocolatées': 'non-chocolate confectioneries',
        'confitures et assimilés': 'jams and similar products',
        'crèmes et spécialités à base de crème': 'creams and cream-based specialties',
        'céréales de petit-déjeuner et biscuits': 'breakfast cereals and biscuits',
        'céréales et biscuits infantiles': 'baby cereals and biscuits',
        'denrées destinées à une alimentation particulière': 'foods for special diets',
        'desserts glacés': 'frozen desserts',
        'desserts infantiles': 'baby desserts',
        'eaux': 'water',
        'farines et pâtes à tarte': 'flours and pie doughs',
        'feuilletées et autres entrées': 'puff pastries and other starters',
        'fromages': 'cheeses',
        'fruits': 'fruits',
        'fruits à coque et graines oléagineuses': 'nuts and oilseeds',
        'glaces': 'ice creams',
        'gâteaux et pâtisseries': 'cakes and pastries',
        'herbes': 'herbs',
        'huiles de poissons': 'fish oils',
        'huiles et graisses végétales': 'vegetable oils and fats',
        'ingrédients divers': 'various ingredients',
        'laits': 'milks',
        'laits et boissons infantiles': 'baby milk and drinks',
        'légumes': 'vegetables',
        'légumineuses': 'legumes',
        'margarines': 'margarines',
        'mollusques et crustacés crus': 'raw mollusks and shellfish',
        'mollusques et crustacés cuits': 'cooked mollusks and shellfish',
        'pains et viennoiseries': 'breads and pastries',
        'petits pots salés et plats infantiles': 'savory baby food jars and baby meals',
        'pizzas, tartes et crêpes salées': 'pizzas, pies, and savory crepes',
        'plats composés': 'composed dishes',
        'plats végétariens': 'vegetarian dishes',
        'poissons crus': 'raw fish',
        'poissons cuits': 'cooked fish',
        'pommes de terre et autres tubercules': 'potatoes and other tubers',
        'produits laitiers frais et assimilés': 'fresh dairy products and similar items',
        'produits à base de poissons et produits de la mer': 'fish-based products and seafood',
        'pâtes, riz et céréales': 'pasta, rice, and cereals',
        'salades composées et crudités': 'composed salads and raw vegetables',
        'sandwichs': 'sandwiches',
        'sauces': 'sauces',
        'sels': 'salts',
        'sorbets': 'sorbets',
        'soupes': 'soups',
        'substituts de charcuterie': 'cold cut substitutes',
        'substituts de viande': 'meat substitutes',
        'sucres, miels et assimilés': 'sugars, honeys, and similar products',
        'viandes crues': 'raw meats',
        'viandes cuites': 'cooked meats',
        'épices': 'spices',
        'œufs': 'eggs'
    }

    url = "https://entrepot.recherche.data.gouv.fr/api/access/datafile/:persistentId?persistentId=doi:10.57745/94BKZL"
    temp_file = DATA_DIR / 'agribalyse_data.xlsx'
    output_file = DATA_DIR / 'agribalyse_data.csv'

    try:
        print("Downloading Agribalyse data...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(temp_file, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        print("Processing Agribalyse data...")
        agribalyse_pd = pd.read_excel(temp_file, sheet_name="Detail etape", skiprows=3).dropna()[AGRIBALYSE_COLUMNS]
        agribalyse_pd.columns = ['group', 'subgroup', 'product_name', 'dqr', 'agriculture', 'processing', 
                                'packaging', 'transportation', 'retail', 'consumption', 'total']
        
        agribalyse_pd['group'] = agribalyse_pd['group'].apply(lambda x: FRENCH_TO_ENGLISH_GROUP[x])
        agribalyse_pd['subgroup'] = agribalyse_pd['subgroup'].apply(lambda x: FRENCH_TO_ENGLISH_SUB[x])
        
        agribalyse_pd.to_csv(output_file, index=False)
        os.remove(temp_file)
        print(f"Successfully saved {output_file}")
        return True

    except Exception as e:
        print(f"Error processing Agribalyse data: {e}")
        if temp_file.exists():
            os.remove(temp_file)
        return False

def download_bigclimate_data():
    """Download and process BigClimateDB data."""
    url = "https://denstoreklimadatabase.dk/files/media/document/Downloadversion%201.2_ENG.xlsx"
    temp_file = DATA_DIR / 'bigclimatedb.xlsx'
    output_file = DATA_DIR / 'bigclimatedb.csv'

    SHEET_MAPPING = {
        "DK": "Denmark",
        "GB": "United Kingdom",
        "FR": "France",
        "NL": "Netherlands",
        "ES": "Spain"
    }

    COLUMNS_TO_KEEP = [
        "Name",
        "Category",
        "Total kg CO2-eq/kg",
        "Agriculture",
        "iLUC",
        "Food processing",
        "Packaging",
        "Transport",
        "Retail"
    ]

    try:
        print("Downloading BigClimateDB data...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(temp_file, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)

        print("Processing BigClimateDB data...")
        df_list = []
        for sheet, region in SHEET_MAPPING.items():
            df = pd.read_excel(temp_file, sheet_name=sheet, usecols=COLUMNS_TO_KEEP)
            df["region"] = region
            df_list.append(df)

        bigclimatedb = pd.concat(df_list, ignore_index=True)
        bigclimatedb.to_csv(output_file, index=False)
        os.remove(temp_file)
        print(f"Successfully saved {output_file}")
        return True

    except Exception as e:
        print(f"Error processing BigClimateDB data: {e}")
        if temp_file.exists():
            os.remove(temp_file)
        return False

def process_data():
    """Process all required data sources."""
    ensure_directories()
    success = True
    
    missing_bonsai_files = check_existing_bonsai_data()
    if missing_bonsai_files:
        try:
            print(f"Downloading missing BONSAI files: {', '.join(missing_bonsai_files)}")
            download_bonsai_data(missing_bonsai_files)
        except Exception as e:
            print(f"Error processing BONSAI data: {e}")
            success = False
    
    if check_existing_agribalyse_data():
        if not download_agribalyse_data():
            success = False
    
    if check_existing_bigclimate_data():
        if not download_bigclimate_data():
            success = False
    
    return success
