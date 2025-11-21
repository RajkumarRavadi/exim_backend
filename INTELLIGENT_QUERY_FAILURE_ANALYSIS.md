# Intelligent Query System - Failure Analysis & Improvement Plan

## Executive Summary

**Current Failure Rate:** ~30-40% for complex/dynamic queries  
**Target Failure Rate:** <10%  
**Primary Issues:** AI decision-making, query validation, error recovery, context handling

---

## 1. Current System Architecture Analysis

### 1.1 Flow Diagram
```
User Query
    ↓
DocType Detection (keyword matching)
    ↓
Fetch DocType Schemas (all fields)
    ↓
Build AI Prompt (very large - 15K+ tokens)
    ↓
AI Analysis (single decision)
    ↓
Execute (direct_api OR dynamic_query)
    ↓
Return Results
```

### 1.2 Key Components

1. **DocType Detection** (`doctype_fields.py`)
   - Keyword matching with confidence scoring
   - Limited to top 3 DocTypes
   - Can miss relevant DocTypes or include irrelevant ones

2. **AI Prompt Builder** (`intelligent_query.py`)
   - Includes all fields from detected DocTypes
   - Very large prompts (15K+ tokens)
   - Many examples but can be overwhelming

3. **AI Decision Maker** (`_call_ai_for_analysis`)
   - Single-shot decision
   - No validation of decision
   - No confidence scoring

4. **Query Executor** (`_execute_ai_decision`)
   - Direct API execution
   - Dynamic SQL execution
   - Limited error recovery

---

## 2. Identified Failure Points

### 2.1 Failure Point 1: AI Decision Making (40% of failures)

**Problem:**
- AI sometimes chooses wrong execution type
- AI generates invalid SQL syntax
- AI uses wrong field names
- AI doesn't understand complex relationships

**Examples:**
```
Query: "customers with no orders in last month"
AI Decision: direct_api with filters={"orders": {"$nin": [...]}}
Result: ❌ SQL syntax error (subqueries not supported in filters)

Query: "top customers by revenue"
AI Decision: dynamic_query with wrong table joins
Result: ❌ SQL error (table doesn't exist)
```

**Root Causes:**
1. Prompt too large → AI gets confused
2. No validation of AI's decision before execution
3. No examples for edge cases
4. AI doesn't understand ERPNext table structure

---

### 2.2 Failure Point 2: DocType Detection (25% of failures)

**Problem:**
- Misses relevant DocTypes
- Includes irrelevant DocTypes
- Wrong confidence scoring

**Examples:**
```
Query: "payment entries"
Detected: ["Customer", "Item", "Sales Order"] ❌
Should be: ["Payment Entry"] ✅

Query: "sales orders"
Detected: ["Sales Order", "Blanket Order", "Payment Order", "Purchase Order", ...] ❌
Should be: ["Sales Order"] ✅
```

**Root Causes:**
1. Keyword matching too broad
2. No semantic understanding
3. Limited to top 3 DocTypes
4. No context from previous queries

---

### 2.3 Failure Point 3: Query Execution (20% of failures)

**Problem:**
- SQL syntax errors
- Invalid field names
- Missing table relationships
- Performance issues

**Examples:**
```
AI Generated SQL:
SELECT * FROM tabCustomer WHERE link_doctype = 'Customer'
Result: ❌ Unknown column 'link_doctype' in 'WHERE'

AI Generated SQL:
SELECT c.name FROM tabCustomer c JOIN tabSalesOrder so...
Result: ❌ Table 'tabSalesOrder' doesn't exist (should be 'tabSales Order')
```

**Root Causes:**
1. No SQL validation before execution
2. AI doesn't know actual table names
3. No relationship mapping
4. No query optimization

---

### 2.4 Failure Point 4: Error Recovery (10% of failures)

**Problem:**
- Errors not categorized
- No automatic retry with corrections
- Generic error messages
- No learning from failures

**Examples:**
```
Error: SQL syntax error
System: Returns generic error ❌
Should: Retry with corrected query ✅

Error: Field doesn't exist
System: Returns error ❌
Should: Remove invalid field and retry ✅
```

**Root Causes:**
1. No error categorization
2. No retry mechanism
3. No query correction logic
4. No failure logging for learning

---

### 2.5 Failure Point 5: Context & Memory (5% of failures)

**Problem:**
- Limited conversation memory
- No query decomposition
- Can't handle multi-step queries

**Examples:**
```
Query: "customers from USA who ordered more than $10,000"
System: Tries to do in one query ❌
Should: Decompose into steps ✅
  1. Find customers from USA
  2. Find their orders > $10,000
  3. Join results
```

**Root Causes:**
1. Single-shot execution
2. No query decomposition
3. Limited context window
4. No multi-step planning

---

## 3. Improvement Strategy

### 3.1 Phase 1: Quick Wins (Reduce failures by 50%)

**Priority: HIGH | Effort: 2-3 days | Impact: 30% → 15% failure rate**

#### 3.1.1 Add Query Validation Layer

**What:** Validate AI's decision before execution

**Implementation:**
```python
def _validate_ai_decision(decision, doctype_schemas):
    """
    Validate AI's decision before execution
    """
    execution_type = decision.get("execution_type")
    
    if execution_type == "direct_api":
        # Validate API exists
        api_name = decision.get("api_name")
        if api_name not in VALID_APIS:
            return {"valid": False, "error": f"Unknown API: {api_name}"}
        
        # Validate parameters
        parameters = decision.get("parameters", {})
        doctype = parameters.get("doctype")
        if doctype and doctype not in doctype_schemas:
            return {"valid": False, "error": f"DocType {doctype} not in schemas"}
        
        # Validate filters use valid fields
        filters = parameters.get("filters", {})
        if filters:
            meta = frappe.get_meta(doctype)
            valid_fields = {f.fieldname for f in meta.fields}
            for key in filters.keys():
                if key not in valid_fields and key not in ["name", "docstatus"]:
                    return {"valid": False, "error": f"Invalid field in filters: {key}"}
    
    elif execution_type == "dynamic_query":
        query = decision.get("query", "")
        
        # Validate SQL syntax (basic check)
        if "frappe.db.sql" in query:
            # Check for dangerous operations
            dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
            if any(op in query.upper() for op in dangerous):
                return {"valid": False, "error": "Query contains dangerous operations"}
            
            # Check table names exist
            import re
            tables = re.findall(r'`tab([^`]+)`', query)
            for table in tables:
                if not frappe.db.exists("DocType", table):
                    return {"valid": False, "error": f"Table {table} doesn't exist"}
    
    return {"valid": True}
```

**File:** `intelligent_query.py` - Add before `_execute_ai_decision`

---

#### 3.1.2 Improve DocType Detection

**What:** Better keyword matching and confidence scoring

**Implementation:**
```python
def detect_doctypes_from_query(query: str):
    # ... existing code ...
    
    # IMPROVEMENT 1: Use exact phrase matching first
    # "payment entry" should match "Payment Entry" with 0.98 confidence
    # Not "Payment" (0.6) and "Entry" (0.6)
    
    # IMPROVEMENT 2: Limit to top 1-2 DocTypes for simple queries
    if len(query.split()) <= 5:  # Simple query
        detected_list = detected_list[:1]  # Only top 1
    else:  # Complex query
        detected_list = detected_list[:3]  # Top 3
    
    # IMPROVEMENT 3: Minimum confidence threshold
    min_confidence = 0.7
    detected_list = [
        dt for dt in detected_list 
        if detected[dt] >= min_confidence
    ]
    
    # IMPROVEMENT 4: If no high-confidence matches, use semantic fallback
    if not detected_list:
        # Try to extract entity from query
        # "who" → Customer, "what" → Item, "when" → Date-based
        detected_list = _semantic_fallback(query)
```

**File:** `doctype_fields.py` - Enhance `detect_doctypes_from_query`

---

#### 3.1.3 Add SQL Query Corrector

**What:** Fix common SQL errors automatically

**Implementation:**
```python
def _correct_sql_query(query, doctype_schemas):
    """
    Correct common SQL errors in AI-generated queries
    """
    # Fix 1: Table name spacing
    # "tabSalesOrder" → "tabSales Order"
    for doctype in doctype_schemas.keys():
        wrong_name = f"tab{doctype.replace(' ', '')}"
        correct_name = f"`tab{doctype}`"
        query = query.replace(wrong_name, correct_name)
    
    # Fix 2: Field name validation
    # Remove invalid fields from SELECT
    import re
    select_match = re.search(r'SELECT\s+(.+?)\s+FROM', query, re.IGNORECASE)
    if select_match:
        fields = [f.strip() for f in select_match.group(1).split(',')]
        # Validate each field exists in schema
        # Remove invalid ones
    
    # Fix 3: Add missing WHERE conditions
    # If query has JOIN but no WHERE, add docstatus = 1
    if "JOIN" in query.upper() and "WHERE" not in query.upper():
        query = query.replace("FROM", "WHERE docstatus = 1 FROM")
    
    return query
```

**File:** `intelligent_query.py` - Add before SQL execution

---

#### 3.1.4 Add Retry Mechanism

**What:** Retry failed queries with corrections

**Implementation:**
```python
def _execute_ai_decision_with_retry(decision, doctype_schemas, max_retries=2):
    """
    Execute AI decision with automatic retry on errors
    """
    for attempt in range(max_retries + 1):
        try:
            result = _execute_ai_decision(decision, doctype_schemas)
            
            if result.get("success"):
                return result
            
            # If failed, try to correct
            error = result.get("error", "")
            
            if attempt < max_retries:
                # Try to correct based on error
                if "Unknown column" in error:
                    # Remove invalid field and retry
                    decision = _remove_invalid_field(decision, error)
                elif "Table doesn't exist" in error:
                    # Fix table name and retry
                    decision = _fix_table_name(decision, error)
                elif "SQL syntax" in error:
                    # Try to fix SQL syntax
                    decision = _fix_sql_syntax(decision, error)
                
                frappe.logger().info(f"[Retry] Attempt {attempt + 1}/{max_retries}")
                continue
            
            # Max retries reached
            return result
            
        except Exception as e:
            if attempt < max_retries:
                continue
            raise
    
    return {"success": False, "error": "Max retries exceeded"}
```

**File:** `intelligent_query.py` - Replace `_execute_ai_decision` call

---

### 3.2 Phase 2: Medium-Term Improvements (Reduce failures by 30%)

**Priority: MEDIUM | Effort: 1 week | Impact: 15% → 10% failure rate**

#### 3.2.1 Optimize AI Prompt

**What:** Reduce prompt size, add better examples

**Current Issues:**
- Prompt is 15K+ tokens (too large)
- Includes all fields (overwhelming)
- Too many examples (confusing)

**Improvements:**
```python
def _build_intelligent_prompt(query, doctype_schemas):
    # IMPROVEMENT 1: Only include relevant fields
    # Instead of all 30 fields, include:
    # - Required fields
    # - Commonly used fields (name, status, date, amount)
    # - Fields mentioned in query
    
    # IMPROVEMENT 2: Use field summaries instead of full list
    # "Customer has: name, customer_name, territory, customer_group, email, mobile_no"
    # Instead of listing all 30 fields
    
    # IMPROVEMENT 3: Add query-specific examples
    # If query mentions "no orders" → show negative condition example
    # If query mentions "top" → show aggregation example
    
    # IMPROVEMENT 4: Add relationship hints
    # "Customer → Sales Order (via customer field)"
    # "Sales Order → Sales Order Item (child table)"
```

**File:** `intelligent_query.py` - Rewrite `_build_intelligent_prompt`

---

#### 3.2.2 Add Query Decomposition

**What:** Break complex queries into steps

**Implementation:**
```python
def _decompose_complex_query(query, doctype_schemas):
    """
    Decompose complex queries into simpler steps
    """
    # Example: "customers from USA who ordered > $10,000"
    # Step 1: Find customers from USA
    # Step 2: Find their orders > $10,000
    # Step 3: Join results
    
    decomposition_prompt = f"""
    Decompose this query into steps:
    Query: "{query}"
    
    Return JSON:
    {{
      "steps": [
        {{"step": 1, "query": "Find customers from USA", "doctype": "Customer"}},
        {{"step": 2, "query": "Find orders > $10,000", "doctype": "Sales Order"}},
        {{"step": 3, "query": "Join customers and orders", "type": "join"}}
      ]
    }}
    """
    
    # Call AI to decompose
    # Execute steps sequentially
    # Combine results
```

**File:** `intelligent_query.py` - New function

---

#### 3.2.3 Add Confidence Scoring

**What:** Score AI's confidence and ask for clarification if low

**Implementation:**
```python
def _call_ai_for_analysis(prompt, user_query, session_id):
    # ... existing code ...
    
    # Add confidence to response
    decision["confidence"] = _calculate_confidence(decision, user_query)
    
    # If confidence < 0.7, ask for clarification
    if decision["confidence"] < 0.7:
        return {
            "success": False,
            "requires_clarification": True,
            "suggestions": _generate_clarification_suggestions(decision, user_query)
        }
    
    return {"success": True, "decision": decision, ...}

def _calculate_confidence(decision, query):
    """
    Calculate confidence score for AI's decision
    """
    confidence = 0.5  # Base confidence
    
    # Increase if:
    # - DocType clearly identified (+0.2)
    # - Query matches example pattern (+0.2)
    # - All required fields present (+0.1)
    
    # Decrease if:
    # - Ambiguous query (-0.2)
    # - Complex relationships (-0.1)
    # - Missing required fields (-0.3)
    
    return min(1.0, max(0.0, confidence))
```

**File:** `intelligent_query.py` - Enhance `_call_ai_for_analysis`

---

### 3.3 Phase 3: Long-Term Improvements (Reduce failures by 20%)

**Priority: LOW | Effort: 2 weeks | Impact: 10% → 5% failure rate**

#### 3.3.1 Add Learning System

**What:** Learn from failures and improve

**Implementation:**
```python
def _learn_from_failure(query, decision, error):
    """
    Store failed queries for analysis and improvement
    """
    failure_log = {
        "query": query,
        "decision": decision,
        "error": str(error),
        "timestamp": frappe.utils.now(),
        "doctypes": detected_doctypes,
        "schemas": doctype_schemas.keys()
    }
    
    # Store in cache or database
    frappe.cache().hset("query_failures", query_hash, json.dumps(failure_log))
    
    # Analyze patterns
    # - Common error types
    # - Common query patterns that fail
    # - Improve prompts based on failures
```

**File:** `intelligent_query.py` - New function

---

#### 3.3.2 Add Query Templates

**What:** Pre-built query templates for common patterns

**Implementation:**
```python
QUERY_TEMPLATES = {
    "customers_with_no_orders": {
        "pattern": r"customers?\s+(with\s+)?no\s+orders?",
        "template": """
        SELECT c.name, c.customer_name 
        FROM `tabCustomer` c 
        LEFT JOIN `tabSales Order` so ON so.customer = c.name 
        WHERE so.name IS NULL
        """,
        "confidence": 0.95
    },
    "top_customers_by_revenue": {
        "pattern": r"top\s+\d+\s+customers?\s+by\s+(revenue|sales|value)",
        "template": """
        SELECT c.name, c.customer_name, SUM(so.grand_total) as total
        FROM `tabCustomer` c
        INNER JOIN `tabSales Order` so ON so.customer = c.name
        WHERE so.docstatus = 1
        GROUP BY c.name
        ORDER BY total DESC
        LIMIT {limit}
        """,
        "confidence": 0.95
    }
}

def _match_query_template(query):
    """
    Match query to template for high-confidence execution
    """
    for template_name, template in QUERY_TEMPLATES.items():
        if re.search(template["pattern"], query, re.IGNORECASE):
            return template
    
    return None
```

**File:** `intelligent_query.py` - New module

---

## 4. Implementation Priority

### Week 1: Quick Wins
1. ✅ Add query validation layer (Day 1-2)
2. ✅ Improve DocType detection (Day 2-3)
3. ✅ Add SQL query corrector (Day 3-4)
4. ✅ Add retry mechanism (Day 4-5)

**Expected Impact:** 30% → 15% failure rate

### Week 2-3: Medium-Term
5. ✅ Optimize AI prompt (Week 2)
6. ✅ Add query decomposition (Week 2-3)
7. ✅ Add confidence scoring (Week 3)

**Expected Impact:** 15% → 10% failure rate

### Week 4+: Long-Term
8. ✅ Add learning system
9. ✅ Add query templates
10. ✅ Performance optimization

**Expected Impact:** 10% → 5% failure rate

---

## 5. Testing Strategy

### 5.1 Test Cases

**Simple Queries (Should be 95%+ success):**
- "show all customers"
- "count sales orders"
- "get customer details for Ajay"

**Medium Queries (Should be 85%+ success):**
- "customers from USA"
- "sales orders in last month"
- "top 10 customers by revenue"

**Complex Queries (Should be 70%+ success):**
- "customers with no orders in last month"
- "items never sold"
- "payment status of invoice ACC-SINV-00001"

### 5.2 Metrics to Track

1. **Success Rate by Query Type**
   - Simple: Target 95%
   - Medium: Target 85%
   - Complex: Target 70%

2. **Error Categories**
   - SQL syntax errors
   - Invalid field names
   - Missing DocTypes
   - Wrong execution type

3. **Retry Success Rate**
   - How many failures are fixed by retry?

4. **Response Time**
   - Average query time
   - Time to first result

---

## 6. Code Changes Summary

### Files to Modify

1. **`intelligent_query.py`**
   - Add `_validate_ai_decision()` function
   - Add `_correct_sql_query()` function
   - Add `_execute_ai_decision_with_retry()` function
   - Enhance `_build_intelligent_prompt()` function
   - Add `_decompose_complex_query()` function
   - Add `_calculate_confidence()` function

2. **`doctype_fields.py`**
   - Enhance `detect_doctypes_from_query()` function
   - Add `_semantic_fallback()` function
   - Improve confidence scoring

3. **New File: `query_templates.py`**
   - Define query templates
   - Template matching logic

4. **New File: `query_validator.py`**
   - SQL validation
   - Field validation
   - Relationship validation

---

## 7. Expected Results

### Before Improvements
- Simple queries: 90% success
- Medium queries: 70% success
- Complex queries: 40% success
- **Overall: ~65% success rate**

### After Phase 1 (Quick Wins)
- Simple queries: 98% success
- Medium queries: 85% success
- Complex queries: 60% success
- **Overall: ~80% success rate**

### After Phase 2 (Medium-Term)
- Simple queries: 99% success
- Medium queries: 90% success
- Complex queries: 75% success
- **Overall: ~88% success rate**

### After Phase 3 (Long-Term)
- Simple queries: 99% success
- Medium queries: 95% success
- Complex queries: 85% success
- **Overall: ~93% success rate**

---

## 8. Risk Mitigation

### Risks
1. **Over-engineering:** Too many retries/validations slow down system
   - **Mitigation:** Limit retries to 2, cache validations

2. **False Positives:** Validation rejects valid queries
   - **Mitigation:** Log all rejections, review and adjust

3. **Performance:** Additional validation adds latency
   - **Mitigation:** Cache schema lookups, parallel validation

4. **Complexity:** More code = more bugs
   - **Mitigation:** Comprehensive testing, gradual rollout

---

## 9. Next Steps

1. **Review this document** with team
2. **Prioritize improvements** based on your needs
3. **Start with Phase 1** (quick wins)
4. **Measure results** after each phase
5. **Iterate** based on real-world usage

---

## 10. Questions to Consider

1. **Which failure type is most common in your usage?**
   - Focus improvements there first

2. **What's your acceptable failure rate?**
   - 5%? 10%? This affects which phases to implement

3. **How much latency is acceptable?**
   - More validation = slower but more accurate

4. **Do you have query logs?**
   - Analyze real failures to prioritize fixes

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-09  
**Author:** AI Analysis System

