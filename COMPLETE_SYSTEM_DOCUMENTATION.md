# Exim Backend - Complete System Documentation

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Overview](#system-overview)
3. [Architecture](#architecture)
4. [Component Details](#component-details)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [API Endpoints](#api-endpoints)
7. [Frontend Implementation](#frontend-implementation)
8. [Backend Implementation](#backend-implementation)
9. [AI Integration](#ai-integration)
10. [PDF Processing](#pdf-processing)
11. [Image Processing](#image-processing)
12. [DocType Handlers](#doctype-handlers)
13. [Session Management](#session-management)
14. [Error Handling](#error-handling)
15. [Deployment & Configuration](#deployment--configuration)

---

## Executive Summary

**Exim Backend** is a Frappe/ERPNext application that provides AI-powered natural language interface for interacting with ERPNext data. The system enables users to:

- Query ERPNext data using natural language
- Create documents (Customers, Items, Sales Orders, etc.) through conversational interface
- Upload and process PDF documents to create Sales Orders automatically
- Extract text from images using OCR
- Get intelligent responses with suggested actions

**Technology Stack:**
- **Backend**: Python (Frappe Framework), ERPNext
- **Frontend**: JavaScript (Vanilla JS), HTML/CSS
- **AI**: Google Gemini (via OpenRouter or direct API)
- **OCR**: Tesseract (pytesseract)
- **PDF Processing**: PyPDF2, pdfplumber

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (Web Browser - ai_chat.js)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Chat Input   │  │ File Upload  │  │ Action Buttons│         │
│  │ (Text/Image) │  │ (PDF/Image)  │  │ (Execute)    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND API LAYER                          │
│              (JavaScript - ai_chat.js)                         │
│  • Session Management                                          │
│  • Message Rendering                                           │
│  • File Handling                                               │
│  • Action Execution                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP POST/GET
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND API LAYER                           │
│              (Python - ai_chat.py)                             │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ Main Entry Point: process_chat()                      │    │
│  │  • Message Processing                                 │    │
│  │  • File Upload Handling                               │    │
│  │  • Session Management                                 │    │
│  │  • AI Integration                                      │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ AI Service   │    │ PDF Handler │    │ Image OCR    │
│ (Gemini API) │    │ (PDF Proc)  │    │ (Tesseract)  │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DOCUMENT HANDLERS                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Base Handler│  │ Customer    │  │ Sales Order  │          │
│  │ (Abstract)  │  │ Handler     │  │ Handler      │           │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Item Handler│  │ Sales Person │  │ PDF Sales     │         │
│  │             │  │ Handler      │  │ Order Handler │         │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ERPNext DATABASE                             │
│              (MySQL/MariaDB via Frappe ORM)                    │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Frontend (ai_chat.js)**: User interface and interaction layer
2. **Backend API (ai_chat.py)**: Main request processing and orchestration
3. **AI Service**: Natural language understanding and response generation
4. **DocType Handlers**: Specialized handlers for each ERPNext document type
5. **PDF Processor**: Extracts and structures data from PDF documents
6. **Image Reader**: OCR text extraction from images
7. **Session Manager**: Conversation history and context management

---

## Architecture

### 1. Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  • HTML/CSS UI                                               │
│  • JavaScript Event Handlers                                 │
│  • Message Rendering                                         │
│  • File Upload UI                                            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                        │
│  • Request Routing                                          │
│  • Session Management                                        │
│  • Business Logic Orchestration                              │
│  • AI Integration                                            │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                             │
│  • DocType Handlers                                          │
│  • PDF Processing Service                                    │
│  • Image OCR Service                                         │
│  • AI Service Wrapper                                        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER                         │
│  • Frappe ORM                                                │
│  • Database Queries                                          │
│  • Cache Management                                          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    DATA STORAGE                              │
│  • ERPNext Database (MySQL/MariaDB)                         │
│  • Frappe Cache (Redis/Memory)                              │
│  • File Storage (Frappe Files)                              │
└─────────────────────────────────────────────────────────────┘
```

### 2. Request Flow Architecture

```
User Action
    │
    ▼
Frontend (ai_chat.js)
    │
    ├─► File Upload? ──► Handle File (PDF/Image)
    │
    ├─► Text Message? ──► Send to Backend
    │
    └─► Action Button? ──► Execute Action
    │
    ▼
Backend (ai_chat.py)
    │
    ├─► PDF File? ──► PDF Handler ──► AI Extractor ──► Sales Order Handler
    │
    ├─► Image File? ──► OCR Extraction ──► Append to Message
    │
    └─► Text Message? ──► AI Processing
    │
    ▼
AI Service (Gemini)
    │
    ├─► Analyze Intent
    ├─► Detect DocTypes
    ├─► Generate Response
    └─► Suggest Actions (JSON)
    │
    ▼
Action Execution
    │
    ├─► Search? ──► DocType Handler ──► Database Query
    ├─► Create? ──► DocType Handler ──► Document Creation
    ├─► Count? ──► DocType Handler ──► Count Query
    └─► Details? ──► DocType Handler ──► Document Retrieval
    │
    ▼
Response to Frontend
    │
    └─► Render Message + Actions
```

---

## Component Details

### 1. Frontend Component (ai_chat.js)

**Location**: `exim_backend/templates/includes/ai_chat.js`

**Responsibilities**:
- User interface rendering
- Message display and formatting
- File upload handling (PDF/Image)
- Session management (localStorage)
- API communication
- Action button rendering and execution
- Typing indicators
- Error handling and notifications

**Key Functions**:

```javascript
// Main Functions
handleSendMessage()        // Process user input
sendChatMessage()          // Send to backend API
sendIntelligentQuery()     // (Disabled) Alternative query system
executeAction()            // Execute suggested actions
handleFileUpload()         // Handle PDF/Image uploads
addMessage()               // Display messages in UI
showTypingIndicator()      // Show loading state
```

**State Management**:
- `sessionId`: Conversation session identifier
- `currentImage`: Currently attached image
- `currentFile`: Currently attached PDF
- `isProcessing`: Request in progress flag

### 2. Backend Main API (ai_chat.py)

**Location**: `exim_backend/api/ai_chat.py`

**Main Entry Point**: `process_chat()`

**Responsibilities**:
- Request validation and parsing
- File upload handling
- PDF processing coordination
- Image OCR extraction
- AI service integration
- Conversation history management
- Action suggestion parsing
- Response formatting

**Key Functions**:

```python
process_chat()                    # Main chat processing endpoint
call_ai_api()                     # AI service wrapper
get_conversation_history()         # Retrieve chat history
save_to_history()                  # Save message to history
build_optimized_system_prompt()    # Build AI system prompt
estimate_tokens()                  # Token counting
clear_chat_history()               # Clear conversation
```

**Flow**:

```
1. Receive request (message, image, pdf, session_id)
2. Check for PDF context (active PDF session)
3. Handle PDF upload if present
4. Extract text from image if present
5. Detect DocTypes from message
6. Fetch field metadata for detected DocTypes
7. Build system prompt with field information
8. Get conversation history
9. Call AI API with full context
10. Parse AI response for suggested actions
11. Save to conversation history
12. Return response with actions
```

### 3. DocType Handlers

**Base Handler**: `exim_backend/api/doctypes/base_handler.py`

**Inheritance Structure**:
```
BaseDocTypeHandler (Abstract)
    ├── CustomerHandler
    ├── ItemHandler
    ├── SalesOrderHandler
    ├── SalesPersonHandler
    └── PDFSalesOrderHandler
```

**Base Handler Methods**:

```python
get_fields_info()              # Get DocType field metadata
build_field_reference()        # Build field reference string
prepare_document_data()        # Prepare data for creation
create_document()              # Create document
dynamic_search()               # Search with filters
count_documents()             # Count documents
get_document_details()        # Get single document
normalize_date_value()        # Normalize date formats
```

**Handler-Specific Implementations**:

- **CustomerHandler**: Customer-specific logic, address handling
- **ItemHandler**: Item code generation, stock information
- **SalesOrderHandler**: Item validation, totals calculation
- **SalesPersonHandler**: Tree structure handling, performance metrics
- **PDFSalesOrderHandler**: PDF extraction workflow

### 4. AI Integration

**Service**: Google Gemini (via OpenRouter or Direct API)

**Configuration**:
- API Key: `openrouter_api_key` or `gemini_api_key` in site_config.json
- Model: `ai_model` config or default `google/gemini-2.0-flash-exp:free`
- Max Tokens: `ai_max_tokens` (default: 8000)

**System Prompt Structure**:

```
1. Role Definition (ERPNext AI Assistant)
2. Available Actions (JSON format)
3. DocType Field References
4. Examples and Rules
5. Response Format Guidelines
```

**AI Response Format**:

The AI returns:
- Natural language response
- Optional JSON action suggestion:
  ```json
  {
    "action": "dynamic_search|create_document|count_documents|get_document_details",
    "doctype": "Customer|Item|Sales Order|...",
    "filters": {...},
    "fields": {...},
    "execute_immediately": true|false
  }
  ```

### 5. PDF Processing

**Components**:
- `PDFProcessor`: Extracts text/tables from PDF
- `AISalesOrderExtractor`: Uses AI to structure PDF data
- `PDFSalesOrderHandler`: Orchestrates PDF workflow
- `PDFChatIntegration`: Chat interface integration

**Workflow**:

```
1. User uploads PDF
2. PDFProcessor extracts raw content
3. AISalesOrderExtractor structures data using AI
4. Validation and enrichment
5. Store in session cache
6. Present to user for confirmation
7. User confirms/modifies
8. Create Sales Order via SalesOrderHandler
```

### 6. Image Processing

**Component**: `image_reader.py`

**Technology**: Tesseract OCR (pytesseract)

**Flow**:
```
1. User uploads image
2. Save temporarily
3. Extract text using pytesseract
4. Append extracted text to user message
5. Process as regular text message
6. Cleanup temporary file
```

### 7. Session Management

**Storage**: Frappe Cache (Redis/Memory)

**Session Data Structure**:
```python
{
    "session_id": "chat_xxx",
    "history": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "pdf_context": {...},  # If active PDF session
    "timestamp": "..."
}
```

**Cache Keys**:
- `ai_chat_history_{session_id}`: Conversation history
- `pdf_sales_order:{session_id}`: PDF extraction session

**TTL**: 24 hours (86400 seconds)

---

## Data Flow Diagrams

### 1. Text Message Processing Flow

```
┌─────────────┐
│   User      │
│  Types      │
│  Message    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend (ai_chat.js)              │
│  • Validate input                   │
│  • Get session_id                   │
│  • Prepare FormData                 │
└──────┬──────────────────────────────┘
       │
       │ HTTP POST
       │ /api/method/exim_backend.api.ai_chat.process_chat
       ▼
┌─────────────────────────────────────┐
│  Backend (ai_chat.py)               │
│  process_chat()                     │
└──────┬──────────────────────────────┘
       │
       ├─► Extract message text
       ├─► Get session_id
       ├─► Check conversation history
       │
       ▼
┌─────────────────────────────────────┐
│  DocType Detection                  │
│  • Parse message keywords           │
│  • Detect mentioned DocTypes        │
│  • Default to Customer if none      │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Field Metadata Retrieval            │
│  • Get handler for each DocType      │
│  • Fetch field information           │
│  • Build field reference string     │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  System Prompt Building              │
│  • Include role definition           │
│  • Add available actions             │
│  • Include field references          │
│  • Add examples and rules            │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Conversation History                │
│  • Get last 10 messages              │
│  • Add to messages array             │
│  • Add current user message          │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Token Management                   │
│  • Estimate tokens                  │
│  • Truncate if exceeds limit        │
│  • Keep system + current message    │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  AI API Call (Gemini)               │
│  • Send messages array              │
│  • Receive response                 │
│  • Parse for JSON actions           │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Response Processing                 │
│  • Save to history                   │
│  • Extract suggested_action JSON    │
│  • Calculate token usage            │
└──────┬──────────────────────────────┘
       │
       │ JSON Response
       ▼
┌─────────────────────────────────────┐
│  Frontend Rendering                  │
│  • Display AI response              │
│  • Show action buttons if present    │
│  • Update conversation UI            │
└─────────────────────────────────────┘
```

### 2. PDF Upload and Sales Order Creation Flow

```
┌─────────────┐
│   User      │
│  Uploads    │
│    PDF      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend (ai_chat.js)              │
│  handleFileUpload()                 │
│  • Validate PDF file                │
│  • Show preview                     │
└──────┬──────────────────────────────┘
       │
       │ User clicks Send
       ▼
┌─────────────────────────────────────┐
│  Frontend sends PDF                 │
│  • FormData with PDF file           │
│  • Optional message text            │
└──────┬──────────────────────────────┘
       │
       │ HTTP POST
       │ /api/method/exim_backend.api.ai_chat.process_chat
       ▼
┌─────────────────────────────────────┐
│  Backend (ai_chat.py)               │
│  process_chat()                     │
│  • Detect PDF file                  │
│  • Save to Frappe Files             │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  PDF Chat Integration               │
│  handle_pdf_in_chat()               │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  PDF Sales Order Handler             │
│  process_pdf()                      │
└──────┬──────────────────────────────┘
       │
       ├─► Step 1: PDF Content Extraction
       │   ┌─────────────────────────────┐
       │   │ PDFProcessor                 │
       │   │ • Extract text               │
       │   │ • Extract tables             │
       │   │ • Extract images             │
       │   └─────────────────────────────┘
       │
       ├─► Step 2: AI Data Extraction
       │   ┌─────────────────────────────┐
       │   │ AISalesOrderExtractor        │
       │   │ • Structure data using AI   │
       │   │ • Extract customer           │
       │   │ • Extract items              │
       │   │ • Extract dates              │
       │   └─────────────────────────────┘
       │
       ├─► Step 3: Validation
       │   ┌─────────────────────────────┐
       │   │ Validate & Enrich            │
       │   │ • Check customer exists      │
       │   │ • Check items exist          │
       │   │ • Set defaults if missing    │
       │   │ • Generate warnings          │
       │   └─────────────────────────────┘
       │
       └─► Step 4: Store in Session
           ┌─────────────────────────────┐
           │ Cache Session Data          │
           │ • Extracted data             │
           │ • PDF content                │
           │ • Status: pending           │
           └─────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Return to Frontend                │
│  • Extracted data                   │
│  • Validation warnings              │
│  • Session ID                        │
│  • Requires confirmation            │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend Display                   │
│  • Show extracted data              │
│  • Show warnings                    │
│  • Show action buttons:             │
│    - Confirm                        │
│    - Modify                         │
│    - Cancel                         │
└──────┬──────────────────────────────┘
       │
       │ User clicks "Confirm"
       ▼
┌─────────────────────────────────────┐
│  Frontend sends confirmation        │
│  • Session ID                       │
│  • Message: "confirm"               │
└──────┬──────────────────────────────┘
       │
       │ HTTP POST
       ▼
┌─────────────────────────────────────┐
│  Backend processes confirmation    │
│  • Get session data                │
│  • Clean data                      │
│  • Create Sales Order              │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Sales Order Handler                │
│  create_document()                 │
│  • Validate customer                │
│  • Validate items                   │
│  • Create document                 │
│  • Calculate totals                │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Return Success                     │
│  • Sales Order name                 │
│  • Customer name                    │
│  • Grand total                      │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend displays success          │
│  • Show order details              │
│  • Clear PDF context               │
└─────────────────────────────────────┘
```

### 3. Action Execution Flow

```
┌─────────────┐
│   User      │
│  Clicks     │
│  Action     │
│  Button     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend (ai_chat.js)              │
│  executeAction()                    │
│  • Parse action JSON                │
│  • Determine action type            │
└──────┬──────────────────────────────┘
       │
       ├─► Action: dynamic_search
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ HTTP POST                    │
       │   │ /api/method/.../execute_action│
       │   │ Body: {action, doctype, ...} │
       │   └─────────────────────────────┘
       │
       ├─► Action: create_document
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ HTTP POST                    │
       │   │ /api/method/.../execute_action│
       │   │ Body: {action, doctype, fields}│
       │   └─────────────────────────────┘
       │
       ├─► Action: count_documents
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ HTTP POST                    │
       │   │ /api/method/.../execute_action│
       │   │ Body: {action, doctype, filters}│
       │   └─────────────────────────────┘
       │
       └─► Action: get_document_details
           │
           ▼
           ┌─────────────────────────────┐
           │ HTTP POST                    │
           │ /api/method/.../execute_action│
           │ Body: {action, doctype, name}│
           └─────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Backend (ai_chat.py)               │
│  execute_action()                   │
│  • Parse action JSON                │
│  • Route to appropriate handler     │
└──────┬──────────────────────────────┘
       │
       ├─► dynamic_search
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ Get Handler                  │
       │   │ handler.dynamic_search()    │
       │   │ • Build SQL query            │
       │   │ • Apply filters              │
       │   │ • Normalize dates            │
       │   │ • Execute query              │
       │   └─────────────────────────────┘
       │
       ├─► create_document
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ Get Handler                  │
       │   │ handler.create_document()    │
       │   │ • Prepare data               │
       │   │ • Validate                   │
       │   │ • Create document           │
       │   │ • Return result              │
       │   └─────────────────────────────┘
       │
       ├─► count_documents
       │   │
       │   ▼
       │   ┌─────────────────────────────┐
       │   │ Get Handler                  │
       │   │ handler.count_documents()    │
       │   │ • Apply filters              │
       │   │ • Count records              │
       │   │ • Return count + names       │
       │   └─────────────────────────────┘
       │
       └─► get_document_details
           │
           ▼
           ┌─────────────────────────────┐
           │ Get Handler                  │
           │ handler.get_document_details()│
           │ • Load document             │
           │ • Get related data           │
           │ • Return full details        │
           └─────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Return Result                      │
│  • Status (success/error)            │
│  • Data (results/document)         │
│  • Message                          │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend displays result           │
│  • Format data                      │
│  • Show in message                  │
│  • Update UI                        │
└─────────────────────────────────────┘
```

### 4. Image OCR Processing Flow

```
┌─────────────┐
│   User      │
│  Uploads    │
│   Image     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend (ai_chat.js)              │
│  handleFileUpload()                 │
│  • Validate image file             │
│  • Show preview                     │
└──────┬──────────────────────────────┘
       │
       │ User clicks Send
       ▼
┌─────────────────────────────────────┐
│  Frontend sends image               │
│  • FormData with image file         │
│  • Optional message text            │
└──────┬──────────────────────────────┘
       │
       │ HTTP POST
       │ /api/method/exim_backend.api.ai_chat.process_chat
       ▼
┌─────────────────────────────────────┐
│  Backend (ai_chat.py)               │
│  process_chat()                     │
│  • Detect image file                │
│  • Save temporarily                 │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Image Reader (image_reader.py)     │
│  extract_text_from_image()         │
│  • Load image with PIL              │
│  • Run Tesseract OCR                │
│  • Extract text                     │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Append to Message                  │
│  • If no message: use extracted text │
│  • If message: append extracted text│
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Continue as Text Message           │
│  • Process through AI               │
│  • Generate response                │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Return Response                    │
│  • AI response                      │
│  • Extracted text                   │
│  • Suggested actions                │
└──────┬──────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────┐
│  Frontend displays                  │
│  • Show extracted text              │
│  • Show AI response                 │
│  • Show action buttons              │
└─────────────────────────────────────┘
```

---

## API Endpoints

### Core Chat Endpoints

#### 1. Process Chat
```
POST /api/method/exim_backend.api.ai_chat.process_chat

Parameters:
  - message (string, optional): User message text
  - image (file, optional): Image file for OCR
  - pdf (file, optional): PDF file for sales order
  - file (file, optional): Generic file upload
  - session_id (string, optional): Session identifier
  - clear_history (boolean, optional): Clear conversation history

Response:
{
  "status": "success|error",
  "message": "AI response text",
  "suggested_action": {
    "action": "dynamic_search|create_document|...",
    "doctype": "Customer|Item|...",
    "filters": {...},
    "execute_immediately": true|false
  },
  "extracted_text": "OCR text if image provided",
  "token_usage": {
    "input_tokens": 1234,
    "output_tokens": 567,
    "total_tokens": 1801
  },
  "session_id": "chat_xxx",
  "prompt_info": {...}
}
```

#### 2. Clear Chat History
```
POST /api/method/exim_backend.api.ai_chat.clear_chat_history

Parameters:
  - session_id (string, required): Session identifier

Response:
{
  "status": "success|error",
  "message": "Conversation history cleared"
}
```

#### 3. Execute Action
```
POST /api/method/exim_backend.api.ai_chat.execute_action

Parameters:
  - action (JSON string, required): Action object
    {
      "action": "dynamic_search|create_document|count_documents|get_document_details",
      "doctype": "Customer|Item|Sales Order|...",
      "filters": {...},  // For search/count
      "fields": {...},   // For create
      "name": "...",     // For get_document_details
      "order_by": "...", // For search
      "limit": 20        // For search
    }

Response:
{
  "status": "success|error",
  "message": "Result message",
  "data": {...},  // Results/document data
  "count": 123    // For count/search actions
}
```

### DocType Handler Endpoints

#### 4. Dynamic Search
```
POST /api/method/exim_backend.api.ai_chat.execute_action

Action Type: dynamic_search
{
  "action": "dynamic_search",
  "doctype": "Customer",
  "filters": {
    "customer_name": {"$like": "%John%"},
    "territory": "North"
  },
  "order_by": "modified desc",
  "limit": 20
}
```

#### 5. Create Document
```
POST /api/method/exim_backend.api.ai_chat.execute_action

Action Type: create_document
{
  "action": "create_document",
  "doctype": "Customer",
  "fields": {
    "customer_name": "John Doe",
    "mobile_no": "1234567890",
    "email_id": "john@example.com"
  }
}
```

#### 6. Count Documents
```
POST /api/method/exim_backend.api.ai_chat.execute_action

Action Type: count_documents
{
  "action": "count_documents",
  "doctype": "Sales Order",
  "filters": {
    "status": "Submitted"
  }
}
```

#### 7. Get Document Details
```
POST /api/method/exim_backend.api.ai_chat.execute_action

Action Type: get_document_details
{
  "action": "get_document_details",
  "doctype": "Customer",
  "name": "CUST-00001"
}
```

### PDF Sales Order Endpoints

#### 8. Process PDF File
```
POST /api/method/exim_backend.api.doctypes.pdf_sales_order_handler.process_pdf_file

Parameters:
  - file_url (string, required): Frappe File URL
  - session_id (string, optional): Session identifier

Response:
{
  "status": "success|error",
  "message": "Extraction result message",
  "session_id": "pdf_so_xxx",
  "extracted_data": {
    "customer": "...",
    "items": [...],
    "transaction_date": "...",
    "delivery_date": "..."
  },
  "validation_warnings": [...],
  "requires_confirmation": true
}
```

#### 9. Confirm and Create Order
```
POST /api/method/exim_backend.api.doctypes.pdf_sales_order_handler.confirm_and_create

Parameters:
  - session_id (string, required): Session identifier
  - confirmed_data (JSON string, optional): Modified data

Response:
{
  "status": "success|error",
  "message": "Sales order created successfully",
  "sales_order_name": "SAL-ORD-2025-00001",
  "customer": "CUST-00001",
  "customer_name": "John Doe",
  "grand_total": 1000.00
}
```

### Field Metadata Endpoints

#### 10. Get DocType Fields
```
GET /api/method/exim_backend.api.doctype_fields.get_doctype_fields

Parameters:
  - doctype (string, required): DocType name
  - include_children (int, optional): 1 to include child tables
  - child_doctype (string, optional): Specific child table

Response:
{
  "success": true,
  "data": {
    "doctype": "Sales Order",
    "fields": [
      {
        "label": "Customer",
        "fieldname": "customer",
        "fieldtype": "Link",
        "options": "Customer"
      },
      ...
    ],
    "children": [
      {
        "label": "Items",
        "child_doctype": "Sales Order Item",
        "fieldname": "items",
        "fields": [...]
      }
    ]
  }
}
```

---

## Frontend Implementation

### File Structure

```
exim_backend/
└── templates/
    └── includes/
        └── ai_chat.js  (4184 lines)
```

### Key Components

#### 1. DOM Elements
```javascript
const messagesContainer = document.getElementById('messagesContainer');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const attachBtn = document.getElementById('attachBtn');
const fileInput = document.getElementById('fileInput');
const filePreview = document.getElementById('filePreview');
```

#### 2. State Management
```javascript
let currentImage = null;
let currentFile = null;
let currentFileType = null;  // 'image' or 'pdf'
let isProcessing = false;
let sessionId = localStorage.getItem('ai_chat_session_id') || generateSessionId();
```

#### 3. Main Functions

**handleSendMessage()**:
- Validates input
- Adds user message to UI
- Handles file attachments
- Sends to backend
- Displays response
- Shows action buttons

**sendChatMessage()**:
- Creates FormData
- Adds message, image, PDF, session_id
- Sends POST request
- Handles response
- Updates UI

**executeAction()**:
- Parses action JSON
- Sends to execute_action endpoint
- Displays results
- Updates conversation

**handleFileUpload()**:
- Validates file type
- Shows preview
- Stores file reference

### Message Rendering

Messages are rendered with:
- Role-based styling (user/assistant)
- Markdown support
- Code block highlighting
- Action buttons for suggested actions
- Image/PDF previews

### Action Buttons

When AI suggests an action, frontend renders buttons:
- **Execute**: Immediately execute the action
- **Modify**: Allow user to edit before execution
- **Cancel**: Dismiss the action

---

## Backend Implementation

### File Structure

```
exim_backend/
└── api/
    ├── ai_chat.py                    # Main chat API (2203 lines)
    ├── intelligent_query.py          # (Disabled) Alternative query system
    ├── doctype_fields.py             # Field metadata API
    ├── image_reader.py                # OCR functionality
    ├── pdf_chat_integration.py        # PDF chat integration
    ├── pdf_processor.py              # PDF content extraction
    ├── ai_extractor.py               # AI-based data extraction
    └── doctypes/
        ├── base_handler.py           # Base handler class
        ├── customer_handler.py       # Customer operations
        ├── item_handler.py           # Item operations
        ├── sales_order_handler.py    # Sales Order operations
        ├── sales_person_handler.py   # Sales Person operations
        └── pdf_sales_order_handler.py # PDF Sales Order workflow
```

### Main Processing Flow

#### process_chat() Function

```python
def process_chat():
    """
    Main entry point for chat processing.
    
    Steps:
    1. Extract request parameters
    2. Handle PDF context (if active PDF session)
    3. Handle PDF file upload
    4. Handle image file (OCR)
    5. Detect DocTypes from message
    6. Fetch field metadata
    7. Build system prompt
    8. Get conversation history
    9. Call AI API
    10. Parse response for actions
    11. Save to history
    12. Return response
    """
```

**Key Steps**:

1. **Request Parsing**:
   ```python
   message = frappe.form_dict.get("message", "").strip()
   image_file = frappe.request.files.get("image")
   pdf_file = frappe.request.files.get("pdf") or frappe.request.files.get("file")
   session_id = frappe.form_dict.get("session_id") or "default"
   ```

2. **PDF Handling**:
   ```python
   if pdf_file:
       # Save PDF to Frappe Files
       file_doc = save_file(...)
       # Process via PDF handler
       pdf_result = handle_pdf_in_chat(file_url, session_id, message)
   ```

3. **Image OCR**:
   ```python
   if image_file:
       # Extract text using Tesseract
       extracted_text = image_to_string(Image.open(filepath))
       # Append to message
       message = f"{message}\n\nExtracted text: {extracted_text}"
   ```

4. **DocType Detection**:
   ```python
   doctype_keywords = {
       "Customer": ["customer", "customers", "client"],
       "Sales Order": ["sales order", "so"],
       ...
   }
   # Detect from message keywords
   ```

5. **Field Metadata**:
   ```python
   for doctype in detected_doctypes:
       handler = get_handler(doctype)
       fields_info = handler.get_fields_info()
       field_reference = handler.build_field_reference(fields_info)
   ```

6. **System Prompt Building**:
   ```python
   system_prompt = build_optimized_system_prompt(doctype_fields_map)
   # Includes: role, actions, fields, examples, rules
   ```

7. **AI API Call**:
   ```python
   messages = [
       {"role": "system", "content": system_prompt},
       ...history...,
       {"role": "user", "content": message}
   ]
   ai_response = call_ai_api(messages, config)
   ```

8. **Action Parsing**:
   ```python
   # Extract JSON from AI response
   suggested_action = parse_json_from_response(ai_response)
   ```

### DocType Handler System

#### Base Handler

All handlers inherit from `BaseDocTypeHandler`:

```python
class BaseDocTypeHandler:
    def get_fields_info(self):
        """Get field metadata for doctype"""
    
    def dynamic_search(self, filters, limit, order_by):
        """Search with dynamic filters"""
    
    def create_document(self, fields):
        """Create document"""
    
    def count_documents(self, filters):
        """Count documents"""
    
    def get_document_details(self, name):
        """Get single document"""
```

#### Handler Registration

```python
# In doctypes/__init__.py
HANDLERS = {
    "Customer": CustomerHandler,
    "Item": ItemHandler,
    "Sales Order": SalesOrderHandler,
    "Sales Person": SalesPersonHandler,
}

def get_handler(doctype):
    return HANDLERS.get(doctype)()
```

### Dynamic Search Implementation

```python
def dynamic_search(self, filters, limit=20, order_by="modified desc"):
    """
    Build dynamic SQL query from filters.
    
    Supports:
    - Direct value: {"field": "value"}
    - Operators: {"field": {"$like": "%value%"}}
    - Date normalization: "today", "yesterday", etc.
    - Multiple conditions: AND logic
    """
    # Map field names
    # Normalize date values
    # Build WHERE clause
    # Execute query
    # Return results
```

**Filter Operators**:
- `$like`: LIKE pattern matching
- `$is_null`: IS NULL check
- `$is_not_null`: IS NOT NULL check
- `$gte`: Greater than or equal
- `$lte`: Less than or equal
- `$in`: IN list

**Date Normalization**:
- Keywords: "today", "yesterday", "tomorrow"
- Relative: "7 days ago", "this week", "this month"
- Formats: "DD-MM-YYYY", "YYYY-MM-DD"

---

## AI Integration

### Configuration

**Site Config (site_config.json)**:
```json
{
  "openrouter_api_key": "sk-or-xxx",  // OR
  "gemini_api_key": "AIzaSy-xxx",
  "ai_model": "google/gemini-2.0-flash-exp:free",
  "ai_max_tokens": 8000
}
```

### AI Service Wrapper

```python
def call_ai_api(messages, config, stream=False):
    """
    Call AI API (OpenRouter or Direct Gemini).
    
    OpenRouter:
    - Endpoint: https://openrouter.ai/api/v1/chat/completions
    - Format: OpenAI-compatible
    
    Direct Gemini:
    - Library: google.generativeai
    - Model: gemini-1.5-flash or gemini-2.0-flash-exp
    """
```

### System Prompt Structure

```
You are an ERPNext AI Assistant...

AVAILABLE ACTIONS (JSON format):
1. dynamic_search
2. create_document
3. count_documents
4. get_document_details

DOCUMENT FIELDS:
[Field references for detected DocTypes]

EXAMPLES:
[Query examples with expected actions]

RULES:
[Response format, field mapping, date handling, etc.]
```

### AI Response Parsing

The AI response may contain:
1. **Natural language text**: Direct answer to user
2. **JSON action**: Suggested action in JSON format

Parsing logic:
```python
# Look for JSON in markdown code blocks
json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
match = re.search(json_pattern, ai_response)

# Or find JSON without code blocks
start_idx = ai_response.find("{")
end_idx = ai_response.rfind("}") + 1
json_str = ai_response[start_idx:end_idx]

# Parse JSON
suggested_action = json.loads(json_str)
```

---

## PDF Processing

### Components

1. **PDFProcessor** (`pdf_processor.py`):
   - Extracts text from PDF
   - Extracts tables
   - Extracts images
   - Returns structured content

2. **AISalesOrderExtractor** (`ai_extractor.py`):
   - Takes PDF content
   - Uses AI to structure data
   - Extracts customer, items, dates, prices
   - Returns structured JSON

3. **PDFSalesOrderHandler** (`pdf_sales_order_handler.py`):
   - Orchestrates workflow
   - Validates extracted data
   - Manages session state
   - Creates Sales Order

### Workflow Steps

1. **PDF Upload**:
   ```python
   file_doc = save_file(fname=pdf_file.filename, content=pdf_file.read())
   file_url = file_doc.file_url
   ```

2. **Content Extraction**:
   ```python
   pdf_processor = PDFProcessor()
   extraction_result = pdf_processor.extract_from_pdf(file_url)
   pdf_content = extraction_result.get("content")
   ```

3. **AI Extraction**:
   ```python
   ai_extractor = AISalesOrderExtractor()
   ai_result = ai_extractor.extract_sales_order_data(pdf_content)
   extracted_data = ai_result.get("data")
   ```

4. **Validation**:
   ```python
   validated_data = handler._validate_and_enrich_data(extracted_data)
   # Check customer exists
   # Check items exist
   # Set defaults
   # Generate warnings
   ```

5. **Session Storage**:
   ```python
   cache_key = f"pdf_sales_order:{session_id}"
   frappe.cache().set_value(cache_key, json.dumps(data), expires_in_sec=86400)
   ```

6. **User Confirmation**:
   ```python
   # User reviews data
   # User confirms or modifies
   # Handler updates data if modified
   ```

7. **Sales Order Creation**:
   ```python
   sales_order_handler = SalesOrderHandler()
   result = sales_order_handler.create_document(validated_data)
   ```

---

## Image Processing

### OCR Implementation

**Technology**: Tesseract OCR via pytesseract

**Process**:
```python
from pytesseract import image_to_string
from PIL import Image

# Save image temporarily
filepath = os.path.join(temp_path, image_file.filename)
image_file.save(filepath)

# Extract text
extracted_text = image_to_string(Image.open(filepath))

# Cleanup
os.remove(filepath)

# Append to message
message = f"{message}\n\nExtracted text: {extracted_text}"
```

**Integration**:
- Image upload handled in `process_chat()`
- Text extraction happens before AI processing
- Extracted text is appended to user message
- AI processes combined message

---

## DocType Handlers

### Handler Hierarchy

```
BaseDocTypeHandler (Abstract Base Class)
    │
    ├── CustomerHandler
    │   • Customer-specific validation
    │   • Address handling
    │   • Contact management
    │
    ├── ItemHandler
    │   • Item code generation
    │   • Stock information
    │   • Price information
    │
    ├── SalesOrderHandler
    │   • Item validation
    │   • Totals calculation
    │   • Date handling
    │
    ├── SalesPersonHandler
    │   • Tree structure handling
    │   • Performance metrics
    │   • Summary generation
    │
    └── PDFSalesOrderHandler
        • PDF workflow orchestration
        • Session management
        • Data validation
```

### Handler Methods

Each handler implements:

1. **get_search_fields()**: Fields to return in search
2. **get_date_fields()**: Date/datetime fields for normalization
3. **prepare_document_data()**: Data preparation before creation
4. **create_document()**: Document creation with validation
5. **dynamic_search()**: Search with filters (inherited from base)
6. **count_documents()**: Count with filters (inherited from base)
7. **get_document_details()**: Get single document (inherited from base)

### Specialized Features

#### CustomerHandler
- Address creation
- Contact linking
- Territory/Group defaults

#### ItemHandler
- Item code auto-generation
- Stock information retrieval
- Price list information

#### SalesOrderHandler
- Item validation
- Quantity validation
- Auto-fill item details
- Totals calculation

#### SalesPersonHandler
- Tree structure (NestedSet)
- Performance summary
- Order/invoice aggregation

---

## Session Management

### Session Storage

**Location**: Frappe Cache (Redis or Memory)

**Cache Keys**:
- `ai_chat_history_{session_id}`: Conversation history
- `pdf_sales_order:{session_id}`: PDF extraction session

**TTL**: 24 hours (86400 seconds)

### Session Data Structure

**Conversation History**:
```python
[
    {"role": "user", "content": "Show me customers"},
    {"role": "assistant", "content": "Here are the customers..."},
    ...
]
```

**PDF Session**:
```python
{
    "session_id": "pdf_so_xxx",
    "extracted_data": {
        "customer": "...",
        "items": [...],
        ...
    },
    "pdf_content": {...},
    "status": "pending_confirmation|completed|cancelled",
    "timestamp": "2025-01-01T12:00:00",
    "last_updated": "2025-01-01T12:05:00"
}
```

### Session Lifecycle

1. **Creation**: Generated on first message or file upload
2. **Storage**: Saved to cache after each message
3. **Retrieval**: Loaded on each request
4. **Expiration**: Auto-expires after 24 hours
5. **Clearing**: Manual clear via API or new chat

---

## Error Handling

### Error Types

1. **Validation Errors**:
   - Missing required fields
   - Invalid field values
   - Duplicate entries

2. **API Errors**:
   - AI API failures
   - Network timeouts
   - Invalid responses

3. **Processing Errors**:
   - PDF extraction failures
   - OCR failures
   - Database errors

### Error Response Format

```python
{
    "status": "error",
    "message": "Error description",
    "error_type": "ValidationError|APIError|ProcessingError",
    "details": {...}  # Optional additional details
}
```

### Error Handling Strategy

1. **Try-Except Blocks**: Wrap all operations
2. **Logging**: Log errors with full traceback
3. **User-Friendly Messages**: Convert technical errors to user messages
4. **Graceful Degradation**: Continue operation when possible
5. **Error Recovery**: Retry logic for transient failures

---

## Deployment & Configuration

### Installation

```bash
# Install app
bench get-app exim_backend
bench install-app exim_backend

# Install dependencies
bench pip install google-generativeai pytesseract pdfplumber PyPDF2 Pillow
```

### Configuration

**1. AI API Key**:
```bash
# Add to site_config.json
bench --site [site-name] set-config openrouter_api_key sk-or-xxx
# OR
bench --site [site-name] set-config gemini_api_key AIzaSy-xxx
```

**2. AI Model** (optional):
```bash
bench --site [site-name] set-config ai_model google/gemini-2.0-flash-exp:free
```

**3. Max Tokens** (optional):
```bash
bench --site [site-name] set-config ai_max_tokens 8000
```

**4. PDF Settings** (optional):
```bash
bench --site [site-name] set-config pdf_sales_order_skip_validation true
bench --site [site-name] set-config pdf_sales_order_default_customer "CUST-00001"
bench --site [site-name] set-config pdf_sales_order_default_company "Company Name"
```

### System Requirements

- **Python**: 3.8+
- **Frappe**: v15+
- **ERPNext**: v15+
- **Tesseract**: For OCR functionality
- **Redis**: Recommended for cache (optional)

### Access

**Chat Interface**: `http://your-site/ai-chat`

**API Endpoints**: `http://your-site/api/method/exim_backend.api.*`

---

## Summary

**Exim Backend** is a comprehensive AI-powered interface for ERPNext that enables:

1. **Natural Language Interaction**: Users can query and create documents using plain English
2. **Multi-Modal Input**: Supports text, images (OCR), and PDFs
3. **Intelligent Document Creation**: Automatically extracts and structures data from PDFs
4. **Conversational Context**: Maintains conversation history for follow-up questions
5. **Action Suggestions**: AI suggests actions that users can execute with one click
6. **Extensible Architecture**: Handler-based system for easy extension to new DocTypes

The system is built on a solid foundation with:
- **Layered Architecture**: Clear separation of concerns
- **Handler Pattern**: Reusable DocType handlers
- **Session Management**: Persistent conversation context
- **Error Handling**: Robust error management
- **Scalable Design**: Can handle multiple concurrent users

This documentation provides a complete understanding of the system architecture, implementation details, and data flows from end to end.

