# Security Policy

## Supported Versions

We actively support and provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | ✅ Currently supported |
| < 1.0   | ❌ No longer supported |

## Reporting a Vulnerability

**We take security seriously.** If you discover a security vulnerability in SilentLock, please help us protect our users by following responsible disclosure:

### 🔒 Private Reporting (Recommended)
For security vulnerabilities, please **do not** create a public issue. Instead:

1. **Email**: Send details to our security team at [security@silentlock.dev](mailto:security@silentlock.dev)
2. **Subject**: Use "SECURITY: Brief description of issue"
3. **Details**: Include steps to reproduce, impact assessment, and suggested fixes
4. **Encryption**: PGP-encrypt sensitive information when possible

### ⏰ Response Timeline
- **Acknowledgment**: Within 24 hours
- **Initial Assessment**: Within 48 hours  
- **Regular Updates**: Every 72 hours until resolved
- **Resolution Target**: 7-14 days depending on complexity

### 🛡️ Security Scope

#### In Scope ✅
- **Encryption vulnerabilities** (AES implementation, key derivation)
- **Authentication bypass** (master password verification)
- **Data exposure** (unencrypted storage, memory dumps)
- **Injection attacks** (SQL injection, command injection)
- **Privilege escalation** (local system access)
- **Browser integration vulnerabilities** (form detection bypass)
- **Memory safety issues** (buffer overflows, memory leaks)

#### Out of Scope ❌
- **Physical access attacks** (device theft, shoulder surfing)
- **Operating system vulnerabilities** (Windows exploits not specific to SilentLock)
- **Network-based attacks** (SilentLock doesn't use network)
- **Social engineering** (tricking users into revealing master password)
- **Brute force attacks** on properly secured master passwords

### 🏆 Recognition

We believe in recognizing security researchers who help keep our users safe:

- **Hall of Fame**: Public recognition (with permission)
- **CVE Assignment**: For significant vulnerabilities
- **Detailed Credit**: In security advisories and release notes
- **Early Access**: To beta versions for continued testing

### 📋 Disclosure Process

1. **Report received** - We acknowledge receipt and assign a team
2. **Validation** - We reproduce and validate the vulnerability  
3. **Assessment** - We determine severity and impact scope
4. **Development** - We develop and test a fix
5. **Testing** - We validate the fix resolves the issue
6. **Release** - We release the update to users
7. **Disclosure** - We publish a security advisory (coordinated timing)

### 🔍 Security Measures

SilentLock implements multiple layers of security:

#### Encryption & Storage
- **AES-256-GCM** encryption for all stored passwords
- **PBKDF2** key derivation with 100,000 iterations
- **Unique salts** for each encrypted entry
- **Local SQLite** database with encryption at rest
- **Secure memory handling** to prevent data leaks

#### Application Security  
- **Input validation** for all user data
- **SQL parameterization** to prevent injection
- **Process isolation** for credential handling
- **Self-monitoring protection** to prevent interference
- **Secure random generation** for cryptographic operations

#### Privacy Protection
- **No network communication** - completely offline
- **No telemetry or analytics** - zero data collection
- **Local storage only** - no cloud synchronization
- **Memory cleanup** - sensitive data cleared after use
- **Audit logging** - optional tracking of access patterns

### 📞 Contact Information

- **Security Email**: security@silentlock.dev
- **GitHub Security Advisories**: [Private vulnerability reporting](https://github.com/Lintshiwe/SilentLock/security/advisories)
- **General Issues**: [Public GitHub Issues](https://github.com/Lintshiwe/SilentLock/issues) (for non-security bugs)

### 🤝 Security Community

We encourage security research and welcome:
- **Responsible disclosure** of vulnerabilities
- **Code review** from security experts
- **Penetration testing** by qualified researchers  
- **Security suggestions** for improvement
- **Best practice recommendations**

---

**Thank you for helping keep SilentLock secure! 🔐**

*This security policy applies to all official SilentLock releases and source code.*