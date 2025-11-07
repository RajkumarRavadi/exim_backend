# Troubleshooting Guide

## Common Issues and Solutions

### 1. 400 BAD REQUEST Error

**Error Message:**
```
POST http://127.0.0.1:8002/api/method/exim_backend.api.ai_chat.process_chat 400 (BAD REQUEST)
```

**Cause:** Missing CSRF token in the API request headers.

**Solution:** ✅ FIXED - The JavaScript now includes the CSRF token in all POST requests.

**What was changed:**
- Added `getCSRFToken()` function to retrieve the CSRF token
- Added `X-Frappe-CSRF-Token` header to all fetch requests
- Added proper error handling for API responses

**If you still see this error:**
1. Clear your browser cache (Ctrl+Shift+R)
2. Restart your bench: `bench restart`
3. Check browser console for detailed error messages
4. Verify the Gemini API key is configured properly

---

### 2. "Gemini API key not configured" Error

**Error Message:**
```
Gemini API key not configured. Please add 'gemini_api_key' to site_config.json
```

**Cause:** The Gemini API key is not set in the site configuration.

**Solution:**
```bash
bench --site [your-site-name] set-config gemini_api_key YOUR_API_KEY_HERE
bench restart
```

**Verification:**
```bash
# Check if the key is set
bench --site [your-site-name] console
>>> frappe.conf.get("gemini_api_key")
```

---

### 3. Image Upload Not Working

**Error Message:** Image previews but doesn't process.

**Possible Causes:**
1. Tesseract OCR not installed
2. pytesseract Python package not installed
3. Invalid image format

**Solutions:**

**Install Tesseract:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Windows - Download from:
# https://github.com/UB-Mannheim/tesseract/wiki
```

**Install pytesseract:**
```bash
bench pip install pytesseract
```

**Check supported formats:**
- PNG, JPG, JPEG, GIF, BMP, TIFF

---

### 4. Chat Interface Not Loading

**Symptoms:** Blank page or 404 error when accessing `/ai-chat`

**Solution:**

1. **Check if the file exists:**
```bash
ls -la apps/exim_backend/exim_backend/www/ai-chat.html
```

2. **Restart bench:**
```bash
bench restart
```

3. **Clear build:**
```bash
bench build
bench clear-cache
bench restart
```

4. **Check file permissions:**
```bash
chmod 644 apps/exim_backend/exim_backend/www/ai-chat.html
```

---

### 5. CORS or Network Errors

**Error Message:**
```
Failed to load resource: net::ERR_CONNECTION_REFUSED
```

**Solutions:**

1. **Check if bench is running:**
```bash
bench start
```

2. **Check the correct port:** 
- Default development: `http://localhost:8000`
- If using port 8002: `http://localhost:8002`

3. **Check site name in URL:**
```
http://site-name:8000/ai-chat
```

---

### 6. Frappe Object Not Defined

**Error Message:**
```
Uncaught ReferenceError: frappe is not defined
```

**Cause:** The page is not loading the Frappe JavaScript framework.

**Solution:** The HTML template should extend `templates/web.html` which includes Frappe's JS.

**Verification in HTML:**
```html
{% extends "templates/web.html" %}
```

**If still not working:**
- Clear browser cache
- Hard refresh (Ctrl+Shift+R)
- Check browser console for other errors

---

### 7. Document Creation Fails

**Error Messages:**
- "Validation error: [field] is mandatory"
- "DocType '[name]' does not exist"
- "Failed to create document"

**Solutions:**

**For Mandatory Field Errors:**
- The AI may not have extracted all required fields
- Provide more detailed information in your message
- Example: Instead of "Create customer John", use "Create customer John Doe with email john@example.com"

**For DocType Not Found:**
- Verify the DocType exists in your ERPNext installation
- Check spelling and capitalization (it's case-sensitive)
- Some DocTypes may need specific modules installed

**For Permission Errors:**
- If `allow_guest=False`, ensure you're logged in
- Check user permissions for the DocType
- Guest users may have restricted access

---

### 8. Slow Response Times

**Symptoms:** AI takes a long time to respond

**Causes & Solutions:**

1. **Gemini API Rate Limits:**
   - Free tier has lower rate limits
   - Wait a few seconds between requests
   - Consider upgrading to paid tier

2. **Large Images:**
   - Compress images before uploading
   - Recommended: < 2MB, < 2000px width

3. **Complex Prompts:**
   - Keep messages concise
   - Break complex requests into smaller steps

---

### 9. JavaScript Console Warnings

**Warning about highlightAll():**
```
initHighlighting() is deprecated. Use highlightAll() instead.
```
- This is from Frappe's code highlighting library
- Does not affect functionality
- Can be safely ignored

**Warning about website_script.js:**
```
The resource was preloaded but not used within a few seconds
```
- This is a Frappe framework optimization warning
- Does not affect functionality
- Can be safely ignored

**Grammarly Extension Errors:**
```
grm ERROR [iterable] Not supported
```
- This is from the Grammarly browser extension
- Does not affect the chat functionality
- Can be safely ignored or disable Grammarly on this page

---

### 10. Response Format Issues

**Error:** AI response not displaying correctly

**Solution:** The JavaScript now properly handles Frappe's response format which wraps data in a `message` key.

**What was fixed:**
```javascript
const result = await response.json();
return result.message || result;  // Handle Frappe's response wrapper
```

---

## Debugging Tips

### Enable Debug Mode

1. **Check Backend Logs:**
```bash
tail -f logs/web.log
```

2. **Check Error Logs:**
```bash
tail -f logs/error.log
```

3. **Check Worker Logs:**
```bash
tail -f logs/worker.log
```

### Browser Console Debugging

Open browser console (F12) and check:
1. **Network Tab:** See actual API requests/responses
2. **Console Tab:** See JavaScript errors
3. **Application Tab:** Check cookies and localStorage

### Test API Directly

Use curl to test endpoints:

```bash
# Test chat endpoint
curl -X POST http://localhost:8000/api/method/exim_backend.api.ai_chat.process_chat \
  -H "X-Frappe-CSRF-Token: YOUR_TOKEN" \
  -F "message=Hello"

# Test with image
curl -X POST http://localhost:8000/api/method/exim_backend.api.ai_chat.process_chat \
  -H "X-Frappe-CSRF-Token: YOUR_TOKEN" \
  -F "message=What is this?" \
  -F "image=@/path/to/image.jpg"
```

### Get CSRF Token

In browser console:
```javascript
console.log(frappe.csrf_token);
```

---

## Performance Optimization

### For Production Use

1. **Enable Caching:**
   - Cache common AI responses
   - Use Redis for session management

2. **Rate Limiting:**
   - Implement request throttling
   - Prevent API abuse

3. **Image Optimization:**
   - Compress images on upload
   - Use image CDN

4. **Database Indexing:**
   - If storing chat history, add proper indexes
   - Monitor query performance

---

## Getting Help

If none of these solutions work:

1. **Check the logs:**
```bash
cd /path/to/your/bench
tail -f logs/*.log
```

2. **Enable verbose logging in Python:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

3. **Test with minimal example:**
```
Message: "Hello"
Expected: AI responds with a greeting
```

4. **Collect diagnostic info:**
- Frappe version: `bench version`
- Python version: `python --version`
- Node version: `node --version`
- Browser and version
- Error messages from console
- Network tab screenshot

5. **Check the implementation:**
- Verify all files exist
- Check file permissions
- Ensure bench is running
- Verify site is accessible

---

## Quick Checklist

Before reporting an issue, verify:

- [ ] Gemini API key is configured
- [ ] Bench is running (`bench start`)
- [ ] Dependencies installed (`bench pip install google-generativeai pytesseract`)
- [ ] Tesseract OCR installed on system
- [ ] Browser cache cleared
- [ ] CSRF token is being sent (check Network tab)
- [ ] No errors in bench logs
- [ ] Site URL is correct
- [ ] Internet connection is working (for Gemini API)
- [ ] API key has not exceeded quota

---

## Recent Fixes Applied

### Version 1.0.1 - CSRF Token Fix

**Date:** 2024

**Changes:**
- ✅ Added CSRF token to all POST requests
- ✅ Added proper error handling for API responses
- ✅ Fixed Frappe response format handling
- ✅ Added logging to backend for debugging
- ✅ Improved error messages

**Migration:** No action needed, just refresh the page after bench restart.

---

## Contact & Support

For additional help:
- Review the SETUP_GUIDE.md
- Check the IMPLEMENTATION_SUMMARY.md
- Review inline code comments
- Check Frappe/ERPNext community forums

