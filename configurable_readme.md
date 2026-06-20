# Configurable Agentic Search Solution

This enhanced version of the Agentic Search Solution supports multiple e-commerce sites through a configuration-driven approach. Deploy the same codebase to different sites by simply changing the configuration file.

## Features

- **Multi-Site Support**: Configure different sites with unique selectors, URLs, and search parameters
- **Inventory-Aware Ranking**: Products with higher inventory are prioritized when relevance is equal
- **Business Summary Generation**: Automatically generates relevancy assessments and product movement recommendations
- **Configuration-Driven**: All site-specific parameters are externalized to configuration files
- **Command Line Interface**: Easy deployment and management through CLI commands

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install selenium requests webdriver-manager

# Install Ollama (if not already installed)
# Visit https://ollama.ai/ for installation instructions

# Pull a language model
ollama pull gemma3
```

### 2. Configuration

Copy and customize the `config.json` file for your sites:

```bash
cp config.json my_config.json
# Edit my_config.json with your site-specific settings
```

### 3. Run for a Single Site

```bash
# List available sites
python main.py --list-sites

# Deploy for TruckPro
python main.py --site truckpro

# Deploy for TundraFMP with custom model
python main.py --site tundrafmp --model llama3

# Deploy with custom output file
python main.py --site truckpro --output-file custom_results.json
```

### 4. Deploy All Sites

```bash
# Deploy all configured sites
python deploy.py --deploy-all

# Deploy all sites with overrides
python deploy.py --deploy-all --model llama3 --max-results 15
```

## Configuration Structure

The `config.json` file contains configurations for multiple sites:

```json
{
  "site_configs": {
    "your_site_key": {
      "site_name": "Your Site Name",
      "target_url": "https://your-site.com/",
      "search_tasks": [...],
      "inventory_test_cases": [...],
      "scraping_config": {...},
      "output_config": {...}
    }
  },
  "llm_config": {...},
  "evaluation_config": {...},
  "chrome_config": {...},
  "deployment_config": {...}
}
```

### Adding a New Site

1. Add a new site configuration to the `site_configs` section
2. Configure site-specific selectors and parameters
3. Test the configuration: `python main.py --validate your_site_key`
4. Deploy: `python main.py --site your_site_key`

## Configuration Parameters

### Site Configuration

| Parameter | Description | Example |
|-----------|-------------|---------|
| `site_name` | Display name for the site | "TruckPro" |
| `target_url` | Base URL of the site | "https://www.truckpro.com/" |
| `search_tasks` | List of search queries to test | `[{"query": "brake pad"}]` |
| `inventory_test_cases` | Inventory-specific test cases | `[{"query": "ABCD", "search_type": "part_number"}]` |

### Scraping Configuration

| Parameter | Description | Example |
|-----------|-------------|---------|
| `search_input_selectors` | CSS selectors for search input | `["#searchInput", "input[type='search']"]` |
| `search_button_selectors` | XPath selectors for search button | `["//button[contains(@class, 'search')]"]` |
| `product_card_selectors` | CSS selectors for product cards | `["div.productlist", "div.product-card"]` |
| `max_results_per_query` | Maximum results to scrape | `10` |
| `wait_timeout` | Element wait timeout (seconds) | `10` |
| `page_load_timeout` | Page load timeout (seconds) | `30` |

### LLM Configuration

| Parameter | Description | Example |
|-----------|-------------|---------|
| `default_model` | Ollama model to use | "gemma3" |
| `timeout` | API request timeout | `120` |
| `max_retries` | Number of API retries | `3` |

### Evaluation Configuration

| Parameter | Description | Example |
|-----------|-------------|---------|
| `enable_inventory_ranking` | Enable inventory-aware ranking | `true` |
| `enable_detailed_analysis` | Generate detailed analysis | `true` |
| `inventory_weight_factor` | Inventory impact on ranking (0.0-1.0) | `0.3` |
| `low_stock_threshold` | Threshold for low stock warning | `5` |

## Command Line Options

### Main Application (`main.py`)

```bash
python main.py [OPTIONS]

Options:
  --site SITE_KEY         Site to deploy (required)
  --config CONFIG_FILE    Configuration file path (default: config.json)
  --list-sites           List available site configurations
  --validate SITE_KEY    Validate configuration for a site
  --model MODEL_NAME     Override LLM model
  --max-results N        Override max results per query
  --headless BOOL        Override headless browser setting
  --output-file PATH     Override output file path
```

### Deployment Script (`deploy.py`)

```bash
python deploy.py [OPTIONS]

Options:
  --deploy-all           Deploy all configured sites
  --site SITE_KEY        Deploy specific site
  --check-deps           Check if dependencies are installed
  --check-ollama         Check Ollama status and available models
  --validate-all         Validate all site configurations
  --list-sites          List available sites
```

## Output Files

Each site deployment generates:

1. **Main Results File** (e.g., `truckpro_evaluation_results.json`):
   - Search results with LLM evaluations
   - Business summaries and recommendations
   - Overall performance metrics

2. **Detailed Analysis File** (e.g., `truckpro_detailed_analysis.json`):
   - Inventory impact analysis
   - Ranking change explanations
   - Detailed evaluation metadata

## Business Summary Features

Each search query generates a business summary including:

- **Relevancy Assessment**: Overall quality of search results
- **Product Movement Recommendations**: Specific actions to improve sales
- **Key Insights**: Important findings about product performance
- **Action Items**: Prioritized tasks for improvement

Example business summary:
```json
{
  "relevancy_assessment": "Search for 'brake pad' on TruckPro returned 8 results with good relevancy (5 high, 2 medium, 1 low relevance). Inventory availability is strong with 6 items in stock, 2 out of stock.",
  "product_movement_recommendations": [
    "Restock 2 out-of-stock items or consider removing them from search results to improve customer experience",
    "Continue using inventory-aware ranking as it's successfully prioritizing available products"
  ],
  "key_insights": [
    "Top performing products: BP001, BP002",
    "Products needing attention: BP008"
  ],
  "action_items": [
    "OPTIMIZE: Strong performance - consider promoting these search results in marketing"
  ]
}
```

## Inventory-Aware Ranking

The system automatically prioritizes products with higher inventory when relevance levels are equal:

1. **Same Relevance**: Products with more inventory rank higher
2. **Out of Stock**: Items with 0 inventory rank lower within their relevance tier
3. **Low Stock**: Items below the threshold are flagged for attention

Example: If searching for "ABCD" returns:
- `12ABCD` (exact match, 0 inventory)
- `AAABCD` (substring match, 500 inventory)

The system will rank `AAABCD` higher due to inventory availability.

## Troubleshooting

### Common Issues

1. **"Configuration file not found"**
   ```bash
   # Make sure config.json exists
   cp config.example.json config.json
   ```

2. **"Ollama is not running"**
   ```bash
   # Start Ollama server
   ollama serve
   
   # Check if it's running
   python deploy.py --check-ollama
   ```

3. **"Missing dependencies"**
   ```bash
   # Check what's missing
   python deploy.py --check-deps
   
   # Install missing packages
   pip install selenium requests webdriver-manager
   ```

4. **"WebDriver setup failed"**
   ```bash
   # Install Chrome WebDriver manager
   pip install webdriver-manager
   
   # Or specify path in config
   "chrome_driver_path": "/path/to/chromedriver"
   ```

### Validation

Always validate your configuration before deployment:

```bash
# Validate specific site
python main.py --validate truckpro

# Validate all sites
python deploy.py --validate-all
```

## Extending the System

### Adding New Sites

1. Study the target site's HTML structure
2. Identify CSS selectors for search elements
3. Add configuration to `config.json`
4. Test with a few queries
5. Validate and deploy

### Custom Evaluation Logic

Modify `llm_evaluator.py` to add custom evaluation criteria:

1. Update prompt templates in `get_enhanced_prompt_template()`
2. Modify ranking logic in `apply_inventory_aware_ranking()`
3. Add new business summary rules in `generate_business_summary()`

### Site-Specific Customizations

For sites requiring special handling:
1. Create site-specific modules (e.g., `scraper_special.py`)
2. Add conditional logic in the main orchestrator
3. Use configuration flags to enable special features

## Performance Considerations

- **Headless Mode**: Use `"headless": true` for better performance
- **Result Limits**: Set appropriate `max_results_per_query` values
- **Timeout Settings**: Adjust timeouts based on site performance
- **Batch Processing**: Use `--deploy-all` for multiple sites
- **Resource Management**: Monitor memory usage with large result sets

## Security Notes

- **User Agents**: Configure realistic user agents to avoid detection
- **Rate Limiting**: Use appropriate delays between requests
- **Credentials**: Never store credentials in configuration files
- **IP Rotation**: Consider proxy rotation for high-volume scraping

## Contributing

To contribute to this project:

1. Fork the repository
2. Create a feature branch
3. Add your site configuration
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.