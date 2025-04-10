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
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found in environment variables")
        
        # Configure Gemini API
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro-vision')
        
        # Read the PDF file and encode it as base64
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Create prompt for Gemini API
        prompt = """
        Extract the following information from this Purchase Order PDF:
        - Model Number/SKU for each line item
        - Price listed on the PO for each line item
        
        Format the output as a JSON array of objects, where each object represents a line item with:
        - "model": the exact model number/SKU as written
        - "price": the price as a number (without currency symbols)
        
        Example output:
        [
            {"model": "ABC123", "price": "299.99"},
            {"model": "XYZ456", "price": "149.50"}
        ]
        
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
