import os
import google.generativeai as genai
import logging
import base64

def extract_data_from_pdf(pdf_path):
    """
    Extracts model numbers and prices from a PDF file using Google Gemini API
    
    Args:
        pdf_path (str): Path to the PDF file
    
    Returns:
        list: List of dictionaries containing model and price
    """
    try:
        # Get API key from environment variable
        api_key = os.environ.get("GOOGLE_GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Google Gemini API key not found in environment variables")
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        # Use Gemini 1.5 flash model - the currently available model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Read the PDF file and encode it as base64
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Create prompt for Gemini API
        prompt = """
        Extract the following information from this Purchase Order PDF:
        - Item Number/Model Number/SKU/Part Number for each line item (look for any identifier that would match a product code)
        - Price listed on the PO for each line item (look for any of these: Unit Price, Base Price, Price, Extended Price)
        
        Format the output as a JSON array of objects, where each object represents a line item with:
        - "model": the exact item number/model number/SKU as written
        - "price": the price as a number (without currency symbols)
        - "description": the full description text if available (this can help with matching)
        
        Example output:
        [
            {"model": "ABC123", "price": "299.99", "description": "Widget Type A Blue 12-pack"},
            {"model": "XYZ456", "price": "149.50", "description": "Premium Service Kit (RED-789)"}
        ]
        
        IMPORTANT: For model/item numbers:
        - Pay special attention to the Description column, as it may contain the actual item number needed for matching
        - Look for text patterns like: "Item: ABC123", "Model #ABC123", "Part ABC123", "SKU ABC123", "part number ABC123" within descriptions
        - Look for alphanumeric codes that appear in a standardized format (like AB-1234, 123ABC, etc.)
        - Look for codes that are in all caps or have a mix of letters and numbers
        - Look for columns or fields labeled: Item Number, Model, SKU, Part #, Description, Product ID
        - If you find more than one potential product identifier, extract the most likely one based on format
        
        For prices:
        - Look for columns or fields labeled: Unit Price, Price, Base Price, Amount, Extended Price, Each, EA Price
        - If there are multiple prices, choose the one that represents the per-unit price, not the extended/total price
        
        Only include items where you can clearly identify both the model number and price. If there's ambiguity or you can't extract the data reliably, note it in the results.
        Do not guess or infer any information that is not explicitly present in the document.
        """
        
        # Send the PDF to Gemini API
        response = model.generate_content([
            prompt,
            {"mime_type": "application/pdf", "data": pdf_base64}
        ])
        
        # Extract the JSON data from the response
        response_text = response.text
        
        # Try to find JSON data in the response
        import re
        import json
        
        # Look for JSON array pattern
        json_pattern = r'\[\s*\{.*?\}\s*\]'
        json_match = re.search(json_pattern, response_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(0)
            try:
                extracted_data = json.loads(json_str)
                logging.info(f"Successfully extracted {len(extracted_data)} line items from PDF")
                
                # Log each extracted line for debugging
                for i, item in enumerate(extracted_data, 1):
                    if i == 2:  # Focus on line 2 specifically
                        logging.error(f"PDF EXTRACTION Line 2: FULL DATA = {item}")
                    logging.debug(f"PDF Line {i}: model='{item.get('model', 'N/A')}', price='{item.get('price', 'N/A')}', description='{item.get('description', 'N/A')[:100]}...'")
                
                return extracted_data
            except json.JSONDecodeError as e:
                logging.error(f"Error parsing JSON from Gemini API response: {str(e)}")
                raise ValueError("Failed to parse extracted data as JSON")
        else:
            logging.error("No valid JSON found in Gemini API response")
            raise ValueError("Failed to extract structured data from PDF")
            
    except Exception as e:
        logging.error(f"Error extracting data from PDF: {str(e)}")
        raise
