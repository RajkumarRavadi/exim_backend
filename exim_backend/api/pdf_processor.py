"""
PDF Processor Module.
Handles PDF parsing, text extraction, table extraction, and image processing.
"""

import frappe
import os
import base64
from typing import Dict, List, Any


class PDFProcessor:
	"""Processes PDF files and extracts content."""
	
	def __init__(self):
		self.supported_extensions = ['.pdf']
	
	def extract_from_pdf(self, file_path_or_url):
		"""
		Extract content from a PDF file.
		
		Args:
			file_path_or_url: Path to PDF file or Frappe File URL
		
		Returns:
			dict: Extracted content including text, tables, images, and metadata
		"""
		try:
			# Resolve file path
			file_path = self._resolve_file_path(file_path_or_url)
			
			if not file_path or not os.path.exists(file_path):
				return {
					"status": "error",
					"message": f"File not found: {file_path_or_url}"
				}
			
			# Check file extension
			if not file_path.lower().endswith('.pdf'):
				return {
					"status": "error",
					"message": "File must be a PDF document"
				}
			
			frappe.logger().info(f"Extracting content from PDF: {file_path}")
			
			# Extract text content
			text_content = self._extract_text(file_path)
			
			# Extract tables
			tables = self._extract_tables(file_path)
			
			# Extract images (for vision AI processing)
			images = self._extract_images(file_path)
			
			# Get PDF metadata
			metadata = self._get_pdf_metadata(file_path)
			
			return {
				"status": "success",
				"content": {
					"text": text_content,
					"tables": tables,
					"images": images,
					"metadata": metadata,
					"file_path": file_path
				}
			}
			
		except Exception as e:
			frappe.logger().error(f"Error extracting PDF content: {str(e)}")
			frappe.logger().exception("Full exception traceback:")
			return {
				"status": "error",
				"message": f"Failed to extract PDF content: {str(e)}"
			}
	
	def _resolve_file_path(self, file_path_or_url):
		"""
		Resolve Frappe file URL to actual file path.
		
		Args:
			file_path_or_url: File URL or path
		
		Returns:
			str: Actual file path
		"""
		try:
			# If it's a Frappe file URL (/files/...)
			if file_path_or_url.startswith('/files/'):
				# Get site path
				site_path = frappe.get_site_path()
				# Remove leading slash and construct full path
				relative_path = file_path_or_url.lstrip('/')
				file_path = os.path.join(site_path, 'public', relative_path)
				return file_path
			
			# If it's a File doctype name
			if frappe.db.exists("File", {"name": file_path_or_url}):
				file_doc = frappe.get_doc("File", file_path_or_url)
				return frappe.get_site_path(file_doc.file_url.lstrip('/'))
			
			# If it's already an absolute path
			if os.path.isabs(file_path_or_url):
				return file_path_or_url
			
			# Otherwise, treat as relative to site
			return os.path.join(frappe.get_site_path(), file_path_or_url)
			
		except Exception as e:
			frappe.logger().error(f"Error resolving file path: {str(e)}")
			return file_path_or_url
	
	def _extract_text(self, file_path):
		"""
		Extract text content from PDF.
		Uses pdfplumber for better text extraction.
		"""
		text_content = {
			"full_text": "",
			"pages": [],
			"page_count": 0,
			"ocr_used": False
		}
		
		try:
			# Try using pdfplumber (better for structured PDFs)
			try:
				import pdfplumber
				
				with pdfplumber.open(file_path) as pdf:
					text_content["page_count"] = len(pdf.pages)
					
					for page_num, page in enumerate(pdf.pages, start=1):
						page_text = page.extract_text() or ""
						text_content["pages"].append({
							"page_number": page_num,
							"text": page_text
						})
						text_content["full_text"] += f"\n--- Page {page_num} ---\n{page_text}"
				
				frappe.logger().info(f"Extracted text using pdfplumber: {len(text_content['full_text'])} characters")
				
			except ImportError:
				frappe.logger().warning("pdfplumber not installed, falling back to PyPDF2")
			
			# Fallback to PyPDF2
			try:
				import PyPDF2
				
				with open(file_path, 'rb') as pdf_file:
					pdf_reader = PyPDF2.PdfReader(pdf_file)
					text_content["page_count"] = len(pdf_reader.pages)
					
					for page_num, page in enumerate(pdf_reader.pages, start=1):
						page_text = page.extract_text() or ""
						text_content["pages"].append({
							"page_number": page_num,
							"text": page_text
						})
						text_content["full_text"] += f"\n--- Page {page_num} ---\n{page_text}"
				
				frappe.logger().info(f"Extracted text using PyPDF2: {len(text_content['full_text'])} characters")
				
			except ImportError:
				frappe.logger().error("Neither pdfplumber nor PyPDF2 is installed")
			
		except Exception as e:
			frappe.logger().error(f"Error extracting text from PDF: {str(e)}")
		if self._needs_ocr_fallback(text_content):
			self._extract_text_via_ocr(file_path, text_content)
		
		return text_content

	def _needs_ocr_fallback(self, text_content: Dict[str, Any]) -> bool:
		"""
		Determine if OCR fallback is needed (e.g., scanned PDFs with no extractable text).
		"""
		full_text = (text_content.get("full_text") or "").strip()
		if len(full_text) >= 80:
			return False
		
		pages = text_content.get("pages") or []
		for page in pages:
			if (page.get("text") or "").strip():
				return False
		
		return True

	def _extract_text_via_ocr(self, file_path: str, text_content: Dict[str, Any], max_pages: int = 5):
		"""
		Extract text using OCR (pytesseract) for scanned PDFs.
		Updates text_content in-place.
		"""
		try:
			from pdf2image import convert_from_path
			import pytesseract
		except ImportError:
			frappe.logger().warning("OCR fallback unavailable (pdf2image or pytesseract not installed)")
			return
		
		try:
			images = convert_from_path(file_path, dpi=250, first_page=1, last_page=max_pages)
		except Exception as e:
			frappe.logger().error(f"OCR fallback failed to convert PDF: {str(e)}")
			return
		
		text_content["ocr_used"] = True
		text_content["pages"] = []
		text_content["full_text"] = ""
		text_content["page_count"] = len(images)
		
		for page_idx, image in enumerate(images, start=1):
			if page_idx > max_pages:
				break
			try:
				page_text = pytesseract.image_to_string(image) or ""
				text_content["pages"].append({
					"page_number": page_idx,
					"text": page_text
				})
				text_content["full_text"] += f"\n--- OCR Page {page_idx} ---\n{page_text}"
			except Exception as ocr_error:
				frappe.logger().error(f"OCR extraction error on page {page_idx}: {str(ocr_error)}")
				continue
		
		frappe.logger().info(f"OCR fallback extracted {len(text_content['pages'])} page(s) of text")
	
	def _extract_tables(self, file_path):
		"""
		Extract tables from PDF.
		Uses pdfplumber for table detection.
		"""
		tables = []
		
		try:
			import pdfplumber
			
			with pdfplumber.open(file_path) as pdf:
				for page_num, page in enumerate(pdf.pages, start=1):
					page_tables = page.extract_tables()
					
					if page_tables:
						for table_idx, table in enumerate(page_tables):
							if table and len(table) > 0:
								# Convert table to list of dicts (assuming first row is header)
								headers = table[0] if table else []
								rows = table[1:] if len(table) > 1 else []
								
								table_data = {
									"page": page_num,
									"table_index": table_idx,
									"headers": headers,
									"rows": rows,
									"row_count": len(rows)
								}
								tables.append(table_data)
			
			frappe.logger().info(f"Extracted {len(tables)} tables from PDF")
			
		except ImportError:
			frappe.logger().warning("pdfplumber not installed, cannot extract tables")
		except Exception as e:
			frappe.logger().error(f"Error extracting tables from PDF: {str(e)}")
		
		return tables
	
	def _extract_images(self, file_path):
		"""
		Extract images from PDF for vision AI processing.
		Returns base64 encoded images or image references.
		"""
		images = []
		
		try:
			# Try using PyMuPDF (fitz) for better image extraction
			try:
				import fitz  # PyMuPDF
				
				doc = fitz.open(file_path)
				
				for page_num, page in enumerate(doc, start=1):
					image_list = page.get_images()
					
					for img_idx, img in enumerate(image_list):
						xref = img[0]
						base_image = doc.extract_image(xref)
						image_bytes = base_image["image"]
						image_ext = base_image["ext"]
						
						# Convert to base64 for AI processing
						image_b64 = base64.b64encode(image_bytes).decode('utf-8')
						
						images.append({
							"page": page_num,
							"image_index": img_idx,
							"format": image_ext,
							"base64": image_b64[:100] + "..."  # Store preview only, full image on demand
						})
				
				doc.close()
				frappe.logger().info(f"Extracted {len(images)} images from PDF using PyMuPDF")
				
			except ImportError:
				frappe.logger().warning("PyMuPDF not installed, cannot extract images")
			
		except Exception as e:
			frappe.logger().error(f"Error extracting images from PDF: {str(e)}")
		
		return images
	
	def _get_pdf_metadata(self, file_path):
		"""
		Extract PDF metadata (author, creation date, etc.).
		"""
		metadata = {}
		
		try:
			import PyPDF2
			
			with open(file_path, 'rb') as pdf_file:
				pdf_reader = PyPDF2.PdfReader(pdf_file)
				
				if pdf_reader.metadata:
					metadata = {
						"title": pdf_reader.metadata.get('/Title', ''),
						"author": pdf_reader.metadata.get('/Author', ''),
						"subject": pdf_reader.metadata.get('/Subject', ''),
						"creator": pdf_reader.metadata.get('/Creator', ''),
						"producer": pdf_reader.metadata.get('/Producer', ''),
						"creation_date": pdf_reader.metadata.get('/CreationDate', ''),
						"modification_date": pdf_reader.metadata.get('/ModDate', '')
					}
				
				metadata["page_count"] = len(pdf_reader.pages)
			
		except Exception as e:
			frappe.logger().error(f"Error extracting PDF metadata: {str(e)}")
		
		return metadata
	
	def convert_pdf_page_to_image(self, file_path, page_number=1, dpi=200):
		"""
		Convert a PDF page to an image for vision AI processing.
		
		Args:
			file_path: Path to PDF file
			page_number: Page number to convert (1-indexed)
			dpi: Resolution for conversion
		
		Returns:
			dict: Image data in base64 format
		"""
		try:
			# Try using pdf2image
			try:
				from pdf2image import convert_from_path
				
				images = convert_from_path(
					file_path,
					first_page=page_number,
					last_page=page_number,
					dpi=dpi
				)
				
				if images:
					import io
					img = images[0]
					
					# Convert to bytes
					img_byte_arr = io.BytesIO()
					img.save(img_byte_arr, format='PNG')
					img_byte_arr = img_byte_arr.getvalue()
					
					# Convert to base64
					img_b64 = base64.b64encode(img_byte_arr).decode('utf-8')
					
					return {
						"status": "success",
						"page": page_number,
						"format": "png",
						"base64": img_b64
					}
				
			except ImportError:
				frappe.logger().warning("pdf2image not installed")
				return {
					"status": "error",
					"message": "pdf2image library not installed"
				}
			
		except Exception as e:
			frappe.logger().error(f"Error converting PDF page to image: {str(e)}")
			return {
				"status": "error",
				"message": f"Failed to convert PDF page: {str(e)}"
			}


# Utility function to get PDF as base64 for AI vision models
def get_pdf_as_base64(file_path, max_pages=5):
	"""
	Convert PDF pages to base64 images for AI vision processing.
	
	Args:
		file_path: Path to PDF file
		max_pages: Maximum number of pages to convert
	
	Returns:
		list: List of base64 encoded images
	"""
	processor = PDFProcessor()
	images = []
	
	for page_num in range(1, max_pages + 1):
		result = processor.convert_pdf_page_to_image(file_path, page_num)
		if result.get("status") == "success":
			images.append(result)
		else:
			break
	
	return images

