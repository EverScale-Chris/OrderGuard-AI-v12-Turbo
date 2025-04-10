import os
import uuid
import json
import logging
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
        price_books = get_all_price_books()
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
            
            # Add to database
            pricebook_id = str(uuid.uuid4())
            add_price_book(pricebook_id, pricebook_name, price_data)
            
            # Clean up the temporary file
            os.remove(filepath)
            
            return jsonify({"success": True, "message": f"Price book '{pricebook_name}' added successfully"})
        except Exception as e:
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
            
            # Get price book data
            price_book = get_price_book_data(price_book_id)
            if not price_book:
                return jsonify({"error": "Selected price book not found"}), 404
            
            # Extract data from PDF using Gemini API
            extracted_data = extract_data_from_pdf(filepath)
            
            # Compare extracted data with price book
            comparison_results = compare_with_price_book(extracted_data, price_book)
            
            # Generate email report
            email_report = generate_email_report(comparison_results, price_book['name'])
            
            # Clean up the temporary file
            os.remove(filepath)
            
            return jsonify({
                "success": True,
                "email_report": email_report,
                "comparison_results": comparison_results
            })
        except Exception as e:
            logging.error(f"Error processing purchase order: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Invalid file type. Please upload a PDF file"}), 400

def compare_with_price_book(extracted_data, price_book):
    results = []
    price_data = price_book['data']
    
    for item in extracted_data:
        result = {
            "model": item.get("model", "Extraction Issue"),
            "po_price": item.get("price", "Extraction Issue"),
            "status": "Data Extraction Issue"
        }
        
        # Skip if we couldn't extract the model or price
        if "model" not in item or "price" not in item:
            results.append(result)
            continue
        
        # Check if model exists in price book
        if item["model"] in price_data:
            book_price = price_data[item["model"]]
            result["book_price"] = book_price
            
            # Compare prices
            if float(item["price"]) == float(book_price):
                result["status"] = "Match"
            else:
                result["status"] = "Mismatch"
                result["discrepancy"] = abs(float(item["price"]) - float(book_price))
        else:
            result["status"] = "Model Not Found"
        
        results.append(result)
    
    return results

def generate_email_report(comparison_results, price_book_name):
    email_text = f"""Subject: Review of your Purchase Order - Ref Price Book: {price_book_name}

Hi,

Thank you for your Purchase Order. We have reviewed it against our "{price_book_name}" price book. The following details were found for the line items based on the data provided:

"""
    
    for item in comparison_results:
        email_text += f"*   **Line Item:** {item['model']}\n"
        email_text += f"    *   **PO Price:** ${item['po_price']}\n"
        
        if item['status'] == "Match":
            email_text += f"    *   **Status:** Matched Price Book\n"
        elif item['status'] == "Mismatch":
            email_text += f"    *   **Status:** Mismatch - Price Book price is ${item['book_price']}. Discrepancy: ${item['discrepancy']:.2f}.\n"
        elif item['status'] == "Model Not Found":
            email_text += f"    *   **Status:** Model Not Found in Selected Price Book. Please verify the model number.\n"
        else:
            email_text += f"    *   **Status:** Data Extraction Issue from PO Line Item. Manual review required.\n"
    
    email_text += f"""
Please review any items marked with discrepancies or issues based on the "{price_book_name}" pricing.

Best regards,

Your Company Name
"""
    
    return email_text

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
