"""Test script to investigate why 'tzatziki' doesn't find 'Tzatziki dip' in USDA search"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('USDA_API_KEY')

# Test 1: Check FDC ID 2705448 directly
print("=" * 80)
print("TEST 1: Check FDC ID 2705448 (Tzatziki dip) directly")
print("=" * 80)
response = requests.get(f'https://api.nal.usda.gov/fdc/v1/food/2705448', params={'api_key': api_key})
data = response.json()
print(f'Description: {data.get("description")}')
print(f'Data Type: {data.get("dataType")}')
print(f'Food Category: {data.get("foodCategory")}')

# Test 2: Search with "tzatziki" query (no filter)
print("\n" + "=" * 80)
print("TEST 2: Search 'tzatziki' (no data type filter)")
print("=" * 80)
response = requests.get('https://api.nal.usda.gov/fdc/v1/foods/search', 
                        params={'query': 'tzatziki', 'pageSize': 50, 'api_key': api_key})
data = response.json()
foods = data.get('foods', [])
print(f'Total results: {len(foods)}')
print('\nTop 15 results:')
for i, food in enumerate(foods[:15], 1):
    print(f'{i}. {food.get("description")} (FDC: {food.get("fdcId")}, Type: {food.get("dataType")})')

tzatziki_matches = [f for f in foods if 'tzatziki' in f.get('description', '').lower()]
print(f'\nTzatziki matches: {len(tzatziki_matches)}')
for f in tzatziki_matches:
    print(f'  - {f.get("description")} (FDC: {f.get("fdcId")}, Type: {f.get("dataType")})')

# Test 3: Search with "tzatziki sauce" query (no filter)
print("\n" + "=" * 80)
print("TEST 3: Search 'tzatziki sauce' (no data type filter)")
print("=" * 80)
response = requests.get('https://api.nal.usda.gov/fdc/v1/foods/search', 
                        params={'query': 'tzatziki sauce', 'pageSize': 50, 'api_key': api_key})
data = response.json()
foods = data.get('foods', [])
print(f'Total results: {len(foods)}')
print('\nTop 15 results:')
for i, food in enumerate(foods[:15], 1):
    print(f'{i}. {food.get("description")} (FDC: {food.get("fdcId")}, Type: {food.get("dataType")})')

tzatziki_matches = [f for f in foods if 'tzatziki' in f.get('description', '').lower()]
print(f'\nTzatziki matches: {len(tzatziki_matches)}')
for f in tzatziki_matches:
    print(f'  - {f.get("description")} (FDC: {f.get("fdcId")}, Type: {f.get("dataType")})')

# Test 4: Search with "tzatziki" query (Foundation,SR Legacy filter)
print("\n" + "=" * 80)
print("TEST 4: Search 'tzatziki' (Foundation,SR Legacy filter)")
print("=" * 80)
response = requests.get('https://api.nal.usda.gov/fdc/v1/foods/search', 
                        params={'query': 'tzatziki', 'pageSize': 50, 'dataType': 'Foundation,SR Legacy', 'api_key': api_key})
data = response.json()
foods = data.get('foods', [])
print(f'Total results: {len(foods)}')
if foods:
    print('\nTop 15 results:')
    for i, food in enumerate(foods[:15], 1):
        print(f'{i}. {food.get("description")} (FDC: {food.get("fdcId")}, Type: {food.get("dataType")})')
else:
    print("No results with Foundation,SR Legacy filter")

# Test 5: Search with "tzatziki sauce" query (Foundation,SR Legacy filter)
print("\n" + "=" * 80)
print("TEST 5: Search 'tzatziki sauce' (Foundation,SR Legacy filter)")
print("=" * 80)
response = requests.get('https://api.nal.usda.gov/fdc/v1/foods/search', 
                        params={'query': 'tzatziki sauce', 'pageSize': 50, 'dataType': 'Foundation,SR Legacy', 'api_key': api_key})
data = response.json()
foods = data.get('foods', [])
print(f'Total results: {len(foods)}')
if foods:
    print('\nTop 15 results:')
    for i, food in enumerate(foods[:15], 1):
        print(f'{i}. {food.get("description")} (FDC: {food.get("fdcId")}, Type: {food.get("dataType")})')
else:
    print("No results with Foundation,SR Legacy filter")

# Test 6: Check if FDC 2705448 appears in any search
print("\n" + "=" * 80)
print("TEST 6: Check if FDC 2705448 appears in search results")
print("=" * 80)
for query in ['tzatziki', 'tzatziki sauce', 'tzatziki dip']:
    response = requests.get('https://api.nal.usda.gov/fdc/v1/foods/search', 
                            params={'query': query, 'pageSize': 200, 'api_key': api_key})
    data = response.json()
    foods = data.get('foods', [])
    found = any(f.get('fdcId') == 2705448 for f in foods)
    position = next((i+1 for i, f in enumerate(foods) if f.get('fdcId') == 2705448), None)
    print(f"Query '{query}': Found={found}, Position={position}")
