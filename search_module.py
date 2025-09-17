#search_module.py
import requests
import time
from typing import List, Dict, Any, Tuple
from config_manager import ConfigManager

class SearchModule:
    """Handles all search operations using Google Places API"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.api_key = config_manager.get_api_key('google_places')
        self.visited_place_ids = set()  # Avoid duplicates
        self.us_states = set(config_manager.get_us_states())
        
        # Get search parameters from config
        self.max_results = config_manager.get_max_results()
        self.tier_1_radius = config_manager.get('search.tier_1_radius', 50000)
        self.tier_2_radius = config_manager.get('search.tier_2_radius', 25000)
        
        print(f"✅ SearchModule initialized with {self.max_results} max results")
    
    def get_coordinates(self, city: str) -> Tuple[float, float]:
        """Get coordinates for a city"""
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geocode_params = {
            'address': city,
            'key': self.api_key
        }

        try:
            response = requests.get(geocode_url, params=geocode_params)
            data = response.json()

            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                return location['lat'], location['lng']
            else:
                print(f"Could not get coordinates for {city}: {data['status']}")
                return None, None
        except Exception as e:
            print(f"Error getting coordinates for {city}: {e}")
            return None, None
    
    def search_companies(self, city: str, keyword: str, radius: int = 50000) -> List[Dict[str, Any]]:
        """Search for companies in a city with a specific keyword"""
        lat, lng = self.get_coordinates(city)
        if not lat or not lng:
            return []

        places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        places_params = {
            'location': f"{lat},{lng}",
            'radius': radius,
            'type': 'establishment',
            'keyword': keyword,
            'key': self.api_key
        }

        try:
            response = requests.get(places_url, params=places_params)
            data = response.json()

            if data['status'] == 'OK':
                companies = []
                for place in data.get('results', []):
                    # Avoid duplicates
                    if place.get('place_id') not in self.visited_place_ids:
                        self.visited_place_ids.add(place.get('place_id'))

                        company_data = {
                            'name': place.get('name'),
                            'address': place.get('vicinity'),
                            'city': city,
                            'state': self.extract_state(place.get('vicinity', '')),
                            'keyword_used': keyword,
                            'types': ', '.join(place.get('types', [])),
                            'rating': place.get('rating'),
                            'user_ratings_total': place.get('user_ratings_total'),
                            'place_id': place.get('place_id'),
                            'price_level': place.get('price_level'),
                            'business_status': place.get('business_status')
                        }
                        companies.append(company_data)

                return companies
            else:
                print(f"Error searching {city} with keyword '{keyword}': {data['status']}")
                return []

        except Exception as e:
            print(f"Error searching {city} with keyword '{keyword}': {e}")
            return []
    
    def extract_state(self, address: str) -> str:
        """Extract state from address"""
        if not address:
            return ""

        words = address.upper().split()
        for word in words:
            if word in self.us_states:
                return word
        return ""
    
    def search_with_optimized_keywords(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Search with separate tracking of core vs peripheral results"""
        # Get all search parameters from config
        core_keywords = self.config.get_core_keywords()
        peripheral_keywords = self.config.get_peripheral_keywords()
        tier_1_cities = self.config.get_tier_1_cities()
        tier_2_cities = self.config.get_tier_2_cities()

        print("=== CORE ICP SEARCHES (High Value) ===")
        core_results = []
        for city in tier_1_cities:
            for keyword in core_keywords:
                companies = self.search_companies(city, keyword, radius=self.tier_1_radius)
                core_results.extend(companies)
                print(f"{city} - '{keyword}': {len(companies)} companies")
                if len(core_results) >= self.max_results:
                    print(f"\nTotal core ICP results: {len(core_results)}")
                    return core_results[:self.max_results], []

        print(f"\nTotal core ICP results: {len(core_results)}")

        print("\n=== PERIPHERAL SEARCHES (Size Indicators) ===")
        peripheral_results = []
        for city in tier_2_cities:
            for keyword in peripheral_keywords:
                companies = self.search_companies(city, keyword, radius=self.tier_2_radius)
                peripheral_results.extend(companies)
                print(f"{city} - '{keyword}': {len(companies)} companies")
                if len(core_results) + len(peripheral_results) >= self.max_results:
                    remaining = max(0, self.max_results - len(core_results))
                    print(f"\nTotal peripheral results: {len(peripheral_results)}")
                    return core_results, peripheral_results[:remaining]

        print(f"\nTotal peripheral results: {len(peripheral_results)}")
        return core_results, peripheral_results
    
    def search_comprehensive(self) -> List[Dict[str, Any]]:
        """Legacy comprehensive search method (if needed)"""
        cities = self.config.get('search.comprehensive_cities', [])
        keywords = self.config.get('search.comprehensive_keywords', [])
        
        all_companies = []
        total_searches = len(cities) * len(keywords)
        current_search = 0

        print(f"Starting comprehensive search across {len(cities)} cities and {len(keywords)} keywords")
        print(f"Total searches to perform: {total_searches}")

        for city in cities:
            for keyword in keywords:
                current_search += 1
                print(f"\nProgress: {current_search}/{total_searches}")
                print(f"Searching: {city} - '{keyword}'")

                companies = self.search_companies(city, keyword)
                all_companies.extend(companies)

                print(f"Found {len(companies)} new companies (Total: {len(all_companies)})")

                # Be respectful to the API - add delay
                time.sleep(0.5)

                # Stop if we have enough companies
                if len(all_companies) >= self.max_results:
                    print(f"\nReached target of {self.max_results}+ companies!")
                    break

            if len(all_companies) >= self.max_results:
                break

        return all_companies