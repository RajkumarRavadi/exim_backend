"""
PDF Sales Order Handler.
Handles the complete workflow of creating sales orders from PDF documents.

Workflow:
1. Receive PDF file
2. Extract content (text, tables, images)
3. Use AI to structure and format data
4. Present data to user for confirmation
5. Create sales order using SalesOrderHandler
"""

import frappe
import json
import os
from datetime import datetime
from exim_backend.api.doctypes.sales_order_handler import SalesOrderHandler
from exim_backend.api.pdf_processor import PDFProcessor
from exim_backend.api.ai_extractor import AISalesOrderExtractor


class PDFSalesOrderHandler:
	"""Handler for creating sales orders from PDF documents."""
	
	def __init__(self):
		self.pdf_processor = PDFProcessor()
		self.ai_extractor = AISalesOrderExtractor()
		self.sales_order_handler = SalesOrderHandler()
		self.session_cache = {}
		self.skip_validation = frappe.conf.get("pdf_sales_order_skip_validation", True)
		self.default_customer_name = frappe.conf.get("pdf_sales_order_default_customer")
		self.default_company_name = frappe.conf.get("pdf_sales_order_default_company")
		self.default_item_code = frappe.conf.get("pdf_sales_order_default_item")
	
	def process_pdf(self, file_path_or_url, session_id=None):
		"""
		Main entry point for processing a PDF and extracting sales order data.
		
		Args:
			file_path_or_url: Path to PDF file or Frappe File URL
			session_id: Optional session ID for tracking the extraction state
		
		Returns:
			dict: Contains status, extracted data, and session information
		"""
		try:
			# Generate session ID if not provided
			if not session_id:
				session_id = self._generate_session_id()
			
			frappe.logger().info(f"Processing PDF for session: {session_id}")
			
			# Step 1: Extract content from PDF
			extraction_result = self.pdf_processor.extract_from_pdf(file_path_or_url)
			
			if extraction_result.get("status") != "success":
				return {
					"status": "error",
					"message": f"Failed to extract PDF content: {extraction_result.get('message')}",
					"session_id": session_id
				}
			
			pdf_content = extraction_result.get("content", {})
			
			# Step 2: Use AI to structure the data into sales order format
			frappe.logger().info(f"Using AI to extract sales order data from PDF content")
			ai_result = self.ai_extractor.extract_sales_order_data(pdf_content)
			
			if ai_result.get("status") != "success":
				return {
					"status": "error",
					"message": f"Failed to extract sales order data: {ai_result.get('message')}",
					"session_id": session_id
				}
			
			extracted_data = ai_result.get("data", {})
			
			# Step 3: Validate and enrich the extracted data
			validated_data = self._validate_and_enrich_data(extracted_data)
			
			# Step 4: Store in session cache for confirmation
			self.session_cache[session_id] = {
				"extracted_data": validated_data,
				"pdf_content": pdf_content,
				"timestamp": datetime.now().isoformat(),
				"status": "pending_confirmation"
			}
			
			# Save to cache (Frappe Cache)
			self._save_to_cache(session_id, self.session_cache[session_id])
			
			return {
				"status": "success",
				"message": "Sales order data extracted successfully. Please review and confirm.",
				"session_id": session_id,
				"extracted_data": validated_data,
				"validation_warnings": validated_data.get("_warnings", []),
				"requires_confirmation": True
			}
			
		except Exception as e:
			frappe.logger().error(f"Error processing PDF: {str(e)}")
			frappe.logger().exception("Full exception traceback:")
			return {
				"status": "error",
				"message": f"An error occurred while processing the PDF: {str(e)}",
				"session_id": session_id
			}
	
	def confirm_and_create_order(self, session_id, confirmed_data=None, auto_create=False):
		"""
		Confirm the extracted data and create the sales order.
		
		Args:
			session_id: Session ID from the extraction process
			confirmed_data: Optional modified data from user (if user made corrections)
			auto_create: If True, skip confirmation and create directly
		
		Returns:
			dict: Result of sales order creation
		"""
		try:
			# Retrieve session data
			session_data = self._get_from_cache(session_id)
			
			if not session_data:
				return {
					"status": "error",
					"message": f"Session '{session_id}' not found or expired. Please re-upload the PDF."
				}
			
			if session_data.get("status") == "completed":
				return {
					"status": "error",
					"message": "This session has already been completed. Please start a new session."
				}
			
			# Use confirmed data if provided, otherwise use extracted data
			sales_order_data = confirmed_data if confirmed_data else session_data.get("extracted_data", {})
			
			# Remove internal fields (validation warnings, etc.)
			sales_order_data = self._clean_data_for_creation(sales_order_data)
			
			frappe.logger().info(f"Creating sales order from session: {session_id}")
			
			# Step 5: Create the sales order using existing handler
			creation_result = self.sales_order_handler.create_document(sales_order_data)
			
			if creation_result.get("status") == "success":
				# Update session status
				session_data["status"] = "completed"
				session_data["sales_order_name"] = creation_result.get("name")
				session_data["completion_timestamp"] = datetime.now().isoformat()
				self._save_to_cache(session_id, session_data)
				
				return {
					"status": "success",
					"message": creation_result.get("message"),
					"sales_order_name": creation_result.get("name"),
					"sales_order_doctype": creation_result.get("doctype"),
					"customer": creation_result.get("customer"),
					"customer_name": creation_result.get("customer_name"),
					"grand_total": creation_result.get("grand_total"),
					"session_id": session_id
				}
			else:
				return {
					"status": "error",
					"message": creation_result.get("message"),
					"session_id": session_id
				}
			
		except Exception as e:
			frappe.logger().error(f"Error creating sales order from PDF: {str(e)}")
			frappe.logger().exception("Full exception traceback:")
			return {
				"status": "error",
				"message": f"Failed to create sales order: {str(e)}",
				"session_id": session_id
			}
	
	def update_extracted_data(self, session_id, updated_fields):
		"""
		Update specific fields in the extracted data before confirmation.
		
		Args:
			session_id: Session ID
			updated_fields: Dictionary of fields to update
		
		Returns:
			dict: Updated extracted data
		"""
		try:
			session_data = self._get_from_cache(session_id)
			
			if not session_data:
				return {
					"status": "error",
					"message": f"Session '{session_id}' not found or expired."
				}
			
			# Update the fields
			extracted_data = session_data.get("extracted_data", {})
			extracted_data.update(updated_fields)
			
			# Re-validate
			validated_data = self._validate_and_enrich_data(extracted_data)
			
			# Update session cache
			session_data["extracted_data"] = validated_data
			session_data["last_updated"] = datetime.now().isoformat()
			self._save_to_cache(session_id, session_data)
			
			return {
				"status": "success",
				"message": "Data updated successfully",
				"extracted_data": validated_data,
				"validation_warnings": validated_data.get("_warnings", [])
			}
			
		except Exception as e:
			frappe.logger().error(f"Error updating extracted data: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to update data: {str(e)}"
			}
	
	def get_session_data(self, session_id):
		"""
		Retrieve session data for review.
		
		Args:
			session_id: Session ID
		
		Returns:
			dict: Session data
		"""
		try:
			session_data = self._get_from_cache(session_id)
			
			if not session_data:
				return {
					"status": "error",
					"message": f"Session '{session_id}' not found or expired."
				}
			
			return {
				"status": "success",
				"session_id": session_id,
				"extracted_data": session_data.get("extracted_data"),
				"session_status": session_data.get("status"),
				"timestamp": session_data.get("timestamp"),
				"last_updated": session_data.get("last_updated")
			}
			
		except Exception as e:
			frappe.logger().error(f"Error retrieving session data: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to retrieve session data: {str(e)}"
			}
	
	def cancel_session(self, session_id):
		"""
		Cancel a session and clear its data.
		
		Args:
			session_id: Session ID
		
		Returns:
			dict: Cancellation status
		"""
		try:
			session_data = self._get_from_cache(session_id)
			
			if not session_data:
				return {
					"status": "error",
					"message": f"Session '{session_id}' not found."
				}
			
			# Mark as cancelled
			session_data["status"] = "cancelled"
			session_data["cancellation_timestamp"] = datetime.now().isoformat()
			self._save_to_cache(session_id, session_data)
			
			return {
				"status": "success",
				"message": "Session cancelled successfully",
				"session_id": session_id
			}
			
		except Exception as e:
			frappe.logger().error(f"Error cancelling session: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to cancel session: {str(e)}"
			}
	
	# Private helper methods
	
	def _validate_and_enrich_data(self, extracted_data):
		"""
		Validate and enrich the extracted sales order data.
		Checks for required fields, validates customer/items exist, etc.
		"""
		if getattr(self, "skip_validation", False):
			data = extracted_data.copy()
			data["_warnings"] = data.get("_warnings", [])
			
			# Ensure customer is present
			if not data.get("customer"):
				default_customer = self._get_default_customer()
				if default_customer:
					data["customer"] = default_customer.get("name")
					data["customer_name"] = default_customer.get("customer_name")
			
			# Ensure company is present
			company_name = data.get("company")
			if not company_name or not frappe.db.exists("Company", company_name):
				default_company = self._get_default_company()
				if default_company:
					data["company"] = default_company
			
			# Ensure at least one item exists
			items = data.get("items") or []
			if not items:
				default_item = self._get_default_item()
				if default_item:
					data["items"] = [{
						"item_code": default_item.get("item_code"),
						"item_name": default_item.get("item_name"),
						"qty": 1,
						"rate": default_item.get("standard_rate") or 0,
						"uom": default_item.get("stock_uom")
					}]
			
			return data

		warnings = []
		validated_data = extracted_data.copy()
		
		# Validate customer
		customer = extracted_data.get("customer")
		if customer:
			if not frappe.db.exists("Customer", customer):
				warnings.append(f"Customer '{customer}' not found in system. Please create or select existing customer.")
				validated_data["_customer_exists"] = False
			else:
				validated_data["_customer_exists"] = True
		else:
			warnings.append("Customer information not found in PDF. Please provide customer name.")
		
		# Validate and enrich items
		items = extracted_data.get("items", [])
		if not items or len(items) == 0:
			warnings.append("No items found in PDF. Please add items manually.")
		else:
			validated_items = []
			for idx, item in enumerate(items):
				item_code = item.get("item_code")
				if item_code:
					if frappe.db.exists("Item", item_code):
						# Enrich with item data
						item_doc = frappe.get_doc("Item", item_code)
						item["_item_exists"] = True
						item["item_name"] = item.get("item_name") or item_doc.item_name
						item["uom"] = item.get("uom") or item_doc.stock_uom
					else:
						warnings.append(f"Item '{item_code}' (line {idx + 1}) not found in system.")
						item["_item_exists"] = False
				else:
					warnings.append(f"Item code missing for line {idx + 1}")
					item["_item_exists"] = False
				
				validated_items.append(item)
			
			validated_data["items"] = validated_items
		
		# Validate company
		company = extracted_data.get("company")
		if company:
			if not frappe.db.exists("Company", company):
				warnings.append(f"Company '{company}' not found. Using default company.")
				default_company = frappe.db.get_single_value("Global Defaults", "default_company")
				if default_company:
					validated_data["company"] = default_company
		else:
			default_company = frappe.db.get_single_value("Global Defaults", "default_company")
			if default_company:
				validated_data["company"] = default_company
		
		# Add warnings to data
		validated_data["_warnings"] = warnings
		
		return validated_data
	
	def _clean_data_for_creation(self, data):
		"""Remove internal validation fields before creating sales order."""
		cleaned_data = {}
		for key, value in data.items():
			if not key.startswith("_"):
				if key == "items" and isinstance(value, list):
					# Clean items too
					cleaned_items = []
					for item in value:
						cleaned_item = {k: v for k, v in item.items() if not k.startswith("_")}
						cleaned_items.append(cleaned_item)
					cleaned_data[key] = cleaned_items
				else:
					cleaned_data[key] = value
		
		return cleaned_data
	def _get_default_customer(self):
		"""Get default customer details for fallback."""
		try:
			if self.default_customer_name:
				customer_name = frappe.db.exists("Customer", self.default_customer_name)
				if customer_name:
					doc = frappe.get_doc("Customer", customer_name)
					return {"name": doc.name, "customer_name": doc.customer_name}
			
			customer_doc = frappe.get_all("Customer", fields=["name", "customer_name"], limit=1)
			if customer_doc:
				return customer_doc[0]
		except Exception as e:
			frappe.logger().error(f"Default customer fetch failed: {str(e)}")
		return None

	def _get_default_item(self):
		"""Get default item details for fallback."""
		try:
			if self.default_item_code:
				item_name = frappe.db.exists("Item", self.default_item_code)
				if item_name:
					doc = frappe.get_doc("Item", item_name)
					return {
						"item_code": doc.name,
						"item_name": doc.item_name,
						"stock_uom": doc.stock_uom,
						"standard_rate": getattr(doc, "standard_rate", 0)
					}
			
			item_doc = frappe.get_all("Item", fields=["name as item_code", "item_name", "stock_uom", "standard_rate"], limit=1)
			if item_doc:
				return item_doc[0]
		except Exception as e:
			frappe.logger().error(f"Default item fetch failed: {str(e)}")
		return None

	def _get_default_company(self):
		"""Get default company to use when extracted company is invalid."""
		try:
			if self.default_company_name and frappe.db.exists("Company", self.default_company_name):
				return self.default_company_name
			
			default_company = frappe.db.get_single_value("Global Defaults", "default_company")
			if default_company and frappe.db.exists("Company", default_company):
				return default_company
			
			company_doc = frappe.get_all("Company", fields=["name"], limit=1)
			if company_doc:
				return company_doc[0]["name"]
		except Exception as e:
			frappe.logger().error(f"Default company fetch failed: {str(e)}")
		return None
	
	def _generate_session_id(self):
		"""Generate a unique session ID."""
		import uuid
		return f"pdf_so_{uuid.uuid4().hex[:12]}"
	
	def _save_to_cache(self, session_id, data):
		"""Save session data to Frappe cache."""
		try:
			cache_key = f"pdf_sales_order:{session_id}"
			# Store for 24 hours (86400 seconds)
			frappe.cache().set_value(cache_key, json.dumps(data), expires_in_sec=86400)
		except Exception as e:
			frappe.logger().error(f"Error saving to cache: {str(e)}")
	
	def _get_from_cache(self, session_id):
		"""Retrieve session data from Frappe cache."""
		try:
			cache_key = f"pdf_sales_order:{session_id}"
			cached_data = frappe.cache().get_value(cache_key)
			if cached_data:
				return json.loads(cached_data)
			# Fallback to in-memory cache
			return self.session_cache.get(session_id)
		except Exception as e:
			frappe.logger().error(f"Error retrieving from cache: {str(e)}")
			return None


# Convenience functions for API endpoints

@frappe.whitelist()
def process_pdf_file(file_url, session_id=None):
	"""
	API endpoint to process a PDF file and extract sales order data.
	
	Args:
		file_url: Frappe File URL or file path
		session_id: Optional session ID
	
	Returns:
		dict: Extraction result
	"""
	handler = PDFSalesOrderHandler()
	return handler.process_pdf(file_url, session_id)


@frappe.whitelist()
def confirm_and_create(session_id, confirmed_data=None):
	"""
	API endpoint to confirm extracted data and create sales order.
	
	Args:
		session_id: Session ID from extraction
		confirmed_data: Optional JSON string of modified data
	
	Returns:
		dict: Creation result
	"""
	handler = PDFSalesOrderHandler()
	
	# Parse confirmed_data if it's a string
	if confirmed_data and isinstance(confirmed_data, str):
		try:
			confirmed_data = json.loads(confirmed_data)
		except json.JSONDecodeError:
			return {
				"status": "error",
				"message": "Invalid JSON format for confirmed_data"
			}
	
	return handler.confirm_and_create_order(session_id, confirmed_data)


@frappe.whitelist()
def update_session_data(session_id, updated_fields):
	"""
	API endpoint to update extracted data fields.
	
	Args:
		session_id: Session ID
		updated_fields: JSON string of fields to update
	
	Returns:
		dict: Update result
	"""
	handler = PDFSalesOrderHandler()
	
	# Parse updated_fields if it's a string
	if updated_fields and isinstance(updated_fields, str):
		try:
			updated_fields = json.loads(updated_fields)
		except json.JSONDecodeError:
			return {
				"status": "error",
				"message": "Invalid JSON format for updated_fields"
			}
	
	return handler.update_extracted_data(session_id, updated_fields)


@frappe.whitelist()
def get_session_info(session_id):
	"""
	API endpoint to retrieve session data.
	
	Args:
		session_id: Session ID
	
	Returns:
		dict: Session data
	"""
	handler = PDFSalesOrderHandler()
	return handler.get_session_data(session_id)


@frappe.whitelist()
def cancel_pdf_session(session_id):
	"""
	API endpoint to cancel a session.
	
	Args:
		session_id: Session ID
	
	Returns:
		dict: Cancellation result
	"""
	handler = PDFSalesOrderHandler()
	return handler.cancel_session(session_id)

