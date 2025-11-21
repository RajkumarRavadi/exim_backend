"""
Customer DocType handler.
Contains all customer-specific logic and operations.
"""

import frappe
import json
from exim_backend.api.doctypes.base_handler import BaseDocTypeHandler


class CustomerHandler(BaseDocTypeHandler):
	"""Handler for Customer doctype operations."""
	
	def __init__(self):
		super().__init__()
		self.doctype = "Customer"
		self.label = "Customer"
	
	def get_search_fields(self):
		"""Get fields to include in customer search results."""
		return """
			name,
			customer_name,
			customer_type,
			mobile_no,
			email_id,
			customer_primary_contact,
			territory,
			customer_group,
			default_currency,
			default_price_list,
			payment_terms,
			creation,
			modified
		"""
	
	def prepare_document_data(self, fields):
		"""Prepare customer data with required fields and defaults."""
		# Set defaults for required fields
		if not fields.get("customer_type"):
			fields["customer_type"] = "Individual" if not fields.get("company") else "Company"
		
		if not fields.get("customer_group"):
			fields["customer_group"] = frappe.db.get_single_value("Selling Settings", "customer_group") or "Individual"
		
		if not fields.get("territory"):
			fields["territory"] = frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
		
		# Set default currency if not provided
		if not fields.get("default_currency"):
			fields["default_currency"] = frappe.db.get_single_value("System Settings", "currency") or "USD"
		
		# Map common field names
		field_mapping = {
			"email": "email_id",
			"phone": "mobile_no",
			"mobile": "mobile_no",
			"contact": "customer_primary_contact",
			"primary_contact": "customer_primary_contact"
		}
		
		for old_key, new_key in field_mapping.items():
			if old_key in fields and new_key not in fields:
				fields[new_key] = fields.pop(old_key)
		
		# Remove address fields from customer data (handled separately)
		address_fields = ["address_line1", "address_line2", "city", "state", "country", "pincode"]
		customer_fields = {k: v for k, v in fields.items() if k not in address_fields}
		
		return customer_fields
	
	def create_document(self, fields):
		"""Create customer with address if provided."""
		try:
			prepared_fields = self.prepare_document_data(fields)
			
			# Extract address fields before creating customer
			address_fields = {}
			address_mapping = {
				"address_line1": "address_line1",
				"address_line2": "address_line2",
				"city": "city",
				"state": "state",
				"country": "country",
				"pincode": "pincode"
			}
			
			for old_key, new_key in address_mapping.items():
				if old_key in fields:
					address_fields[new_key] = fields[old_key]
			
			# Create customer
			doc = frappe.get_doc({
				"doctype": self.doctype,
				**prepared_fields
			})
			doc.insert(ignore_permissions=True)
			
			# Commit to ensure document is saved
			frappe.db.commit()
			
			# Create address if provided
			if address_fields:
				self.create_customer_address(doc.name, address_fields)
				frappe.db.commit()
			
			return {
				"status": "success",
				"message": f"{self.label} '{doc.customer_name}' created successfully",
				"name": doc.name,
				"doctype": self.doctype
			}
		except Exception as e:
			frappe.logger().error(f"Create {self.doctype} error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to create {self.label}: {str(e)}"
			}
	
	def create_customer_address(self, customer_name, address_fields):
		"""Create address for customer."""
		try:
			address = frappe.get_doc({
				"doctype": "Address",
				**address_fields,
				"links": [{
					"link_doctype": "Customer",
					"link_name": customer_name
				}]
			})
			address.insert(ignore_permissions=True)
			frappe.logger().info(f"Created address {address.name} for customer {customer_name}")
		except Exception as e:
			frappe.logger().error(f"Failed to create address: {str(e)}")
	
	def get_document_details(self, name):
		"""Get detailed customer information including address and contacts."""
		try:
			if not frappe.db.exists(self.doctype, name):
				return {
					"status": "error",
					"message": f"{self.label} '{name}' not found"
				}
			
			doc = frappe.get_doc(self.doctype, name)
			customer_data = doc.as_dict()
			
			# Get primary address (with error handling)
			address = None
			try:
				# Check if Address DocType exists and has link_doctype and link_name fields
				if frappe.db.exists("DocType", "Address"):
					address_meta = frappe.get_meta("Address")
					has_link_fields = any(f.fieldname == "link_doctype" for f in address_meta.fields) and \
									  any(f.fieldname == "link_name" for f in address_meta.fields)
					
					if has_link_fields:
						try:
							address = frappe.db.get_value(
								"Address",
								{"link_doctype": "Customer", "link_name": name, "is_primary_address": 1},
								["name", "address_line1", "address_line2", "city", "state", "country", "pincode"],
								as_dict=True
							)
							
							if not address:
								# Get any address if no primary
								address = frappe.db.get_value(
									"Address",
									{"link_doctype": "Customer", "link_name": name},
									["name", "address_line1", "address_line2", "city", "state", "country", "pincode"],
									as_dict=True
								)
						except Exception as db_error:
							# Database error (e.g., column doesn't exist)
							frappe.logger().warning(f"Database error fetching address for customer {name}: {str(db_error)}")
							address = None
					else:
						# Address DocType exists but doesn't have link fields
						frappe.logger().warning(f"Address DocType doesn't have link_doctype/link_name fields, skipping address fetch")
				else:
					# Address DocType doesn't exist
					frappe.logger().warning(f"Address DocType doesn't exist, skipping address fetch")
			except Exception as addr_error:
				# Catch any other errors (meta access, etc.)
				frappe.logger().warning(f"Failed to fetch address for customer {name}: {str(addr_error)}")
				address = None
			
			customer_data["address"] = address
			
			# Get sales team
			sales_team = frappe.get_all(
				"Sales Team",
				filters={"parent": name},
				fields=["sales_person", "allocated_percentage"]
			)
			customer_data["sales_team"] = sales_team
			
			return {
				"status": "success",
				"customer": customer_data
			}
		except Exception as e:
			frappe.logger().error(f"Get customer details error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to get details: {str(e)}"
			}
	
	def search_by_query(self, query, limit=10):
		"""
		Search customers by name, email, or mobile.
		Legacy method for backward compatibility.
		"""
		try:
			if not query:
				return {
					"status": "error",
					"message": "Search query is required"
				}
			
			customers = frappe.db.sql("""
				SELECT 
					name,
					customer_name,
					customer_type,
					mobile_no,
					email_id,
					customer_primary_contact,
					territory,
					customer_group,
					default_currency,
					default_price_list,
					creation,
					modified
				FROM `tabCustomer`
				WHERE 
					customer_name LIKE %(search)s
					OR mobile_no LIKE %(search)s
					OR email_id LIKE %(search)s
					OR name LIKE %(search)s
				ORDER BY modified DESC
				LIMIT %(limit)s
			""", {
				"search": f"%{query}%",
				"limit": limit
			}, as_dict=True)
			
			return {
				"status": "success",
				"count": len(customers),
				"customers": customers
			}
		except Exception as e:
			frappe.logger().error(f"Customer search error: {str(e)}")
			return {
				"status": "error",
				"message": f"Search failed: {str(e)}"
			}
	
	def count_with_breakdown(self):
		"""
		Count customers with breakdown by territory and group.
		"""
		try:
			total_count = frappe.db.count(self.doctype)
			
			# Count by territory
			by_territory = frappe.db.sql("""
				SELECT territory, COUNT(*) as count
				FROM `tabCustomer`
				GROUP BY territory
				ORDER BY count DESC
			""", as_dict=True)
			
			# Count by customer group
			by_group = frappe.db.sql("""
				SELECT customer_group, COUNT(*) as count
				FROM `tabCustomer`
				GROUP BY customer_group
				ORDER BY count DESC
			""", as_dict=True)
			
			return {
				"status": "success",
				"total_count": total_count,
				"by_territory": by_territory,
				"by_group": by_group
			}
		except Exception as e:
			frappe.logger().error(f"Count customers error: {str(e)}")
			return {
				"status": "error",
				"message": f"Count failed: {str(e)}"
			}
	
	def find_duplicates(self):
		"""
		Find customers with duplicate names.
		"""
		try:
			# Find duplicate customer names
			query = """
				SELECT 
					customer_name,
					COUNT(*) as count,
					GROUP_CONCAT(name SEPARATOR ', ') as customer_ids
				FROM `tabCustomer`
				GROUP BY customer_name
				HAVING COUNT(*) > 1
				ORDER BY count DESC
			"""
			
			duplicates = frappe.db.sql(query, as_dict=True)
			
			# Get detailed info for each duplicate
			duplicate_details = []
			for dup in duplicates:
				customer_ids = dup['customer_ids'].split(', ')
				customers = []
				
				for cust_id in customer_ids:
					customer = frappe.db.get_value(
						"Customer",
						cust_id,
						["name", "customer_name", "mobile_no", "email_id", "territory", "customer_group"],
						as_dict=True
					)
					if customer:
						customers.append(customer)
				
				duplicate_details.append({
					"customer_name": dup['customer_name'],
					"count": dup['count'],
					"customers": customers
				})
			
			return {
				"status": "success",
				"duplicate_count": len(duplicates),
				"duplicates": duplicate_details
			}
		except Exception as e:
			frappe.logger().error(f"Find duplicates error: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to find duplicates: {str(e)}"
			}

