import csv
import os
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Iterator, Tuple, Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class PricingRule(ABC):
    """Abstract base class for all pricing rules"""
    
    def __init__(self, priority: int):
        self.priority = priority  # Lower number means higher priority
    
    @abstractmethod
    def should_apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> bool:
        """Determine if this rule should be applied to the product"""
        pass
    
    @abstractmethod
    def apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> float:
        """Apply the rule and return the new price"""
        pass
    
    def __lt__(self, other):
        """Allow rules to be sorted by priority"""
        return self.priority < other.priority


class LowStockHighDemandRule(PricingRule):
    """Rule 1: Increase price by 15% if stock < 20 and quantity_sold > 30"""
    
    def __init__(self, priority: int = 1):
        super().__init__(priority)
    
    def should_apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> bool:
        return (int(product['stock']) < 20 and 
                int(sales_data.get('quantity_sold', 0)) > 30)
    
    def apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> float:
        current_price = float(product['current_price'])
        return current_price * 1.15


class DeadStockRule(PricingRule):
    """Rule 2: Decrease price by 30% if stock > 200 and quantity_sold == 0"""
    
    def __init__(self, priority: int = 2):
        super().__init__(priority)
    
    def should_apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> bool:
        return (int(product['stock']) > 200 and 
                int(sales_data.get('quantity_sold', 0)) == 0)
    
    def apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> float:
        current_price = float(product['current_price'])
        return current_price * 0.7


class OverstockedInventoryRule(PricingRule):
    """Rule 3: Decrease price by 10% if stock > 100 and quantity_sold < 20"""
    
    def __init__(self, priority: int = 3):
        super().__init__(priority)
    
    def should_apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> bool:
        return (int(product['stock']) > 100 and 
                int(sales_data.get('quantity_sold', 0)) < 20)
    
    def apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> float:
        current_price = float(product['current_price'])
        return current_price * 0.9


class MinimumProfitRule(PricingRule):
    """Rule 4: Ensure price is at least 20% above cost_price"""
    
    def __init__(self, priority: int = 4):
        super().__init__(priority)
    
    def should_apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> bool:
        # This rule is always checked
        return True
    
    def apply(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> float:
        cost_price = float(product['cost_price'])
        minimum_price = cost_price * 1.2
        current_new_price = float(product.get('new_price', product['current_price']))
        return max(current_new_price, minimum_price)


class PricingEngine:
    """
    Pricing engine that applies rules to products based on their priority
    """
    
    def __init__(self):
        self.rules: List[PricingRule] = []
    
    def add_rule(self, rule: PricingRule) -> None:
        """Add a rule to the engine"""
        self.rules.append(rule)
        # Sort rules by priority, with highest priority (lowest number) first
        self.rules.sort()
    
    def remove_rule(self, rule_class) -> None:
        """Remove a rule from the engine by class type"""
        self.rules = [rule for rule in self.rules if not isinstance(rule, rule_class)]
    
    def process_product(self, product: Dict[str, Any], sales_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single product through all applicable rules"""
        result = product.copy()
        result['old_price'] = float(product['current_price'])
        
        # First, apply the first applicable rule from rules 1-3 (if any)
        # These rules are mutually exclusive - only apply the highest priority rule
        applied_exclusive_rule = False
        
        # Find and apply highest priority rule that should be applied
        for rule in self.rules:
            # Skip the minimum profit rule which is always applied at the end
            if isinstance(rule, MinimumProfitRule):
                continue
                
            if rule.should_apply(product, sales_data):
                result['new_price'] = rule.apply(product, sales_data)
                applied_exclusive_rule = True
                break
        
        # If no exclusive rule was applied, use the current price
        if not applied_exclusive_rule:
            result['new_price'] = float(product['current_price'])
        
        # Always apply the minimum profit rule at the end if it exists
        min_profit_rules = [r for r in self.rules if isinstance(r, MinimumProfitRule)]
        if min_profit_rules:
            min_profit_rule = min_profit_rules[0]
            result['new_price'] = min_profit_rule.apply(result, sales_data)
        
        # Round to 2 decimal places
        result['new_price'] = round(result['new_price'], 2)
        
        return result


def load_sales_data(file_path: str) -> Dict[str, Dict[str, Any]]:
    """Load sales data from CSV file, indexed by SKU"""
    sales_data = {}
    
    with open(file_path, 'r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            sales_data[row['sku']] = row
    
    return sales_data


def process_products(products_file: str, sales_file: str, 
                     pricing_engine: PricingEngine) -> Iterator[Dict[str, Any]]:
    """
    Process products one by one to minimize memory usage
    Yields processed products with updated prices
    """
    # Load sales data into memory (it's typically smaller than product data)
    sales_data = load_sales_data(sales_file)
    
    with open(products_file, 'r', newline='') as file:
        reader = csv.DictReader(file)
        for product in reader:
            # Get sales data for this product (default to 0 sold if not found)
            product_sales = sales_data.get(product['sku'], {'quantity_sold': '0'})
            
            # Process the product and yield the result
            yield pricing_engine.process_product(product, product_sales)


def write_output(products: Iterator[Dict[str, Any]], output_file: str) -> None:
    """Write processed products to output CSV file"""
    fieldnames = ['sku', 'old_price', 'new_price']
    
    with open(output_file, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        
        for product in products:
            # Format prices with $ sign for output
            row = {
                'sku': product['sku'],
                'old_price': f"${product['old_price']:.2f}",
                'new_price': f"${product['new_price']:.2f}"
            }
            writer.writerow(row)


def calculate_file_hash(file_path: str) -> str:
    """Calculate a hash of the file contents to detect changes"""
    if not os.path.exists(file_path):
        return ""
        
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


class CSVChangeHandler(FileSystemEventHandler):
    def __init__(self, products_file: str, sales_file: str, output_file: str, pricing_engine: PricingEngine):
        self.products_file = products_file
        self.sales_file = sales_file
        self.output_file = output_file
        self.pricing_engine = pricing_engine
        
        # Store file hashes to avoid processing when files are saved but not actually changed
        self.products_hash = calculate_file_hash(products_file)
        self.sales_hash = calculate_file_hash(sales_file)
        
        # Process files initially
        self.process_files()
        
    def on_modified(self, event):
        # Check if the modified file is one we're watching
        if not event.is_directory:
            if event.src_path.endswith(self.products_file) or event.src_path.endswith(self.sales_file):
                self.process_files()
    
    def process_files(self):
        """Process files if they've changed based on hash comparison"""
        # Check if either file has changed
        new_products_hash = calculate_file_hash(self.products_file)
        new_sales_hash = calculate_file_hash(self.sales_file)
        
        files_changed = False
        
        if new_products_hash != self.products_hash:
            self.products_hash = new_products_hash
            files_changed = True
            
        if new_sales_hash != self.sales_hash:
            self.sales_hash = new_sales_hash
            files_changed = True
        
        # Only process if files actually changed
        if files_changed:
            try:
                # Process the products and write output
                processed_products = process_products(self.products_file, self.sales_file, self.pricing_engine)
                write_output(processed_products, self.output_file)
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Files changed - Updated prices written to {self.output_file}")
            except Exception as e:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error processing files: {str(e)}")


def run_interactive_pricing_engine():
    """Run the pricing engine in interactive mode, watching for file changes"""
    # Define input and output file paths
    products_file = 'products.csv'
    sales_file = 'sales.csv'
    output_file = 'updated_prices.csv'
    
    # Create the pricing engine and add rules in priority order
    engine = PricingEngine()
    engine.add_rule(LowStockHighDemandRule(priority=1))
    engine.add_rule(DeadStockRule(priority=2))
    engine.add_rule(OverstockedInventoryRule(priority=3))
    engine.add_rule(MinimumProfitRule(priority=4))
    
    # Set up the file system observer with our custom event handler
    event_handler = CSVChangeHandler(products_file, sales_file, output_file, engine)
    observer = Observer()
    
    # We'll watch the current directory
    watch_path = os.path.dirname(os.path.abspath(products_file)) or '.'
    observer.schedule(event_handler, path=watch_path, recursive=False)
    
    # Start the observer
    observer.start()
    
    print(f"Interactive pricing engine started.")
    print(f"Watching for changes in {products_file} and {sales_file}...")
    print(f"Press Ctrl+C to stop.")
    
    try:
        # Keep the script running until Ctrl+C is pressed
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # Stop the observer when Ctrl+C is pressed
        observer.stop()
    
    # Wait for the observer to finish
    observer.join()
    print("Interactive pricing engine stopped.")


if __name__ == "__main__":
    run_interactive_pricing_engine()