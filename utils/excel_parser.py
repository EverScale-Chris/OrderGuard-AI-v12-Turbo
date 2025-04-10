import pandas as pd
import logging
import os

def parse_excel_file(filepath):
    """
    Parses an Excel file to extract model numbers and prices
    
    Args:
        filepath (str): Path to the Excel file
    
    Returns:
        dict: Dictionary mapping model numbers to prices
    """
    try:
        # Log file info
        logging.debug(f"Parsing Excel file: {filepath}")
        logging.debug(f"File exists: {os.path.exists(filepath)}")
        logging.debug(f"File size: {os.path.getsize(filepath)} bytes")
        
        # Read the Excel file
        df = pd.read_excel(filepath)
        
        # Log column names
        logging.debug(f"Columns found in Excel file: {list(df.columns)}")
        
        # Check if required columns exist - looking for Item Number and Base Price columns
        required_columns = ["Item Number", "Base Price"]
        for col in required_columns:
            if col not in df.columns:
                logging.error(f"Required column '{col}' not found. Available columns: {list(df.columns)}")
                raise ValueError(f"Required column '{col}' not found in Excel file")
        
        # Extract model numbers and prices
        price_data = {}
        for _, row in df.iterrows():
            model_number = str(row["Item Number"]).strip()
            price = row["Base Price"]
            
            # Skip rows with empty model numbers
            if not model_number or pd.isna(model_number):
                continue
                
            # Convert price to float and format to 2 decimal places
            try:
                price = float(price)
                price_data[model_number] = f"{price:.2f}"
            except (ValueError, TypeError):
                logging.warning(f"Invalid price for model {model_number}: {price}")
        
        # Return the dictionary of model numbers to prices
        return price_data
    except Exception as e:
        logging.error(f"Error parsing Excel file: {str(e)}")
        raise
