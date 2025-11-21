"""
Intelligent Query Processor - Dynamic AI-powered data operations
Implements the new approach: Detect DocTypes → Fetch Fields → AI Analysis → Execute

⚠️ INTELLIGENT QUERY SYSTEM DISABLED ⚠️
This entire module has been disabled. The system now uses the traditional functional approach.
All intelligent query features are commented out.
"""

import json
import re
import frappe
from frappe import _
from exim_backend.api.doctype_fields import detect_doctypes_from_query, get_multiple_doctypes_fields


# INTELLIGENT QUERY SYSTEM DISABLED - Commented out to use traditional functional approach
# @frappe.whitelist(allow_guest=True, methods=["POST"])
def process_intelligent_query():
    """
    Main entry point for intelligent query processing.
    
    ⚠️ DISABLED - This function is commented out. Use traditional functional approach instead.
    
    Flow:
    1. Handle greetings (hi, hello, etc.) with ERPNext assistant introduction
    2. Detect DocTypes from user query
    3. Fetch all fields for detected DocTypes (including child tables)
    4. Build intelligent prompt with field metadata
    5. Send to AI for analysis
    6. AI decides: Direct API only (dynamic queries are disabled)
    7. Execute and return results
    
    Request:
        {
          "query": "Show me customers from USA",
          "session_id": "chat_xxx"
        }
    
    Response:
        {
          "status": "success",
          "execution_type": "direct_api" or "direct_response" (for greetings),
          "data": {...},
          "ai_reasoning": "Why this API was chosen"
        }
    
    NOTE: Dynamic queries are DISABLED. Only direct API calls are used.
    """
    # INTELLIGENT QUERY SYSTEM DISABLED - Return error if accidentally called
    return {
        "status": "error",
        "message": "Intelligent Query System is disabled. Please use the traditional functional approach."
    }
    
    # COMMENTED OUT - Original implementation below
    # All code below is disabled - uncomment to re-enable intelligent query system
    """
    try:
        # 1. Get user query
        query = frappe.form_dict.get("query", "").strip()
        session_id = frappe.form_dict.get("session_id")
        
        if not query:
            return _error_response("Query is required")
        
        frappe.logger().info(f"[Intelligent Query] Processing: {query[:100]}")
        
        # 1.1. Handle greetings and simple conversational queries
        query_lower = query.lower().strip()
        greeting_patterns = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        
        if any(query_lower.startswith(pattern) or query_lower == pattern for pattern in greeting_patterns):
            return {
                "status": "success",
                "execution_type": "direct_response",
                "data": {
                    "message": "Hello! I'm your ERPNext AI assistant. I can help you with:\n\n"
                              "• **Searching** for customers, items, sales orders, and other documents\n"
                              "• **Getting details** of specific documents\n"
                              "• **Counting** documents with filters\n"
                              "• **Analyzing** sales data, order statistics, and customer information\n\n"
                              "What would you like to know? For example:\n"
                              "- Show me all customers\n"
                              "- Get details of customer ABC\n"
                              "- How many sales orders are there?\n"
                              "- Top customers by order value"
                },
                "ai_reasoning": "Greeting detected - providing ERPNext assistant introduction"
            }
        
        # Store original query for context storage
        original_query = query
        
        # 1.5. Check for follow-up questions and resolve references
        query, context_info = _resolve_follow_up_references(query, session_id)
        
        # 2. Detect DocTypes involved
        doctype_detection = detect_doctypes_from_query(query)
        
        if not doctype_detection.get("success"):
            return _error_response("Failed to detect DocTypes")
        
        detected_doctypes = doctype_detection["data"]["detected_doctypes"]
        
        if not detected_doctypes:
            # Fallback to common DocTypes
            detected_doctypes = ["Customer", "Item", "Sales Order"]
            frappe.logger().info("[Intelligent Query] No doctypes detected, using defaults")
        
        frappe.logger().info(f"[Intelligent Query] Detected DocTypes: {detected_doctypes}")
        
        # 3. Fetch all fields for detected DocTypes
        fields_response = get_multiple_doctypes_fields(
            doctypes=detected_doctypes,
            include_children=1
        )
        
        if not fields_response.get("success"):
            return _error_response("Failed to fetch DocType fields")
        
        doctype_schemas = fields_response["data"]
        
        # 4. Build intelligent prompt
        intelligent_prompt = _build_intelligent_prompt(query, doctype_schemas)
        
        # 5. Send to AI for analysis
        ai_response = _call_ai_for_analysis(intelligent_prompt, query, session_id)
        
        if not ai_response.get("success"):
            return _error_response(f"AI analysis failed: {ai_response.get('error')}")
        
        # 5.5. Validate AI decision before execution
        validation = _validate_ai_decision(ai_response["decision"], doctype_schemas)
        if not validation["valid"]:
            frappe.logger().error(f"[Validation] AI decision invalid: {validation['error']}")
            return _error_response(f"Invalid query decision: {validation['error']}. Please rephrase your query.")
        
        # 6. Execute based on AI decision (with retry)
        execution_result = _execute_with_retry(ai_response["decision"], doctype_schemas, max_retries=2)
        
        frappe.logger().info(f"[Intelligent Query] Execution result: {execution_result}")
        
        # Check if execution was successful
        if not execution_result.get("success", True):
            return _error_response(f"Execution failed: {execution_result.get('error', 'Unknown error')}")
        
        # Store context for follow-up questions
        result_data = execution_result.get("data", {})
        primary_doctype = detected_doctypes[0] if detected_doctypes else None
        
        # Determine doctype from data if available
        if result_data.get("doctype"):
            primary_doctype = result_data["doctype"]
        elif ai_response["decision"].get("parameters", {}).get("doctype"):
            primary_doctype = ai_response["decision"]["parameters"]["doctype"]
        
        # Store context
        if primary_doctype and session_id:
            results = result_data.get("results", [])
            
            # Handle get_document_details response format
            # It returns {"customer": {...}} or {"item": {...}} etc.
            if not results:
                # Check if result_data has a doctype-specific key (lowercase)
                doctype_key = primary_doctype.lower()
                if doctype_key in result_data:
                    # Normalize to results array format
                    doc = result_data[doctype_key]
                    if isinstance(doc, dict):
                        results = [doc]
                    else:
                        results = [doc] if doc else []
                # Also check for "document" key (generic)
                elif "document" in result_data:
                    doc = result_data["document"]
                    if isinstance(doc, dict):
                        results = [doc]
                    else:
                        results = [doc] if doc else []
            
            if not results and result_data.get("total_count"):
                # For count queries, we don't have results, but store the doctype
                _store_query_context(session_id, primary_doctype, original_query, [])
            else:
                _store_query_context(session_id, primary_doctype, original_query, results)
        
        # Track metrics for analysis
        execution_type = ai_response["decision"].get("execution_type")
        frappe.logger().info(f"[Metrics] Query: {original_query[:50]}, Type: {execution_type}, Success: {execution_result.get('success')}")
        
        # Track in cache for analysis
        cache_key = f"query_metrics_{frappe.utils.today()}"
        metrics = frappe.cache().get_value(cache_key) or {"total": 0, "success": 0, "failed": 0}
        metrics["total"] += 1
        if execution_result.get("success"):
            metrics["success"] += 1
        else:
            metrics["failed"] += 1
        frappe.cache().set_value(cache_key, metrics, expires_in_sec=86400)
        
        return {
            "status": "success",
            "execution_type": execution_type,
            "data": result_data,
            "ai_reasoning": ai_response["decision"].get("reasoning"),
            "detected_doctypes": detected_doctypes,
            "query_metadata": {
                "confidence": doctype_detection["data"]["confidence"],
                "keywords_matched": doctype_detection["data"]["keywords_matched"],
            },
            "context_resolved": context_info is not None
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Intelligent Query Error")
        return _error_response(f"Processing failed: {str(e)}")


def _resolve_follow_up_references(query, session_id):
    """
    Resolve follow-up questions like "what is it?", "show me that", "the first one"
    by checking conversation history and last query context.
    """
    query_lower = query.lower().strip()
    
    # Check if this is a follow-up question
    follow_up_indicators = [
        "what is it", "what is that", "what are they",
        "show me it", "show me that", "show them",
        "tell me about it", "tell me about that",
        "the first one", "the last one", "that one",
        "it", "they", "them", "that", "those",
        "complete info", "complete details", "full details", "full info",
        "give complete", "show complete", "get complete"
    ]
    
    is_follow_up = any(indicator in query_lower for indicator in follow_up_indicators)
    
    if not is_follow_up or not session_id:
        return query, None
    
    # Get last query context from cache
    cache_key = f"intelligent_query_context_{session_id}"
    last_context = frappe.cache().get_value(cache_key)
    
    if not last_context:
        frappe.logger().info("[Follow-up] No previous context found")
        return query, None
    
    # Resolve the reference
    last_doctype = last_context.get("doctype")
    last_query = last_context.get("query", "")
    last_results = last_context.get("results", [])
    
    frappe.logger().info(f"[Follow-up] Resolving reference. Last doctype: {last_doctype}, Last query: {last_query}")
    
    # Build enhanced query with context
    if last_doctype:
        # Check if asking for complete details/info
        is_complete_info_request = any(phrase in query_lower for phrase in [
            "complete info", "complete details", "full details", "full info",
            "give complete", "show complete", "get complete"
        ])
        
        # If asking for complete info/details, get details of the first result
        if is_complete_info_request:
            if last_results and len(last_results) > 0:
                # Get the first result's name
                first_result_name = last_results[0].get("name") or last_results[0].get(last_doctype.lower().replace(" ", "_"))
                if first_result_name:
                    enhanced_query = f"Get complete details of {last_doctype} {first_result_name}"
                    frappe.logger().info(f"[Follow-up] Enhanced query (complete info): {enhanced_query}")
                    return enhanced_query, {"resolved_from": query, "original_doctype": last_doctype}
            else:
                # No results, but we have a doctype - try to get from last query if it mentioned a name
                # Extract potential name from last query
                # Try to find a name pattern in the last query
                name_pattern = r'\b([A-Z][a-z]+|[A-Z]+-\d+|\d+)\b'
                matches = re.findall(name_pattern, last_query)
                if matches:
                    potential_name = matches[-1]  # Take the last match
                    enhanced_query = f"Get complete details of {last_doctype} {potential_name}"
                    frappe.logger().info(f"[Follow-up] Enhanced query (complete info with extracted name): {enhanced_query}")
                    return enhanced_query, {"resolved_from": query, "original_doctype": last_doctype}
                else:
                    # Fallback: show all
                    enhanced_query = f"Show me all {last_doctype.lower()}"
                    frappe.logger().info(f"[Follow-up] Enhanced query (complete info fallback): {enhanced_query}")
                    return enhanced_query, {"resolved_from": query, "original_doctype": last_doctype}
        
        # If asking "what is it?" about a count result, show all items of that doctype
        if "what is" in query_lower or "tell me about" in query_lower or "what are" in query_lower:
            if last_results and len(last_results) > 0:
                # Get the first result's name
                first_result_name = last_results[0].get("name") or last_results[0].get(last_doctype.lower().replace(" ", "_"))
                if first_result_name:
                    enhanced_query = f"Get details of {last_doctype} {first_result_name}"
                    frappe.logger().info(f"[Follow-up] Enhanced query: {enhanced_query}")
                    return enhanced_query, {"resolved_from": query, "original_doctype": last_doctype}
            
            # For count queries (no results), show all items
            enhanced_query = f"Show me all {last_doctype.lower()}"
            frappe.logger().info(f"[Follow-up] Enhanced query: {enhanced_query}")
            return enhanced_query, {"resolved_from": query, "original_doctype": last_doctype}
        elif "show" in query_lower or "list" in query_lower:
            enhanced_query = f"Show me all {last_doctype.lower()}"
            frappe.logger().info(f"[Follow-up] Enhanced query: {enhanced_query}")
            return enhanced_query, {"resolved_from": query, "original_doctype": last_doctype}
        else:
            # Generic follow-up, add context
            enhanced_query = f"{query} (referring to {last_doctype} from previous query: {last_query})"
            frappe.logger().info(f"[Follow-up] Enhanced query: {enhanced_query}")
            return enhanced_query, {"resolved_from": query, "original_doctype": last_doctype}
    
    return query, None


def _store_query_context(session_id, doctype, query, results):
    """
    Store query context for follow-up questions.
    """
    if not session_id:
        return
    
    cache_key = f"intelligent_query_context_{session_id}"
    context = {
        "doctype": doctype,
        "query": query,
        "results": results[:5] if isinstance(results, list) else [results] if results else [],
        "timestamp": frappe.utils.now()
    }
    
    frappe.cache().set_value(cache_key, context, expires_in_sec=3600)  # 1 hour
    frappe.logger().info(f"[Context] Stored context for session {session_id[:10]}: doctype={doctype}")


def _build_intelligent_prompt(query, doctype_schemas):
    """
    Build comprehensive prompt with:
    - User query
    - All DocType schemas (fields + relationships)
    - Available direct APIs
    - Dynamic query instructions
    """
    
    # Build DocType schema section
    schema_section = "## AVAILABLE DOCTYPES AND FIELDS\n\n"
    
    for doctype, schema in doctype_schemas.items():
        schema_section += f"### {doctype}\n"
        schema_section += "**Fields:**\n"
        
        # Parent fields
        for field in schema["fields"][:30]:  # Limit to top 30 fields
            field_info = f"- `{field['fieldname']}` ({field['fieldtype']})"
            if field.get("reqd"):
                field_info += " [REQUIRED]"
            if field.get("options"):
                field_info += f" → Links to: {field['options']}"
            schema_section += field_info + "\n"
        
        # Child tables
        if schema.get("children"):
            schema_section += "\n**Child Tables:**\n"
            for child in schema["children"]:
                schema_section += f"- `{child['fieldname']}` → {child['child_doctype']}\n"
                schema_section += f"  Fields: {', '.join([f['fieldname'] for f in child['fields'][:10]])}\n"
        
        schema_section += "\n"
    
    # Build available APIs section (ONLY DIRECT APIs - dynamic_query is DISABLED)
    apis_section = """## AVAILABLE DIRECT APIs (ONLY OPTION - Dynamic Query is DISABLED)

You MUST use one of these direct APIs. Dynamic queries are NOT available.

1. **dynamic_search** - Search with filters
   - Parameters: doctype, filters (dict), limit, order_by
   - Example: {"doctype": "Customer", "filters": {"territory": "USA"}}

2. **get_document_details** - Get specific document
   - Parameters: doctype, name
   - Example: {"doctype": "Customer", "name": "CUST-00001"}

3. **count_documents** - Count with filters
   - Parameters: doctype, filters
   - Example: {"doctype": "Customer", "filters": {"customer_group": "Commercial"}}

4. **get_customers_by_order_count** - Top customers by order count
   - Parameters: limit
   
5. **get_customers_by_order_value** - Top customers by order value
   - Parameters: min_value, from_date, to_date

6. **get_orders_by_item** - Orders containing specific item
   - Parameters: item_code

7. **get_orders_by_territory** - Orders from specific territory
   - Parameters: territory

8. **get_most_sold_items** - Top selling items
   - Parameters: limit, from_date, to_date

9. **create_document** - Create a new document
   - Parameters: doctype, fields (dict of field values)
   - Example: {"doctype": "Customer", "fields": {"customer_name": "John Doe", "mobile_no": "1234567890", "email_id": "john@example.com"}}
   - Use this for queries like "create customer", "add new customer", "create new [doctype]"

"""
    
    # Build full prompt
    full_prompt = f"""You are an intelligent ERPNext query analyzer.

{schema_section}

{apis_section}

## YOUR TASK

Analyze the user query and choose the BEST DIRECT API from the list above.

**IMPORTANT: Dynamic queries are DISABLED. You MUST use only direct APIs.**

USER QUERY: "{query}"

## RESPONSE FORMAT

Return JSON:
{{
  "execution_type": "direct_api",
  "reasoning": "Why you chose this API",
  "api_name": "dynamic_search",
  "parameters": {{"doctype": "Customer", "filters": {{}}}}
}}

IMPORTANT RULES:
- **ALWAYS use "execution_type": "direct_api"** - dynamic_query is NOT available
- For simple queries (search, count, get details), use DIRECT API
  Examples: "show all customers", "count items", "find customer ABC"
  
- For queries asking for details of a SPECIFIC document by name, use get_document_details:
  Examples: 
    * "show ajay customer complete details" → get_document_details with doctype="Customer", name="Ajay"
    * "get details of customer ABC" → get_document_details with doctype="Customer", name="ABC"
    * "show me customer CUST-00001" → get_document_details with doctype="Customer", name="CUST-00001"
    * "complete info about sales order SO-00001" → get_document_details with doctype="Sales Order", name="SO-00001"
  
- For two-part questions (e.g., "how many X and what are they?"), use dynamic_search
  to list the items (which also shows the count) rather than just count_documents
  
- For complex queries that might need SQL, try to break them down into simpler direct API calls
  Examples: 
    * "customers with no orders" → Use dynamic_search with appropriate filters if possible
    * "top customers by revenue" → Use get_customers_by_order_value
    * "items never sold" → Use dynamic_search with filters, or get_most_sold_items to see what IS sold
  
- If a query cannot be answered with direct APIs, choose the closest match and explain in reasoning

EXAMPLE DIRECT API CALLS:

Example 1: Get details of a specific document (use direct API)
{{
  "execution_type": "direct_api",
  "api_name": "get_document_details",
  "parameters": {{"doctype": "Customer", "name": "Ajay"}},
  "reasoning": "User wants complete details of a specific customer by name"
}}

Example 2: Count documents with filter (use direct API)
{{
  "execution_type": "direct_api",
  "api_name": "count_documents",
  "parameters": {{"doctype": "Purchase Order", "filters": {{"docstatus": 1}}}},
  "reasoning": "Simple count query with filter, use count_documents API"
}}

Example 3: Simple customer search (use direct API)
{{
  "execution_type": "direct_api",
  "api_name": "dynamic_search",
  "parameters": {{"doctype": "Customer", "filters": {{"territory": "USA"}}}},
  "reasoning": "Simple filter, use dynamic_search API"
}}

Example 4: Top customers by order value (use direct API)
{{
  "execution_type": "direct_api",
  "api_name": "get_customers_by_order_value",
  "parameters": {{"limit": 10}},
  "reasoning": "Use get_customers_by_order_value API for top customers"
}}

IMPORTANT FOR COUNT QUERIES:
- For simple count queries like "How many X are Y?", use count_documents API
- Example: "How many purchase orders are submitted?" → count_documents with doctype="Purchase Order", filters={{docstatus: 1}}

IMPORTANT FOR COMPLEX QUERIES:
- If a query seems complex, try to use the closest matching direct API
- For "top customers by revenue" → use get_customers_by_order_value
- For "top selling items" → use get_most_sold_items
- For "orders by territory" → use get_orders_by_territory
- Always prefer direct APIs over trying to construct SQL queries

IMPORTANT FOR CREATION QUERIES:
- For queries asking to CREATE, ADD, or INSERT a new document, use create_document API
- Extract all field values from the user query and map them to the correct field names
- Common field mappings for Customer:
  * "name" or customer name → customer_name
  * phone/mobile number → mobile_no
  * email → email_id
  * address fields → address_line1, city, state, country, pincode
- Examples:
  * "Create new customer Rajkumar Ravadi, 9381964965, rajkumarravadi3@gmail.com" 
    → create_document with doctype="Customer", fields={{"customer_name": "Rajkumar Ravadi", "mobile_no": "9381964965", "email_id": "rajkumarravadi3@gmail.com"}}
  * "Create customer Kunal 9381964965 kunal@nonitet.com"
    → create_document with doctype="Customer", fields={{"customer_name": "Kunal", "mobile_no": "9381964965", "email_id": "kunal@nonitet.com"}}
  * "Add new customer John Doe with email john@example.com and phone 1234567890"
    → create_document with doctype="Customer", fields={{"customer_name": "John Doe", "email_id": "john@example.com", "mobile_no": "1234567890"}}

Example 5: Create a new customer (use create_document API)
{{
  "execution_type": "direct_api",
  "api_name": "create_document",
  "parameters": {{
    "doctype": "Customer",
    "fields": {{
      "customer_name": "John Doe",
      "mobile_no": "1234567890",
      "email_id": "john@example.com"
    }}
  }},
  "reasoning": "User wants to create a new customer with provided details"
}}
"""
    
    return full_prompt


def _call_ai_for_analysis(prompt, user_query, session_id):
    """
    Call AI to analyze query and decide execution approach
    NOTE: Dynamic queries are DISABLED - only direct_api is allowed
    """
    try:
        # Get AI config (same as ai_chat.py)
        from exim_backend.api.ai_chat import get_ai_config, call_ai_api
        
        ai_config = get_ai_config()
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_query}
        ]
        
        # Call AI
        ai_response = call_ai_api(messages, ai_config)
        
        # Extract JSON decision
        decision = _extract_json_from_response(ai_response)
        
        if not decision:
            return {"success": False, "error": "Failed to parse AI response"}
        
        # FORCE direct_api - reject dynamic_query
        if decision.get("execution_type") == "dynamic_query":
            frappe.logger().warning("[AI Decision] Dynamic query requested but disabled - forcing direct_api")
            # Try to convert to direct_api by using dynamic_search
            decision["execution_type"] = "direct_api"
            if "api_name" not in decision:
                decision["api_name"] = "dynamic_search"
            if "parameters" not in decision:
                decision["parameters"] = {}
            decision["reasoning"] = (decision.get("reasoning", "") + 
                                    " [Note: Dynamic query disabled, using direct API instead]")
        
        # Ensure execution_type is direct_api
        if decision.get("execution_type") != "direct_api":
            decision["execution_type"] = "direct_api"
        
        frappe.logger().info(f"[AI Decision] Type: {decision.get('execution_type')}")
        frappe.logger().info(f"[AI Decision] API: {decision.get('api_name')}")
        frappe.logger().info(f"[AI Decision] Reasoning: {decision.get('reasoning', '')[:200]}")
        
        return {
            "success": True,
            "decision": decision,
            "raw_response": ai_response
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "AI Analysis Error")
        return {"success": False, "error": str(e)}


def _validate_ai_decision(decision, doctype_schemas):
    """
    Validate AI's decision before execution to catch errors early.
    Returns: {"valid": bool, "error": str}
    """
    execution_type = decision.get("execution_type")
    
    if not execution_type:
        return {"valid": False, "error": "Missing execution_type"}
    
    if execution_type == "direct_api":
        api_name = decision.get("api_name")
        if not api_name:
            return {"valid": False, "error": "Missing api_name for direct_api"}
        
        # Validate API exists
        valid_apis = [
            "dynamic_search", "get_document_details", "count_documents",
            "get_customers_by_order_count", "get_customers_by_order_value",
            "get_orders_by_item", "get_orders_by_territory", "get_most_sold_items",
            "create_document"
        ]
        if api_name not in valid_apis:
            return {"valid": False, "error": f"Unknown API: {api_name}"}
        
        # Validate parameters
        parameters = decision.get("parameters", {})
        if not parameters:
            return {"valid": False, "error": "Missing parameters"}
        
        # For create_document, validate doctype and fields
        if api_name == "create_document":
            doctype = parameters.get("doctype")
            if not doctype:
                return {"valid": False, "error": "Missing doctype for create_document"}
            if doctype not in doctype_schemas:
                return {"valid": False, "error": f"DocType '{doctype}' not in detected schemas"}
            fields = parameters.get("fields", {})
            if not fields:
                return {"valid": False, "error": "Missing fields for create_document"}
            # Don't validate field names for creation - let the handler deal with it
        else:
            # For other APIs, validate doctype and filters
            doctype = parameters.get("doctype")
            if doctype:
                if doctype not in doctype_schemas:
                    return {"valid": False, "error": f"DocType '{doctype}' not in detected schemas"}
                
                # Validate filters use valid fields
                filters = parameters.get("filters", {})
                if filters:
                    try:
                        meta = frappe.get_meta(doctype)
                        valid_fields = {f.fieldname for f in meta.fields}
                        valid_fields.update(["name", "docstatus", "modified", "creation", "owner"])
                        
                        for key in filters.keys():
                            if key not in valid_fields:
                                return {"valid": False, "error": f"Invalid field in filters: '{key}' (not in {doctype} fields)"}
                    except Exception as e:
                        frappe.logger().warning(f"Could not validate filters: {str(e)}")
    
    elif execution_type == "dynamic_query":
        # Dynamic queries are DISABLED
        return {"valid": False, "error": "Dynamic queries are disabled. Please use direct APIs only."}
    
    else:
        return {"valid": False, "error": f"Unknown execution_type: {execution_type}. Only 'direct_api' is allowed."}
    
    return {"valid": True}


def _remove_invalid_field(decision, field_name):
    """Remove invalid field from decision parameters."""
    if decision.get("execution_type") == "direct_api":
        parameters = decision.get("parameters", {})
        filters = parameters.get("filters", {})
        if field_name in filters:
            del filters[field_name]
            parameters["filters"] = filters
            decision["parameters"] = parameters
    return decision


def _fix_table_name(decision, error, doctype_schemas):
    """Try to fix table name in SQL query."""
    if decision.get("execution_type") == "dynamic_query":
        query = decision.get("query", "")
        # Try to find and replace with correct table name
        for doctype in doctype_schemas.keys():
            wrong_name = f"tab{doctype.replace(' ', '')}"
            correct_name = f"`tab{doctype}`"
            if wrong_name in query:
                query = query.replace(wrong_name, correct_name)
                decision["query"] = query
                break
    return decision


def _execute_with_retry(decision, doctype_schemas, max_retries=2):
    """
    Execute AI decision with automatic retry on errors.
    """
    import time
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            # Try execution
            result = _execute_ai_decision(decision, doctype_schemas)
            
            if result.get("success"):
                if attempt > 0:
                    frappe.logger().info(f"[Retry] Success on attempt {attempt + 1}")
                return result
            
            # Execution failed
            error = result.get("error", "Unknown error")
            last_error = error
            
            if attempt < max_retries:
                frappe.logger().warning(f"[Retry] Attempt {attempt + 1} failed: {error}")
                
                # Try to correct based on error type
                if "Unknown column" in error or "Unknown field" in error:
                    # Extract field name from error
                    field_match = re.search(r"'(.*?)'", error)
                    if field_match:
                        field_name = field_match.group(1)
                        decision = _remove_invalid_field(decision, field_name)
                        frappe.logger().info(f"[Retry] Removed invalid field: {field_name}")
                
                elif "Table" in error and "doesn't exist" in error:
                    # Try to fix table name
                    decision = _fix_table_name(decision, error, doctype_schemas)
                    frappe.logger().info(f"[Retry] Attempted to fix table name")
                
                elif "SQL syntax" in error or "syntax error" in error.lower() or "Incorrect table name" in error or "table name" in error.lower():
                    # SQL/table errors shouldn't occur since dynamic queries are disabled
                    # But log for debugging
                    frappe.logger().warning(f"[Retry] SQL/table error detected but dynamic queries are disabled: {error}")
                
                # Wait a bit before retry
                time.sleep(0.1)
                continue
            
            # Max retries reached
            frappe.logger().error(f"[Retry] Max retries ({max_retries}) exceeded")
            return result
            
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                frappe.logger().warning(f"[Retry] Exception on attempt {attempt + 1}: {str(e)}")
                continue
            raise
    
    return {"success": False, "error": last_error or "Max retries exceeded"}


def _execute_ai_decision(decision, doctype_schemas):
    """
    Execute the AI's decision - only direct API (dynamic queries are disabled)
    """
    execution_type = decision.get("execution_type")
    
    try:
        if execution_type == "direct_api":
            return _execute_direct_api(decision)
        
        elif execution_type == "dynamic_query":
            # Dynamic queries are disabled - should not reach here due to validation
            return {"success": False, "error": "Dynamic queries are disabled. Please use direct APIs only."}
        
        else:
            return {"success": False, "error": f"Unknown execution type: {execution_type}. Only 'direct_api' is allowed."}
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Execution Error")
        return {"success": False, "error": str(e)}


def _execute_direct_api(decision):
    """
    Execute a direct API call
    """
    api_name = decision.get("api_name")
    parameters = decision.get("parameters", {})
    
    frappe.logger().info(f"[Direct API] Calling: {api_name} with params: {parameters}")
    
    # Map to actual API functions
    api_map = {
        "dynamic_search": "exim_backend.api.ai_chat.dynamic_search",
        "get_document_details": "exim_backend.api.ai_chat.get_document_details",
        "count_documents": "exim_backend.api.ai_chat.count_documents",
        "get_customers_by_order_count": "exim_backend.api.ai_chat.get_customers_by_order_count",
        "get_customers_by_order_value": "exim_backend.api.ai_chat.get_customers_by_order_value",
        "get_orders_by_item": "exim_backend.api.ai_chat.get_orders_by_item",
        "get_orders_by_territory": "exim_backend.api.ai_chat.get_orders_by_territory",
        "get_most_sold_items": "exim_backend.api.ai_chat.get_most_sold_items",
        "create_document": "exim_backend.api.ai_chat.create_document",
    }
    
    if api_name not in api_map:
        frappe.logger().error(f"[Direct API] Unknown API: {api_name}")
        return {"success": False, "error": f"Unknown API: {api_name}"}
    
    try:
        # Call the API
        method = frappe.get_attr(api_map[api_name])
        
        # Set parameters in frappe.form_dict
        for key, value in parameters.items():
            if isinstance(value, (dict, list)):
                frappe.form_dict[key] = json.dumps(value)
            else:
                frappe.form_dict[key] = value
        
        frappe.logger().info(f"[Direct API] Calling method: {api_map[api_name]}")
        result = method()
        frappe.logger().info(f"[Direct API] Result type: {type(result)}, has results: {bool(result)}")
        
        # Check if result is a proper response structure
        if isinstance(result, dict):
            if result.get("status") == "error":
                error_msg = result.get("message", "Unknown error")
                
                # Special handling for "Handler not available" error
                if "Handler not available" in error_msg:
                    frappe.logger().info(f"[Direct API] Handler not available, using generic fallback")
                    return _execute_generic_search(parameters)
                
                return {"success": False, "error": error_msg}
            
            # Extract results from various response formats
            if "results" in result:
                data = result
            elif "message" in result and isinstance(result["message"], dict):
                data = result["message"]
            else:
                data = result
            
            # Add doctype to data if available in parameters (for count queries)
            if "doctype" in parameters and "doctype" not in data:
                data["doctype"] = parameters["doctype"]
        else:
            data = {"results": result if result else []}
            # Add doctype if available
            if "doctype" in parameters:
                data["doctype"] = parameters["doctype"]
        
        return {"success": True, "data": data}
        
    except Exception as e:
        error_str = str(e)
        frappe.logger().error(f"[Direct API] Error executing {api_name}: {error_str}")
        
        # If handler not available, use generic fallback
        if "Handler not available" in error_str or "handler" in error_str.lower():
            frappe.logger().info(f"[Direct API] Handler error, using generic fallback")
            return _execute_generic_search(parameters)
        
        frappe.log_error(frappe.get_traceback(), f"Direct API Error: {api_name}")
        return {"success": False, "error": error_str}


def _execute_generic_search(parameters):
    """
    Generic search fallback for DocTypes without specific handlers.
    Uses frappe.db.get_all directly.
    """
    try:
        doctype = parameters.get("doctype")
        filters = parameters.get("filters", {})
        limit = int(parameters.get("limit", 20))
        order_by = parameters.get("order_by", "modified desc")
        
        frappe.logger().info(f"[Generic Search] DocType: {doctype}, Filters: {filters}, Limit: {limit}")
        
        if not doctype:
            return {"success": False, "error": "DocType is required"}
        
        # Check if DocType exists
        if not frappe.db.exists("DocType", doctype):
            return {"success": False, "error": f"DocType '{doctype}' does not exist"}
        
        # Get meta to determine fields
        meta = frappe.get_meta(doctype)
        
        # Build field list - get key fields, excluding non-selectable field types
        fields = ["name"]
        excluded_fieldtypes = [
            "Table", "HTML", "Code", "Text Editor", "Attach Image",
            "Section Break", "Column Break", "Tab Break", "Fold",
            "Button", "Heading"
        ]
        
        # Get common data fields (limit to avoid SQL errors)
        # Include: Data, Date, Link, Select, Currency, etc.
        included_fieldtypes = [
            "Data", "Date", "Datetime", "Int", "Float", "Currency", 
            "Percent", "Check", "Select", "Small Text", "Link", 
            "Dynamic Link", "Time", "Duration"
        ]
        
        for df in meta.fields[:30]:  # Check more fields to get good ones
            if (df.fieldtype in included_fieldtypes and 
                df.fieldname and 
                df.fieldname not in fields and
                not df.fieldname.startswith('_') and
                df.fieldname != 'name'):
                fields.append(df.fieldname)
                if len(fields) >= 15:  # Limit to 15 fields total
                    break
        
        # If we only have 'name', add some common fields that usually exist
        if len(fields) == 1:
            # Try common field names that exist in most DocTypes
            common_fields = ["modified", "modified_by", "creation", "owner", "docstatus", "status"]
            for field in common_fields:
                if field not in fields:
                    try:
                        # Check if field exists in meta
                        if any(f.fieldname == field for f in meta.fields):
                            fields.append(field)
                    except:
                        pass
        
        frappe.logger().info(f"[Generic Search] Selected fields: {fields}")
        
        # Validate and clean filters - remove fields that don't exist in meta
        valid_filters = {}
        if filters:
            try:
                valid_fieldnames = {f.fieldname for f in meta.fields}
                valid_fieldnames.add("name")  # Always valid
                valid_fieldnames.add("docstatus")  # Always valid
                valid_fieldnames.add("modified")  # Always valid
                valid_fieldnames.add("creation")  # Always valid
                valid_fieldnames.add("owner")  # Always valid
                valid_fieldnames.add("modified_by")  # Always valid
                
                for key, value in filters.items():
                    # Skip None values
                    if value is None:
                        continue
                    
                    # Handle complex filters (dict with operators)
                    if isinstance(value, dict):
                        # For dict filters, the key should be a valid field
                        if key in valid_fieldnames:
                            valid_filters[key] = value
                        else:
                            frappe.logger().warning(f"[Generic Search] Skipping invalid filter field: {key} (not in {doctype} fields)")
                    else:
                        # Simple filter
                        if key in valid_fieldnames:
                            valid_filters[key] = value
                        else:
                            frappe.logger().warning(f"[Generic Search] Skipping invalid filter field: {key} (not in {doctype} fields)")
            except Exception as filter_error:
                frappe.logger().warning(f"[Generic Search] Error validating filters: {str(filter_error)}, using empty filters")
                valid_filters = {}
        
        frappe.logger().info(f"[Generic Search] Valid filters: {valid_filters}")
        
        # Execute query with error handling for invalid fields
        try:
            results = frappe.get_all(
                doctype,
                filters=valid_filters if valid_filters else None,
                fields=fields,
                limit_page_length=limit,
                order_by=order_by
            )
        except Exception as field_error:
            # If field error, try with minimal fields and only valid filters
            frappe.logger().warning(f"[Generic Search] Field error, retrying with minimal fields: {str(field_error)}")
            minimal_fields = ["name"]
            # Try to add a few safe fields
            safe_fields = ["modified", "creation", "docstatus"]
            for field in safe_fields:
                if any(f.fieldname == field for f in meta.fields):
                    minimal_fields.append(field)
            
            # Use only the most basic valid filters (name, docstatus)
            minimal_filters = {}
            if valid_filters:
                for key, value in valid_filters.items():
                    if key in ["name", "docstatus"]:
                        minimal_filters[key] = value
            
            results = frappe.get_all(
                doctype,
                filters=minimal_filters if minimal_filters else None,
                fields=minimal_fields,
                limit_page_length=limit,
                order_by=order_by
            )
        
        frappe.logger().info(f"[Generic Search] Found {len(results)} results")
        
        return {
            "success": True,
            "data": {
                "results": results,
                "count": len(results),
                "doctype": doctype
            }
        }
    
    except Exception as e:
        frappe.logger().error(f"[Generic Search] Error: {str(e)}")
        frappe.log_error(frappe.get_traceback(), "Generic Search Error")
        return {"success": False, "error": str(e)}


def _correct_sql_query(query, doctype_schemas):
    """
    Correct common SQL errors in AI-generated queries.
    """
    if not query or not query.strip():
        return query
    
    corrected = query
    
    # Fix 1: Table name spacing - Handle multi-word DocTypes first
    # "tabSalesOrder" → "`tabSales Order`"
    # Process in order of specificity (longer names first)
    sorted_doctypes = sorted(doctype_schemas.keys(), key=len, reverse=True)
    for doctype in sorted_doctypes:
        if not doctype or not doctype.strip():
            continue
        
        # Create wrong name (no spaces)
        wrong_name = f"tab{doctype.replace(' ', '')}"
        correct_name = f"`tab{doctype}`"
        
        # Only replace if wrong name exists and correct name is not already there
        if wrong_name in corrected and correct_name not in corrected:
            # Use word boundary to avoid partial matches
            corrected = re.sub(r'\b' + re.escape(wrong_name) + r'\b', correct_name, corrected)
            frappe.logger().info(f"[SQL Correction] Fixed table name: {wrong_name} → {correct_name}")
    
    # Fix 2: Handle common table name patterns
    # "Purchase Order" → "Purchase Order" (already has space, just needs quoting)
    for doctype in doctype_schemas.keys():
        if not doctype or not doctype.strip():
            continue
        
        # If doctype has space, ensure it's properly quoted
        if ' ' in doctype:
            unquoted_pattern = f"tab{doctype}"
            quoted_pattern = f"`tab{doctype}`"
            if unquoted_pattern in corrected and quoted_pattern not in corrected:
                corrected = re.sub(r'\b' + re.escape(unquoted_pattern) + r'\b', quoted_pattern, corrected)
    
    # Fix 3: Add missing WHERE for JOINs
    # If query has JOIN but no WHERE, add docstatus = 1
    if "JOIN" in corrected.upper() and "WHERE" not in corrected.upper():
        # Find the FROM clause and add WHERE after it
        from_match = re.search(r'FROM\s+`tab([^`]+)`', corrected, re.IGNORECASE)
        if from_match:
            # Add WHERE docstatus = 1 after FROM
            corrected = re.sub(
                r'(FROM\s+`tab[^`]+`)',
                r'\1 WHERE docstatus = 1',
                corrected,
                count=1,
                flags=re.IGNORECASE
            )
            frappe.logger().info("[SQL Correction] Added WHERE docstatus = 1")
    
    # Fix 4: Ensure proper quoting for table names (more careful regex)
    # Only match if not already quoted and has valid table name
    def quote_table(match):
        table_name = match.group(1)
        if not table_name or not table_name.strip():
            return match.group(0)  # Return original if empty
        # Check if this matches a known doctype
        for doctype in doctype_schemas.keys():
            if doctype.replace(' ', '') == table_name:
                return f"`tab{doctype}`"
        # If no match, return original
        return match.group(0)
    
    # Only replace unquoted tabTableName patterns that aren't already in backticks
    corrected = re.sub(
        r'(?<!`)tab([A-Z][a-zA-Z0-9]+)(?!`)',
        quote_table,
        corrected
    )
    
    # Validate: Check for empty table names
    empty_table_pattern = r'`tab\s*`'
    if re.search(empty_table_pattern, corrected):
        frappe.logger().error(f"[SQL Correction] Found empty table name in query: {corrected[:200]}")
        # Try to extract doctype from schemas
        if doctype_schemas:
            # Use first doctype as fallback
            first_doctype = list(doctype_schemas.keys())[0]
            corrected = re.sub(empty_table_pattern, f"`tab{first_doctype}`", corrected)
            frappe.logger().info(f"[SQL Correction] Replaced empty table with: `tab{first_doctype}`")
    
    return corrected


def _execute_dynamic_query(decision, doctype_schemas):
    """
    Execute a dynamically generated query
    This is the fallback for complex queries
    """
    query_type = decision.get("query_type", "frappe.db.get_all")
    query_code = decision.get("query", "")
    
    frappe.logger().info(f"[Dynamic Query] Type: {query_type}")
    frappe.logger().info(f"[Dynamic Query] Code: {query_code[:200]}")
    
    try:
        # Security: Validate query is safe
        if not _is_safe_query(query_code):
            return {"success": False, "error": "Query contains unsafe operations"}
        
        # Correct common SQL errors
        if query_type == "frappe.db.sql":
            query_code = _correct_sql_query(query_code, doctype_schemas)
            frappe.logger().info(f"[Dynamic Query] Corrected code: {query_code[:200]}")
            
            # Final validation: Ensure query has valid table names
            tables = re.findall(r'`tab([^`]+)`', query_code)
            has_empty_tables = any(not t or not t.strip() for t in tables) if tables else True
            
            if not tables or has_empty_tables:
                # If no valid tables found, try to use detected doctypes
                if doctype_schemas:
                    first_doctype = list(doctype_schemas.keys())[0]
                    frappe.logger().warning(f"[Dynamic Query] No valid table names found, using detected doctype: {first_doctype}")
                    # Replace empty table patterns with first doctype
                    query_code = re.sub(r'`tab\s*`', f"`tab{first_doctype}`", query_code)
                    query_code = re.sub(r'`tab\'\'`', f"`tab{first_doctype}`", query_code)
                    query_code = re.sub(r'`tab`', f"`tab{first_doctype}`", query_code)
                    # Also handle unquoted empty patterns
                    query_code = re.sub(r'\btab\b(?!\w)', f"`tab{first_doctype}`", query_code)
                else:
                    # No schemas available, return error
                    return {"success": False, "error": "Query contains empty table name and no DocTypes detected. Please rephrase your query."}
            
            # Double-check after replacement
            tables_after = re.findall(r'`tab([^`]+)`', query_code)
            if not tables_after or any(not t or not t.strip() for t in tables_after):
                return {"success": False, "error": "Unable to determine table name from query. Please specify the DocType clearly in your query."}
            
            # Update decision with corrected query for potential retries
            decision["query"] = query_code
        
        # Execute the query
        if query_type == "frappe.db.get_all":
            result = _execute_get_all_query(query_code)
        elif query_type == "frappe.db.sql":
            result = _execute_sql_query(query_code)
        else:
            return {"success": False, "error": f"Unsupported query type: {query_type}"}
        
        return {
            "success": True,
            "data": {
                "results": result,
                "count": len(result) if isinstance(result, list) else 1,
                "query_executed": query_code
            }
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Dynamic Query Execution Error")
        return {"success": False, "error": str(e)}


def _execute_get_all_query(query_code):
    """
    Safely execute frappe.db.get_all query
    """
    # Parse the query code to extract parameters
    # Example: "frappe.db.get_all('Customer', filters={'territory': 'USA'}, fields=['name'])"
    
    try:
        # Use eval in a restricted namespace (safer)
        namespace = {
            "frappe": frappe,
            "__builtins__": {}  # Restrict builtins
        }
        
        result = eval(query_code, namespace)
        return result
    
    except Exception as e:
        frappe.logger().error(f"Query execution failed: {str(e)}")
        raise


def _execute_sql_query(query_code):
    """
    Safely execute SQL query
    """
    try:
        # Execute SQL
        result = frappe.db.sql(query_code, as_dict=True)
        return result
    
    except Exception as e:
        frappe.logger().error(f"SQL execution failed: {str(e)}")
        raise


def _is_safe_query(query_code):
    """
    Validate query doesn't contain dangerous operations
    """
    dangerous_keywords = [
        "import ",
        "exec(",
        "eval(",
        "__",
        "delete",
        "drop",
        "truncate",
        "update ",
        "insert ",
        "commit",
        "system",
        "os.",
        "subprocess",
    ]
    
    query_lower = query_code.lower()
    
    for keyword in dangerous_keywords:
        if keyword in query_lower:
            frappe.logger().error(f"Unsafe query detected: contains '{keyword}'")
            return False
    
    return True


def _extract_json_from_response(response):
    """
    Extract JSON from AI response (handles markdown code blocks)
    """
    import re
    
    # Try to find JSON in code blocks
    json_pattern = r'```(?:json)?\s*(\{[\s\S]*?\})\s*```'
    match = re.search(json_pattern, response)
    
    if match:
        json_str = match.group(1)
    else:
        # Try to find raw JSON
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, response)
        if match:
            json_str = match.group(0)
        else:
            return None
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        frappe.logger().error(f"Failed to parse JSON: {json_str[:200]}")
        return None


def _error_response(message):
    """
    Standard error response
    """
    return {
        "status": "error",
        "message": message
    }

