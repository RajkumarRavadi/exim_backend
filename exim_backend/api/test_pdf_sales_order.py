"""
Test and Demo script for PDF Sales Order functionality.
Run this file to test the PDF sales order processing.

Usage:
    bench execute exim_backend.api.test_pdf_sales_order.run_tests
"""

import frappe
import os
from exim_backend.api.doctypes.pdf_sales_order_handler import PDFSalesOrderHandler
from exim_backend.api.pdf_chat_integration import PDFChatIntegration


def run_tests():
	"""Run all tests for PDF sales order functionality."""
	print("\n" + "="*60)
	print("PDF SALES ORDER - TEST SUITE")
	print("="*60 + "\n")
	
	# Test 1: Test PDF Processor
	print("TEST 1: PDF Processor")
	test_pdf_processor()
	
	# Test 2: Test AI Extractor (with sample data)
	print("\nTEST 2: AI Extractor")
	test_ai_extractor()
	
	# Test 3: Test Complete Workflow (with mock PDF)
	print("\nTEST 3: Complete Workflow")
	test_complete_workflow()
	
	# Test 4: Test Chat Integration
	print("\nTEST 4: Chat Integration")
	test_chat_integration()
	
	print("\n" + "="*60)
	print("ALL TESTS COMPLETED")
	print("="*60 + "\n")


def test_pdf_processor():
	"""Test PDF processor functionality."""
	from exim_backend.api.pdf_processor import PDFProcessor
	
	processor = PDFProcessor()
	print("✓ PDFProcessor initialized successfully")
	
	# Test with a sample text
	sample_content = {
		"text": {
			"full_text": """
			SALES ORDER
			
			Customer: ABC Corporation
			Date: 2024-01-15
			Delivery Date: 2024-01-22
			PO Number: PO-2024-001
			
			Items:
			Item Code    Description         Qty    Rate
			ITEM-001     Product A          10     100.00
			ITEM-002     Product B          5      200.00
			
			Total: $1500.00
			""",
			"page_count": 1
		},
		"tables": [
			{
				"headers": ["Item Code", "Description", "Qty", "Rate"],
				"rows": [
					["ITEM-001", "Product A", "10", "100.00"],
					["ITEM-002", "Product B", "5", "200.00"]
				]
			}
		],
		"images": [],
		"metadata": {"page_count": 1}
	}
	
	print("✓ Sample PDF content created")
	print(f"  - Text length: {len(sample_content['text']['full_text'])} chars")
	print(f"  - Tables found: {len(sample_content['tables'])}")
	
	return sample_content


def test_ai_extractor():
	"""Test AI extractor functionality."""
	from exim_backend.api.ai_extractor import AISalesOrderExtractor
	
	extractor = AISalesOrderExtractor()
	print("✓ AISalesOrderExtractor initialized successfully")
	
	# Create sample PDF content
	sample_content = {
		"text": {
			"full_text": """
			SALES ORDER
			Customer: ABC Corporation
			Date: 2024-01-15
			Delivery Date: 2024-01-22
			PO Number: PO-2024-001
			
			Items:
			ITEM-001 - Product A - Qty: 10 - Rate: 100.00
			ITEM-002 - Product B - Qty: 5 - Rate: 200.00
			""",
			"page_count": 1
		},
		"tables": [
			{
				"headers": ["Item Code", "Description", "Qty", "Rate"],
				"rows": [
					["ITEM-001", "Product A", "10", "100.00"],
					["ITEM-002", "Product B", "5", "200.00"]
				]
			}
		],
		"images": [],
		"metadata": {}
	}
	
	# Test extraction
	result = extractor.extract_sales_order_data(sample_content)
	
	if result.get("status") == "success":
		print("✓ Data extraction successful")
		data = result.get("data", {})
		print(f"  - Customer: {data.get('customer')}")
		print(f"  - Transaction Date: {data.get('transaction_date')}")
		print(f"  - Items extracted: {len(data.get('items', []))}")
	else:
		print(f"✗ Data extraction failed: {result.get('message')}")
	
	return result


def test_complete_workflow():
	"""Test complete PDF sales order workflow."""
	handler = PDFSalesOrderHandler()
	print("✓ PDFSalesOrderHandler initialized successfully")
	
	# Create test data (simulating extracted PDF data)
	test_data = {
		"customer": "Test Customer",
		"customer_name": "Test Customer Corp",
		"transaction_date": "2024-01-15",
		"delivery_date": "2024-01-22",
		"company": frappe.db.get_single_value("Global Defaults", "default_company"),
		"items": [
			{
				"item_code": "TEST-ITEM-001",
				"item_name": "Test Product A",
				"qty": 10,
				"rate": 100.00,
				"uom": "Nos"
			}
		]
	}
	
	print("✓ Test data created")
	print(f"  - Customer: {test_data.get('customer_name')}")
	print(f"  - Items: {len(test_data.get('items', []))}")
	
	# Validate the data
	validated_data = handler._validate_and_enrich_data(test_data)
	warnings = validated_data.get("_warnings", [])
	
	if warnings:
		print(f"⚠ Validation warnings ({len(warnings)}):")
		for warning in warnings:
			print(f"    - {warning}")
	else:
		print("✓ No validation warnings")
	
	print("\n✓ Workflow test completed")
	print("  Note: Actual sales order creation skipped in test mode")
	
	return validated_data


def test_chat_integration():
	"""Test chat integration functionality."""
	integration = PDFChatIntegration()
	print("✓ PDFChatIntegration initialized successfully")
	
	# Test intent parsing
	test_messages = [
		("confirm", "confirm"),
		("yes, create the order", "confirm"),
		("cancel this", "cancel"),
		("change customer to CUST-001", "modify"),
		("show me the data", "show_data"),
		("random message", "unknown")
	]
	
	print("✓ Testing intent parsing:")
	for message, expected_action in test_messages:
		intent = integration._parse_user_intent(message)
		action = intent.get("action")
		status = "✓" if action == expected_action else "✗"
		print(f"  {status} '{message[:30]}...' → {action}")
	
	print("✓ Chat integration test completed")


def create_sample_customers_and_items():
	"""
	Create sample customers and items for testing.
	Run this before testing actual sales order creation.
	"""
	print("\nCreating sample test data...")
	
	# Create test customer
	try:
		if not frappe.db.exists("Customer", "TEST-CUST-001"):
			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": "Test Customer Corp",
				"customer_type": "Company",
				"customer_group": frappe.db.get_single_value("Selling Settings", "customer_group") or "Commercial",
				"territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
			})
			customer.insert(ignore_permissions=True)
			print(f"✓ Created customer: {customer.name}")
		else:
			print("✓ Test customer already exists")
	except Exception as e:
		print(f"✗ Error creating customer: {str(e)}")
	
	# Create test items
	test_items = [
		{"item_code": "TEST-ITEM-001", "item_name": "Test Product A"},
		{"item_code": "TEST-ITEM-002", "item_name": "Test Product B"}
	]
	
	for item_data in test_items:
		try:
			if not frappe.db.exists("Item", item_data["item_code"]):
				item = frappe.get_doc({
					"doctype": "Item",
					"item_code": item_data["item_code"],
					"item_name": item_data["item_name"],
					"item_group": frappe.db.get_single_value("Stock Settings", "item_group") or "All Item Groups",
					"stock_uom": "Nos",
					"is_stock_item": 0
				})
				item.insert(ignore_permissions=True)
				print(f"✓ Created item: {item.item_code}")
			else:
				print(f"✓ Test item {item_data['item_code']} already exists")
		except Exception as e:
			print(f"✗ Error creating item {item_data['item_code']}: {str(e)}")
	
	frappe.db.commit()
	print("✓ Sample data creation completed")


def test_with_real_sales_order():
	"""
	Test creating a real sales order (requires test data to exist).
	Run create_sample_customers_and_items() first.
	"""
	print("\n" + "="*60)
	print("CREATING REAL SALES ORDER FROM TEST DATA")
	print("="*60 + "\n")
	
	handler = PDFSalesOrderHandler()
	
	# Simulated extracted data from PDF
	extracted_data = {
		"customer": "TEST-CUST-001",
		"transaction_date": "2024-01-15",
		"delivery_date": "2024-01-22",
		"company": frappe.db.get_single_value("Global Defaults", "default_company"),
		"items": [
			{
				"item_code": "TEST-ITEM-001",
				"qty": 10,
				"rate": 100.00
			},
			{
				"item_code": "TEST-ITEM-002",
				"qty": 5,
				"rate": 200.00
			}
		]
	}
	
	print("Test data prepared:")
	print(f"  Customer: {extracted_data['customer']}")
	print(f"  Items: {len(extracted_data['items'])}")
	
	# Create using the handler directly
	from exim_backend.api.doctypes.sales_order_handler import SalesOrderHandler
	so_handler = SalesOrderHandler()
	
	result = so_handler.create_document(extracted_data)
	
	if result.get("status") == "success":
		print(f"\n✓ Sales Order created successfully!")
		print(f"  Order ID: {result.get('name')}")
		print(f"  Customer: {result.get('customer_name')}")
		print(f"  Total: {result.get('grand_total')}")
	else:
		print(f"\n✗ Failed to create sales order:")
		print(f"  Error: {result.get('message')}")


# Quick diagnostic function
def check_dependencies():
	"""Check if all required dependencies are installed."""
	print("\n" + "="*60)
	print("CHECKING DEPENDENCIES")
	print("="*60 + "\n")
	
	dependencies = {
		"pdfplumber": "PDF text extraction",
		"PyPDF2": "PDF reading (fallback)",
		"fitz": "PDF image extraction (PyMuPDF)",
		"pdf2image": "PDF to image conversion",
		"PIL": "Image processing (Pillow)",
		"dateutil": "Date parsing",
		"google.generativeai": "Google Gemini API (optional, for direct Gemini)"
	}
	
	for module_name, description in dependencies.items():
		try:
			__import__(module_name)
			print(f"✓ {module_name:25} - {description}")
		except ImportError:
			print(f"✗ {module_name:25} - {description} [NOT INSTALLED]")
	
	# Check AI API configuration
	print("\n" + "-"*60)
	print("AI API CONFIGURATION")
	print("-"*60 + "\n")
	
	openrouter_key = frappe.conf.get("openrouter_api_key")
	gemini_key = frappe.conf.get("gemini_api_key")
	ai_model = frappe.conf.get("ai_model")
	
	if openrouter_key:
		print(f"✓ OpenRouter API Key: Configured")
		print(f"  Model: {ai_model or 'google/gemini-2.0-flash-exp:free (default)'}")
	elif gemini_key:
		print(f"✓ Gemini API Key: Configured")
		print(f"  Model: {ai_model or 'gemini-1.5-flash (default)'}")
	else:
		print(f"⚠ No AI API Key configured")
		print(f"  AI extraction will use rule-based fallback")
		print(f"  For better results, configure openrouter_api_key or gemini_api_key")
	
	print("\n" + "="*60 + "\n")


# Main execution
if __name__ == "__main__":
	run_tests()


# Convenience functions for bench execute
def quick_test():
	"""Quick test - check dependencies and run basic tests."""
	check_dependencies()
	run_tests()


def setup_test_data():
	"""Setup test customers and items."""
	create_sample_customers_and_items()


def full_test():
	"""Full test - setup data and create real sales order."""
	create_sample_customers_and_items()
	test_with_real_sales_order()

