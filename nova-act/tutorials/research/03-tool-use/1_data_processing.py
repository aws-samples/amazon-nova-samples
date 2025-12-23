#!/usr/bin/env python3
"""
Data Processing with Amazon Nova Act and Pandas

This script demonstrates how to extract data with Nova Act and process it
using pandas for analysis, transformation, and visualization.

Prerequisites:
- Complete the centralized setup first (see ../00-setup/README.md)
- Completion of previous tutorials

Setup:
1. Run the centralized setup (one-time):
   cd ../00-setup
   ./setup.sh

2. Activate the virtual environment:
   source ../00-setup/venv/bin/activate

3. Run this tutorial:
   python data_processing.py

Note: The setup script installs pandas and all required dependencies.
"""

import os
import json
from nova_act import NovaAct
from pydantic import BaseModel
from typing import List

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("\033[93m[WARNING]\033[0m pandas not installed. Install with: pip install pandas")


def check_api_key():
    """Check if the API key is set."""
    api_key = os.getenv('NOVA_ACT_API_KEY')
    if not api_key:
        print("\033[91m[ERROR]\033[0m API key not found. Please set the NOVA_ACT_API_KEY environment variable.")
        return None
    print("\033[93m[OK]\033[0m API key found!")
    return api_key


def example_extract_to_dataframe(api_key: str):
    """
    Example 1: Extract structured data and convert to DataFrame
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 1: Extract to DataFrame\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    if not PANDAS_AVAILABLE:
        print("\033[93m[WARNING]\033[0m Skipping - pandas not installed")
        return
    
    print("\n\033[93m[OK]\033[0m Extracting structured data and converting to pandas DataFrame")
    print("  DataFrames make it easy to analyze, filter, and export web-scraped data.")
    print("  You'll see Nova Act extract product information and organize it into a table format.")
    print("\n\033[94m→ Next:\033[0m Scraping Amazon product data and creating a DataFrame for analysis")
    
    # Define schema for structured data
    class Product(BaseModel):
        name: str
        price: float
        rating: float
    
    class ProductList(BaseModel):
        products: List[Product]
    
    with NovaAct(starting_page="https://www.amazon.com/gp/movers-and-shakers/music/ref=zg_bsms_nav_music_0_amazon-renewed", nova_act_api_key=api_key) as nova:
        print("\n\033[93m[OK]\033[0m Extracting structured data...")
        
        # Extract data with schema
        result = nova.act(
            "Extract the first 5 products with their exact names, actual prices in dollars, and real star ratings (look for stars or rating numbers like 3.2, 4.7, etc.)",
            schema=ProductList.model_json_schema()
        )
        
        if result.matches_schema:
            # Convert to pandas DataFrame
            product_list = ProductList.model_validate(result.parsed_response)
            df = pd.DataFrame([product.dict() for product in product_list.products])
            
            print("\n\033[93m[OK]\033[0m Data extracted and converted to DataFrame:")
            print(df)
            
            # Save to CSV
            csv_path = "/tmp/extracted_data.csv"
            df.to_csv(csv_path, index=False)
            print(f"\n\033[93m[OK]\033[0m Data saved to: {csv_path}")
        else:
            print("\033[91m[ERROR]\033[0m Could not extract structured data")


def example_data_analysis(api_key: str):
    """
    Example 2: Perform data analysis on extracted data
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 2: Data Analysis\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    if not PANDAS_AVAILABLE:
        print("\033[93m[WARNING]\033[0m Skipping - pandas not installed")
        return
    
    print("\n\033[93m[OK]\033[0m Performing data analysis on extracted product information")
    print("  Data analysis helps identify trends, averages, and insights from scraped data.")
    print("  You'll see Nova Act extract data and then calculate statistics like average prices and ratings.")
    print("\n\033[94m→ Next:\033[0m Scraping product data and computing analytical insights")
    
    class Product(BaseModel):
        name: str
        price: float
        rating: float
    
    class ProductList(BaseModel):
        products: List[Product]
    
    with NovaAct(starting_page="https://www.amazon.com/blackfriday?ref_=nav_cs_td_bf_dt_cr", nova_act_api_key=api_key) as nova:
        print("\n\033[93m[OK]\033[0m Extracting product data...")
        
        result = nova.act(
            "Extract the first 5 products with their exact names, actual prices in dollars, and real star ratings (look for stars or rating numbers like 3.2, 4.7, etc.)",
            schema=ProductList.model_json_schema()
        )
        
        if result.matches_schema:
            product_list = ProductList.model_validate(result.parsed_response)
            df = pd.DataFrame([p.dict() for p in product_list.products])
            
            print("\n\033[93m[OK]\033[0m Product DataFrame:")
            print(df)
            
            # Perform analysis
            print(f"\n\033[93m[OK]\033[0m Statistical Analysis:")
            print(f"  Total products: {len(df)}")
            print(f"  Average price: ${df['price'].mean():.2f}")
            print(f"  Price range: ${df['price'].min():.2f} - ${df['price'].max():.2f}")
            print(f"  Average rating: {df['rating'].mean():.2f}")
            
            # Find best value (high rating, low price)
            df['value_score'] = df['rating'] / df['price']
            best_value = df.loc[df['value_score'].idxmax()]
            print(f"\n\033[93m[OK]\033[0m Best value product:")
            print(f"  Name: {best_value['name']}")
            print(f"  Price: ${best_value['price']:.2f}")
            print(f"  Rating: {best_value['rating']:.2f}")


def example_data_transformation(api_key: str):
    """
    Example 3: Transform and clean extracted data
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 3: Data Transformation\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    if not PANDAS_AVAILABLE:
        print("\033[93m[WARNING]\033[0m Skipping - pandas not installed")
        return
    
    print("\n\033[93m[OK]\033[0m Transforming and cleaning extracted data")
    print("  Data transformation converts raw scraped data into clean, usable formats.")
    print("  You'll see Nova Act extract data and then apply cleaning and formatting operations.")
    print("\n\033[94m→ Next:\033[0m Extracting raw data and applying transformation techniques")
    
    with NovaAct(starting_page="https://www.amazon.com/blackfriday?ref_=nav_cs_td_bf_dt_cr", nova_act_api_key=api_key) as nova:
        print("\n\033[93m[OK]\033[0m Extracting raw data...")
        
        # Extract some data
        result = nova.act(
            "Extract the page title and main heading",
            schema={"type": "object", "properties": {"title": {"type": "string"}, "heading": {"type": "string"}}, "required": ["title", "heading"]}
        )
        
        if result.response:
            # Create DataFrame from raw data
            raw_data = {
                'content': [result.response],
                'url': [nova.page.url],
                'timestamp': [pd.Timestamp.now()]
            }
            df = pd.DataFrame(raw_data)
            
            print("\n\033[93m[OK]\033[0m Raw DataFrame:")
            print(df)
            
            # Transform data
            df['content_length'] = df['content'].str.len()
            df['domain'] = df['url'].str.extract(r'https?://([^/]+)')
            df['date'] = df['timestamp'].dt.date
            df['time'] = df['timestamp'].dt.time
            
            print("\n\033[93m[OK]\033[0m Transformed DataFrame:")
            print(df[['domain', 'content_length', 'date', 'time']])
            
            # Save transformed data
            output_path = "/tmp/transformed_data.json"
            df.to_json(output_path, orient='records', date_format='iso')
            print(f"\n\033[93m[OK]\033[0m Transformed data saved to: {output_path}")


def example_multi_page_aggregation(api_key: str):
    """
    Example 4: Aggregate data from multiple pages
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 4: Multi-Page Aggregation\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    if not PANDAS_AVAILABLE:
        print("\033[93m[WARNING]\033[0m Skipping - pandas not installed")
        return
    
    # Use two different Amazon pages for aggregation
    pages = [
        "https://www.amazon.com/gp/browse.html?node=120955898011&ref_=nav_cs_handmade",
        "https://www.amazon.com/fmc/ssd-storefront?ref_=nav_cs_SSD_nav_storefront"
    ]
    
    all_data = []
    
    for page_url in pages:
        print(f"\n\033[93m[OK]\033[0m Processing: {page_url}")
        
        with NovaAct(starting_page=page_url, nova_act_api_key=api_key) as nova:
            result = nova.act(
                "What is the main heading on this page?",
                schema={"type": "object", "properties": {"heading": {"type": "string"}}, "required": ["heading"]}
            )
            
            if result.response:
                all_data.append({
                    'url': page_url,
                    'heading': result.response,
                    'timestamp': pd.Timestamp.now()
                })
    
    # Create combined DataFrame
    df = pd.DataFrame(all_data)
    
    print("\n\033[93m[OK]\033[0m Combined DataFrame:")
    print(df)
    
    # Aggregate statistics
    print(f"\n\033[93m[OK]\033[0m Aggregation:")
    print(f"  Total pages processed: {len(df)}")
    print(f"  Average heading length: {df['heading'].str.len().mean():.1f} characters")
    
    # Save aggregated data
    output_path = "/tmp/aggregated_data.csv"
    df.to_csv(output_path, index=False)
    print(f"\n\033[93m[OK]\033[0m Aggregated data saved to: {output_path}")


def example_data_filtering(api_key: str):
    """
    Example 5: Filter and query extracted data
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 5: Data Filtering\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    if not PANDAS_AVAILABLE:
        print("\033[93m[WARNING]\033[0m Skipping - pandas not installed")
        return
    
    class DataPoint(BaseModel):
        category: str
        value: float
        status: str
    
    class DataSet(BaseModel):
        data: List[DataPoint]
    
    with NovaAct(starting_page="https://www.amazon.com/blackfriday?ref_=nav_cs_td_bf_dt_cr", nova_act_api_key=api_key) as nova:
        print("\n\033[93m[OK]\033[0m Extracting dataset...")
        
        result = nova.act(
            "Extract the first 5 data points with categories, values, and status",
            schema=DataSet.model_json_schema()
        )
        
        if result.matches_schema:
            dataset = DataSet.model_validate(result.parsed_response)
            df = pd.DataFrame([d.dict() for d in dataset.data])
            
            print("\n\033[93m[OK]\033[0m Full DataFrame:")
            print(df)
            
            # Filter data
            high_value = df[df['value'] > df['value'].median()]
            print(f"\n\033[93m[OK]\033[0m High value items (>{df['value'].median():.2f}):")
            print(high_value)
            
            # Group by category
            category_stats = df.groupby('category')['value'].agg(['count', 'mean', 'sum'])
            print("\n\033[93m[OK]\033[0m Statistics by category:")
            print(category_stats)
            
            # Filter by status
            active_items = df[df['status'] == 'active']
            print(f"\n\033[93m[OK]\033[0m Active items: {len(active_items)}")


def example_export_formats(api_key: str):
    """
    Example 6: Export data in various formats
    """
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mExample 6: Export Formats\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    if not PANDAS_AVAILABLE:
        print("\033[93m[WARNING]\033[0m Skipping - pandas not installed")
        return
    
    with NovaAct(starting_page="https://www.amazon.com/gp/movers-and-shakers/?ref_=nav_em_ms_0_1_1_4", nova_act_api_key=api_key) as nova:
        print("\n\033[93m[OK]\033[0m Extracting data for export...")
        
        result = nova.act(
            "Extract the page title and URL",
            schema={"type": "object", "properties": {"title": {"type": "string"}, "url": {"type": "string"}}, "required": ["title", "url"]}
        )
        
        if result.response:
            # Create sample DataFrame
            data = {
                'title': [result.response],
                'url': [nova.page.url],
                'timestamp': [pd.Timestamp.now()],
                'status': ['success']
            }
            df = pd.DataFrame(data)
            
            print("\n\033[93m[OK]\033[0m Exporting to multiple formats...")
            
            # CSV
            csv_path = "/tmp/export.csv"
            df.to_csv(csv_path, index=False)
            print(f"  [OK] CSV: {csv_path}")
            
            # JSON
            json_path = "/tmp/export.json"
            df.to_json(json_path, orient='records', date_format='iso')
            print(f"  [OK] JSON: {json_path}")
            
            # Excel (requires openpyxl)
            try:
                excel_path = "/tmp/export.xlsx"
                df.to_excel(excel_path, index=False)
                print(f"  [OK] Excel: {excel_path}")
            except ImportError:
                print(f"  [WARNING] Excel: Skipped (install openpyxl)")
            
            # HTML
            html_path = "/tmp/export.html"
            df.to_html(html_path, index=False)
            print(f"  [OK] HTML: {html_path}")
            
            print("\n\033[93m[OK]\033[0m All exports completed")


def main():
    """Main function to run all data processing examples."""
    print(f"\n\033[94m{'='*60}\033[0m")
    print(f"\033[94mData Processing with Amazon Nova Act and Pandas\033[0m")
    print(f"\033[94m{'='*60}\033[0m")
    
    if not PANDAS_AVAILABLE:
        print("\n\033[91m[ERROR]\033[0m pandas is required for this tutorial")
        print("  Install with: pip install pandas")
        return
    
    # Check API key
    api_key = check_api_key()
    if not api_key:
        return
    
    print("\n[DATA] Data Processing Workflow:")
    print("  1. Extract structured data with Nova Act")
    print("  2. Convert to pandas DataFrame")
    print("  3. Analyze, transform, and filter")
    print("  4. Export in various formats")
    
    print("\nThis tutorial includes 6 examples. Press Enter after each to continue...")
    
    try:
        # Example 1
        example_extract_to_dataframe(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Data extraction to pandas DataFrame")
        print(f"\033[94m→ Next:\033[0m Statistical analysis and data insights")
        input("\n>> Press Enter to continue to Example 2...")
        
        # Example 2
        example_data_analysis(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Data analysis with pandas statistics")
        print(f"\033[94m→ Next:\033[0m Data transformation and cleaning operations")
        input("\n>> Press Enter to continue to Example 3...")
        
        # Example 3
        example_data_transformation(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Data transformation and cleaning")
        print(f"\033[94m→ Next:\033[0m Multi-page data aggregation workflow")
        input("\n>> Press Enter to continue to Example 4...")
        
        # Example 4
        example_multi_page_aggregation(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Multi-page data collection and aggregation")
        print(f"\033[94m→ Next:\033[0m Data filtering and querying techniques")
        input("\n>> Press Enter to continue to Example 5...")
        
        # Example 5
        example_data_filtering(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Data filtering and querying operations")
        print(f"\033[94m→ Next:\033[0m Exporting data to multiple file formats")
        input("\n>> Press Enter to continue to Example 6...")
        
        # Example 6
        example_export_formats(api_key)
        print(f"\n\033[92m✓ Completed:\033[0m Data export to multiple formats")
        
        print(f"\n\033[94m{'='*60}\033[0m")
        print(f"\033[94m[OK] All data processing examples completed!\033[0m")
        print(f"\033[94m{'='*60}\033[0m")
        
        print("\nKey Takeaways:")
        print("- Always use Pydantic schemas for structured extraction")
        print("- Convert to DataFrame for powerful analysis")
        print("- Use pandas for filtering, grouping, and aggregation")
        print("- Export to multiple formats (CSV, JSON, Excel, HTML)")
        print("- Aggregate data from multiple pages")
        
        print("\nNext Steps:")
        print("- Explore the Observability tutorial (04-observability)")
        print("- Build your own data extraction pipelines")
        print("- Experiment with other pandas features")
        
    except KeyboardInterrupt:
        print("\n\n[WARNING] Tutorial interrupted by user")
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m Error running examples: {e}")
        print("\nTroubleshooting:")
        print("- Ensure pandas is installed: pip install pandas")
        print("- Check your API key is valid")
        print("- Verify internet connection")


if __name__ == "__main__":
    main()
