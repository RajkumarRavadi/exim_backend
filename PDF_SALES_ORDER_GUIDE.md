# PDF Sales Order Processing - Complete Guide

## Overview

This feature allows you to create sales orders directly from PDF documents using AI-powered data extraction. The system analyzes PDFs (including text, tables, and images), extracts relevant information, and creates structured sales orders after user confirmation.

## Workflow

```
1. Upload PDF → 2. AI Extracts Data → 3. User Reviews → 4. User Confirms → 5. Sales Order Created
```

### Detailed Flow:
1. **PDF Upload**: User uploads a sales order PDF to the system
2. **Content Extraction**: System extracts text, tables, and images from PDF
3. **AI Processing**: AI analyzes content and structures it into sales order format
4. **Data Validation**: System validates customer/item existence and adds warnings
5. **User Confirmation**: Present formatted data to user for review
6. **Data Correction** (optional): User can modify extracted data
7. **Order Creation**: System creates sales order using existing handler

## Installation

### 1. Install Python Dependencies

```bash
cd /home/frappeuser/frappe-bench-v15/apps/exim_backend
pip install -r pdf_requirements.txt
```

### 2. Install System Dependencies (for pdf2image)

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

### 3. Configure AI Settings (Optional but Recommended)

For best results, configure OpenAI API key:

1. Go to: Settings → AI Settings (or create this DocType)
2. Add field: `openai_api_key`
3. Enter your OpenAI API key

Or add to `site_config.json`:
```json
{
  "openai_api_key": "sk-your-api-key-here"
}
```

## API Endpoints

All endpoints are whitelisted and can be called via REST API.

### 1. Process PDF File

**Endpoint:** `api/method/exim_backend.api.doctypes.pdf_sales_order_handler.process_pdf_file`

**Method:** POST

**Parameters:**
- `file_url` (required): File URL or path
- `session_id` (optional): Custom session ID

**Example Request:**
```python
import requests

response = requests.post(
    "https://your-site.com/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.process_pdf_file",
    data={
        "file_url": "/files/sales_order_123.pdf"
    },
    headers={
        "Authorization": "token api_key:api_secret"
    }
)

result = response.json()
```

**Example Response:**
```json
{
  "message": {
    "status": "success",
    "message": "Sales order data extracted successfully. Please review and confirm.",
    "session_id": "pdf_so_a1b2c3d4e5f6",
    "extracted_data": {
      "customer": "CUST-00001",
      "transaction_date": "2024-01-15",
      "delivery_date": "2024-01-22",
      "items": [
        {
          "item_code": "ITEM-001",
          "item_name": "Product A",
          "qty": 10,
          "rate": 100.00,
          "uom": "Nos"
        }
      ]
    },
    "validation_warnings": [
      "Customer 'CUST-00001' not found in system. Please create or select existing customer."
    ],
    "requires_confirmation": true
  }
}
```

### 2. Confirm and Create Sales Order

**Endpoint:** `api/method/exim_backend.api.doctypes.pdf_sales_order_handler.confirm_and_create`

**Method:** POST

**Parameters:**
- `session_id` (required): Session ID from extraction
- `confirmed_data` (optional): Modified data as JSON string

**Example Request:**
```python
response = requests.post(
    "https://your-site.com/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.confirm_and_create",
    data={
        "session_id": "pdf_so_a1b2c3d4e5f6"
    },
    headers={
        "Authorization": "token api_key:api_secret"
    }
)
```

**With Modified Data:**
```python
import json

modified_data = {
    "customer": "CUST-00002",  # Corrected customer
    "transaction_date": "2024-01-16",
    "items": [
        {
            "item_code": "ITEM-001",
            "qty": 15,  # Modified quantity
            "rate": 95.00
        }
    ]
}

response = requests.post(
    "https://your-site.com/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.confirm_and_create",
    data={
        "session_id": "pdf_so_a1b2c3d4e5f6",
        "confirmed_data": json.dumps(modified_data)
    }
)
```

**Example Response:**
```json
{
  "message": {
    "status": "success",
    "message": "Sales Order 'SO-00123' created successfully for customer 'ABC Corp'",
    "sales_order_name": "SO-00123",
    "customer": "CUST-00002",
    "grand_total": 1425.00,
    "session_id": "pdf_so_a1b2c3d4e5f6"
  }
}
```

### 3. Update Session Data

**Endpoint:** `api/method/exim_backend.api.doctypes.pdf_sales_order_handler.update_session_data`

**Method:** POST

**Parameters:**
- `session_id` (required): Session ID
- `updated_fields` (required): Fields to update as JSON

**Example:**
```python
response = requests.post(
    url,
    data={
        "session_id": "pdf_so_a1b2c3d4e5f6",
        "updated_fields": json.dumps({
            "customer": "CUST-00003",
            "po_no": "PO-2024-001"
        })
    }
)
```

### 4. Get Session Information

**Endpoint:** `api/method/exim_backend.api.doctypes.pdf_sales_order_handler.get_session_info`

**Method:** GET/POST

**Parameters:**
- `session_id` (required): Session ID

### 5. Cancel Session

**Endpoint:** `api/method/exim_backend.api.doctypes.pdf_sales_order_handler.cancel_pdf_session`

**Method:** POST

**Parameters:**
- `session_id` (required): Session ID

## Integration with AI Chat System

To integrate with your existing AI chat system (`ai_chat.py`), add the following function:

```python
# Add to ai_chat.py

def handle_pdf_sales_order(file_url, conversation_id):
    """
    Handle PDF sales order creation through chat interface.
    
    Args:
        file_url: URL of uploaded PDF file
        conversation_id: Chat conversation ID (used as session_id)
    
    Returns:
        str: Response message for user
    """
    from exim_backend.api.doctypes.pdf_sales_order_handler import PDFSalesOrderHandler
    
    handler = PDFSalesOrderHandler()
    
    # Process the PDF
    result = handler.process_pdf(file_url, session_id=conversation_id)
    
    if result.get("status") == "success":
        extracted_data = result.get("extracted_data", {})
        warnings = result.get("validation_warnings", [])
        
        # Format response for user
        response = "✅ **PDF Analyzed Successfully!**\n\n"
        response += "**Extracted Sales Order Data:**\n\n"
        
        # Customer info
        response += f"**Customer:** {extracted_data.get('customer') or 'Not found'}\n"
        response += f"**Order Date:** {extracted_data.get('transaction_date') or 'Not found'}\n"
        response += f"**Delivery Date:** {extracted_data.get('delivery_date') or 'Not found'}\n"
        
        # Items
        items = extracted_data.get('items', [])
        if items:
            response += f"\n**Items:** ({len(items)} items)\n"
            for idx, item in enumerate(items, 1):
                response += f"{idx}. {item.get('item_name', 'Unknown')} - Qty: {item.get('qty', 0)}, Rate: {item.get('rate', 0)}\n"
        else:
            response += "\n⚠️ **No items found**\n"
        
        # Warnings
        if warnings:
            response += "\n**⚠️ Validation Warnings:**\n"
            for warning in warnings:
                response += f"- {warning}\n"
        
        response += f"\n**Please review the data above and confirm:**\n"
        response += f"- Type **'confirm'** to create the sales order\n"
        response += f"- Type **'modify [field] [value]'** to change any field\n"
        response += f"- Type **'cancel'** to cancel\n"
        
        # Store session ID in conversation context
        return response
    else:
        return f"❌ **Error:** {result.get('message')}"


def handle_pdf_confirmation(session_id, action="confirm", modifications=None):
    """
    Handle user confirmation or modifications.
    
    Args:
        session_id: Session ID from extraction
        action: "confirm", "modify", or "cancel"
        modifications: Dict of fields to modify
    
    Returns:
        str: Response message
    """
    from exim_backend.api.doctypes.pdf_sales_order_handler import PDFSalesOrderHandler
    
    handler = PDFSalesOrderHandler()
    
    if action == "cancel":
        result = handler.cancel_session(session_id)
        return "❌ Sales order creation cancelled."
    
    elif action == "modify" and modifications:
        result = handler.update_extracted_data(session_id, modifications)
        if result.get("status") == "success":
            return "✅ Data updated successfully. Please review and confirm again."
        else:
            return f"❌ Error: {result.get('message')}"
    
    elif action == "confirm":
        result = handler.confirm_and_create_order(session_id)
        if result.get("status") == "success":
            response = f"✅ **Sales Order Created Successfully!**\n\n"
            response += f"**Order ID:** {result.get('sales_order_name')}\n"
            response += f"**Customer:** {result.get('customer_name')}\n"
            response += f"**Total Amount:** {result.get('grand_total')}\n"
            return response
        else:
            return f"❌ **Error:** {result.get('message')}"
    
    return "Invalid action"
```

## Python Usage Examples

### Example 1: Basic PDF Processing

```python
import frappe
from exim_backend.api.doctypes.pdf_sales_order_handler import PDFSalesOrderHandler

# Initialize handler
handler = PDFSalesOrderHandler()

# Process PDF
result = handler.process_pdf("/path/to/sales_order.pdf")

if result["status"] == "success":
    session_id = result["session_id"]
    extracted_data = result["extracted_data"]
    
    print(f"Session ID: {session_id}")
    print(f"Customer: {extracted_data.get('customer')}")
    print(f"Items: {len(extracted_data.get('items', []))}")
    
    # Confirm and create order
    order_result = handler.confirm_and_create_order(session_id)
    
    if order_result["status"] == "success":
        print(f"Sales Order Created: {order_result['sales_order_name']}")
```

### Example 2: With Data Modifications

```python
# Process PDF
result = handler.process_pdf("/path/to/sales_order.pdf")
session_id = result["session_id"]

# Update customer
handler.update_extracted_data(session_id, {
    "customer": "CUST-00001",
    "delivery_date": "2024-02-01"
})

# Modify items
confirmed_data = result["extracted_data"]
confirmed_data["items"][0]["qty"] = 20  # Change quantity

# Create order with modifications
order_result = handler.confirm_and_create_order(session_id, confirmed_data)
```

### Example 3: Error Handling

```python
result = handler.process_pdf("/path/to/sales_order.pdf")

if result["status"] == "error":
    print(f"Error: {result['message']}")
    # Handle error
elif result.get("validation_warnings"):
    print("Warnings found:")
    for warning in result["validation_warnings"]:
        print(f"  - {warning}")
    # Prompt user for corrections
else:
    # Proceed with creation
    pass
```

## Architecture

### Component Structure

```
pdf_sales_order_handler.py (Main orchestrator)
├── pdf_processor.py (PDF content extraction)
│   ├── Text extraction (pdfplumber, PyPDF2)
│   ├── Table extraction (pdfplumber)
│   └── Image extraction (PyMuPDF)
│
├── ai_extractor.py (AI-powered data structuring)
│   ├── OpenAI integration
│   ├── Fallback rule-based extraction
│   └── Data validation
│
└── sales_order_handler.py (Existing sales order creation)
```

### Session Management

- Sessions are stored in Frappe cache with 24-hour expiration
- Session ID format: `pdf_so_{12_char_hex}`
- Session states: `pending_confirmation`, `completed`, `cancelled`

### Data Flow

```
PDF File
  ↓
PDFProcessor.extract_from_pdf()
  ↓ (text, tables, images)
AISalesOrderExtractor.extract_sales_order_data()
  ↓ (structured data)
PDFSalesOrderHandler.process_pdf()
  ↓ (validation, warnings)
[User Confirmation]
  ↓
PDFSalesOrderHandler.confirm_and_create_order()
  ↓
SalesOrderHandler.create_document()
  ↓
Sales Order Created ✅
```

## PDF Format Requirements

The system works best with PDFs that contain:

### Required Information:
- Customer name/ID
- At least one item with:
  - Item code or name
  - Quantity
  - Rate/price (optional, can be filled from item master)

### Optional Information:
- Order date
- Delivery date
- PO number and date
- Company name
- Item UOM

### Supported PDF Types:
1. **Text-based PDFs** - Best results
2. **PDFs with tables** - Excellent item extraction
3. **Scanned PDFs** - Requires OCR (install pytesseract)
4. **PDFs with images** - Can be processed with vision AI

## Troubleshooting

### Common Issues:

**1. "pdfplumber not installed"**
```bash
pip install pdfplumber
```

**2. "pdf2image requires poppler"**
```bash
# Ubuntu
sudo apt-get install poppler-utils
```

**3. "Customer not found"**
- Ensure customer exists in system
- Or update the extracted data with correct customer ID

**4. "Item not found"**
- Create items first, or
- Modify extracted data with correct item codes

**5. Low extraction quality**
- Configure OpenAI API key for better AI extraction
- Ensure PDF is not password-protected
- Check PDF text is selectable (not scanned image)

## Advanced Configuration

### Custom AI Model

Edit `ai_extractor.py` to use different AI models:

```python
# Use GPT-3.5 for cost efficiency
response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",  # Instead of gpt-4
    ...
)
```

### Custom Validation Rules

Edit `pdf_sales_order_handler.py`, method `_validate_and_enrich_data()`:

```python
def _validate_and_enrich_data(self, extracted_data):
    # Add custom validation logic
    if extracted_data.get("grand_total", 0) > 100000:
        warnings.append("Order exceeds approval limit")
    
    # Add custom enrichment
    extracted_data["custom_field"] = "custom_value"
```

### OCR for Scanned PDFs

Install Tesseract OCR:
```bash
sudo apt-get install tesseract-ocr
pip install pytesseract
```

Then enable in `pdf_processor.py`.

## Security Considerations

1. **File Upload**: Validate file types and sizes
2. **API Access**: Use Frappe permissions and API keys
3. **Data Validation**: Always validate extracted data before creation
4. **Session Expiry**: Sessions expire after 24 hours
5. **Error Logging**: Sensitive data not logged

## Performance Tips

1. **Batch Processing**: Process multiple PDFs asynchronously
2. **Cache Results**: Session data cached for 24 hours
3. **Optimize AI Calls**: Use fallback extraction when AI unavailable
4. **Limit PDF Size**: Recommend PDFs under 10MB

## Future Enhancements

- [ ] Multi-language support
- [ ] OCR for scanned documents
- [ ] Batch PDF processing
- [ ] Custom extraction templates
- [ ] Machine learning model training
- [ ] Email PDF import
- [ ] WhatsApp PDF integration

## Support

For issues or questions:
1. Check logs: `frappe.logger()`
2. Review session data: `get_session_info(session_id)`
3. Test with sample PDFs first
4. Verify all dependencies installed

## API Testing with Postman

Import this collection to test all endpoints:

```json
{
  "info": {
    "name": "PDF Sales Order API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Process PDF",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.process_pdf_file",
        "body": {
          "mode": "formdata",
          "formdata": [
            {
              "key": "file_url",
              "value": "/files/sales_order.pdf"
            }
          ]
        }
      }
    },
    {
      "name": "Confirm and Create",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.confirm_and_create",
        "body": {
          "mode": "formdata",
          "formdata": [
            {
              "key": "session_id",
              "value": "{{session_id}}"
            }
          ]
        }
      }
    }
  ]
}
```

---

**Version:** 1.0  
**Last Updated:** November 2024  
**Maintainer:** Exim Backend Team

