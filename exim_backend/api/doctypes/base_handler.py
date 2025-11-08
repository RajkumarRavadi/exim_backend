"""
Base handler class for all DocType handlers.
All doctype handlers should inherit from this class.
"""

import frappe


class BaseDocTypeHandler:
	"""
	Base class for all doctype handlers.
	Provides common functionality and defines the interface.
	"""
	
	def __init__(self):
		self.doctype = None  # Should be set by subclasses
		self.label = None  # Human-readable name
	
	def get_fields_info(self):
		"""
		Get field information for this doctype.
		Returns: Dict with fields, child_tables, etc.
		"""
		try:
			if not frappe.db.exists("DocType", self.doctype):
				return {
					"status": "error",
					"message": f"DocType '{self.doctype}' does not exist"
				}
			
			meta = frappe.get_meta(self.doctype)
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
				
				# Handle child tables
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
			
			return {
				"status": "success",
				"doctype": self.doctype,
				"fields": fields_info,
				"child_tables": child_tables,
				"total_fields": len(fields_info)
			}
		except Exception as e:
			frappe.logger().error(f"Get fields info error for {self.doctype}: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get fields info: {str(e)}"
			}
	
	def build_field_reference(self, fields_info):
		"""
		Build a concise field reference string for AI prompt.
		"""
		if fields_info.get("status") != "success":
			return "Fields metadata not available"
		
		fields = fields_info.get("fields", [])
		return "\n".join([
			f"- {f['fieldname']} ({f['fieldtype']}){' [required]' if f.get('reqd') else ''}"
			for f in fields
			if not f.get('hidden') and f['fieldtype'] not in ['Section Break', 'Column Break', 'Tab Break']
		])
	
	def prepare_document_data(self, fields):
		"""
		Prepare document data for creation.
		Override in subclasses for doctype-specific logic.
		
		Args:
			fields: Dict of field values
		Returns:
			Prepared fields dict
		"""
		return fields
	
	def create_document(self, fields):
		"""
		Create a document of this doctype.
		Override in subclasses for custom creation logic.
		
		Args:
			fields: Dict of field values
		Returns:
			Created document dict
		"""
		try:
			prepared_fields = self.prepare_document_data(fields)
			doc = frappe.get_doc({
				"doctype": self.doctype,
				**prepared_fields
			})
			doc.insert(ignore_permissions=True)
			
			return {
				"status": "success",
				"message": f"{self.label} created successfully",
				"name": doc.name,
				"doctype": self.doctype
			}
		except Exception as e:
			frappe.logger().error(f"Create {self.doctype} error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to create {self.label}: {str(e)}"
			}
	
	def dynamic_search(self, filters, limit=20, order_by="modified desc"):
		"""
		Perform dynamic search on this doctype.
		Override in subclasses for custom search logic.
		
		Args:
			filters: Dict of filter conditions
			limit: Max results
			order_by: Order by clause
		Returns:
			Search results
		"""
		try:
			# Build WHERE clause dynamically
			conditions = []
			values = {}
			
			for field, value in filters.items():
				if value is None or value == "":
					continue
				
				if isinstance(value, dict):
					# Handle operators
					for operator, op_value in value.items():
						if operator == "$like":
							conditions.append(f"`{field}` LIKE %({field})s")
							values[field] = op_value
						elif operator == "$is_null":
							conditions.append(f"(`{field}` IS NULL OR `{field}` = '' OR `{field}` = 'Not Set')")
						elif operator == "$is_not_null":
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
					conditions.append(f"`{field}` = %({field})s")
					values[field] = value
			
			where_clause = " AND ".join(conditions) if conditions else "1=1"
			
			# Get fields to select (override in subclasses)
			select_fields = self.get_search_fields()
			
			query = f"""
				SELECT {select_fields}
				FROM `tab{self.doctype}`
				WHERE {where_clause}
				ORDER BY {order_by}
				LIMIT %(limit)s
			"""
			
			values["limit"] = limit
			
			results = frappe.db.sql(query, values, as_dict=True)
			
			return {
				"status": "success",
				"count": len(results),
				"results": results,
				"filters_applied": filters
			}
		except Exception as e:
			frappe.logger().error(f"Dynamic search error for {self.doctype}: {str(e)}")
			return {
				"status": "error",
				"message": f"Search failed: {str(e)}"
			}
	
	def get_search_fields(self):
		"""
		Get fields to include in search results.
		Override in subclasses to specify which fields to return.
		"""
		return "name, *"  # Default: all fields
	
	def count_documents(self, filters=None):
		"""
		Count documents with optional filters.
		Override in subclasses for custom counting logic.
		
		Args:
			filters: Optional filter dict
		Returns:
			Count result
		"""
		try:
			if filters:
				# Use dynamic_search to count
				result = self.dynamic_search(filters, limit=10000)
				return {
					"status": "success",
					"total_count": result.get("count", 0)
				}
			else:
				total = frappe.db.count(self.doctype)
				return {
					"status": "success",
					"total_count": total
				}
		except Exception as e:
			frappe.logger().error(f"Count error for {self.doctype}: {str(e)}")
			return {
				"status": "error",
				"message": f"Count failed: {str(e)}"
			}
	
	def get_document_details(self, name):
		"""
		Get detailed information for a specific document.
		Override in subclasses for custom detail retrieval.
		
		Args:
			name: Document name/ID
		Returns:
			Document details
		"""
		try:
			if not frappe.db.exists(self.doctype, name):
				return {
					"status": "error",
					"message": f"{self.label} '{name}' not found"
				}
			
			doc = frappe.get_doc(self.doctype, name)
			return {
				"status": "success",
				"document": doc.as_dict()
			}
		except Exception as e:
			frappe.logger().error(f"Get details error for {self.doctype}: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get details: {str(e)}"
			}

