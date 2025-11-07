import frappe
import pytesseract
from PIL import Image
# import openai
import os
import json

@frappe.whitelist(allow_guest=True)
def extract_and_format_image_data():
    """
    API: Extract text from image and return structured data.
    Endpoint: /api/method/exim_backend.api.image_reader.extract_and_format_image_data
    """
    file = frappe.request.files.get("image")
    if not file:
        frappe.throw("Please upload an image file")

    # Save temporarily
    temp_path = frappe.get_site_path("public", "temp")
    os.makedirs(temp_path, exist_ok=True)
    filepath = os.path.join(temp_path, file.filename)
    file.save(filepath)

    # Extract text
    extracted_text = pytesseract.image_to_string(Image.open(filepath))

    # Load OpenAI key
    openai.api_key = frappe.conf.get("openai_api_key")

    # Format data intelligently using AI
    prompt = f"""
    You are a smart text parser. Analyze the following OCR text and return a well-structured JSON
    with meaningful key-value pairs. If possible, categorize it logically (e.g., invoice, list, note, etc.)
    Do not include explanations — return only valid JSON.

    Text:
    {extracted_text}
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    formatted_data = response["choices"][0]["message"]["content"]

    # Clean up
    os.remove(filepath)

    try:
        formatted_data_json = json.loads(formatted_data)
    except:
        formatted_data_json = {"parsed_output": formatted_data}

    return {
        "status": "success",
        "data": formatted_data_json,
        "raw_text": extracted_text
    }





import frappe
import pytesseract
from PIL import Image
import os

@frappe.whitelist(allow_guest=True, methods=["POST"])
def extract_text_from_image():
    """
    API Endpoint: /api/method/exim_backend.api.image_reader.extract_text_from_image
    Accepts: image (form-data)
    Returns: extracted text using OCR
    
    Example curl usage:
    curl --location --request POST 'http://127.0.0.1:8000/api/method/exim_backend.api.image_reader.extract_text_from_image' \\
         --header 'Cookie: full_name=Guest; sid=Guest; system_user=no; user_id=Guest; user_image=' \\
         --form 'image=@"/path/to/your/image.png"'
    
    Note: 
    - Use POST method (not PUT)
    - Form field must be named "image" (not just =@filename)
    """
    # 1. Get image file from request
    file = frappe.request.files.get("image")
    if not file:
        frappe.throw("Please upload an image file")

    # 2. Save temporarily
    temp_path = frappe.get_site_path("public", "temp")
    os.makedirs(temp_path, exist_ok=True)
    filepath = os.path.join(temp_path, file.filename)
    file.save(filepath)

    # 3. Perform OCR (extract text)
    extracted_text = pytesseract.image_to_string(Image.open(filepath))

    # 4. Cleanup temporary file
    os.remove(filepath)

    # 5. Return extracted text
    return {
        "status": "success",
        "extracted_text": extracted_text.strip()
    }



# 1. extract text from image is done
# 2. understand the extracted text, 
    #   and try to come up with the relation between text and erpnext doctypes. 
# 3. if the relation is found, then create a new document of the found doctype. 
# 4. if the relation is not found, then return the return the extracted text and ask the user 
    # to do which type of work next?
# 5. all this in a simple minimal chat like interface.
# 6. create a new page for this all chat interface. 
