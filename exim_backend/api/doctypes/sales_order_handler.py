"""
Sales Order DocType handler.
Contains all sales order-specific logic and operations.
"""

import frappe
import json
from frappe.utils import nowdate, add_days
from exim_backend.api.doctypes.base_handler import BaseDocTypeHandler


class SalesOrderHandler(BaseDocTypeHandler):
	"""Handler for Sales Order doctype operations."""
	
	def __init__(self):
		super().__init__()
		self.doctype = "Sales Order"
		self.label = "Sales Order"
	
	def get_search_fields(self):
		"""Get fields to include in sales order search results."""
		return """
			name,
			customer,
			customer_name,
			transaction_date,
			delivery_date,
			status,
			grand_total,
			currency,
			company,
			creation,
			modified
		"""
	
	def get_date_fields(self):
		"""Get list of date/datetime fields for Sales Order."""
		return ['creation', 'modified', 'transaction_date', 'delivery_date', 'po_date']
	
	def prepare_document_data(self, fields):
		"""Prepare sales order data with required fields and defaults."""
		# Set default order_type
		if not fields.get("order_type"):
			fields["order_type"] = "Sales"
		
		# Set default transaction_date if not provided
		if not fields.get("transaction_date"):
			fields["transaction_date"] = nowdate()
		
		# Set default delivery_date if not provided (7 days from transaction_date)
		if not fields.get("delivery_date"):
			transaction_date = fields.get("transaction_date") or nowdate()
			fields["delivery_date"] = add_days(transaction_date, 7)
		
		# Get default company if not provided
		if not fields.get("company"):
			company = frappe.db.get_single_value("Global Defaults", "default_company")
			if company:
				fields["company"] = company
		
		# Map common field names
		field_mapping = {
			"date": "transaction_date",
			"order_date": "transaction_date",
			"delivery": "delivery_date",
			"items": "items",  # Keep items as is
		}
		
		for old_key, new_key in field_mapping.items():
			if old_key in fields and new_key not in fields:
				fields[new_key] = fields.pop(old_key)
		
		return fields
	
	def prepare_item_data(self, item):
		"""Prepare individual item data for Sales Order Item."""
		# Validate item_code exists
		if not item.get("item_code"):
			raise ValueError("item_code is required for each item")
		
		# Validate qty
		if not item.get("qty") or item.get("qty") <= 0:
			raise ValueError("qty must be greater than 0 for each item")
		
		# Get item details if item_code exists
		if frappe.db.exists("Item", item.get("item_code")):
			item_doc = frappe.get_doc("Item", item.get("item_code"))
			
			# Auto-fill item_name if not provided
			if not item.get("item_name"):
				item["item_name"] = item_doc.item_name
			
			# Auto-fill uom if not provided
			if not item.get("uom"):
				item["uom"] = item_doc.stock_uom
			
			# Auto-fill stock_uom if not provided
			if not item.get("stock_uom"):
				item["stock_uom"] = item_doc.stock_uom
		
		return item
	
	def create_document(self, fields):
		"""Create sales order with proper validation."""
		try:
			prepared_fields = self.prepare_document_data(fields)
			
			# Validate required fields
			if not prepared_fields.get("customer"):
				return {
					"status": "error",
					"message": "Customer is required. Please provide 'customer' field."
				}
			
			# Validate customer exists
			if not frappe.db.exists("Customer", prepared_fields.get("customer")):
				return {
					"status": "error",
					"message": f"Customer '{prepared_fields.get('customer')}' does not exist."
				}
			
			if not prepared_fields.get("company"):
				return {
					"status": "error",
					"message": "Company is required. Please provide 'company' field or set default company in Global Defaults."
				}
			
			# Validate company exists
			if not frappe.db.exists("Company", prepared_fields.get("company")):
				return {
					"status": "error",
					"message": f"Company '{prepared_fields.get('company')}' does not exist."
				}
			
			# Validate items
			items = prepared_fields.get("items", [])
			if not items or len(items) == 0:
				return {
					"status": "error",
					"message": "At least one item is required. Please provide 'items' array with item_code and qty."
				}
			
			# Prepare items array
			prepared_items = []
			for idx, item in enumerate(items):
				try:
					prepared_item = self.prepare_item_data(item)
					prepared_items.append(prepared_item)
				except ValueError as e:
					return {
						"status": "error",
						"message": f"Error in item {idx + 1}: {str(e)}"
					}
			
			# Replace items with prepared items
			prepared_fields["items"] = prepared_items
			
			# Create sales order
			doc = frappe.get_doc({
				"doctype": self.doctype,
				**prepared_fields
			})
			
			# Insert the document (this will automatically calculate totals during validation)
			doc.insert(ignore_permissions=True)
			
			# Commit to ensure document is saved
			frappe.db.commit()
			
			return {
				"status": "success",
				"message": f"{self.label} '{doc.name}' created successfully for customer '{doc.customer_name}'",
				"name": doc.name,
				"doctype": self.doctype,
				"customer": doc.customer,
				"customer_name": doc.customer_name,
				"grand_total": doc.grand_total,
				"transaction_date": str(doc.transaction_date),
				"delivery_date": str(doc.delivery_date) if doc.delivery_date else None
			}
		except frappe.exceptions.ValidationError as e:
			error_msg = str(e)
			frappe.logger().error(f"Validation error creating {self.doctype}: {error_msg}")
			return {
				"status": "error",
				"message": f"Validation error: {error_msg}"
			}
		except Exception as e:
			error_msg = str(e)
			frappe.logger().error(f"Create {self.doctype} error: {error_msg}")
			frappe.log_error(title=f"Sales Order Creation Error")
			return {
				"status": "error",
				"message": f"Failed to create {self.label}: {error_msg}"
			}
	
	def get_document_details(self, name):
		"""Get detailed sales order information."""
		try:
			if not frappe.db.exists(self.doctype, name):
				return {
					"status": "error",
					"message": f"{self.label} '{name}' not found"
				}
			
			doc = frappe.get_doc(self.doctype, name)
			sales_order_data = doc.as_dict()
			
			# Include items information
			if sales_order_data.get("items"):
				# Items are already included in as_dict()
				pass
			
			return {
				"status": "success",
				"sales_order": sales_order_data
			}
		except Exception as e:
			frappe.logger().error(f"Get sales order details error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get details: {str(e)}"
			}
	
	def count_by_customer(self):
		"""Count sales orders grouped by customer."""
		try:
			query = """
				SELECT 
					customer,
					customer_name,
					COUNT(*) as order_count
				FROM `tabSales Order`
				GROUP BY customer, customer_name
				ORDER BY order_count DESC
			"""
			results = frappe.db.sql(query, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Count by customer error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to count by customer: {str(e)}"
			}
	
	def get_items_count(self, limit=20, order_by="item_count desc"):
		"""Get sales orders with item counts, ordered by number of items."""
		try:
			query = f"""
				SELECT 
					so.name,
					so.customer,
					so.customer_name,
					so.transaction_date,
					so.status,
					so.grand_total,
					so.currency,
					so.company,
					COUNT(soi.name) as item_count
				FROM `tabSales Order` so
				LEFT JOIN `tabSales Order Item` soi ON soi.parent = so.name
				GROUP BY so.name, so.customer, so.customer_name, so.transaction_date, so.status, so.grand_total, so.currency, so.company
				ORDER BY {order_by}
				LIMIT %(limit)s
			"""
			results = frappe.db.sql(query, {"limit": limit}, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Get items count error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get items count: {str(e)}"
			}
	
	def get_customers_by_order_count(self, limit=10, order_by="order_count desc"):
		"""Get customers with most orders, ordered by order count."""
		try:
			query = f"""
				SELECT 
					so.customer,
					so.customer_name,
					COUNT(*) as order_count,
					SUM(so.grand_total) as total_value,
					so.currency,
					MAX(so.transaction_date) as last_order_date
				FROM `tabSales Order` so
				WHERE so.customer IS NOT NULL
				GROUP BY so.customer, so.customer_name, so.currency
				ORDER BY {order_by}
				LIMIT %(limit)s
			"""
			results = frappe.db.sql(query, {"limit": limit}, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Get customers by order count error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get customers by order count: {str(e)}"
			}
	
	def get_customers_by_order_value(self, limit=10, order_by="total_value desc"):
		"""Get customers with highest order value, ordered by total value."""
		try:
			query = f"""
				SELECT 
					so.customer,
					so.customer_name,
					COUNT(*) as order_count,
					SUM(so.grand_total) as total_value,
					AVG(so.grand_total) as avg_order_value,
					so.currency,
					MAX(so.transaction_date) as last_order_date
				FROM `tabSales Order` so
				WHERE so.customer IS NOT NULL
				GROUP BY so.customer, so.customer_name, so.currency
				ORDER BY {order_by}
				LIMIT %(limit)s
			"""
			results = frappe.db.sql(query, {"limit": limit}, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Get customers by order value error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get customers by order value: {str(e)}"
			}
	
	def get_orders_by_customer_group(self, customer_group):
		"""Get sales orders filtered by customer group."""
		try:
			# Join with Customer to filter by customer_group
			query = """
				SELECT 
					so.name,
					so.customer,
					so.customer_name,
					so.transaction_date,
					so.status,
					so.grand_total,
					so.currency,
					so.company,
					c.customer_group,
					c.territory
				FROM `tabSales Order` so
				INNER JOIN `tabCustomer` c ON c.name = so.customer
				WHERE c.customer_group = %(customer_group)s
				ORDER BY so.modified DESC
				LIMIT 100
			"""
			results = frappe.db.sql(query, {"customer_group": customer_group}, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Get orders by customer group error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get orders by customer group: {str(e)}"
			}
	
	def get_orders_by_territory(self, territory):
		"""Get sales orders filtered by territory."""
		try:
			# Join with Customer to filter by territory
			query = """
				SELECT 
					so.name,
					so.customer,
					so.customer_name,
					so.transaction_date,
					so.status,
					so.grand_total,
					so.currency,
					so.company,
					c.customer_group,
					c.territory
				FROM `tabSales Order` so
				INNER JOIN `tabCustomer` c ON c.name = so.customer
				WHERE c.territory = %(territory)s
				ORDER BY so.modified DESC
				LIMIT 100
			"""
			results = frappe.db.sql(query, {"territory": territory}, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Get orders by territory error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get orders by territory: {str(e)}"
			}
	
	def get_orders_by_item(self, item_code):
		"""Get sales orders containing a specific item."""
		try:
			query = """
				SELECT DISTINCT
					so.name,
					so.customer,
					so.customer_name,
					so.transaction_date,
					so.status,
					so.grand_total,
					so.currency,
					so.company,
					soi.item_code,
					soi.item_name,
					soi.qty,
					soi.rate,
					soi.amount
				FROM `tabSales Order` so
				INNER JOIN `tabSales Order Item` soi ON soi.parent = so.name
				WHERE soi.item_code = %(item_code)s
				ORDER BY so.modified DESC
				LIMIT 100
			"""
			results = frappe.db.sql(query, {"item_code": item_code}, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Get orders by item error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get orders by item: {str(e)}"
			}
	
	def get_orders_with_most_items(self, limit=10, order_by="item_count desc"):
		"""Get sales orders with most line items, ordered by item count."""
		try:
			query = f"""
				SELECT 
					so.name,
					so.customer,
					so.customer_name,
					so.transaction_date,
					so.status,
					so.grand_total,
					so.currency,
					so.company,
					COUNT(soi.name) as item_count
				FROM `tabSales Order` so
				LEFT JOIN `tabSales Order Item` soi ON soi.parent = so.name
				GROUP BY so.name, so.customer, so.customer_name, so.transaction_date, so.status, so.grand_total, so.currency, so.company
				ORDER BY {order_by}
				LIMIT %(limit)s
			"""
			results = frappe.db.sql(query, {"limit": limit}, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Get orders with most items error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get orders with most items: {str(e)}"
			}
	
	def get_orders_by_item_group(self, item_group):
		"""Get sales orders containing items from a specific item group."""
		try:
			# Join with Sales Order Item and Item to filter by item_group
			query = """
				SELECT DISTINCT
					so.name,
					so.customer,
					so.customer_name,
					so.transaction_date,
					so.status,
					so.grand_total,
					so.currency,
					so.company,
					soi.item_code,
					soi.item_name,
					soi.qty,
					i.item_group
				FROM `tabSales Order` so
				INNER JOIN `tabSales Order Item` soi ON soi.parent = so.name
				INNER JOIN `tabItem` i ON i.name = soi.item_code
				WHERE i.item_group = %(item_group)s
				ORDER BY so.modified DESC
				LIMIT 100
			"""
			results = frappe.db.sql(query, {"item_group": item_group}, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Get orders by item group error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get orders by item group: {str(e)}"
			}
	
	def get_total_quantity_sold(self, item_code, from_date=None, to_date=None):
		"""Get total quantity sold for a specific item within a date range."""
		try:
			conditions = ["soi.item_code = %(item_code)s"]
			params = {"item_code": item_code}
			
			# Normalize date values if provided
			if from_date:
				normalized_from_date = self.normalize_date_value(from_date, "transaction_date")
				conditions.append("so.transaction_date >= %(from_date)s")
				params["from_date"] = normalized_from_date
			if to_date:
				normalized_to_date = self.normalize_date_value(to_date, "transaction_date")
				conditions.append("so.transaction_date <= %(to_date)s")
				params["to_date"] = normalized_to_date
			
			where_clause = " AND ".join(conditions)
			
			query = f"""
				SELECT 
					soi.item_code,
					soi.item_name,
					SUM(soi.qty) as total_qty,
					SUM(soi.amount) as total_amount,
					COUNT(DISTINCT so.name) as order_count
				FROM `tabSales Order Item` soi
				INNER JOIN `tabSales Order` so ON so.name = soi.parent
				WHERE {where_clause}
				GROUP BY soi.item_code, soi.item_name
			"""
			results = frappe.db.sql(query, params, as_dict=True)
			
			if results and len(results) > 0:
				return {
					"status": "success",
					"item_code": item_code,
					"item_name": results[0].get("item_name"),
					"total_qty": results[0].get("total_qty", 0),
					"total_amount": results[0].get("total_amount", 0),
					"order_count": results[0].get("order_count", 0),
					"from_date": from_date,
					"to_date": to_date
				}
			else:
				return {
					"status": "success",
					"item_code": item_code,
					"total_qty": 0,
					"total_amount": 0,
					"order_count": 0,
					"from_date": from_date,
					"to_date": to_date
				}
		except Exception as e:
			frappe.logger().error(f"Get total quantity sold error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get total quantity sold: {str(e)}"
			}
	
	def get_most_sold_items(self, limit=10, order_by="total_qty desc", from_date=None, to_date=None):
		"""Get most sold items aggregated by item_code, ordered by total quantity."""
		try:
			conditions = []
			params = {}
			
			# Normalize date values if provided
			if from_date:
				normalized_from_date = self.normalize_date_value(from_date, "transaction_date")
				conditions.append("so.transaction_date >= %(from_date)s")
				params["from_date"] = normalized_from_date
			if to_date:
				normalized_to_date = self.normalize_date_value(to_date, "transaction_date")
				conditions.append("so.transaction_date <= %(to_date)s")
				params["to_date"] = normalized_to_date
			
			where_clause = " AND ".join(conditions) if conditions else "1=1"
			params["limit"] = limit
			
			query = f"""
				SELECT 
					soi.item_code,
					soi.item_name,
					SUM(soi.qty) as total_qty,
					SUM(soi.amount) as total_amount,
					COUNT(DISTINCT so.name) as order_count,
					AVG(soi.rate) as avg_rate
				FROM `tabSales Order Item` soi
				INNER JOIN `tabSales Order` so ON so.name = soi.parent
				WHERE {where_clause}
				GROUP BY soi.item_code, soi.item_name
				ORDER BY {order_by}
				LIMIT %(limit)s
			"""
			results = frappe.db.sql(query, params, as_dict=True)
			return {
				"status": "success",
				"count": len(results),
				"results": results
			}
		except Exception as e:
			frappe.logger().error(f"Get most sold items error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get most sold items: {str(e)}"
			}

