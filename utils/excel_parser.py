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
        
        # Get column headers from the first row
        column_headers = {}
        if len(df) > 0:
            first_row = df.iloc[0]
            for col_idx in range(len(first_row)):
                if pd.notna(first_row.iloc[col_idx]):
                    column_headers[col_idx] = str(first_row.iloc[col_idx]).strip()
        
        logging.debug(f"Column headers found: {column_headers}")
        
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
            
            # Look for price in Column E first (index 4) - NOW PRIMARY
            price = None
            price_column_header = None
            
            if len(row) > 4 and pd.notna(row.iloc[4]):
                try:
                    price = float(row.iloc[4])
                    price_column_header = column_headers.get(4, "Column E")
                except (ValueError, TypeError):
                    pass
            
            # If no valid price in Column E, try Column D (index 3) as fallback
            if price is None and len(row) > 3 and pd.notna(row.iloc[3]):
                try:
                    price = float(row.iloc[3])
                    price_column_header = column_headers.get(3, "Column D")
                except (ValueError, TypeError):
                    pass
            
            # Store the price data with source column info and Excel row number
            if price is not None and price_column_header is not None:
                excel_row_number = index + 1  # Convert to 1-based row number (Excel style)
                price_data[model_number] = {
                    "price": f"{price:.2f}",
                    "source_column": price_column_header,
                    "excel_row": excel_row_number
                }
                logging.debug(f"Found item {model_number}: ${price:.2f} from '{price_column_header}' at Excel row {excel_row_number}")
            else:
                logging.warning(f"No valid price found for model {model_number} in columns D or E")
        
        logging.debug(f"Successfully parsed {len(price_data)} items from Excel file")
        return price_data
        
    except Exception as e:
        logging.error(f"Error parsing Excel file: {str(e)}")
        raise
