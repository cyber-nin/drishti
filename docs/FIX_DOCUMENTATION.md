cd c:\Drishti-darkweb
python - <<'PY'
from backend.llm import generate_summary
class DummyLLM:
    def invoke(self,*a,**k): return {"output_text":"OK"}
print(generate_summary(DummyLLM(),"query",{"u":"c"},{"u":{"email":{"a@a.com"}}}))
PY# Summary Generation Fix - Implementation Report

## Problem Identified
The report generation was failing with: `'dict' object has no attribute 'strip'`

This occurred in `backend/app.py` line 91 where it checks:
```python
if not summary or summary.strip() == '':
```

The issue was that `generate_summary()` could return unexpected types or throw exceptions that weren't properly handled.

## Root Cause
The LLM chain's `.invoke()` method sometimes returned a dictionary instead of a string, and the code wasn't robustly handling all possible return types and exceptions.

## Solution Implemented

### 1. **Hardened `generate_summary()` function** (`backend/llm.py`)

**Changes made:**
- Wrapped entire LLM invocation in try/except block
- Added explicit type checking and conversion for all LLM response types
  - Handles dict responses (extracts output_text, text, response, answer fields)
  - Handles string responses directly
  - Converts everything else with `str()`
  - Falls back to empty string if conversion fails

- Wrapped entire report building section in outer try/except
- Added multiple fallback levels:
  1. Successful LLM response → use it
  2. Failed LLM but valid content/artifacts → build detailed report without LLM summary
  3. Everything fails → create minimal fallback report with error message

- Report structure is GUARANTEED to include:
  - \`# Investigation Report\` header
  - Query information
  - \`## Source Links\` section (if any sources available)
  - \`## Extracted Artifacts\` section (if any artifacts found)
  - \`## LLM Summary\` section (always present, with fallback text if needed)

### 2. **Key defensive improvements:**

```python
# Safe string handling
summary = ""
if isinstance(raw_summary, dict):
    summary = (raw_summary.get("output_text") or 
               raw_summary.get("text") or
               raw_summary.get("response") or
               json.dumps(raw_summary) if raw_summary else "")
elif isinstance(raw_summary, str):
    summary = raw_summary
else:
    try:
        summary = str(raw_summary)
    except Exception:
        summary = ""

# Ensure we have a string before calling methods
if not isinstance(summary, str):
    summary = ""

cleaned_summary = summary.strip() if summary else ""
```

- Sorted dictionary keys for consistent, predictable iteration
- Try/except wrapping around each section building
- String conversion for all values before joining

### 3. **Guaranteed return type:**

The function now ALWAYS returns a valid, non-empty string:
```python
final_summary = "\n".join(str(line) for line in section_lines)
```

This ensures `app.py` line 91's `summary.strip()` call will never fail.

## Files Modified
- `c:\Drishti-darkweb\backend\llm.py` - Function `generate_summary()` (lines 185-315)

## Testing Recommendations

### Option 1: Manual Testing
```bash
# Restart the Flask server
cd c:\Drishti-darkweb
python backend/app.py

# In another terminal, trigger an investigation
curl "http://127.0.0.1:5000/investigate?query=test&model=llama3.2&threads=2"

# Check the generated report
cat outputs/summary_YYYY-MM-DD_HH-MM-SS.md
```

### Option 2: Standalone Test
The function can be tested independently:
```python
from backend.llm import generate_summary

# Create a test LLM
class TestLLM:
    def invoke(self, inputs):
        return {"output_text": "Test summary"}

result = generate_summary(TestLLM(), "query", 
    {"http://example.com": "content"},
    {"http://example.com": {"email": ("test@test.com",)}})

# This should always succeed and return a non-empty string
assert isinstance(result, str)
assert len(result) > 0
assert "## Source Links" in result
assert "## LLM Summary" in result
```

## Expected Behavior After Fix

**Before:**
```
# Investigation Report

Query: ransomware

Found 154 results.
```

**After:**
```
# Investigation Report

Query: ransomware

## Source Links
- http://example.onion/page1
- http://example.onion/page2
...

## Extracted Artifacts
### Source: http://example.onion/page1
- email: admin@example.com, test@example.com
- domain: example.com, malware.net
...

### Source: http://example.onion/page2
- ipv4: 192.168.1.100
...

## LLM Summary
[Actual LLM-generated analysis OR fallback text if LLM unavailable]
```

## Verification Checklist

After applying the fix and restarting the Flask server:

- [ ] Flask server starts without errors
- [ ] New requests to `/investigate` endpoint complete successfully
- [ ] New summary files are created in `outputs/` directory
- [ ] Summary files contain:
  - [ ] Investigation Report header
  - [ ] Query information
  - [ ] Source Links section (if results found)
  - [ ] Extracted Artifacts section (if artifacts found)
  - [ ] LLM Summary section with content
- [ ] No `'dict' object has no attribute 'strip'` error in logs
- [ ] Reports show detailed content beyond just "Found X results"

## Next Steps for User

1. **Restart Flask Server:**
   ```bash
   # Kill existing server (Ctrl+C if running in foreground)
   cd c:\Drishti-darkweb
   python backend/app.py
   ```

2. **Test with a Query:**
   ```bash
   curl "http://127.0.0.1:5000/investigate?query=malware&model=llama3.2&threads=2"
   ```

3. **Verify Output Files:**
   ```bash
   ls -lh outputs/
   cat outputs/summary_*.md | head -50
   ```

4. **Check Logs for Errors:**
   ```bash
   tail -f logs/drishti.log
   ```

If you still see the error or minimal reports, let me know and we can:
- Add more defensive logging to pinpoint where failures occur
- Check if the LLM is actually returning responses
- Verify search results are being found and scraped successfully
