### Exim Backend

a simple frappe app which supports AI integration to erpnext

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app exim_backend
```

After installation, install the required dependencies:

```bash
bench pip install google-generativeai
```

### Configuration

#### AI Chatbot Setup

This app includes an AI chatbot powered by Google Gemini that can help create ERPNext documents from natural language and images.

**1. Get Google Gemini API Key**

- Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
- Sign in with your Google account
- Create a new API key
- Copy the API key

**2. Add API Key to Site Configuration**

Add the Gemini API key to your site's configuration file:

```bash
# Open site_config.json
nano sites/[your-site-name]/site_config.json
```

Add the following line to the JSON file:

```json
{
  ...other config...,
  "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE"
}
```

Alternatively, you can use the bench command:

```bash
bench --site [your-site-name] set-config gemini_api_key YOUR_GEMINI_API_KEY_HERE
```

**3. Restart Bench**

```bash
bench restart
```

### Features

#### AI Chat Assistant

Access the AI chat interface at: `http://your-site/ai-chat`

The AI assistant can:
- Chat naturally with users
- Extract text from uploaded images using OCR
- Understand user intent to create ERPNext documents
- Map extracted data to appropriate DocTypes (Customer, Item, Sales Invoice, etc.)
- Create documents directly from chat conversations

**Supported DocTypes:**
- Customer, Supplier, Employee, Lead
- Item, Sales Order, Purchase Order
- Sales Invoice, Purchase Invoice
- Quotation, Material Request
- And more...

**Usage:**
1. Type a message or upload an image
2. The AI will analyze the content
3. If it detects document creation intent, it will suggest creating a document
4. Review and confirm to create the document in ERPNext

#### API Endpoints

**Process Chat Message:**
```
POST /api/method/exim_backend.api.ai_chat.process_chat
Parameters: message (text), image (file, optional)
```

**Get Available DocTypes:**
```
GET /api/method/exim_backend.api.ai_chat.get_available_doctypes
```

**Create Document:**
```
POST /api/method/exim_backend.api.ai_chat.create_document
Parameters: doctype (text), fields (JSON)
```

**Extract Text from Image:**
```
POST /api/method/exim_backend.api.image_reader.extract_text_from_image
Parameters: image (file)
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/exim_backend
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
