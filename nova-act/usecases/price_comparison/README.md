# Price Comparison using Amazon Nova Act

This project demonstrates automated price comparison across multiple retailers using Amazon Nova Act. It showcases how AI-powered browser agents can intelligently search for products, navigate retail websites, and extract pricing information to help consumers find the best deals.

## Overview

This demonstration implements a concurrent price comparison workflow that searches for products across major retailers (e.g. Amazon, Best Buy, Costco, Target) and compiles results into a sortable comparison table.

### Key Benefits

- **Automated Price Discovery**: AI agents navigate retail sites and extract current pricing
- **Concurrent Execution**: Parallel searches across multiple retailers reduce total execution time
- **Structured Output**: Results exported to CSV for easy analysis and comparison
- **Flexible Configuration**: Customize product searches and retailer sources

## Architecture

The demo consists of two main components:

1. **Nova Act Browser Agents**: Automated browser sessions that navigate retail websites, handle captchas, and extract product information
2. **Concurrent Execution Engine**: ThreadPoolExecutor manages parallel searches across multiple retailers

## Prerequisites

Before running this demo, ensure you have:

### Development Environment

- **Python 3.11 or higher**
- **pip** (Python package manager)

### API Access

- **Amazon Nova Act API Key** - Visit [Nova Act home page](https://nova.amazon.com/act) to generate your API key

## Getting Started

Follow these steps to set up and run the price comparison tool:

### Step 1: Install Dependencies

```bash
# Navigate to the project directory
cd nova-act/usecases/price_comparison

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Key

Set your Nova Act API key as an environment variable:

```bash
export NOVA_ACT_API_KEY="your-api-key-here"
```

### Step 3: Run Price Comparison

```bash
# Run with default product (iPad Pro 13-inch M4, 256GB Wi-Fi)
python main.py

# Run with custom product
python main.py --product_name "iPhone 15 Pro Max 256GB" --product_sku "MU793LL/A"

# Run with custom sources
python main.py --sources '[("Walmart", "https://www.walmart.com"), ("Amazon", "https://www.amazon.com")]'

# Run in non-headless mode (visible browser)
python main.py --headless=False
```

## Usage Examples

### Default Search

```bash
python main.py
```

Searches for "iPad Pro 13-inch (M4 chip), 256GB Wi-Fi" (SKU: MVX23LL/A) across Amazon, Best Buy, Costco, and Target.

### Custom Product Search

```bash
python main.py --product_name "MacBook Air 13-inch M3" --product_sku "MRXN3LL/A"
```

### Custom Retailer Sources

```bash
python main.py --sources '[("Walmart", "https://www.walmart.com"), ("Newegg", "https://www.newegg.com")]'
```

### Debug Mode (Visible Browser)

```bash
python main.py --headless=False
```

## Output

Results are saved to `price_comparison_results.csv` with the following columns:

| Column            | Description                              |
| ----------------- | ---------------------------------------- |
| Source            | Retailer name (Amazon, Best Buy, etc.)   |
| Product Name      | Matched product name from retailer       |
| Product SKU       | Search SKU used                          |
| Price             | Current price (sorted lowest to highest) |
| Promotion Details | Any active promotions or discounts       |

## Project Structure

```
price_comparison/
├── README.md           # This file
├── main.py             # Main application script
└── requirements.txt    # Python dependencies
```

## How It Works

1. **Initialization**: Creates Nova Act browser sessions for each retailer
2. **Captcha Handling**: Detects captchas and prompts user to solve if needed
3. **Product Search**: Searches using the product SKU on each retailer site
4. **Result Extraction**: AI agent identifies the most relevant product and extracts pricing
5. **Data Compilation**: Results are aggregated, sorted by price, and exported to CSV

## Troubleshooting

### Common Issues

1. **Captcha Detected**

   - The tool will pause and prompt you to solve the captcha manually
   - Press Enter after solving to continue

2. **Product Not Found**

   - Verify the SKU is valid for the target retailers
   - Some products may not be available at all retailers

3. **Browser Session Errors**

   - Ensure you have a stable internet connection
   - Try running in non-headless mode to debug: `--headless=False`

4. **API Key Issues**
   ```bash
   export NOVA_ACT_API_KEY="your-api-key-here"
   ```

## Additional Resources

- [Amazon Nova Act](https://nova.amazon.com/act)
- [Nova Act Documentation](https://docs.aws.amazon.com/nova/latest/userguide/what-is-nova.html)
