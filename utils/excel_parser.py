import pandas as pd
import logging
import os

def parse_excel_file(filepath):
    """
    Parses an Excel file to extract model numbers and prices using column positions
    
    Args:
        filepath (str): Path to the Excel file
    
    Returns:
        dict: Dictionary mapping model numbers to price info with source column
    """
    try:
        # Log file info
        logging.debug(f"Parsing Excel file: {filepath}")
        logging.debug(f"File exists: {os.path.exists(filepath)}")
        logging.debug(f"File size: {os.path.getsize(filepath)} bytes")
        
        # Read the Excel file without headers to access by column position
        df = pd.read_excel(filepath, header=None)
        
        # Log shape and first few rows
        logging.debug(f"Excel file shape: {df.shape}")
        logging.debug(f"First 5 rows: {df.head().to_string()}")
        
        # Extract model numbers and prices using column positions
        # Column A (index 0) = Item Number
        # Column D (index 3) = Primary price location
        # Column E (index 4) = Secondary price location
        price_data = {}
        
        # Skip the header row (start from row 1)
        for index, row in df.iterrows():
            if index == 0:  # Skip header row
                continue
                
            # Get item number from Column A (index 0)
            if len(row) > 0:
                model_number = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
            else:
                continue
            
            # Skip rows with empty model numbers
            if not model_number or model_number == "nan":
                continue
            
            # Look for price in Column D first (index 3)
            price = None
            price_column = None
            
            if len(row) > 3 and pd.notna(row.iloc[3]):
                try:
                    price = float(row.iloc[3])
                    price_column = "D"
                except (ValueError, TypeError):
                    pass
            
            # If no valid price in Column D, try Column E (index 4)
            if price is None and len(row) > 4 and pd.notna(row.iloc[4]):
                try:
                    price = float(row.iloc[4])
                    price_column = "E"
                except (ValueError, TypeError):
                    pass
            
            # Store the price data with source column info
            if price is not None and price_column is not None:
                price_data[model_number] = {
                    "price": f"{price:.2f}",
                    "source_column": price_column
                }
                logging.debug(f"Found item {model_number}: ${price:.2f} from Column {price_column}")
            else:
                logging.warning(f"No valid price found for model {model_number} in columns D or E")
        
        logging.debug(f"Successfully parsed {len(price_data)} items from Excel file")
        return price_data
        
    except Exception as e:
        logging.error(f"Error parsing Excel file: {str(e)}")
        raise
