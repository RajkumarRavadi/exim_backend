"""
Item DocType handler.
Contains all item-specific logic and operations.
"""

import frappe
import json
from exim_backend.api.doctypes.base_handler import BaseDocTypeHandler


class ItemHandler(BaseDocTypeHandler):
	"""Handler for Item doctype operations."""
	
	def __init__(self):
		super().__init__()
		self.doctype = "Item"
		self.label = "Item"
	
	def get_search_fields(self):
		"""Get fields to include in item search results."""
		return """
			name,
			item_code,
			item_name,
			item_group,
			stock_uom,
			is_stock_item,
			has_variants,
			has_batch_no,
			has_serial_no,
			brand,
			description,
			standard_rate,
			creation,
			modified
		"""
	
	def prepare_document_data(self, fields):
		"""Prepare item data with required fields and defaults."""
		# Set defaults for required fields
		if not fields.get("item_group"):
			fields["item_group"] = frappe.db.get_single_value("Stock Settings", "item_group") or "All Item Groups"
		
		if not fields.get("stock_uom"):
			fields["stock_uom"] = frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos"
		
		# Generate item_code if not provided but item_name is available
		if not fields.get("item_code") and fields.get("item_name"):
			# Create item_code from item_name (uppercase, replace spaces with hyphens)
			item_code = fields.get("item_name", "").upper().replace(" ", "-").replace("_", "-")
			# Remove special characters except hyphens
			import re
			item_code = re.sub(r'[^A-Z0-9\-]', '', item_code)
			fields["item_code"] = item_code
		
		# Set item_name from item_code if item_name not provided
		if not fields.get("item_name") and fields.get("item_code"):
			fields["item_name"] = fields.get("item_code")
		
		# Set defaults for common fields
		if "is_stock_item" not in fields:
			fields["is_stock_item"] = 1  # Default to stock item
		
		if "has_variants" not in fields:
			fields["has_variants"] = 0
		
		if "has_batch_no" not in fields:
			fields["has_batch_no"] = 0
		
		if "has_serial_no" not in fields:
			fields["has_serial_no"] = 0
		
		# Map common field names
		field_mapping = {
			"name": "item_name",
			"product_name": "item_name",
			"product_code": "item_code",
			"code": "item_code",
			"uom": "stock_uom",
			"unit": "stock_uom",
			"unit_of_measure": "stock_uom",
			"price": "standard_rate",
			"rate": "standard_rate",
			"selling_price": "standard_rate",
		}
		
		for old_key, new_key in field_mapping.items():
			if old_key in fields and new_key not in fields:
				fields[new_key] = fields.pop(old_key)
		
		return fields
	
	def create_document(self, fields):
		"""Create item with proper validation."""
		try:
			prepared_fields = self.prepare_document_data(fields)
			
			# Validate required fields
			if not prepared_fields.get("item_code"):
				return {
					"status": "error",
					"message": "Item code is required. Please provide 'item_code' or 'item_name'."
				}
			
			if not prepared_fields.get("item_name"):
				return {
					"status": "error",
					"message": "Item name is required."
				}
			
			# Check if item_code already exists
			if frappe.db.exists("Item", prepared_fields.get("item_code")):
				return {
					"status": "error",
					"message": f"Item with code '{prepared_fields.get('item_code')}' already exists."
				}
			
			# Create item
			doc = frappe.get_doc({
				"doctype": self.doctype,
				**prepared_fields
			})
			doc.insert(ignore_permissions=True)
			
			# Commit to ensure document is saved
			frappe.db.commit()
			
			return {
				"status": "success",
				"message": f"{self.label} '{doc.item_name}' (Code: {doc.item_code}) created successfully",
				"name": doc.name,
				"doctype": self.doctype,
				"item_code": doc.item_code
			}
		except frappe.exceptions.DuplicateEntryError:
			frappe.logger().error(f"Duplicate item code: {fields.get('item_code')}")
			return {
				"status": "error",
				"message": f"Item with code '{fields.get('item_code')}' already exists."
			}
		except Exception as e:
			frappe.logger().error(f"Create {self.doctype} error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to create {self.label}: {str(e)}"
			}
	
	def get_document_details(self, name):
		"""Get detailed item information."""
		try:
			original_name = name
			frappe.logger().info(f"Getting item details for: '{name}'")
			
			# Try to find by document name (ID) first
			if not frappe.db.exists(self.doctype, name):
				frappe.logger().info(f"Item '{name}' not found by document name, trying item_code...")
				# Try to find by item_code field
				item_code = frappe.db.get_value(self.doctype, {"item_code": name}, "name")
				if item_code:
					frappe.logger().info(f"Found item by item_code: {item_code}")
					name = item_code
				else:
					frappe.logger().info(f"Item '{name}' not found by item_code, trying item_name (exact match)...")
					# Try to find by item_name field (case-insensitive, exact match first)
					item_name = frappe.db.sql("""
						SELECT name 
						FROM `tabItem` 
						WHERE LOWER(item_name) = LOWER(%s)
						LIMIT 1
					""", name, as_dict=True)
					if item_name and len(item_name) > 0:
						frappe.logger().info(f"Found item by item_name (exact): {item_name[0].name}")
						name = item_name[0].name
					else:
						frappe.logger().info(f"Item '{name}' not found by exact item_name, trying partial match...")
						# Try partial match on item_name (case-insensitive)
						item_name = frappe.db.sql("""
							SELECT name 
							FROM `tabItem` 
							WHERE LOWER(item_name) LIKE LOWER(%s)
							ORDER BY modified DESC
							LIMIT 1
						""", f"%{name}%", as_dict=True)
						if item_name and len(item_name) > 0:
							frappe.logger().info(f"Found item by item_name (partial): {item_name[0].name}")
							name = item_name[0].name
						else:
							error_msg = f"{self.label} '{original_name}' not found. Please check the item code or name."
							frappe.logger().warning(error_msg)
							return {
								"status": "error",
								"message": error_msg
							}
			
			# Get the document
			frappe.logger().info(f"Loading item document: {name}")
			doc = frappe.get_doc(self.doctype, name)
			item_data = doc.as_dict()
			
			if not item_data:
				error_msg = f"Failed to retrieve item data for '{name}'"
				frappe.logger().error(error_msg)
				return {
					"status": "error",
					"message": error_msg
				}
			
			# Get item prices
			try:
				item_prices = frappe.get_all(
					"Item Price",
					filters={"item_code": doc.item_code},
					fields=["price_list", "price_list_rate", "currency"],
					limit=5
				)
				item_data["prices"] = item_prices or []
			except Exception as price_error:
				frappe.logger().warning(f"Error getting item prices: {str(price_error)}")
				item_data["prices"] = []
			
			# Get stock information if it's a stock item
			if doc.is_stock_item:
				try:
					bin_data = frappe.db.sql("""
						SELECT 
							warehouse,
							actual_qty,
							reserved_qty,
							ordered_qty,
							projected_qty
						FROM `tabBin`
						WHERE item_code = %s
						LIMIT 5
					""", doc.item_code, as_dict=True)
					item_data["stock"] = bin_data or []
				except Exception as stock_error:
					frappe.logger().warning(f"Error getting stock information: {str(stock_error)}")
					item_data["stock"] = []
			else:
				item_data["stock"] = []
			
			# Ensure item_data has required fields
			if not item_data.get("name") and not item_data.get("item_code"):
				error_msg = f"Item data is missing required fields (name/item_code)"
				frappe.logger().error(f"{error_msg}. Item data: {item_data}")
				return {
					"status": "error",
					"message": error_msg
				}
			
			result = {
				"status": "success",
				"item": item_data
			}
			frappe.logger().info(f"Successfully retrieved item details for '{name}'. Item code: {item_data.get('item_code')}, Item name: {item_data.get('item_name')}")
			return result
			
		except frappe.DoesNotExistError:
			error_msg = f"{self.label} '{original_name if 'original_name' in locals() else name}' does not exist"
			frappe.logger().error(error_msg)
			return {
				"status": "error",
				"message": error_msg
			}
		except Exception as e:
			error_msg = f"Failed to get details: {str(e)}"
			frappe.logger().error(f"Get item details error for '{name if 'name' in locals() else 'unknown'}': {error_msg}")
			frappe.logger().exception("Full exception traceback:")
			return {
				"status": "error",
				"message": error_msg
			}
	
	def search_by_query(self, query, limit=10):
		"""
		Search items by code, name, or description.
		Legacy method for backward compatibility.
		"""
		try:
			if not query:
				return {
					"status": "error",
					"message": "Search query is required"
				}
			
			items = frappe.db.sql("""
				SELECT 
					name,
					item_code,
					item_name,
					item_group,
					stock_uom,
					is_stock_item,
					has_variants,
					brand,
					description,
					standard_rate,
					creation,
					modified
				FROM `tabItem`
				WHERE 
					item_code LIKE %(search)s
					OR item_name LIKE %(search)s
					OR description LIKE %(search)s
					OR name LIKE %(search)s
				ORDER BY modified DESC
				LIMIT %(limit)s
			""", {
				"search": f"%{query}%",
				"limit": limit
			}, as_dict=True)
			
			return {
				"status": "success",
				"count": len(items),
				"items": items
			}
		except Exception as e:
			frappe.logger().error(f"Item search error: {str(e)}")
			return {
				"status": "error",
				"message": f"Search failed: {str(e)}"
			}
	
	def count_with_breakdown(self):
		"""
		Count items with breakdown by item group and stock status.
		"""
		try:
			total_count = frappe.db.count(self.doctype)
			
			# Count by item group
			by_group = frappe.db.sql("""
				SELECT item_group, COUNT(*) as count
				FROM `tabItem`
				GROUP BY item_group
				ORDER BY count DESC
				LIMIT 10
			""", as_dict=True)
			
			# Count by stock status
			stock_items = frappe.db.count(self.doctype, filters={"is_stock_item": 1})
			non_stock_items = total_count - stock_items
			
			# Count by variant status
			has_variants = frappe.db.count(self.doctype, filters={"has_variants": 1})
			
			return {
				"status": "success",
				"total_count": total_count,
				"by_group": by_group,
				"stock_items": stock_items,
				"non_stock_items": non_stock_items,
				"has_variants": has_variants
			}
		except Exception as e:
			frappe.logger().error(f"Count items error: {str(e)}")
			return {
				"status": "error",
				"message": f"Count failed: {str(e)}"
			}

