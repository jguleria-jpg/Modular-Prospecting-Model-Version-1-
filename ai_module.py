# ai_module.py
import time
import re
import requests
from typing import List, Dict, Any
from openai import OpenAI
from config_manager import ConfigManager

class AIModule:
    """Handles all AI evaluation operations"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.api_key = config_manager.get_api_key('openai')
        self.default_model = config_manager.get('api.default_model', 'gpt-4o-mini')
        self.client = OpenAI(api_key=self.api_key)
        self.ai_config = config_manager.get_ai_config()
        
        print("✅ AIModule initialized")
    
    def run_prompt(self, prompt: str, model: str = None, system_role: str = 'helpful assistant', max_tokens: int = 300) -> str:
        """Run a prompt through OpenAI API"""
        model = model or self.default_model
        resp = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt},
            ],
            max_tokens=max_tokens
        )
        return str(resp.choices[0].message.content)
    
    def build_precheck_prompt(self, company: Dict[str, Any]) -> str:
        """Build prompt for AI Pre-check"""
        return f"""
Evaluate if this company has reliable business information for B2B prospecting.

Company:
- Name: {company.get('name')}
- City/State: {company.get('city')}, {company.get('state')}
- Keyword/Industry signal: {company.get('keyword_used')}
- Google rating/reviews: {company.get('rating')} ({company.get('user_ratings_total')})
- Types: {company.get('types')}

Does this company have reliable business information for B2B sales prospecting?

Answer with only "Yes" or "No".
""".strip()
    
    def build_evaluation_prompt(self, company: Dict[str, Any], site_excerpt: str = None) -> str:
        """Build prompt for AI Evaluation"""
        return f"""
Evaluate this company as a prospect for compliance-driven, mission/safety-critical software services.

Reference: PSI Software (medical devices, defense, industrial automation; embedded/real-time; FDA/MIL-SPEC).

Company:
- Name: {company.get('name')}
- City/State: {company.get('city')}, {company.get('state')}
- Keyword/Industry signal: {company.get('keyword_used')}
- Website: {company.get('website')}
- Google rating/reviews: {company.get('rating')} ({company.get('user_ratings_total')})
- Types: {company.get('types')}

Website excerpt (if any):
{(site_excerpt or 'N/A')}

You must return EXACTLY these fields in this format:

ai_fit_category: [High/Medium/Low] with one-sentence justification (e.g., "High: fits ICP due to industry and US presence")
ai_reasoning: [Yes/No] with short explanation (e.g., "Yes: operates in medical device manufacturing in the US")
ai_people_assessment: [summary of leadership/hiring signals or "Not enough data"]
ai_revenue_assessment: [Early-stage/Small (<$5M)/Mid ($5-50M)/Large ($50M+)/Unknown based on size signals]

Example format:
ai_fit_category: High: fits ICP due to medical device manufacturing focus and US presence
ai_reasoning: Yes: operates in medical device manufacturing in the US with regulatory compliance needs
ai_people_assessment: Strong leadership team with technical backgrounds, active LinkedIn presence
ai_revenue_assessment: Mid ($5-50M): established company with multiple locations and strong online presence
""".strip()
    
    def _fetch_site_excerpt(self, url: str) -> str:
        """Fetch website excerpt for AI evaluation"""
        max_chars = self.config.get_site_excerpt_max_chars()
        
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
    
    def _parse_ai_evaluation_fields(self, text: str) -> Dict[str, str]:
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
    
    def ai_precheck(self, companies: List[Dict[str, Any]], cap: int = None) -> List[Dict[str, Any]]:
        """AI Pre-check to filter companies with reliable business info"""
        if cap is None:
            cap = len(companies)
        
        # Get AI parameters from config
        delay = self.config.get_precheck_delay()
        max_tokens = self.config.get_precheck_max_tokens()
        
        passed_companies = []
        
        print("=== AI PRE-CHECK ===")
        print("Filtering companies with reliable business information...")
        
        for i, company in enumerate(companies[:cap]):
            try:
                prompt = self.build_precheck_prompt(company)
                response = self.run_prompt(
                    prompt, 
                    system_role="You are a B2B sales expert evaluating business information quality.", 
                    max_tokens=max_tokens
                )
                
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
        
        print(f"\nPre-check results: {len(passed_companies)}/{len(companies[:cap])} companies passed")
        return passed_companies
    
    def add_ai_evaluation(self, companies: List[Dict[str, Any]], cap: int = 100) -> List[Dict[str, Any]]:
        """AI Evaluation with structured fields"""
        # Get AI parameters from config
        delay = self.config.get_evaluation_delay()
        max_tokens = self.config.get_evaluation_max_tokens()
        
        enriched = []
        
        print("=== AI EVALUATION ===")
        print("Evaluating companies with structured assessment...")
        
        for i, c in enumerate(companies[:cap]):
            try:
                site_excerpt = self._fetch_site_excerpt(c.get('website')) if c.get('website') else None
                prompt = self.build_evaluation_prompt(c, site_excerpt)
                ai_text = self.run_prompt(
                    prompt, 
                    system_role="You are a B2B sales expert for regulated industries.", 
                    max_tokens=max_tokens
                )
                
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