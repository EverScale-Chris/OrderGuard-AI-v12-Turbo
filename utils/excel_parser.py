import pandas as pd
import logging

def parse_excel_file(filepath):
    """
    Parses an Excel file to extract model numbers and prices
    
    Args:
        filepath (str): Path to the Excel file
    
    Returns:
        dict: Dictionary mapping model numbers to prices
    """
    try:
        # Read the Excel file
        df = pd.read_excel(filepath)
        
        # Check if required columns exist - looking for Model Number and Correct Base Price columns
        required_columns = ["Model Number", "Correct Base Price"]
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' not found in Excel file")
        
        # Extract model numbers and prices
        price_data = {}
        for _, row in df.iterrows():
            model_number = str(row["Model Number"]).strip()
            price = row["Correct Base Price"]
            
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
