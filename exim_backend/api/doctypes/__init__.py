"""
DocType handlers module for AI Chat system.
Each doctype has its own handler for specific operations.
"""

from exim_backend.api.doctypes.base_handler import BaseDocTypeHandler
from exim_backend.api.doctypes.customer_handler import CustomerHandler

# Registry of available doctype handlers
DOCTYPE_HANDLERS = {
	"Customer": CustomerHandler,
	# Add more doctypes here as they are implemented
	# "Supplier": SupplierHandler,
	# "Item": ItemHandler,
	# "Lead": LeadHandler,
}


def get_handler(doctype):
	"""
	Get the appropriate handler for a doctype.
	
	Args:
		doctype: Name of the doctype
	Returns:
		Handler instance or None if not found
	"""
	handler_class = DOCTYPE_HANDLERS.get(doctype)
	if handler_class:
		return handler_class()
	return None


def get_available_doctypes():
	"""Get list of available doctypes."""
	return list(DOCTYPE_HANDLERS.keys())

