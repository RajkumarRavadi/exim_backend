import frappe
import json
import os
import requests
from PIL import Image
import hashlib
import time

# Import the existing image extraction function
from exim_backend.api.image_reader import extract_text_from_image

# Import PDF chat integration for sales order creation from PDFs
from exim_backend.api.pdf_chat_integration import (
	PDFChatIntegration,
	check_pdf_context,
	handle_pdf_in_chat,
	handle_pdf_response,
	is_pdf_sales_order_intent
)


def estimate_tokens(text):
	"""
	Estimate token count (rough approximation: 1 token ≈ 4 characters for English).
	More accurate: ~0.75 tokens per word or 4 characters per token.
	"""
	if not text:
		return 0
	# Rough estimation: 1 token ≈ 4 characters
	return len(text) // 4


def get_conversation_history(session_id, limit=10):
	"""
	Get conversation history for a session.
	Stored in Frappe cache (session-based).
	"""
	if not session_id:
		return []
	
	cache_key = f"ai_chat_history_{session_id}"
	cached_data = frappe.cache().get(cache_key)
	
	if cached_data:
		try:
			# Handle bytes (decode to string first)
			if isinstance(cached_data, bytes):
				cached_data = cached_data.decode('utf-8')
			
			# Deserialize from JSON if it's a string
			if isinstance(cached_data, str):
				history = json.loads(cached_data)
			elif isinstance(cached_data, list):
				# Already a list (shouldn't happen but handle it)
				history = cached_data
			else:
				history = []
		except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as e:
			frappe.logger().error(f"Error deserializing history: {str(e)}")
			history = []
	else:
		history = []
	
	# Return last N messages
	return history[-limit:] if history else []


def save_to_history(session_id, role, content):
	"""
	Save a message to conversation history.
	"""
	if not session_id:
		return
	
	cache_key = f"ai_chat_history_{session_id}"
	cached_data = frappe.cache().get(cache_key)
	
	if cached_data:
		try:
			# Handle bytes (decode to string first)
			if isinstance(cached_data, bytes):
				cached_data = cached_data.decode('utf-8')
			
			# Deserialize from JSON if it's a string
			if isinstance(cached_data, str):
				history = json.loads(cached_data)
			elif isinstance(cached_data, list):
				# Already a list (shouldn't happen but handle it)
				history = cached_data
			else:
				history = []
		except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as e:
			frappe.logger().error(f"Error deserializing history: {str(e)}")
			history = []
	else:
		history = []
	
	history.append({
		"role": role,
		"content": content,
		"timestamp": time.time()
	})
	
	# Keep only last 20 messages to prevent memory issues
	history = history[-20:]
	
	# Store in cache as JSON string (expires in 24 hours = 86400 seconds)
	try:
		history_json = json.dumps(history)
		frappe.cache().set(cache_key, history_json)
		frappe.cache().expire(cache_key, 86400)
	except Exception as e:
		frappe.logger().error(f"Error saving history to cache: {str(e)}")


def clear_history(session_id):
	"""Clear conversation history for a session."""
	if session_id:
		cache_key = f"ai_chat_history_{session_id}"
		frappe.cache().delete(cache_key)


def build_optimized_system_prompt(doctype_fields_map):
	"""
	Build optimized, concise system prompt for multiple doctypes.
	
	Args:
		doctype_fields_map: Dict of {doctype: field_reference_string}
	"""
	# Build doctype sections
	doctype_sections = []
	for doctype, fields in doctype_fields_map.items():
		if fields and fields != "Fields metadata not available":
			doctype_sections.append(f"{doctype.upper()} FIELDS:\n{fields}")
	
	fields_section = "\n\n".join(doctype_sections) if doctype_sections else "No field metadata available"
	
	# Get available doctypes
	from exim_backend.api.doctypes import get_available_doctypes
	available_doctypes = ", ".join(get_available_doctypes())
	
	return f"""You are an ERPNext AI assistant. Help users with ERPNext data across multiple doctypes.

AVAILABLE DOCTYPES: {available_doctypes}

{fields_section}

IMPORTANT: The fields list above shows COMMON fields, but get_document_details returns ALL fields including:
- All standard fields (name, creation, modified, etc.)
- All custom fields
- Calculated fields (like total_projected_qty, valuation_rate, etc.)
- Related data (prices, stock, uoms, etc.)
When user asks about ANY field of a specific document, use get_document_details - it returns complete data.

ACTIONS:
1. DIRECT ANSWER - Answer from context (no JSON)
2. dynamic_search - Query with filters and sorting: {{"action": "dynamic_search", "doctype": "Customer", "filters": {{"field": "value"}}, "order_by": "field desc", "limit": 1, "execute_immediately": true}}
3. get_document_details - Full details (returns ALL fields): {{"action": "get_document_details", "doctype": "Customer", "name": "X", "execute_immediately": true}}
4. count_documents - Statistics: {{"action": "count_documents", "doctype": "Customer", "filters": {{"field": "value"}}, "execute_immediately": true}}
5. create_document - Create: {{"action": "create_document", "doctype": "Customer", "fields": {{}}, "execute_immediately": false}}
   
   ⚠️ CRITICAL FOR CUSTOMER CREATION ⚠️
   When user provides customer creation request with name, phone, and email:
   - DO NOT ask for more information - extract what's provided and create the action
   - Extract customer name, phone/mobile number, email from the natural language query
   - Map correctly: name → customer_name, phone/mobile → mobile_no, email → email_id
   - Phone numbers: Extract digits only (remove spaces, dashes, parentheses if present)
   - Email: Extract the full email address as provided
   - ALWAYS set execute_immediately: false to show action button for user review
   - Example: "Create customer Kunal 9988775566 kunal@example.com" 
     → Extract: customer_name="Kunal", mobile_no="9988775566", email_id="kunal@example.com"
     → Response: Show friendly message + action button with extracted fields
   - If user provides all three (name, phone, email), create the action immediately - DO NOT ask for more
6. find_duplicates - Find duplicates (Customer only): {{"action": "find_duplicates", "doctype": "Customer", "execute_immediately": true}}
7. get_customers_by_order_count - Top customers by order count (Sales Order only): {{"action": "get_customers_by_order_count", "limit": 5, "execute_immediately": true}}
8. get_customers_by_order_value - Biggest customers by total value (Sales Order only): {{"action": "get_customers_by_order_value", "limit": 5, "execute_immediately": true}}
9. get_orders_by_customer_group - Orders by customer group (Sales Order only): {{"action": "get_orders_by_customer_group", "customer_group": "Group Name", "execute_immediately": true}}
10. get_orders_by_territory - Orders by territory (Sales Order only): {{"action": "get_orders_by_territory", "territory": "Territory Name", "execute_immediately": true}}
11. get_orders_by_item - Orders containing specific item (Sales Order only): {{"action": "get_orders_by_item", "item_code": "Item Code", "execute_immediately": true}}
12. get_orders_with_most_items - Orders with most line items (Sales Order only): {{"action": "get_orders_with_most_items", "limit": 10, "execute_immediately": true}}
13. get_orders_by_item_group - Orders with items from specific group (Sales Order only): {{"action": "get_orders_by_item_group", "item_group": "Item Group Name", "execute_immediately": true}}
14. get_total_quantity_sold - Total quantity sold for item (Sales Order only): {{"action": "get_total_quantity_sold", "item_code": "Item Code", "from_date": "this week", "to_date": "today", "execute_immediately": true}}
15. get_most_sold_items - Most sold items aggregated (Sales Order only): {{"action": "get_most_sold_items", "limit": 5, "from_date": "this week", "execute_immediately": true}}

FILTER OPERATORS:
- {{"$like": "%text%"}} - Partial match
- {{"$is_null": true}} - Missing/empty field
- {{"$is_not_null": true}} - Has value
- {{"field": "value"}} - Exact match

EXAMPLES:
Q: "Find customer Rajkumar" → {{"action": "dynamic_search", "doctype": "Customer", "filters": {{"customer_name": {{"$like": "%Rajkumar%"}}}}, "execute_immediately": true}}
Q: "Customers without email" → {{"action": "dynamic_search", "doctype": "Customer", "filters": {{"email_id": {{"$is_null": true}}}}, "execute_immediately": true}}
Q: "Create supplier ABC Corp" → {{"action": "create_document", "doctype": "Supplier", "fields": {{"supplier_name": "ABC Corp"}}, "execute_immediately": false}}
Q: "Create new customer Kunal 9988775566 kunal@example.com" → {{"action": "create_document", "doctype": "Customer", "fields": {{"customer_name": "Kunal", "mobile_no": "9988775566", "email_id": "kunal@example.com"}}, "execute_immediately": false}}
Q: "Create customer John Doe with phone 1234567890 and email john@test.com" → {{"action": "create_document", "doctype": "Customer", "fields": {{"customer_name": "John Doe", "mobile_no": "1234567890", "email_id": "john@test.com"}}, "execute_immediately": false}}
Q: "Create new customer Rajkumar Ravadi, 9381964965, rajkumarravadi3@gmail.com" → {{"action": "create_document", "doctype": "Customer", "fields": {{"customer_name": "Rajkumar Ravadi", "mobile_no": "9381964965", "email_id": "rajkumarravadi3@gmail.com"}}, "execute_immediately": false}}

CRITICAL FOR CUSTOMER CREATION:
- When user says "create customer [name] [phone] [email]", ALWAYS extract all three pieces of information
- Map them correctly: name → customer_name, phone/mobile → mobile_no, email → email_id
- Phone numbers can be in any format (with/without spaces, dashes, parentheses) - extract digits only if needed
- Email addresses are usually clear - extract the full email
- ALWAYS set execute_immediately: false so user can review before creating
- DO NOT ask for more information if name, phone, and email are provided - extract them and show action button
- If only name is provided, you can still create the action but mention missing fields in your response
Q: "How many customers?" → {{"action": "count_documents", "doctype": "Customer", "execute_immediately": true}}
Q: "What's X's phone?" → Direct answer if known, else search
Q: "Show item description for banana" → {{"action": "get_document_details", "doctype": "Item", "name": "banana", "execute_immediately": true}}
Q: "What are the UOMs for item Apple?" → {{"action": "get_document_details", "doctype": "Item", "name": "Apple", "execute_immediately": true}}
Q: "What is the conversion factor for Pair in item Banana?" → {{"action": "get_document_details", "doctype": "Item", "name": "Banana", "execute_immediately": true}}
Q: "What is the total projected qty of item banana?" → {{"action": "get_document_details", "doctype": "Item", "name": "banana", "execute_immediately": true}}
Q: "What is the [ANY FIELD] of [ITEM NAME]?" → ALWAYS use get_document_details
Q: "Sales Order with highest value" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{}}, "order_by": "grand_total desc", "limit": 1, "execute_immediately": true}}
Q: "Sales Order with lowest value" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{}}, "order_by": "grand_total asc", "limit": 1, "execute_immediately": true}}
Q: "Highest value sales order" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{}}, "order_by": "grand_total desc", "limit": 1, "execute_immediately": true}}
Q: "Sales orders created today" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"creation": "today"}}, "execute_immediately": true}}
Q: "Sales orders created on 08-11-2025" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"creation": "08-11-2025"}}, "execute_immediately": true}}
Q: "Sales orders with transaction date 08-11-2025" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"transaction_date": "08-11-2025"}}, "execute_immediately": true}}
Q: "Sales orders created yesterday" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"creation": "yesterday"}}, "execute_immediately": true}}
Q: "Show me all sales orders" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{}}, "order_by": "modified desc", "execute_immediately": true}}
Q: "List sales orders created this week" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"creation": {{"$gte": "this week", "$lte": "today"}}}}, "order_by": "creation desc", "execute_immediately": true}}
Q: "Show submitted sales orders" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"status": "Submitted"}}, "execute_immediately": true}}
Q: "Show completed sales orders" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"status": "Completed"}}, "execute_immediately": true}}
Q: "Show draft sales orders" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"status": "Draft"}}, "execute_immediately": true}}
Q: "How many sales orders are there?" → {{"action": "count_documents", "doctype": "Sales Order", "execute_immediately": true}}
Q: "List all sales orders for Company A" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"company": "Company A"}}, "execute_immediately": true}}
Q: "Sales orders created in the last 7 days" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"creation": {{"$gte": "7 days ago"}}}}, "order_by": "creation desc", "execute_immediately": true}}
Q: "Show orders from John Traders" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"customer": "John Traders"}}, "execute_immediately": true}}
Q: "How many orders has John Traders placed?" → {{"action": "count_documents", "doctype": "Sales Order", "filters": {{"customer": "John Traders"}}, "execute_immediately": true}}
Q: "Top 5 customers by order count" → Use count_by_customer API endpoint or dynamic_search. For top N, use count_by_customer with limit parameter
Q: "Who are my biggest customers?" → Use get_customers_by_order_value API endpoint to get customers with highest total order value
Q: "Show orders from South Region customers" → Use get_orders_by_territory API endpoint with territory="South Region"
Q: "Show orders from customers in Demo Customer Group" → Use get_orders_by_customer_group API endpoint with customer_group="Demo Customer Group"
Q: "Show orders containing Laptop Model X" → {{"action": "get_orders_by_item", "item_code": "Laptop Model X", "execute_immediately": true}}
Q: "Which orders have the most line items?" → {{"action": "get_orders_with_most_items", "limit": 10, "execute_immediately": true}}
Q: "Show orders with Electronics items" → {{"action": "get_orders_by_item_group", "item_group": "Electronics", "execute_immediately": true}}
Q: "Total Laptops sold this week" → {{"action": "get_total_quantity_sold", "item_code": "Laptop", "from_date": "this week", "execute_immediately": true}}
Q: "Top 5 most ordered products" → {{"action": "get_most_sold_items", "limit": 5, "execute_immediately": true}}
Q: "Orders placed today" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"transaction_date": "today"}}, "execute_immediately": true}}
Q: "Orders created today" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"creation": "today"}}, "execute_immediately": true}}
Q: "Orders this week" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"transaction_date": {{"$gte": "this week", "$lte": "today"}}}}, "execute_immediately": true}}
Q: "Orders this month" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"transaction_date": {{"$gte": "1 month ago"}}}}, "execute_immediately": true}}
Q: "Orders between Aug 1 and Aug 31" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"transaction_date": {{"$gte": "01-08-2025", "$lte": "31-08-2025"}}}}, "execute_immediately": true}}
Q: "Deliveries scheduled this week" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"delivery_date": {{"$gte": "this week", "$lte": "today"}}}}, "execute_immediately": true}}
Q: "Orders expected for delivery today" → {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{"delivery_date": "today"}}, "execute_immediately": true}}
Q: "Which customer has more sales orders?" → Use count_documents with filters grouped by customer, or use dynamic_search to get all sales orders and analyze
Q: "Which sales order contains more items?" → Use get_document_details for each sales order to count items, or use dynamic_search with order_by based on item count if available

RULES:
- ALWAYS specify doctype in action JSON
- Return ONLY JSON for actions (no markdown)
- Set execute_immediately: true for queries, false for creates
- Use direct answers when possible (no JSON needed)
- CRITICAL RULE: When user asks about ANY field/information of a SPECIFIC named item/customer/etc, ALWAYS use get_document_details
- get_document_details returns ALL fields (not just the ones in the fields list above) - use it for any field question
- For questions like "what is X of item Y" or "show me X for Y", use get_document_details
- NEVER say "I cannot" or "field not available" - instead use get_document_details to get complete data
- NEVER ask user to fetch details first - automatically use get_document_details
- IMPORTANT: When providing text responses, use plain text or markdown format (use * for lists, ** for bold, ` for code). NEVER use HTML tags like <p>, <ul>, <li> in your responses - the system will format it automatically
- SORTING: Use "order_by" in dynamic_search to sort results. Examples: "grand_total desc" (highest first), "grand_total asc" (lowest first), "modified desc" (newest first)
- FINDING MAX/MIN: To find highest/lowest value, use dynamic_search with order_by and limit: 1. Example: {{"action": "dynamic_search", "doctype": "Sales Order", "filters": {{}}, "order_by": "grand_total desc", "limit": 1, "execute_immediately": true}}
- DATE FILTERS: For date queries, use field names: "creation" (for created date), "transaction_date" (for transaction/order date), "delivery_date" (for delivery date). Date formats supported: "today", "yesterday", "DD-MM-YYYY" (e.g., "08-11-2025"), "YYYY-MM-DD" (e.g., "2025-11-08"), "this week", "7 days ago", "1 month ago", "this month". The system will automatically convert formats.
- FIELD MAPPING: "created" or "created_date" maps to "creation", "date" or "order_date" maps to "transaction_date"
- DATE RANGE QUERIES: Use operators like {{"$gte": "start_date"}} for "greater than or equal" and {{"$lte": "end_date"}} for "less than or equal". For "between two dates", use both: {{"transaction_date": {{"$gte": "start", "$lte": "end"}}}}. For "this week", use both bounds: {{"creation": {{"$gte": "this week", "$lte": "today"}}}} to get records from start of week to today. For "this month", use {{"$gte": "1 month ago"}} or {{"$gte": "this month"}}.
- DELIVERY DATE QUERIES: For delivery-related queries, use "delivery_date" field. "Deliveries scheduled this week" → {{"delivery_date": {{"$gte": "this week", "$lte": "today"}}}}, "Orders expected for delivery today" → {{"delivery_date": "today"}}.
- CONTEXT AWARENESS: When user asks follow-up questions like "what is it", "give its details", "show me that", etc., refer to the previous conversation. Extract document names from the previous assistant message. Look for patterns like "Document name: X" or document IDs in the format like "SAL-ORD-2025-00006", "CUST-00001", etc. If a search or count query returned 1 document, use that document's name automatically. If multiple documents were mentioned, use the first one or ask for clarification only if truly ambiguous.
- When user says "it", "that", "this", or similar pronouns, they refer to the most recently mentioned document(s) in the conversation. Look for document names/IDs in the previous assistant message (they appear as bold text or in format like SAL-ORD-XXXX, CUST-XXXX, etc.). Use get_document_details with the document name from context.
- EXTRACTING DOCUMENT NAMES: When you see search results or count results in the conversation, extract the document name/ID. Common patterns: Sales Orders (SAL-ORD-XXXX), Customers (CUST-XXXX or customer names), Items (item codes or names). The document name is usually the first bold text or ID shown in the result.
- Think before acting - understand intent and doctype first"""


def get_ai_config():
	"""Get AI API configuration."""
	api_key = frappe.conf.get("openrouter_api_key") or frappe.conf.get("gemini_api_key")
	if not api_key:
		frappe.throw("AI API key not configured. Please add 'openrouter_api_key' to site_config.json")
	
	# Check if using OpenRouter or direct Gemini
	use_openrouter = frappe.conf.get("openrouter_api_key") is not None
	
	return {
		"api_key": api_key,
		"use_openrouter": use_openrouter,
		"model": frappe.conf.get("ai_model") or ("google/gemini-2.0-flash-exp:free" if use_openrouter else "gemini-1.5-flash")
	}


def call_ai_api(messages, config, stream=False):
	"""
	Call AI API with conversation history support.
	
	Args:
		messages: List of message dicts with 'role' and 'content' keys
		config: AI configuration dict
		stream: Whether to stream the response (OpenRouter only)
	
	Returns:
		Response text or generator for streaming
	"""
	if config["use_openrouter"]:
		# Use OpenRouter API (OpenAI-compatible format)
		headers = {
			"Authorization": f"Bearer {config['api_key']}",
			"Content-Type": "application/json",
			"HTTP-Referer": frappe.conf.get("site_url", "http://localhost"),
			"X-Title": "ERPNext AI Assistant"
		}
		
		data = {
			"model": config["model"],
			"messages": messages,
			"stream": stream
		}
		
		if stream:
			# For streaming, return the response object
			response = requests.post(
				"https://openrouter.ai/api/v1/chat/completions",
				headers=headers,
				json=data,
				timeout=60,
				stream=True
			)
			
			if response.status_code != 200:
				frappe.throw(f"OpenRouter API error: {response.status_code} - {response.text}")
			
			return response
		else:
			response = requests.post(
				"https://openrouter.ai/api/v1/chat/completions",
				headers=headers,
				json=data,
				timeout=60
			)
			
			if response.status_code != 200:
				frappe.throw(f"OpenRouter API error: {response.status_code} - {response.text}")
			
			result = response.json()
			return result["choices"][0]["message"]["content"]
	else:
		# Use direct Google Gemini API
		# Convert messages to single prompt (Gemini doesn't support message history well)
		if len(messages) > 1:
			# Combine system and user messages
			prompt_parts = []
			for msg in messages:
				if msg["role"] == "system":
					prompt_parts.append(f"System: {msg['content']}")
				elif msg["role"] == "user":
					prompt_parts.append(f"User: {msg['content']}")
				elif msg["role"] == "assistant":
					prompt_parts.append(f"Assistant: {msg['content']}")
			prompt = "\n\n".join(prompt_parts)
		else:
			prompt = messages[0]["content"]
		
		import google.generativeai as genai
		genai.configure(api_key=config["api_key"])
		model = genai.GenerativeModel(config["model"])
		response = model.generate_content(prompt)
		return response.text


@frappe.whitelist(allow_guest=True, methods=["POST"])
def process_chat():
	"""
	Main chat endpoint that processes user messages, images, and PDFs.
	Now supports conversation history, token counting, streaming, and PDF sales order creation.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.process_chat
	Accepts: 
		- message (text): User's message
		- image (file, optional): Image to extract text from
		- pdf (file, optional): PDF file for sales order creation
		- file (file, optional): Generic file upload (supports PDF)
		- session_id (text, optional): Session ID for conversation history
		- clear_history (bool, optional): Clear conversation history
	Returns: AI response with suggested actions, token usage info
	
	PDF Sales Order Workflow:
		1. Upload PDF with message containing "sales order" or "order"
		2. AI extracts customer, items, dates, prices
		3. User reviews extracted data
		4. User confirms/modifies data
		5. Sales order is created automatically
	"""
	try:
		message = frappe.form_dict.get("message", "").strip()
		image_file = frappe.request.files.get("image")
		session_id = frappe.form_dict.get("session_id") or frappe.session.get("sid") or "default"
		clear_hist = frappe.form_dict.get("clear_history", "false").lower() == "true"
		
		frappe.logger().info(f"Chat request - Session: {session_id[:10]}, Message: {message[:50] if message else 'None'}, Has Image: {bool(image_file)}")
		
		# Clear history if requested
		if clear_hist:
			clear_history(session_id)
		
		# ========== PDF SALES ORDER INTEGRATION START ==========
		# Check if user has an active PDF session (awaiting confirmation/modification)
		pdf_context = check_pdf_context(session_id)
		if pdf_context.get("has_context"):
			frappe.logger().info(f"Active PDF session found for {session_id[:10]}, handling response")
			# User is in middle of PDF workflow - handle their response
			pdf_result = handle_pdf_response(session_id, message)
			
			# Save to history
			save_to_history(session_id, "user", message)
			save_to_history(session_id, "assistant", pdf_result["message"])
			
			return {
				"status": pdf_result.get("status", "success"),
				"response": pdf_result["message"],
				"requires_action": pdf_result.get("requires_action", False),
				"completed": pdf_result.get("completed", False),
				"cancelled": pdf_result.get("cancelled", False)
			}
		
		# Check for PDF file upload
		pdf_file = frappe.request.files.get("pdf") or frappe.request.files.get("file")
		if pdf_file and pdf_file.filename.lower().endswith('.pdf'):
			frappe.logger().info(f"PDF file uploaded: {pdf_file.filename}")
			
			try:
				# Save PDF to files
				from frappe.utils.file_manager import save_file
				file_doc = save_file(
					fname=pdf_file.filename,
					content=pdf_file.read(),
					dt=None,
					dn=None,
					is_private=0
				)
				file_url = file_doc.file_url
				
				frappe.logger().info(f"PDF saved to: {file_url}")
				
				# AUTOMATICALLY process any PDF upload for sales order creation
				frappe.logger().info(f"Automatically processing PDF for sales order creation")
				try:
					pdf_result = handle_pdf_in_chat(file_url, session_id, message or "Create sales order from PDF")
				except Exception as pdf_error:
					frappe.logger().error(f"Error in handle_pdf_in_chat: {str(pdf_error)}")
					frappe.logger().exception("Full traceback:")
					return {
						"status": "error",
						"response": f"❌ Failed to process PDF: {str(pdf_error)}. Please check server logs for details.",
						"requires_action": False,
						"session_id": session_id
					}
				
				# Save to history
				save_to_history(session_id, "user", f"{message or 'Uploaded PDF'} [PDF: {pdf_file.filename}]")
				save_to_history(session_id, "assistant", pdf_result.get("message", "PDF processed"))
				
				return {
					"status": pdf_result.get("status", "success"),
					"response": pdf_result.get("message", "PDF processed successfully"),
					"requires_action": pdf_result.get("requires_action", False),
					"data": pdf_result.get("data"),
					"session_id": session_id
				}
			except Exception as e:
				frappe.logger().error(f"Error processing PDF file: {str(e)}")
				frappe.logger().exception("Full traceback:")
				return {
					"status": "error",
					"response": f"❌ Failed to process PDF file: {str(e)}. Please ensure the file is a valid PDF and try again.",
					"requires_action": False,
					"session_id": session_id
				}
		# ========== PDF SALES ORDER INTEGRATION END ==========
		
		if not message and not image_file:
			frappe.response["http_status_code"] = 400
			return {
				"status": "error",
				"message": "Please provide a message or image"
			}
		
		# Extract text from image if provided
		extracted_text = ""
		if image_file:
			# Save temporarily and extract text
			temp_path = frappe.get_site_path("public", "temp")
			os.makedirs(temp_path, exist_ok=True)
			filepath = os.path.join(temp_path, image_file.filename)
			image_file.save(filepath)
			
			# Extract text using OCR
			from pytesseract import image_to_string
			extracted_text = image_to_string(Image.open(filepath))
			
			# Cleanup
			os.remove(filepath)
			
			# If no message, use extracted text as message
			if not message:
				message = f"I uploaded an image with this text: {extracted_text}"
			else:
				message = f"{message}\n\nExtracted text from image: {extracted_text}"
		
		# Get AI configuration
		config = get_ai_config()
		
		# Detect doctypes from message or use default (Customer for now)
		from exim_backend.api.doctypes import get_available_doctypes, get_handler
		
		# Simple doctype detection from message
		message_lower = message.lower()
		detected_doctypes = []
		
		# Check for doctype mentions
		doctype_keywords = {
			"Customer": ["customer", "customers", "client", "clients"],
			"Supplier": ["supplier", "suppliers", "vendor", "vendors"],
			"Item": ["item", "items", "product", "products"],
			"Lead": ["lead", "leads", "prospect", "prospects"],
			"Sales Order": ["sales order", "sales orders", "so", "salesorder"],
			"Purchase Order": ["purchase order", "purchase orders", "po"],
		}
		
		available_doctypes = get_available_doctypes()
		for doctype in available_doctypes:
			keywords = doctype_keywords.get(doctype, [doctype.lower()])
			if any(keyword in message_lower for keyword in keywords):
				detected_doctypes.append(doctype)
		
		# Default to Customer if no doctype detected
		if not detected_doctypes:
			detected_doctypes = ["Customer"]
		
		# Fetch field metadata for detected doctypes
		doctype_fields_map = {}
		for doctype in detected_doctypes:
			handler = get_handler(doctype)
			if handler:
				fields_info = handler.get_fields_info()
				doctype_fields_map[doctype] = handler.build_field_reference(fields_info)
			else:
				doctype_fields_map[doctype] = "Fields metadata not available"
		
		# Build optimized system prompt with multiple doctypes
		system_prompt = build_optimized_system_prompt(doctype_fields_map)
		
		# Get conversation history
		history = get_conversation_history(session_id, limit=10)
		
		# Build messages array
		messages = [{"role": "system", "content": system_prompt}]
		
		# Add conversation history
		for h in history:
			messages.append({"role": h["role"], "content": h["content"]})
		
		# Add current user message
		messages.append({"role": "user", "content": message})
		
		# Calculate token usage
		total_tokens = sum([estimate_tokens(msg["content"]) for msg in messages])
		max_tokens = frappe.conf.get("ai_max_tokens", 8000)  # Default limit
		
		# Truncate history if too long
		if total_tokens > max_tokens:
			# Keep system prompt and current message, reduce history
			excess = total_tokens - max_tokens
			system_tokens = estimate_tokens(system_prompt)
			user_tokens = estimate_tokens(message)
			available_for_history = max_tokens - system_tokens - user_tokens - 500  # Buffer
			
			# Keep only recent history that fits
			trimmed_history = []
			history_tokens = 0
			for h in reversed(history):
				h_tokens = estimate_tokens(h["content"])
				if history_tokens + h_tokens <= available_for_history:
					trimmed_history.insert(0, h)
					history_tokens += h_tokens
				else:
					break
			
			messages = [{"role": "system", "content": system_prompt}]
			for h in trimmed_history:
				messages.append({"role": h["role"], "content": h["content"]})
			messages.append({"role": "user", "content": message})
			total_tokens = sum([estimate_tokens(msg["content"]) for msg in messages])
		
		# Log token usage
		frappe.logger().info(f"Token usage - Total: {total_tokens}, System: {estimate_tokens(system_prompt)}, History: {len(history)} msgs, User: {estimate_tokens(message)}")
		
		# Log the exact prompt being sent to AI
		frappe.logger().info("=" * 80)
		frappe.logger().info("EXACT PROMPT BEING SENT TO AI")
		frappe.logger().info("=" * 80)
		frappe.logger().info(f"Session ID: {session_id[:20]}...")
		frappe.logger().info(f"Detected DocTypes: {detected_doctypes}")
		frappe.logger().info(f"Total Messages: {len(messages)}")
		frappe.logger().info(f"Conversation History: {len(history)} messages")
		frappe.logger().info("-" * 80)
		
		# Log each message in the array
		for idx, msg in enumerate(messages, 1):
			role = msg.get("role", "unknown")
			content = msg.get("content", "")
			content_preview = content[:200] + "..." if len(content) > 200 else content
			token_count = estimate_tokens(content)
			
			frappe.logger().info(f"\n[{idx}] Role: {role.upper()} ({token_count} tokens)")
			frappe.logger().info(f"Content Preview: {content_preview}")
			
			# For system prompt, log full content
			if role == "system":
				frappe.logger().info("Full System Prompt:")
				frappe.logger().info("-" * 80)
				frappe.logger().info(content)
				frappe.logger().info("-" * 80)
			# For history and user messages, log full content (they're usually shorter)
			elif role in ["user", "assistant"]:
				frappe.logger().info(f"Full Content:")
				frappe.logger().info(content)
		
		frappe.logger().info("=" * 80)
		frappe.logger().info("END OF PROMPT LOG")
		frappe.logger().info("=" * 80)
		
		# Also log as JSON for easy parsing (truncated for very long content)
		try:
			# Create a version for logging (truncate very long content)
			messages_for_log = []
			for msg in messages:
				msg_copy = msg.copy()
				content = msg_copy.get("content", "")
				if len(content) > 5000:
					msg_copy["content"] = content[:5000] + f"\n... [TRUNCATED - {len(content)} total chars]"
				messages_for_log.append(msg_copy)
			
			frappe.logger().info("Messages Array (JSON format, truncated if >5000 chars):")
			frappe.logger().info(json.dumps(messages_for_log, indent=2, ensure_ascii=False))
		except Exception as e:
			frappe.logger().error(f"Error logging messages as JSON: {str(e)}")
		
		# Save user message to history
		save_to_history(session_id, "user", message)
		
		# Generate response using AI with conversation history
		ai_response = call_ai_api(messages, config, stream=False)
		
		# Save AI response to history
		save_to_history(session_id, "assistant", ai_response)
		
		# Try to parse if there's a suggested action in the response
		suggested_action = None
		try:
			# Look for JSON in the response
			if "suggested_action" in ai_response.lower() or "action" in ai_response.lower():
				# Remove markdown code blocks if present
				import re
				
				# Try to find JSON in markdown code blocks first (more specific)
				json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
				match = re.search(json_pattern, ai_response, re.DOTALL)
				
				if match:
					json_str = match.group(1).strip()
					frappe.logger().info(f"Found JSON in code block: {json_str[:100]}...")
				else:
					# Try to extract JSON without code blocks
					start_idx = ai_response.find("{")
					end_idx = ai_response.rfind("}") + 1
					if start_idx != -1 and end_idx > start_idx:
						json_str = ai_response[start_idx:end_idx].strip()
						frappe.logger().info(f"Found JSON without code block: {json_str[:100]}...")
					else:
						json_str = None
				
				if json_str:
					# Clean up the JSON string
					json_str = json_str.replace('\n', ' ').replace('\r', '')
					parsed = json.loads(json_str)
					
					frappe.logger().info(f"Parsed JSON structure: {parsed.keys()}")
					
					# Check if it has the suggested_action structure
					if "suggested_action" in parsed:
						suggested_action = parsed["suggested_action"]
						frappe.logger().info(f"Extracted suggested_action: {suggested_action}")
					elif "action" in parsed:
						# Already at action level
						suggested_action = parsed
						frappe.logger().info(f"Using direct action: {suggested_action}")
		except json.JSONDecodeError as e:
			frappe.logger().error(f"JSON decode error: {str(e)}")
			frappe.logger().error(f"Failed JSON string: {json_str if 'json_str' in locals() else 'N/A'}")
		except Exception as e:
			frappe.logger().error(f"Error parsing suggested action: {str(e)}")
			pass
		
		# Calculate response tokens
		response_tokens = estimate_tokens(ai_response)
		
		# Log for debugging
		frappe.logger().info(f"AI Response length: {len(ai_response)}, Tokens: {response_tokens}")
		frappe.logger().info(f"Suggested action found: {suggested_action is not None}")
		if suggested_action:
			frappe.logger().info(f"Suggested action details: {json.dumps(suggested_action)}")
		
		# Prepare prompt info for frontend logging
		prompt_info = {
			"detected_doctypes": detected_doctypes,
			"total_messages": len(messages),
			"history_count": len(history),
			"system_prompt_preview": system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt,
			"system_prompt_length": len(system_prompt),
			"system_prompt_tokens": estimate_tokens(system_prompt),
			"messages_summary": [
				{
					"role": msg.get("role"),
					"content_preview": msg.get("content", "")[:200] + "..." if len(msg.get("content", "")) > 200 else msg.get("content", ""),
					"content_length": len(msg.get("content", "")),
					"tokens": estimate_tokens(msg.get("content", ""))
				}
				for msg in messages
			],
			"full_messages": messages  # Include full messages for detailed inspection
		}
		
		return {
			"status": "success",
			"message": ai_response,
			"suggested_action": suggested_action,
			"extracted_text": extracted_text if image_file else None,
			"token_usage": {
				"input_tokens": total_tokens,
				"output_tokens": response_tokens,
				"total_tokens": total_tokens + response_tokens
			},
			"session_id": session_id,
			"prompt_info": prompt_info  # Add prompt info for frontend logging
		}
		
	except Exception as e:
		frappe.log_error(f"Chat processing error: {str(e)}")
		return {
			"status": "error",
			"message": f"An error occurred: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def clear_chat_history():
	"""
	Clear conversation history for a session.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.clear_chat_history
	Accepts:
		- session_id: Session ID to clear history for
	Returns: Success status
	"""
	try:
		session_id = frappe.form_dict.get("session_id") or frappe.session.get("sid") or "default"
		clear_history(session_id)
		return {
			"status": "success",
			"message": "Conversation history cleared"
		}
	except Exception as e:
		frappe.logger().error(f"Clear history error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to clear history: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_available_doctypes():
	"""
	Return list of available ERPNext doctypes with their required fields.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_available_doctypes
	Returns: List of doctypes with metadata
	"""
	try:
		# Common ERPNext doctypes
		doctypes = [
			{
				"name": "Customer",
				"label": "Customer",
				"module": "CRM",
				"required_fields": ["customer_name"]
			},
			{
				"name": "Supplier",
				"label": "Supplier",
				"module": "Buying",
				"required_fields": ["supplier_name"]
			},
			{
				"name": "Item",
				"label": "Item",
				"module": "Stock",
				"required_fields": ["item_code", "item_name", "item_group"]
			},
			{
				"name": "Sales Invoice",
				"label": "Sales Invoice",
				"module": "Accounts",
				"required_fields": ["customer", "items"]
			},
			{
				"name": "Purchase Invoice",
				"label": "Purchase Invoice",
				"module": "Accounts",
				"required_fields": ["supplier", "items"]
			},
			{
				"name": "Sales Order",
				"label": "Sales Order",
				"module": "Selling",
				"required_fields": ["customer", "items"]
			},
			{
				"name": "Purchase Order",
				"label": "Purchase Order",
				"module": "Buying",
				"required_fields": ["supplier", "items"]
			},
			{
				"name": "Quotation",
				"label": "Quotation",
				"module": "Selling",
				"required_fields": ["party_name", "items"]
			},
			{
				"name": "Lead",
				"label": "Lead",
				"module": "CRM",
				"required_fields": ["lead_name"]
			},
			{
				"name": "Employee",
				"label": "Employee",
				"module": "HR",
				"required_fields": ["first_name"]
			}
		]
		
		return {
			"status": "success",
			"doctypes": doctypes
		}
		
	except Exception as e:
		frappe.log_error(f"Get doctypes error: {str(e)}")
		return {
			"status": "error",
			"message": f"An error occurred: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def create_document():
	"""
	Create a new ERPNext document using doctype handlers.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.create_document
	Accepts:
		- doctype: DocType name
		- fields: Dictionary of field values
	Returns: Created document details or error
	"""
	try:
		doctype = frappe.form_dict.get("doctype")
		fields_json = frappe.form_dict.get("fields")
		
		if not doctype:
			return {
				"status": "error",
				"message": "DocType is required"
			}
		
		if not fields_json:
			return {
				"status": "error",
				"message": "Fields are required"
			}
		
		# Parse fields if string
		if isinstance(fields_json, str):
			fields = json.loads(fields_json)
		else:
			fields = fields_json
		
		# Get handler for this doctype
		from exim_backend.api.doctypes import get_handler
		handler = get_handler(doctype)
		
		if handler:
			# Use handler to create document
			return handler.create_document(fields)
		else:
			# Fallback to generic creation
			if not frappe.db.exists("DocType", doctype):
				return {
					"status": "error",
					"message": f"DocType '{doctype}' does not exist or handler not available"
				}
			
			doc = frappe.get_doc({
				"doctype": doctype,
				**fields
			})
			doc.insert(ignore_permissions=True)
			
			return {
				"status": "success",
				"message": f"{doctype} '{doc.name}' created successfully",
				"name": doc.name,
				"doctype": doctype
			}
		
	except frappe.exceptions.ValidationError as e:
		error_msg = str(e)
		frappe.logger().error(f"Validation error creating {doctype}: {error_msg}")
		return {
			"status": "error",
			"message": f"Validation error: {error_msg}"
		}
	except Exception as e:
		error_msg = str(e)
		frappe.logger().error(f"Error creating {doctype}: {error_msg}")
		frappe.log_error(title=f"Document Creation Error - {doctype}")
		return {
			"status": "error",
			"message": f"Failed to create {doctype}: {error_msg}"
		}


def create_customer_address(customer_name, fields):
	"""Create address for customer from provided fields."""
	address_fields = {}
	
	# Extract address fields
	address_mapping = {
		"address_line1": "address_line1",
		"address_line2": "address_line2",
		"city": "city",
		"state": "state",
		"country": "country",
		"pincode": "pincode"
	}
	
	for old_key, new_key in address_mapping.items():
		if old_key in fields:
			address_fields[new_key] = fields[old_key]
	
	# Only create address if at least one field is provided
	if not address_fields:
		return
	
	# Create address document
	address = frappe.get_doc({
		"doctype": "Address",
		**address_fields,
		"links": [{
			"link_doctype": "Customer",
			"link_name": customer_name
		}]
	})
	
	address.insert(ignore_permissions=True)
	frappe.logger().info(f"Created address {address.name} for customer {customer_name}")


def prepare_customer_data(fields):
	"""Prepare customer data with required fields."""
	# Set defaults for required fields
	if not fields.get("customer_type"):
		fields["customer_type"] = "Individual" if not fields.get("company") else "Company"
	
	if not fields.get("customer_group"):
		fields["customer_group"] = frappe.db.get_single_value("Selling Settings", "customer_group") or "Individual"
	
	if not fields.get("territory"):
		fields["territory"] = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
	
	# Set default currency if not provided
	if not fields.get("default_currency"):
		fields["default_currency"] = frappe.db.get_single_value("System Settings", "currency") or "USD"
	
	# Map common field names
	field_mapping = {
		"email": "email_id",
		"phone": "mobile_no",
		"mobile": "mobile_no",
		"contact": "customer_primary_contact",
		"primary_contact": "customer_primary_contact"
	}
	
	for old_key, new_key in field_mapping.items():
		if old_key in fields and new_key not in fields:
			fields[new_key] = fields.pop(old_key)
	
	# Remove address fields from customer data (they'll be handled separately)
	address_fields = ["address_line1", "address_line2", "city", "state", "country", "pincode"]
	customer_fields = {k: v for k, v in fields.items() if k not in address_fields}
	
	return customer_fields


def prepare_supplier_data(fields):
	"""Prepare supplier data with required fields."""
	if not fields.get("supplier_group"):
		fields["supplier_group"] = frappe.db.get_single_value("Buying Settings", "supplier_group") or "All Supplier Groups"
	
	if not fields.get("supplier_type"):
		fields["supplier_type"] = "Company"
	
	# Map common field names
	field_mapping = {
		"email": "email_id",
		"phone": "mobile_no",
		"mobile": "mobile_no"
	}
	
	for old_key, new_key in field_mapping.items():
		if old_key in fields and new_key not in fields:
			fields[new_key] = fields.pop(old_key)
	
	return fields


def prepare_item_data(fields):
	"""Prepare item data with required fields."""
	if not fields.get("item_group"):
		fields["item_group"] = frappe.db.get_single_value("Stock Settings", "item_group") or "All Item Groups"
	
	if not fields.get("stock_uom"):
		fields["stock_uom"] = frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos"
	
	# Set item code if not provided
	if not fields.get("item_code"):
		fields["item_code"] = fields.get("item_name", "").upper().replace(" ", "-")
	
	return fields


def prepare_lead_data(fields):
	"""Prepare lead data with required fields."""
	# Lead name is required
	if not fields.get("lead_name"):
		fields["lead_name"] = fields.get("first_name", "") + " " + fields.get("last_name", "")
	
	# Map common field names
	field_mapping = {
		"name": "lead_name",
		"customer_name": "lead_name",
		"email": "email_id",
		"phone": "mobile_no",
		"mobile": "mobile_no"
	}
	
	for old_key, new_key in field_mapping.items():
		if old_key in fields and new_key not in fields:
			fields[new_key] = fields.pop(old_key)
	
	return fields


@frappe.whitelist(allow_guest=True, methods=["POST"])
def search_customers():
	"""
	Search for customers based on various criteria.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.search_customers
	Accepts:
		- query: Search query (name, email, phone)
		- limit: Number of results (default: 10)
	Returns: List of matching customers
	"""
	try:
		query = frappe.form_dict.get("query", "").strip()
		limit = int(frappe.form_dict.get("limit", 10))
		
		if not query:
			return {
				"status": "error",
				"message": "Search query is required"
			}
		
		# Search customers by name, email, or mobile
		customers = frappe.db.sql("""
			SELECT 
				name,
				customer_name,
				customer_type,
				mobile_no,
				email_id,
				customer_primary_contact,
				territory,
				customer_group,
				default_currency,
				default_price_list,
				creation,
				modified
			FROM `tabCustomer`
			WHERE 
				customer_name LIKE %(search)s
				OR mobile_no LIKE %(search)s
				OR email_id LIKE %(search)s
				OR name LIKE %(search)s
			ORDER BY modified DESC
			LIMIT %(limit)s
		""", {
			"search": f"%{query}%",
			"limit": limit
		}, as_dict=True)
		
		return {
			"status": "success",
			"count": len(customers),
			"customers": customers
		}
		
	except Exception as e:
		frappe.logger().error(f"Customer search error: {str(e)}")
		return {
			"status": "error",
			"message": f"Search failed: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_doctype_fields():
	"""
	Get complete field information for a doctype including child tables.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_doctype_fields
	Accepts:
		- doctype: DocType name (default: Customer)
	Returns: Complete field structure with types, options, and child tables
	"""
	try:
		doctype = frappe.form_dict.get("doctype", "Customer")
		
		# Validate doctype exists
		if not frappe.db.exists("DocType", doctype):
			return {
				"status": "error",
				"message": f"DocType '{doctype}' does not exist"
			}
		
		# Get doctype meta
		meta = frappe.get_meta(doctype)
		
		# Extract field information
		fields_info = []
		child_tables = {}
		
		for field in meta.fields:
			field_data = {
				"fieldname": field.fieldname,
				"label": field.label,
				"fieldtype": field.fieldtype,
				"options": field.options if field.options else None,
				"reqd": field.reqd,
				"read_only": field.read_only,
				"hidden": field.hidden,
				"in_list_view": field.in_list_view,
				"in_standard_filter": field.in_standard_filter,
			}
			
			# If it's a Table field (child table), get its structure
			if field.fieldtype == "Table" and field.options:
				child_meta = frappe.get_meta(field.options)
				child_fields = []
				
				for child_field in child_meta.fields:
					child_fields.append({
						"fieldname": child_field.fieldname,
						"label": child_field.label,
						"fieldtype": child_field.fieldtype,
						"options": child_field.options if child_field.options else None
					})
				
				child_tables[field.fieldname] = {
					"label": field.label,
					"child_doctype": field.options,
					"fields": child_fields
				}
			
			fields_info.append(field_data)
		
		# Get standard fields that are always present
		standard_fields = [
			{"fieldname": "name", "label": "ID", "fieldtype": "Data", "searchable": True},
			{"fieldname": "owner", "label": "Created By", "fieldtype": "Link", "options": "User"},
			{"fieldname": "creation", "label": "Created On", "fieldtype": "Datetime"},
			{"fieldname": "modified", "label": "Last Modified", "fieldtype": "Datetime"},
			{"fieldname": "modified_by", "label": "Modified By", "fieldtype": "Link", "options": "User"}
		]
		
		return {
			"status": "success",
			"doctype": doctype,
			"fields": fields_info,
			"child_tables": child_tables,
			"standard_fields": standard_fields,
			"total_fields": len(fields_info)
		}
		
	except Exception as e:
		frappe.logger().error(f"Get doctype fields error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get doctype fields: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def dynamic_search():
	"""
	Generic dynamic search that uses doctype handlers.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.dynamic_search
	Accepts:
		- doctype: DocType name (required)
		- filters: JSON object with field:value pairs
		- limit: Number of results (default: 20)
		- order_by: Field to order by (default: modified desc)
	Returns: Documents matching the dynamic filters
	"""
	try:
		doctype = frappe.form_dict.get("doctype")
		filters_json = frappe.form_dict.get("filters")
		limit = int(frappe.form_dict.get("limit", 20))
		order_by = frappe.form_dict.get("order_by", "modified desc")
		
		if not doctype:
			return {
				"status": "error",
				"message": "DocType is required"
			}
		
		# Parse filters (allow empty filters for sorting-only queries)
		filters = {}
		if filters_json:
			if isinstance(filters_json, str):
				filters = json.loads(filters_json)
			else:
				filters = filters_json
		
		# Get handler for this doctype
		from exim_backend.api.doctypes import get_handler
		handler = get_handler(doctype)
		
		if handler:
			# Check for special aggregation queries for Sales Order
			if doctype == "Sales Order":
				# Handle customer group filter (requires join with Customer)
				if "customer_group" in filters:
					customer_group = filters.pop("customer_group")
					if hasattr(handler, 'get_orders_by_customer_group'):
						result = handler.get_orders_by_customer_group(customer_group)
						if "results" in result:
							result["sales_orders"] = result.pop("results")
						return result
				# Handle territory filter (requires join with Customer)
				if "territory" in filters:
					territory = filters.pop("territory")
					if hasattr(handler, 'get_orders_by_territory'):
						result = handler.get_orders_by_territory(territory)
						if "results" in result:
							result["sales_orders"] = result.pop("results")
						return result
			
			result = handler.dynamic_search(filters, limit, order_by)
			# Rename 'results' to doctype-specific name for backward compatibility
			if "results" in result:
				# Use plural form of doctype name (simple: add 's')
				doctype_key = doctype.lower() + "s"  # customers, items, etc.
				result[doctype_key] = result.pop("results")
			return result
		else:
			return {
				"status": "error",
				"message": f"Handler not available for doctype '{doctype}'"
			}
		
	except Exception as e:
		frappe.logger().error(f"Dynamic search error: {str(e)}")
		return {
			"status": "error",
			"message": f"Search failed: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def dynamic_customer_search():
	"""
	Legacy endpoint for backward compatibility.
	Routes to dynamic_search with doctype=Customer.
	"""
	doctype = frappe.form_dict.get("doctype", "Customer")
	frappe.form_dict["doctype"] = doctype
	return dynamic_search()


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def find_duplicates():
	"""
	Generic find duplicates using doctype handlers.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.find_duplicates
	Accepts:
		- doctype: DocType name (required)
	Returns: Duplicate documents
	"""
	try:
		doctype = frappe.form_dict.get("doctype")
		
		if not doctype:
			return {
				"status": "error",
				"message": "DocType is required"
			}
		
		# Get handler for this doctype
		from exim_backend.api.doctypes import get_handler
		handler = get_handler(doctype)
		
		if handler and hasattr(handler, 'find_duplicates'):
			return handler.find_duplicates()
		else:
			return {
				"status": "error",
				"message": f"Find duplicates not supported for doctype '{doctype}'"
			}
		
	except Exception as e:
		frappe.logger().error(f"Find duplicates error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to find duplicates: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def find_duplicate_customers():
	"""
	Legacy endpoint for backward compatibility.
	Routes to find_duplicates with doctype=Customer.
	"""
	frappe.form_dict["doctype"] = "Customer"
	return find_duplicates()


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def count_documents():
	"""
	Generic count documents using doctype handlers.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.count_documents
	Accepts:
		- doctype: DocType name (required)
		- filters: Optional filters (JSON)
	Returns: Document count
	"""
	try:
		doctype = frappe.form_dict.get("doctype")
		filters_json = frappe.form_dict.get("filters")
		
		if not doctype:
			return {
				"status": "error",
				"message": "DocType is required"
			}
		
		# Parse filters if provided
		filters = None
		if filters_json:
			if isinstance(filters_json, str):
				filters = json.loads(filters_json)
			else:
				filters = filters_json
		
		# Get handler for this doctype
		from exim_backend.api.doctypes import get_handler
		handler = get_handler(doctype)
		
		if handler:
			# Use handler's count method, or custom method if available
			if hasattr(handler, 'count_with_breakdown'):
				return handler.count_with_breakdown()
			else:
				return handler.count_documents(filters)
		else:
			# Fallback to generic count
			if filters:
				# Use dynamic_search to count
				frappe.form_dict["filters"] = filters_json
				frappe.form_dict["limit"] = 10000
				result = dynamic_search()
				if result.get("status") == "success":
					return {
						"status": "success",
						"total_count": result.get("count", 0)
					}
			else:
				total = frappe.db.count(doctype)
				return {
					"status": "success",
					"total_count": total
				}
		
	except Exception as e:
		frappe.logger().error(f"Count documents error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to count documents: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def count_customers():
	"""
	Legacy endpoint for backward compatibility.
	Routes to count_documents with doctype=Customer.
	"""
	frappe.form_dict["doctype"] = "Customer"
	return count_documents()


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_sales_person_count():
	"""
	Get total count of sales persons.
	Optionally filter by enabled status, is_group, etc.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_sales_person_count
	Accepts:
		- filters: Optional filters (JSON) - e.g., {"enabled": 1}
	Returns: Sales person count
	"""
	try:
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Person")
		
		if handler:
			filters_json = frappe.form_dict.get("filters")
			filters = None
			if filters_json:
				if isinstance(filters_json, str):
					filters = json.loads(filters_json)
				else:
					filters = filters_json
			
			return handler.get_sales_person_count(filters)
		else:
			return {
				"status": "error",
				"message": "Sales Person handler not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get sales person count error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get sales person count: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_sales_person_names():
	"""
	Get list of sales person names.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_sales_person_names
	Accepts:
		- filters: Optional filters (JSON) - e.g., {"enabled": 1}
		- limit: Optional limit on number of results
	Returns: List of sales person names with details
	"""
	try:
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Person")
		
		if handler:
			filters_json = frappe.form_dict.get("filters")
			limit = frappe.form_dict.get("limit")
			
			filters = None
			if filters_json:
				if isinstance(filters_json, str):
					filters = json.loads(filters_json)
				else:
					filters = filters_json
			
			if limit:
				limit = int(limit)
			
			return handler.get_sales_person_names(filters, limit)
		else:
			return {
				"status": "error",
				"message": "Sales Person handler not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get sales person names error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get sales person names: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_customers_by_order_count():
	"""
	Get customers with most orders, ordered by order count.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_customers_by_order_count
	Accepts:
		- limit: Number of results (default: 10)
		- order_by: Order by clause (default: order_count desc)
	Returns: Customers with order counts
	"""
	try:
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Order")
		
		if handler and hasattr(handler, 'get_customers_by_order_count'):
			limit = int(frappe.form_dict.get("limit", 10))
			order_by = frappe.form_dict.get("order_by", "order_count desc")
			return handler.get_customers_by_order_count(limit, order_by)
		else:
			return {
				"status": "error",
				"message": "Handler or method not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get customers by order count error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get customers by order count: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_customers_by_order_value():
	"""
	Get customers with highest order value, ordered by total value.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_customers_by_order_value
	Accepts:
		- limit: Number of results (default: 10)
		- order_by: Order by clause (default: total_value desc)
	Returns: Customers with order values
	"""
	try:
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Order")
		
		if handler and hasattr(handler, 'get_customers_by_order_value'):
			limit = int(frappe.form_dict.get("limit", 10))
			order_by = frappe.form_dict.get("order_by", "total_value desc")
			return handler.get_customers_by_order_value(limit, order_by)
		else:
			return {
				"status": "error",
				"message": "Handler or method not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get customers by order value error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get customers by order value: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_orders_by_customer_group():
	"""
	Get sales orders filtered by customer group.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_orders_by_customer_group
	Accepts:
		- customer_group: Customer group name (required)
	Returns: Sales orders for customers in the specified group
	"""
	try:
		customer_group = frappe.form_dict.get("customer_group")
		if not customer_group:
			return {
				"status": "error",
				"message": "Customer group is required"
			}
		
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Order")
		
		if handler and hasattr(handler, 'get_orders_by_customer_group'):
			result = handler.get_orders_by_customer_group(customer_group)
			# Rename 'results' to 'sales_orders' for consistency
			if "results" in result:
				result["sales_orders"] = result.pop("results")
			return result
		else:
			return {
				"status": "error",
				"message": "Handler or method not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get orders by customer group error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get orders by customer group: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_orders_by_territory():
	"""
	Get sales orders filtered by territory.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_orders_by_territory
	Accepts:
		- territory: Territory name (required)
	Returns: Sales orders for customers in the specified territory
	"""
	try:
		territory = frappe.form_dict.get("territory")
		if not territory:
			return {
				"status": "error",
				"message": "Territory is required"
			}
		
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Order")
		
		if handler and hasattr(handler, 'get_orders_by_territory'):
			result = handler.get_orders_by_territory(territory)
			# Rename 'results' to 'sales_orders' for consistency
			if "results" in result:
				result["sales_orders"] = result.pop("results")
			return result
		else:
			return {
				"status": "error",
				"message": "Handler or method not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get orders by territory error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get orders by territory: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_orders_by_item():
	"""
	Get sales orders containing a specific item.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_orders_by_item
	Accepts:
		- item_code: Item code (required)
	Returns: Sales orders containing the specified item
	"""
	try:
		item_code = frappe.form_dict.get("item_code")
		if not item_code:
			return {
				"status": "error",
				"message": "Item code is required"
			}
		
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Order")
		
		if handler and hasattr(handler, 'get_orders_by_item'):
			result = handler.get_orders_by_item(item_code)
			# Rename 'results' to 'sales_orders' for consistency
			if "results" in result:
				result["sales_orders"] = result.pop("results")
			return result
		else:
			return {
				"status": "error",
				"message": "Handler or method not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get orders by item error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get orders by item: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_orders_with_most_items():
	"""
	Get sales orders with most line items.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_orders_with_most_items
	Accepts:
		- limit: Number of results (default: 10)
		- order_by: Order by clause (default: item_count desc)
	Returns: Sales orders with item counts
	"""
	try:
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Order")
		
		if handler and hasattr(handler, 'get_orders_with_most_items'):
			limit = int(frappe.form_dict.get("limit", 10))
			order_by = frappe.form_dict.get("order_by", "item_count desc")
			result = handler.get_orders_with_most_items(limit, order_by)
			# Rename 'results' to 'sales_orders' for consistency
			if "results" in result:
				result["sales_orders"] = result.pop("results")
			return result
		else:
			return {
				"status": "error",
				"message": "Handler or method not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get orders with most items error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get orders with most items: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_orders_by_item_group():
	"""
	Get sales orders containing items from a specific item group.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_orders_by_item_group
	Accepts:
		- item_group: Item group name (required)
	Returns: Sales orders containing items from the specified group
	"""
	try:
		item_group = frappe.form_dict.get("item_group")
		if not item_group:
			return {
				"status": "error",
				"message": "Item group is required"
			}
		
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Order")
		
		if handler and hasattr(handler, 'get_orders_by_item_group'):
			result = handler.get_orders_by_item_group(item_group)
			# Rename 'results' to 'sales_orders' for consistency
			if "results" in result:
				result["sales_orders"] = result.pop("results")
			return result
		else:
			return {
				"status": "error",
				"message": "Handler or method not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get orders by item group error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get orders by item group: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_total_quantity_sold():
	"""
	Get total quantity sold for a specific item within a date range.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_total_quantity_sold
	Accepts:
		- item_code: Item code (required)
		- from_date: Start date (optional)
		- to_date: End date (optional)
	Returns: Total quantity and amount sold
	"""
	try:
		item_code = frappe.form_dict.get("item_code")
		if not item_code:
			return {
				"status": "error",
				"message": "Item code is required"
			}
		
		from_date = frappe.form_dict.get("from_date")
		to_date = frappe.form_dict.get("to_date")
		
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Order")
		
		if handler and hasattr(handler, 'get_total_quantity_sold'):
			return handler.get_total_quantity_sold(item_code, from_date, to_date)
		else:
			return {
				"status": "error",
				"message": "Handler or method not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get total quantity sold error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get total quantity sold: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def get_most_sold_items():
	"""
	Get most sold items aggregated by item_code.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_most_sold_items
	Accepts:
		- limit: Number of results (default: 10)
		- order_by: Order by clause (default: total_qty desc)
		- from_date: Start date (optional)
		- to_date: End date (optional)
	Returns: Most sold items with quantities and amounts
	"""
	try:
		from exim_backend.api.doctypes import get_handler
		handler = get_handler("Sales Order")
		
		if handler and hasattr(handler, 'get_most_sold_items'):
			limit = int(frappe.form_dict.get("limit", 10))
			order_by = frappe.form_dict.get("order_by", "total_qty desc")
			from_date = frappe.form_dict.get("from_date")
			to_date = frappe.form_dict.get("to_date")
			return handler.get_most_sold_items(limit, order_by, from_date, to_date)
		else:
			return {
				"status": "error",
				"message": "Handler or method not available"
			}
	except Exception as e:
		frappe.logger().error(f"Get most sold items error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get most sold items: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def get_document_details():
	"""
	Generic get document details using doctype handlers.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_document_details
	Accepts:
		- doctype: DocType name (required)
		- name: Document name/ID (required)
	Returns: Document details
	"""
	try:
		doctype = frappe.form_dict.get("doctype")
		name = frappe.form_dict.get("name", "").strip()
		
		if not doctype:
			return {
				"status": "error",
				"message": "DocType is required"
			}
		
		if not name:
			return {
				"status": "error",
				"message": "Document name is required"
			}
		
		# Get handler for this doctype
		from exim_backend.api.doctypes import get_handler
		handler = get_handler(doctype)
		
		if handler:
			result = handler.get_document_details(name)
			frappe.logger().info(f"Handler returned result for {doctype} '{name}': status={result.get('status')}, keys={list(result.keys())}")
			
			# Rename 'document' to doctype-specific name for backward compatibility
			if "document" in result:
				# Use lowercase doctype as key (customer, item, etc.)
				doctype_key = doctype.lower()
				result[doctype_key] = result.pop("document")
				frappe.logger().info(f"Renamed 'document' to '{doctype_key}'")
			
			# Log the final result structure
			frappe.logger().info(f"Final API response for {doctype} '{name}': {json.dumps({k: type(v).__name__ if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in result.items()}, indent=2)}")
			return result
		else:
			# Fallback to generic retrieval
			if not frappe.db.exists(doctype, name):
				return {
					"status": "error",
					"message": f"{doctype} '{name}' not found"
				}
			
			doc = frappe.get_doc(doctype, name)
			return {
				"status": "success",
				"document": doc.as_dict()
			}
		
	except Exception as e:
		frappe.logger().error(f"Get document details error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get details: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def get_customer_details():
	"""
	Legacy endpoint for backward compatibility.
	Routes to get_document_details with doctype=Customer.
	"""
	customer_name = frappe.form_dict.get("customer_name", "").strip()
	frappe.form_dict["doctype"] = "Customer"
	frappe.form_dict["name"] = customer_name
	return get_document_details()


@frappe.whitelist(allow_guest=True, methods=["POST"])
def analyze_image_with_ai():
	"""
	Extract text from image and analyze it with Gemini AI.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.analyze_image_with_ai
	Accepts: image (file)
	Returns: Extracted text and AI analysis
	"""
	try:
		image_file = frappe.request.files.get("image")
		if not image_file:
			return {
				"status": "error",
				"message": "Please upload an image file"
			}
		
		# Save temporarily and extract text
		temp_path = frappe.get_site_path("public", "temp")
		os.makedirs(temp_path, exist_ok=True)
		filepath = os.path.join(temp_path, image_file.filename)
		image_file.save(filepath)
		
		# Extract text using OCR
		from pytesseract import image_to_string
		extracted_text = image_to_string(Image.open(filepath))
		
		# Cleanup
		os.remove(filepath)
		
		if not extracted_text.strip():
			return {
				"status": "success",
				"extracted_text": "",
				"message": "No text found in image"
			}
		
		# Analyze with AI
		config = get_ai_config()
		analysis_prompt = f"""Analyze this text extracted from an image and identify:
1. What type of document it appears to be
2. Which ERPNext DocType would be appropriate (Customer, Item, Sales Invoice, etc.)
3. What fields can be extracted and their values

Extracted text:
{extracted_text}

Provide a structured analysis."""
		
		analysis = call_ai_api(analysis_prompt, config)
		
		return {
			"status": "success",
			"extracted_text": extracted_text,
			"analysis": analysis
		}
		
	except Exception as e:
		frappe.log_error(f"Image analysis error: {str(e)}")
		return {
			"status": "error",
			"message": f"An error occurred: {str(e)}"
		}

