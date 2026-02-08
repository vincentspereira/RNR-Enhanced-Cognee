# Enhanced Cognee - Security Hardening Checklist

## Pre-Deployment Security Checklist

### 1. Authentication & Authorization
- [ ] **Strong Password Policy**
  - [ ] All passwords are 32+ characters with mixed case, numbers, symbols
  - [ ] Passwords are stored in secure vault (not in code)
  - [ ] Passwords are rotated regularly (90 days recommended)
  - [ ] Default passwords are changed

- [ ] **API Key Management**
  - [ ] API keys are cryptographically random (64+ characters)
  - [ ] API keys are stored in environment variables only
  - [ ] API key rotation mechanism is in place
  - [ ] API keys are scoped to minimal necessary permissions

- [ ] **Multi-Factor Authentication (MFA)**
  - [ ] MFA is enabled for all admin accounts
  - [ ] MFA is enforced for database access
  - [ ] Backup codes are stored securely

### 2. Network Security
- [ ] **Firewall Configuration**
  - [ ] Only necessary ports are exposed (80, 443, maybe 8000)
  - [ ] Database ports NOT exposed publicly
  - [ ] Internal services on private network
  - [ ] VPN required for admin access

- [ ] **TLS/SSL Configuration**
  - [ ] HTTPS is enforced in production
  - [ ] SSL certificates are valid and from trusted CA
  - [ ] Certificate expiration monitoring is set up
  - [ ] Weak ciphers and protocols are disabled
  - [ ] HSTS headers are enabled
  - [ ] Certificate auto-renewal is configured

- [ ] **Network Isolation**
  - [ ] Services are on isolated Docker network
  - [ ] Inter-service communication is internal only
  - [ ] Database access is restricted to application layer

### 3. Application Security
- [ ] **Input Validation**
  - [ ] All user inputs are validated and sanitized
  - [ ] SQL injection prevention (parameterized queries)
  - [ ] XSS prevention (output encoding)
  - [ ] CSRF tokens are implemented
  - [ ] File upload restrictions are in place

- [ ] **Session Management**
  - [ ] Sessions timeout after inactivity (30 min recommended)
  - [ ] Secure session cookies (HttpOnly, Secure, SameSite)
  - [ ] Session regeneration after login
  - [ ] Concurrent session limits

- [ ] **Rate Limiting**
  - [ ] Rate limiting is enabled (100 req/min recommended)
  - [ ] Burst limits are configured
  - [ ] IP-based blocking for abuse
  - [ ] API key-based rate limits

- [ ] **CORS Configuration**
  - [ ] Only trusted domains in CORS allowlist
  - [ ] Credentials are not allowed in CORS
  - [ ] Preflight requests are properly handled

### 4. Database Security
- [ ] **PostgreSQL**
  - [ ] Only localhost/internal network access
  - [ ] Strong superuser password
  - [ ] Limited user permissions (principle of least privilege)
  - [ ] Encrypted connections (SSL/TLS)
  - [ ] Row-level security (RLS) enabled
  - [ ] Audit logging is enabled
  - [ ] Regular database backups are automated

- [ ] **Qdrant**
  - [ ] API key is configured
  - [ ] Only internal network access
  - [ ] Collections have proper access controls
  - [ ] Search result limits are enforced

- [ ] **Neo4j**
  - [ ] Strong authentication
  - [ ] Only bolt protocol (not HTTP)
  - [ ] User privileges are minimized
  - [ ] Procedure allowlist is configured

- [ ] **Redis**
  - [ ] Strong password is set
  - [ ] Commands are restricted (CONFIG, FLUSHDB disabled)
  - [ ] Only internal network access
  - [ ] Data persistence is enabled

### 5. Container Security
- [ ] **Docker Hardening**
  - [ ] Containers run as non-root user
  - [ ] Read-only filesystems where possible
  - [ ] Resource limits are enforced (CPU, memory)
  - [ ] Health checks are configured
  - [ ] Restart policies are configured
  - [ ] Secrets are NOT in images (use environment variables or Docker secrets)
  - [ ] Base images are updated regularly
  - [ ] Vulnerability scanning is integrated

### 6. Logging & Monitoring
- [ ] **Security Logging**
  - [ ] All authentication attempts are logged
  - [ ] Authorization failures are logged
  - [ ] Suspicious activities are logged
  - [ ] Log data includes: timestamp, user, action, result, IP
  - [ ] Logs are shipped to secure centralized storage
  - [ ] Log retention policy is configured (90+ days)
  - [ ] Log access is restricted and audited

- [ ] **Intrusion Detection**
  - [ ] Failed login attempts trigger alerts (> 5 failures)
  - [ ] Unusual access patterns trigger alerts
  - [ ] API abuse triggers alerts
  - [ ] Database anomaly detection is enabled

- [ ] **Performance Monitoring**
  - [ ] CPU, memory, disk usage monitoring
  - [ ] Response time monitoring
  - [ ] Error rate monitoring
  - [ ] Alert thresholds are configured

### 7. Data Protection
- [ ] **Encryption at Rest**
  - [ ] Database backups are encrypted
  - [ ] Filesystem encryption is enabled (LUKS, EFS)
  - [ ] Secrets are encrypted in storage

- [ ] **Encryption in Transit**
  - [ ] All external traffic uses TLS 1.3+
  - [ ] Internal traffic uses TLS where possible
  - [ ] Certificate pinning is implemented

- [ ] **Data Retention**
  - [ ] Automatic data archival is configured
  - [ ] Old data is purged according to policy
  - [ ] Personal data is anonymized after retention period

- [ ] **Backup Security**
  - [ ] Backups are encrypted
  - [ ] Backup access is restricted
  - [ ] Backups are stored in multiple locations
  - [ ] Backup restoration is tested regularly
  - [ ] Backup integrity is verified

### 8. Dependencies & Vulnerabilities
- [ ] **Dependency Management**
  - [ ] Dependencies are scanned for vulnerabilities
  - [ ] High/critical vulnerabilities are patched
  - [ ] Automatic dependency updates are tested
  - [ ] SBOM (Software Bill of Materials) is maintained

- [ ] **Third-Party Services**
  - [ ] LLM providers have secure API key handling
  - [ ] Third-party APIs are accessed over HTTPS
  - [ ] Third-party data processing agreements are in place
  - [ ] Third-party access is logged

### 9. Operational Security
- [ ] **Access Control**
  - [ ] Principle of least privilege is enforced
  - [ ] Admin access is limited and audited
  - [ ] Access reviews are conducted quarterly
  - [ ] Access is revoked immediately upon termination

- [ ] **Change Management**
  - [ ] All changes go through code review
  - [ ] Changes are tested in staging first
  - [ ] Rollback plan is documented
  - [ ] Deployment is automated
  - [ ] Blue-green deployment is used

- [ ] **Incident Response**
  - [ ] Incident response plan is documented
  - [ ] Team is trained on incident response
  - [ ] Emergency contacts are documented
  - [ ] Response time targets are defined (1 hour acknowledgment)
  - [ ] Post-incident reviews are conducted

### 10. Compliance & Legal
- [ ] **GDPR Compliance** (if applicable)
  - [ ] Data processing agreement is in place
  - [ ] Data subject rights are supported
  - [ ] Data breach notification procedure is documented
  - [ ] DPO (Data Protection Officer) is assigned

- [ ] **OWASP Top 10**
  - [ ] A01: Broken Access Control - ✅ Verified
  - [ ] A02: Cryptographic Failures - ✅ Verified
  - [ ] A03: Injection - ✅ Verified
  - [ ] A04: Insecure Design - ✅ Verified
  - [ ] A05: Security Misconfiguration - ✅ Verified
  - [ ] A06: Vulnerable Components - ✅ Verified
  - [ ] A07: Auth Failures - ✅ Verified
  - [ ] A08: Data Integrity Failures - ✅ Verified
  - [ ] A09: Logging Failures - ✅ Verified
  - [ ] A10: Server-Side Request Forgery - ✅ Verified

## Security Testing Commands

### Scan Docker Images for Vulnerabilities
```bash
# Trivy scan
trivy image enhanced-cognee-server:latest

# Docker Scout
docker scout quickview enhanced-cognee-server:latest
docker scout cves enhanced-cognee-server:latest
```

### Check for Exposed Ports
```bash
# Only web server should be exposed
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

### Verify SSL/TLS Configuration
```bash
# Test SSL configuration
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

### Test Security Headers
```bash
# Check security headers
curl -I https://your-domain.com
```

### Review Environment Variables
```bash
# Ensure no secrets in Docker image
docker history enhanced-cognee-server:latest
```

## Pre-Deployment Security Script

Create `scripts/security_check.sh`:

```bash
#!/bin/bash
echo "=== Enhanced Cognee Security Check ==="

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "❌ ERROR: .env.production not found"
    exit 1
fi

# Check for default passwords
if grep -q "CHANGE_THIS" .env.production; then
    echo "❌ ERROR: Default passwords detected in .env.production"
    exit 1
fi

# Check if .env.production is in .gitignore
if ! grep -q ".env.production" .gitignore; then
    echo "❌ WARNING: .env.production not in .gitignore"
fi

# Check Docker network isolation
if ! docker network inspect cognee-network &>/dev/null; then
    echo "❌ ERROR: Docker network 'cognee-network' not found"
    exit 1
fi

echo "✅ Security checks passed"
echo "⚠️  Remember to:"
echo "  - Run vulnerability scans"
echo "  - Test backup restoration"
echo "  - Verify monitoring setup"
echo "  - Review firewall rules"
```

## Post-Deployment Monitoring

### Daily Checks
- [ ] Review security logs for anomalies
- [ ] Check failed login attempts
- [ ] Monitor API usage patterns
- [ ] Verify backup completion

### Weekly Checks
- [ ] Review and update vulnerability scan results
- [ ] Check for security patches
- [ ] Review access logs
- [ ] Test backup restoration

### Monthly Checks
- [ ] Conduct security audit
- [ ] Review and rotate secrets
- [ ] Update security documentation
- [ ] Security training for team

### Quarterly Checks
- [ ] Penetration testing
- [ ] Review access controls
- [ ] Update incident response plan
- [ ] Third-party security assessment

## Emergency Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| Security Lead | | | |
| DevOps Lead | | | |
| Database Admin | | | |
| Incident Response | | | |

## Security Resources

- OWASP: https://owasp.org
- CWE: https://cwe.mitre.org/
- Docker Security: https://docs.docker.com/engine/security/
- NIST Cybersecurity Framework: https://www.nist.gov/cyberframework
