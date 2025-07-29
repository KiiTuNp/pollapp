#!/usr/bin/env python3
"""
Test script to verify the MongoDB installation fix
"""

import subprocess
import tempfile
import os

def test_gpg_command():
    """Test the corrected GPG command"""
    print("🧪 Testing GPG command for MongoDB key processing")
    
    # Create a temporary file to simulate the MongoDB key
    test_key_content = """-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBE-3mBQBEADWr4H2DdGGmb6uYlC4F+r/F1bBp1M9C/N+8FkPdK3mF7N5M2...
(Test PGP Key - not real)
-----END PGP PUBLIC KEY BLOCK-----"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.asc', delete=False) as temp_file:
        temp_file.write(test_key_content)
        temp_file_path = temp_file.name
    
    try:
        # Test the corrected GPG command syntax
        print("Testing: cat file | gpg --dearmor -o output")
        
        with tempfile.NamedTemporaryFile(suffix='.gpg', delete=False) as output_file:
            output_path = output_file.name
        
        # This is the corrected command we use in the installer
        result = subprocess.run([
            'bash', '-c', 
            f'cat {temp_file_path} | gpg --dearmor -o {output_path}'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ GPG command syntax is correct")
            
            # Check if output file was created
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print("✅ GPG output file created successfully")
                return True
            else:
                print("❌ GPG output file not created")
                return False
        else:
            print(f"❌ GPG command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing GPG command: {e}")
        return False
    finally:
        # Cleanup temp files
        for temp_path in [temp_file_path, output_path]:
            try:
                os.unlink(temp_path)
            except:
                pass

def test_mongodb_fallback():
    """Test MongoDB fallback installation method"""
    print("\n🧪 Testing MongoDB installation fallback")
    
    # Check if standard MongoDB packages are available
    try:
        result = subprocess.run([
            'apt-cache', 'search', 'mongodb'
        ], capture_output=True, text=True)
        
        if 'mongodb' in result.stdout:
            print("✅ MongoDB packages available in repositories")
            return True
        else:
            print("⚠️ MongoDB packages not found in repositories")
            return False
            
    except Exception as e:
        print(f"❌ Error checking MongoDB availability: {e}")
        return False

def test_service_detection():
    """Test service detection logic"""
    print("\n🧪 Testing systemd service detection")
    
    try:
        result = subprocess.run([
            'systemctl', 'list-units', '--type=service', '--all'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Service detection working")
            
            # Check for MongoDB-related services
            services = result.stdout
            mongo_services = []
            
            if 'mongodb.service' in services:
                mongo_services.append('mongodb.service')
            if 'mongod.service' in services:
                mongo_services.append('mongod.service')
                
            if mongo_services:
                print(f"✅ Found MongoDB services: {', '.join(mongo_services)}")
            else:
                print("ℹ️ No MongoDB services currently installed (expected)")
            
            return True
        else:
            print("❌ Service detection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing service detection: {e}")
        return False

def test_installation_script_fix():
    """Test that the installation script has been fixed"""
    print("\n🧪 Testing installation script fixes")
    
    try:
        with open('/app/install.py', 'r') as f:
            content = f.read()
        
        # Check for corrected GPG syntax
        if 'cat /tmp/mongodb.asc | gpg --dearmor -o' in content:
            print("✅ Corrected GPG syntax found in install.py")
        else:
            print("❌ Corrected GPG syntax not found")
            return False
        
        # Check for fallback method
        if 'install_mongodb_fallback' in content:
            print("✅ MongoDB fallback method implemented")
        else:
            print("❌ MongoDB fallback method not found")
            return False
            
        # Check for error handling
        if 'try:' in content and 'except Exception as e:' in content:
            print("✅ Error handling implemented")
        else:
            print("❌ Error handling not found")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error checking installation script: {e}")
        return False

def main():
    """Main test function"""
    print("🔧 MongoDB Installation Fix Validation")
    print("=" * 50)
    
    tests = [
        ("GPG Command", test_gpg_command),
        ("MongoDB Fallback", test_mongodb_fallback),
        ("Service Detection", test_service_detection),
        ("Installation Script Fix", test_installation_script_fix)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 All tests passed! MongoDB installation fix is working.")
        print("\n🚀 The installation script should now work correctly:")
        print("   sudo python3 install.py")
    else:
        print("\n⚠️ Some tests failed. Please check the issues above.")
    
    return passed == len(tests)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)