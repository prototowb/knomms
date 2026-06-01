# Debugging & Troubleshooting Skill

## Overview

Debugging is the systematic process of identifying, isolating, and fixing software defects. This skill provides proven methodologies for efficient debugging across any codebase or technology stack.

## Core Philosophy

> **Observe → Hypothesize → Test → Repeat**

Debugging is science, not guesswork. Form hypotheses, test them systematically, and follow the evidence.

## When to Use This Skill

Use systematic debugging when:
- ✅ Code produces unexpected results
- ✅ Tests are failing
- ✅ Errors or exceptions occur
- ✅ Performance issues arise
- ✅ Integration problems surface
- ✅ Production incidents occur

Skip formal debugging for:
- ❌ Syntax errors (use linter/compiler)
- ❌ Simple typos (code review catches these)
- ❌ Missing dependencies (package manager handles)
- ❌ Configuration issues (check config first)

## The Scientific Method for Debugging

```
1. OBSERVE
   ↓
2. REPRODUCE
   ↓
3. ISOLATE
   ↓
4. HYPOTHESIZE
   ↓
5. TEST
   ↓
6. FIX
   ↓
7. VERIFY
   ↓
8. PREVENT
```

---

## Step 1: OBSERVE - Gather Evidence

### What to Collect

**Error Messages**:
- Full error text (don't truncate!)
- Stack traces
- Error codes
- Line numbers

**Symptoms**:
- What's broken?
- What's the expected behavior?
- What's the actual behavior?
- When did it start?
- What changed recently?

**Context**:
- Environment (dev, staging, prod)
- Browser/OS/platform
- User actions leading to issue
- Frequency (always, sometimes, once)

### Observation Techniques

**Example** (Python):
```python
# Before debugging
result = calculate_total(items)  # Returns wrong value

# Add observation points
print(f"DEBUG: items = {items}")
result = calculate_total(items)
print(f"DEBUG: result = {result}")
print(f"DEBUG: expected = {expected_total}")
```

**Example** (JavaScript):
```javascript
// Use console.log strategically
console.log('DEBUG: Input:', input);
console.log('DEBUG: Processed:', processedData);
console.log('DEBUG: Output:', output);

// Use console.table for arrays/objects
console.table(users);
```

**Key Principle**: **Don't assume anything. Verify everything.**

---

## Step 2: REPRODUCE - Make It Happen Reliably

### Reproduction Criteria

A bug is reproducible when you can:
1. List exact steps to trigger it
2. Observe it consistently
3. Demonstrate it to others

### Minimal Reproduction Case

**Goal**: Simplest possible code that demonstrates the bug

**Example**:
```python
# Instead of running entire app
# Create minimal test case

def test_bug_reproduction():
    """Minimal case showing the bug"""
    # Arrange
    data = [1, 2, 3]

    # Act
    result = buggy_function(data)

    # Assert - This should pass but fails
    assert result == 6, f"Expected 6 but got {result}"
```

### If You Can't Reproduce

- Bug may be intermittent (race condition, timing issue)
- Environment-specific (works locally, fails in prod)
- Data-dependent (specific inputs trigger it)
- User-specific (permissions, settings)

**Solution**: Add more logging and wait for next occurrence

---

## Step 3: ISOLATE - Narrow the Scope

### Divide and Conquer

**Binary Search Debugging**:

```
1. Identify "works" point and "broken" point
2. Test the midpoint
3. Narrow to half with the bug
4. Repeat until you find exact location
```

**Example** (Git bisect):
```bash
git bisect start
git bisect bad           # Current version is broken
git bisect good abc123   # This commit was working
# Git will checkout midpoint - test it
git bisect bad           # or good
# Repeat until exact commit found
```

### Isolation Techniques

**Comment Out Code**:
```python
# result = complex_calculation(data)
result = 42  # Hardcode to isolate problem

# If problem goes away → bug is in complex_calculation()
# If problem persists → bug is elsewhere
```

**Use Breakpoints**:
```python
# Add debugger breakpoint
import pdb; pdb.set_trace()

# Or use IDE breakpoints
# Inspect variables at exact moment of failure
```

**Simplify Inputs**:
```python
# Instead of complex real data
items = [{'id': 1, 'name': 'A', 'price': 10, ...}, ...]

# Use minimal data
items = [{'price': 10}]
```

---

## Step 4: HYPOTHESIZE - Form Theories

### Good Hypothesis Characteristics

1. **Specific**: "The null check is missing" not "Something's wrong"
2. **Testable**: You can verify if it's true or false
3. **Evidence-based**: Based on observations, not guesses

### Common Bug Patterns

**Off-by-one errors**:
```python
# Hypothesis: Loop goes one iteration too far
for i in range(len(items)):  # Should be range(len(items) - 1)?
    compare(items[i], items[i + 1])  # Index out of bounds!
```

**Null/undefined checks**:
```javascript
// Hypothesis: data can be null
const result = data.map(x => x.value);  // Crashes if data is null
// Fix: Add null check
const result = data?.map(x => x.value) ?? [];
```

**Type mismatches**:
```python
# Hypothesis: Mixing strings and integers
total = "10" + 20  # "1020" instead of 30
```

**Scope issues**:
```javascript
// Hypothesis: Variable scope problem
for (var i = 0; i < 5; i++) {  // var not let
    setTimeout(() => console.log(i), 100);
}
// Prints "5" five times, not "0,1,2,3,4"
```

---

## Step 5: TEST - Verify Your Hypothesis

### Testing Methods

**Add Assertions**:
```python
def process_data(data):
    assert data is not None, "Data cannot be None"
    assert len(data) > 0, "Data cannot be empty"
    assert all(isinstance(item, dict) for item in data), "All items must be dicts"

    # Continue processing...
```

**Print Debugging** (when debugger unavailable):
```python
# Strategic prints
print(f"CHECKPOINT 1: data = {data}")
result = transform(data)
print(f"CHECKPOINT 2: result = {result}")
```

**Write a Test**:
```python
def test_hypothesis_null_handling():
    """Test: Function should handle None input"""
    result = buggy_function(None)
    assert result is not None, "Should return default, not None"
```

**Use Debugger**:
```python
# Interactive debugging
import pdb
pdb.set_trace()

# Commands:
# n - next line
# s - step into function
# c - continue
# p variable - print variable
# l - list code around current line
```

---

## Step 6: FIX - Apply the Solution

### Fix Guidelines

**1. Fix the Root Cause, Not Symptoms**

❌ **Bad** (symptom fix):
```python
# Silencing the error
try:
    result = items[index]
except IndexError:
    result = None  # Hiding the problem!
```

✅ **Good** (root cause fix):
```python
# Fixing the logic
if index < len(items):
    result = items[index]
else:
    result = default_value
```

**2. Make Minimal Changes**

- Change only what's necessary
- One bug fix per commit
- Don't refactor while fixing bugs

**3. Add Defensive Code**

```python
def process_user(user_id):
    # Validate inputs
    if not isinstance(user_id, int):
        raise TypeError(f"user_id must be int, got {type(user_id)}")

    if user_id <= 0:
        raise ValueError(f"user_id must be positive, got {user_id}")

    # Rest of function...
```

---

## Step 7: VERIFY - Confirm the Fix

### Verification Checklist

- [ ] Original failing test now passes
- [ ] All other tests still pass
- [ ] Manual testing shows correct behavior
- [ ] Edge cases handled
- [ ] No new bugs introduced
- [ ] Performance not degraded

### Regression Test

```python
def test_bug_123_fixed():
    """
    Regression test for Bug #123: NullPointerException in user login

    Before fix: login(None) crashed
    After fix: login(None) returns error gracefully
    """
    result = login(None)
    assert result.success is False
    assert result.error == "Invalid credentials"
```

---

## Step 8: PREVENT - Stop Future Occurrences

### Prevention Strategies

**1. Add Tests**:
```python
# Test the bug scenario
def test_edge_case_empty_list():
    """Prevent regression of Bug #456"""
    result = process_items([])
    assert result == []  # Should handle empty gracefully
```

**2. Improve Error Handling**:
```python
# Before: Silent failure
value = config.get('key')

# After: Clear error message
value = config.get('key')
if value is None:
    raise ConfigError("Missing required config: 'key'")
```

**3. Add Validation**:
```python
# Validate at boundaries
def api_endpoint(data):
    schema.validate(data)  # Fail fast if data is invalid
    return process(data)
```

**4. Document Gotchas**:
```python
def complex_function(data):
    """
    Process data with complex rules.

    Note: This function REQUIRES data to be sorted.
    If data is unsorted, results will be incorrect.

    Args:
        data: Sorted list of items
    """
```

---

## Debugging Techniques

### Rubber Duck Debugging

**Method**: Explain the problem out loud to an inanimate object

**Why It Works**:
- Forces you to articulate assumptions
- Often reveals flaws in logic
- Slows down thinking

**Example**:
```
"So, this function takes a list... wait, what if the list is empty?
I never check for that! That's the bug!"
```

### Print Debugging

**Strategic Placement**:
```python
def complex_algorithm(data):
    print(f"START: data = {data}")

    step1 = transform(data)
    print(f"AFTER TRANSFORM: step1 = {step1}")

    step2 = filter(step1)
    print(f"AFTER FILTER: step2 = {step2}")

    result = aggregate(step2)
    print(f"FINAL: result = {result}")

    return result
```

### Binary Search Debugging

**Process**:
1. Code works at line 1
2. Code broken at line 100
3. Test line 50 → broken
4. Test line 25 → works
5. Test line 37 → broken
6. Test line 31 → works
7. Bug is between lines 31-37

### The Wolf Fence Algorithm

> "There's one wolf in Alaska. How do you find it?"
> "Build a fence across Alaska. If wolf howls, it's on one side. Repeat."

**Apply to Code**:
```python
# Split code in half
if True:  # First half
    part1()
else:  # Second half
    part2()

# Which half has the bug?
# Split that half again
```

---

## Debugging Tools

### Language-Specific Debuggers

**Python**:
```python
import pdb
pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

**JavaScript**:
```javascript
debugger;  // Browser will pause here

// Or use browser DevTools
console.log(), console.table(), console.trace()
```

**IDE Debuggers**:
- Set breakpoints
- Step through code
- Inspect variables
- Evaluate expressions
- Watch variables

### Logging Best Practices

```python
import logging

logging.debug("Detailed info for diagnosing problems")
logging.info("Confirmation that things are working")
logging.warning("Something unexpected but not an error")
logging.error("Error occurred but app can continue")
logging.critical("Serious error, app may crash")

# Example
logging.debug(f"Processing user_id={user_id}, data={data}")
```

---

## Common Debugging Scenarios

### Intermittent Bugs

**Causes**:
- Race conditions
- Timing issues
- Non-deterministic inputs

**Solution**:
```python
# Add extensive logging
import logging
import traceback

try:
    result = flaky_function()
except Exception as e:
    logging.error(f"Flaky function failed: {e}")
    logging.error(f"Stack trace: {traceback.format_exc()}")
    logging.error(f"Context: {relevant_state}")
    raise
```

### Production-Only Bugs

**Can't Reproduce Locally**:
- Environment differences
- Data differences
- Scale differences

**Solution**:
1. Add feature flags to enable debug logging in prod
2. Capture request/response for failing cases
3. Sanitize and import prod data to dev
4. Use production-like environment (staging)

### Performance Issues

**Debugging Slow Code**:
```python
import time

def debug_performance():
    start = time.time()

    step1()
    print(f"Step 1: {time.time() - start:.2f}s")

    step2()
    print(f"Step 2: {time.time() - start:.2f}s")

    step3()
    print(f"Step 3: {time.time() - start:.2f}s")
```

**Or use profiler**:
```python
import cProfile
cProfile.run('slow_function()')
```

---

## Debugging Checklist

Before you start:
- [ ] Can you reproduce the bug?
- [ ] Do you have error messages/stack traces?
- [ ] What changed recently?

During debugging:
- [ ] Have you verified your assumptions?
- [ ] Have you checked the simplest explanation?
- [ ] Have you isolated the problem?
- [ ] Have you formed a testable hypothesis?

After fixing:
- [ ] Does the fix address root cause?
- [ ] Do all tests pass?
- [ ] Did you add a regression test?
- [ ] Did you document the fix?

---

## Anti-Patterns to Avoid

### ❌ Random Changes

**Bad**:
```
"Let me try changing this and see if it works..."
"Maybe if I restart it 10 times..."
"Let me tweak these settings randomly..."
```

**Why Bad**: No learning, wastes time, may introduce new bugs

### ❌ Ignoring Error Messages

**Bad**:
```python
try:
    risky_operation()
except:  # Catch everything, say nothing
    pass
```

**Why Bad**: Hides valuable diagnostic information

### ❌ Not Reproducing First

**Bad**: Trying to fix without reproducing

**Why Bad**: How do you know if your fix works?

### ❌ Fixing Multiple Bugs at Once

**Bad**: "While I'm here, let me fix these other issues..."

**Why Bad**: Can't tell which fix solved which problem

---

## Real-World Example

### The Bug

```python
def calculate_average(numbers):
    return sum(numbers) / len(numbers)

# Sometimes returns wrong answer!
```

### The Investigation

**1. OBSERVE**:
- User reports: "Average is wrong"
- Input: `[10, 20, 30]`
- Expected: `20.0`
- Actual: `20` (integer!)

**2. REPRODUCE**:
```python
result = calculate_average([10, 20, 30])
print(f"Result: {result}, Type: {type(result)}")
# Output: Result: 20, Type: <class 'int'>
```

**3. ISOLATE**:
```python
# Is it sum() or len() or division?
s = sum([10, 20, 30])  # 60
l = len([10, 20, 30])  # 3
r = s / l              # 20 (int in Python 2, float in Python 3)
```

**4. HYPOTHESIZE**:
- Maybe Python 2 vs 3 division behavior?
- Or integer division being used?

**5. TEST**:
```python
# Python 2: 60 / 3 = 20 (integer division)
# Python 3: 60 / 3 = 20.0 (float division)
```

**6. FIX**:
```python
def calculate_average(numbers):
    return float(sum(numbers)) / len(numbers)  # Force float
    # Or: from __future__ import division  (Python 2)
```

**7. VERIFY**:
```python
assert calculate_average([10, 20, 30]) == 20.0
assert isinstance(calculate_average([10, 20, 30]), float)
```

**8. PREVENT**:
```python
def test_average_returns_float():
    """Regression test: average should always return float"""
    result = calculate_average([10, 20, 30])
    assert isinstance(result, float)
    assert result == 20.0
```

---

## Key Takeaways

1. **Be Systematic**: Follow the 8-step process
2. **Verify Assumptions**: Don't guess, check
3. **Reproduce First**: Can't fix what you can't reproduce
4. **Isolate the Problem**: Binary search to narrow scope
5. **Fix Root Cause**: Not symptoms
6. **Add Tests**: Prevent regression
7. **Document**: Help future debuggers

---

## Resources

### Tools
- Debuggers (pdb, gdb, lldb, Chrome DevTools)
- Profilers (cProfile, perf, Chrome Performance)
- Logging frameworks
- Error tracking (Sentry, Rollbar)

### Further Reading
- "Debugging" by David Agans
- "Why Programs Fail" by Andreas Zeller
- "The Practice of Programming" by Kernighan & Pike

---

*For AI Agents*: This skill provides systematic debugging patterns. Use these techniques when investigating code issues, but adapt based on the specific language, framework, and context. The core principles (observe, hypothesize, test) apply universally.
