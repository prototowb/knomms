# Security Auditing Skill

**Capability Type**: Skill
**Category**: Security
**Complexity**: Advanced
**Estimated Time**: 4-8 hours (varies by codebase size)

## Overview

The Security Auditing skill provides a comprehensive framework for identifying, assessing, and remediating security vulnerabilities in software projects. This skill covers everything from dependency scanning to code-level security reviews, helping teams build secure applications.

## When to Use This Skill

Use this skill when you need to:

- **Pre-Release Security Review**: Audit code before production deployment
- **Regular Security Assessments**: Periodic security health checks
- **Compliance Requirements**: Meet security standards (SOC 2, HIPAA, PCI-DSS, etc.)
- **Post-Incident Analysis**: Review security after a breach or vulnerability
- **New Feature Security**: Assess security implications of new functionality
- **Third-Party Integration**: Evaluate security of external dependencies
- **Security-Critical Projects**: Applications handling sensitive data

## Prerequisites

Before starting a security audit, ensure you have:

- **Access to Codebase**: Full repository access including dependencies
- **Understanding of Architecture**: System design and data flow knowledge
- **Security Tools**: Install relevant security scanning tools
- **Test Environment**: Safe environment for security testing
- **Documentation**: API docs, architecture diagrams, threat models
- **Credentials**: Test accounts with various permission levels

## Security Auditing Workflow

### Step 1: Planning and Scoping

**Define Audit Scope**:
```markdown
**Audit Scope**:
- Application components: [web app, API, mobile app, microservices]
- Security domains: [authentication, authorization, data protection, API security]
- Testing methods: [static analysis, dynamic analysis, dependency scanning, code review]
- Out of scope: [third-party services, infrastructure managed by cloud provider]

**Risk Assessment**:
- High-risk areas: [user authentication, payment processing, personal data storage]
- Medium-risk areas: [public APIs, file uploads, search functionality]
- Low-risk areas: [static content, read-only dashboards]

**Testing Timeline**:
- Phase 1: Automated scans (Day 1-2)
- Phase 2: Manual code review (Day 3-5)
- Phase 3: Penetration testing (Day 6-7)
- Phase 4: Reporting and remediation (Day 8)
```

**Gather Security Context**:
- Review threat models and previous security assessments
- Identify sensitive data flows (PII, credentials, financial data)
- Document authentication and authorization mechanisms
- Map attack surface (endpoints, inputs, integrations)

### Step 2: Dependency Vulnerability Scanning

**Scan Dependencies for Known Vulnerabilities**:

**JavaScript/Node.js**:
```bash
# NPM audit
npm audit
npm audit fix

# Yarn audit
yarn audit

# Snyk
npm install -g snyk
snyk test
snyk monitor
```

**Python**:
```bash
# Safety
pip install safety
safety check --json

# Bandit (for code scanning)
pip install bandit
bandit -r . -f json -o bandit-report.json

# pip-audit
pip install pip-audit
pip-audit
```

**Ruby**:
```bash
# Bundler audit
gem install bundler-audit
bundle-audit check --update
```

**Java**:
```bash
# OWASP Dependency-Check
mvn org.owasp:dependency-check-maven:check
```

**Analyze Results**:
- **Critical vulnerabilities**: Immediate attention required
- **High severity**: Plan remediation within 1 week
- **Medium/Low severity**: Track and address in next sprint
- **False positives**: Document and suppress with justification

### Step 3: Static Application Security Testing (SAST)

**Run Static Code Analysis**:

**Multi-Language Tools**:
```bash
# SonarQube
docker run -d --name sonarqube -p 9000:9000 sonarqube
# Configure project and run analysis

# Semgrep (open-source)
pip install semgrep
semgrep --config=auto .
```

**Language-Specific Tools**:

**JavaScript/TypeScript**:
```bash
# ESLint with security plugin
npm install eslint eslint-plugin-security
npx eslint . --ext .js,.ts

# NodeJSScan
pip install nodejsscan
nodejsscan -d .
```

**Python**:
```bash
# Bandit
bandit -r . -f html -o security-report.html

# Pylint with security checks
pip install pylint
pylint --load-plugins=pylint.extensions.security .
```

**Review Common Vulnerability Patterns**:
- **SQL Injection**: Unsanitized database queries
- **XSS (Cross-Site Scripting)**: Unescaped user input in HTML
- **Command Injection**: Unsanitized shell command execution
- **Path Traversal**: User-controlled file paths
- **Insecure Deserialization**: Unsafe object deserialization
- **Hardcoded Secrets**: API keys, passwords, tokens in code

### Step 4: Manual Code Review for Security

**Focus Areas for Manual Review**:

**1. Authentication and Session Management**:
```python
# Check for:
# - Weak password policies
# - Insecure session storage
# - Missing session expiration
# - Improper logout handling

# Good Example:
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

def register_user(username, password):
    # Enforce strong password requirements
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters")

    # Use secure hashing
    hashed = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    # Generate secure session token
    session_token = secrets.token_urlsafe(32)

    # Store with expiration
    store_user(username, hashed, session_token, expires_in=3600)
```

**2. Authorization and Access Control**:
```javascript
// Check for:
// - Missing authorization checks
// - Insecure Direct Object References (IDOR)
// - Privilege escalation vulnerabilities
// - Broken access control

// Good Example:
async function updateUserProfile(userId, requestingUserId, updates) {
    // Always verify requesting user has permission
    if (userId !== requestingUserId && !isAdmin(requestingUserId)) {
        throw new UnauthorizedError("Cannot update another user's profile");
    }

    // Validate user owns the resource
    const user = await User.findById(userId);
    if (!user) {
        throw new NotFoundError("User not found");
    }

    // Apply updates with whitelist
    const allowedFields = ['name', 'email', 'bio'];
    const sanitizedUpdates = pick(updates, allowedFields);

    return await user.update(sanitizedUpdates);
}
```

**3. Input Validation and Output Encoding**:
```python
# Check for:
# - Unvalidated user input
# - Missing output encoding
# - Type confusion vulnerabilities
# - Regex DoS (ReDoS)

# Good Example:
import re
from html import escape
from typing import Optional

def sanitize_search_query(query: str, max_length: int = 100) -> Optional[str]:
    """Sanitize user search input"""
    if not query or not isinstance(query, str):
        return None

    # Limit length to prevent ReDoS
    query = query[:max_length]

    # Remove dangerous characters
    query = re.sub(r'[<>"\';\\]', '', query)

    # Escape for HTML output
    return escape(query.strip())

# In template rendering:
# {{ search_query|safe }} should only be used after sanitization
```

**4. Cryptography and Data Protection**:
```python
# Check for:
# - Weak encryption algorithms (DES, MD5, SHA1)
# - Hardcoded encryption keys
# - Improper key management
# - Sensitive data in logs

# Good Example:
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import os

def encrypt_sensitive_data(data: str, user_key: str) -> bytes:
    """Encrypt sensitive data using user-specific key"""
    # Derive key from user-specific secret
    salt = os.environ['ENCRYPTION_SALT'].encode()
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000
    )
    key = base64.urlsafe_b64encode(kdf.derive(user_key.encode()))

    # Encrypt using Fernet (AES-128-CBC)
    f = Fernet(key)
    return f.encrypt(data.encode())

# Never log decrypted sensitive data
logger.info(f"Encrypted data: [REDACTED]")
```

**5. API Security**:
```javascript
// Check for:
// - Missing rate limiting
// - Weak API authentication
// - Insufficient input validation
// - Mass assignment vulnerabilities
// - Missing CORS configuration

// Good Example:
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');

// Apply security middleware
app.use(helmet());
app.use(express.json({ limit: '10kb' })); // Limit payload size

// Rate limiting
const apiLimiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // Limit each IP to 100 requests per window
    message: 'Too many requests, please try again later'
});
app.use('/api/', apiLimiter);

// Validate API keys
app.use('/api/', (req, res, next) => {
    const apiKey = req.header('X-API-Key');
    if (!apiKey || !isValidApiKey(apiKey)) {
        return res.status(401).json({ error: 'Invalid API key' });
    }
    next();
});

// CORS configuration
const cors = require('cors');
app.use(cors({
    origin: process.env.ALLOWED_ORIGINS.split(','),
    credentials: true,
    optionsSuccessStatus: 200
}));
```

### Step 5: Dynamic Application Security Testing (DAST)

**Perform Runtime Security Testing**:

**Set Up Test Environment**:
```bash
# Ensure testing in isolated environment
# Never run security tests against production!

# Start application in test mode
export NODE_ENV=test
export DB_HOST=test-db.local
npm start
```

**Common DAST Tools**:
```bash
# OWASP ZAP (Zed Attack Proxy)
docker run -t owasp/zap2docker-stable zap-baseline.py \
    -t http://localhost:3000 \
    -r zap-report.html

# Burp Suite Community Edition
# Manual testing through proxy

# Nikto (web server scanner)
nikto -h http://localhost:3000 -output nikto-report.html
```

**Manual Penetration Testing**:
- **Authentication bypass**: Test login mechanisms
- **Session fixation**: Attempt to hijack sessions
- **CSRF attacks**: Test cross-site request forgery protection
- **Injection attacks**: SQL, NoSQL, command, LDAP injection
- **File upload vulnerabilities**: Malicious file uploads
- **Business logic flaws**: Workflow manipulation

### Step 6: Configuration and Infrastructure Review

**Check Security Configurations**:

**Web Server Security**:
```nginx
# Nginx security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

# Disable server version disclosure
server_tokens off;

# Limit request size
client_max_body_size 10M;
```

**Environment Variables and Secrets**:
```bash
# Check for exposed secrets
# Never commit .env files!

# Use secret management tools
# - AWS Secrets Manager
# - HashiCorp Vault
# - Azure Key Vault
# - Google Cloud Secret Manager

# Verify .gitignore
cat .gitignore | grep -E "(\.env|\.pem|\.key|credentials)"
```

**Database Security**:
- **Least privilege**: Database users have minimal required permissions
- **Connection security**: Use SSL/TLS for database connections
- **Backup encryption**: Encrypted backups stored securely
- **Query parameterization**: No string concatenation in queries

**Cloud Infrastructure**:
- **Security groups**: Minimal open ports
- **IAM policies**: Principle of least privilege
- **Logging enabled**: CloudTrail, VPC Flow Logs
- **Encryption at rest**: For all sensitive data stores
- **Network segmentation**: Proper VPC/subnet configuration

### Step 7: Reporting and Remediation

**Security Audit Report Structure**:

```markdown
# Security Audit Report

**Project**: 
**Audit Date**: {{DATE}}
**Auditor**: [Name/Team]
**Scope**: [Components audited]

## Executive Summary
- **Total Issues Found**: 47
- **Critical**: 2
- **High**: 8
- **Medium**: 15
- **Low**: 22
- **Overall Risk Level**: MODERATE

## Critical Findings

### CRIT-001: SQL Injection in User Search
**Severity**: Critical
**CVSS Score**: 9.8
**Component**: `src/api/search.js:45`
**Description**: User input directly concatenated into SQL query without sanitization
**Proof of Concept**:
```sql
' OR '1'='1' --
```
**Impact**: Complete database compromise, data exfiltration
**Remediation**: Use parameterized queries or ORM
**Status**: OPEN
**Priority**: P0 - Fix immediately

### CRIT-002: Hardcoded AWS Credentials
**Severity**: Critical
**CVSS Score**: 10.0
**Component**: `src/config/aws.js:12`
**Description**: AWS access keys hardcoded in source code
**Impact**: Unauthorized access to AWS resources, data breach
**Remediation**:
1. Revoke exposed credentials immediately
2. Use AWS IAM roles or environment variables
3. Implement secret scanning in CI/CD
**Status**: OPEN
**Priority**: P0 - Fix immediately

## High Severity Findings
[List 8 high-severity issues with similar detail]

## Medium/Low Severity Findings
[Summarized list with references]

## Dependency Vulnerabilities
- **Critical**: 1 (lodash < 4.17.21)
- **High**: 5
- **Medium**: 12

## Compliance Status
- **OWASP Top 10 2021**: 7/10 categories addressed
- **CWE Top 25**: 18/25 weaknesses not present
- **Security Headers**: 4/6 recommended headers present

## Recommendations

### Immediate Actions (Week 1)
1. Fix critical SQL injection vulnerability
2. Revoke and rotate hardcoded credentials
3. Update critical dependencies (lodash, axios)

### Short-term Improvements (Month 1)
1. Implement input validation framework
2. Add rate limiting to all API endpoints
3. Enable security logging and monitoring
4. Configure CSP headers

### Long-term Initiatives (Quarter 1)
1. Implement automated security scanning in CI/CD
2. Conduct security training for development team
3. Establish secure SDLC practices
4. Set up bug bounty program

## Appendix
- Detailed scan results (attached)
- Tool versions and configurations
- Testing methodology
```

**Prioritize Remediation**:

**Critical (P0)**: Fix within 24 hours
- Remote code execution
- Authentication bypass
- Data exposure
- Hardcoded credentials

**High (P1)**: Fix within 1 week
- SQL/NoSQL injection
- Privilege escalation
- Sensitive data in logs
- Weak cryptography

**Medium (P2)**: Fix within 1 month
- Missing rate limiting
- Insecure defaults
- Information disclosure
- Session fixation

**Low (P3)**: Fix within quarter
- Missing security headers
- Verbose error messages
- Version disclosure
- Minor config issues

## Common Security Vulnerabilities (OWASP Top 10 2021)

1. **Broken Access Control**: Authorization failures allowing unauthorized actions
2. **Cryptographic Failures**: Weak encryption or exposed sensitive data
3. **Injection**: SQL, NoSQL, OS command, LDAP injection attacks
4. **Insecure Design**: Missing or ineffective security controls
5. **Security Misconfiguration**: Improper security settings
6. **Vulnerable and Outdated Components**: Using libraries with known CVEs
7. **Identification and Authentication Failures**: Weak authentication mechanisms
8. **Software and Data Integrity Failures**: Unverified code/data
9. **Security Logging and Monitoring Failures**: Insufficient logging
10. **Server-Side Request Forgery (SSRF)**: Unauthorized server-side requests

## Security Tools Reference

### Free/Open-Source Tools
- **OWASP ZAP**: Web application security scanner
- **Bandit**: Python security linter
- **Semgrep**: Static analysis for multiple languages
- **npm audit**: Node.js dependency scanner
- **Safety**: Python dependency checker
- **git-secrets**: Prevent committing secrets
- **TruffleHog**: Scan git repos for secrets

### Commercial Tools
- **Snyk**: Dependency and container scanning
- **Checkmarx**: Enterprise SAST/DAST
- **Veracode**: Application security platform
- **Burp Suite Pro**: Advanced web security testing
- **Acunetix**: Automated web vulnerability scanner

### Cloud-Specific Tools
- **AWS GuardDuty**: Threat detection
- **AWS Security Hub**: Security posture management
- **Azure Defender**: Cloud workload protection
- **Google Security Command Center**: Cloud security and risk management

## Best Practices

1. **Shift Left Security**: Integrate security testing early in development
2. **Defense in Depth**: Multiple layers of security controls
3. **Principle of Least Privilege**: Minimal necessary permissions
4. **Secure by Default**: Safe default configurations
5. **Input Validation**: Validate all user input
6. **Output Encoding**: Encode all output to prevent XSS
7. **Parameterized Queries**: Never concatenate SQL queries
8. **Keep Dependencies Updated**: Regular dependency updates
9. **Security Logging**: Comprehensive audit trails
10. **Incident Response Plan**: Prepared for security incidents

## Integration with Other Skills

- **Testing Workflow**: Include security tests in test suite
- **Code Review**: Security-focused code review checklist
- **Documentation**: Document security architecture and controls
- **Performance**: Balance security controls with performance
- **Dependency Management**: Automate vulnerability scanning

## Success Metrics

- **Vulnerability Remediation Rate**: % of issues fixed within SLA
- **Time to Remediation**: Average time from discovery to fix
- **Dependency Health**: % of dependencies without known CVEs
- **Security Test Coverage**: % of code covered by security tests
- **False Positive Rate**: Accuracy of security scanning tools
- **Mean Time to Detection (MTTD)**: Time to detect security issues
- **Mean Time to Response (MTTR)**: Time to respond to incidents

---

**Skill Version**: 1.0.0
**Last Updated**: {{DATE}}
**Maintained By**: Proto Gear Community
