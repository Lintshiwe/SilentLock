#!/usr/bin/env python3
"""
Test script for SilentLock Password Manager
Verifies core functionality without GUI.
"""

import sys
import os
import tempfile

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.security import SecurityManager
from src.database import DatabaseManager


def test_encryption():
    """Test encryption/decryption functionality."""
    print("Testing encryption...")
    
    security = SecurityManager()
    password = "test_master_password"
    data = "secret_password_123"
    
    # Encrypt
    encrypted = security.encrypt_data(data, password)
    print(f"Encrypted data keys: {list(encrypted.keys())}")
    
    # Decrypt
    decrypted = security.decrypt_data(encrypted, password)
    
    assert decrypted == data, f"Decryption failed: {decrypted} != {data}"
    print("✓ Encryption test passed!")


def test_database():
    """Test database functionality."""
    print("\nTesting database...")
    
    # Use temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        db = DatabaseManager(db_path)
        master_password = "test_master_password_123"
        
        # Set master password
        assert db.set_master_password(master_password), "Failed to set master password"
        print("✓ Master password set")
        
        # Verify master password
        assert db.verify_master_password(master_password), "Failed to verify master password"
        print("✓ Master password verified")
        
        # Store credential
        assert db.store_credential(
            "Test Site",
            "https://test.com",
            "testuser",
            "testpass123",
            master_password,
            "Test notes"
        ), "Failed to store credential"
        print("✓ Credential stored")
        
        # Retrieve credential
        cred = db.get_credential("https://test.com", "testuser", master_password)
        assert cred is not None, "Failed to retrieve credential"
        assert cred['password'] == "testpass123", f"Password mismatch: {cred['password']}"
        print("✓ Credential retrieved")
        
        # Search credentials
        results = db.search_credentials("Test", master_password)
        assert len(results) == 1, f"Search failed: {len(results)} results"
        print("✓ Search functionality works")
        
    finally:
        # Clean up
        try:
            os.unlink(db_path)
        except:
            pass
    
    print("✓ Database tests passed!")


def test_imports():
    """Test all module imports."""
    print("\nTesting imports...")
    
    try:
        import src.security
        print("✓ Security module imported")
        
        import src.database
        print("✓ Database module imported")
        
        import src.form_detector
        print("✓ Form detector module imported")
        
        # Note: GUI module might fail on headless systems
        try:
            import src.gui
            print("✓ GUI module imported")
        except Exception as e:
            print(f"⚠ GUI module import failed (expected on headless systems): {e}")
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        raise


def main():
    """Run all tests."""
    print("SilentLock Password Manager - Test Suite")
    print("=" * 50)
    
    try:
        test_imports()
        test_encryption()
        test_database()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! SilentLock is ready to use.")
        print("\nTo start the application:")
        print("  python main.py")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()