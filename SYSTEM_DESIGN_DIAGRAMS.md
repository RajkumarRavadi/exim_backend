# Exim Backend - System Design Diagrams (Mermaid)

This document contains high-level design diagrams in Mermaid format for the Exim Backend application.

---

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph "User Layer"
        User[👤 User]
        Browser[🌐 Web Browser]
    end

    subgraph "Frontend Layer"
        UI[Chat Interface<br/>ai_chat.js]
        FileUpload[File Upload Handler]
        MessageDisplay[Message Renderer]
        ActionButtons[Action Buttons]
    end

    subgraph "API Gateway"
        APIRouter[Frappe API Router]
    end

    subgraph "Backend Services"
        ChatAPI[AI Chat API<br/>ai_chat.py]
        PDFHandler[PDF Handler<br/>pdf_sales_order_handler.py]
        ImageOCR[Image OCR<br/>image_reader.py]
        ActionExecutor[Action Executor<br/>execute_action]
    end

    subgraph "AI Services"
        AIService[AI Service Wrapper]
        GeminiAPI[Google Gemini API<br/>via OpenRouter/Direct]
    end

    subgraph "DocType Handlers"
        BaseHandler[Base Handler<br/>base_handler.py]
        CustomerHandler[Customer Handler]
        ItemHandler[Item Handler]
        SalesOrderHandler[Sales Order Handler]
        SalesPersonHandler[Sales Person Handler]
    end

    subgraph "Processing Services"
        PDFProcessor[PDF Processor<br/>pdf_processor.py]
        AIExtractor[AI Extractor<br/>ai_extractor.py]
        FieldMetadata[Field Metadata<br/>doctype_fields.py]
    end

    subgraph "Data Layer"
        FrappeORM[Frappe ORM]
        Database[(ERPNext Database<br/>MySQL/MariaDB)]
        Cache[(Frappe Cache<br/>Redis/Memory)]
        FileStorage[(File Storage<br/>Frappe Files)]
    end

    User --> Browser
    Browser --> UI
    UI --> FileUpload
    UI --> MessageDisplay
    UI --> ActionButtons
    
    UI --> APIRouter
    FileUpload --> APIRouter
    ActionButtons --> APIRouter
    
    APIRouter --> ChatAPI
    APIRouter --> PDFHandler
    APIRouter --> ImageOCR
    APIRouter --> ActionExecutor
    
    ChatAPI --> AIService
    ChatAPI --> FieldMetadata
    ChatAPI --> Cache
    
    AIService --> GeminiAPI
    
    PDFHandler --> PDFProcessor
    PDFHandler --> AIExtractor
    PDFHandler --> SalesOrderHandler
    PDFHandler --> Cache
    
    ImageOCR --> FileStorage
    
    ActionExecutor --> BaseHandler
    BaseHandler --> CustomerHandler
    BaseHandler --> ItemHandler
    BaseHandler --> SalesOrderHandler
    BaseHandler --> SalesPersonHandler
    
    CustomerHandler --> FrappeORM
    ItemHandler --> FrappeORM
    SalesOrderHandler --> FrappeORM
    SalesPersonHandler --> FrappeORM
    
    FrappeORM --> Database
    ChatAPI --> Cache
    PDFHandler --> Cache
```

---

## 2. Request Flow Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend<br/>(ai_chat.js)
    participant API as Chat API<br/>(ai_chat.py)
    participant AI as AI Service<br/>(Gemini)
    participant H as DocType Handler
    participant DB as Database

    U->>F: Type message / Upload file
    F->>F: Validate input
    F->>F: Prepare FormData
    
    alt PDF Upload
        F->>API: POST /process_chat (with PDF)
        API->>API: Save PDF to Files
        API->>API: Process PDF
        API->>API: Extract data with AI
        API->>API: Validate & enrich
        API->>API: Store in session cache
        API->>F: Return extracted data
        F->>U: Show data for confirmation
        U->>F: Confirm/Cancel/Modify
        F->>API: POST /process_chat (confirm)
        API->>H: Create Sales Order
        H->>DB: Insert document
        DB->>H: Return result
        H->>API: Return success
        API->>F: Return order details
        F->>U: Show success message
    else Image Upload
        F->>API: POST /process_chat (with image)
        API->>API: Extract text (OCR)
        API->>API: Append to message
        API->>AI: Process message
        AI->>API: Return response
        API->>F: Return response
        F->>U: Display response
    else Text Message
        F->>API: POST /process_chat (message)
        API->>API: Detect DocTypes
        API->>API: Fetch field metadata
        API->>API: Build system prompt
        API->>API: Get conversation history
        API->>AI: Send messages array
        AI->>API: Return response + actions
        API->>API: Parse suggested actions
        API->>API: Save to history
        API->>F: Return response + actions
        F->>U: Display response + buttons
        
        alt User clicks Execute Action
            U->>F: Click action button
            F->>API: POST /execute_action
            API->>H: Execute action
            H->>DB: Query/Create/Update
            DB->>H: Return data
            H->>API: Return result
            API->>F: Return result
            F->>U: Display result
        end
    end
```

---

## 3. Component Interaction Diagram

```mermaid
graph LR
    subgraph "Frontend Components"
        A[Message Input]
        B[File Upload]
        C[Message Display]
        D[Action Buttons]
    end

    subgraph "Backend API"
        E[process_chat]
        F[execute_action]
        G[clear_history]
    end

    subgraph "Processing"
        H[PDF Processor]
        I[Image OCR]
        J[AI Service]
        K[Field Metadata]
    end

    subgraph "Handlers"
        L[Base Handler]
        M[Customer Handler]
        N[Item Handler]
        O[Sales Order Handler]
        P[Sales Person Handler]
    end

    subgraph "Storage"
        Q[(Database)]
        R[(Cache)]
        S[(Files)]
    end

    A --> E
    B --> E
    C --> E
    D --> F
    
    E --> H
    E --> I
    E --> J
    E --> K
    E --> R
    
    F --> L
    L --> M
    L --> N
    L --> O
    L --> P
    
    M --> Q
    N --> Q
    O --> Q
    P --> Q
    
    H --> S
    I --> S
    J --> R
    K --> Q
```

---

## 4. PDF Processing Workflow

```mermaid
flowchart TD
    Start([User Uploads PDF]) --> Validate{Valid PDF?}
    Validate -->|No| Error1[Return Error]
    Validate -->|Yes| SaveFile[Save to Frappe Files]
    
    SaveFile --> ExtractContent[PDF Processor<br/>Extract Content]
    ExtractContent --> ExtractText[Extract Text]
    ExtractContent --> ExtractTables[Extract Tables]
    ExtractContent --> ExtractImages[Extract Images]
    
    ExtractText --> AIExtract[AI Extractor<br/>Structure Data]
    ExtractTables --> AIExtract
    ExtractImages --> AIExtract
    
    AIExtract --> ValidateData{Validate Data}
    ValidateData -->|Missing Customer| SetDefault1[Set Default Customer]
    ValidateData -->|Missing Items| SetDefault2[Set Default Items]
    ValidateData -->|Missing Company| SetDefault3[Set Default Company]
    ValidateData -->|Valid| StoreSession[Store in Session Cache]
    
    SetDefault1 --> StoreSession
    SetDefault2 --> StoreSession
    SetDefault3 --> StoreSession
    
    StoreSession --> ShowData[Show Extracted Data to User]
    ShowData --> UserDecision{User Action}
    
    UserDecision -->|Confirm| CreateOrder[Create Sales Order]
    UserDecision -->|Modify| UpdateData[Update Data]
    UserDecision -->|Cancel| CancelSession[Cancel Session]
    
    UpdateData --> ValidateData
    CancelSession --> End1([End])
    
    CreateOrder --> ValidateOrder{Validate Order}
    ValidateOrder -->|Invalid| ShowError[Show Error]
    ValidateOrder -->|Valid| InsertDB[Insert to Database]
    
    ShowError --> UserDecision
    InsertDB --> Success[Return Success]
    Success --> End2([End])
    Error1 --> End3([End])
```

---

## 5. AI Processing Flow

```mermaid
flowchart TD
    Start([User Message]) --> GetHistory[Get Conversation History]
    GetHistory --> DetectDocTypes[Detect DocTypes from Message]
    DetectDocTypes --> FetchFields[Fetch Field Metadata]
    
    FetchFields --> BuildPrompt[Build System Prompt]
    BuildPrompt --> AddRole[Add Role Definition]
    BuildPrompt --> AddActions[Add Available Actions]
    BuildPrompt --> AddFields[Add Field References]
    BuildPrompt --> AddExamples[Add Examples & Rules]
    
    AddRole --> CombineMessages[Combine Messages]
    AddActions --> CombineMessages
    AddFields --> CombineMessages
    AddExamples --> CombineMessages
    
    CombineMessages --> CheckTokens{Token Count OK?}
    CheckTokens -->|Too Many| TruncateHistory[Truncate History]
    CheckTokens -->|OK| CallAI[Call AI API]
    TruncateHistory --> CallAI
    
    CallAI --> AIResponse[AI Response]
    AIResponse --> ParseResponse[Parse Response]
    ParseResponse --> ExtractText[Extract Text]
    ParseResponse --> ExtractJSON[Extract JSON Actions]
    
    ExtractText --> SaveHistory[Save to History]
    ExtractJSON --> SaveHistory
    
    SaveHistory --> ReturnResponse[Return Response]
    ReturnResponse --> ShowUI[Show in UI]
    ShowUI --> UserAction{User Action?}
    
    UserAction -->|Execute| ExecuteAction[Execute Action]
    UserAction -->|Modify| ModifyAction[Modify Action]
    UserAction -->|Cancel| CancelAction[Cancel Action]
    
    ExecuteAction --> HandlerCall[Call DocType Handler]
    HandlerCall --> DBQuery[Database Query]
    DBQuery --> ReturnResult[Return Result]
    ReturnResult --> ShowResult[Show Result]
    
    ModifyAction --> ShowUI
    CancelAction --> End([End])
    ShowResult --> End
```

---

## 6. DocType Handler Architecture

```mermaid
classDiagram
    class BaseDocTypeHandler {
        +doctype: str
        +label: str
        +get_fields_info()
        +build_field_reference()
        +prepare_document_data()
        +create_document()
        +dynamic_search()
        +count_documents()
        +get_document_details()
        +normalize_date_value()
    }
    
    class CustomerHandler {
        +get_search_fields()
        +prepare_document_data()
        +create_document()
        +create_customer_address()
        +get_document_details()
        +search_by_query()
        +count_with_breakdown()
    }
    
    class ItemHandler {
        +get_search_fields()
        +prepare_document_data()
        +create_document()
        +get_document_details()
        +search_by_query()
        +count_with_breakdown()
    }
    
    class SalesOrderHandler {
        +get_search_fields()
        +get_date_fields()
        +prepare_document_data()
        +prepare_item_data()
        +create_document()
        +get_document_details()
    }
    
    class SalesPersonHandler {
        +get_search_fields()
        +prepare_document_data()
        +create_document()
        +get_document_details()
        +get_sales_person_summary()
        +get_all_sales_persons_summary()
    }
    
    class PDFSalesOrderHandler {
        +process_pdf()
        +confirm_and_create_order()
        +update_extracted_data()
        +get_session_data()
        +cancel_session()
    }
    
    BaseDocTypeHandler <|-- CustomerHandler
    BaseDocTypeHandler <|-- ItemHandler
    BaseDocTypeHandler <|-- SalesOrderHandler
    BaseDocTypeHandler <|-- SalesPersonHandler
    BaseDocTypeHandler <|-- PDFSalesOrderHandler
```

---

## 7. Session Management Flow

```mermaid
stateDiagram-v2
    [*] --> NewSession: User starts chat
    
    NewSession --> ActiveSession: First message
    
    ActiveSession --> Processing: Message sent
    Processing --> ActiveSession: Response received
    
    ActiveSession --> PDFPending: PDF uploaded
    PDFPending --> PDFConfirmed: User confirms
    PDFPending --> PDFCancelled: User cancels
    PDFPending --> PDFModified: User modifies
    
    PDFModified --> PDFPending: Data updated
    PDFConfirmed --> ActiveSession: Order created
    PDFCancelled --> ActiveSession: Session cleared
    
    ActiveSession --> HistoryCleared: User clears history
    HistoryCleared --> ActiveSession: Continue chatting
    
    ActiveSession --> Expired: 24 hours TTL
    Expired --> [*]
    
    ActiveSession --> NewSession: User starts new chat
```

---

## 8. Action Execution Flow

```mermaid
flowchart TD
    Start([Action Button Clicked]) --> ParseAction[Parse Action JSON]
    ParseAction --> ActionType{Action Type?}
    
    ActionType -->|dynamic_search| SearchFlow[Search Flow]
    ActionType -->|create_document| CreateFlow[Create Flow]
    ActionType -->|count_documents| CountFlow[Count Flow]
    ActionType -->|get_document_details| DetailsFlow[Details Flow]
    
    SearchFlow --> GetHandler1[Get DocType Handler]
    GetHandler1 --> BuildQuery[Build SQL Query]
    BuildQuery --> ApplyFilters[Apply Filters]
    ApplyFilters --> NormalizeDates[Normalize Date Values]
    NormalizeDates --> ExecuteQuery[Execute Query]
    ExecuteQuery --> FormatResults[Format Results]
    FormatResults --> Return1[Return Results]
    
    CreateFlow --> GetHandler2[Get DocType Handler]
    GetHandler2 --> PrepareData[Prepare Document Data]
    PrepareData --> ValidateData[Validate Data]
    ValidateData -->|Invalid| Error1[Return Error]
    ValidateData -->|Valid| CreateDoc[Create Document]
    CreateDoc --> Return2[Return Success]
    
    CountFlow --> GetHandler3[Get DocType Handler]
    GetHandler3 --> ApplyFilters2[Apply Filters]
    ApplyFilters2 --> CountQuery[Count Query]
    CountQuery --> GetNames{Count <= 5?}
    GetNames -->|Yes| IncludeNames[Include Document Names]
    GetNames -->|No| SkipNames[Skip Names]
    IncludeNames --> Return3[Return Count + Names]
    SkipNames --> Return3
    
    DetailsFlow --> GetHandler4[Get DocType Handler]
    GetHandler4 --> LoadDoc[Load Document]
    LoadDoc --> GetRelated[Get Related Data]
    GetRelated --> Return4[Return Details]
    
    Return1 --> Display[Display Result]
    Return2 --> Display
    Return3 --> Display
    Return4 --> Display
    Error1 --> Display
    Display --> End([End])
```

---

## 9. Data Flow - Complete System

```mermaid
flowchart TB
    subgraph "Input Sources"
        UserInput[User Input]
        ImageFile[Image File]
        PDFFile[PDF File]
    end
    
    subgraph "Frontend Processing"
        ValidateInput[Validate Input]
        PrepareRequest[Prepare Request]
    end
    
    subgraph "Backend API"
        RouteRequest[Route Request]
        ProcessMessage[Process Message]
        HandleFile[Handle File]
    end
    
    subgraph "AI Processing"
        DetectDocTypes[Detect DocTypes]
        FetchMetadata[Fetch Metadata]
        BuildPrompt[Build Prompt]
        CallAI[Call AI]
    end
    
    subgraph "Action Execution"
        ParseAction[Parse Action]
        GetHandler[Get Handler]
        Execute[Execute Operation]
    end
    
    subgraph "Data Storage"
        Database[(Database)]
        Cache[(Cache)]
        Files[(Files)]
    end
    
    UserInput --> ValidateInput
    ImageFile --> ValidateInput
    PDFFile --> ValidateInput
    
    ValidateInput --> PrepareRequest
    PrepareRequest --> RouteRequest
    
    RouteRequest --> ProcessMessage
    RouteRequest --> HandleFile
    
    ProcessMessage --> DetectDocTypes
    DetectDocTypes --> FetchMetadata
    FetchMetadata --> BuildPrompt
    BuildPrompt --> CallAI
    
    CallAI --> ParseAction
    ParseAction --> GetHandler
    GetHandler --> Execute
    
    Execute --> Database
    ProcessMessage --> Cache
    HandleFile --> Files
    
    Database --> Execute
    Cache --> ProcessMessage
    Files --> HandleFile
```

---

## 10. System Deployment Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        Browser1[Browser 1]
        Browser2[Browser 2]
        BrowserN[Browser N]
    end
    
    subgraph "Load Balancer / Web Server"
        Nginx[Nginx / Apache]
    end
    
    subgraph "Application Server"
        FrappeApp[Frappe Application]
        EximBackend[Exim Backend App]
    end
    
    subgraph "Service Layer"
        AIService[AI Service<br/>Gemini API]
        OCRService[OCR Service<br/>Tesseract]
    end
    
    subgraph "Data Layer"
        MySQL[(MySQL/MariaDB<br/>ERPNext Data)]
        Redis[(Redis<br/>Cache)]
        FileSystem[(File System<br/>PDFs/Images)]
    end
    
    Browser1 --> Nginx
    Browser2 --> Nginx
    BrowserN --> Nginx
    
    Nginx --> FrappeApp
    FrappeApp --> EximBackend
    
    EximBackend --> AIService
    EximBackend --> OCRService
    EximBackend --> MySQL
    EximBackend --> Redis
    EximBackend --> FileSystem
```

---

## How to Use These Diagrams

### Viewing Mermaid Diagrams

1. **VS Code**: Install "Markdown Preview Mermaid Support" extension
2. **GitHub**: Mermaid diagrams render automatically in markdown files
3. **Online**: Use [Mermaid Live Editor](https://mermaid.live/)
4. **Documentation Tools**: Most modern documentation tools support Mermaid

### Diagram Types Included

1. **System Architecture Overview**: High-level component relationships
2. **Request Flow Diagram**: Sequence of operations
3. **Component Interaction**: Component relationships
4. **PDF Processing Workflow**: PDF handling flow
5. **AI Processing Flow**: AI integration flow
6. **DocType Handler Architecture**: Class diagram of handlers
7. **Session Management Flow**: State diagram for sessions
8. **Action Execution Flow**: Action processing flow
9. **Data Flow**: Complete data flow through system
10. **Deployment Architecture**: Infrastructure diagram

### Customization

You can customize these diagrams by:
- Modifying the Mermaid syntax
- Adding/removing components
- Changing relationships
- Adding more detail to specific flows
- Creating new diagrams for specific use cases

---

## Notes

- All diagrams use standard Mermaid syntax
- Diagrams are designed to be self-contained and readable
- Color coding and styling can be added using Mermaid themes
- Diagrams can be exported as PNG/SVG using Mermaid tools
- These diagrams complement the detailed documentation in `COMPLETE_SYSTEM_DOCUMENTATION.md`

