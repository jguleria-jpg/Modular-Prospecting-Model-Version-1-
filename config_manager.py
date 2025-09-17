#Config_manager.py
import yaml
import os
from typing import Dict, Any, List

class ConfigManager:
    """Enhanced configuration manager with convenience methods"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        print(f"✅ Configuration loaded from {self.config_path}")
        return config
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation (e.g., 'api.google_places_key')"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    # Convenience methods for common config access
    def get_api_key(self, service: str) -> str:
        """Get API key for a specific service"""
        return self.get(f'api.{service}_key')
    
    def get_search_config(self) -> Dict[str, Any]:
        """Get search configuration"""
        return self.get('search', {})
    
    def get_filter_config(self) -> Dict[str, Any]:
        """Get filter configuration"""
        return self.get('filters', {})
    
    def get_scoring_config(self) -> Dict[str, Any]:
        """Get scoring configuration"""
        return self.get('scoring', {})
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Get AI configuration"""
        return self.get('ai', {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration"""
        return self.get('output', {})
    
    def get_us_states(self) -> List[str]:
        """Get list of US states"""
        return self.get('us_states', [])
    
    # Specific getters for commonly used values
    def get_max_results(self) -> int:
        """Get maximum results limit"""
        return self.get('search.max_results', 100)
    
    def get_core_keywords(self) -> List[str]:
        """Get core ICP keywords"""
        return self.get('search.core_icp_keywords', [])
    
    def get_peripheral_keywords(self) -> List[str]:
        """Get peripheral keywords"""
        return self.get('search.peripheral_keywords', [])
    
    def get_tier_1_cities(self) -> List[str]:
        """Get tier 1 cities"""
        return self.get('search.tier_1_cities', [])
    
    def get_tier_2_cities(self) -> List[str]:
        """Get tier 2 cities"""
        return self.get('search.tier_2_cities', [])
    
    def get_excluded_types(self) -> List[str]:
        """Get excluded business types"""
        return self.get('filters.excluded_types', [])
    
    def get_negative_keywords(self) -> List[str]:
        """Get negative keywords for filtering"""
        return self.get('filters.negative_keywords', [])
    
    def get_min_review_count(self) -> int:
        """Get minimum review count for filtering"""
        return self.get('filters.min_review_count', 3)
    
    def get_business_indicators(self) -> List[str]:
        """Get business indicators for website validation"""
        return self.get('filters.business_indicators', [])
    
    def get_precheck_delay(self) -> float:
        """Get AI pre-check delay"""
        return self.get('ai.precheck_delay', 0.3)
    
    def get_evaluation_delay(self) -> float:
        """Get AI evaluation delay"""
        return self.get('ai.evaluation_delay', 0.3)
    
    def get_precheck_max_tokens(self) -> int:
        """Get AI pre-check max tokens"""
        return self.get('ai.precheck_max_tokens', 10)
    
    def get_evaluation_max_tokens(self) -> int:
        """Get AI evaluation max tokens"""
        return self.get('ai.evaluation_max_tokens', 500)
    
    def get_site_excerpt_max_chars(self) -> int:
        """Get website excerpt max characters"""
        return self.get('ai.site_excerpt_max_chars', 1200)