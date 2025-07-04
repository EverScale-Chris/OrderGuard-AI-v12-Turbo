import os
import uuid
import json
import logging
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, g
from werkzeug.utils import secure_filename
import tempfile
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, login_required, current_user, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError

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

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models inside app context to avoid circular imports
with app.app_context():
    from models import User, PriceBook, PriceItem, ProcessedPO, POLineItem
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

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

# Authentication Forms
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_for('login') in next_page:
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/pricebooks')
@login_required
def pricebooks():
    return render_template('pricebooks.html')

@app.route('/process-po')
@login_required
def process_po():
    return render_template('process_po.html')

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        # Get all processed POs for this user
        processed_pos = ProcessedPO.query.filter_by(user_id=current_user.id).all()
        
        # Calculate overall metrics - only count each unique PO once
        po_numbers_processed = {}  # Track unique PO numbers and their data
        total_lines_reviewed = 0
        total_mismatches = 0
        total_not_found = 0
        total_matches = 0
        total_savings = 0.0
        
        for po in processed_pos:
            # Extract PO number from filename to ensure uniqueness
            po_number = extract_po_number_from_filename(po.filename)
            
            # Only process each unique PO number once (use the most recent one)
            if po_number not in po_numbers_processed:
                po_numbers_processed[po_number] = po
                
                line_items = POLineItem.query.filter_by(processed_po_id=po.id).all()
                
                for item in line_items:
                    total_lines_reviewed += 1
                    
                    if item.status == 'Match':
                        total_matches += 1
                    elif item.status == 'Mismatch':
                        total_mismatches += 1
                        # Calculate savings (when PO price < book price, meaning you're paying less)
                        if item.book_price and item.po_price < item.book_price:
                            total_savings += (item.book_price - item.po_price)
                    elif item.status == 'Model Not Found':
                        total_not_found += 1
        
        # Calculate percentages
        match_percentage = (total_matches / total_lines_reviewed * 100) if total_lines_reviewed > 0 else 0
        mismatch_percentage = (total_mismatches / total_lines_reviewed * 100) if total_lines_reviewed > 0 else 0
        not_found_percentage = (total_not_found / total_lines_reviewed * 100) if total_lines_reviewed > 0 else 0
        
        # Average savings per PO
        avg_savings_per_po = total_savings / len(po_numbers_processed) if po_numbers_processed else 0
        
        # Recent activity (last 10 POs)
        recent_pos = ProcessedPO.query.filter_by(user_id=current_user.id).order_by(ProcessedPO.processed_at.desc()).limit(10).all()
        
        metrics = {
            'total_pos': len(po_numbers_processed),  # Unique PO count
            'total_lines_reviewed': total_lines_reviewed,
            'total_matches': total_matches,
            'total_mismatches': total_mismatches,
            'total_not_found': total_not_found,
            'total_savings': total_savings,
            'match_percentage': round(match_percentage, 1),
            'mismatch_percentage': round(mismatch_percentage, 1),
            'not_found_percentage': round(not_found_percentage, 1),
            'avg_savings_per_po': avg_savings_per_po,
            'recent_pos': recent_pos
        }
        
        return render_template('dashboard.html', metrics=metrics)
        
    except Exception as e:
        logging.error(f"Error loading dashboard: {str(e)}")
        return render_template('dashboard.html', metrics={}, error="Unable to load dashboard data")

@app.route('/admin')
@login_required
def admin_panel():
    """Admin panel for managing user accounts"""
    # Check if current user is admin
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get all users with their stats
    users = db.session.query(User).all()
    user_stats = []
    
    for user in users:
        # Count user's price books and processed POs
        price_book_count = PriceBook.query.filter_by(user_id=user.id).count()
        processed_po_count = ProcessedPO.query.filter_by(user_id=user.id).count()
        
        user_stats.append({
            'user': user,
            'price_book_count': price_book_count,
            'processed_po_count': processed_po_count
        })
    
    return render_template('admin.html', user_stats=user_stats)

@app.route('/admin/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_admin(user_id):
    """Toggle admin status for a user"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent removing admin from yourself
    if user.id == current_user.id:
        flash('You cannot change your own admin status.', 'warning')
        return redirect(url_for('admin_panel'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = "granted" if user.is_admin else "removed"
    flash(f'Admin privileges {status} for {user.username}.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete a user account and all associated data"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'warning')
        return redirect(url_for('admin_panel'))
    
    try:
        # Delete user's processed POs (cascade will handle line items)
        ProcessedPO.query.filter_by(user_id=user.id).delete()
        
        # Delete user's price books (cascade will handle price items)
        PriceBook.query.filter_by(user_id=user.id).delete()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User {user.username} and all associated data deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting user {user_id}: {str(e)}")
        flash('Error deleting user. Please try again.', 'danger')
    
    return redirect(url_for('admin_panel'))

@app.route('/api/pricebooks', methods=['GET'])
@login_required
def get_price_books():
    try:
        # Get price books for the current user
        price_books = []
        # Apply row-level security - only show price books owned by the current user
        all_price_books = PriceBook.query.filter_by(user_id=current_user.id).order_by(PriceBook.name).all()
        
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
@login_required
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
            
            # Check if price book with the same name already exists for this user
            existing_book = PriceBook.query.filter_by(name=pricebook_name, user_id=current_user.id).first()
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
            
            # Create and save price book FIRST with the current user's ID
            new_price_book = PriceBook(id=pricebook_id, name=pricebook_name, user_id=current_user.id)
            db.session.add(new_price_book)
            db.session.commit()  # Save the price book first so items can reference it
            logging.debug(f"Created and saved price book: {new_price_book}")
            
            # Add price items in batches to handle large uploads (up to 5000+ items)
            item_count = 0
            batch_size = 50  # Larger batches for faster processing, but still safe
            items_to_add = []
            
            for model_number, price_info in price_data.items():
                try:
                    # Handle new data structure with price, source column, and Excel row
                    if isinstance(price_info, dict):
                        price_float = float(price_info["price"])
                        source_column = price_info["source_column"]
                        excel_row = price_info.get("excel_row")  # Keep as integer, not string
                        if excel_row == "Unknown":
                            excel_row = None
                    else:
                        # Fallback for old format
                        price_float = float(price_info)
                        source_column = "Unknown"
                        excel_row = None
                    
                    new_item = PriceItem(model_number=model_number, price=price_float, price_book_id=pricebook_id, source_column=source_column, excel_row=excel_row)
                    items_to_add.append(new_item)
                    item_count += 1
                    
                    # Process in batches
                    if len(items_to_add) >= batch_size:
                        db.session.add_all(items_to_add)
                        db.session.commit()
                        logging.info(f"Successfully processed batch: {item_count - len(items_to_add) + 1} to {item_count} items")
                        items_to_add = []
                    
                    # Skip individual item logging for performance
                except Exception as item_error:
                    logging.error(f"Error adding item {model_number}: {str(item_error)}")
            
            # Add any remaining items
            if items_to_add:
                db.session.add_all(items_to_add)
                db.session.commit()
                logging.debug(f"Committed final batch of {len(items_to_add)} items")
            
            logging.debug(f"Added {item_count} price items")
            logging.debug("Successfully completed price book upload")
            
            # Clean up the temporary file
            os.remove(filepath)
            
            return jsonify({"success": True, "message": f"Price book '{pricebook_name}' added successfully"})
        except Exception as e:
            db.session.rollback()  # Rollback the session in case of error
            logging.error(f"Error processing price book: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Invalid file type. Please upload an .xlsx file"}), 400

@app.route('/api/pricebooks/<price_book_id>', methods=['DELETE'])
@login_required
def delete_price_book(price_book_id):
    try:
        # Find the price book and verify ownership
        price_book = PriceBook.query.filter_by(id=price_book_id, user_id=current_user.id).first()
        if not price_book:
            return jsonify({"error": "Price book not found"}), 404
        
        # Delete all processed POs that reference this price book first
        processed_pos = ProcessedPO.query.filter_by(price_book_id=price_book_id, user_id=current_user.id).all()
        for po in processed_pos:
            # Delete all line items for each PO
            POLineItem.query.filter_by(processed_po_id=po.id).delete()
            # Delete the PO itself
            db.session.delete(po)
        
        # Delete all associated price items
        PriceItem.query.filter_by(price_book_id=price_book_id).delete()
        
        # Delete the price book
        db.session.delete(price_book)
        db.session.commit()
        
        return jsonify({"success": True, "message": f"Price book '{price_book.name}' deleted successfully"})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting price book: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/process-po', methods=['POST'])
@login_required
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
                
            # Check if the price book belongs to the current user
            if price_book.user_id != current_user.id:
                os.remove(filepath)  # Clean up
                return jsonify({"error": "You don't have permission to access this price book"}), 403
            
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
            
            # Save processed PO to database with current user's ID
            new_po = ProcessedPO(
                filename=filename,
                price_book_id=price_book_id,
                user_id=current_user.id
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
            
            # Calculate total value of errors
            total_error_value = sum(result.get("error_value", 0) for result in comparison_results)
            
            return jsonify({
                "success": True,
                "email_report": email_report,
                "comparison_results": comparison_results,
                "total_error_value": total_error_value
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
    
    # Create a dictionary to lookup price, Excel row number, and source column
    # CRITICAL: Only use the FIRST occurrence of each model number to prevent wrong line matching
    price_items_dict = {}
    for item in price_items:
        logging.debug(f"Item {item.model_number}: excel_row={item.excel_row}, source_column={item.source_column}")
        # Only add if we haven't seen this model number before
        if item.model_number not in price_items_dict:
            price_items_dict[item.model_number] = {
                "price": item.price,
                "excel_row": item.excel_row,  # Keep the actual value, don't convert to "Unknown"
                "source_column": item.source_column or "Unknown"  # Include source column info
            }
            logging.debug(f"FIRST occurrence of {item.model_number} at row {item.excel_row}")
        else:
            logging.warning(f"DUPLICATE model {item.model_number} at row {item.excel_row} - IGNORED (keeping first occurrence at row {price_items_dict[item.model_number]['excel_row']})")
    
    for po_line_number, item in enumerate(extracted_data, 1):
        logging.debug(f"PO line {po_line_number}: Raw extracted data = {item}")
        
        # Ensure there's always a valid model number (never null)
        model_number = item.get("model", "")
        if model_number is None or model_number == "":
            model_number = "Unknown Item"
            
        logging.debug(f"PO line {po_line_number}: Primary model = '{model_number}'")
        
        result = {
            "model": model_number,
            "po_price": item.get("price", "Extraction Issue"),
            "quantity": item.get("quantity", 1),  # Default to 1 if not found
            "status": "Data Extraction Issue",
            "po_line_number": po_line_number,  # Track PO line number
            "price_book_row": None,  # Initialize price book row to None
            "error_value": 0  # Total dollar amount of error for this line
        }
        
        # Include description if available
        if "description" in item:
            result["description"] = item["description"]
        
        # Skip if we couldn't extract the price
        if "price" not in item:
            results.append(result)
            continue
        
        # Check all potential model numbers found in the line (both primary and in description)
        matched_model = None
        lookup_model_for_dash = None  # Reset this for each line to prevent cross-contamination
        all_potential_models = []
        
        # Add the primary extracted model
        if "model" in item and item["model"]:
            all_potential_models.append(item["model"])
        
        # Also search for model numbers in the description using regex
        if "description" in item and item["description"]:
            description = item["description"]
            import re
            # Find model-like patterns in description, including BW-prefixed models
            model_patterns = re.findall(r'BW[A-Za-z0-9][-A-Za-z0-9_]{4,}[A-Za-z0-9]|[A-Za-z0-9][-A-Za-z0-9_]{4,}[A-Za-z0-9]', description)
            all_potential_models.extend(model_patterns)
            
            # Also check for known model numbers from price book
            for model_number in price_book_model_numbers:
                if model_number in description:
                    all_potential_models.append(model_number)
            
            # Specifically look for BW-prefixed patterns in the description
            bw_patterns = re.findall(r'BW[A-Z0-9][-A-Z0-9]{6,}', description, re.IGNORECASE)
            all_potential_models.extend(bw_patterns)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_models = []
        for model in all_potential_models:
            if model not in seen:
                seen.add(model)
                unique_models.append(model)
        

        
        logging.debug(f"PO line {po_line_number}: All potential models found: {unique_models}")
        

        # STEP 1: Direct exact matches first - use any model that matches exactly as-is
        for model in unique_models:
            if model in price_items_dict:
                matched_model = model
                logging.info(f"PO line {po_line_number}: STEP 1 - Direct exact match '{model}'")
                break
        
        # STEP 2: BW prefix search - for extracted BW models, remove BW and check price book
        if not matched_model:
            for model in unique_models:
                if model.startswith("BW"):
                    base_model = model[2:]  # Remove "BW" prefix
                    if base_model in price_items_dict:
                        matched_model = model  # Show BW model but map to base price
                        logging.info(f"PO line {po_line_number}: STEP 2 - BW model '{model}' maps to price book '{base_model}'")
                        break
        
        # STEP 3: B prefix search - for extracted B models, remove B and check price book
        if not matched_model:
            for model in unique_models:
                if model.startswith("B") and not model.startswith("BW"):
                    base_model = model[1:]  # Remove "B" prefix
                    if base_model in price_items_dict:
                        matched_model = model  # Show B model but map to base price
                        logging.info(f"PO line {po_line_number}: STEP 3 - B model '{model}' maps to price book '{base_model}'")
                        break
        
        # STEP 4: Dash-removal fallback search - try matching without dashes
        if not matched_model:
            # Create a mapping of dash-removed models to original models from price book
            dashless_price_book = {}
            for original_model in price_items_dict.keys():
                dashless_model = original_model.replace("-", "")
                dashless_price_book[dashless_model] = original_model
            
            # Try all extracted models with dashes removed
            for model in unique_models:
                dashless_extracted = model.replace("-", "")
                if dashless_extracted in dashless_price_book:
                    original_price_book_model = dashless_price_book[dashless_extracted]
                    # CRITICAL: Only allow if they are EXACTLY the same when dashes are removed
                    # The only difference should be the presence/absence of dashes
                    if dashless_extracted == original_price_book_model.replace("-", ""):
                        matched_model = model  # Show original extracted model
                        lookup_model_for_dash = original_price_book_model  # Use original price book model
                        logging.info(f"PO line {po_line_number}: STEP 4 - Dash-removal match '{model}' maps to price book '{lookup_model_for_dash}'")
                        break
                    else:
                        logging.warning(f"PO line {po_line_number}: REJECTED dash-removal match '{model}' to '{original_price_book_model}' - not identical when dashes removed")
                        continue
                
                # Also try BW prefix removal + dash removal
                if model.startswith("BW"):
                    base_model_no_bw = model[2:]  # Remove BW
                    dashless_base = base_model_no_bw.replace("-", "")
                    if dashless_base in dashless_price_book:
                        original_price_book_model = dashless_price_book[dashless_base]
                        # CRITICAL: Only allow if they are EXACTLY the same when dashes are removed
                        if dashless_base == original_price_book_model.replace("-", ""):
                            matched_model = model  # Show BW model
                            lookup_model_for_dash = original_price_book_model
                            logging.info(f"PO line {po_line_number}: STEP 4 - BW + dash-removal match '{model}' (base: '{base_model_no_bw}') maps to price book '{lookup_model_for_dash}'")
                            break
                        else:
                            logging.warning(f"PO line {po_line_number}: REJECTED BW + dash-removal match '{model}' to '{original_price_book_model}' - not identical when dashes removed")
                            continue
                
                # Also try B prefix removal + dash removal
                if model.startswith("B") and not model.startswith("BW"):
                    base_model_no_b = model[1:]  # Remove B
                    dashless_base = base_model_no_b.replace("-", "")
                    if dashless_base in dashless_price_book:
                        original_price_book_model = dashless_price_book[dashless_base]
                        # CRITICAL: Only allow if they are EXACTLY the same when dashes are removed
                        if dashless_base == original_price_book_model.replace("-", ""):
                            matched_model = model  # Show B model
                            lookup_model_for_dash = original_price_book_model
                            logging.info(f"PO line {po_line_number}: STEP 4 - B + dash-removal match '{model}' (base: '{base_model_no_b}') maps to price book '{lookup_model_for_dash}'")
                            break
                        else:
                            logging.warning(f"PO line {po_line_number}: REJECTED B + dash-removal match '{model}' to '{original_price_book_model}' - not identical when dashes removed")
                            continue
        
        # STEP 5: If no matches found, it will be marked as "NOT FOUND"
        

        

        
        # If we found a match, compare prices
        if matched_model:
            # Update the result model to show the matched model, not the original extracted model
            result["model"] = matched_model
            logging.debug(f"PO line {po_line_number}: Found match for '{matched_model}'")
            
            # Handle BW/B prefixed models and dash-removal matches
            lookup_model = matched_model
            
            # Check if we used dash-removal matching (lookup_model_for_dash was set)
            if lookup_model_for_dash is not None:
                lookup_model = lookup_model_for_dash
            elif matched_model.startswith("BW"):
                # For BW models, always look up price using base model (without BW)
                lookup_model = matched_model[2:]  # Remove BW prefix for price lookup
            elif matched_model.startswith("B") and not matched_model.startswith("BW"):
                # For B models, always look up price using base model (without B)
                lookup_model = matched_model[1:]  # Remove B prefix for price lookup
            
            if lookup_model not in price_items_dict:
                logging.error(f"PO line {po_line_number}: lookup_model '{lookup_model}' not found in price book")
                result["status"] = "Lookup Error"
                results.append(result)
                continue
                
            item_data = price_items_dict[lookup_model]
            book_price = item_data["price"]
            result["book_price"] = book_price
            result["price_book_row"] = item_data["excel_row"]
            result["source_column"] = item_data["source_column"]
            
            # Compare prices
            try:
                po_price = float(item["price"])
                book_price_float = float(book_price)
                quantity = float(result["quantity"])
                
                if po_price == book_price_float:
                    result["status"] = "Match"
                else:
                    result["status"] = "Mismatch"
                    price_diff = abs(po_price - book_price_float)
                    result["discrepancy"] = price_diff
                    # Calculate total error value: price difference * quantity
                    result["error_value"] = price_diff * quantity
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
    
    # Get all items with issues (mismatches and model not found)
    problem_items = [item for item in comparison_results if item['status'] in ["Mismatch", "Model Not Found"]]
    
    # Use actual PO line numbers, not a counter
    for item in problem_items:
        try:
            po_price = float(item['po_price'])
            po_price_formatted = f"${po_price:.2f}"
        except (ValueError, TypeError):
            po_price_formatted = f"${item['po_price']}"
            
        # Get the actual PO line number
        po_line = item.get('po_line_number', 'Unknown')
        
        # Format the message based on the status
        if item['status'] == "Mismatch":
            try:
                book_price = float(item['book_price'])
                book_price_formatted = f"${book_price:.2f}"
            except (ValueError, TypeError):
                book_price_formatted = f"${item['book_price']}"
            
            # Include source column information if available
            source_info = f" (Row {item['price_book_row']})" if item.get('price_book_row') else ""
            email_text += f"PO Line {po_line} - {item['model']} - PO Price {po_price_formatted} - Price Book {book_price_formatted}{source_info}\n"
        elif item['status'] == "Model Not Found":
            email_text += f"PO Line {po_line} - {item['model']} - Model not found in price book\n"
    
    # If there are no problem items
    if not problem_items:
        email_text += "No price discrepancies found. All prices match our records.\n"
    
    email_text += """
Please revise these items and resubmit at your convenience. We truly appreciate your business.
"""
    
    return email_text

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
