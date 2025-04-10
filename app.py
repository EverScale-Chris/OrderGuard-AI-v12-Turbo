import os
import uuid
import json
import logging
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
import tempfile
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Define base model class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the Base class
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key-for-development")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Import models after initializing db to avoid circular imports
with app.app_context():
    from models import PriceBook, PriceItem, ProcessedPO, POLineItem
    db.create_all()

# Import Excel parser and PDF parser
from utils.excel_parser import parse_excel_file
from utils.pdf_parser import extract_data_from_pdf

# Configure temporary file storage
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS_XLSX = {'xlsx'}
ALLOWED_EXTENSIONS_PDF = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pricebooks')
def pricebooks():
    return render_template('pricebooks.html')

@app.route('/process-po')
def process_po():
    return render_template('process_po.html')

@app.route('/api/pricebooks', methods=['GET'])
def get_price_books():
    try:
        # Get all price books from PostgreSQL instead of Replit DB
        price_books = []
        all_price_books = PriceBook.query.order_by(PriceBook.name).all()
        
        for book in all_price_books:
            price_books.append({
                "id": book.id,
                "name": book.name,
                "created_at": book.created_at.isoformat() if book.created_at else None
            })
            
        return jsonify(price_books)
    except Exception as e:
        logging.error(f"Error getting price books: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/pricebooks', methods=['POST'])
def upload_price_book():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    pricebook_name = request.form.get('pricebook_name', '')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not pricebook_name:
        return jsonify({"error": "Price book name is required"}), 400
    
    if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_XLSX):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Parse the Excel file
            price_data = parse_excel_file(filepath)
            
            # Check if price book with the same name already exists
            existing_book = PriceBook.query.filter_by(name=pricebook_name).first()
            if existing_book:
                os.remove(filepath)  # Clean up the temp file
                return jsonify({"error": f"Price book '{pricebook_name}' already exists"}), 400
            
            # Add to database using SQLAlchemy
            pricebook_id = str(uuid.uuid4())
            logging.debug(f"Generated price book ID: {pricebook_id}")
            logging.debug(f"Price book name: {pricebook_name}")
            logging.debug(f"Number of items in price data: {len(price_data)}")
            
            # Log a few sample items
            items_sample = list(price_data.items())[:5] if price_data else []
            logging.debug(f"Sample items: {items_sample}")
            
            # Create new price book
            new_price_book = PriceBook(id=pricebook_id, name=pricebook_name)
            logging.debug(f"Created price book object: {new_price_book}")
            
            # Add price items
            item_count = 0
            for model_number, price in price_data.items():
                try:
                    price_float = float(price)
                    new_item = PriceItem(model_number=model_number, price=price_float, price_book_id=pricebook_id)
                    db.session.add(new_item)
                    item_count += 1
                except Exception as item_error:
                    logging.error(f"Error adding item {model_number}: {str(item_error)}")
            
            logging.debug(f"Added {item_count} price items")
            
            # Add price book and commit transaction
            db.session.add(new_price_book)
            logging.debug("Added price book to session, committing...")
            db.session.commit()
            logging.debug("Successfully committed to database")
            
            # Clean up the temporary file
            os.remove(filepath)
            
            return jsonify({"success": True, "message": f"Price book '{pricebook_name}' added successfully"})
        except Exception as e:
            db.session.rollback()  # Rollback the session in case of error
            logging.error(f"Error processing price book: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Invalid file type. Please upload an .xlsx file"}), 400

@app.route('/api/process-po', methods=['POST'])
def process_purchase_order():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    price_book_id = request.form.get('pricebook_id', '')
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not price_book_id:
        return jsonify({"error": "Price book selection is required"}), 400
    
    if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_PDF):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Get price book data from PostgreSQL
            price_book = PriceBook.query.get(price_book_id)
            if not price_book:
                os.remove(filepath)  # Clean up
                return jsonify({"error": "Selected price book not found"}), 404
            
            # Extract data from PDF using Gemini API
            extracted_data = extract_data_from_pdf(filepath)
            
            # Create a dictionary of model numbers to prices for the selected price book
            price_book_data = {}
            price_items = PriceItem.query.filter_by(price_book_id=price_book_id).all()
            for item in price_items:
                price_book_data[item.model_number] = item.price
            
            # Prepare the price book data structure for the comparison function
            price_book_for_comparison = {
                'id': price_book.id,
                'name': price_book.name,
                'data': price_book_data
            }
            
            # Compare extracted data with price book
            comparison_results = compare_with_price_book(extracted_data, price_book_for_comparison)
            
            # Generate email report with the filename to extract PO number
            email_report = generate_email_report(comparison_results, price_book.name, filename)
            
            # Save processed PO to database
            new_po = ProcessedPO(
                filename=filename,
                price_book_id=price_book_id
            )
            db.session.add(new_po)
            db.session.flush()  # Get the ID without committing
            
            # Save line items
            for result in comparison_results:
                # Ensure we have a non-null model number (use a default if needed)
                model_number = result.get("model", "Unknown")
                if model_number is None or model_number == "":
                    model_number = "Unknown"
                    
                line_item = POLineItem(
                    processed_po_id=new_po.id,
                    model_number=model_number,
                    po_price=float(result["po_price"]) if isinstance(result["po_price"], (int, float, str)) else 0.0,
                    book_price=float(result["book_price"]) if "book_price" in result and isinstance(result["book_price"], (int, float, str)) else None,
                    status=result["status"],
                    discrepancy=float(result["discrepancy"]) if "discrepancy" in result and isinstance(result["discrepancy"], (int, float, str)) else None
                )
                db.session.add(line_item)
            
            db.session.commit()
            
            # Clean up the temporary file
            os.remove(filepath)
            
            return jsonify({
                "success": True,
                "email_report": email_report,
                "comparison_results": comparison_results
            })
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            logging.error(f"Error processing purchase order: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Invalid file type. Please upload a PDF file"}), 400

def compare_with_price_book(extracted_data, price_book):
    results = []
    price_data = price_book['data']
    price_book_model_numbers = set(price_data.keys())
    price_book_id = price_book['id']
    
    # Get all price items for this price book with their IDs to use as row numbers
    price_items = PriceItem.query.filter_by(price_book_id=price_book_id).all()
    
    # Create a dictionary to lookup both price and row number (using the DB ID as row number)
    price_items_dict = {}
    for item in price_items:
        price_items_dict[item.model_number] = {
            "price": item.price,
            "row_number": item.id  # Using database ID as row reference
        }
    
    for item in extracted_data:
        # Ensure there's always a valid model number (never null)
        model_number = item.get("model", "")
        if model_number is None or model_number == "":
            model_number = "Unknown Item"
            
        result = {
            "model": model_number,
            "po_price": item.get("price", "Extraction Issue"),
            "status": "Data Extraction Issue",
            "row_number": None  # Initialize row number to None
        }
        
        # Include description if available
        if "description" in item:
            result["description"] = item["description"]
        
        # Skip if we couldn't extract the price
        if "price" not in item:
            results.append(result)
            continue
        
        # First try direct match with model number
        matched_model = None
        
        if "model" in item and item["model"] in price_items_dict:
            matched_model = item["model"]
        else:
            # If no direct match, try to find model number in description
            if "description" in item and item["description"]:
                description = item["description"]
                
                # Try to find any price book model number within the description
                for model_number in price_book_model_numbers:
                    if model_number in description:
                        matched_model = model_number
                        # Update the model in the result to the matched one from description
                        result["model"] = model_number
                        logging.info(f"Found model {model_number} in description: {description}")
                        break
        
        # If we found a match, compare prices
        if matched_model:
            item_data = price_items_dict[matched_model]
            book_price = item_data["price"]
            result["book_price"] = book_price
            result["row_number"] = item_data["row_number"]
            
            # Compare prices
            try:
                if float(item["price"]) == float(book_price):
                    result["status"] = "Match"
                else:
                    result["status"] = "Mismatch"
                    result["discrepancy"] = abs(float(item["price"]) - float(book_price))
            except (ValueError, TypeError):
                # Handle case where price might not be convertible to float
                result["status"] = "Price Format Error"
        else:
            result["status"] = "Model Not Found"
        
        results.append(result)
    
    return results

def extract_po_number_from_filename(filename):
    """
    Attempts to extract a PO number from the PDF filename
    
    Args:
        filename (str): The filename of the PDF
        
    Returns:
        str: Extracted PO number or a default placeholder
    """
    # Remove file extension and path
    base_name = os.path.basename(filename)
    base_name = os.path.splitext(base_name)[0]
    
    # Common patterns in PO filenames
    po_patterns = [
        r'P0*(\d+)',  # Matches P0000123 or P123
        r'PO[-_]?0*(\d+)',  # Matches PO-123, PO_123, PO123
        r'Purchase[-_]?Order[-_]?0*(\d+)',  # Matches Purchase-Order-123
        r'Order[-_]?0*(\d+)',  # Matches Order-123
        r'(\d{5,})',  # Matches any sequence of 5+ digits (likely a PO number)
    ]
    
    for pattern in po_patterns:
        match = re.search(pattern, base_name, re.IGNORECASE)
        if match:
            return match.group(1)
            
    # If no pattern matches, use the filename without extension as fallback
    return base_name

def generate_email_report(comparison_results, price_book_name, filename="Unknown PO"):
    # Extract PO number from filename if available
    po_number = extract_po_number_from_filename(filename)
    
    email_text = f"""Subject: Purchase Order Review - {po_number}

Hi,

I have reviewed your purchase order ({po_number}). The following discrepancies have been found:

"""
    
    # Get only the mismatched items
    mismatched_items = [item for item in comparison_results if item['status'] == "Mismatch"]
    
    # Add a line number counter
    for i, item in enumerate(mismatched_items, 1):
        try:
            po_price = float(item['po_price'])
            po_price_formatted = f"${po_price:.2f}"
        except (ValueError, TypeError):
            po_price_formatted = f"${item['po_price']}"
            
        try:
            book_price = float(item['book_price'])
            book_price_formatted = f"${book_price:.2f}"
        except (ValueError, TypeError):
            book_price_formatted = f"${item['book_price']}"
            
        email_text += f"Line Item {i} - {item['model']} - PO Price {po_price_formatted} - Price Book {book_price_formatted}\n"
    
    # If there are no mismatched items
    if not mismatched_items:
        email_text += "No price discrepancies found. All prices match our records.\n"
    
    email_text += """
Please revise these items and resubmit at your convenience. We truly appreciate your business.
"""
    
    return email_text

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
