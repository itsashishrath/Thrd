# Dynamic Pricing Engine

## Overview

This project implements a modular pricing engine that automatically adjusts product prices based on inventory levels and sales performance. The pricing engine applies a configurable set of rules with defined precedence to optimize product pricing.

Two implementations are provided:
1. **Basic Pricing Engine** - Memory-optimized core implementation
2. **Interactive Pricing Engine** - Real-time monitoring version for production use

## Features

- **Modular rule system** that allows easy addition, removal and modification of pricing rules
- **Priority-based rule processing** to ensure rules are applied in the correct order
- **Memory-efficient processing** utilizing Python generators for handling large datasets
- **Real-time monitoring** of CSV changes in the interactive version

## Implementation Details

### Basic Pricing Engine (`pricing_engine.py`)

This implementation focuses on memory efficiency and modularity:

- **Memory Optimization:** 
  - Processes products one by one using generators
  - Only keeps sales data (typically smaller than product data) fully in memory
  - Streams results directly to output file

- **Modularity:**
  - Each pricing rule is an independent class inheriting from `PricingRule` abstract base class
  - Rules can be added or removed at runtime
  - Rule precedence is controlled via priority values

### Interactive Pricing Engine (`interactive_pricing_engine.py`)

Builds upon the basic engine adding real-time monitoring capabilities:

- **File Monitoring:**
  - Uses `watchdog` library to monitor CSV files for changes
  - Calculates MD5 hashes to detect actual content changes
  - Automatically reprocesses data when changes are detected

- **Production-Ready Features:**
  - Runs continuously in the background
  - Handles errors gracefully
  - Provides timestamped logging
  - Efficient change detection to prevent unnecessary processing

## Getting Started

### Prerequisites

- Python 3.6 or higher
- watchdog (for interactive version): `pip install watchdog`

### Basic Usage

1. Place your data files in the same directory as the script:
   - `products.csv` - Product catalog with pricing, cost, and stock information
   - `sales.csv` - Recent sales data

2. Run either version of the pricing engine:
   ```
   python pricing_engine.py
   ```
   or for interactive version:
   ```
   python interactive_pricing_engine.py
   ```

3. Check the generated `updated_prices.csv` file for results

### Interactive Mode

In interactive mode, the engine:
1. Processes files immediately on startup
2. Continuously monitors both CSV files for changes
3. Automatically updates `updated_prices.csv` when changes are detected
4. Displays status messages when processing occurs

Press `Ctrl+C` to stop the interactive monitoring.

## Rule System

The current implementation includes four pricing rules applied in the following order:

1. **Low Stock, High Demand** (Priority 1):
   - Condition: `stock < 20` AND `quantity_sold > 30`
   - Action: Increase price by 15%

2. **Dead Stock** (Priority 2):
   - Condition: `stock > 200` AND `quantity_sold == 0`
   - Action: Decrease price by 30%

3. **Overstocked Inventory** (Priority 3):
   - Condition: `stock > 100` AND `quantity_sold < 20`
   - Action: Decrease price by 10%

4. **Minimum Profit Constraint** (Always applied last):
   - Condition: Always checked
   - Action: Ensure price is at least 20% above cost_price

## Adding New Rules

To add a new pricing rule:

1. Create a new class extending `PricingRule`
2. Implement `should_apply()` and `apply()` methods
3. Add the rule to the engine with desired priority:
   ```python
   engine.add_rule(YourNewRule(priority=desired_priority))
   ```

## Assumptions

- The CSV files have the required column structure as specified in the project requirements
- The `products.csv` file has columns: sku, name, current_price, cost_price, stock
- The `sales.csv` file has columns: sku, quantity_sold
- The CSV files are properly formatted with headers
- In the interactive version, files are watched in the same directory as the script
- Product SKUs are unique identifiers
- All numeric values in CSVs can be converted to appropriate types (int, float)
- Only the first applicable rule among Rules 1-3 should be applied to each product
- Rule 4 is always applied after any of the above rules

## Limitations

- The interactive version requires the watchdog library
- Processing happens in-memory, so extremely large files might cause memory issues
- The interactive version watches the specific directory, not subdirectories
- The script does not handle concurrent file modifications
