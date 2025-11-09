# PDF Sales Order - Quick Start Guide

Get started with PDF-based sales order creation in 5 minutes!

## 🚀 Quick Setup

### Step 1: Install Dependencies (2 minutes)

```bash
cd /home/frappeuser/frappe-bench-v15/apps/exim_backend
pip install -r pdf_requirements.txt

# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install poppler-utils
```

### Step 2: Run Tests (1 minute)

```bash
# Check if everything is installed correctly
bench --site your-site execute exim_backend.api.test_pdf_sales_order.check_dependencies

# Run basic tests
bench --site your-site execute exim_backend.api.test_pdf_sales_order.quick_test
```

### Step 3: Setup Test Data (Optional, 1 minute)

```bash
# Create sample customers and items for testing
bench --site your-site execute exim_backend.api.test_pdf_sales_order.setup_test_data
```

### Step 4: Test with Real Sales Order (1 minute)

```bash
# Create a real sales order from test data
bench --site your-site execute exim_backend.api.test_pdf_sales_order.full_test
```

## 📝 Basic Usage

### Option 1: Via Python Code

```python
import frappe
from exim_backend.api.doctypes.pdf_sales_order_handler import PDFSalesOrderHandler

# Initialize handler
handler = PDFSalesOrderHandler()

# Process PDF
result = handler.process_pdf("/path/to/sales_order.pdf")

if result["status"] == "success":
    session_id = result["session_id"]
    
    # Review extracted data
    print(result["extracted_data"])
    
    # Create sales order
    order = handler.confirm_and_create_order(session_id)
    print(f"Order created: {order['sales_order_name']}")
```

### Option 2: Via REST API

```bash
# 1. Process PDF
curl -X POST https://your-site.com/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.process_pdf_file \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d "file_url=/files/sales_order.pdf"

# Response will include session_id

# 2. Create sales order
curl -X POST https://your-site.com/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.confirm_and_create \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d "session_id=pdf_so_xxxxx"
```

### Option 3: Via Chat Interface

```python
from exim_backend.api.pdf_chat_integration import PDFChatIntegration

integration = PDFChatIntegration()

# Handle PDF upload
response = integration.handle_pdf_upload(
    file_url="/files/sales_order.pdf",
    conversation_id="chat_12345"
)

print(response["message"])  # Shows formatted extraction result

# Handle user confirmation
response = integration.handle_user_response(
    conversation_id="chat_12345",
    user_message="confirm"
)

print(response["message"])  # Shows creation result
```

## 🎯 Integration with Your AI Chat

Add this to your `ai_chat.py`:

```python
from exim_backend.api.pdf_chat_integration import (
    is_pdf_sales_order_intent,
    handle_pdf_in_chat,
    handle_pdf_response,
    check_pdf_context
)

def process_user_message(user_message, file_attachments, conversation_id):
    # Check if user has active PDF session
    pdf_context = check_pdf_context(conversation_id)
    
    if pdf_context.get("has_context"):
        # User is in middle of PDF workflow, handle response
        result = handle_pdf_response(conversation_id, user_message)
        return result["message"]
    
    # Check if message has PDF attachment for sales order
    if file_attachments:
        for file_url in file_attachments:
            if file_url.endswith('.pdf') and is_pdf_sales_order_intent(user_message):
                # Handle PDF upload
                result = handle_pdf_in_chat(file_url, conversation_id, user_message)
                return result["message"]
    
    # Continue with regular chat processing...
```

## 📋 Sample PDF Format

Your PDF should contain:

```
SALES ORDER

Customer: ABC Corporation
Order Date: 2024-01-15
Delivery Date: 2024-01-22
PO Number: PO-2024-001

Items:
┌──────────┬─────────────────┬─────┬─────────┐
│ Item Code│ Description     │ Qty │ Rate    │
├──────────┼─────────────────┼─────┼─────────┤
│ ITEM-001 │ Product A       │  10 │  100.00 │
│ ITEM-002 │ Product B       │   5 │  200.00 │
└──────────┴─────────────────┴─────┴─────────┘

Total: $1,500.00
```

## 🔧 Configure OpenAI (Optional but Recommended)

For better AI extraction, add your OpenAI API key:

**Method 1: Site Config**
```bash
bench --site your-site set-config openai_api_key "sk-your-key-here"
```

**Method 2: Environment Variable**
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Method 3: Create AI Settings DocType**
- Create a Single DocType named "AI Settings"
- Add a field `openai_api_key` (Data field)
- Set your API key there

## 🎨 User Workflow Example

1. **User uploads PDF via chat**
   ```
   User: "Here's a sales order PDF [uploads file]"
   ```

2. **System extracts and displays data**
   ```
   Bot: ✅ PDF Analyzed Successfully!
   
   **Extracted Sales Order Data:**
   
   👤 Customer: ABC Corporation
   📅 Order Date: 2024-01-15
   🚚 Delivery Date: 2024-01-22
   
   📦 Items: (2 items)
     1. Product A - Qty: 10, Rate: 100.00
     2. Product B - Qty: 5, Rate: 200.00
   
   **What would you like to do?**
   • Type 'confirm' to create the sales order
   • Type 'change [field] to [value]' to modify
   • Type 'cancel' to cancel
   ```

3. **User reviews and confirms**
   ```
   User: "confirm"
   ```

4. **System creates order**
   ```
   Bot: ✅ Sales Order Created Successfully!
   
   📋 Order ID: SO-00123
   👤 Customer: ABC Corporation
   💰 Total Amount: 1500.00
   ```

## 🐛 Troubleshooting

### Dependencies Not Found

```bash
# Reinstall dependencies
pip install -r pdf_requirements.txt --upgrade

# Check installation
python -c "import pdfplumber; import PyPDF2; print('OK')"
```

### "poppler not found" Error

```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
```

### Customer/Item Not Found

```bash
# Create test data first
bench --site your-site execute exim_backend.api.test_pdf_sales_order.setup_test_data
```

### Low Extraction Quality

1. Configure OpenAI API key (see above)
2. Ensure PDF is text-based (not scanned image)
3. Check PDF contains clear tables/structured data
4. Try with different PDF formats

## 📚 Next Steps

- Read the full guide: `PDF_SALES_ORDER_GUIDE.md`
- Explore the code: `exim_backend/api/doctypes/pdf_sales_order_handler.py`
- Customize extraction: `exim_backend/api/ai_extractor.py`
- Add custom validation: Edit `_validate_and_enrich_data()` method

## 💡 Tips

1. **Better Results**: Use PDFs with clear tables for item lists
2. **Performance**: Process PDFs asynchronously for large files
3. **Accuracy**: Always review extracted data before confirmation
4. **Testing**: Test with your actual PDF formats first
5. **Monitoring**: Check Frappe logs for extraction issues

## 🔗 Useful Commands

```bash
# Check dependencies
bench --site your-site execute exim_backend.api.test_pdf_sales_order.check_dependencies

# Run all tests
bench --site your-site execute exim_backend.api.test_pdf_sales_order.run_tests

# Setup test data
bench --site your-site execute exim_backend.api.test_pdf_sales_order.setup_test_data

# Full test with real order
bench --site your-site execute exim_backend.api.test_pdf_sales_order.full_test

# View logs
tail -f ~/frappe-bench-v15/logs/your-site.log
```

## 🎉 You're Ready!

Your PDF sales order system is now set up! Upload a PDF and watch the magic happen.

Need help? Check:
- Full documentation: `PDF_SALES_ORDER_GUIDE.md`
- Test file: `exim_backend/api/test_pdf_sales_order.py`
- Example PDFs: `samples/` directory (if available)

---

**Happy PDF Processing! 📄 → 🎯**

