# output_module.py
import pandas as pd
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from config_manager import ConfigManager

class OutputModule:
    """Handles all output operations"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.output_config = config_manager.get_output_config()
        self.scoring_config = config_manager.get_scoring_config()
        
        print("✅ OutputModule initialized")
    
    def save_results(self, companies: List[Dict[str, Any]], filename_prefix: str = None) -> Optional[str]:
        """Save results to CSV with exact schema requirements"""
        if filename_prefix is None:
            filename_prefix = self.output_config.get('filename_prefix', 'prospecting_results')
        
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

            # Sort by fit category and rating if configured
            if self.output_config.get('sort_by_fit_category', True):
                category_order = {'High': 3, 'Medium': 2, 'Low': 1, 'Unknown': 0}
                df['sort_order'] = df['ai_fit_category'].map(category_order).fillna(0)
                
                if self.output_config.get('sort_by_rating', True):
                    df = df.sort_values(['sort_order', 'rating'], ascending=[False, False])
                else:
                    df = df.sort_values(['sort_order'], ascending=[False])
                
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
            self._print_summary_statistics(df)

            return csv_file
        else:
            print("No companies to save")
            return None
    
    def _print_summary_statistics(self, df: pd.DataFrame):
        """Print summary statistics"""
        print(f"\n=== Summary Statistics ===")
        
        # Companies by state
        if 'state' in df.columns and not df['state'].isna().all():
            print(f"Companies by state:")
            print(df['state'].value_counts().head(10))

        # Top keywords
        if 'keywords' in df.columns and not df['keywords'].isna().all():
            print(f"\nTop keywords that found companies:")
            print(df['keywords'].value_counts().head(10))

        # Fit categories
        if 'ai_fit_category' in df.columns and not df['ai_fit_category'].isna().all():
            print(f"\nFit categories:")
            print(df['ai_fit_category'].value_counts())

        # Revenue assessments
        if 'ai_revenue_assessment' in df.columns and not df['ai_revenue_assessment'].isna().all():
            print(f"\nRevenue assessments:")
            print(df['ai_revenue_assessment'].value_counts())

        # People assessments
        if 'ai_people_assessment' in df.columns and not df['ai_people_assessment'].isna().all():
            print(f"\nPeople assessments:")
            print(df['ai_people_assessment'].value_counts())

        # Average rating
        if 'rating' in df.columns and not df['rating'].isna().all():
            avg_rating = df['rating'].mean()
            if not pd.isna(avg_rating):
                print(f"\nAverage rating: {avg_rating:.2f}")
    
    def save_results_with_custom_schema(self, companies: List[Dict[str, Any]], 
                                      schema_columns: List[str], 
                                      filename_prefix: str = None) -> Optional[str]:
        """Save results with custom schema columns"""
        if filename_prefix is None:
            filename_prefix = self.output_config.get('filename_prefix', 'prospecting_results')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if companies:
            # Create DataFrame with custom schema
            filtered_data = []
            for company in companies:
                filtered_company = {}
                
                # Map fields to custom schema
                for column in schema_columns:
                    # Handle common field mappings
                    if column == 'keywords':
                        filtered_company[column] = company.get('keyword_used', None)
                    elif column == 'ai_evaluation':
                        filtered_company[column] = company.get('ai_evaluation', None)
                    elif column == 'ai_fit_category':
                        filtered_company[column] = company.get('ai_fit_category', None)
                    elif column == 'ai_reasoning':
                        filtered_company[column] = company.get('ai_reasoning', None)
                    elif column == 'ai_people_assessment':
                        filtered_company[column] = company.get('ai_people_assessment', None)
                    elif column == 'ai_revenue_assessment':
                        filtered_company[column] = company.get('ai_revenue_assessment', None)
                    else:
                        # Direct mapping
                        filtered_company[column] = company.get(column, None)
                
                filtered_data.append(filtered_company)
            
            df = pd.DataFrame(filtered_data)

            # Get the current working directory
            current_dir = os.getcwd()

            # Save to CSV
            csv_file = os.path.join(current_dir, f"{filename_prefix}_{timestamp}.csv")
            df.to_csv(csv_file, index=False)

            print(f"\nCustom schema results saved to: {csv_file}")
            print(f"Total companies found: {len(companies)}")
            print(f"Custom schema columns: {list(df.columns)}")

            return csv_file
        else:
            print("No companies to save")
            return None
    
    def export_to_excel(self, companies: List[Dict[str, Any]], filename_prefix: str = None) -> Optional[str]:
        """Export results to Excel format"""
        if filename_prefix is None:
            filename_prefix = self.output_config.get('filename_prefix', 'prospecting_results')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if companies:
            # Create DataFrame (same as CSV method)
            schema_columns = [
                'place_id', 'name', 'address', 'city', 'state', 'keywords', 'types', 
                'rating', 'website', 'phone', 'ai_evaluation', 'ai_fit_category', 
                'ai_reasoning', 'ai_people_assessment', 'ai_revenue_assessment'
            ]
            
            filtered_data = []
            for company in companies:
                filtered_company = {}
                for column in schema_columns:
                    if column == 'keywords':
                        filtered_company[column] = company.get('keyword_used', None)
                    else:
                        filtered_company[column] = company.get(column, None)
                filtered_data.append(filtered_company)
            
            df = pd.DataFrame(filtered_data)

            # Get the current working directory
            current_dir = os.getcwd()

            # Save to Excel
            excel_file = os.path.join(current_dir, f"{filename_prefix}_{timestamp}.xlsx")
            df.to_excel(excel_file, index=False)

            print(f"\nExcel results saved to: {excel_file}")
            print(f"Total companies found: {len(companies)}")

            return excel_file
        else:
            print("No companies to save")
            return None