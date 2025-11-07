import frappe
import json
import os
import requests
from PIL import Image

# Import the existing image extraction function
from exim_backend.api.image_reader import extract_text_from_image


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


def call_ai_api(prompt, config):
	"""Call AI API (supports both OpenRouter and direct Gemini)."""
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
			"messages": [
				{
					"role": "user",
					"content": prompt
				}
			]
		}
		
		response = requests.post(
			"https://openrouter.ai/api/v1/chat/completions",
			headers=headers,
			json=data,
			timeout=30
		)
		
		if response.status_code != 200:
			frappe.throw(f"OpenRouter API error: {response.status_code} - {response.text}")
		
		result = response.json()
		return result["choices"][0]["message"]["content"]
	else:
		# Use direct Google Gemini API
		import google.generativeai as genai
		genai.configure(api_key=config["api_key"])
		model = genai.GenerativeModel(config["model"])
		response = model.generate_content(prompt)
		return response.text


@frappe.whitelist(allow_guest=True, methods=["POST"])
def process_chat():
	"""
	Main chat endpoint that processes user messages and optional images.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.process_chat
	Accepts: 
		- message (text): User's message
		- image (file, optional): Image to extract text from
	Returns: AI response with suggested actions
	"""
	try:
		message = frappe.form_dict.get("message", "").strip()
		image_file = frappe.request.files.get("image")
		
		frappe.logger().info(f"Chat request received - Message: {message[:50] if message else 'None'}, Has Image: {bool(image_file)}")
		
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
		
		# Get AI configuration and process message
		config = get_ai_config()
		
		# Fetch Customer doctype field metadata for intelligent processing
		try:
			fields_response = get_doctype_fields()
			if fields_response.get("status") == "success":
				customer_fields = fields_response.get("fields", [])
				# Build a concise field reference for AI
				field_reference = "\n".join([
					f"- {f['fieldname']} ({f['fieldtype']}){' [required]' if f.get('reqd') else ''}"
					for f in customer_fields
					if not f.get('hidden') and f['fieldtype'] not in ['Section Break', 'Column Break', 'Tab Break']
				])
			else:
				field_reference = "Fields metadata not available"
		except Exception as e:
			frappe.logger().error(f"Failed to fetch field metadata: {str(e)}")
			field_reference = "Fields metadata not available"
		
		# Create system prompt for the AI
		system_prompt = f"""You are an intelligent AI assistant for an ERPNext system. Your role is to:
1. UNDERSTAND user intent deeply - think about what they REALLY want
2. Provide CONVERSATIONAL and HELPFUL responses
3. Execute actions ONLY when database queries are needed
4. Answer DIRECTLY from context when possible

=== CUSTOMER DOCTYPE FIELDS ===
{field_reference}

=== WHEN TO USE EACH ACTION ===
A) DIRECT ANSWER - When you can answer from previous context or general knowledge
   - Example: "What's Rajkumar's phone?" → Just say the number if you just fetched it
   - Example: "When was customer created?" → Explain creation date if you have the details

B) DYNAMIC SEARCH - When you need to query database with filters
   - Example: "Find customers from India" → filters: {{"territory": "India"}}
   - Example: "Show customers using USD" → filters: {{"default_currency": "USD"}}
   - Example: "Find Rajkumar" → filters: {{"customer_name": {{"$like": "%Rajkumar%"}}}}
   
C) GET DETAILS - When user asks for complete details of a specific customer
   - Example: "Show full details of Rajkumar" → get_customer_details
   
D) FIND DUPLICATES - When user asks about duplicate/same names
   - Example: "Are there customers with same name?" → find_duplicates
   - Example: "Show duplicate customers" → find_duplicates
   
E) COUNT - When user asks for statistics
   - Example: "How many customers?" → count_customers

F) CREATE - When user wants to create a new customer
   - Example: "Create customer John" → create_document

=== RESPONSE FORMAT for DIRECT ANSWER (NO action needed) ===
Just respond naturally in plain text. NO JSON needed.

Examples:
- User: "What's Rajkumar's phone number?" → Response: "Rajkumar's phone number is 919381964965 📱"
- User: "Are there customers with same name?" → Response: "Yes! I can see 'Sarah Johnson' appears twice in the results above."

=== RESPONSE FORMAT for CREATE ===
{{
  "suggested_action": {{
    "action": "create_document",
    "doctype": "Customer",
    "fields": {{
      "customer_name": "John Doe",
      "mobile_no": "1234567890",
      "email_id": "john@example.com",
      "default_currency": "USD",
      "default_price_list": "Standard Selling",
      "payment_terms": "Net 30",
      "customer_primary_contact": "John Doe"
    }},
    "confidence": 0.95
  }}
}}

=== RESPONSE FORMAT for DYNAMIC SEARCH (NEW - MOST INTELLIGENT) ===
{{
  "suggested_action": {{
    "action": "dynamic_search",
    "filters": {{
      "territory": "United States",
      "default_currency": "USD"
    }},
    "execute_immediately": true,
    "confidence": 0.95
  }}
}}

Example queries:
- "Show me customers from United States" → filters: {{"territory": "United States"}}
- "Find customers using USD currency" → filters: {{"default_currency": "USD"}}  
- "List customers in India with INR" → filters: {{"territory": "India", "default_currency": "INR"}}
- "Find Rajkumar" → filters: {{"customer_name": {{"$like": "%Rajkumar%"}}}}
- "Customers with email containing gmail" → filters: {{"email_id": {{"$like": "%gmail%"}}}}

CRITICAL: For "don't have", "missing", "not set", "without" queries:
- "Customers without primary contact" → filters: {{"customer_primary_contact": {{"$is_null": true}}}}
- "How many customers don't have a primary contact?" → filters: {{"customer_primary_contact": {{"$is_null": true}}}}
- "Customers missing email" → filters: {{"email_id": {{"$is_null": true}}}}
- "Customers with primary contact" → filters: {{"customer_primary_contact": {{"$is_not_null": true}}}}

OPERATORS AVAILABLE:
- {{"$like": "%text%"}} - Partial text match
- {{"$is_null": true}} - Field is NULL, empty, or "Not Set"
- {{"$is_not_null": true}} - Field has a value
- {{"$gte": value}} - Greater than or equal
- {{"$lte": value}} - Less than or equal
- {{"$in": [val1, val2]}} - Value in list

=== RESPONSE FORMAT for GET DETAILS (specific customer by exact name) ===
{{
  "suggested_action": {{
    "action": "get_customer_details",
    "customer_name": "Rajkumar",
    "execute_immediately": true,
    "confidence": 0.95
  }}
}}

=== RESPONSE FORMAT for FIND DUPLICATES ===
{{
  "suggested_action": {{
    "action": "find_duplicates",
    "execute_immediately": true,
    "confidence": 0.95
  }}
}}

=== RESPONSE FORMAT for COUNT ===
{{
  "suggested_action": {{
    "action": "count_customers",
    "execute_immediately": true,
    "confidence": 0.95
  }}
}}

=== QUERY TYPE RECOGNITION ===
✅ DIRECT ANSWER (just text, no JSON):
- "What's X's phone?" → Answer directly if you know it
- "When was X created?" → Answer from context if available
- "Give me just the phone number" → Extract and provide specific info

✅ DYNAMIC SEARCH (with JSON action):
- "Find customers from X" → filters: {{"territory": "X"}}
- "Show customers using X currency" → filters: {{"default_currency": "X"}}
- "Search for X" → filters: {{"customer_name": {{"$like": "%X%"}}}}
- "Customers without/don't have/missing X" → filters: {{"field_name": {{"$is_null": true}}}}
- "Customers with X" (when X is a field) → filters: {{"field_name": {{"$is_not_null": true}}}}
- "How many customers don't have X?" → filters: {{"field_name": {{"$is_null": true}}}}

✅ GET DETAILS (with JSON action):
- "Show full details of X" → get_customer_details

✅ FIND DUPLICATES (with JSON action):
- "Are there customers with same name?" → find_duplicates
- "Show duplicate customers" → find_duplicates
- "Find customers with exact same names" → find_duplicates

✅ COUNT (with JSON action):
- "How many customers?" (general count) → count_customers
- "How many customers don't have X?" (filtered count) → dynamic_search with $is_null filter
- "How many customers from X?" (filtered count) → dynamic_search with filter

✅ CREATE (with JSON action):
- "Create customer X" → create_document

=== INTELLIGENCE RULES ===
1. 🧠 THINK FIRST: Understand the user's question deeply
   - "How many customers don't have X?" = Count customers where X field is NULL/empty
   - "Customers without X" = Filter where X field is NULL/empty
   - "Customers missing X" = Filter where X field is NULL/empty
   - "Customers with X" = Filter where X field has a value (NOT NULL)

2. 🔍 Need fresh data? → Use appropriate action with execute_immediately: true
3. 📊 For specific info requests (phone, email, date) → Extract and answer directly if available
4. 🎯 For filtering/searching → Use dynamic_search with smart filters
5. ⚠️ For creating records → Use create_document with execute_immediately: false
6. 🔢 Build filters intelligently based on field names from the field reference:
   - Partial match: {{"fieldname": {{"$like": "%text%"}}}}
   - Exact match: {{"fieldname": "exact_value"}}
   - NULL/empty check: {{"fieldname": {{"$is_null": true}}}}
   - Has value check: {{"fieldname": {{"$is_not_null": true}}}}
   - Multiple criteria: {{"field1": "value1", "field2": {{"$is_null": true}}}}

CRITICAL RULES:
- 🎯 For DIRECT ANSWERS: Respond with plain conversational text (NO JSON)
- 🔧 For ACTIONS: Return ONLY the JSON object as plain text (no markdown, no backticks)
- ⚡ Set execute_immediately: true for queries, false for creates
- 🧠 Be contextually aware - remember previous conversation

EXAMPLE RESPONSES:

📝 DIRECT ANSWERS (just text):
Q: "What's Rajkumar's phone number?"
A: Rajkumar's phone number is **919381964965** 📱

Q: "Give me just Rajkumar's phone number"
A: Rajkumar's phone number is **919381964965** 📱

Q: "When did Rajkumar get created?"
A: I'll need to fetch those details. Let me get the creation date for you.
THEN: {{"suggested_action": {{"action": "get_customer_details", "customer_name": "Rajkumar", "execute_immediately": true, "confidence": 0.95}}}}

🔍 ACTIONS (JSON):
Q: "Find customer Rajkumar"
A: {{"suggested_action": {{"action": "dynamic_search", "filters": {{"customer_name": {{"$like": "%Rajkumar%"}}}}, "execute_immediately": true, "confidence": 0.95}}}}

Q: "Show customers from India"
A: {{"suggested_action": {{"action": "dynamic_search", "filters": {{"territory": "India"}}, "execute_immediately": true, "confidence": 0.95}}}}

Q: "How many customers don't have a primary contact?"
A: {{"suggested_action": {{"action": "dynamic_search", "filters": {{"customer_primary_contact": {{"$is_null": true}}}}, "execute_immediately": true, "confidence": 0.95}}}}

Q: "Customers without email"
A: {{"suggested_action": {{"action": "dynamic_search", "filters": {{"email_id": {{"$is_null": true}}}}, "execute_immediately": true, "confidence": 0.95}}}}

Q: "Are there customers with same name?"
A: {{"suggested_action": {{"action": "find_duplicates", "execute_immediately": true, "confidence": 0.95}}}}

Q: "How many customers"
A: {{"suggested_action": {{"action": "count_customers", "execute_immediately": true, "confidence": 0.95}}}}

Q: "Create customer John"
A: {{"suggested_action": {{"action": "create_document", "doctype": "Customer", "fields": {{"customer_name": "John"}}, "execute_immediately": false, "confidence": 0.95}}}}

User message: """ + message
		
		# Generate response using AI
		ai_response = call_ai_api(system_prompt, config)
		
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
		
		# Log for debugging
		frappe.logger().info(f"AI Response length: {len(ai_response)}")
		frappe.logger().info(f"Suggested action found: {suggested_action is not None}")
		if suggested_action:
			frappe.logger().info(f"Suggested action details: {json.dumps(suggested_action)}")
		
		return {
			"status": "success",
			"message": ai_response,
			"suggested_action": suggested_action,
			"extracted_text": extracted_text if image_file else None
		}
		
	except Exception as e:
		frappe.log_error(f"Chat processing error: {str(e)}")
		return {
			"status": "error",
			"message": f"An error occurred: {str(e)}"
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
	Create a new ERPNext document based on AI suggestion.
	
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
		
		# Validate doctype exists
		if not frappe.db.exists("DocType", doctype):
			return {
				"status": "error",
				"message": f"DocType '{doctype}' does not exist"
			}
		
		# Handle specific doctypes with required fields
		if doctype == "Customer":
			fields = prepare_customer_data(fields)
		elif doctype == "Supplier":
			fields = prepare_supplier_data(fields)
		elif doctype == "Item":
			fields = prepare_item_data(fields)
		elif doctype == "Lead":
			fields = prepare_lead_data(fields)
		
		# Create new document
		doc = frappe.get_doc({
			"doctype": doctype,
			**fields
		})
		
		# Insert document
		doc.insert(ignore_permissions=True)
		
		# If customer, create address if address fields provided
		if doctype == "Customer" and any(key.startswith('address_') for key in fields.keys()):
			try:
				create_customer_address(doc.name, fields)
			except Exception as e:
				frappe.logger().error(f"Failed to create address: {str(e)}")
		
		frappe.db.commit()
		
		return {
			"status": "success",
			"message": f"{doctype} '{doc.name}' created successfully!",
			"document": {
				"name": doc.name,
				"doctype": doctype,
				"link": f"/app/{doctype.lower().replace(' ', '-')}/{doc.name}"
			}
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
def dynamic_customer_search():
	"""
	Dynamic customer search that builds queries based on AI-generated filters.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.dynamic_customer_search
	Accepts:
		- filters: JSON object with field:value pairs
		- limit: Number of results (default: 10)
		- order_by: Field to order by (default: modified desc)
	Returns: Customers matching the dynamic filters
	"""
	try:
		filters_json = frappe.form_dict.get("filters")
		limit = int(frappe.form_dict.get("limit", 10))
		order_by = frappe.form_dict.get("order_by", "modified desc")
		
		if not filters_json:
			return {
				"status": "error",
				"message": "Filters are required"
			}
		
		# Parse filters
		if isinstance(filters_json, str):
			filters = json.loads(filters_json)
		else:
			filters = filters_json
		
		frappe.logger().info(f"Dynamic search filters: {filters}")
		
		# Build WHERE clause dynamically
		conditions = []
		values = {}
		
		for field, value in filters.items():
			# Handle NULL/empty checks
			if value is None or value == "":
				# If value is explicitly None or empty string, skip (unless it's a NULL check)
				continue
			
			# Handle different filter types
			if isinstance(value, dict):
				# Support operators: {"$like": "%text%"}, {"$is_null": true}, {"$is_not_null": true}, etc.
				for operator, op_value in value.items():
					if operator == "$like":
						conditions.append(f"`{field}` LIKE %({field})s")
						values[field] = op_value
					elif operator == "$is_null":
						# Field is NULL or empty
						conditions.append(f"(`{field}` IS NULL OR `{field}` = '' OR `{field}` = 'Not Set')")
					elif operator == "$is_not_null":
						# Field is NOT NULL and not empty
						conditions.append(f"(`{field}` IS NOT NULL AND `{field}` != '' AND `{field}` != 'Not Set')")
					elif operator == "$gte":
						conditions.append(f"`{field}` >= %({field})s")
						values[field] = op_value
					elif operator == "$lte":
						conditions.append(f"`{field}` <= %({field})s")
						values[field] = op_value
					elif operator == "$in":
						placeholders = ", ".join([f"%({field}_{i})s" for i in range(len(op_value))])
						conditions.append(f"`{field}` IN ({placeholders})")
						for i, v in enumerate(op_value):
							values[f"{field}_{i}"] = v
			else:
				# Simple equality
				conditions.append(f"`{field}` = %({field})s")
				values[field] = value
		
		where_clause = " AND ".join(conditions) if conditions else "1=1"
		
		# Build and execute query
		query = f"""
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
				payment_terms,
				creation,
				modified
			FROM `tabCustomer`
			WHERE {where_clause}
			ORDER BY {order_by}
			LIMIT %(limit)s
		"""
		
		values["limit"] = limit
		
		frappe.logger().info(f"Executing query: {query}")
		frappe.logger().info(f"With values: {values}")
		
		customers = frappe.db.sql(query, values, as_dict=True)
		
		return {
			"status": "success",
			"count": len(customers),
			"customers": customers,
			"filters_applied": filters
		}
		
	except Exception as e:
		frappe.logger().error(f"Dynamic search error: {str(e)}")
		return {
			"status": "error",
			"message": f"Search failed: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def find_duplicate_customers():
	"""
	Find customers with duplicate names.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.find_duplicate_customers
	Returns: Customers that have duplicate names
	"""
	try:
		# Find duplicate customer names
		query = """
			SELECT 
				customer_name,
				COUNT(*) as count,
				GROUP_CONCAT(name SEPARATOR ', ') as customer_ids
			FROM `tabCustomer`
			GROUP BY customer_name
			HAVING COUNT(*) > 1
			ORDER BY count DESC
		"""
		
		duplicates = frappe.db.sql(query, as_dict=True)
		
		# Get detailed info for each duplicate
		duplicate_details = []
		for dup in duplicates:
			customer_ids = dup['customer_ids'].split(', ')
			customers = []
			
			for cust_id in customer_ids:
				customer = frappe.db.get_value(
					"Customer",
					cust_id,
					["name", "customer_name", "mobile_no", "email_id", "territory", "customer_group"],
					as_dict=True
				)
				if customer:
					customers.append(customer)
			
			duplicate_details.append({
				"customer_name": dup['customer_name'],
				"count": dup['count'],
				"customers": customers
			})
		
		return {
			"status": "success",
			"duplicate_count": len(duplicates),
			"duplicates": duplicate_details
		}
		
	except Exception as e:
		frappe.logger().error(f"Find duplicates error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to find duplicates: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def count_customers():
	"""
	Count total customers or by specific criteria.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.count_customers
	Returns: Customer count
	"""
	try:
		# Get total count
		total_count = frappe.db.count("Customer")
		
		# Get count by territory
		territory_counts = frappe.db.sql("""
			SELECT territory, COUNT(*) as count
			FROM `tabCustomer`
			WHERE territory IS NOT NULL AND territory != ''
			GROUP BY territory
			ORDER BY count DESC
			LIMIT 5
		""", as_dict=True)
		
		# Get count by customer group
		group_counts = frappe.db.sql("""
			SELECT customer_group, COUNT(*) as count
			FROM `tabCustomer`
			WHERE customer_group IS NOT NULL AND customer_group != ''
			GROUP BY customer_group
			ORDER BY count DESC
			LIMIT 5
		""", as_dict=True)
		
		return {
			"status": "success",
			"total_count": total_count,
			"by_territory": territory_counts,
			"by_group": group_counts
		}
		
	except Exception as e:
		frappe.logger().error(f"Count customers error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to count customers: {str(e)}"
		}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def get_customer_details():
	"""
	Get detailed information about a specific customer.
	
	API Endpoint: /api/method/exim_backend.api.ai_chat.get_customer_details
	Accepts:
		- customer_name: Customer ID or name
	Returns: Customer details
	"""
	try:
		customer_name = frappe.form_dict.get("customer_name", "").strip()
		
		if not customer_name:
			return {
				"status": "error",
				"message": "Customer name is required"
			}
		
		# Get customer document
		if not frappe.db.exists("Customer", customer_name):
			# Try to find by customer_name field
			customer_id = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
			if customer_id:
				customer_name = customer_id
			else:
				return {
					"status": "error",
					"message": f"Customer '{customer_name}' not found"
				}
		
		customer = frappe.get_doc("Customer", customer_name)
		
		# Get primary address if exists
		address = None
		address_links = frappe.get_all(
			"Dynamic Link",
			filters={
				"link_doctype": "Customer",
				"link_name": customer.name,
				"parenttype": "Address"
			},
			fields=["parent"],
			limit=1
		)
		
		if address_links:
			address_doc = frappe.get_doc("Address", address_links[0].parent)
			address = {
				"address_line1": address_doc.address_line1,
				"address_line2": address_doc.address_line2,
				"city": address_doc.city,
				"state": address_doc.state,
				"country": address_doc.country,
				"pincode": address_doc.pincode
			}
		
		# Get primary contact if exists
		contact = None
		contact_links = frappe.get_all(
			"Dynamic Link",
			filters={
				"link_doctype": "Customer",
				"link_name": customer.name,
				"parenttype": "Contact"
			},
			fields=["parent"],
			limit=1
		)
		
		if contact_links:
			contact_doc = frappe.get_doc("Contact", contact_links[0].parent)
			contact = {
				"name": contact_doc.name,
				"first_name": contact_doc.first_name,
				"last_name": contact_doc.last_name,
				"email_id": contact_doc.email_id,
				"mobile_no": contact_doc.mobile_no,
				"phone": contact_doc.phone
			}
		
		# Prepare response
		customer_data = {
			"name": customer.name,
			"customer_name": customer.customer_name,
			"customer_type": customer.customer_type,
			"customer_group": customer.customer_group,
			"territory": customer.territory,
			"mobile_no": customer.mobile_no,
			"email_id": customer.email_id,
			"customer_primary_contact": customer.customer_primary_contact,
			"default_currency": customer.default_currency,
			"default_price_list": customer.default_price_list,
			"payment_terms": customer.payment_terms,
			"sales_team": [{"sales_person": st.sales_person, "allocated_percentage": st.allocated_percentage} for st in customer.sales_team] if customer.sales_team else [],
			"address": address,
			"contact": contact,
			"creation": str(customer.creation),
			"modified": str(customer.modified)
		}
		
		return {
			"status": "success",
			"customer": customer_data
		}
		
	except Exception as e:
		frappe.logger().error(f"Get customer details error: {str(e)}")
		return {
			"status": "error",
			"message": f"Failed to get customer details: {str(e)}"
		}


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

