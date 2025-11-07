# AI Chatbot Setup Guide

## Quick Start Guide for Google Gemini Integration

### Step 1: Install Dependencies

After installing the exim_backend app, install the Google Gemini SDK:

```bash
cd /path/to/your/frappe-bench
bench pip install google-generativeai
```

### Step 2: Get Your Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key

### Step 3: Configure Your Site

You have two options to add the API key:

#### Option A: Using bench command (Recommended)

```bash
bench --site [your-site-name] set-config gemini_api_key YOUR_API_KEY_HERE
```

Example:
```bash
bench --site site1.local set-config gemini_api_key AIzaSyDXXXXXXXXXXXXXXXXXXXXXXXXXX
```

#### Option B: Manual configuration

1. Navigate to your site's directory:
```bash
cd sites/[your-site-name]
```

2. Edit `site_config.json`:
```bash
nano site_config.json
```

3. Add the gemini_api_key:
```json
{
  "db_name": "your_db_name",
  "db_password": "your_password",
  "gemini_api_key": "YOUR_API_KEY_HERE"
}
```

4. Save and exit (Ctrl+X, then Y, then Enter)

### Step 4: Restart Services

```bash
bench restart
```

Or if using supervisor:
```bash
sudo supervisorctl restart all
```

### Step 5: Access the AI Chat Interface

Open your browser and navigate to:
```
http://your-site-url/ai-chat
```

For local development:
```
http://localhost:8000/ai-chat
```

## How to Use the AI Chatbot

### Basic Chat
Simply type a message and press Enter or click the send button.

**Example:**
```
"Hello, what can you help me with?"
```

### Creating Documents

The AI can understand natural language requests to create ERPNext documents.

**Examples:**

1. **Create a Customer:**
```
"Create a new customer named John Doe"
"Add customer: ABC Corp, email: contact@abccorp.com"
```

2. **Create an Item:**
```
"Add a new item: Laptop, item code: LAP-001, item group: Products"
```

3. **Create a Lead:**
```
"New lead: Sarah Smith from XYZ Company, phone: 123-456-7890"
```

### Using Image Upload

1. Click the 📎 (paperclip) icon
2. Select an image containing text (invoice, business card, form, etc.)
3. The AI will:
   - Extract text using OCR
   - Analyze the content
   - Suggest creating appropriate ERPNext documents
   - Extract field values automatically

**Example Use Cases:**
- Upload a business card → Create Customer/Lead
- Upload an invoice → Create Sales/Purchase Invoice
- Upload a product label → Create Item
- Upload a form → Extract and populate fields

### Confirming Document Creation

When the AI suggests creating a document:
1. Review the suggested DocType and fields
2. Click "Create Document" to proceed
3. Click "Cancel" to dismiss the suggestion
4. The document will be created in ERPNext
5. You'll receive a confirmation with the document ID

## Troubleshooting

### "Gemini API key not configured" Error

**Solution:** Make sure you've added the API key to site_config.json and restarted the bench.

```bash
bench --site [site-name] set-config gemini_api_key YOUR_KEY
bench restart
```

### Chat interface not loading

**Solution:** Clear browser cache or hard refresh (Ctrl+Shift+R)

### Images not being processed

**Solution:** 
1. Ensure pytesseract is installed:
```bash
bench pip install pytesseract
```

2. Install Tesseract OCR on your system:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
```

### API Rate Limits

Google Gemini has rate limits. If you encounter rate limit errors:
- Wait a few moments before retrying
- Consider upgrading your Gemini API plan for higher limits

### Document Creation Fails

**Common reasons:**
1. **Missing required fields:** The AI may not have extracted all required fields
2. **Invalid values:** Check if field values match ERPNext validation rules
3. **Permissions:** Ensure guest user has permission to create documents (or disable allow_guest in the API)

**Solution:** Review the error message in the chat and provide additional information.

## Security Considerations

### Production Deployment

For production use, consider:

1. **Disable guest access** in `ai_chat.py`:
```python
@frappe.whitelist(allow_guest=False)  # Require login
```

2. **Add rate limiting** to prevent API abuse

3. **Validate all inputs** before document creation

4. **Use permission checks:**
```python
frappe.has_permission(doctype, "create")
```

5. **Keep your API key secure:**
   - Never commit site_config.json to version control
   - Use environment variables in cloud deployments
   - Rotate API keys regularly

## Advanced Configuration

### Customize AI Behavior

Edit `exim_backend/api/ai_chat.py` and modify the `system_prompt` in the `process_chat()` function to customize how the AI responds.

### Add More DocTypes

In `get_available_doctypes()`, add more doctypes to the list:

```python
{
    "name": "Project",
    "label": "Project",
    "module": "Projects",
    "required_fields": ["project_name"]
}
```

### Change AI Model

To use a different Gemini model, modify the `get_gemini_model()` function:

```python
return genai.GenerativeModel('gemini-1.5-pro')  # More capable but slower
```

Available models:
- `gemini-1.5-flash` - Fast and efficient (default)
- `gemini-1.5-pro` - More capable, better for complex tasks
- `gemini-1.0-pro` - Legacy model

## Support

For issues, questions, or contributions:
- Check the README.md file
- Review the API documentation in the code
- Test API endpoints using curl or Postman
- Check Frappe/ERPNext logs for errors

## API Testing

Test the chat endpoint using curl:

```bash
curl -X POST http://localhost:8000/api/method/exim_backend.api.ai_chat.process_chat \
  -F "message=Create a customer named John Doe"
```

Test with image:

```bash
curl -X POST http://localhost:8000/api/method/exim_backend.api.ai_chat.process_chat \
  -F "message=What is in this image?" \
  -F "image=@/path/to/your/image.jpg"
```

## Next Steps

- Explore more complex document creation flows
- Integrate with existing ERPNext workflows
- Customize the chat interface styling
- Add support for document querying and updates
- Implement conversation history storage
- Add multi-language support

Enjoy using your AI-powered ERPNext assistant! 🤖✨

