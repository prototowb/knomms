# Refactoring Skill

## Overview

Refactoring is the disciplined technique of restructuring code to improve its internal structure without changing its external behavior. This skill provides patterns for safely improving code quality.

## Core Philosophy

> **Keep tests green. Small steps. Frequent commits.**

Refactoring is NOT rewriting. It's surgical improvement with safety nets.

## When to Refactor

Refactor when code:
- ✅ Works but is hard to understand
- ✅ Has duplication
- ✅ Violates design principles
- ✅ Has poor naming
- ✅ Is overly complex
- ✅ Has code smells

DON'T refactor when:
- ❌ Tests are failing (fix tests first)
- ❌ Adding new features (separate concerns)
- ❌ Under time pressure (schedule it properly)
- ❌ Code will be deleted soon

---

## The Refactoring Process

```
1. Ensure tests exist and pass
   ↓
2. Make small change
   ↓
3. Run tests
   ↓
4. Commit if green
   ↓
5. Repeat
```

### Golden Rule

**Tests must stay green throughout refactoring.**

If tests fail, undo and try smaller steps.

---

## Code Smells

### 1. Long Method

**Smell**: Function > 20-30 lines

**Refactoring**: Extract Method

**Before**:
```python
def process_order(order):
    # Validate
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Negative total")

    # Calculate
    subtotal = sum(item.price * item.quantity for item in order.items)
    tax = subtotal * 0.08
    shipping = 10 if subtotal < 50 else 0
    total = subtotal + tax + shipping

    # Save
    order.subtotal = subtotal
    order.tax = tax
    order.shipping = shipping
    order.total = total
    order.save()

    # Notify
    send_email(order.customer.email, "Order confirmed")
    send_sms(order.customer.phone, "Order confirmed")
```

**After**:
```python
def process_order(order):
    validate_order(order)
    calculate_totals(order)
    save_order(order)
    notify_customer(order)

def validate_order(order):
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Negative total")

def calculate_totals(order):
    order.subtotal = sum(item.price * item.quantity for item in order.items)
    order.tax = order.subtotal * 0.08
    order.shipping = 10 if order.subtotal < 50 else 0
    order.total = order.subtotal + order.tax + order.shipping

def save_order(order):
    order.save()

def notify_customer(order):
    send_email(order.customer.email, "Order confirmed")
    send_sms(order.customer.phone, "Order confirmed")
```

### 2. Duplicate Code

**Smell**: Same code in multiple places

**Refactoring**: Extract common code

**Before**:
```python
def send_welcome_email(user):
    subject = "Welcome!"
    body = f"Hello {user.name}"
    send_email(user.email, subject, body)
    log_email(user.email, subject)

def send_reset_email(user):
    subject = "Password Reset"
    body = f"Reset link: {reset_link}"
    send_email(user.email, subject, body)
    log_email(user.email, subject)
```

**After**:
```python
def send_user_email(user, subject, body):
    send_email(user.email, subject, body)
    log_email(user.email, subject)

def send_welcome_email(user):
    send_user_email(user, "Welcome!", f"Hello {user.name}")

def send_reset_email(user):
    send_user_email(user, "Password Reset", f"Reset link: {reset_link}")
```

### 3. Long Parameter List

**Smell**: Function with > 3-4 parameters

**Refactoring**: Introduce Parameter Object

**Before**:
```python
def create_user(name, email, phone, address, city, state, zip):
    # Too many parameters!
    pass
```

**After**:
```python
class UserInfo:
    def __init__(self, name, email, phone, address):
        self.name = name
        self.email = email
        self.phone = phone
        self.address = address

def create_user(user_info):
    # Single, well-structured parameter
    pass
```

### 4. Large Class

**Smell**: Class with too many responsibilities

**Refactoring**: Extract Class

**Before**:
```python
class User:
    def __init__(self):
        # User data
        self.name = ""
        self.email = ""

        # Authentication
        self.password_hash = ""
        self.last_login = None

        # Permissions
        self.roles = []
        self.permissions = []

        # Notifications
        self.email_preferences = {}
        self.sms_enabled = False

    # 50+ methods handling all these concerns
```

**After**:
```python
class User:
    def __init__(self):
        self.name = ""
        self.email = ""
        self.auth = UserAuthentication()
        self.permissions = UserPermissions()
        self.notifications = UserNotifications()
```

### 5. Magic Numbers

**Smell**: Unexplained constants

**Refactoring**: Replace with Named Constant

**Before**:
```python
if user.age >= 18:  # Why 18?
    allow_access()

price = quantity * 1.08  # What's 1.08?
```

**After**:
```python
LEGAL_AGE = 18
if user.age >= LEGAL_AGE:
    allow_access()

TAX_RATE = 0.08
price = quantity * (1 + TAX_RATE)
```

---

## Refactoring Patterns

### Extract Method

**When**: Function does too much

**Before**:
```python
def print_invoice(invoice):
    print("*" * 50)
    print(f"Invoice #{invoice.id}")
    print(f"Date: {invoice.date}")
    print("*" * 50)
    for item in invoice.items:
        print(f"{item.name}: ${item.price}")
    print("*" * 50)
    print(f"Total: ${invoice.total}")
```

**After**:
```python
def print_invoice(invoice):
    print_header(invoice)
    print_items(invoice.items)
    print_total(invoice.total)

def print_header(invoice):
    print("*" * 50)
    print(f"Invoice #{invoice.id}")
    print(f"Date: {invoice.date}")
    print("*" * 50)

def print_items(items):
    for item in items:
        print(f"{item.name}: ${item.price}")

def print_total(total):
    print("*" * 50)
    print(f"Total: ${total}")
```

### Rename

**When**: Names are unclear

**Before**:
```python
def calc(a, b, c):
    return a * b + c

x = calc(10, 5, 3)
```

**After**:
```python
def calculate_total_with_tax(price, quantity, tax):
    return price * quantity + tax

total = calculate_total_with_tax(10, 5, 3)
```

### Extract Variable

**When**: Complex expression

**Before**:
```python
if (user.age >= 18 and user.has_license) or user.is_admin:
    allow_access()
```

**After**:
```python
is_adult_with_license = user.age >= 18 and user.has_license
can_access = is_adult_with_license or user.is_admin

if can_access:
    allow_access()
```

### Replace Conditional with Polymorphism

**When**: Type checking with if/elif

**Before**:
```python
def get_speed(vehicle):
    if vehicle.type == "car":
        return vehicle.horsepower * 2
    elif vehicle.type == "bike":
        return vehicle.gear_ratio * 10
    elif vehicle.type == "plane":
        return vehicle.engine_thrust * 100
```

**After**:
```python
class Car:
    def get_speed(self):
        return self.horsepower * 2

class Bike:
    def get_speed(self):
        return self.gear_ratio * 10

class Plane:
    def get_speed(self):
        return self.engine_thrust * 100

# Usage
speed = vehicle.get_speed()  # Polymorphic call
```

### Introduce Explaining Variable

**When**: Complex boolean logic

**Before**:
```python
if platform == "windows" and version >= 10 or platform == "mac" and version >= 11:
    install()
```

**After**:
```python
is_supported_windows = platform == "windows" and version >= 10
is_supported_mac = platform == "mac" and version >= 11
is_supported_platform = is_supported_windows or is_supported_mac

if is_supported_platform:
    install()
```

---

## Refactoring Checklist

Before refactoring:
- [ ] All tests pass
- [ ] You understand the code
- [ ] You have time to do it properly

During refactoring:
- [ ] Small, incremental changes
- [ ] Run tests after each change
- [ ] Commit frequently
- [ ] Keep behavior unchanged

After refactoring:
- [ ] All tests still pass
- [ ] Code is more readable
- [ ] Complexity reduced
- [ ] No new bugs introduced

---

## Anti-Patterns

### ❌ Big Bang Refactoring

**Bad**: Rewriting entire module at once

**Good**: Incremental improvements over time

### ❌ Refactoring Without Tests

**Bad**: Changing code with no safety net

**Good**: Write tests first, then refactor

### ❌ Feature + Refactor Together

**Bad**: Adding features while refactoring

**Good**: Separate commits for features and refactoring

### ❌ Premature Optimization

**Bad**: Refactoring for performance without measuring

**Good**: Profile first, optimize bottlenecks only

---

## Refactoring Techniques

### 1. Strangler Fig Pattern

Gradually replace old code:

```
1. Create new implementation alongside old
2. Redirect some traffic to new
3. Monitor and compare
4. Gradually increase new traffic
5. Remove old code when safe
```

### 2. Branch by Abstraction

Refactor without breaking production:

```python
# Step 1: Create abstraction
class PaymentProcessor:
    def process(self, payment):
        raise NotImplementedError

# Step 2: Wrap old code
class OldPaymentProcessor(PaymentProcessor):
    def process(self, payment):
        # Old implementation
        pass

# Step 3: Create new implementation
class NewPaymentProcessor(PaymentProcessor):
    def process(self, payment):
        # New implementation
        pass

# Step 4: Switch (with feature flag)
processor = NewPaymentProcessor() if USE_NEW else OldPaymentProcessor()
processor.process(payment)

# Step 5: Remove old code when stable
```

### 3. Boy Scout Rule

> "Leave code better than you found it."

Small improvements every time you touch code.

---

## Real-World Example

### The Problem

```python
def process_data(d):
    r = []
    for i in d:
        if i['status'] == 'active':
            x = i['value'] * 1.08
            if x > 100:
                r.append({'id': i['id'], 'val': x, 'cat': 'high'})
            else:
                r.append({'id': i['id'], 'val': x, 'cat': 'low'})
    return r
```

**Issues**:
- Poor naming (d, r, i, x)
- Magic number (1.08)
- Complex nested logic
- No extraction of concepts

### The Refactoring

**Step 1: Rename variables**
```python
def process_data(data):
    results = []
    for item in data:
        if item['status'] == 'active':
            adjusted_value = item['value'] * 1.08
            if adjusted_value > 100:
                results.append({'id': item['id'], 'val': adjusted_value, 'cat': 'high'})
            else:
                results.append({'id': item['id'], 'val': adjusted_value, 'cat': 'low'})
    return results
```

**Step 2: Extract magic number**
```python
TAX_RATE = 0.08
HIGH_VALUE_THRESHOLD = 100

def process_data(data):
    results = []
    for item in data:
        if item['status'] == 'active':
            adjusted_value = item['value'] * (1 + TAX_RATE)
            if adjusted_value > HIGH_VALUE_THRESHOLD:
                results.append({'id': item['id'], 'val': adjusted_value, 'cat': 'high'})
            else:
                results.append({'id': item['id'], 'val': adjusted_value, 'cat': 'low'})
    return results
```

**Step 3: Extract methods**
```python
def process_data(data):
    active_items = filter_active(data)
    return [process_item(item) for item in active_items]

def filter_active(data):
    return [item for item in data if item['status'] == 'active']

def process_item(item):
    adjusted_value = apply_tax(item['value'])
    category = categorize_value(adjusted_value)
    return {
        'id': item['id'],
        'val': adjusted_value,
        'cat': category
    }

def apply_tax(value):
    return value * (1 + TAX_RATE)

def categorize_value(value):
    return 'high' if value > HIGH_VALUE_THRESHOLD else 'low'
```

**Step 4: Use data classes (final)**
```python
@dataclass
class ProcessedItem:
    id: int
    value: float
    category: str

def process_data(data: List[Dict]) -> List[ProcessedItem]:
    active_items = filter_active(data)
    return [process_item(item) for item in active_items]

def filter_active(data: List[Dict]) -> List[Dict]:
    return [item for item in data if item['status'] == 'active']

def process_item(item: Dict) -> ProcessedItem:
    adjusted_value = apply_tax(item['value'])
    category = categorize_value(adjusted_value)
    return ProcessedItem(
        id=item['id'],
        value=adjusted_value,
        category=category
    )

def apply_tax(value: float) -> float:
    return value * (1 + TAX_RATE)

def categorize_value(value: float) -> str:
    return 'high' if value > HIGH_VALUE_THRESHOLD else 'low'
```

---

## Key Takeaways

1. **Refactor in small steps** - Keep tests green
2. **Have tests first** - Safety net is essential
3. **One refactoring at a time** - Don't mix changes
4. **Commit frequently** - Easy to undo if needed
5. **Extract, don't inline** - Build abstractions
6. **Name things well** - Clarity over cleverness
7. **Follow Boy Scout Rule** - Continuous improvement

---

*For AI Agents*: Use this skill to improve code quality systematically. Always ensure tests exist and pass before refactoring. Make small, incremental changes and verify behavior remains unchanged. Focus on readability and maintainability over cleverness.
