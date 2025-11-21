"""
Sales Person DocType handler.
Contains all sales person-specific logic and operations.

The Sales Person doctype in ERPNext is a tree structure (NestedSet) that allows
hierarchical organization of sales persons. Key fields include:
- sales_person_name: Required, unique name of the sales person
- parent_sales_person: Link to parent sales person (for tree structure)
- employee: Link to Employee record
- department: Auto-fetched from employee
- is_group: Checkbox to indicate if this is a group node
- enabled: Checkbox to enable/disable the sales person
- commission_rate: Commission rate for the sales person
- targets: Table of Target Detail records for setting sales targets
"""

import frappe
from frappe.utils import flt, getdate, add_days, today
from datetime import datetime, timedelta
from exim_backend.api.doctypes.base_handler import BaseDocTypeHandler


class SalesPersonHandler(BaseDocTypeHandler):
	"""Handler for Sales Person doctype operations."""
	
	def __init__(self):
		super().__init__()
		self.doctype = "Sales Person"
		self.label = "Sales Person"
	
	def get_search_fields(self):
		"""Get fields to include in sales person search results."""
		return """
			name,
			sales_person_name,
			parent_sales_person,
			employee,
			department,
			is_group,
			enabled,
			commission_rate,
			creation,
			modified
		"""
	
	def prepare_document_data(self, fields):
		"""
		Prepare sales person data with required fields and defaults.
		
		Args:
			fields: Dictionary of field values
		
		Returns:
			Prepared fields dictionary with defaults applied
		"""
		# Set default is_group if not provided
		if "is_group" not in fields:
			fields["is_group"] = 0
		
		# Set default enabled if not provided
		if "enabled" not in fields:
			fields["enabled"] = 1
		
		# Set parent_sales_person to root if not provided
		# Sales Person is a tree doctype, so it needs a parent
		if not fields.get("parent_sales_person"):
			# Get root of Sales Person tree
			try:
				from frappe.utils.nestedset import get_root_of
				root = get_root_of("Sales Person")
				if root:
					fields["parent_sales_person"] = root
			except Exception as e:
				frappe.logger().warning(f"Could not get root of Sales Person tree: {str(e)}")
				# If root doesn't exist, we'll let Frappe handle it during validation
		
		# Map common field names
		field_mapping = {
			"name": "sales_person_name",  # Allow 'name' as alias for sales_person_name
			"salesperson_name": "sales_person_name",
			"sales_person": "sales_person_name",
		}
		
		for old_key, new_key in field_mapping.items():
			if old_key in fields and new_key not in fields:
				fields[new_key] = fields.pop(old_key)
		
		return fields
	
	def create_document(self, fields):
		"""
		Create sales person with proper validation.
		
		Args:
			fields: Dictionary of field values
		
		Returns:
			dict: Result with status, message, and created document info
		"""
		try:
			prepared_fields = self.prepare_document_data(fields)
			
			# Validate required fields
			if not prepared_fields.get("sales_person_name"):
				return {
					"status": "error",
					"message": "Sales Person Name is required. Please provide 'sales_person_name' field."
				}
			
			# Check if sales person with same name already exists
			if frappe.db.exists(self.doctype, {"sales_person_name": prepared_fields.get("sales_person_name")}):
				return {
					"status": "error",
					"message": f"Sales Person with name '{prepared_fields.get('sales_person_name')}' already exists."
				}
			
			# Validate employee if provided
			if prepared_fields.get("employee"):
				if not frappe.db.exists("Employee", prepared_fields.get("employee")):
					return {
						"status": "error",
						"message": f"Employee '{prepared_fields.get('employee')}' does not exist."
					}
			
			# Validate parent_sales_person if provided
			if prepared_fields.get("parent_sales_person"):
				if not frappe.db.exists(self.doctype, prepared_fields.get("parent_sales_person")):
					return {
						"status": "error",
						"message": f"Parent Sales Person '{prepared_fields.get('parent_sales_person')}' does not exist."
					}
			
			# Create sales person
			doc = frappe.get_doc({
				"doctype": self.doctype,
				**prepared_fields
			})
			doc.insert(ignore_permissions=True)
			
			# Commit to ensure document is saved
			frappe.db.commit()
			
			return {
				"status": "success",
				"message": f"{self.label} '{doc.sales_person_name}' created successfully",
				"name": doc.name,
				"doctype": self.doctype,
				"sales_person_name": doc.sales_person_name,
				"employee": doc.employee,
				"department": doc.department,
				"is_group": doc.is_group,
				"enabled": doc.enabled
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
			frappe.log_error(title=f"Sales Person Creation Error")
			return {
				"status": "error",
				"message": f"Failed to create {self.label}: {error_msg}"
			}
	
	def get_document_details(self, name):
		"""
		Get detailed sales person information.
		
		Args:
			name: Sales Person name/ID
		
		Returns:
			dict: Sales person details including targets
		"""
		try:
			if not frappe.db.exists(self.doctype, name):
				return {
					"status": "error",
					"message": f"{self.label} '{name}' not found"
				}
			
			doc = frappe.get_doc(self.doctype, name)
			sales_person_data = doc.as_dict()
			
			# Include targets information if available
			if sales_person_data.get("targets"):
				# Targets are already included in as_dict()
				pass
			
			return {
				"status": "success",
				"sales_person": sales_person_data
			}
		except Exception as e:
			frappe.logger().error(f"Get sales person details error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get details: {str(e)}"
			}
	
	def get_sales_person_count(self, filters=None):
		"""
		Get total count of sales persons.
		Optionally filter by enabled status, is_group, etc.
		
		Args:
			filters: Optional dictionary of filters (e.g., {"enabled": 1})
		
		Returns:
			dict: Count result with optional breakdown
		"""
		try:
			if filters:
				# Use dynamic_search to count with filters
				result = self.count_documents(filters)
				return result
			else:
				# Get total count
				total_count = frappe.db.count(self.doctype)
				return {
					"status": "success",
					"total_count": total_count
				}
		except Exception as e:
			frappe.logger().error(f"Get sales person count error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get count: {str(e)}"
			}
	
	def get_sales_person_names(self, filters=None, limit=None):
		"""
		Get list of sales person names.
		
		Args:
			filters: Optional dictionary of filters (e.g., {"enabled": 1})
			limit: Optional limit on number of results
		
		Returns:
			dict: List of sales person names with optional details
		"""
		try:
			# Build query conditions
			conditions = []
			values = {}
			
			if filters:
				for field, value in filters.items():
					if value is not None and value != "":
						conditions.append(f"`{field}` = %({field})s")
						values[field] = value
			
			where_clause = " AND ".join(conditions) if conditions else "1=1"
			
			# Build limit clause
			limit_clause = ""
			if limit:
				limit_clause = f"LIMIT %(limit)s"
				values["limit"] = limit
			
			# Query to get sales person names
			query = f"""
				SELECT 
					name,
					sales_person_name,
					parent_sales_person,
					employee,
					department,
					is_group,
					enabled
				FROM `tab{self.doctype}`
				WHERE {where_clause}
				ORDER BY sales_person_name ASC
				{limit_clause}
			"""
			
			results = frappe.db.sql(query, values, as_dict=True)
			
			# Extract just the names if needed, or return full details
			names = [r.get("sales_person_name") for r in results]
			
			return {
				"status": "success",
				"count": len(results),
				"names": names,
				"sales_persons": results  # Include full details for flexibility
			}
		except Exception as e:
			frappe.logger().error(f"Get sales person names error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get names: {str(e)}"
			}
	
	def get_sales_persons_by_status(self):
		"""
		Get count of sales persons grouped by enabled status.
		
		Returns:
			dict: Count breakdown by enabled/disabled status
		"""
		try:
			query = """
				SELECT 
					enabled,
					COUNT(*) as count
				FROM `tabSales Person`
				GROUP BY enabled
				ORDER BY enabled DESC
			"""
			results = frappe.db.sql(query, as_dict=True)
			
			# Format results
			enabled_count = 0
			disabled_count = 0
			
			for result in results:
				if result.get("enabled"):
					enabled_count = result.get("count", 0)
				else:
					disabled_count = result.get("count", 0)
			
			return {
				"status": "success",
				"enabled_count": enabled_count,
				"disabled_count": disabled_count,
				"total_count": enabled_count + disabled_count,
				"breakdown": results
			}
		except Exception as e:
			frappe.logger().error(f"Get sales persons by status error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get status breakdown: {str(e)}"
			}
	
	def get_sales_persons_by_group(self):
		"""
		Get count of sales persons grouped by is_group flag.
		
		Returns:
			dict: Count breakdown by group/individual
		"""
		try:
			query = """
				SELECT 
					is_group,
					COUNT(*) as count
				FROM `tabSales Person`
				GROUP BY is_group
				ORDER BY is_group DESC
			"""
			results = frappe.db.sql(query, as_dict=True)
			
			# Format results
			group_count = 0
			individual_count = 0
			
			for result in results:
				if result.get("is_group"):
					group_count = result.get("count", 0)
				else:
					individual_count = result.get("count", 0)
			
			return {
				"status": "success",
				"group_count": group_count,
				"individual_count": individual_count,
				"total_count": group_count + individual_count,
				"breakdown": results
			}
		except Exception as e:
			frappe.logger().error(f"Get sales persons by group error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get group breakdown: {str(e)}"
			}
	
	def get_sales_persons_with_employees(self):
		"""
		Get sales persons that are linked to employees.
		
		Returns:
			dict: List of sales persons with employee information
		"""
		try:
			query = """
				SELECT 
					name,
					sales_person_name,
					employee,
					department,
					enabled
				FROM `tabSales Person`
				WHERE employee IS NOT NULL AND employee != ''
				ORDER BY sales_person_name ASC
			"""
			results = frappe.db.sql(query, as_dict=True)
			
			return {
				"status": "success",
				"count": len(results),
				"sales_persons": results
			}
		except Exception as e:
			frappe.logger().error(f"Get sales persons with employees error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get sales persons with employees: {str(e)}"
			}
	
	def get_sales_person_hierarchy(self, name):
		"""
		Get sales person hierarchy (parent and children) for a given sales person.
		
		Args:
			name: Sales Person name/ID
		
		Returns:
			dict: Hierarchy information including parent and children
		"""
		try:
			if not frappe.db.exists(self.doctype, name):
				return {
					"status": "error",
					"message": f"{self.label} '{name}' not found"
				}
			
			doc = frappe.get_doc(self.doctype, name)
			
			# Get parent information
			parent_info = None
			if doc.parent_sales_person:
				parent_doc = frappe.get_doc(self.doctype, doc.parent_sales_person)
				parent_info = {
					"name": parent_doc.name,
					"sales_person_name": parent_doc.sales_person_name,
					"is_group": parent_doc.is_group
				}
			
			# Get children (direct descendants)
			children = frappe.db.sql("""
				SELECT 
					name,
					sales_person_name,
					employee,
					is_group,
					enabled
				FROM `tabSales Person`
				WHERE parent_sales_person = %(name)s
				ORDER BY sales_person_name ASC
			""", {"name": name}, as_dict=True)
			
			return {
				"status": "success",
				"sales_person": {
					"name": doc.name,
					"sales_person_name": doc.sales_person_name,
					"is_group": doc.is_group,
					"enabled": doc.enabled
				},
				"parent": parent_info,
				"children": children,
				"children_count": len(children)
			}
		except Exception as e:
			frappe.logger().error(f"Get sales person hierarchy error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get hierarchy: {str(e)}"
			}
	
	def get_sales_orders_for_sales_person(self, sales_person_name_or_id, filters=None, limit=None):
		"""
		Get sales orders for a specific sales person.
		Handles lookup by sales person name or ID.
		
		Args:
			sales_person_name_or_id: Sales Person name or ID (e.g., "Navneet" or "SP-00001")
			filters: Optional additional filters for Sales Orders
			limit: Optional limit on number of results
		
		Returns:
			dict: Sales orders with count
		"""
		try:
			# First, try to find the sales person by name or ID
			sales_person_id = None
			
			# Check if it's already an ID (starts with common prefixes or is exact match)
			if frappe.db.exists(self.doctype, sales_person_name_or_id):
				sales_person_id = sales_person_name_or_id
			else:
				# Try to find by sales_person_name
				sales_person_doc = frappe.db.get_value(
					self.doctype,
					{"sales_person_name": ["like", f"%{sales_person_name_or_id}%"]},
					"name",
					as_dict=False
				)
				if sales_person_doc:
					sales_person_id = sales_person_doc
			
			if not sales_person_id:
				return {
					"status": "error",
					"message": f"Sales Person '{sales_person_name_or_id}' not found"
				}
			
			# Build query conditions
			conditions = ["st.sales_person = %(sales_person)s", "st.parenttype = 'Sales Order'"]
			values = {"sales_person": sales_person_id}
			
			# Add additional filters if provided
			if filters:
				for field, value in filters.items():
					if field in ["docstatus", "status", "customer", "company"]:
						if isinstance(value, dict):
							# Handle operators
							for operator, op_value in value.items():
								if operator == "$in":
									placeholders = ", ".join([f"%({field}_{i})s" for i in range(len(op_value))])
									conditions.append(f"so.{field} IN ({placeholders})")
									for i, v in enumerate(op_value):
										values[f"{field}_{i}"] = v
								elif operator == "$like":
									conditions.append(f"so.{field} LIKE %({field}_like)s")
									values[f"{field}_like"] = op_value
						else:
							conditions.append(f"so.{field} = %({field})s")
							values[field] = value
			
			where_clause = " AND ".join(conditions)
			
			# Build limit clause
			limit_clause = ""
			if limit:
				limit_clause = f"LIMIT %(limit)s"
				values["limit"] = int(limit)
			
			# Query to get sales orders
			query = f"""
				SELECT DISTINCT
					so.name,
					so.customer,
					so.customer_name,
					so.transaction_date,
					so.delivery_date,
					so.status,
					so.grand_total,
					so.currency,
					so.company,
					so.docstatus,
					so.creation,
					so.modified
				FROM `tabSales Team` st
				INNER JOIN `tabSales Order` so ON so.name = st.parent
				WHERE {where_clause}
				ORDER BY so.modified DESC
				{limit_clause}
			"""
			
			results = frappe.db.sql(query, values, as_dict=True)
			
			return {
				"status": "success",
				"count": len(results),
				"sales_person": sales_person_id,
				"sales_orders": results
			}
		except Exception as e:
			frappe.logger().error(f"Get sales orders for sales person error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get sales orders: {str(e)}"
			}
	
	def count_sales_orders_for_sales_person(self, sales_person_name_or_id, filters=None):
		"""
		Count sales orders for a specific sales person.
		Handles lookup by sales person name or ID.
		
		Args:
			sales_person_name_or_id: Sales Person name or ID (e.g., "Navneet" or "SP-00001")
			filters: Optional additional filters (e.g., {"docstatus": 1} for submitted only)
		
		Returns:
			dict: Count result
		"""
		try:
			# First, try to find the sales person by name or ID
			sales_person_id = None
			
			# Check if it's already an ID
			if frappe.db.exists(self.doctype, sales_person_name_or_id):
				sales_person_id = sales_person_name_or_id
			else:
				# Try to find by sales_person_name
				sales_person_doc = frappe.db.get_value(
					self.doctype,
					{"sales_person_name": ["like", f"%{sales_person_name_or_id}%"]},
					"name",
					as_dict=False
				)
				if sales_person_doc:
					sales_person_id = sales_person_doc
			
			if not sales_person_id:
				return {
					"status": "error",
					"message": f"Sales Person '{sales_person_name_or_id}' not found"
				}
			
			# Build query conditions
			conditions = ["st.sales_person = %(sales_person)s", "st.parenttype = 'Sales Order'"]
			values = {"sales_person": sales_person_id}
			
			# Add additional filters if provided
			if filters:
				for field, value in filters.items():
					if field in ["docstatus", "status", "customer", "company"]:
						if isinstance(value, dict):
							# Handle operators
							for operator, op_value in value.items():
								if operator == "$in":
									placeholders = ", ".join([f"%({field}_{i})s" for i in range(len(op_value))])
									conditions.append(f"so.{field} IN ({placeholders})")
									for i, v in enumerate(op_value):
										values[f"{field}_{i}"] = v
								elif operator == "$like":
									conditions.append(f"so.{field} LIKE %({field}_like)s")
									values[f"{field}_like"] = op_value
						else:
							conditions.append(f"so.{field} = %({field})s")
							values[field] = value
			
			where_clause = " AND ".join(conditions)
			
			# Query to count sales orders
			query = f"""
				SELECT COUNT(DISTINCT so.name) as total_count
				FROM `tabSales Team` st
				INNER JOIN `tabSales Order` so ON so.name = st.parent
				WHERE {where_clause}
			"""
			
			result = frappe.db.sql(query, values, as_dict=True)
			count = result[0]["total_count"] if result else 0
			
			return {
				"status": "success",
				"sales_person": sales_person_id,
				"total_count": count
			}
		except Exception as e:
			frappe.logger().error(f"Count sales orders for sales person error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to count sales orders: {str(e)}"
			}
	
	def get_sales_person_summary(self, sales_person, from_date=None, to_date=None):
		"""
		Get comprehensive summary for a sales person including:
		- Sales Orders count (submitted and draft)
		- Sales Invoices count (submitted and draft)
		- Total sales amounts
		- Outstanding amounts
		- Unique customers handled
		- And more metrics
		
		Sales Orders and Sales Invoices are linked to Sales Persons through
		the Sales Team child table. The relationship is:
		- Sales Order/Sales Invoice -> sales_team (Table) -> Sales Team -> sales_person
		
		Args:
			sales_person: Sales Person name/ID
			from_date: Optional start date for filtering (YYYY-MM-DD format)
			to_date: Optional end date for filtering (YYYY-MM-DD format)
		
		Returns:
			dict: Comprehensive summary with all metrics
		"""
		try:
			# Validate sales person exists
			if not frappe.db.exists(self.doctype, sales_person):
				return {
					"status": "error",
					"message": f"Sales Person '{sales_person}' not found"
				}
			
			# Prepare date filters
			date_conditions = ""
			date_params = {}
			if from_date:
				date_conditions += " AND so.transaction_date >= %(from_date)s"
				date_params["from_date"] = from_date
			if to_date:
				date_conditions += " AND so.transaction_date <= %(to_date)s"
				date_params["to_date"] = to_date
			
			# Date conditions for invoices (use posting_date)
			invoice_date_conditions = ""
			invoice_date_params = {}
			if from_date:
				invoice_date_conditions += " AND si.posting_date >= %(from_date)s"
				invoice_date_params["from_date"] = from_date
			if to_date:
				invoice_date_conditions += " AND si.posting_date <= %(to_date)s"
				invoice_date_params["to_date"] = to_date
			
			summary = {}
			
			# -----------------------
			# Sales Orders Count (Submitted - docstatus = 1)
			# -----------------------
			# Query Sales Orders through Sales Team where sales_person matches
			# and parenttype is "Sales Order" and docstatus is 1 (submitted)
			submitted_sales_orders = frappe.db.sql(f"""
				SELECT DISTINCT st.parent as sales_order_name
				FROM `tabSales Team` st
				INNER JOIN `tabSales Order` so ON so.name = st.parent
				WHERE st.sales_person = %(sales_person)s
				AND st.parenttype = 'Sales Order'
				AND so.docstatus = 1
				{date_conditions}
			""", {"sales_person": sales_person, **date_params}, as_dict=True)
			
			summary["sales_order_count"] = len(submitted_sales_orders)
			
			# -----------------------
			# Sales Orders Count (Draft/Non-submitted - docstatus = 0)
			# -----------------------
			draft_sales_orders = frappe.db.sql(f"""
				SELECT DISTINCT st.parent as sales_order_name
				FROM `tabSales Team` st
				INNER JOIN `tabSales Order` so ON so.name = st.parent
				WHERE st.sales_person = %(sales_person)s
				AND st.parenttype = 'Sales Order'
				AND so.docstatus = 0
				{date_conditions}
			""", {"sales_person": sales_person, **date_params}, as_dict=True)
			
			summary["draft_sales_order_count"] = len(draft_sales_orders)
			summary["total_sales_order_count"] = summary["sales_order_count"] + summary["draft_sales_order_count"]
			
			# -----------------------
			# Sales Orders Total Amount (Submitted)
			# -----------------------
			# Get total allocated amount from Sales Team for submitted orders
			sales_order_total = frappe.db.sql(f"""
				SELECT 
					SUM(st.allocated_amount) as total_allocated_amount,
					SUM(so.grand_total) as total_grand_total
				FROM `tabSales Team` st
				INNER JOIN `tabSales Order` so ON so.name = st.parent
				WHERE st.sales_person = %(sales_person)s
				AND st.parenttype = 'Sales Order'
				AND so.docstatus = 1
				{date_conditions}
			""", {"sales_person": sales_person, **date_params}, as_dict=True)
			
			summary["total_sales_order_amount"] = flt(sales_order_total[0]["total_allocated_amount"]) if sales_order_total and sales_order_total[0]["total_allocated_amount"] else 0
			summary["total_sales_order_grand_total"] = flt(sales_order_total[0]["total_grand_total"]) if sales_order_total and sales_order_total[0]["total_grand_total"] else 0
			
			# -----------------------
			# Sales Invoices Count (Submitted - docstatus = 1)
			# -----------------------
			submitted_sales_invoices = frappe.db.sql(f"""
				SELECT DISTINCT st.parent as sales_invoice_name
				FROM `tabSales Team` st
				INNER JOIN `tabSales Invoice` si ON si.name = st.parent
				WHERE st.sales_person = %(sales_person)s
				AND st.parenttype = 'Sales Invoice'
				AND si.docstatus = 1
				{invoice_date_conditions}
			""", {"sales_person": sales_person, **invoice_date_params}, as_dict=True)
			
			summary["sales_invoice_count"] = len(submitted_sales_invoices)
			
			# -----------------------
			# Sales Invoices Count (Draft/Non-submitted - docstatus = 0)
			# -----------------------
			draft_sales_invoices = frappe.db.sql(f"""
				SELECT DISTINCT st.parent as sales_invoice_name
				FROM `tabSales Team` st
				INNER JOIN `tabSales Invoice` si ON si.name = st.parent
				WHERE st.sales_person = %(sales_person)s
				AND st.parenttype = 'Sales Invoice'
				AND si.docstatus = 0
				{invoice_date_conditions}
			""", {"sales_person": sales_person, **invoice_date_params}, as_dict=True)
			
			summary["draft_sales_invoice_count"] = len(draft_sales_invoices)
			summary["total_sales_invoice_count"] = summary["sales_invoice_count"] + summary["draft_sales_invoice_count"]
			
			# -----------------------
			# Sales Invoices Total Amount (Submitted)
			# -----------------------
			# Get total allocated amount and grand total from Sales Team for submitted invoices
			sales_invoice_total = frappe.db.sql(f"""
				SELECT 
					SUM(st.allocated_amount) as total_allocated_amount,
					SUM(si.grand_total) as total_grand_total
				FROM `tabSales Team` st
				INNER JOIN `tabSales Invoice` si ON si.name = st.parent
				WHERE st.sales_person = %(sales_person)s
				AND st.parenttype = 'Sales Invoice'
				AND si.docstatus = 1
				{invoice_date_conditions}
			""", {"sales_person": sales_person, **invoice_date_params}, as_dict=True)
			
			summary["total_sales_amount"] = flt(sales_invoice_total[0]["total_allocated_amount"]) if sales_invoice_total and sales_invoice_total[0]["total_allocated_amount"] else 0
			summary["total_sales_invoice_grand_total"] = flt(sales_invoice_total[0]["total_grand_total"]) if sales_invoice_total and sales_invoice_total[0]["total_grand_total"] else 0
			
			# -----------------------
			# Outstanding Amount
			# -----------------------
			# Calculate outstanding amount from submitted sales invoices
			outstanding_result = frappe.db.sql(f"""
				SELECT SUM(si.outstanding_amount) as total_outstanding
				FROM `tabSales Invoice` si
				WHERE si.docstatus = 1
				AND si.name IN (
					SELECT DISTINCT st.parent
					FROM `tabSales Team` st
					WHERE st.sales_person = %(sales_person)s
					AND st.parenttype = 'Sales Invoice'
				)
				{invoice_date_conditions}
			""", {"sales_person": sales_person, **invoice_date_params}, as_dict=True)
			
			summary["outstanding_amount"] = flt(outstanding_result[0]["total_outstanding"]) if outstanding_result and outstanding_result[0]["total_outstanding"] else 0
			
			# # -----------------------
			# # Paid Amount
			# # -----------------------
			# paid_result = frappe.db.sql(f"""
			# 	SELECT SUM(si.paid_amount) as total_paid
			# 	FROM `tabSales Invoice` si
			# 	WHERE si.docstatus = 1
			# 	AND si.name IN (
			# 		SELECT DISTINCT st.parent
			# 		FROM `tabSales Team` st
			# 		WHERE st.sales_person = %(sales_person)s
			# 		AND st.parenttype = 'Sales Invoice'
			# 	)
			# 	{invoice_date_conditions}
			# """, {"sales_person": sales_person, **invoice_date_params}, as_dict=True)
			
			# summary["paid_amount"] = flt(paid_result[0]["total_paid"]) if paid_result and paid_result[0]["total_paid"] else 0
			
			# -----------------------
			# Paid Amount
			# -----------------------
			# Payment Entry references are stored in tabPayment Entry Reference child table
			# We need to join Payment Entry with Payment Entry Reference to get the allocated amounts
			paid_date_conditions = ""
			paid_date_params = {}
			if from_date:
				paid_date_conditions += " AND pe.posting_date >= %(from_date)s"
				paid_date_params["from_date"] = from_date
			if to_date:
				paid_date_conditions += " AND pe.posting_date <= %(to_date)s"
				paid_date_params["to_date"] = to_date
			
			paid_result = frappe.db.sql(f"""
				SELECT SUM(per.allocated_amount) as total_paid
				FROM `tabPayment Entry` pe
				INNER JOIN `tabPayment Entry Reference` per ON pe.name = per.parent
				WHERE per.reference_doctype = 'Sales Invoice'
				AND per.reference_name IN (
					SELECT DISTINCT st.parent
					FROM `tabSales Team` st
					WHERE st.sales_person = %(sales_person)s
					AND st.parenttype = 'Sales Invoice'
				)
				AND pe.docstatus = 1
				{paid_date_conditions}
			""", {"sales_person": sales_person, **paid_date_params}, as_dict=True)

			summary["paid_amount"] = flt(paid_result[0]["total_paid"]) if paid_result and paid_result[0]["total_paid"] else 0

			# -----------------------
			# Unique Customers Handled
			# -----------------------
			# Get unique customers from both Sales Orders and Sales Invoices
			customers_from_orders = frappe.db.sql(f"""
				SELECT DISTINCT so.customer
				FROM `tabSales Order` so
				WHERE so.name IN (
					SELECT DISTINCT st.parent
					FROM `tabSales Team` st
					WHERE st.sales_person = %(sales_person)s
					AND st.parenttype = 'Sales Order'
				)
				AND so.customer IS NOT NULL
				{date_conditions}
			""", {"sales_person": sales_person, **date_params}, as_dict=True)
			
			customers_from_invoices = frappe.db.sql(f"""
				SELECT DISTINCT si.customer
				FROM `tabSales Invoice` si
				WHERE si.name IN (
					SELECT DISTINCT st.parent
					FROM `tabSales Team` st
					WHERE st.sales_person = %(sales_person)s
					AND st.parenttype = 'Sales Invoice'
				)
				AND si.customer IS NOT NULL
				{invoice_date_conditions}
			""", {"sales_person": sales_person, **invoice_date_params}, as_dict=True)
			
			# Combine and get unique customers
			all_customers = set()
			for cust in customers_from_orders:
				if cust.get("customer"):
					all_customers.add(cust["customer"])
			for cust in customers_from_invoices:
				if cust.get("customer"):
					all_customers.add(cust["customer"])
			
			summary["unique_customers"] = len(all_customers)
			
			# -----------------------
			# Average Order Value
			# -----------------------
			if summary["sales_order_count"] > 0:
				summary["average_order_value"] = summary["total_sales_order_amount"] / summary["sales_order_count"]
			else:
				summary["average_order_value"] = 0
			
			# -----------------------
			# Average Invoice Value
			# -----------------------
			if summary["sales_invoice_count"] > 0:
				summary["average_invoice_value"] = summary["total_sales_amount"] / summary["sales_invoice_count"]
			else:
				summary["average_invoice_value"] = 0
			
			# -----------------------
			# Conversion Rate (Invoices / Orders)
			# -----------------------
			if summary["sales_order_count"] > 0:
				summary["conversion_rate"] = (summary["sales_invoice_count"] / summary["sales_order_count"]) * 100
			else:
				summary["conversion_rate"] = 0
			
			# -----------------------
			# Payment Status Breakdown
			# -----------------------
			payment_status = frappe.db.sql(f"""
				SELECT 
					si.status,
					COUNT(*) as count,
					SUM(si.grand_total) as total_amount
				FROM `tabSales Invoice` si
				WHERE si.docstatus = 1
				AND si.name IN (
					SELECT DISTINCT st.parent
					FROM `tabSales Team` st
					WHERE st.sales_person = %(sales_person)s
					AND st.parenttype = 'Sales Invoice'
				)
				{invoice_date_conditions}
				GROUP BY si.status
			""", {"sales_person": sales_person, **invoice_date_params}, as_dict=True)
			
			summary["payment_status_breakdown"] = payment_status
			
			# -----------------------
			# Sales Order Status Breakdown
			# -----------------------
			order_status = frappe.db.sql(f"""
				SELECT 
					so.status,
					COUNT(*) as count,
					SUM(so.grand_total) as total_amount
				FROM `tabSales Order` so
				WHERE so.name IN (
					SELECT DISTINCT st.parent
					FROM `tabSales Team` st
					WHERE st.sales_person = %(sales_person)s
					AND st.parenttype = 'Sales Order'
				)
				{date_conditions}
				GROUP BY so.status
			""", {"sales_person": sales_person, **date_params}, as_dict=True)
			
			summary["sales_order_status_breakdown"] = order_status
			
			# -----------------------
			# Recent Activity (Last 5 Sales Orders and Invoices)
			# -----------------------
			recent_orders = frappe.db.sql(f"""
				SELECT 
					so.name,
					so.customer,
					so.customer_name,
					so.transaction_date,
					so.grand_total,
					so.status,
					so.docstatus
				FROM `tabSales Order` so
				WHERE so.name IN (
					SELECT DISTINCT st.parent
					FROM `tabSales Team` st
					WHERE st.sales_person = %(sales_person)s
					AND st.parenttype = 'Sales Order'
				)
				{date_conditions}
				ORDER BY so.modified DESC
				LIMIT 5
			""", {"sales_person": sales_person, **date_params}, as_dict=True)
			
			recent_invoices = frappe.db.sql(f"""
				SELECT 
					si.name,
					si.customer,
					si.customer_name,
					si.posting_date,
					si.grand_total,
					si.status,
					si.outstanding_amount,
					si.docstatus
				FROM `tabSales Invoice` si
				WHERE si.name IN (
					SELECT DISTINCT st.parent
					FROM `tabSales Team` st
					WHERE st.sales_person = %(sales_person)s
					AND st.parenttype = 'Sales Invoice'
				)
				{invoice_date_conditions}
				ORDER BY si.modified DESC
				LIMIT 5
			""", {"sales_person": sales_person, **invoice_date_params}, as_dict=True)
			
			summary["recent_orders"] = recent_orders
			summary["recent_invoices"] = recent_invoices
			
			# -----------------------
			# Get Sales Person Details
			# -----------------------
			sales_person_doc = frappe.get_doc(self.doctype, sales_person)
			summary["sales_person_name"] = sales_person_doc.sales_person_name
			summary["employee"] = sales_person_doc.employee
			summary["department"] = sales_person_doc.department
			summary["enabled"] = sales_person_doc.enabled
			summary["is_group"] = sales_person_doc.is_group
			summary["commission_rate"] = sales_person_doc.commission_rate
			
			# -----------------------
			# Total Commission Earned (if available)
			# -----------------------
			# Calculate from incentives in Sales Team
			# Note: Commission is linked to parent documents, so we need to filter by parent dates
			commission_date_conditions = ""
			commission_date_params = {}
			if from_date or to_date:
				conditions = []
				if from_date:
					conditions.append("""
						((st.parenttype = 'Sales Order' AND EXISTS (
							SELECT 1 FROM `tabSales Order` so 
							WHERE so.name = st.parent AND so.transaction_date >= %(from_date)s
						))
						OR (st.parenttype = 'Sales Invoice' AND EXISTS (
							SELECT 1 FROM `tabSales Invoice` si 
							WHERE si.name = st.parent AND si.posting_date >= %(from_date)s
						)))
					""")
					commission_date_params["from_date"] = from_date
				if to_date:
					conditions.append("""
						((st.parenttype = 'Sales Order' AND EXISTS (
							SELECT 1 FROM `tabSales Order` so 
							WHERE so.name = st.parent AND so.transaction_date <= %(to_date)s
						))
						OR (st.parenttype = 'Sales Invoice' AND EXISTS (
							SELECT 1 FROM `tabSales Invoice` si 
							WHERE si.name = st.parent AND si.posting_date <= %(to_date)s
						)))
					""")
					commission_date_params["to_date"] = to_date
				if conditions:
					commission_date_conditions = " AND " + " AND ".join(conditions)
			
			commission_result = frappe.db.sql(f"""
				SELECT SUM(st.incentives) as total_incentives
				FROM `tabSales Team` st
				WHERE st.sales_person = %(sales_person)s
				AND st.incentives IS NOT NULL
				AND st.incentives > 0
				{commission_date_conditions}
			""", {"sales_person": sales_person, **commission_date_params}, as_dict=True)
			
			summary["total_commission_earned"] = flt(commission_result[0]["total_incentives"]) if commission_result and commission_result[0]["total_incentives"] else 0
			
			# Add date range info to summary
			if from_date or to_date:
				summary["date_range"] = {
					"from_date": from_date,
					"to_date": to_date
				}
			
			return {
				"status": "success",
				"sales_person": sales_person,
				"summary": summary
			}
			
		except Exception as e:
			frappe.logger().error(f"Get sales person summary error: {str(e)}")
			frappe.log_error(title="Sales Person Summary Error", message=frappe.get_traceback())
			return {
				"status": "error",
				"message": f"Failed to get sales person summary: {str(e)}"
			}
	
	def get_all_sales_persons_summary(self, from_date=None, to_date=None, filters=None):
		"""
		Get comprehensive summary for all sales persons.
		Returns data in a table format suitable for display.
		
		Args:
			from_date: Optional start date for filtering (YYYY-MM-DD format)
			to_date: Optional end date for filtering (YYYY-MM-DD format)
			filters: Optional filters for sales persons (e.g., {"enabled": 1})
		
		Returns:
			dict: Table data with all sales persons and their summaries
		"""
		try:
			# Get all sales persons
			conditions = []
			values = {}
			
			# Apply filters if provided
			if filters:
				for field, value in filters.items():
					if value is not None and value != "":
						conditions.append(f"`{field}` = %({field})s")
						values[field] = value
			
			where_clause = " AND ".join(conditions) if conditions else "1=1"
			
			# Get all enabled sales persons (exclude groups by default, or include if filter specifies)
			sales_persons = frappe.db.sql(f"""
				SELECT 
					name,
					sales_person_name,
					employee,
					department,
					enabled,
					is_group
				FROM `tab{self.doctype}`
				WHERE {where_clause}
				ORDER BY sales_person_name ASC
			""", values, as_dict=True)
			
			if not sales_persons:
				return {
					"status": "success",
					"count": 0,
					"table_data": [],
					"from_date": from_date,
					"to_date": to_date
				}
			
			# Get summary for each sales person
			table_data = []
			for sp in sales_persons:
				# Skip group nodes if not explicitly requested
				if sp.get("is_group") and (not filters or not filters.get("is_group")):
					continue
				
				# Get summary for this sales person
				summary_result = self.get_sales_person_summary(sp["name"], from_date=from_date, to_date=to_date)
				
				if summary_result.get("status") == "success":
					summary = summary_result.get("summary", {})
					
					# Create table row
					row = {
						"sales_person": sp["name"],
						"sales_person_name": summary.get("sales_person_name") or sp["sales_person_name"],
						"employee": summary.get("employee") or sp.get("employee"),
						"department": summary.get("department") or sp.get("department"),
						"enabled": summary.get("enabled", sp.get("enabled", 0)),
						
						# Sales Orders
						"sales_order_count": summary.get("sales_order_count", 0),
						"draft_sales_order_count": summary.get("draft_sales_order_count", 0),
						"total_sales_order_count": summary.get("total_sales_order_count", 0),
						"total_sales_order_amount": summary.get("total_sales_order_amount", 0),
						
						# Sales Invoices
						"sales_invoice_count": summary.get("sales_invoice_count", 0),
						"draft_sales_invoice_count": summary.get("draft_sales_invoice_count", 0),
						"total_sales_invoice_count": summary.get("total_sales_invoice_count", 0),
						"total_sales_amount": summary.get("total_sales_amount", 0),
						
						# Financial
						"outstanding_amount": summary.get("outstanding_amount", 0),
						"paid_amount": summary.get("paid_amount", 0),
						"total_commission_earned": summary.get("total_commission_earned", 0),
						
						# Performance
						"unique_customers": summary.get("unique_customers", 0),
						"average_order_value": summary.get("average_order_value", 0),
						"average_invoice_value": summary.get("average_invoice_value", 0),
						"conversion_rate": summary.get("conversion_rate", 0),
					}
					
					table_data.append(row)
			
			return {
				"status": "success",
				"count": len(table_data),
				"table_data": table_data,
				"from_date": from_date,
				"to_date": to_date
			}
			
		except Exception as e:
			frappe.logger().error(f"Get all sales persons summary error: {str(e)}")
			frappe.log_error(title="All Sales Persons Summary Error", message=frappe.get_traceback())
			return {
				"status": "error",
				"message": f"Failed to get all sales persons summary: {str(e)}"
			}

