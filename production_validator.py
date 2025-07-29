#!/usr/bin/env python3
"""
Production Validator for Secret Poll
====================================

Comprehensive validation script to ensure everything is production-ready.
"""

import os
import sys
import subprocess
import json
import socket
import re
from pathlib import Path

class ProductionValidator:
    """Validates all aspects of the Secret Poll installation for production readiness"""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.successes = []
    
    def log_issue(self, message):
        """Log a critical issue"""
        self.issues.append(message)
        print(f"❌ ISSUE: {message}")
    
    def log_warning(self, message):
        """Log a warning"""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")
    
    def log_success(self, message):
        """Log a success"""
        self.successes.append(message)
        print(f"✅ SUCCESS: {message}")
    
    def validate_install_script(self):
        """Validate the installation script for robustness"""
        print("\n🔍 VALIDATING INSTALLATION SCRIPT")
        print("=" * 50)
        
        script_path = Path("/app/install.py")
        
        # Check if script exists
        if not script_path.exists():
            self.log_issue("install.py not found")
            return
        
        # Check syntax
        try:
            result = subprocess.run([sys.executable, "-m", "py_compile", str(script_path)], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.log_success("Python syntax is valid")
            else:
                self.log_issue(f"Python syntax error: {result.stderr}")
        except Exception as e:
            self.log_issue(f"Could not validate syntax: {e}")
        
        # Check critical components
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Check for robust error handling
        if "try:" in content and "except Exception as" in content:
            self.log_success("Error handling present")
        else:
            self.log_warning("Limited error handling detected")
        
        # Check for fallback mechanisms
        if "fallback" in content.lower():
            self.log_success("Fallback mechanisms implemented")
        else:
            self.log_warning("No fallback mechanisms detected")
        
        # Check for proper logging
        if 'self.log(' in content:
            self.log_success("Logging system implemented")
        else:
            self.log_issue("No logging system found")
        
        # Check Node.js installation robustness
        if "NodeSource failed" in content:
            self.log_success("Node.js fallback mechanism present")
        else:
            self.log_warning("Node.js installation may not be robust")
        
        # Check MongoDB robustness
        mongodb_methods = content.count("mongodb")
        if mongodb_methods >= 3:
            self.log_success("Multiple MongoDB installation methods")
        else:
            self.log_warning("Limited MongoDB installation options")
    
    def validate_backend_dependencies(self):
        """Validate backend dependencies and compatibility"""
        print("\n🐍 VALIDATING BACKEND DEPENDENCIES")
        print("=" * 50)
        
        requirements_path = Path("/app/backend/requirements.txt")
        
        if not requirements_path.exists():
            self.log_issue("backend/requirements.txt not found")
            return
        
        with open(requirements_path, 'r') as f:
            requirements = f.read()
        
        # Check for critical dependencies
        critical_deps = ['fastapi', 'uvicorn', 'pymongo', 'websockets', 'reportlab']
        
        for dep in critical_deps:
            if dep in requirements.lower():
                self.log_success(f"{dep} dependency present")
            else:
                self.log_issue(f"Missing critical dependency: {dep}")
        
        # Check for version pinning
        if '==' in requirements:
            self.log_success("Version pinning detected")
        else:
            self.log_warning("No version pinning - may cause compatibility issues")
        
        # Validate Python version compatibility
        try:
            result = subprocess.run([sys.executable, "--version"], 
                                  capture_output=True, text=True)
            python_version = result.stdout.strip()
            if "Python 3." in python_version:
                major, minor = python_version.split()[1].split('.')[:2]
                if int(major) >= 3 and int(minor) >= 8:
                    self.log_success(f"Python version compatible: {python_version}")
                else:
                    self.log_issue(f"Python version too old: {python_version}")
            else:
                self.log_issue("Could not determine Python version")
        except Exception as e:
            self.log_warning(f"Could not check Python version: {e}")
    
    def validate_frontend_dependencies(self):
        """Validate frontend dependencies and compatibility"""
        print("\n⚛️ VALIDATING FRONTEND DEPENDENCIES")
        print("=" * 50)
        
        package_json_path = Path("/app/frontend/package.json")
        
        if not package_json_path.exists():
            self.log_issue("frontend/package.json not found")
            return
        
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
        except Exception as e:
            self.log_issue(f"Could not parse package.json: {e}")
            return
        
        # Check for critical dependencies
        dependencies = package_data.get('dependencies', {})
        dev_dependencies = package_data.get('devDependencies', {})
        all_deps = {**dependencies, **dev_dependencies}
        
        critical_deps = ['react', 'react-dom', 'react-scripts']
        
        for dep in critical_deps:
            if dep in all_deps:
                self.log_success(f"{dep} dependency present: {all_deps[dep]}")
            else:
                self.log_issue(f"Missing critical dependency: {dep}")
        
        # Check React version compatibility
        if 'react' in dependencies:
            react_version = dependencies['react']
            if '^18' in react_version or '^17' in react_version:
                self.log_success(f"React version compatible: {react_version}")
            else:
                self.log_warning(f"React version may be outdated: {react_version}")
        
        # Check for build scripts
        scripts = package_data.get('scripts', {})
        if 'build' in scripts:
            self.log_success("Build script present")
        else:
            self.log_issue("No build script found")
        
        if 'start' in scripts:
            self.log_success("Start script present")
        else:
            self.log_warning("No start script found")
    
    def validate_node_compatibility(self):
        """Validate Node.js installation and compatibility"""
        print("\n🟢 VALIDATING NODE.JS COMPATIBILITY")
        print("=" * 50)
        
        # Check if Node.js is available
        try:
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                version_match = re.match(r'v(\d+)\.(\d+)\.(\d+)', node_version)
                if version_match:
                    major = int(version_match.group(1))
                    minor = int(version_match.group(2))
                    
                    # Check for Node.js 20 (preferred) or 18+ (minimum for React 19)
                    if major == 20:
                        self.log_success(f"Node.js 20 (optimal): {node_version}")
                    elif major >= 18:
                        if major == 18 and minor >= 17:
                            self.log_success(f"Node.js version compatible with React 19: {node_version}")
                        elif major > 18:
                            self.log_success(f"Node.js version compatible: {node_version}")
                        else:
                            self.log_warning(f"Node.js 18.17+ required for React 19, got: {node_version}")
                    else:
                        self.log_issue(f"Node.js version too old for React 19: {node_version} (need 18.17+)")
                else:
                    self.log_warning(f"Could not parse Node.js version: {node_version}")
            else:
                self.log_issue("Node.js not found or not working")
        except FileNotFoundError:
            self.log_issue("Node.js not installed")
        except Exception as e:
            self.log_warning(f"Could not check Node.js: {e}")
        
        # Check npm compatibility
        try:
            result = subprocess.run(['npm', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                npm_version = result.stdout.strip()
                npm_major = int(npm_version.split('.')[0])
                if npm_major >= 8:
                    self.log_success(f"npm version compatible: {npm_version}")
                else:
                    self.log_warning(f"npm version may be outdated: {npm_version} (recommended: 8+)")
            else:
                self.log_issue("npm not working")
        except FileNotFoundError:
            self.log_issue("npm not installed")
        except Exception as e:
            self.log_warning(f"Could not check npm: {e}")
        
        # Check yarn availability
        try:
            result = subprocess.run(['yarn', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                yarn_version = result.stdout.strip()
                self.log_success(f"yarn available: {yarn_version}")
            else:
                self.log_warning("yarn not available (npm will be used)")
        except FileNotFoundError:
            self.log_warning("yarn not installed (npm will be used)")
        except Exception as e:
            self.log_warning(f"Could not check yarn: {e}")
    
    def validate_system_compatibility(self):
        """Validate system compatibility for production"""
        print("\n🖥️ VALIDATING SYSTEM COMPATIBILITY")
        print("=" * 50)
        
        # Check OS compatibility
        try:
            with open('/etc/os-release') as f:
                os_info = f.read().lower()
                if 'ubuntu' in os_info:
                    self.log_success("Ubuntu detected - fully supported")
                elif 'debian' in os_info:
                    self.log_success("Debian detected - fully supported")
                elif 'centos' in os_info or 'rhel' in os_info:
                    self.log_warning("CentOS/RHEL detected - may need adjustments")
                else:
                    self.log_warning("OS not specifically tested")
        except Exception as e:
            self.log_warning(f"Could not determine OS: {e}")
        
        # Check system resources
        try:
            # Memory check
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        mem_kb = int(line.split()[1])
                        mem_gb = mem_kb / (1024**2)
                        if mem_gb >= 2:
                            self.log_success(f"Memory sufficient: {mem_gb:.1f}GB")
                        elif mem_gb >= 1:
                            self.log_warning(f"Memory adequate: {mem_gb:.1f}GB")
                        else:
                            self.log_issue(f"Memory insufficient: {mem_gb:.1f}GB")
                        break
        except Exception as e:
            self.log_warning(f"Could not check memory: {e}")
        
        # Disk space check
        try:
            statvfs = os.statvfs('/')
            available_gb = (statvfs.f_bavail * statvfs.f_frsize) / (1024**3)
            if available_gb >= 10:
                self.log_success(f"Disk space sufficient: {available_gb:.1f}GB")
            elif available_gb >= 5:
                self.log_warning(f"Disk space adequate: {available_gb:.1f}GB")
            else:
                self.log_issue(f"Disk space insufficient: {available_gb:.1f}GB")
        except Exception as e:
            self.log_warning(f"Could not check disk space: {e}")
        
        # Check systemd (required for services)
        try:
            result = subprocess.run(['systemctl', '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.log_success("systemd available")
            else:
                self.log_issue("systemd not available")
        except FileNotFoundError:
            self.log_issue("systemd not found")
        except Exception as e:
            self.log_warning(f"Could not check systemd: {e}")
    
    def validate_network_requirements(self):
        """Validate network requirements for production"""
        print("\n🌐 VALIDATING NETWORK REQUIREMENTS")
        print("=" * 50)
        
        # Check internet connectivity
        test_urls = [
            'https://deb.nodesource.com',
            'https://www.mongodb.org',
            'https://registry.npmjs.org',
            'https://pypi.org'
        ]
        
        for url in test_urls:
            try:
                import urllib.request
                response = urllib.request.urlopen(url, timeout=10)
                if response.getcode() == 200:
                    self.log_success(f"Can reach {url}")
                else:
                    self.log_warning(f"Issue connecting to {url}")
            except Exception as e:
                self.log_warning(f"Cannot reach {url}: {e}")
        
        # Check required ports availability
        required_ports = [80, 443, 8001, 27017]
        for port in required_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result != 0:
                    self.log_success(f"Port {port} available")
                else:
                    self.log_warning(f"Port {port} already in use")
            except Exception as e:
                self.log_warning(f"Could not check port {port}: {e}")
    
    def validate_security_requirements(self):
        """Validate security requirements for production"""
        print("\n🔒 VALIDATING SECURITY REQUIREMENTS")
        print("=" * 50)
        
        # Check if running as root (bad for production)
        if os.geteuid() == 0:
            self.log_warning("Running validation as root (installer needs root, but app shouldn't run as root)")
        else:
            self.log_success("Not running as root")
        
        # Check firewall
        try:
            result = subprocess.run(['ufw', 'status'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                if 'Status: active' in result.stdout:
                    self.log_success("UFW firewall active")
                else:
                    self.log_warning("UFW firewall not active")
            else:
                self.log_warning("UFW not available")
        except FileNotFoundError:
            self.log_warning("UFW not installed")
        except Exception as e:
            self.log_warning(f"Could not check firewall: {e}")
        
        # Check SSL certificate tools
        try:
            result = subprocess.run(['openssl', 'version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.log_success("OpenSSL available")
            else:
                self.log_issue("OpenSSL not working")
        except FileNotFoundError:
            self.log_issue("OpenSSL not installed")
        except Exception as e:
            self.log_warning(f"Could not check OpenSSL: {e}")
    
    def validate_application_files(self):
        """Validate application files are present and correct"""
        print("\n📁 VALIDATING APPLICATION FILES")
        print("=" * 50)
        
        required_files = [
            "/app/backend/server.py",
            "/app/backend/requirements.txt",
            "/app/frontend/package.json",
            "/app/frontend/src/App.js",
            "/app/install.py"
        ]
        
        for file_path in required_files:
            if Path(file_path).exists():
                self.log_success(f"{file_path} exists")
            else:
                self.log_issue(f"{file_path} missing")
        
        # Check backend server.py for critical components
        try:
            with open("/app/backend/server.py", 'r') as f:
                server_content = f.read()
            
            critical_components = ['FastAPI', 'WebSocket', 'MongoDB', 'health']
            for component in critical_components:
                if component.lower() in server_content.lower():
                    self.log_success(f"Backend has {component} support")
                else:
                    self.log_warning(f"Backend missing {component} support")
        except Exception as e:
            self.log_warning(f"Could not validate backend: {e}")
    
    def run_comprehensive_validation(self):
        """Run all validation checks"""
        print("🔍 SECRET POLL - PRODUCTION VALIDATION")
        print("=" * 60)
        
        # Run all validations
        self.validate_install_script()
        self.validate_system_compatibility()
        self.validate_node_compatibility()
        self.validate_backend_dependencies()
        self.validate_frontend_dependencies()
        self.validate_network_requirements()
        self.validate_security_requirements()
        self.validate_application_files()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        
        print(f"✅ Successes: {len(self.successes)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Issues: {len(self.issues)}")
        
        # Categorize readiness
        if len(self.issues) == 0:
            if len(self.warnings) == 0:
                status = "🎉 PERFECT - PRODUCTION READY"
                color = "\033[92m"  # Green
            elif len(self.warnings) <= 3:
                status = "✅ GOOD - PRODUCTION READY (minor warnings)"
                color = "\033[93m"  # Yellow
            else:
                status = "⚠️ ACCEPTABLE - Review warnings before production"
                color = "\033[93m"  # Yellow
        elif len(self.issues) <= 2:
            status = "⚠️ NEEDS ATTENTION - Address issues before production"
            color = "\033[93m"  # Yellow
        else:
            status = "❌ NOT READY - Critical issues must be resolved"
            color = "\033[91m"  # Red
        
        print(f"\n{color}{status}\0\033[0m")
        
        if self.issues:
            print(f"\n❌ Critical Issues to Address:")
            for issue in self.issues:
                print(f"   • {issue}")
        
        if self.warnings:
            print(f"\n⚠️ Warnings to Review:")
            for warning in self.warnings[:5]:  # Show top 5 warnings
                print(f"   • {warning}")
            if len(self.warnings) > 5:
                print(f"   ... and {len(self.warnings) - 5} more warnings")
        
        return len(self.issues) == 0

def main():
    """Main validation function"""
    validator = ProductionValidator()
    ready = validator.run_comprehensive_validation()
    
    print(f"\n🎯 Final Status: {'READY FOR PRODUCTION' if ready else 'NOT READY'}")
    
    return ready

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)