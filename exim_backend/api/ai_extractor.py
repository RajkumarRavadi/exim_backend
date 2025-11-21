"""
AI Sales Order Extractor.
Uses AI models to extract and structure sales order data from PDF content.
"""

import copy
import frappe
import json
import re
from typing import Dict, List, Any


class AISalesOrderExtractor:
	"""Uses AI to extract structured sales order data from PDF content."""
	
	def __init__(self):
		self.extraction_prompt_template = self._get_extraction_prompt()
	
	def extract_sales_order_data(self, pdf_content):
		"""
		Extract sales order data from PDF content using AI.
		
		Args:
			pdf_content: Dict containing text, tables, images from PDF
		
		Returns:
			dict: Structured sales order data
		"""
		try:
			frappe.logger().info("Starting AI extraction of sales order data")
			
			# Prepare content for AI
			formatted_content = self._format_content_for_ai(pdf_content)
			
			# Get AI extraction
			extraction_result = self._call_ai_for_extraction(formatted_content)
			
			if extraction_result.get("status") != "success":
				return {
					"status": "error",
					"message": extraction_result.get("message", "AI extraction failed")
				}
			
			# Parse and validate the extracted data
			extracted_data = extraction_result.get("data", {})
			structured_data = self._structure_sales_order_data(extracted_data)
			structured_data = self._merge_with_fallback_data(structured_data, formatted_content)
			
			return {
				"status": "success",
				"data": structured_data
			}
			
		except Exception as e:
			frappe.logger().error(f"Error in AI extraction: {str(e)}")
			frappe.logger().exception("Full exception traceback:")
			return {
				"status": "error",
				"message": f"AI extraction failed: {str(e)}"
			}
	
	def _format_content_for_ai(self, pdf_content):
		"""
		Format PDF content into a structure suitable for AI processing.
		"""
		formatted = {
			"text": "",
			"tables": [],
			"has_images": False
		}
		
		# Extract text content
		text_data = pdf_content.get("text", {})
		formatted["text"] = text_data.get("full_text", "")
		formatted["pages"] = text_data.get("pages", [])
		
		# Extract tables
		tables = pdf_content.get("tables", [])
		formatted["tables"] = tables
		formatted["table_count"] = len(tables)
		formatted["table_previews"] = self._build_table_previews(tables)
		
		# Check for images
		images = pdf_content.get("images", [])
		formatted["has_images"] = len(images) > 0
		formatted["image_count"] = len(images)
		
		formatted["key_snippets"] = self._extract_key_snippets(formatted["pages"])
		
		return formatted
	
	def _call_ai_for_extraction(self, formatted_content):
		"""
		Call AI service to extract sales order data.
		This integrates with your existing AI system.
		"""
		try:
			# Build the extraction prompt
			prompt = self._build_extraction_prompt(formatted_content)
			
			# Option 1: Use OpenAI API directly
			extraction_data = self._extract_using_openai(prompt, formatted_content)
			
			# Option 2: Use your existing AI chat system (if available)
			# extraction_data = self._extract_using_chat_system(prompt, formatted_content)
			
			return {
				"status": "success",
				"data": extraction_data
			}
			
		except Exception as e:
			frappe.logger().error(f"Error calling AI for extraction: {str(e)}")
			return {
				"status": "error",
				"message": f"AI call failed: {str(e)}"
			}
	
	def _extract_using_openai(self, prompt, formatted_content):
		"""
		Extract data using AI API (OpenRouter or Gemini).
		Uses the same API configuration as your existing ai_chat.py.
		"""
		try:
			# Get AI API key from Frappe config (same as ai_chat.py)
			api_key = frappe.conf.get("openrouter_api_key") or frappe.conf.get("gemini_api_key")
			
			if not api_key:
				frappe.logger().warning("AI API key not found, using fallback extraction")
				return self._fallback_extraction(formatted_content)
			
			# Check if using OpenRouter or direct Gemini
			use_openrouter = frappe.conf.get("openrouter_api_key") is not None
			
			if use_openrouter:
				# Use OpenRouter API (same as ai_chat.py)
				result = self._extract_using_openrouter(api_key, prompt)
				if result:
					return result
				else:
					frappe.logger().warning("OpenRouter extraction failed, using fallback")
					return self._fallback_extraction(formatted_content)
			else:
				# Use direct Gemini API
				result = self._extract_using_gemini(api_key, prompt, formatted_content)
				if result:
					return result
				else:
					frappe.logger().warning("Gemini extraction failed, using fallback")
					return self._fallback_extraction(formatted_content)
			
		except Exception as e:
			frappe.logger().error(f"Error using AI extraction: {str(e)}")
			# Fallback to rule-based extraction
			return self._fallback_extraction(formatted_content)
	
	def _extract_using_openrouter(self, api_key, prompt):
		"""
		Extract using OpenRouter API (compatible with your existing setup).
		"""
		try:
			import requests
			
			# Get model from config or use default
			model = frappe.conf.get("ai_model") or "google/gemini-2.0-flash-exp:free"
			
			# Prepare messages
			messages = [
				{
					"role": "system",
					"content": "You are a sales order data extraction expert. Extract structured sales order information from the provided content and return ONLY valid JSON."
				},
				{
					"role": "user",
					"content": prompt
				}
			]
			
			# Call OpenRouter API
			headers = {
				"Authorization": f"Bearer {api_key}",
				"Content-Type": "application/json",
				"HTTP-Referer": "https://erp.local",  # Optional
				"X-Title": "ERPNext PDF Extractor"    # Optional
			}
			
			data = {
				"model": model,
				"messages": messages,
				"temperature": 0.1
			}
			
			response = requests.post(
				"https://openrouter.ai/api/v1/chat/completions",
				headers=headers,
				json=data,
				timeout=30
			)
			
			if response.status_code == 200:
				result = response.json()
				content = result["choices"][0]["message"]["content"]
				
				# Clean up the response (remove markdown formatting if present)
				content = content.strip()
				if content.startswith("```json"):
					content = content[7:]
				if content.startswith("```"):
					content = content[3:]
				if content.endswith("```"):
					content = content[:-3]
				content = content.strip()
				
				# Parse JSON
				extracted_data = json.loads(content)
				
				frappe.logger().info(f"Successfully extracted data using OpenRouter ({model})")
				return extracted_data
			else:
				frappe.logger().error(f"OpenRouter API error: {response.status_code} - {response.text}")
				return None
			
		except Exception as e:
			frappe.logger().error(f"Error using OpenRouter extraction: {str(e)}")
			return None
	
	def _extract_using_gemini(self, api_key, prompt, formatted_content):
		"""
		Extract using direct Gemini API.
		"""
		try:
			import google.generativeai as genai
			
			# Configure Gemini
			genai.configure(api_key=api_key)
			
			# Get model
			model_name = frappe.conf.get("ai_model") or "gemini-1.5-flash"
			model = genai.GenerativeModel(model_name)
			
			# Generate response
			response = model.generate_content(prompt)
			content = response.text.strip()
			
			# Clean up the response (remove markdown formatting if present)
			if content.startswith("```json"):
				content = content[7:]
			if content.startswith("```"):
				content = content[3:]
			if content.endswith("```"):
				content = content[:-3]
			content = content.strip()
			
			# Parse JSON
			extracted_data = json.loads(content)
			
			frappe.logger().info(f"Successfully extracted data using Gemini ({model_name})")
			return extracted_data
			
		except Exception as e:
			frappe.logger().error(f"Error using Gemini extraction: {str(e)}")
			return None
	
	def _fallback_extraction(self, formatted_content):
		"""
		Rule-based extraction as fallback when AI is not available.
		Uses regex and heuristics to extract sales order data.
		"""
		frappe.logger().info("Using fallback rule-based extraction")
		
		text = formatted_content.get("text", "")
		tables = formatted_content.get("tables", [])
		
		extracted_data = {
			"customer": None,
			"customer_name": None,
			"transaction_date": None,
			"delivery_date": None,
			"items": [],
			"company": None,
			"po_no": None,
			"po_date": None
		}
		
		# Extract customer information
		customer_match = re.search(r'(?:Customer|Client|Bill To|Sold To)[:\s]+([^\n]+)', text, re.IGNORECASE)
		if customer_match:
			extracted_data["customer_name"] = customer_match.group(1).strip()
		
		# Extract dates
		date_pattern = r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b'
		dates = re.findall(date_pattern, text)
		if dates:
			extracted_data["transaction_date"] = dates[0]
			if len(dates) > 1:
				extracted_data["delivery_date"] = dates[1]
		
		# Extract PO number
		po_match = re.search(r'(?:PO|Purchase Order)[#:\s]+([A-Z0-9\-]+)', text, re.IGNORECASE)
		if po_match:
			extracted_data["po_no"] = po_match.group(1).strip()
		
		# Extract items from tables
		if tables:
			items = self._extract_items_from_tables(tables)
			extracted_data["items"] = items
		else:
			# Try to extract items from text
			items = self._extract_items_from_text(text)
			extracted_data["items"] = items
		
		return extracted_data
	
	def _extract_items_from_tables(self, tables):
		"""Extract item information from PDF tables."""
		items = []
		
		for table in tables:
			headers = table.get("headers", [])
			rows = table.get("rows", [])
			
			if not headers or not rows:
				continue
			
			# Find column indices
			item_col = self._find_column_index(headers, ["item", "product", "description", "part"])
			qty_col = self._find_column_index(headers, ["qty", "quantity", "qnty"])
			rate_col = self._find_column_index(headers, ["rate", "price", "unit price", "amount"])
			
			# Extract items
			for row in rows:
				if not row or len(row) == 0:
					continue
				
				item_data = {}
				
				# Extract item code/name
				if item_col is not None and item_col < len(row):
					item_text = row[item_col]
					if item_text:
						item_data["item_code"] = item_text.strip()
						item_data["item_name"] = item_text.strip()
				
				# Extract quantity
				if qty_col is not None and qty_col < len(row):
					qty_text = row[qty_col]
					if qty_text:
						try:
							# Extract number from string
							qty_match = re.search(r'(\d+(?:\.\d+)?)', str(qty_text))
							if qty_match:
								item_data["qty"] = float(qty_match.group(1))
						except:
							pass
				
				# Extract rate
				if rate_col is not None and rate_col < len(row):
					rate_text = row[rate_col]
					if rate_text:
						try:
							# Extract number from string (remove currency symbols)
							rate_match = re.search(r'(\d+(?:,\d{3})*(?:\.\d+)?)', str(rate_text))
							if rate_match:
								rate_str = rate_match.group(1).replace(',', '')
								item_data["rate"] = float(rate_str)
						except:
							pass
				
				# Only add item if it has required fields
				if item_data.get("item_code") and item_data.get("qty"):
					items.append(item_data)
		
		return items
	
	def _extract_items_from_text(self, text):
		"""Extract item information from plain text (fallback)."""
		items = []
		
		# This is a basic implementation - can be enhanced based on your PDF formats
		# Look for patterns like: "Item: XYZ, Qty: 10, Rate: 100"
		
		item_pattern = r'(?:Item|Product)[:\s]+([^\n,]+)(?:.*?)(?:Qty|Quantity)[:\s]+(\d+(?:\.\d+)?)(?:.*?)(?:Rate|Price)[:\s]+(\d+(?:\.\d+)?)'
		matches = re.findall(item_pattern, text, re.IGNORECASE)
		
		for match in matches:
			items.append({
				"item_code": match[0].strip(),
				"item_name": match[0].strip(),
				"qty": float(match[1]),
				"rate": float(match[2])
			})
		
		return items
	
	def _find_column_index(self, headers, possible_names):
		"""Find column index by matching possible header names."""
		for idx, header in enumerate(headers):
			if not header:
				continue
			header_lower = str(header).lower().strip()
			for name in possible_names:
				if name.lower() in header_lower:
					return idx
		return None
	
	def _build_extraction_prompt(self, formatted_content):
		"""Build the AI extraction prompt."""
		text = formatted_content.get("text", "")
		tables = formatted_content.get("tables", [])
		
		prompt = f"""
Extract sales order information from the following PDF content and return it as a JSON object.

**PDF Content:**

{text[:3000]}  # Limit to first 3000 chars to avoid token limits

"""
		
		if tables:
			prompt += f"\n**Tables Found:** {len(tables)} table(s)\n"
			if formatted_content.get("table_previews"):
				for table_preview in formatted_content["table_previews"][:3]:
					prompt += f"\nTable (Page {table_preview.get('page')}):\n"
					prompt += f"Headers: {table_preview.get('headers')}\n"
					prompt += f"Sample Rows: {table_preview.get('rows')}\n"

		if formatted_content.get("key_snippets"):
			prompt += "\n**Key Information Snippets:**\n"
			for snippet in formatted_content["key_snippets"][:20]:
				prompt += f"- {snippet}\n"
		
		prompt += """

**Required JSON Format:**
{
  "customer": "customer_id_or_name",
  "customer_name": "customer display name",
  "transaction_date": "YYYY-MM-DD",
  "delivery_date": "YYYY-MM-DD",
  "po_no": "purchase order number",
  "po_date": "YYYY-MM-DD",
  "company": "company name",
  "items": [
    {
      "item_code": "item code or name",
      "item_name": "item description",
      "qty": 10,
      "rate": 100.00,
      "uom": "unit of measure"
    }
  ]
}

**Instructions:**
1. Extract customer information (name, ID if available)
2. Extract all dates in YYYY-MM-DD format
3. Extract each line item with: item code/name, quantity, rate/price
4. If UOM (unit of measure) is mentioned, include it
5. Extract PO number and date if available
6. Return ONLY valid JSON, no markdown formatting
7. If a field is not found, use null

Please extract and return the JSON:
"""
		
		return prompt
	
	def _get_extraction_prompt(self):
		"""Get the extraction prompt template."""
		return """
You are a sales order data extraction specialist. Your task is to extract structured sales order information from PDF content.

Extract the following information:
- Customer name/ID
- Order date (transaction date)
- Delivery date
- Purchase order number and date (if available)
- Company name
- Line items with: item code, description, quantity, rate, UOM

Return the data as a well-structured JSON object.
"""
	
	def _structure_sales_order_data(self, extracted_data):
		"""
		Structure and validate the extracted data into Frappe Sales Order format.
		"""
		structured = {
			"doctype": "Sales Order",
			"customer": extracted_data.get("customer") or extracted_data.get("customer_name"),
			"transaction_date": self._normalize_date(extracted_data.get("transaction_date")),
			"delivery_date": self._normalize_date(extracted_data.get("delivery_date")),
			"po_no": extracted_data.get("po_no"),
			"po_date": self._normalize_date(extracted_data.get("po_date")),
			"company": extracted_data.get("company"),
			"items": []
		}
		
		# Structure items
		items = extracted_data.get("items", [])
		for item in items:
			structured_item = {
				"item_code": item.get("item_code"),
				"item_name": item.get("item_name"),
				"qty": item.get("qty", 1),
				"rate": item.get("rate", 0),
				"uom": item.get("uom")
			}
			structured["items"].append(structured_item)
		
		return structured

	def _merge_with_fallback_data(self, structured_data, formatted_content):
		"""
		Merge AI extracted data with fallback extraction to fill missing fields.
		"""
		if not structured_data:
			return structured_data
		
		fallback_raw = self._fallback_extraction(formatted_content)
		if not fallback_raw:
			return structured_data
		
		fallback_structured = self._structure_sales_order_data(fallback_raw)
		merged_data = copy.deepcopy(structured_data)
		
		def is_missing(value):
			if value is None:
				return True
			if isinstance(value, str) and not value.strip():
				return True
			if isinstance(value, list) and len(value) == 0:
				return True
			return False
		
		for field in ["customer", "transaction_date", "delivery_date", "po_no", "po_date", "company"]:
			if is_missing(merged_data.get(field)) and fallback_structured.get(field):
				merged_data[field] = fallback_structured.get(field)
		
		fallback_items = fallback_structured.get("items", [])
		current_items = merged_data.get("items", [])
		
		if is_missing(current_items) and fallback_items:
			merged_data["items"] = fallback_items
		elif current_items and fallback_items:
			merged_items = []
			for idx, item in enumerate(current_items):
				fallback_item = fallback_items[idx] if idx < len(fallback_items) else {}
				merged_item = item.copy()
				for field in ["item_code", "item_name", "qty", "rate", "uom"]:
					if is_missing(merged_item.get(field)) and fallback_item.get(field):
						merged_item[field] = fallback_item.get(field)
				merged_items.append(merged_item)
			
			# Append extra fallback items if AI missed them
			if len(fallback_items) > len(merged_items):
				merged_items.extend(fallback_items[len(merged_items):])
			
			merged_data["items"] = merged_items
		
		return merged_data

	def _build_table_previews(self, tables):
		"""Build normalized table previews for the AI prompt."""
		previews = []
		for table in tables[:5]:
			headers = table.get("headers") or []
			normalized_headers = [self._normalize_header(header) for header in headers if header]
			rows = table.get("rows") or []
			preview_rows = rows[:3]
			previews.append({
				"page": table.get("page"),
				"headers": normalized_headers,
				"rows": preview_rows
			})
		return previews

	def _normalize_header(self, header):
		if not header:
			return ""
		header_text = str(header).strip()
		header_text = re.sub(r'\s+', ' ', header_text)
		return header_text

	def _extract_key_snippets(self, pages):
		"""Extract important snippets (customer, PO, dates, totals) to guide the AI."""
		if not pages:
			return []
		
		keywords = {
			"Customer": ["customer", "client", "bill to", "sold to", "ship to"],
			"PO": ["purchase order", "po#", "po no", "order no", "quote no"],
			"Dates": ["date", "delivery", "ship date", "due date"],
			"Totals": ["total", "subtotal", "amount", "balance"]
		}
		
		snippets = []
		for page in pages:
			page_text = page.get("text") or ""
			if not page_text:
				continue
			
			lines = [line.strip() for line in page_text.splitlines() if line.strip()]
			for line in lines:
				lower_line = line.lower()
				for label, terms in keywords.items():
					if any(term in lower_line for term in terms):
						snippets.append(f"[{label} | Page {page.get('page_number')}] {line}")
						break
			
			if len(snippets) >= 40:
				break
		
		return snippets
	
	def _normalize_date(self, date_str):
		"""
		Normalize date string to YYYY-MM-DD format.
		"""
		if not date_str:
			return None
		
		try:
			from dateutil import parser
			parsed_date = parser.parse(str(date_str))
			return parsed_date.strftime("%Y-%m-%d")
		except:
			# Try common formats manually
			import re
			
			# Try DD-MM-YYYY or DD/MM/YYYY
			match = re.match(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
			if match:
				day, month, year = match.groups()
				return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
			
			# Try MM-DD-YYYY or MM/DD/YYYY
			match = re.match(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
			if match:
				month, day, year = match.groups()
				return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
			
			# Try YYYY-MM-DD (already normalized)
			match = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
			if match:
				year, month, day = match.groups()
				return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
			
			return None
		
		return None

