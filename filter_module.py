# filter_module.py
import requests
import time
import re
from typing import List, Dict, Any
from config_manager import ConfigManager

class FilterModule:
    """Handles all filtering operations"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.api_key = config_manager.get_api_key('google_places')
        self.filter_config = config_manager.get_filter_config()
        self.scoring_config = config_manager.get_scoring_config()
        self.us_states = set(config_manager.get_us_states())
        
        print("✅ FilterModule initialized")
    
    def _to_float(self, v, default=0.0):
        """Convert value to float, handling None and string values"""
        try:
            return float(v)
        except (TypeError, ValueError):
            return default
    
    def filter_noise(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove unwanted businesses"""
        excluded_types = self.config.get_excluded_types()
        negative_keywords = self.config.get_negative_keywords()
        min_review_count = self.config.get_min_review_count()

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

            # Check minimum reviews (FIXED: Handle None values)
            review_count = self._to_float(company.get('user_ratings_total'), 0.0)
            if review_count < min_review_count:
                should_exclude = True

            if should_exclude:
                excluded_count += 1
            else:
                filtered_companies.append(company)

        print(f"Filtered out {excluded_count} irrelevant businesses")
        print(f"Remaining companies: {len(filtered_companies)}")

        return filtered_companies
    
    def validate_website(self, website: str, company_name: str) -> bool:
        """Validate that website is accessible and business-related"""
        business_indicators = self.config.get_business_indicators()
        
        try:
            # Check if website is accessible
            response = requests.get(website, timeout=10)

            if response.status_code == 200:
                content = response.text.lower()

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
    
    def filter_websites_required(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    
    def filter_by_icp_criteria(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter companies based on ICP criteria"""
        filtered_companies = []
        icp_weights = self.scoring_config.get('icp_weights', {})
        min_icp_score = self.scoring_config.get('min_icp_score', 2)

        for company in companies:
            score = 0

            # Location filter (US only)
            if company.get('state') in self.us_states:
                score += icp_weights.get('us_location', 1)

            # Rating filter (quality indicator) - FIXED: Handle None values
            rating = company.get('rating')
            if rating is not None:
                rating_float = self._to_float(rating, 0.0)
                if rating_float >= 3.5:
                    score += icp_weights.get('high_rating', 1)
                elif rating_float >= 3.0:
                    score += icp_weights.get('good_rating', 0.5)

            # Business type indicators (small business keywords)
            business_types = company.get('types', '').lower()
            if any(keyword in business_types for keyword in ['establishment', 'business']):
                score += icp_weights.get('business_type', 1)

            # Keyword match (higher score for industry-specific keywords)
            keyword_used = company.get('keyword_used', '').lower()
            if any(industry in keyword_used for industry in ['medical', 'manufacturing', 'defense', 'consulting']):
                score += icp_weights.get('industry_keyword', 2)
            elif any(size in keyword_used for size in ['small', 'startup', 'boutique', 'specialized']):
                score += icp_weights.get('size_keyword', 1)

            # Only include companies that meet minimum criteria
            if score >= min_icp_score:
                company['icp_score'] = score
                filtered_companies.append(company)

        return filtered_companies
    
    def calculate_website_required_score(self, company: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate ICP score (website is now a requirement, not bonus)"""
        score = 0
        score_breakdown = {}
        
        # Get scoring weights from config
        weights = self.scoring_config.get('website_required_weights', {})
        rating_thresholds = self.scoring_config.get('rating_thresholds', {})

        # Industry match (core ICP keyword) → +3 points
        keyword_used = company.get('keyword_used', '').lower()
        core_keywords = ['medical', 'manufacturing', 'defense', 'consulting', 'engineering', 'biotech']
        if any(core in keyword_used for core in core_keywords):
            score += weights.get('industry_match', 3)
            score_breakdown['industry_match'] = weights.get('industry_match', 3)

        # Website exists (REQUIRED) → +2 points
        if company.get('website_valid'):
            score += weights.get('website_required', 2)
            score_breakdown['website_required'] = weights.get('website_required', 2)

        # Google rating ≥3.5 with ≥10 reviews → +2 points
        rating = self._to_float(company.get('rating'), 0.0)
        reviews = int(self._to_float(company.get('user_ratings_total'), 0.0))
        high_rating_threshold = rating_thresholds.get('high_rating', 3.5)
        high_reviews_threshold = rating_thresholds.get('high_reviews', 10)
        good_rating_threshold = rating_thresholds.get('good_rating', 3.0)
        good_reviews_threshold = rating_thresholds.get('good_reviews', 5)
        
        if rating >= high_rating_threshold and reviews >= high_reviews_threshold:
            score += weights.get('high_rating', 2)
            score_breakdown['high_rating'] = weights.get('high_rating', 2)
        elif rating >= good_rating_threshold and reviews >= good_reviews_threshold:
            score += weights.get('good_rating', 1)
            score_breakdown['good_rating'] = 1

        # Peripheral keyword (size indicators) → +1 point
        size_keywords = ['small', 'boutique', 'specialized', 'startup', 'family-owned']
        if any(size in keyword_used for size in size_keywords):
            score += weights.get('size_indicator', 1)
            score_breakdown['size_indicator'] = weights.get('size_indicator', 1)

        # Location = US target states → +1 point
        if company.get('state') in self.us_states:
            score += weights.get('us_location', 1)
            score_breakdown['us_location'] = weights.get('us_location', 1)

        # Business type validation → +1 point
        business_types = company.get('types', '').lower()
        if 'establishment' in business_types and 'business' in business_types:
            score += weights.get('business_type', 1)
            score_breakdown['business_type'] = weights.get('business_type', 1)

        company['website_required_score'] = score
        company['score_breakdown'] = score_breakdown

        return company
    
    def categorize_by_website_required_fit(self, companies: List[Dict[str, Any]]) -> tuple:
        """Categorize companies by fit (all have websites)"""
        high_fit = []
        medium_fit = []
        low_fit = []
        
        # Get fit thresholds from config
        fit_thresholds = self.scoring_config.get('fit_thresholds', {})
        high_fit_threshold = fit_thresholds.get('high_fit', 7)
        medium_fit_threshold = fit_thresholds.get('medium_fit', 5)
        low_fit_threshold = fit_thresholds.get('low_fit', 3)

        for company in companies:
            score = company.get('website_required_score', 0)

            if score >= high_fit_threshold:
                company['fit_category'] = 'High Fit'
                high_fit.append(company)
            elif score >= medium_fit_threshold:
                company['fit_category'] = 'Medium Fit'
                medium_fit.append(company)
            elif score >= low_fit_threshold:
                company['fit_category'] = 'Low Fit'
                low_fit.append(company)
            # Score < low_fit_threshold gets dropped

        print(f"High Fit: {len(high_fit)} companies")
        print(f"Medium Fit: {len(medium_fit)} companies")
        print(f"Low Fit: {len(low_fit)} companies")

        return high_fit, medium_fit, low_fit