from replit import db
import json
import logging

def get_all_price_books():
    """
    Retrieves all price books from the Replit Database
    
    Returns:
        list: List of price book metadata (id and name)
    """
    try:
        # Get the price book index
        price_book_index = db.get("pricebook_index", {})
        
        # Return list of price books with id and name
        return [{"id": k, "name": v} for k, v in price_book_index.items()]
    except Exception as e:
        logging.error(f"Error retrieving price books: {str(e)}")
        return []

def add_price_book(pricebook_id, pricebook_name, price_data):
    """
    Adds a new price book to the Replit Database
    
    Args:
        pricebook_id (str): Unique identifier for the price book
        pricebook_name (str): Name of the price book
        price_data (dict): Dictionary of model numbers to prices
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the current index or create it if it doesn't exist
        price_book_index = db.get("pricebook_index", {})
        
        # Check if the name already exists
        for existing_id, existing_name in price_book_index.items():
            if existing_name == pricebook_name:
                raise ValueError(f"A price book with the name '{pricebook_name}' already exists")
        
        # Add the new price book to the index
        price_book_index[pricebook_id] = pricebook_name
        db["pricebook_index"] = price_book_index
        
        # Store the price book data
        db[f"pricebook_data_{pricebook_id}"] = price_data
        
        return True
    except Exception as e:
        logging.error(f"Error adding price book: {str(e)}")
        raise

def get_price_book_data(pricebook_id):
    """
    Retrieves a specific price book's data
    
    Args:
        pricebook_id (str): ID of the price book to retrieve
    
    Returns:
        dict: Dictionary containing the price book data and name
    """
    try:
        # Get the price book index
        price_book_index = db.get("pricebook_index", {})
        
        # Check if the price book exists
        if pricebook_id not in price_book_index:
            return None
        
        # Get the price book name and data
        pricebook_name = price_book_index[pricebook_id]
        price_data = db.get(f"pricebook_data_{pricebook_id}", {})
        
        return {
            "id": pricebook_id,
            "name": pricebook_name,
            "data": price_data
        }
    except Exception as e:
        logging.error(f"Error retrieving price book data: {str(e)}")
        return None

def delete_price_book(pricebook_id):
    """
    Deletes a price book from the Replit Database
    
    Args:
        pricebook_id (str): ID of the price book to delete
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the price book index
        price_book_index = db.get("pricebook_index", {})
        
        # Check if the price book exists
        if pricebook_id not in price_book_index:
            return False
        
        # Remove from the index
        del price_book_index[pricebook_id]
        db["pricebook_index"] = price_book_index
        
        # Delete the price book data
        if f"pricebook_data_{pricebook_id}" in db:
            del db[f"pricebook_data_{pricebook_id}"]
        
        return True
    except Exception as e:
        logging.error(f"Error deleting price book: {str(e)}")
        return False
