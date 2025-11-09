"""
PDF Sales Order Chat Integration.
Integrates PDF sales order processing with the AI chat interface.

This module provides functions to handle PDF-based sales order creation
through the chat interface, including user interactions and confirmations.
"""

import frappe
import json
import re
from exim_backend.api.doctypes.pdf_sales_order_handler import PDFSalesOrderHandler


class PDFChatIntegration:
	"""Integration layer between PDF sales order handler and chat interface."""
	
	def __init__(self):
		self.handler = PDFSalesOrderHandler()
		self.context_key_prefix = "pdf_sales_order_context"
	
	def handle_pdf_upload(self, file_url, conversation_id, user_message=""):
		"""
		Handle PDF upload through chat interface.
		
		Args:
			file_url: URL of uploaded PDF file
			conversation_id: Chat conversation ID
			user_message: Optional user message accompanying the upload
		
		Returns:
			dict: Response for chat interface
		"""
		try:
			frappe.logger().info(f"PDF upload received for conversation: {conversation_id}")
			
			# Process the PDF
			result = self.handler.process_pdf(file_url, session_id=conversation_id)
			
			if result.get("status") == "success":
				# Store context for this conversation
				self._save_conversation_context(conversation_id, {
					"session_id": result.get("session_id"),
					"status": "awaiting_confirmation",
					"extracted_data": result.get("extracted_data"),
					"file_url": file_url
				})
				
				# Format response for user
				response_text = self._format_extraction_response(result)
				
				return {
					"status": "success",
					"message": response_text,
					"requires_action": True,
					"action_type": "confirmation",
					"data": result.get("extracted_data"),
					"session_id": result.get("session_id")
				}
			else:
				return {
					"status": "error",
					"message": f"❌ **Failed to process PDF:** {result.get('message')}\n\nPlease ensure the PDF contains sales order information and try again.",
					"requires_action": False
				}
			
		except Exception as e:
			frappe.logger().error(f"Error handling PDF upload: {str(e)}")
			return {
				"status": "error",
				"message": f"❌ An error occurred while processing your PDF: {str(e)}",
				"requires_action": False
			}
	
	def handle_user_response(self, conversation_id, user_message):
		"""
		Handle user response to PDF extraction (confirm, modify, or cancel).
		
		Args:
			conversation_id: Chat conversation ID
			user_message: User's response message
		
		Returns:
			dict: Response for chat interface
		"""
		try:
			# Get conversation context
			context = self._get_conversation_context(conversation_id)
			
			if not context:
				return {
					"status": "error",
					"message": "❌ No active PDF session found. Please upload a PDF first.",
					"requires_action": False
				}
			
			session_id = context.get("session_id")
			
			# Parse user intent
			intent = self._parse_user_intent(user_message)
			
			if intent["action"] == "confirm":
				return self._handle_confirmation(session_id, conversation_id, context)
			
			elif intent["action"] == "cancel":
				return self._handle_cancellation(session_id, conversation_id)
			
			elif intent["action"] == "modify":
				return self._handle_modification(session_id, conversation_id, intent["modifications"])
			
			elif intent["action"] == "show_data":
				return self._handle_show_data(context)
			
			else:
				return {
					"status": "info",
					"message": self._get_help_message(),
					"requires_action": True
				}
			
		except Exception as e:
			frappe.logger().error(f"Error handling user response: {str(e)}")
			return {
				"status": "error",
				"message": f"❌ An error occurred: {str(e)}",
				"requires_action": False
			}
	
	def _parse_user_intent(self, user_message):
		"""
		Parse user message to determine intent and extract modifications.
		
		Returns:
			dict: {"action": str, "modifications": dict}
		"""
		message_lower = user_message.lower().strip()
		
		# Check for confirmation
		if any(keyword in message_lower for keyword in ["confirm", "yes", "create", "proceed", "ok", "correct"]):
			return {"action": "confirm", "modifications": None}
		
		# Check for cancellation
		if any(keyword in message_lower for keyword in ["cancel", "no", "stop", "abort"]):
			return {"action": "cancel", "modifications": None}
		
		# Check for show data
		if any(keyword in message_lower for keyword in ["show", "display", "view", "what", "data"]):
			return {"action": "show_data", "modifications": None}
		
		# Check for modifications
		modifications = {}
		
		# Pattern: "change customer to CUST-001"
		customer_match = re.search(r'(?:change|update|modify|set)\s+customer\s+(?:to|as)?\s*[:\s]+([^\n,]+)', message_lower)
		if customer_match:
			modifications["customer"] = customer_match.group(1).strip()
		
		# Pattern: "change date to 2024-01-15"
		date_match = re.search(r'(?:change|update|modify|set)\s+(?:order\s+)?date\s+(?:to|as)?\s*[:\s]+(\d{4}-\d{2}-\d{2})', message_lower)
		if date_match:
			modifications["transaction_date"] = date_match.group(1).strip()
		
		# Pattern: "change delivery date to 2024-02-01"
		delivery_match = re.search(r'(?:change|update|modify|set)\s+delivery\s+date\s+(?:to|as)?\s*[:\s]+(\d{4}-\d{2}-\d{2})', message_lower)
		if delivery_match:
			modifications["delivery_date"] = delivery_match.group(1).strip()
		
		# Pattern: "change item 1 quantity to 20"
		item_qty_match = re.search(r'(?:change|update|modify|set)\s+item\s+(\d+)\s+(?:quantity|qty)\s+(?:to|as)?\s*[:\s]+(\d+(?:\.\d+)?)', message_lower)
		if item_qty_match:
			modifications["_item_modify"] = {
				"index": int(item_qty_match.group(1)) - 1,  # Convert to 0-indexed
				"field": "qty",
				"value": float(item_qty_match.group(2))
			}
		
		if modifications:
			return {"action": "modify", "modifications": modifications}
		
		return {"action": "unknown", "modifications": None}
	
	def _handle_confirmation(self, session_id, conversation_id, context):
		"""Handle user confirmation and create sales order."""
		result = self.handler.confirm_and_create_order(session_id)
		
		if result.get("status") == "success":
			# Clear context
			self._clear_conversation_context(conversation_id)
			
			response = "✅ **Sales Order Created Successfully!**\n\n"
			response += f"📋 **Order ID:** {result.get('sales_order_name')}\n"
			response += f"👤 **Customer:** {result.get('customer_name')}\n"
			response += f"💰 **Total Amount:** {result.get('grand_total')}\n"
			response += f"\nYou can view the order by searching for '{result.get('sales_order_name')}' or ask me to show its details."
			
			return {
				"status": "success",
				"message": response,
				"requires_action": False,
				"sales_order_name": result.get("sales_order_name"),
				"completed": True
			}
		else:
			return {
				"status": "error",
				"message": f"❌ **Failed to create sales order:**\n\n{result.get('message')}\n\nPlease review the data and try again, or type 'cancel' to abort.",
				"requires_action": True
			}
	
	def _handle_cancellation(self, session_id, conversation_id):
		"""Handle user cancellation."""
		self.handler.cancel_session(session_id)
		self._clear_conversation_context(conversation_id)
		
		return {
			"status": "success",
			"message": "❌ **Sales order creation cancelled.**\n\nFeel free to upload a new PDF whenever you're ready.",
			"requires_action": False,
			"cancelled": True
		}
	
	def _handle_modification(self, session_id, conversation_id, modifications):
		"""Handle user modifications to extracted data."""
		if not modifications:
			return {
				"status": "info",
				"message": "I couldn't understand what you'd like to change. " + self._get_help_message(),
				"requires_action": True
			}
		
		# Handle item modifications separately
		if "_item_modify" in modifications:
			item_mod = modifications.pop("_item_modify")
			# Get current data
			session_data = self.handler.get_session_data(session_id)
			if session_data.get("status") == "success":
				extracted_data = session_data.get("extracted_data", {})
				items = extracted_data.get("items", [])
				
				if 0 <= item_mod["index"] < len(items):
					items[item_mod["index"]][item_mod["field"]] = item_mod["value"]
					modifications["items"] = items
		
		# Update the data
		result = self.handler.update_extracted_data(session_id, modifications)
		
		if result.get("status") == "success":
			# Update context
			context = self._get_conversation_context(conversation_id)
			context["extracted_data"] = result.get("extracted_data")
			self._save_conversation_context(conversation_id, context)
			
			response = "✅ **Data updated successfully!**\n\n"
			response += "**Changes made:**\n"
			for key, value in modifications.items():
				if not key.startswith("_"):
					response += f"- {key}: {value}\n"
			
			response += "\n" + self._format_extraction_response(result)
			
			return {
				"status": "success",
				"message": response,
				"requires_action": True,
				"data": result.get("extracted_data")
			}
		else:
			return {
				"status": "error",
				"message": f"❌ **Failed to update data:** {result.get('message')}",
				"requires_action": True
			}
	
	def _handle_show_data(self, context):
		"""Show current extracted data to user."""
		extracted_data = context.get("extracted_data", {})
		
		response = "📄 **Current Extracted Data:**\n\n"
		response += self._format_data_display(extracted_data)
		response += "\n" + self._get_action_prompt()
		
		return {
			"status": "success",
			"message": response,
			"requires_action": True,
			"data": extracted_data
		}
	
	def _format_extraction_response(self, result):
		"""Format extraction result for chat display."""
		extracted_data = result.get("extracted_data", {})
		warnings = result.get("validation_warnings", [])
		
		response = "✅ **PDF Analyzed Successfully!**\n\n"
		response += self._format_data_display(extracted_data)
		
		# Add warnings if any
		if warnings:
			response += "\n⚠️ **Validation Warnings:**\n"
			for warning in warnings:
				response += f"• {warning}\n"
		
		response += "\n" + self._get_action_prompt()
		
		return response
	
	def _format_data_display(self, data):
		"""Format data for display."""
		display = ""
		
		# Customer
		customer = data.get("customer") or "Not found"
		display += f"**👤 Customer:** {customer}\n"
		
		# Dates
		order_date = data.get("transaction_date") or "Not found"
		delivery_date = data.get("delivery_date") or "Not found"
		display += f"**📅 Order Date:** {order_date}\n"
		display += f"**🚚 Delivery Date:** {delivery_date}\n"
		
		# PO Info (if available)
		if data.get("po_no"):
			display += f"**📝 PO Number:** {data.get('po_no')}\n"
		
		# Company (if available)
		if data.get("company"):
			display += f"**🏢 Company:** {data.get('company')}\n"
		
		# Items
		items = data.get("items", [])
		if items:
			display += f"\n**📦 Items:** ({len(items)} item{'s' if len(items) != 1 else ''})\n"
			for idx, item in enumerate(items, 1):
				item_name = item.get("item_name") or item.get("item_code") or "Unknown"
				qty = item.get("qty", 0)
				rate = item.get("rate", 0)
				uom = item.get("uom", "")
				
				display += f"  {idx}. **{item_name}**\n"
				display += f"     • Qty: {qty} {uom}\n"
				if rate:
					display += f"     • Rate: {rate}\n"
		else:
			display += "\n⚠️ **No items found**\n"
		
		return display
	
	def _get_action_prompt(self):
		"""Get action prompt for user."""
		return """**What would you like to do?**
• Type **'confirm'** to create the sales order
• Type **'change [field] to [value]'** to modify any field
  Example: "change customer to CUST-001"
• Type **'cancel'** to cancel
• Type **'show data'** to see the data again"""
	
	def _get_help_message(self):
		"""Get help message for user."""
		return """**Here's what you can do:**

**To confirm and create the order:**
• Type: "confirm", "yes", "create", or "proceed"

**To modify data:**
• Change customer: "change customer to CUST-001"
• Change date: "change date to 2024-01-15"
• Change delivery date: "change delivery date to 2024-02-01"
• Change item quantity: "change item 1 quantity to 20"

**To cancel:**
• Type: "cancel" or "no"

**To see the data again:**
• Type: "show data" or "display"

What would you like to do?"""
	
	def _save_conversation_context(self, conversation_id, context):
		"""Save conversation context to cache."""
		try:
			cache_key = f"{self.context_key_prefix}:{conversation_id}"
			frappe.cache().set_value(cache_key, json.dumps(context), expires_in_sec=86400)
		except Exception as e:
			frappe.logger().error(f"Error saving conversation context: {str(e)}")
	
	def _get_conversation_context(self, conversation_id):
		"""Get conversation context from cache."""
		try:
			cache_key = f"{self.context_key_prefix}:{conversation_id}"
			cached_data = frappe.cache().get_value(cache_key)
			if cached_data:
				return json.loads(cached_data)
			return None
		except Exception as e:
			frappe.logger().error(f"Error getting conversation context: {str(e)}")
			return None
	
	def _clear_conversation_context(self, conversation_id):
		"""Clear conversation context from cache."""
		try:
			cache_key = f"{self.context_key_prefix}:{conversation_id}"
			frappe.cache().delete_value(cache_key)
		except Exception as e:
			frappe.logger().error(f"Error clearing conversation context: {str(e)}")


# API endpoints for chat integration

@frappe.whitelist()
def handle_pdf_in_chat(file_url, conversation_id, user_message=""):
	"""
	API endpoint to handle PDF upload in chat.
	
	Args:
		file_url: URL of uploaded PDF
		conversation_id: Chat conversation ID
		user_message: Optional user message
	
	Returns:
		dict: Response for chat interface
	"""
	integration = PDFChatIntegration()
	return integration.handle_pdf_upload(file_url, conversation_id, user_message)


@frappe.whitelist()
def handle_pdf_response(conversation_id, user_message):
	"""
	API endpoint to handle user response to PDF extraction.
	
	Args:
		conversation_id: Chat conversation ID
		user_message: User's response message
	
	Returns:
		dict: Response for chat interface
	"""
	integration = PDFChatIntegration()
	return integration.handle_user_response(conversation_id, user_message)


@frappe.whitelist()
def check_pdf_context(conversation_id):
	"""
	Check if there's an active PDF context for a conversation.
	
	Args:
		conversation_id: Chat conversation ID
	
	Returns:
		dict: Context status
	"""
	integration = PDFChatIntegration()
	context = integration._get_conversation_context(conversation_id)
	
	if context:
		return {
			"has_context": True,
			"status": context.get("status"),
			"session_id": context.get("session_id")
		}
	else:
		return {
			"has_context": False
		}


# Helper function to detect if a message is related to PDF sales order
def is_pdf_sales_order_intent(message):
	"""
	Detect if user message is related to PDF sales order creation.
	
	Args:
		message: User message
	
	Returns:
		bool: True if related to PDF sales order
	"""
	message_lower = message.lower()
	
	pdf_keywords = ["pdf", "upload", "file", "document", "scan"]
	sales_order_keywords = ["sales order", "order", "purchase", "so", "create order"]
	
	has_pdf = any(keyword in message_lower for keyword in pdf_keywords)
	has_sales_order = any(keyword in message_lower for keyword in sales_order_keywords)
	
	return has_pdf and has_sales_order

