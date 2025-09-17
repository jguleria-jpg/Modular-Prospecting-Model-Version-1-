# modular_prospecting_model.py
from typing import List, Dict, Any
from config_manager import ConfigManager
from search_module import SearchModule
from filter_module import FilterModule
from ai_module import AIModule
from output_module import OutputModule

class ModularProspectingModel:
    """Modular version of the prospecting model with configuration support"""
    
    def __init__(self, config_path: str = "config.yaml"):
        # Initialize configuration manager
        self.config_manager = ConfigManager(config_path)
        
        # Initialize modules
        self.search_module = SearchModule(self.config_manager)
        self.filter_module = FilterModule(self.config_manager)
        self.ai_module = AIModule(self.config_manager)
        self.output_module = OutputModule(self.config_manager)
        
        print("✅ Modular Prospecting Model initialized")
        print(f"📊 Max results: {self.config_manager.get_max_results()}")
        print(f"🔍 Core keywords: {len(self.config_manager.get_core_keywords())}")
        print(f"🏙️ Tier 1 cities: {len(self.config_manager.get_tier_1_cities())}")

    def run_refined_pipeline(self) -> List[Dict[str, Any]]:
        """Get coordinates for a city"""
        geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
        geocode_params = {
            'address': city,
            'key': self.api_key
        }

        response = requests.get(geocode_url, params=geocode_params)
        data = response.json()

        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            print(f"Could not get coordinates for {city}: {data['status']}")
            return None, None

    # NEW: Get optimized keywords for better targeting
    def get_optimized_keywords(self):
        """Get optimized keywords for better targeting"""

        # Core ICP keywords (high value, direct industry match)
        core_icp_keywords = [
            'medical device', 'manufacturing', 'defense contractor',
            'biotech', 'biotechnology', 'consulting services',
            'professional services', 'engineering services',
            'technical services', 'aerospace', 'healthcare technology',
            'defense systems', 'military technology', 'precision manufacturing'
        ]

        # Peripheral keywords (size indicators, lower value)
        peripheral_keywords = [
            'small business', 'boutique', 'family-owned',
            'specialized consulting', 'IT services', 'software development',
            'local business', 'startup', 'SMB', 'independent business',
            'boutique consulting', 'specialized services'
        ]

        return core_icp_keywords, peripheral_keywords

    # NEW: Get tiered cities for different search strategies
    def get_tiered_cities(self):
        """Get cities with different search strategies"""

        # Tier 1: Major metros (50km radius)
        tier_1_cities = [
            "New York, NY", "Los Angeles, CA", "Chicago, IL",
            "Houston, TX", "Phoenix, AZ", "Philadelphia, PA",
            "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA"
        ]

        # Tier 2: Second-tier BD-friendly markets (25km radius)
        tier_2_cities = [
            "Raleigh, NC", "Salt Lake City, UT", "Austin, TX",
            "Pittsburgh, PA", "Kansas City, MO", "Nashville, TN",
            "Charlotte, NC", "Denver, CO", "Portland, OR",
            "Minneapolis, MN", "Cleveland, OH", "Cincinnati, OH"
        ]

        return tier_1_cities, tier_2_cities

    # NEW: Get exclusion filters for noise filtering
    def get_exclusion_filters(self):
        """Define what businesses to exclude"""

        # Business types to exclude (Google Places types)
        excluded_types = [
            'restaurant', 'bar', 'gym', 'hotel', 'salon',
            'retail', 'grocery', 'daycare', 'real_estate',
            'auto_repair', 'spa', 'beauty_salon', 'car_dealer',
            'gas_station', 'pharmacy', 'bank', 'insurance_agency',
            'lawyer', 'dentist', 'doctor', 'hospital', 'clinic'
        ]

        # Keywords in company names to exclude
        negative_keywords = [
            'restaurant', 'cafe', 'bar', 'gym', 'hotel', 'motel',
            'salon', 'spa', 'retail', 'store', 'shop', 'grocery',
            'supermarket', 'daycare', 'childcare', 'real estate',
            'auto repair', 'car dealer', 'gas station', 'pharmacy',
            'bank', 'insurance', 'law firm', 'dental', 'medical center'
        ]

        return excluded_types, negative_keywords

    def search_companies(self, city, keyword, radius=50000):
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

    def extract_state(self, address):
        """Extract state from address"""
        if not address:
            return ""

        words = address.upper().split()
        for word in words:
            if word in self.us_states:
                return word
        return ""

    # NEW: Noise filtering function
    def filter_noise(self, companies):
        """Remove unwanted businesses"""
        excluded_types, negative_keywords = self.get_exclusion_filters()

        filtered_companies = []
        excluded_count = 0

        for company in companies:
            should_exclude = False

            # Check business types
            company_types = company.get('types', '').lower()
            if any(excluded_type in company_types for excluded_type in excluded_types):
                should_exclude = True

            # Check company name
            company_name = company.get('name', '').lower()
            if any(negative_keyword in company_name for negative_keyword in negative_keywords):
                should_exclude = True

            # Check minimum reviews (optional)
            review_count = self._to_float(company.get('user_ratings_total'), 0.0)
            if review_count < 3:
                should_exclude = True

            if should_exclude:
                excluded_count += 1
            else:
                filtered_companies.append(company)

        print(f"Filtered out {excluded_count} irrelevant businesses")
        print(f"Remaining companies: {len(filtered_companies)}")

        return filtered_companies

    # NEW: Website requirement filter
    def filter_websites_required(self, companies):
        """Only include companies with valid websites"""

        companies_with_websites = []
        excluded_count = 0

        print("=== WEBSITE REQUIREMENT FILTER ===")

        for company in companies:
            place_id = company.get('place_id')
            if not place_id:
                excluded_count += 1
                continue

            try:
                # Get website using Google Places Details API
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_params = {
                    'place_id': place_id,
                    'fields': 'website,formatted_phone_number,types',
                    'key': self.api_key
                }

                response = requests.get(details_url, params=details_params)
                details_data = response.json()

                if details_data['status'] == 'OK':
                    result = details_data['result']
                    website = result.get('website')

                    if website:
                        # Validate website is accessible and business-related
                        if self.validate_website(website, company['name']):
                            company['website'] = website
                            company['phone'] = result.get('formatted_phone_number')
                            company['website_valid'] = True
                            companies_with_websites.append(company)
                            print(f"✅ {company['name']}: {website}")
                        else:
                            excluded_count += 1
                            print(f"❌ {company['name']}: Invalid website")
                    else:
                        excluded_count += 1
                        print(f"❌ {company['name']}: No website")
                else:
                    excluded_count += 1
                    print(f"❌ {company['name']}: API error")

                # Be respectful to API
                time.sleep(0.1)

            except Exception as e:
                excluded_count += 1
                print(f"❌ {company['name']}: Error - {e}")
                continue

        print(f"\nWebsite requirement results:")
        print(f"✅ Companies with valid websites: {len(companies_with_websites)}")
        print(f"❌ Companies excluded: {excluded_count}")

        return companies_with_websites

    # NEW: Website validation function
    def validate_website(self, website, company_name):
        """Validate that website is accessible and business-related"""

        try:
            # Check if website is accessible
            response = requests.get(website, timeout=10)

            if response.status_code == 200:
                content = response.text.lower()

                # Look for business-related keywords
                business_indicators = [
                    'about us', 'company', 'business', 'services',
                    'contact', 'team', 'professional', 'consulting',
                    'manufacturing', 'medical', 'technology', 'solutions'
                ]

                # Check if content contains business indicators
                has_business_content = any(indicator in content for indicator in business_indicators)

                if has_business_content:
                    return True
                else:
                    print(f"   ⚠️ Website exists but not business-focused")
                    return False
            else:
                print(f"   ⚠️ Website inaccessible (status: {response.status_code})")
                return False

        except Exception as e:
            print(f"   ⚠️ Website validation error: {e}")
            return False

    def _fetch_site_excerpt(self, url, max_chars=1200):
        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                return None
            text = r.text
            text = re.sub(r'<script[\s\S]*?</script>', ' ', text, flags=re.I)
            text = re.sub(r'<style[\s\S]*?</style>', ' ', text, flags=re.I)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return text[:max_chars]
        except Exception:
            return None

    def _parse_ai_score(self, text):
        try:
            if not text:
                return None
            m = re.search(r'(?i)prospect\s*score\s*[:\-]?\s*(\d{1,2})', text)
            if m:
                val = max(1, min(int(m.group(1)), 10))
                return val
            m2 = re.search(r'\b(\d{1,2})\s*/\s*10\b', text)
            if m2:
                val = max(1, min(int(m2.group(1)), 10))
                return val
        except:
            pass
        return None

    def _parse_ai_category(self, text):
        t = (text or "").lower()
        if "high" in t:
            return "High"
        if "medium" in t:
            return "Medium"
        if "low" in t:
            return "Low"
        return None

    def _parse_ai_evaluation_fields(self, text):
        """Parse the structured AI evaluation response into separate fields"""
        if not text:
            return {}
        
        fields = {}
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Parse ai_fit_category: High/Medium/Low with justification
            if line.startswith('ai_fit_category:'):
                content = line.replace('ai_fit_category:', '').strip()
                if 'High' in content:
                    fields['ai_fit_category'] = 'High'
                elif 'Medium' in content:
                    fields['ai_fit_category'] = 'Medium'
                elif 'Low' in content:
                    fields['ai_fit_category'] = 'Low'
                else:
                    fields['ai_fit_category'] = 'Unknown'
            
            # Parse ai_reasoning: Yes/No with explanation
            elif line.startswith('ai_reasoning:'):
                content = line.replace('ai_reasoning:', '').strip()
                fields['ai_reasoning'] = content
            
            # Parse ai_people_assessment: leadership/hiring signals or "Not enough data"
            elif line.startswith('ai_people_assessment:'):
                content = line.replace('ai_people_assessment:', '').strip()
                fields['ai_people_assessment'] = content
            
            # Parse ai_revenue_assessment: Early-stage/Small/Mid/Large/Unknown
            elif line.startswith('ai_revenue_assessment:'):
                content = line.replace('ai_revenue_assessment:', '').strip()
                fields['ai_revenue_assessment'] = content
        
        # Ensure all required fields are present with defaults
        if 'ai_fit_category' not in fields:
            fields['ai_fit_category'] = 'Unknown'
        if 'ai_reasoning' not in fields:
            fields['ai_reasoning'] = 'Not evaluated'
        if 'ai_people_assessment' not in fields:
            fields['ai_people_assessment'] = 'Not enough data'
        if 'ai_revenue_assessment' not in fields:
            fields['ai_revenue_assessment'] = 'Unknown'
        
        return fields

    def ai_precheck(self, companies, openai_api_key, delay=0.6):
        """AI Pre-check to filter companies with reliable business info"""
        ai = OpenAI_Class(openai_api_key)
        passed_companies = []
        
        print("=== AI PRE-CHECK ===")
        print("Filtering companies with reliable business information...")
        
        for i, company in enumerate(companies):
            try:
                prompt = build_precheck_prompt(company)
                response = ai.run_prompt(prompt, system_role="You are a B2B sales expert evaluating business information quality.", max_tokens=10)
                
                if response.strip().lower().startswith('yes'):
                    passed_companies.append(company)
                    print(f"✅ {company.get('name')}: Passed pre-check")
                else:
                    print(f"❌ {company.get('name')}: Failed pre-check")
                
                if delay:
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"❌ {company.get('name')}: Pre-check error - {e}")
                continue
        
        print(f"\nPre-check results: {len(passed_companies)}/{len(companies)} companies passed")
        return passed_companies

    # NEW: Enhanced ICP scoring with website requirement
    def calculate_website_required_score(self, company):
        """Calculate ICP score (website is now a requirement, not bonus)"""

        score = 0
        score_breakdown = {}

        # Industry match (core ICP keyword) → +3 points
        keyword_used = company.get('keyword_used', '').lower()
        core_keywords = ['medical', 'manufacturing', 'defense', 'consulting', 'engineering', 'biotech']
        if any(core in keyword_used for core in core_keywords):
            score += 3
            score_breakdown['industry_match'] = 3

        # Website exists (REQUIRED) → +2 points
        if company.get('website_valid'):
            score += 2
            score_breakdown['website_required'] = 2

        # Google rating ≥3.5 with ≥10 reviews → +2 points
        rating = self._to_float(company.get('rating'), 0.0)
        reviews = int(self._to_float(company.get('user_ratings_total'), 0.0))
        if rating >= 3.5 and reviews >= 10:
            score += 2
            score_breakdown['high_rating'] = 2
        elif rating >= 3.0 and reviews >= 5:
            score += 1
            score_breakdown['good_rating'] = 1

        # Peripheral keyword (size indicators) → +1 point
        size_keywords = ['small', 'boutique', 'specialized', 'startup', 'family-owned']
        if any(size in keyword_used for size in size_keywords):
            score += 1
            score_breakdown['size_indicator'] = 1

        # Location = US target states → +1 point
        if company.get('state') in self.us_states:
            score += 1
            score_breakdown['us_location'] = 1

        # Business type validation → +1 point
        business_types = company.get('types', '').lower()
        if 'establishment' in business_types and 'business' in business_types:
            score += 1
            score_breakdown['business_type'] = 1

        company['website_required_score'] = score
        company['score_breakdown'] = score_breakdown

        return company

    # NEW: Categorize by website required fit
    def categorize_by_website_required_fit(self, companies):
        """Categorize companies by fit (all have websites)"""

        high_fit = []
        medium_fit = []
        low_fit = []

        for company in companies:
            score = company.get('website_required_score', 0)

            if score >= 7:  # Higher threshold since website is guaranteed
                company['fit_category'] = 'High Fit'
                high_fit.append(company)
            elif score >= 5:
                company['fit_category'] = 'Medium Fit'
                medium_fit.append(company)
            elif score >= 3:
                company['fit_category'] = 'Low Fit'
                low_fit.append(company)
            # Score < 3 gets dropped

        print(f"High Fit: {len(high_fit)} companies")
        print(f"Medium Fit: {len(medium_fit)} companies")
        print(f"Low Fit: {len(low_fit)} companies")

        return high_fit, medium_fit, low_fit

    # NEW: Search with optimized keywords
    def search_with_optimized_keywords(self):
        """Search with separate tracking of core vs peripheral results"""

        core_keywords, peripheral_keywords = self.get_optimized_keywords()
        tier_1_cities, tier_2_cities = self.get_tiered_cities()

        print("=== CORE ICP SEARCHES (High Value) ===")
        core_results = []
        for city in tier_1_cities:
            for keyword in core_keywords:
                companies = self.search_companies(city, keyword, radius=50000)
                core_results.extend(companies)
                print(f"{city} - '{keyword}': {len(companies)} companies")
                if len(core_results) >= MAX_RESULTS:
                    print(f"\nTotal core ICP results: {len(core_results)}")
                    return core_results[:MAX_RESULTS], []
                # time.sleep(0.5)  # optional: comment/remove for speed

        print(f"\nTotal core ICP results: {len(core_results)}")

        print("\n=== PERIPHERAL SEARCHES (Size Indicators) ===")
        peripheral_results = []
        for city in tier_2_cities:
            for keyword in peripheral_keywords:
                companies = self.search_companies(city, keyword, radius=25000)
                peripheral_results.extend(companies)
                print(f"{city} - '{keyword}': {len(companies)} companies")
                if len(core_results) + len(peripheral_results) >= MAX_RESULTS:
                    remaining = max(0, MAX_RESULTS - len(core_results))
                    print(f"\nTotal peripheral results: {len(peripheral_results)}")
                    return core_results, peripheral_results[:remaining]
                # time.sleep(0.5)  # optional

        print(f"\nTotal peripheral results: {len(peripheral_results)}")
        return core_results, peripheral_results

    def get_comprehensive_results(self):
        """Get companies from multiple cities and keywords"""

        # Major US cities
        cities = [
            "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
            "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA",
            "Austin, TX", "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "Charlotte, NC",
            "San Francisco, CA", "Indianapolis, IN", "Seattle, WA", "Denver, CO", "Boston, MA",
            "Nashville, TN", "Detroit, MI", "Portland, OR", "Memphis, TN", "Oklahoma City, OK",
            "Las Vegas, NV", "Louisville, KY", "Baltimore, MD", "Milwaukee, WI", "Albuquerque, NM"
        ]

        # Comprehensive keyword list based on your ICP
        keywords = [
            # Business size indicators
            'small business', 'startup', 'SMB', 'small company', 'local business',
            'family business', 'independent business', 'boutique', 'specialized',

            # Industry-specific (based on your ICP)
            'medical device', 'manufacturing', 'defense contractor', 'military contractor',
            'biotechnology', 'healthcare technology', 'aerospace', 'consulting services',
            'professional services', 'engineering services', 'technical services',

            # Employee size indicators
            'boutique consulting', 'specialized consulting', 'expert services',
            'niche services', 'specialist', 'consultant', 'advisory services',

            # Additional business types
            'software development', 'IT services', 'business services',
            'management consulting', 'strategy consulting', 'operations consulting'
        ]

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
                self.all_companies.extend(companies)

                print(f"Found {len(companies)} new companies (Total: {len(self.all_companies)})")

                # Be respectful to the API - add delay
                time.sleep(0.5)

                # Stop if we have enough companies
                if len(self.all_companies) >= 100:
                    print(f"\nReached target of 100+ companies!")
                    break

            if len(self.all_companies) >= 100:
                break

        return self.all_companies

    def filter_by_icp_criteria(self, companies):
        """Filter companies based on your ICP criteria"""
        filtered_companies = []

        for company in companies:
            # Filter criteria based on your ICP
            score = 0

            # Location filter (US only)
            if company.get('state') in self.us_states:
                score += 1

            # Rating filter (quality indicator) - FIXED: Handle None values
            rating = company.get('rating')
            if rating is not None:
                rating_float = self._to_float(rating, 0.0)
                if rating_float >= 3.5:
                    score += 1
                elif rating_float >= 3.0:
                    score += 0.5

            # Business type indicators (small business keywords)
            business_types = company.get('types', '').lower()
            if any(keyword in business_types for keyword in ['establishment', 'business']):
                score += 1

            # Keyword match (higher score for industry-specific keywords)
            keyword_used = company.get('keyword_used', '').lower()
            if any(industry in keyword_used for industry in ['medical', 'manufacturing', 'defense', 'consulting']):
                score += 2
            elif any(size in keyword_used for size in ['small', 'startup', 'boutique', 'specialized']):
                score += 1

            # Only include companies that meet minimum criteria
            if score >= 2:
                company['icp_score'] = score
                filtered_companies.append(company)

        return filtered_companies

    def save_results(self, companies, filename_prefix="prospecting_results"):
        """Save results to CSV with exact schema requirements"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if companies:
            # Define the exact schema columns in order
            schema_columns = [
                'place_id', 'name', 'address', 'city', 'state', 'keywords', 'types', 
                'rating', 'website', 'phone', 'ai_evaluation', 'ai_fit_category', 
                'ai_reasoning', 'ai_people_assessment', 'ai_revenue_assessment'
            ]
            
            # Create DataFrame with exact schema
            filtered_data = []
            for company in companies:
                filtered_company = {}
                
                # Map fields to schema
                filtered_company['place_id'] = company.get('place_id', None)
                filtered_company['name'] = company.get('name', None)
                filtered_company['address'] = company.get('address', None)
                filtered_company['city'] = company.get('city', None)
                filtered_company['state'] = company.get('state', None)
                filtered_company['keywords'] = company.get('keyword_used', None)  # Map keyword_used to keywords
                filtered_company['types'] = company.get('types', None)
                filtered_company['rating'] = company.get('rating', None)
                filtered_company['website'] = company.get('website', None)
                filtered_company['phone'] = company.get('phone', None)
                filtered_company['ai_evaluation'] = company.get('ai_evaluation', None)
                filtered_company['ai_fit_category'] = company.get('ai_fit_category', None)
                filtered_company['ai_reasoning'] = company.get('ai_reasoning', None)
                filtered_company['ai_people_assessment'] = company.get('ai_people_assessment', None)
                filtered_company['ai_revenue_assessment'] = company.get('ai_revenue_assessment', None)
                
                filtered_data.append(filtered_company)
            
            df = pd.DataFrame(filtered_data)

            # Sort by ai_fit_category (Yes – direct fit, Maybe – partial fit, No – not a fit) and then by rating
            category_order = {'Yes – direct fit': 3, 'Maybe – partial fit': 2, 'No – not a fit': 1}
            df['sort_order'] = df['ai_fit_category'].map(category_order).fillna(0)
            df = df.sort_values(['sort_order', 'rating'], ascending=[False, False])
            df = df.drop('sort_order', axis=1)

            # Get the current working directory (your environment folder)
            current_dir = os.getcwd()

            # Save to CSV in the current directory
            csv_file = os.path.join(current_dir, f"{filename_prefix}_{timestamp}.csv")
            df.to_csv(csv_file, index=False)

            print(f"\nResults saved to: {csv_file}")
            print(f"Current working directory: {current_dir}")
            print(f"Total companies found: {len(companies)}")
            print(f"Schema columns: {list(df.columns)}")
            print(f"Sample data:\n{df.head()}")

            # Summary statistics
            print(f"\n=== Summary Statistics ===")
            print(f"Companies by state:")
            print(df['state'].value_counts().head(10))

            print(f"\nTop keywords that found companies:")
            print(df['keywords'].value_counts().head(10))

            print(f"\nFit categories:")
            print(df['ai_fit_category'].value_counts())

            print(f"\nRevenue assessments:")
            print(df['ai_revenue_assessment'].value_counts())

            print(f"\nPeople assessments:")
            print(df['ai_people_assessment'].value_counts())

            if 'rating' in df.columns:
                print(f"\nAverage rating: {df['rating'].mean():.2f}")

            return csv_file
        else:
            print("No companies to save")
            return None

    # NEW: Run refined pipeline with all new features
    def run_refined_pipeline(self):
        """Run the complete refined prospecting pipeline following the specified flow"""

        print("=== REFINED PROSPECTING MODEL v3 ===")
        print("Flow: Search → Noise Filter → AI Pre-check → AI Evaluation → Website Validation → Save")

        try:
            # 1. Search with optimized keywords
            print("\n1. Searching with optimized keywords...")
            core_results, peripheral_results = self.search_with_optimized_keywords()
            all_companies = (core_results + peripheral_results)[:MAX_RESULTS]
            
            if not all_companies:
                print("❌ No companies found in initial search!")
                return []

            # 2. Apply noise filtering
            print("\n2. Applying noise filtering...")
            filtered_companies = self.filter_noise(all_companies)
            print(f"After noise filtering: {len(filtered_companies)} companies")
            
            if len(filtered_companies) == 0:
                print("❌ No companies passed noise filtering!")
                return []

            # 3. AI Pre-check
            print("\n3. AI Pre-check...")
            openai_key = "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"
            precheck_companies = self.ai_precheck(filtered_companies, openai_key, delay=0.3)
            
            if len(precheck_companies) == 0:
                print("❌ No companies passed AI pre-check!")
                return []

            # 4. AI Evaluation
            print("\n4. AI Evaluation...")
            evaluated_companies = self.add_ai_evaluation(precheck_companies, openai_key, cap=len(precheck_companies), delay=0.3)
            
            if len(evaluated_companies) == 0:
                print("❌ No companies were evaluated!")
                return []

            # 5. Optional Website Validation (on top 20 companies only)
            print("\n5. Optional Website Validation (top 20 companies)...")
            # Sort by fit category (High, Medium, Low) and take top 20
            category_order = {'High': 3, 'Medium': 2, 'Low': 1, 'Unknown': 0}
            evaluated_companies.sort(key=lambda x: (category_order.get(x.get('ai_fit_category', 'Unknown'), 0), x.get('rating', 0)), reverse=True)
            top_companies = evaluated_companies[:20]
            
            # Try to get websites for top companies
            companies_with_websites = self.filter_websites_required(top_companies)
            
            if len(companies_with_websites) > 0:
                print(f"✅ Found {len(companies_with_websites)} companies with valid websites")
                final_companies = companies_with_websites
            else:
                print("⚠️ No companies passed website validation, using evaluated companies without websites")
                final_companies = top_companies

            # 6. Save results
            print("\n6. Saving results...")
            csv_file = self.save_results(final_companies, "refined_prospecting_results")

            print(f"\n=== PIPELINE COMPLETE ===")
            print(f"Final results saved to: {csv_file}")
            print(f"Total companies: {len(final_companies)}")
            
            # Print summary of AI evaluation fields
            if final_companies:
                print(f"\n=== AI EVALUATION SUMMARY ===")
                high_fit = [c for c in final_companies if c.get('ai_fit_category') == 'High']
                medium_fit = [c for c in final_companies if c.get('ai_fit_category') == 'Medium']
                low_fit = [c for c in final_companies if c.get('ai_fit_category') == 'Low']
                
                print(f"High Fit: {len(high_fit)} companies")
                print(f"Medium Fit: {len(medium_fit)} companies")
                print(f"Low Fit: {len(low_fit)} companies")
                
                avg_score = sum(c.get('ai_prospect_score', 0) for c in final_companies) / len(final_companies)
                print(f"Average Prospect Score: {avg_score:.1f}")

            return final_companies

        except Exception as e:
            print(f"❌ Pipeline failed with error: {e}")
            return []

    def add_ai_evaluation(self, companies, openai_api_key, cap=100, delay=0.6):
        """AI Evaluation with structured fields"""
        ai = OpenAI_Class(openai_api_key)
        enriched = []
        
        print("=== AI EVALUATION ===")
        print("Evaluating companies with structured assessment...")
        
        for i, c in enumerate(companies[:cap]):
            try:
                site_excerpt = self._fetch_site_excerpt(c.get('website')) if c.get('website') else None
                prompt = build_evaluation_prompt(c, site_excerpt)
                ai_text = ai.run_prompt(prompt, system_role="You are a B2B sales expert for regulated industries.", max_tokens=500)
                
                # Store the full AI evaluation text
                c['ai_evaluation'] = ai_text
                
                # Parse structured fields
                parsed_fields = self._parse_ai_evaluation_fields(ai_text)
                c.update(parsed_fields)
                
                enriched.append(c)
                print(f"✅ {c.get('name')}: {c.get('ai_fit_category', 'Unknown')} fit, {c.get('ai_revenue_assessment', 'Unknown')} revenue")
                
                if delay:
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"❌ {c.get('name')}: Evaluation error - {e}")
                # Still add the company but with default values
                c['ai_evaluation'] = f"Error: {e}"
                c['ai_fit_category'] = 'Unknown'
                c['ai_reasoning'] = 'Evaluation failed'
                c['ai_people_assessment'] = 'Not available'
                c['ai_revenue_assessment'] = 'Unknown'
                enriched.append(c)
                continue
        
        print(f"\nAI Evaluation complete: {len(enriched)} companies evaluated")
        return enriched

    def _to_float(self, v, default=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return default


def main():
    """Run the comprehensive prospecting model"""
    api_key = 'AIzaSyDbnaots9JE1FPSdq46V7Io0awtiDqZJgc'

    print("=== Comprehensive Prospecting Model ===")
    print("Target: <= 100 companies matching ICP criteria")
    print("ICP Criteria: US-based, small businesses, medical/manufacturing/consulting focus")

    model = ComprehensiveProspectingModel(api_key)

    # Always run refined pipeline
    results = model.run_refined_pipeline()


if __name__ == "__main__":
    main()
    

