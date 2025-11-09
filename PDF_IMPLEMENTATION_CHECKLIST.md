# PDF Sales Order - Implementation Checklist

Use this checklist to implement and deploy the PDF sales order feature.

## 📋 Pre-Implementation

### ✅ Review & Planning
- [ ] Read `PDF_SALES_ORDER_README.md` (overview)
- [ ] Read `PDF_QUICK_START.md` (setup guide)
- [ ] Review `PDF_SALES_ORDER_GUIDE.md` (complete documentation)
- [ ] Understand the workflow and architecture
- [ ] Identify your PDF format requirements
- [ ] Test with sample PDFs

### ✅ Environment Check
- [ ] Frappe/ERPNext is installed and running
- [ ] Python 3.8+ is available
- [ ] You have sudo access (for system dependencies)
- [ ] Customer and Item masters exist in system
- [ ] You have test PDFs ready

---

## 🛠️ Installation

### ✅ Step 1: Install Python Dependencies (5 minutes)

```bash
cd /home/frappeuser/frappe-bench-v15/apps/exim_backend
pip install -r pdf_requirements.txt
```

**Verify:**
```bash
python -c "import pdfplumber, PyPDF2; print('✓ PDF libraries installed')"
```

- [ ] pdfplumber installed
- [ ] PyPDF2 installed
- [ ] PyMuPDF (fitz) installed
- [ ] pdf2image installed
- [ ] python-dateutil installed

### ✅ Step 2: Install System Dependencies (2 minutes)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install poppler-utils -y
```

**macOS:**
```bash
brew install poppler
```

**Verify:**
```bash
pdftoppm -v
```

- [ ] Poppler installed and working

### ✅ Step 3: Configure OpenAI (Optional, 2 minutes)

**Option A: Site Config**
```bash
bench --site your-site set-config openai_api_key "sk-your-key-here"
```

**Option B: Environment Variable**
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

- [ ] OpenAI API key configured (if using AI extraction)
- [ ] Tested API key is valid

---

## 🧪 Testing

### ✅ Step 4: Run Dependency Check (1 minute)

```bash
bench --site your-site execute exim_backend.api.test_pdf_sales_order.check_dependencies
```

**Expected Output:**
```
✓ pdfplumber     - PDF text extraction
✓ PyPDF2         - PDF reading (fallback)
✓ fitz           - PDF image extraction (PyMuPDF)
✓ pdf2image      - PDF to image conversion
✓ PIL            - Image processing (Pillow)
✓ dateutil       - Date parsing
```

- [ ] All core dependencies show ✓
- [ ] OpenAI library installed (optional)

### ✅ Step 5: Run Basic Tests (2 minutes)

```bash
bench --site your-site execute exim_backend.api.test_pdf_sales_order.quick_test
```

- [ ] PDF Processor test passes
- [ ] AI Extractor test passes
- [ ] Complete Workflow test passes
- [ ] Chat Integration test passes

### ✅ Step 6: Setup Test Data (1 minute)

```bash
bench --site your-site execute exim_backend.api.test_pdf_sales_order.setup_test_data
```

**Verify:**
- [ ] Test customer created: `TEST-CUST-001`
- [ ] Test items created: `TEST-ITEM-001`, `TEST-ITEM-002`

### ✅ Step 7: Test Full Workflow (2 minutes)

```bash
bench --site your-site execute exim_backend.api.test_pdf_sales_order.full_test
```

**Expected:**
- [ ] Sales order created successfully
- [ ] Order has correct customer and items
- [ ] Total amount calculated correctly

---

## 🔌 API Integration

### ✅ Step 8: Test API Endpoints

**Test Process PDF:**
```bash
curl -X POST http://localhost:8000/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.process_pdf_file \
  -H "Authorization: token YOUR_KEY:YOUR_SECRET" \
  -F "file_url=/files/test.pdf"
```

- [ ] API endpoint responds
- [ ] Returns session_id
- [ ] Returns extracted_data
- [ ] Shows validation warnings if any

**Test Confirm & Create:**
```bash
curl -X POST http://localhost:8000/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.confirm_and_create \
  -H "Authorization: token YOUR_KEY:YOUR_SECRET" \
  -F "session_id=pdf_so_xxxxx"
```

- [ ] Creates sales order
- [ ] Returns order name
- [ ] Returns order details

---

## 💬 Chat Integration (Optional)

### ✅ Step 9: Integrate with AI Chat

**Add to your `ai_chat.py`:**

```python
from exim_backend.api.pdf_chat_integration import (
    PDFChatIntegration,
    is_pdf_sales_order_intent,
    check_pdf_context
)
```

**Integration points:**

- [ ] Import PDFChatIntegration class
- [ ] Detect PDF uploads in chat messages
- [ ] Handle PDF processing requests
- [ ] Handle user confirmation/modification responses
- [ ] Clear context after completion

**Test Chat Flow:**
1. [ ] Upload PDF via chat
2. [ ] Receive formatted extraction
3. [ ] Confirm with "confirm"
4. [ ] Receive success message with order ID

---

## 📄 PDF Format Testing

### ✅ Step 10: Test with Your PDFs

**Test with different formats:**

- [ ] Standard text-based PDF
- [ ] PDF with tables
- [ ] Multi-page PDF
- [ ] PDF with images
- [ ] Scanned PDF (if OCR installed)
- [ ] Various date formats
- [ ] Different currencies

**For each PDF format:**
1. [ ] Upload and extract
2. [ ] Review accuracy of extraction
3. [ ] Note any issues
4. [ ] Customize extraction if needed

**Quality Checklist:**
- [ ] Customer name extracted correctly (>90%)
- [ ] Dates extracted correctly (>90%)
- [ ] Items extracted correctly (>85%)
- [ ] Quantities extracted correctly (>95%)
- [ ] Rates/prices extracted correctly (>90%)

---

## 🎨 Customization

### ✅ Step 11: Customize for Your Needs

**Validation Rules** (`pdf_sales_order_handler.py`):
```python
def _validate_and_enrich_data(self, extracted_data):
    # Add custom validation
    if extracted_data.get("grand_total", 0) > 100000:
        warnings.append("Order exceeds approval limit")
```

- [ ] Add custom validation rules
- [ ] Add custom field mappings
- [ ] Set custom defaults

**Extraction Rules** (`ai_extractor.py`):
```python
def _fallback_extraction(self, formatted_content):
    # Customize extraction patterns
    # Add company-specific rules
```

- [ ] Customize regex patterns
- [ ] Add PDF format-specific rules
- [ ] Improve table detection

**Chat Responses** (`pdf_chat_integration.py`):
```python
def _format_data_display(self, data):
    # Customize display format
    # Add custom fields
```

- [ ] Customize chat messages
- [ ] Add custom formatting
- [ ] Localize messages (if needed)

---

## 🚀 Production Deployment

### ✅ Step 12: Pre-Production Checks

**Security:**
- [ ] API keys stored securely (not in code)
- [ ] File upload validation enabled
- [ ] File size limits set (<10MB recommended)
- [ ] API authentication enabled
- [ ] Rate limiting configured

**Performance:**
- [ ] Async processing for large PDFs
- [ ] Cache properly configured
- [ ] Session cleanup scheduled
- [ ] Error logging enabled
- [ ] Monitoring set up

**Data:**
- [ ] All customers exist in master
- [ ] All items exist in master
- [ ] Default company configured
- [ ] Price lists set up
- [ ] UOMs configured

### ✅ Step 13: Deploy to Production

**Deployment steps:**

1. [ ] Backup database
2. [ ] Update code on production server
3. [ ] Install dependencies on production
4. [ ] Configure OpenAI key (if using)
5. [ ] Restart services
6. [ ] Test with production data
7. [ ] Monitor logs for issues

**Post-deployment:**
- [ ] Test full workflow in production
- [ ] Monitor first 10 PDF uploads
- [ ] Check accuracy of extractions
- [ ] Gather user feedback

---

## 📊 Monitoring & Maintenance

### ✅ Step 14: Set Up Monitoring

**Logs to monitor:**
```bash
# Real-time monitoring
tail -f ~/frappe-bench-v15/logs/your-site.log | grep "PDF"

# Error monitoring
tail -f ~/frappe-bench-v15/logs/your-site.log | grep "ERROR.*PDF"
```

- [ ] Log monitoring configured
- [ ] Error alerts set up
- [ ] Success rate tracking
- [ ] Performance metrics tracked

**Metrics to track:**
- [ ] Extraction success rate (target: >90%)
- [ ] Average processing time (target: <5s)
- [ ] User confirmation rate (target: >95%)
- [ ] Error rate (target: <5%)
- [ ] Session completion rate

### ✅ Step 15: Regular Maintenance

**Daily:**
- [ ] Check error logs
- [ ] Monitor extraction success rate

**Weekly:**
- [ ] Review failed extractions
- [ ] Update extraction rules if needed
- [ ] Check storage usage

**Monthly:**
- [ ] Analyze extraction accuracy
- [ ] Update documentation
- [ ] Train team on new features
- [ ] Clean old test data

---

## 📚 Documentation & Training

### ✅ Step 16: Team Enablement

**Documentation:**
- [ ] Share PDF_QUICK_START.md with team
- [ ] Document company-specific PDF formats
- [ ] Create troubleshooting guide
- [ ] Document custom modifications

**Training:**
- [ ] Train support team on feature
- [ ] Create demo video
- [ ] Document common issues
- [ ] Set up support channels

**User Guide:**
- [ ] How to upload PDF
- [ ] How to review extracted data
- [ ] How to make corrections
- [ ] When to contact support

---

## ✅ Final Checklist

Before going live, ensure:

### Technical
- [x] All files created and in correct location
- [ ] All dependencies installed
- [ ] Tests passing
- [ ] APIs working
- [ ] Chat integration working
- [ ] No linter errors
- [ ] Error handling robust

### Business
- [ ] Team trained
- [ ] Documentation complete
- [ ] Support process defined
- [ ] Backup plan in place
- [ ] Rollback procedure documented

### Quality
- [ ] Tested with real PDFs
- [ ] Accuracy acceptable (>90%)
- [ ] Performance acceptable (<5s)
- [ ] User experience good
- [ ] Edge cases handled

---

## 🎉 Success Criteria

Consider implementation successful when:

1. ✅ **Installation**: All dependencies installed, tests passing
2. ✅ **Functionality**: Can process PDFs and create orders
3. ✅ **Accuracy**: >90% extraction accuracy with your PDFs
4. ✅ **Performance**: <5 seconds processing time
5. ✅ **User Experience**: Positive feedback from users
6. ✅ **Integration**: Seamlessly works with existing system
7. ✅ **Stability**: No critical errors in 1 week
8. ✅ **Adoption**: Team actively using the feature

---

## 📞 Support Checklist

If you encounter issues:

1. [ ] Check this checklist - did you miss a step?
2. [ ] Run dependency check
3. [ ] Check logs for specific errors
4. [ ] Review documentation
5. [ ] Test with sample PDFs
6. [ ] Check OpenAI API key (if using)
7. [ ] Verify customer/item masters exist
8. [ ] Check file permissions
9. [ ] Test API authentication
10. [ ] Review error messages carefully

---

## 📝 Notes & Observations

Use this space to track your implementation:

**Installation Date:** _______________

**Production Date:** _______________

**Issues Encountered:**
- 
- 
- 

**Customizations Made:**
- 
- 
- 

**Team Feedback:**
- 
- 
- 

**Next Steps:**
- 
- 
- 

---

## 🎯 Quick Reference

**Test Commands:**
```bash
# Check dependencies
bench --site <site> execute exim_backend.api.test_pdf_sales_order.check_dependencies

# Run tests
bench --site <site> execute exim_backend.api.test_pdf_sales_order.quick_test

# Setup test data
bench --site <site> execute exim_backend.api.test_pdf_sales_order.setup_test_data

# Full test
bench --site <site> execute exim_backend.api.test_pdf_sales_order.full_test
```

**API Endpoints:**
- Process PDF: `/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.process_pdf_file`
- Confirm: `/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.confirm_and_create`
- Update: `/api/method/exim_backend.api.doctypes.pdf_sales_order_handler.update_session_data`

**Key Files:**
- Main: `api/doctypes/pdf_sales_order_handler.py`
- PDF: `api/pdf_processor.py`
- AI: `api/ai_extractor.py`
- Chat: `api/pdf_chat_integration.py`

---

**🎉 You're ready to implement PDF sales order creation!**

**Start with Step 1 and work through systematically.**

**Good luck! 🚀**

---

Last Updated: November 2024  
Version: 1.0

