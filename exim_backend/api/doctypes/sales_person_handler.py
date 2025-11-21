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

