"""
Base handler class for all DocType handlers.
All doctype handlers should inherit from this class.
"""

import frappe
from frappe.utils import getdate, today, formatdate, get_first_day_of_week
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
		
		frappe.logger().info(f"Normalizing date value: '{value}' -> '{value_str}' (field: {field_name})")
		
		# Handle special date keywords
		if value_str == 'today':
			if field_name in ['creation', 'modified']:
				# For datetime fields, return start of today as datetime
				from frappe.utils import get_datetime, now_datetime
				from datetime import time as dt_time
				today_dt = getdate()
				today_start = get_datetime(today_dt).replace(hour=0, minute=0, second=0, microsecond=0)
				result = frappe.db.format_datetime(today_start)
				frappe.logger().info(f"Normalized 'today' to datetime: {result}")
			else:
				# For date fields, return date string
				result = today()
				frappe.logger().info(f"Normalized 'today' to date: {result}")
			return result
		elif value_str == 'yesterday':
			if field_name in ['creation', 'modified']:
				from frappe.utils import get_datetime
				from datetime import time as dt_time
				yesterday_dt = getdate() - timedelta(days=1)
				yesterday_start = get_datetime(yesterday_dt).replace(hour=0, minute=0, second=0, microsecond=0)
				result = frappe.db.format_datetime(yesterday_start)
				frappe.logger().info(f"Normalized 'yesterday' to datetime: {result}")
			else:
				result = formatdate(getdate() - timedelta(days=1))
				frappe.logger().info(f"Normalized 'yesterday' to date: {result}")
			return result
		elif value_str == 'tomorrow':
			if field_name in ['creation', 'modified']:
				from frappe.utils import get_datetime
				from datetime import time as dt_time
				tomorrow_dt = getdate() + timedelta(days=1)
				tomorrow_start = get_datetime(tomorrow_dt).replace(hour=0, minute=0, second=0, microsecond=0)
				result = frappe.db.format_datetime(tomorrow_start)
				frappe.logger().info(f"Normalized 'tomorrow' to datetime: {result}")
			else:
				result = formatdate(getdate() + timedelta(days=1))
				frappe.logger().info(f"Normalized 'tomorrow' to date: {result}")
			return result
		elif value_str in ['this week', 'thisweek']:
			# Start of this week - return as date string for date fields, datetime for datetime fields
			first_day = get_first_day_of_week(today())
			# For datetime fields, return start of day as datetime string
			if field_name in ['creation', 'modified']:
				from frappe.utils import get_datetime
				from datetime import time as dt_time
				first_day_datetime = get_datetime(first_day).replace(hour=0, minute=0, second=0, microsecond=0)
				result = frappe.db.format_datetime(first_day_datetime)
				frappe.logger().info(f"Normalized 'this week' to datetime: {result} (first day of week: {first_day})")
			else:
				# For date fields, return date string
				result = formatdate(first_day)
				frappe.logger().info(f"Normalized 'this week' to date: {result} (first day of week: {first_day})")
			return result
		elif value_str in ['last week', 'lastweek']:
			# Start of last week
			last_week_start = getdate() - timedelta(days=7)
			return formatdate(get_first_day_of_week(last_week_start))
		elif 'days ago' in value_str or 'day ago' in value_str:
			# Handle "7 days ago", "1 day ago", etc.
			try:
				days = int(value_str.split()[0])
				return formatdate(getdate() - timedelta(days=days))
			except:
				pass
		elif 'weeks ago' in value_str or 'week ago' in value_str:
			# Handle "2 weeks ago", "1 week ago", etc.
			try:
				weeks = int(value_str.split()[0])
				return formatdate(getdate() - timedelta(weeks=weeks))
			except:
				pass
		elif 'months ago' in value_str or 'month ago' in value_str:
			# Handle "1 month ago", "2 months ago", etc.
			try:
				months = int(value_str.split()[0])
				# Use timedelta approximation (30 days per month) if relativedelta not available
				try:
					from dateutil.relativedelta import relativedelta
					return formatdate(getdate() - relativedelta(months=months))
				except ImportError:
					# Fallback to approximate using days
					approx_days = months * 30
					return formatdate(getdate() - timedelta(days=approx_days))
			except:
				pass
		elif value_str in ['this month', 'thismonth']:
			# Start of this month
			from datetime import datetime
			current_date = getdate()
			first_day = current_date.replace(day=1)
			return formatdate(first_day)
		
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
				
				# Store original value for special handling of date keywords on datetime fields
				original_value = value
				
				# Normalize date values if this is a date field
				if actual_field in date_fields:
					# For direct value (not operator), normalize it
					if not isinstance(value, dict):
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
							else:
								# If normalization failed, skip this filter
								frappe.logger().warning(f"Date normalization failed for {actual_field} {operator} {op_value}, skipping filter")
								continue
						
						# Create unique parameter name for operators to avoid conflicts
						param_name = f"{actual_field}_{operator}"
						
						if operator == "$like":
							conditions.append(f"`{actual_field}` LIKE %({param_name})s")
							values[param_name] = op_value
						elif operator == "$is_null":
							conditions.append(f"(`{actual_field}` IS NULL OR `{actual_field}` = '' OR `{actual_field}` = 'Not Set')")
						elif operator == "$is_not_null":
							conditions.append(f"(`{actual_field}` IS NOT NULL AND `{actual_field}` != '' AND `{actual_field}` != 'Not Set')")
						elif operator == "$gte":
							# For datetime fields (creation, modified), compare as datetime (no DATE() wrapper)
							# For date fields, use DATE() function for date-only comparison
							if actual_field in ['creation', 'modified']:
								# Datetime fields: compare full datetime (no DATE() wrapper)
								conditions.append(f"`{actual_field}` >= %({param_name})s")
							else:
								# Date fields: use DATE() for date-only comparison
								conditions.append(f"DATE(`{actual_field}`) >= DATE(%({param_name})s)")
							values[param_name] = op_value
							original_value = value.get(operator, op_value) if isinstance(value, dict) else op_value
							frappe.logger().info(f"Date filter: {actual_field} >= {op_value} (normalized from '{original_value}')")
						elif operator == "$lte":
							if actual_field in ['creation', 'modified']:
								# Datetime fields: compare full datetime
								conditions.append(f"`{actual_field}` <= %({param_name})s")
							else:
								# Date fields: use DATE() for date-only comparison
								conditions.append(f"DATE(`{actual_field}`) <= DATE(%({param_name})s)")
							values[param_name] = op_value
							original_value = value.get(operator, op_value) if isinstance(value, dict) else op_value
							frappe.logger().info(f"Date filter: {actual_field} <= {op_value} (normalized from '{original_value}')")
						elif operator == "$in":
							placeholders = ", ".join([f"%({actual_field}_{i})s" for i in range(len(op_value))])
							conditions.append(f"`{actual_field}` IN ({placeholders})")
							for i, v in enumerate(op_value):
								values[f"{actual_field}_{i}"] = v
				else:
					# For direct value comparison (not operator)
					if actual_field in date_fields:
						if actual_field in ['creation', 'modified']:
							# Datetime fields: for "today", "yesterday", "tomorrow", use range (start of day to end of day)
							# For other values, use direct comparison
							# Check original value (before normalization) for date keywords
							original_value_str = str(original_value).strip().lower() if not isinstance(original_value, dict) else None
							if original_value_str in ['today', 'yesterday', 'tomorrow']:
								# For date keywords on datetime fields, use range: >= start of day AND < start of next day
								from frappe.utils import get_datetime
								from datetime import timedelta
								
								# Calculate the target date
								if original_value_str == 'today':
									target_dt = getdate()
								elif original_value_str == 'yesterday':
									target_dt = getdate() - timedelta(days=1)
								elif original_value_str == 'tomorrow':
									target_dt = getdate() + timedelta(days=1)
								
								# Get start of target day and start of next day
								target_start = get_datetime(target_dt).replace(hour=0, minute=0, second=0, microsecond=0)
								next_day_start = target_start + timedelta(days=1)
								target_start_str = frappe.db.format_datetime(target_start)
								next_day_start_str = frappe.db.format_datetime(next_day_start)
								
								conditions.append(f"`{actual_field}` >= %({actual_field}_start)s AND `{actual_field}` < %({actual_field}_end)s")
								values[f"{actual_field}_start"] = target_start_str
								values[f"{actual_field}_end"] = next_day_start_str
								frappe.logger().info(f"Date filter '{original_value_str}' for datetime field {actual_field}: {target_start_str} to {next_day_start_str}")
							else:
								# For other datetime values, use direct comparison
								conditions.append(f"`{actual_field}` = %({actual_field})s")
								values[actual_field] = value
						else:
							# Date fields: use DATE() function for date-only comparison
							conditions.append(f"DATE(`{actual_field}`) = DATE(%({actual_field})s)")
							values[actual_field] = value
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
			
			# Log the query for debugging
			frappe.logger().info(f"Dynamic search query for {self.doctype}: {query}")
			frappe.logger().info(f"Query values: {values}")
			frappe.logger().info(f"Filters received: {filters}")
			
			results = frappe.db.sql(query, values, as_dict=True)
			
			frappe.logger().info(f"Query returned {len(results)} results")
			
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

