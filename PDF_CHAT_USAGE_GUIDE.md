# PDF Sales Order via Chat - Usage Guide

## ✅ Integration Complete!

PDF sales order creation is now **fully integrated** into your AI chatbot!

---

## 🎯 How to Use

### **Method 1: Upload PDF via Chat API**

#### **Example cURL Request:**

```bash
curl -X POST "http://localhost:8000/api/method/exim_backend.api.ai_chat.process_chat" \
  -F "message=Create sales order from this PDF" \
  -F "pdf=@/path/to/sales_order.pdf" \
  -F "session_id=user_123"
```

#### **Example JavaScript/Fetch:**

```javascript
const formData = new FormData();
formData.append('message', 'Create sales order from this PDF');
formData.append('pdf', pdfFile); // File object from input
formData.append('session_id', 'user_123');

fetch('/api/method/exim_backend.api.ai_chat.process_chat', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  console.log('Response:', data.message.response);
});
```

#### **Example Python:**

```python
import requests

url = "http://localhost:8000/api/method/exim_backend.api.ai_chat.process_chat"

files = {
    'pdf': open('/path/to/sales_order.pdf', 'rb')
}
data = {
    'message': 'Create sales order from this PDF',
    'session_id': 'user_123'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

---

## 💬 Chat Workflow

### **Step 1: User Uploads PDF**

**User Action:**
```
Upload: sales_order.pdf
Message: "Create sales order from this PDF"
```

**Bot Response:**
```
✅ PDF Analyzed Successfully!

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

---

### **Step 2: User Reviews & Responds**

#### **Option A: Confirm (Create Order)**

**User:**
```
confirm
```

**Bot:**
```
✅ Sales Order Created Successfully!

📋 Order ID: SO-00123
👤 Customer: ABC Corporation
💰 Total Amount: 1,500.00

You can view the order by searching for 'SO-00123' or ask me to show its details.
```

---

#### **Option B: Modify Data**

**User:**
```
change customer to CUST-001
```

**Bot:**
```
✅ Data updated successfully!

**Changes made:**
- customer: CUST-001

**Updated Sales Order Data:**

👤 Customer: CUST-001
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

**Then User Confirms:**
```
confirm
```

---

#### **Option C: Cancel**

**User:**
```
cancel
```

**Bot:**
```
❌ Sales order creation cancelled.

Feel free to upload a new PDF whenever you're ready.
```

---

## 🔑 Keywords That Trigger PDF Processing

When uploading a PDF, include any of these keywords in your message:

- ✅ `"sales order"`
- ✅ `"order"`
- ✅ `"create order"`
- ✅ `"so"`
- ✅ `"purchase"`

**Examples:**
- "Create sales order from this PDF"
- "Process this order"
- "Make a SO from this file"
- "Create order"

---

## 📝 Supported Commands During Review

Once PDF is processed, user can say:

| Command | Action | Example |
|---------|--------|---------|
| `confirm` | Create sales order | "confirm" |
| `yes` | Create sales order | "yes, create it" |
| `create` | Create sales order | "create the order" |
| `cancel` | Abort process | "cancel" |
| `no` | Abort process | "no, don't create" |
| `change customer to X` | Update customer | "change customer to CUST-001" |
| `change date to YYYY-MM-DD` | Update order date | "change date to 2024-01-20" |
| `change delivery date to YYYY-MM-DD` | Update delivery date | "change delivery date to 2024-02-01" |
| `show data` | Display data again | "show me the data" |

---

## 🎨 Frontend Integration Examples

### **React Example:**

```jsx
import { useState } from 'react';

function PDFUpload() {
  const [message, setMessage] = useState('');
  const [response, setResponse] = useState('');
  const [sessionId] = useState(`session_${Date.now()}`);

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('pdf', file);
    formData.append('message', message || 'Create sales order');
    formData.append('session_id', sessionId);

    try {
      const res = await fetch('/api/method/exim_backend.api.ai_chat.process_chat', {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      setResponse(data.message.response);
    } catch (error) {
      console.error('Upload error:', error);
    }
  };

  const handleResponse = async (userMessage) => {
    const formData = new FormData();
    formData.append('message', userMessage);
    formData.append('session_id', sessionId);

    try {
      const res = await fetch('/api/method/exim_backend.api.ai_chat.process_chat', {
        method: 'POST',
        body: formData
      });
      
      const data = await res.json();
      setResponse(data.message.response);
    } catch (error) {
      console.error('Response error:', error);
    }
  };

  return (
    <div>
      <input 
        type="text" 
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Enter message (optional)"
      />
      <input 
        type="file" 
        accept=".pdf"
        onChange={handleUpload}
      />
      
      {response && (
        <div>
          <pre>{response}</pre>
          <button onClick={() => handleResponse('confirm')}>Confirm</button>
          <button onClick={() => handleResponse('cancel')}>Cancel</button>
        </div>
      )}
    </div>
  );
}
```

---

### **HTML + JavaScript Example:**

```html
<!DOCTYPE html>
<html>
<head>
  <title>PDF Sales Order</title>
</head>
<body>
  <h1>Upload Sales Order PDF</h1>
  
  <input type="text" id="message" placeholder="Your message">
  <input type="file" id="pdfFile" accept=".pdf">
  <button onclick="uploadPDF()">Upload</button>
  
  <div id="response"></div>
  
  <div id="actions" style="display:none;">
    <button onclick="sendResponse('confirm')">Confirm</button>
    <button onclick="sendResponse('cancel')">Cancel</button>
  </div>

  <script>
    const sessionId = 'session_' + Date.now();
    
    async function uploadPDF() {
      const file = document.getElementById('pdfFile').files[0];
      const message = document.getElementById('message').value;
      
      const formData = new FormData();
      formData.append('pdf', file);
      formData.append('message', message || 'Create sales order');
      formData.append('session_id', sessionId);
      
      const response = await fetch('/api/method/exim_backend.api.ai_chat.process_chat', {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      document.getElementById('response').innerText = data.message.response;
      document.getElementById('actions').style.display = 'block';
    }
    
    async function sendResponse(action) {
      const formData = new FormData();
      formData.append('message', action);
      formData.append('session_id', sessionId);
      
      const response = await fetch('/api/method/exim_backend.api.ai_chat.process_chat', {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      document.getElementById('response').innerText = data.message.response;
      
      if (data.message.completed || data.message.cancelled) {
        document.getElementById('actions').style.display = 'none';
      }
    }
  </script>
</body>
</html>
```

---

## 📊 Response Format

### **Success Response (PDF Analyzed):**

```json
{
  "message": {
    "status": "success",
    "response": "✅ PDF Analyzed Successfully!\n\n...",
    "requires_action": true,
    "data": {
      "customer": "ABC Corporation",
      "transaction_date": "2024-01-15",
      "items": [...]
    },
    "session_id": "session_123"
  }
}
```

### **Success Response (Order Created):**

```json
{
  "message": {
    "status": "success",
    "response": "✅ Sales Order Created Successfully!\n\n📋 Order ID: SO-00123\n...",
    "requires_action": false,
    "completed": true
  }
}
```

### **Error Response:**

```json
{
  "message": {
    "status": "error",
    "response": "❌ Failed to process PDF: Customer not found\n\nPlease review the data and try again.",
    "requires_action": true
  }
}
```

---

## 🧪 Testing

### **Test 1: Upload PDF via Terminal**

```bash
# Create a test PDF or use existing one
curl -X POST "http://localhost:8000/api/method/exim_backend.api.ai_chat.process_chat" \
  -F "message=Create sales order" \
  -F "pdf=@/path/to/test_order.pdf" \
  -F "session_id=test_123"
```

### **Test 2: Confirm Order**

```bash
curl -X POST "http://localhost:8000/api/method/exim_backend.api.ai_chat.process_chat" \
  -F "message=confirm" \
  -F "session_id=test_123"
```

---

## 🔧 Troubleshooting

### **Issue: "PDF uploaded but not processing"**

**Check:**
1. Message contains keywords: "sales order", "order", "so", etc.
2. File field name is "pdf" or "file"
3. File extension is `.pdf`

**Solution:**
```bash
# Ensure message has keyword
-F "message=create sales order from this PDF"
```

---

### **Issue: "Session not found"**

**Cause:** Session expired (24 hours) or different session_id used

**Solution:**
```bash
# Use same session_id for entire workflow
session_id="user_123"  # Keep consistent
```

---

### **Issue: "Customer not found"**

**Cause:** Extracted customer doesn't exist in system

**Solution:**
```bash
# Modify customer in chat
curl -F "message=change customer to CUST-001" -F "session_id=test_123"
```

---

## 📋 API Reference

### **Endpoint:**
```
POST /api/method/exim_backend.api.ai_chat.process_chat
```

### **Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `message` | string | Yes | User's message |
| `pdf` | file | No | PDF file for sales order |
| `file` | file | No | Alternative file upload field |
| `session_id` | string | No | Session ID (auto-generated if not provided) |
| `clear_history` | boolean | No | Clear conversation history |

### **File Upload:**
- Field name: `pdf` or `file`
- Accepted format: `.pdf`
- Max size: Depends on Frappe configuration

---

## ✨ Features

✅ **Automatic Extraction** - AI extracts customer, items, dates, prices  
✅ **Validation** - Checks if customer/items exist  
✅ **User Control** - Review and modify before creation  
✅ **Session Management** - Maintains context for 24 hours  
✅ **Error Handling** - Clear error messages and recovery  
✅ **History Integration** - Saves to chat history  
✅ **Multiple Formats** - Works with various PDF layouts  

---

## 🎉 You're Ready!

Your chatbot now supports **PDF-based sales order creation**!

**Next Steps:**
1. Test with a sample PDF
2. Integrate into your frontend
3. Train users on the workflow

---

**Questions? Check:**
- Full guide: `PDF_SALES_ORDER_GUIDE.md`
- AI config: `PDF_AI_CONFIGURATION.md`
- Implementation: `IMPLEMENTATION_SUMMARY.md`

---

**Happy PDF Processing! 📄 → 💬 → 🎯**

Last Updated: November 8, 2025  
Status: ✅ Fully Integrated & Production Ready

