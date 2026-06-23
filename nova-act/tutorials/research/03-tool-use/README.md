# Python Library Integration with Amazon Nova Act

## Overview
This tutorial demonstrates extracting product data from Amazon pages using Nova Act and processing it with pandas for analysis, transformation, and export. You'll learn to build complete data pipelines from web extraction to structured analysis.

## Learning Objectives
- Extract structured product data (names, prices, ratings) from Amazon pages
- Convert extracted data to pandas DataFrames for analysis
- Perform statistical analysis on real product data
- Transform and clean extracted data
- Aggregate data from multiple Amazon product categories
- Filter and query product datasets
- Export data to multiple formats (CSV, JSON, Excel, HTML)

## Prerequisites
**⚠️ Complete the centralized setup first!**
- Complete setup in `../00-setup/`
- Completion of previous tutorials (01-getting-started, 02-human-in-loop)
- Basic understanding of pandas (helpful but not required)

## Tutorial Script

### Data Processing (`1_data_processing.py`)
Six examples demonstrating complete data processing workflows with real Amazon product data.

**Example 1: Extract to DataFrame**
- **Source**: Amazon Music Movers & Shakers
- **Data**: First 5 products with names, prices, and star ratings
- **Output**: Pandas DataFrame and CSV export
- **Focus**: Basic structured data extraction and DataFrame conversion

**Example 2: Data Analysis**
- **Source**: Amazon Black Friday deals
- **Analysis**: Statistical analysis (averages, ranges, best value products)
- **Calculations**: Price statistics, rating analysis, value scoring
- **Focus**: Real-world product analysis and insights

**Example 3: Data Transformation**
- **Source**: Amazon Black Friday deals
- **Transforms**: Content length, domain extraction, date/time parsing
- **Output**: JSON export with transformed fields
- **Focus**: Data cleaning and feature engineering

**Example 4: Multi-Page Aggregation**
- **Sources**: Amazon Handmade + SSD Storefront pages
- **Process**: Extract headings from multiple product categories
- **Analysis**: Cross-category comparison and aggregation
- **Focus**: Combining data from multiple sources

**Example 5: Data Filtering**
- **Source**: Amazon Black Friday deals
- **Operations**: Median filtering, category grouping, status filtering
- **Analysis**: High-value item identification, category statistics
- **Focus**: Advanced pandas filtering and querying

**Example 6: Export Formats**
- **Source**: Amazon Movers & Shakers
- **Exports**: CSV, JSON, Excel, HTML formats
- **Data**: Page metadata with timestamps
- **Focus**: Multi-format data export workflows

## Key Concepts

### Structured Data Extraction
Uses Pydantic schemas to extract specific product information:
```python
class Product(BaseModel):
    name: str
    price: float
    rating: float
```

### Real Amazon Data Sources
- **Music Movers & Shakers**: Trending music products with ratings
- **Black Friday Deals**: Seasonal promotions with varied pricing
- **Handmade Products**: Artisan items with unique characteristics
- **SSD Storefront**: Technology products with specifications
- **General Movers & Shakers**: Cross-category trending items

### Data Processing Pipeline
1. **Extract**: Get structured product data using Nova Act with schemas
2. **Validate**: Ensure data matches expected schema format
3. **Transform**: Clean and enhance data with pandas operations
4. **Analyze**: Perform statistical analysis and insights
5. **Export**: Save results in multiple formats for different uses

### Best Practices Demonstrated
- Always use Pydantic schemas for reliable extraction
- Validate data with `result.matches_schema` before processing
- Limit extractions to manageable sizes (first 5 products)
- Handle missing or malformed data gracefully
- Use descriptive prompts for accurate extraction
- Save intermediate results to prevent data loss

## Data Analysis Techniques

### Statistical Analysis
- Price ranges and averages across product categories
- Rating distributions and quality metrics
- Value scoring (rating-to-price ratios)
- Cross-category comparisons

### Data Transformation
- Content length analysis for product descriptions
- Domain extraction from URLs
- Timestamp parsing and date/time operations
- Feature engineering for enhanced analysis

### Filtering and Querying
- Median-based filtering for high-value items
- Category-based grouping and aggregation
- Status-based filtering for active products
- Multi-criteria product selection

## Export Capabilities
- **CSV**: Spreadsheet-compatible format for analysis tools
- **JSON**: API-friendly format for web applications
- **Excel**: Business-ready format with formatting support
- **HTML**: Web-displayable format for reports and dashboards

## Quick Start
```bash
# Activate environment
source ../00-setup/venv/bin/activate

# Run the tutorial
python 1_data_processing.py
```

## Real-World Applications
- **E-commerce Analysis**: Product pricing and rating trends
- **Market Research**: Competitive analysis across categories
- **Inventory Management**: Product performance tracking
- **Business Intelligence**: Sales and customer preference insights
- **Automated Reporting**: Regular data extraction and analysis pipelines

## Next Steps
- Build custom product analysis workflows
- Explore the Observability tutorial (04-observability)
- Create automated reporting systems
- Integrate with business intelligence tools
- Develop real-time product monitoring systems
