#!/usr/bin/env python3
"""
Test script for admin functionality
"""

import requests
import json

BASE_URL = "http://localhost:5001"

def test_admin_login():
    """Test admin login"""
    print("Testing admin login...")
    
    # Login as admin
    login_data = {
        "username": "admin",
        "password": "admin"
    }
    
    session = requests.Session()
    response = session.post(f"{BASE_URL}/api/auth/login", json=login_data)
    
    if response.status_code == 200:
        print("✓ Admin login successful")
        print(f"  Response: {response.json()}")
        return session
    else:
        print(f"✗ Admin login failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return None

def test_admin_endpoints(session):
    """Test various admin endpoints"""
    if not session:
        print("Skipping admin endpoint tests - no session")
        return
    
    print("\nTesting admin endpoints...")
    
    # Test system overview
    print("\n1. Testing system overview...")
    response = session.get(f"{BASE_URL}/api/admin/stats/overview")
    if response.status_code == 200:
        print("✓ System overview endpoint working")
        data = response.json()
        print(f"  Total users: {data['users']['total']}")
        print(f"  Total goals: {data['goals']['total']}")
    else:
        print(f"✗ System overview failed: {response.status_code}")
    
    # Test user list
    print("\n2. Testing user list...")
    response = session.get(f"{BASE_URL}/api/admin/users")
    if response.status_code == 200:
        print("✓ User list endpoint working")
        data = response.json()
        print(f"  Total users: {data['pagination']['total']}")
    else:
        print(f"✗ User list failed: {response.status_code}")
    
    # Test admin settings
    print("\n3. Testing admin settings...")
    response = session.get(f"{BASE_URL}/api/admin/settings")
    if response.status_code == 200:
        print("✓ Admin settings endpoint working")
        data = response.json()
        print(f"  Total settings: {len(data['settings'])}")
    else:
        print(f"✗ Admin settings failed: {response.status_code}")
    
    # Test backup list
    print("\n4. Testing backup list...")
    response = session.get(f"{BASE_URL}/api/admin/backup/list")
    if response.status_code == 200:
        print("✓ Backup list endpoint working")
        data = response.json()
        print(f"  Total backups: {data['pagination']['total']}")
    else:
        print(f"✗ Backup list failed: {response.status_code}")

def test_non_admin_access():
    """Test that non-admin users can't access admin endpoints"""
    print("\nTesting non-admin access restrictions...")
    
    # First create a regular user
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    session = requests.Session()
    
    # Try to register (might already exist)
    session.post(f"{BASE_URL}/api/auth/register", json=register_data)
    
    # Login as regular user
    login_data = {
        "username": "testuser",
        "password": "testpass123"
    }
    
    response = session.post(f"{BASE_URL}/api/auth/login", json=login_data)
    
    if response.status_code == 200:
        print("✓ Regular user login successful")
        
        # Try to access admin endpoint
        response = session.get(f"{BASE_URL}/api/admin/users")
        if response.status_code == 403:
            print("✓ Admin endpoints properly restricted (403 Forbidden)")
        else:
            print(f"✗ Security issue: Regular user could access admin endpoint! Status: {response.status_code}")
    else:
        print("✗ Could not login as regular user")

def main():
    print("LetsGoal Admin System Test")
    print("=" * 50)
    
    # Test admin login
    admin_session = test_admin_login()
    
    # Test admin endpoints
    test_admin_endpoints(admin_session)
    
    # Test access restrictions
    test_non_admin_access()
    
    print("\n" + "=" * 50)
    print("Admin system test complete!")

if __name__ == "__main__":
    main()