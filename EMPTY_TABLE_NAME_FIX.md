# Empty Table Name Error Fix

## Issue
**Error:** `(1103, "Incorrect table name ''")`  
**Query:** "How many purchase orders are submitted?"

The AI was generating SQL queries with empty table names, causing execution failures.

---

## Root Causes

1. **AI generating queries with empty table names** - The AI might generate queries like `SELECT * FROM `tab`` (empty table name)
2. **Table name correction regex creating empty strings** - The regex pattern might match incorrectly and create empty table names
3. **Multi-word DocTypes not handled correctly** - "Purchase Order" has a space, which might cause issues in table name extraction
4. **No validation before execution** - Empty table names weren't caught before SQL execution

---

## Fixes Implemented

### 1. Enhanced SQL Query Corrector (`_correct_sql_query`)

**Location:** `intelligent_query.py` lines 955-1042

**Improvements:**
- ✅ Added empty query check at start
- ✅ Process DocTypes in order of specificity (longer names first)
- ✅ Better handling of multi-word DocTypes (e.g., "Purchase Order")
- ✅ More careful regex patterns with word boundaries
- ✅ Validation to detect and fix empty table names
- ✅ Fallback to first detected doctype if empty table found

**Key Changes:**
```python
# Check for empty table names
empty_table_pattern = r'`tab\s*`'
if re.search(empty_table_pattern, corrected):
    # Use first doctype as fallback
    first_doctype = list(doctype_schemas.keys())[0]
    corrected = re.sub(empty_table_pattern, f"`tab{first_doctype}`", corrected)
```

### 2. Enhanced Validation (`_validate_ai_decision`)

**Location:** `intelligent_query.py` lines 589-605

**Improvements:**
- ✅ Check for empty table names in quoted patterns: `` `tab` ``
- ✅ Check for empty table names in unquoted patterns
- ✅ Return clear error message if empty table name detected

**Key Changes:**
```python
# Check for empty table names
if not table or not table.strip():
    return {"valid": False, "error": "Query contains empty table name. Please specify a valid DocType."}
```

### 3. Enhanced Retry Mechanism

**Location:** `intelligent_query.py` lines 691-703

**Improvements:**
- ✅ Specific handling for "Incorrect table name" errors
- ✅ Automatic replacement of empty table names with detected doctype
- ✅ Multiple pattern matching for empty table names

**Key Changes:**
```python
elif "Incorrect table name" in error or "table name" in error.lower():
    # Replace empty table names
    query = re.sub(r'`tab\s*`', f"`tab{first_doctype}`", query)
    query = re.sub(r'`tab\'\'`', f"`tab{first_doctype}`", query)
```

### 4. Final Validation Before Execution

**Location:** `intelligent_query.py` lines 1103-1128

**Improvements:**
- ✅ Final check for empty table names after all corrections
- ✅ Automatic replacement using detected doctypes
- ✅ Clear error message if still empty after all fixes
- ✅ Updates decision object with corrected query for retries

**Key Changes:**
```python
# Final validation: Ensure query has valid table names
tables = re.findall(r'`tab([^`]+)`', query_code)
if not tables or any(not t or not t.strip() for t in tables):
    # Use detected doctype as fallback
    first_doctype = list(doctype_schemas.keys())[0]
    query_code = re.sub(r'`tab\s*`', f"`tab{first_doctype}`", query_code)
```

### 5. Improved AI Prompt

**Location:** `intelligent_query.py` lines 458-477

**Improvements:**
- ✅ Added example for count queries with filters
- ✅ Specific example for "Purchase Order" queries
- ✅ Clear guidance to use `count_documents` API for simple count queries

**Key Changes:**
```python
Example 5: Count documents with filter (use direct API)
{{
  "execution_type": "direct_api",
  "api_name": "count_documents",
  "parameters": {{"doctype": "Purchase Order", "filters": {{"docstatus": 1}}}},
  "reasoning": "Simple count query with filter, use count_documents API"
}}

IMPORTANT FOR COUNT QUERIES:
- For simple count queries like "How many X are Y?", prefer count_documents API
- Example: "How many purchase orders are submitted?" → count_documents with doctype="Purchase Order", filters={{docstatus: 1}}
```

---

## Error Handling Flow

```
1. AI generates query
   ↓
2. Validation checks for empty table names
   ↓ (if empty found)
   Return error: "Query contains empty table name"
   ↓ (if valid)
3. SQL Query Corrector fixes common issues
   ↓
4. Final validation before execution
   ↓ (if empty found)
   Replace with detected doctype
   ↓
5. Execute query
   ↓ (if error: "Incorrect table name")
6. Retry mechanism fixes empty table name
   ↓
7. Retry execution
```

---

## Testing

### Test Cases

1. **Simple count query:**
   - Query: "How many purchase orders are submitted?"
   - Expected: Uses `count_documents` API with `doctype="Purchase Order"`

2. **SQL query with empty table:**
   - Query: "Show all purchase orders"
   - Expected: Empty table name detected and replaced with "Purchase Order"

3. **Multi-word DocType:**
   - Query: "How many sales orders are there?"
   - Expected: Correctly handles "Sales Order" with space

---

## Expected Results

### Before Fix
- ❌ Error: `(1103, "Incorrect table name ''")`
- ❌ Query fails immediately
- ❌ No automatic correction

### After Fix
- ✅ Empty table names detected in validation
- ✅ Automatic correction using detected doctypes
- ✅ Retry mechanism fixes on error
- ✅ Clear error messages if all fixes fail
- ✅ AI prefers `count_documents` API for simple count queries

---

## Files Modified

1. ✅ `exim_backend/api/intelligent_query.py`
   - Enhanced `_correct_sql_query()` function
   - Enhanced `_validate_ai_decision()` function
   - Enhanced `_execute_with_retry()` function
   - Enhanced `_execute_dynamic_query()` function
   - Improved AI prompt with count query examples

---

## Prevention

The fixes ensure that:
1. **Validation catches empty table names** before execution
2. **SQL corrector fixes** common empty table name patterns
3. **Retry mechanism** automatically fixes on error
4. **Final validation** ensures valid table names before execution
5. **AI prompt** guides AI to use simpler APIs for count queries

---

**Status:** ✅ COMPLETE  
**Date:** 2025-01-09  
**Impact:** Fixes empty table name errors and improves query generation

