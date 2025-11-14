# SilentLock - Security and Privacy

## 🔒 Security Architecture

### Encryption Details
- **Algorithm**: AES-256-GCM (Galois/Counter Mode)
- **Key Derivation**: PBKDF2-SHA256 with 100,000 iterations
- **Salt**: Random 16-byte salt per credential
- **IV**: Random 12-byte initialization vector per encryption
- **Authentication**: Built-in authentication tag prevents tampering

### Master Password Protection
```
User Password → PBKDF2-SHA256(100k iterations) → 256-bit Key → Encrypt/Decrypt Data
```

### Data Storage
- **Location**: `%APPDATA%\SilentLock\credentials.db`
- **Format**: SQLite database with encrypted password fields
- **Metadata**: Only site names, URLs, usernames stored in plain text
- **Isolation**: Each password encrypted independently

## 🛡️ Privacy Guarantees

### Local-Only Storage
- **No Cloud Sync**: All data remains on your device
- **No Network Calls**: No internet communication required
- **No Telemetry**: No usage data collection
- **No Third-Party Services**: Completely self-contained

### Monitoring Behavior
- **Scope**: Only monitors the device where SilentLock is installed
- **Permission**: Requires explicit user consent for each save
- **Transparency**: Activity log shows all detection events
- **Control**: Can be disabled at any time

### Data Minimization
- **Passwords**: Encrypted immediately upon entry
- **Metadata**: Only essential fields stored
- **Logs**: Minimal activity logging, stored locally
- **Memory**: Secure deletion attempted for sensitive data

## ⚖️ Ethical Use Policy

### Acceptable Use
✅ **Personal password management on your own devices**
✅ **Storing your own credentials with your consent**
✅ **Managing family passwords with explicit permission**
✅ **Educational purposes in controlled environments**

### Prohibited Use
❌ **Installing on devices without permission**
❌ **Capturing credentials without user consent**
❌ **Bypassing authentication systems**
❌ **Accessing accounts that don't belong to you**
❌ **Commercial use without proper licensing**

## 🔍 Code Transparency

### Open Design
- **Source Available**: All code is available for review
- **No Obfuscation**: Clear, readable implementation
- **Standard Libraries**: Uses well-vetted cryptographic libraries
- **Best Practices**: Follows security coding standards

### Security Features
- **Input Validation**: All inputs properly validated
- **SQL Injection Prevention**: Parameterized queries only
- **Memory Safety**: Attempts to clear sensitive data
- **Error Handling**: Graceful failure without data leaks

## 🚨 Threat Model

### What SilentLock Protects Against
- **Data Breaches**: Encrypted storage prevents credential theft
- **Weak Passwords**: Encourages use of strong, unique passwords
- **Password Reuse**: Makes it easy to use different passwords
- **Forgotten Credentials**: Secure storage and retrieval

### What SilentLock Cannot Protect Against
- **Malware on Your System**: If your computer is compromised, all bets are off
- **Shoulder Surfing**: Physical observation of password entry
- **Master Password Compromise**: If master password is stolen, all data is at risk
- **Government Surveillance**: Not designed to resist state-level attacks

## 🔐 Key Security Recommendations

### For Users
1. **Strong Master Password**: Use a unique, complex password you won't forget
2. **Regular Backups**: Keep encrypted database file backed up
3. **System Security**: Keep your operating system and antivirus updated
4. **Physical Security**: Lock your computer when not in use
5. **Regular Review**: Periodically review stored credentials

### For Administrators
1. **Network Isolation**: No network access required for operation
2. **Privilege Management**: Run with minimal required privileges
3. **Monitoring**: Watch for unusual file access patterns
4. **Backup Strategy**: Include encrypted database in backup plans

## 📋 Compliance Considerations

### Personal Use
- **GDPR**: Personal use exemption applies
- **Data Minimization**: Only stores necessary credential data
- **Consent**: Explicit opt-in for all credential storage

### Enterprise Use
- **Policy Compliance**: Check organizational password policies
- **Data Classification**: Treat as sensitive business data
- **Audit Trails**: Activity logs support compliance requirements

## 🛠️ Security Configuration

### High-Security Setup
1. **Enable Monitoring Only When Needed**: Reduce attack surface
2. **Regular Password Changes**: Update master password periodically
3. **Secure File Permissions**: Restrict database file access
4. **Backup Encryption**: Encrypt backup copies separately

### Debugging Security Issues
```powershell
# Test encryption
python test_basic.py

# Check file permissions
icacls "%APPDATA%\SilentLock"

# Verify dependencies
pip list | findstr crypto
```

## 📞 Security Contact

For security vulnerabilities or concerns:
1. **Do Not** publicly disclose security issues
2. **Contact** the development team privately
3. **Provide** detailed technical information
4. **Allow** reasonable time for patches

---

**Remember**: Security is a shared responsibility. Use SilentLock ethically and responsibly.