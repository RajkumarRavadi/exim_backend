"""
Base handler class for all DocType handlers.
All doctype handlers should inherit from this class.
"""

import frappe
from frappe.utils import getdate, today, formatdate
from frappe.utils.dateutils import parse_date
from datetime import datetime, timedelta


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
	
	def normalize_date_value(self, value, field_name):
		"""
		Normalize date values to YYYY-MM-DD format.
		Handles special values like 'today', 'yesterday', and various date formats.
		"""
		if not value or value == "":
			return None
		
		value_str = str(value).strip().lower()
		
		# Handle special date keywords
		if value_str == 'today':
			return today()
		elif value_str == 'yesterday':
			return formatdate(getdate() - timedelta(days=1))
		elif value_str == 'tomorrow':
			return formatdate(getdate() + timedelta(days=1))
		
		# Try to parse the date using Frappe's date parsing
		try:
			# Frappe's parse_date handles multiple formats
			parsed_date = parse_date(value_str)
			return parsed_date
		except:
			# If Frappe parsing fails, try manual parsing
			try:
				# Try common formats: DD-MM-YYYY, YYYY-MM-DD, MM/DD/YYYY, etc.
				date_formats = [
					'%d-%m-%Y',  # 08-11-2025
					'%Y-%m-%d',  # 2025-11-08
					'%d/%m/%Y',  # 08/11/2025
					'%Y/%m/%d',  # 2025/11/08
					'%m-%d-%Y',  # 11-08-2025
					'%m/%d/%Y',  # 11/08/2025
				]
				
				for fmt in date_formats:
					try:
						parsed = datetime.strptime(value_str, fmt)
						return parsed.strftime('%Y-%m-%d')
					except:
						continue
				
				# If all parsing fails, return as-is (might be a datetime string)
				return value_str
			except:
				return value_str
	
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
			# Map common field names to actual field names
			field_mapping = {
				'created': 'creation',
				'created_date': 'creation',
				'date': 'transaction_date',
				'order_date': 'transaction_date',
			}
			
			# Build WHERE clause dynamically
			conditions = []
			values = {}
			
			# Get date fields for this doctype (to normalize date values)
			date_fields = self.get_date_fields()
			
			for field, value in filters.items():
				if value is None or value == "":
					continue
				
				# Map field name if needed
				actual_field = field_mapping.get(field, field)
				
				# Normalize date values if this is a date field
				if actual_field in date_fields:
					normalized_value = self.normalize_date_value(value, actual_field)
					if normalized_value:
						value = normalized_value
				
				if isinstance(value, dict):
					# Handle operators
					for operator, op_value in value.items():
						# Normalize date values in operators too
						if actual_field in date_fields:
							normalized_op_value = self.normalize_date_value(op_value, actual_field)
							if normalized_op_value:
								op_value = normalized_op_value
						
						if operator == "$like":
							conditions.append(f"`{actual_field}` LIKE %({actual_field})s")
							values[actual_field] = op_value
						elif operator == "$is_null":
							conditions.append(f"(`{actual_field}` IS NULL OR `{actual_field}` = '' OR `{actual_field}` = 'Not Set')")
						elif operator == "$is_not_null":
							conditions.append(f"(`{actual_field}` IS NOT NULL AND `{actual_field}` != '' AND `{actual_field}` != 'Not Set')")
						elif operator == "$gte":
							conditions.append(f"DATE(`{actual_field}`) >= DATE(%({actual_field})s)")
							values[actual_field] = op_value
						elif operator == "$lte":
							conditions.append(f"DATE(`{actual_field}`) <= DATE(%({actual_field})s)")
							values[actual_field] = op_value
						elif operator == "$in":
							placeholders = ", ".join([f"%({actual_field}_{i})s" for i in range(len(op_value))])
							conditions.append(f"`{actual_field}` IN ({placeholders})")
							for i, v in enumerate(op_value):
								values[f"{actual_field}_{i}"] = v
				else:
					# For date fields, use DATE() function for comparison
					if actual_field in date_fields:
						conditions.append(f"DATE(`{actual_field}`) = DATE(%({actual_field})s)")
					else:
						conditions.append(f"`{actual_field}` = %({actual_field})s")
					values[actual_field] = value
			
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
	
	def get_date_fields(self):
		"""
		Get list of date/datetime fields for this doctype.
		Override in subclasses to specify date fields.
		"""
		return ['creation', 'modified']
	
	def get_search_fields(self):
		"""
		Get fields to include in search results.
		Override in subclasses to specify which fields to return.
		"""
		return "name, *"  # Default: all fields
	
	def count_documents(self, filters=None):
		"""
		Count documents with optional filters.
		When count is small (<= 5), also return document names for context.
		Override in subclasses for custom counting logic.
		
		Args:
			filters: Optional filter dict
		Returns:
			Count result with document names if count is small
		"""
		try:
			if filters:
				# Use dynamic_search to count and get results
				result = self.dynamic_search(filters, limit=10000)
				count = result.get("count", 0)
				results = result.get("results", [])
				
				response = {
					"status": "success",
					"total_count": count
				}
				
				# If count is small (<= 5), include document names for context
				if count > 0 and count <= 5 and results:
					document_names = [r.get("name") for r in results if r.get("name")]
					if document_names:
						response["document_names"] = document_names
						# Also include first result for more context
						if len(results) == 1:
							response["first_result"] = results[0]
				
				return response
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

