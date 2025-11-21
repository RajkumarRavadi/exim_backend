"""
DocType Fields API - Dynamic field retrieval with child tables
Provides comprehensive field metadata for intelligent AI prompting
"""

import frappe


@frappe.whitelist()
def get_doctype_fields(doctype: str, include_children: int = 1, child_doctype: str | None = None):
    """
    Return field metadata for a given doctype with optional recursive child tables.
    
    Args:
        doctype: DocType name (e.g., "Sales Order")
        include_children: 1 to include child table fields recursively, 0 to exclude
        child_doctype: Optional child table DocType name (e.g., "Sales Order Item").
            If provided, only that child table's fields (and nested children if include_children=1) are returned
    
    Response:
        {
          "success": true,
          "data": {
             "doctype": "Sales Order",
             "fields": [ { label, fieldname, fieldtype, options? }, ... ],
             "children": [
                {
                  "label": "Items",
                  "child_doctype": "Sales Order Item",
                  "fieldname": "items",
                  "fields": [ { label, fieldname, fieldtype, options? }, ... ],
                  "children": [...] // nested
                }
             ]
          }
        }
    """
    if not doctype:
        return _error(400, "BadRequest", "Missing doctype")
    
    if not frappe.db.exists("DocType", doctype):
        return _error(404, "NotFound", f"DocType '{doctype}' not found")
    
    try:
        meta = frappe.get_meta(doctype)
        
        # If a specific child_doctype is requested, return only that child's fields
        if child_doctype:
            # Validate child exists
            if not frappe.db.exists("DocType", child_doctype):
                return _error(404, "NotFound", f"Child DocType '{child_doctype}' not found")
            
            # Optionally ensure it is a child of the given parent doctype
            is_child = any(f.fieldtype == "Table" and f.options == child_doctype for f in meta.fields)
            if not is_child:
                # Not strictly required, but helps catch misuse
                return _error(400, "BadRequest", f"'{child_doctype}' is not a child table of '{doctype}'")
            
            child_meta = frappe.get_meta(child_doctype)
            child_entry = {
                "label": child_doctype,
                "fieldname": None,
                "child_doctype": child_doctype,
                "fields": [_field_dict(cf) for cf in child_meta.fields],
                "children": _collect_children(child_meta) if int(include_children) else [],
            }
            result = {
                "doctype": doctype,
                "fields": [],
                "children": [child_entry],
            }
        else:
            # Full payload (parent + optionally all children)
            fields = [_field_dict(f) for f in meta.fields]
            result = {"doctype": doctype, "fields": fields, "children": []}
            
            if int(include_children):
                result["children"] = _collect_children(meta)
        
        frappe.local.response.http_status_code = 200
        return {"success": True, "data": result}
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get DocType Fields Error")
        return _error(500, "InternalServerError", f"Failed to fetch fields: {str(e)}")


@frappe.whitelist()
def get_multiple_doctypes_fields(doctypes: str | list, include_children: int = 1):
    """
    Get field metadata for multiple DocTypes at once.
    
    Args:
        doctypes: Comma-separated string or list of DocType names
        include_children: 1 to include child tables, 0 to exclude
    
    Response:
        {
          "success": true,
          "data": {
            "Customer": { doctype, fields, children },
            "Sales Order": { doctype, fields, children },
            ...
          }
        }
    """
    # Parse doctypes
    if isinstance(doctypes, str):
        doctype_list = [dt.strip() for dt in doctypes.split(",") if dt.strip()]
    else:
        doctype_list = doctypes
    
    if not doctype_list:
        return _error(400, "BadRequest", "No doctypes provided")
    
    try:
        result = {}
        errors = []
        
        for doctype in doctype_list:
            if not frappe.db.exists("DocType", doctype):
                errors.append(f"DocType '{doctype}' not found")
                continue
            
            try:
                meta = frappe.get_meta(doctype)
                fields = [_field_dict(f) for f in meta.fields]
                
                result[doctype] = {
                    "doctype": doctype,
                    "fields": fields,
                    "children": _collect_children(meta) if int(include_children) else [],
                }
            except Exception as e:
                errors.append(f"Error fetching '{doctype}': {str(e)}")
        
        frappe.local.response.http_status_code = 200
        return {
            "success": True,
            "data": result,
            "errors": errors if errors else None,
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Multiple DocTypes Fields Error")
        return _error(500, "InternalServerError", f"Failed to fetch fields: {str(e)}")


@frappe.whitelist()
def get_all_doctypes(filters: str | None = None):
    """
    Get all available DocTypes in the system.
    
    Args:
        filters: Optional JSON string of filters
            Examples:
            - '{"module": "Core"}' - Only DocTypes from Core module
            - '{"custom": 0}' - Only standard DocTypes
            - '{"issingle": 0}' - Only non-single DocTypes
    
    Response:
        {
          "success": true,
          "data": {
            "doctypes": [
              {
                "name": "Customer",
                "module": "CRM",
                "custom": 0,
                "issingle": 0,
                "is_virtual": 0
              },
              ...
            ],
            "count": 150
          }
        }
    """
    try:
        # Parse filters if provided
        filter_dict = {}
        if filters:
            import json
            filter_dict = json.loads(filters) if isinstance(filters, str) else filters
        
        # Add default filters to exclude system DocTypes
        if 'module' not in filter_dict:
            # Get all DocTypes but exclude hidden/internal ones
            filter_dict['istable'] = 0  # Exclude child tables
        
        # Get DocTypes
        doctypes = frappe.get_all(
            'DocType',
            fields=['name', 'module', 'custom', 'issingle', 'istable'],
            filters=filter_dict,
            order_by='name'
        )
        
        # Filter out system DocTypes
        important_modules = [
            'Accounts', 'Stock', 'Selling', 'Buying', 'CRM', 
            'HR', 'Support', 'Projects', 'Manufacturing',
            'Assets', 'Loan Management', 'Healthcare',
            'Education', 'Non Profit', 'Agriculture',
            'Exim Backend'  # Your custom module
        ]
        
        # Keep custom DocTypes and DocTypes from important modules
        filtered_doctypes = [
            dt for dt in doctypes 
            if dt.get('custom') == 1 or dt.get('module') in important_modules
        ]
        
        frappe.local.response.http_status_code = 200
        return {
            "success": True,
            "data": {
                "doctypes": filtered_doctypes,
                "count": len(filtered_doctypes),
                "total_system_doctypes": len(doctypes)
            }
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get All DocTypes Error")
        return _error(500, "InternalServerError", f"Failed to fetch doctypes: {str(e)}")


@frappe.whitelist()
def detect_doctypes_from_query(query: str):
    """
    Detect which DocTypes are mentioned in a user query.
    Uses keyword matching to identify relevant DocTypes.
    
    Args:
        query: User's natural language query
    
    Response:
        {
          "success": true,
          "data": {
            "detected_doctypes": ["Customer", "Sales Order"],
            "confidence": {
              "Customer": 0.95,
              "Sales Order": 0.80
            },
            "keywords_matched": {
              "Customer": ["customer", "customers"],
              "Sales Order": ["order", "orders"]
            }
          }
        }
    """
    if not query:
        return _error(400, "BadRequest", "Missing query")
    
    try:
        query_lower = query.lower()
        
        # Get all available DocTypes from the system
        all_doctypes_response = get_all_doctypes()
        
        if not all_doctypes_response.get("success"):
            # Fallback to hardcoded list if API fails
            available_doctypes = ["Customer", "Item", "Sales Order", "Sales Invoice"]
        else:
            available_doctypes = [dt['name'] for dt in all_doctypes_response['data']['doctypes']]
        
        # Build dynamic keyword mapping based on actual DocTypes
        doctype_keywords = {}
        
        # Common patterns for DocType names
        for doctype in available_doctypes:
            doctype_lower = doctype.lower()
            keywords = [doctype_lower]
            
            # Add plural form
            if not doctype_lower.endswith('s'):
                keywords.append(doctype_lower + 's')
            
            # Add variations - but be more specific
            if ' ' in doctype:
                # "Sales Order" → ["sales order", "salesorder"]
                # Don't add individual words to avoid false matches
                keywords.append(doctype_lower.replace(' ', ''))
            
            # Add common aliases
            aliases = {
                "Customer": ["client", "clients", "buyer", "buyers"],
                "Item": ["product", "products", "goods", "sku"],
                "Sales Order": ["so", "order", "orders"],
                "Sales Invoice": ["invoice", "invoices", "bill", "bills", "sales invoice"],
                "Purchase Order": ["po", "procurement", "purchase order"],
                "Supplier": ["vendor", "vendors"],
                "Quotation": ["quote", "quotes"],
                "Delivery Note": ["delivery", "deliveries", "shipment"],
                "Payment Entry": ["payment entry", "payment entries", "payments", "payment"],
                "Journal Entry": ["journal entry", "journal entries", "journal"],
                "Purchase Invoice": ["purchase invoice", "purchase invoices", "vendor invoice"],
            }
            
            if doctype in aliases:
                keywords.extend(aliases[doctype])
            
            doctype_keywords[doctype] = keywords
        
        detected = {}
        keywords_matched = {}
        
        # Check each DocType - prioritize exact phrase matches first
        for doctype, keywords in doctype_keywords.items():
            matched = []
            exact_match = False
            exact_phrase_match = False
            
            # First, check for exact phrase matches (multi-word DocTypes)
            if ' ' in doctype:
                doctype_phrase = doctype.lower()
                if doctype_phrase in query_lower:
                    matched.append(doctype_phrase)
                    exact_phrase_match = True
                    exact_match = True
            
            # Then check individual keywords
            for keyword in keywords:
                if keyword in query_lower and keyword not in matched:
                    matched.append(keyword)
                    # Check if it's an exact word match (not just substring)
                    import re
                    if re.search(r'\b' + re.escape(keyword) + r'\b', query_lower):
                        exact_match = True
            
            if matched:
                # Calculate confidence based on keyword matches
                # Exact phrase matches get highest confidence
                if exact_phrase_match:
                    base_confidence = 0.98  # Very high for exact phrase
                elif exact_match:
                    base_confidence = 0.9
                else:
                    base_confidence = 0.6
                
                confidence = min(0.98, base_confidence + (len(matched) * 0.02))
                detected[doctype] = confidence
                keywords_matched[doctype] = matched
        
        # Sort by confidence
        detected_list = sorted(detected.keys(), key=lambda k: detected[k], reverse=True)
        
        # IMPROVEMENT 1: Minimum confidence threshold
        min_confidence = 0.7
        detected_list = [
            dt for dt in detected_list 
            if detected[dt] >= min_confidence
        ]
        
        # IMPROVEMENT 2: Limit based on query complexity
        query_words = len(query.split())
        if query_words <= 5:  # Simple query
            detected_list = detected_list[:1]  # Only top 1
        elif query_words <= 10:  # Medium query
            detected_list = detected_list[:2]  # Top 2
        else:  # Complex query
            detected_list = detected_list[:3]  # Top 3
        
        # IMPROVEMENT 3: If no high-confidence matches, try semantic fallback
        if not detected_list:
            # Common patterns
            query_lower = query.lower()
            if "who" in query_lower or "customer" in query_lower:
                detected_list = ["Customer"]
            elif "what" in query_lower or "item" in query_lower or "product" in query_lower:
                detected_list = ["Item"]
            elif "order" in query_lower:
                detected_list = ["Sales Order"]
            elif "invoice" in query_lower or "bill" in query_lower:
                detected_list = ["Sales Invoice"]
            else:
                # Default fallback
                detected_list = ["Customer", "Item", "Sales Order"]
            
            frappe.logger().info(f"[DocType Detection] Using semantic fallback: {detected_list}")
            # Set default confidence for fallback
            for dt in detected_list:
                if dt not in detected:
                    detected[dt] = 0.6
                    keywords_matched[dt] = ["semantic_fallback"]
        
        frappe.local.response.http_status_code = 200
        return {
            "success": True,
            "data": {
                "detected_doctypes": detected_list if detected_list else ["Customer", "Item", "Sales Order"],
                "confidence": {k: detected[k] for k in detected_list},
                "keywords_matched": {k: keywords_matched.get(k, []) for k in detected_list},
                "all_detected": sorted(detected.keys(), key=lambda k: detected[k], reverse=True),  # Keep full list for debugging
            }
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Detect DocTypes Error")
        return _error(500, "InternalServerError", f"Failed to detect doctypes: {str(e)}")


def _collect_children(meta):
    """Recursively collect child table fields"""
    children = []
    for f in meta.fields:
        if f.fieldtype == "Table" and f.options:
            try:
                child_meta = frappe.get_meta(f.options)
                child_entry = {
                    "label": f.label or f.fieldname,
                    "fieldname": f.fieldname,
                    "child_doctype": f.options,
                    "fields": [_field_dict(cf) for cf in child_meta.fields],
                    "children": _collect_children(child_meta),
                }
                children.append(child_entry)
            except Exception as e:
                frappe.log_error(f"Error collecting child table {f.options}: {str(e)}")
                continue
    return children


def _field_dict(f):
    """Convert field meta to dictionary with relevant info"""
    data = {
        "label": f.label or f.fieldname or "",
        "fieldname": f.fieldname,
        "fieldtype": f.fieldtype,
        "reqd": getattr(f, "reqd", 0),
        "read_only": getattr(f, "read_only", 0),
    }
    
    # Add options for Link, Select, Table fields
    if getattr(f, "options", None):
        data["options"] = f.options
    
    # Add default value if exists
    if getattr(f, "default", None):
        data["default"] = f.default
    
    # Add description if exists
    if getattr(f, "description", None):
        data["description"] = f.description
    
    return data


def _error(status, err_type, msg):
    """Standard error response"""
    frappe.local.response.http_status_code = status
    return {
        "success": False,
        "error": {
            "code": status,
            "type": err_type,
            "message": frappe._(msg),
        }
    }

