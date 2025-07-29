#!/usr/bin/env python3
"""
Secret Poll - Production Installation Script
============================================

A professional Python script to install and configure Secret Poll
for production deployment with domain configuration, web server setup,
and SSL certificates.

Usage: sudo python3 install.py
"""

import os
import sys
import subprocess
import json
import socket
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.request
import urllib.error

class Colors:
    """ANSI color codes for terminal output"""
    PURPLE = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

class SecretPollInstaller:
    """Professional installer for Secret Poll application"""
    
    def __init__(self):
        self.config = {}
        self.install_dir = "/opt/secret-poll"
        self.log_file = "/var/log/secret-poll-install.log"
        self.service_name = "secret-poll"
        self.total_steps = 12
        self.current_step = 0
        
    def progress(self, step_description: str):
        """Display progress with step counter"""
        self.current_step += 1
        percentage = int((self.current_step / self.total_steps) * 100)
        bar_length = 30
        filled_length = int(bar_length * self.current_step // self.total_steps)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        print(f"\n{Colors.BOLD}[{self.current_step}/{self.total_steps}] {step_description}{Colors.END}")
        print(f"{Colors.CYAN}Progress: |{bar}| {percentage}% Complete{Colors.END}")
        self.log(f"Step {self.current_step}/{self.total_steps}: {step_description}", "PROGRESS")
        
    def print_header(self):
        """Print installation header"""
        header = f"""
{Colors.PURPLE}╔═══════════════════════════════════════════════════════════════════════════════╗
║                      🗳️  SECRET POLL - PRODUCTION INSTALLER                  ║
║                           Professional Python Installation                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝{Colors.END}
"""
        print(header)
    
    def log(self, message: str, level: str = "INFO"):
        """Log messages to file and console"""
        timestamp = subprocess.check_output(['date'], text=True).strip()
        log_entry = f"[{timestamp}] {level}: {message}"
        
        # Console output with colors
        if level == "INFO":
            print(f"{Colors.CYAN}ℹ️  {message}{Colors.END}")
        elif level == "SUCCESS":
            print(f"{Colors.GREEN}✅ {message}{Colors.END}")
        elif level == "WARNING":
            print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")
        elif level == "ERROR":
            print(f"{Colors.RED}❌ {message}{Colors.END}")
        elif level == "STEP":
            print(f"{Colors.BLUE}▶ {message}{Colors.END}")
        
        # Write to log file
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            with open(self.log_file, 'a') as f:
                f.write(log_entry + '\n')
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")
    
    def cleanup_vps(self):
        """Clean VPS environment to avoid conflicts"""
        self.progress("Cleaning VPS environment to prevent conflicts")
        
        # Stop potentially conflicting services
        conflicting_services = ['apache2', 'nginx', 'httpd', 'lighttpd']
        for service in conflicting_services:
            try:
                # Check if service is running
                result = subprocess.run(['systemctl', 'is-active', service], 
                                      capture_output=True, text=True)
                if result.stdout.strip() == 'active':
                    self.log(f"Stopping conflicting service: {service}", "INFO")
                    self.run_command(['systemctl', 'stop', service], ignore_errors=True)
                    self.run_command(['systemctl', 'disable', service], ignore_errors=True)
            except:
                continue
        
        # Clean package cache
        self.log("Cleaning package cache", "INFO")
        self.run_command(['apt-get', 'clean'], ignore_errors=True)
        self.run_command(['apt-get', 'autoremove', '-y'], ignore_errors=True)
        
        # Clear any existing installations in target directory
        if os.path.exists(self.install_dir):
            self.log(f"Removing existing installation at {self.install_dir}", "WARNING")
            self.run_command(['rm', '-rf', self.install_dir], ignore_errors=True)
        
        # Check for port conflicts and attempt to free them
        conflicting_ports = [80, 443, 8001]
        for port in conflicting_ports:
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                      capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            self.log(f"Killing process on port {port} (PID: {pid})", "WARNING")
                            self.run_command(['kill', '-9', pid], ignore_errors=True)
            except:
                continue
        
        self.log("VPS cleanup completed", "SUCCESS")
    
    def check_root(self):
        """Verify script is running as root"""
        if os.geteuid() != 0:
            self.log("This script must be run as root", "ERROR")
            self.log("Please run: sudo python3 install.py", "INFO")
            sys.exit(1)
    
    def check_system_requirements(self):
        """Check system requirements and compatibility"""
        self.log("Checking system requirements", "STEP")
        
        # Check OS
        try:
            with open('/etc/os-release') as f:
                os_info = f.read()
                if 'ubuntu' in os_info.lower() or 'debian' in os_info.lower():
                    self.log("Supported OS detected", "SUCCESS")
                else:
                    self.log("OS may not be fully supported, but continuing", "WARNING")
        except FileNotFoundError:
            self.log("Cannot determine OS, continuing with installation", "WARNING")
        
        # Check available disk space (minimum 2GB)
        statvfs = os.statvfs('/')
        available_gb = (statvfs.f_bavail * statvfs.f_frsize) / (1024**3)
        if available_gb < 2:
            self.log(f"Low disk space: {available_gb:.1f}GB available", "ERROR")
            sys.exit(1)
        
        # Check memory (minimum 1GB)
        try:
            with open('/proc/meminfo') as f:
                for line in f:
                    if line.startswith('MemAvailable:'):
                        mem_kb = int(line.split()[1])
                        mem_gb = mem_kb / (1024**2)
                        if mem_gb < 1:
                            self.log(f"Low memory: {mem_gb:.1f}GB available", "WARNING")
                        break
        except:
            pass
        
        self.log("System requirements check completed", "SUCCESS")
    
    def collect_configuration(self):
        """Interactive configuration collection"""
        self.log("Starting configuration setup", "STEP")
        
        print(f"\n{Colors.CYAN}Please provide the following configuration details:{Colors.END}\n")
        
        # Domain configuration
        while True:
            domain = input(f"{Colors.BOLD}Domain or IP address{Colors.END} (e.g., poll.yourdomain.com): ").strip()
            if domain:
                if self.validate_domain_or_ip(domain):
                    self.config['domain'] = domain
                    break
                else:
                    print(f"{Colors.RED}Invalid domain or IP format{Colors.END}")
            else:
                print(f"{Colors.RED}Domain is required{Colors.END}")
        
        # Check if domain is IP or hostname
        self.config['is_ip'] = self.is_ip_address(domain)
        
        # SSL Configuration (only for domains, not IPs)
        if not self.config['is_ip']:
            ssl_choice = input(f"{Colors.BOLD}Enable SSL with Let's Encrypt?{Colors.END} [Y/n]: ").strip().lower()
            self.config['enable_ssl'] = ssl_choice != 'n'
            
            if self.config['enable_ssl']:
                while True:
                    email = input(f"{Colors.BOLD}Email for SSL certificates{Colors.END}: ").strip()
                    if email and '@' in email:
                        self.config['ssl_email'] = email
                        break
                    print(f"{Colors.RED}Valid email required{Colors.END}")
        else:
            self.config['enable_ssl'] = False
        
        # Web server choice
        print(f"\n{Colors.BOLD}Web server options:{Colors.END}")
        print("1. Nginx (Recommended)")
        print("2. Apache")
        print("3. Standalone (No reverse proxy)")
        
        while True:
            choice = input(f"{Colors.BOLD}Choose web server{Colors.END} [1-3] (default: 1): ").strip()
            if not choice:
                choice = "1"
            
            if choice in ["1", "2", "3"]:
                web_servers = {"1": "nginx", "2": "apache", "3": "standalone"}
                self.config['web_server'] = web_servers[choice]
                break
            print(f"{Colors.RED}Please choose 1, 2, or 3{Colors.END}")
        
        # Environment configuration
        env_choice = input(f"{Colors.BOLD}Environment{Colors.END} [production/staging] (default: production): ").strip().lower()
        self.config['environment'] = env_choice if env_choice in ['production', 'staging'] else 'production'
        
        # Installation directory
        install_dir = input(f"{Colors.BOLD}Installation directory{Colors.END} (default: /opt/secret-poll): ").strip()
        if install_dir:
            self.install_dir = install_dir
        
        # Show configuration summary
        self.show_configuration_summary()
    
    def validate_domain_or_ip(self, value: str) -> bool:
        """Validate domain name or IP address"""
        # Check if it's a valid IP address
        if self.is_ip_address(value):
            return True
        
        # Check if it's a valid domain name
        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
        )
        return bool(domain_pattern.match(value))
    
    def is_ip_address(self, value: str) -> bool:
        """Check if value is a valid IP address"""
        try:
            socket.inet_aton(value)
            return True
        except socket.error:
            return False
    
    def show_configuration_summary(self):
        """Display configuration summary and get confirmation"""
        print(f"\n{Colors.PURPLE}╔═══════════════════════════════════════════════════════════════════════════════╗")
        print(f"║                            CONFIGURATION SUMMARY                             ║")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════╝{Colors.END}")
        
        print(f"{Colors.CYAN}Domain:{Colors.END} {self.config['domain']}")
        print(f"{Colors.CYAN}SSL:{Colors.END} {'Enabled' if self.config['enable_ssl'] else 'Disabled'}")
        if self.config['enable_ssl']:
            print(f"{Colors.CYAN}SSL Email:{Colors.END} {self.config['ssl_email']}")
        print(f"{Colors.CYAN}Web Server:{Colors.END} {self.config['web_server'].title()}")
        print(f"{Colors.CYAN}Environment:{Colors.END} {self.config['environment']}")
        print(f"{Colors.CYAN}Install Directory:{Colors.END} {self.install_dir}")
        
        confirm = input(f"\n{Colors.BOLD}Proceed with installation? [Y/n]:{Colors.END} ").strip().lower()
        if confirm == 'n':
            self.log("Installation cancelled by user", "INFO")
            sys.exit(0)
    
    def install_system_dependencies(self):
        """Install system dependencies"""
        self.progress("Installing system dependencies and preparing environment")
        
        # Update package list
        self.run_command(['apt-get', 'update'], "Updating package list")
        
        # Install basic dependencies
        basic_packages = [
            'curl', 'wget', 'git', 'unzip', 'software-properties-common',
            'apt-transport-https', 'ca-certificates', 'gnupg', 'lsb-release',
            'lsof', 'htop', 'nano', 'vim'  # Added useful system tools
        ]
        self.run_command(['apt-get', 'install', '-y'] + basic_packages, "Installing basic packages")
        
        # Install Python dependencies
        python_packages = ['python3', 'python3-pip', 'python3-venv', 'python3-dev', 'build-essential']
        self.run_command(['apt-get', 'install', '-y'] + python_packages, "Installing Python")
        
        # Install Node.js 18
        self.log("Installing Node.js 18", "INFO")
        try:
            # First try using NodeSource repository
            self.run_command(['curl', '-fsSL', 'https://deb.nodesource.com/setup_18.x', '-o', '/tmp/nodejs_setup.sh'])
            self.run_command(['bash', '/tmp/nodejs_setup.sh'])
            self.run_command(['apt-get', 'install', '-y', 'nodejs'], "Installing Node.js")
        except:
            # Fallback to Ubuntu repository
            self.log("NodeSource failed, trying Ubuntu repository", "WARNING")
            self.run_command(['apt-get', 'install', '-y', 'nodejs', 'npm'], "Installing Node.js from Ubuntu repos")
        
        # Install MongoDB
        self.install_mongodb()
        
        # Install web server
        if self.config['web_server'] == 'nginx':
            self.run_command(['apt-get', 'install', '-y', 'nginx'], "Installing Nginx")
        elif self.config['web_server'] == 'apache':
            self.run_command(['apt-get', 'install', '-y', 'apache2'], "Installing Apache")
        
        self.log("System dependencies installed successfully", "SUCCESS")
    
    def install_mongodb(self):
        """Install MongoDB"""
        self.log("Installing MongoDB", "INFO")
        
        # Try multiple installation methods
        mongodb_installed = False
        
        # Method 1: Try official MongoDB repository
        try:
            self.log("Attempting MongoDB installation via official repository", "INFO")
            
            # Download and install GPG key
            self.run_command([
                'curl', '-fsSL', 'https://www.mongodb.org/static/pgp/server-7.0.asc',
                '-o', '/tmp/mongodb.asc'
            ])
            
            # Try multiple GPG command variations
            gpg_commands = [
                ['bash', '-c', 'cat /tmp/mongodb.asc | gpg --dearmor --batch --yes -o /usr/share/keyrings/mongodb-server-7.0.gpg'],
                ['bash', '-c', 'gpg --dearmor --batch --yes < /tmp/mongodb.asc > /usr/share/keyrings/mongodb-server-7.0.gpg'],
                ['gpg', '--dearmor', '--batch', '--yes', '--output', '/usr/share/keyrings/mongodb-server-7.0.gpg', '/tmp/mongodb.asc']
            ]
            
            gpg_success = False
            for cmd in gpg_commands:
                try:
                    self.run_command(cmd)
                    gpg_success = True
                    break
                except:
                    continue
            
            if not gpg_success:
                raise Exception("All GPG methods failed")
            
            # Add MongoDB repository
            distro = self.run_command(['lsb_release', '-cs'], capture_output=True).strip()
            repo_line = f"deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu {distro}/mongodb-org/7.0 multiverse"
            
            with open('/etc/apt/sources.list.d/mongodb-org-7.0.list', 'w') as f:
                f.write(repo_line + '\n')
            
            # Install MongoDB
            self.run_command(['apt-get', 'update'])
            self.run_command(['apt-get', 'install', '-y', 'mongodb-org'], "Installing MongoDB from official repository")
            
            # Enable and start MongoDB
            self.run_command(['systemctl', 'enable', 'mongod'])
            self.run_command(['systemctl', 'start', 'mongod'])
            
            mongodb_installed = True
            self.log("MongoDB installed successfully from official repository", "SUCCESS")
            
        except Exception as e:
            self.log(f"Official MongoDB installation failed: {e}", "WARNING")
        
        # Method 2: Fallback to Ubuntu repositories
        if not mongodb_installed:
            try:
                self.log("Attempting MongoDB installation via Ubuntu repositories", "INFO")
                
                # Try installing from Ubuntu repositories
                self.run_command(['apt-get', 'install', '-y', 'mongodb'], "Installing MongoDB from Ubuntu repos")
                
                # Start the appropriate service
                mongodb_service = None
                try:
                    # Check which MongoDB service is available
                    result = subprocess.run(['systemctl', 'list-unit-files'], 
                                          capture_output=True, text=True, check=True)
                    
                    if 'mongod.service' in result.stdout:
                        mongodb_service = 'mongod'
                    elif 'mongodb.service' in result.stdout:
                        mongodb_service = 'mongodb'
                    
                    if mongodb_service:
                        self.run_command(['systemctl', 'enable', mongodb_service])
                        self.run_command(['systemctl', 'start', mongodb_service])
                        self.log(f"MongoDB started as {mongodb_service} service", "SUCCESS")
                    else:
                        self.log("MongoDB installed but service not found", "WARNING")
                        
                except Exception as service_error:
                    self.log(f"Service setup failed: {service_error}", "WARNING")
                
                mongodb_installed = True
                self.log("MongoDB installed successfully from Ubuntu repositories", "SUCCESS")
                
            except Exception as e:
                self.log(f"Ubuntu repository MongoDB installation failed: {e}", "WARNING")
        
        # Method 3: Try snap package
        if not mongodb_installed:
            try:
                self.log("Attempting MongoDB installation via snap", "INFO")
                self.run_command(['snap', 'install', 'mongodb'], "Installing MongoDB via snap")
                mongodb_installed = True
                self.log("MongoDB installed successfully via snap", "SUCCESS")
                
            except Exception as e:
                self.log(f"Snap MongoDB installation failed: {e}", "WARNING")
        
        # Final check
        if not mongodb_installed:
            self.log("All MongoDB installation methods failed", "ERROR")
            self.log("MongoDB will need to be installed manually", "WARNING")
            self.log("The application can still be installed, but you'll need to:", "INFO")
            self.log("1. Install MongoDB manually", "INFO") 
            self.log("2. Ensure it's running on localhost:27017", "INFO")
        else:
            # Verify MongoDB is running
            self.verify_mongodb_installation()
    
    def verify_mongodb_installation(self):
        """Verify MongoDB is properly installed and running"""
        self.log("Verifying MongoDB installation", "INFO")
        
        # Wait a moment for service to start
        import time
        time.sleep(3)
        
        # Try different ways to check if MongoDB is running
        mongodb_running = False
        
        # Check systemd services
        for service in ['mongod', 'mongodb']:
            try:
                result = subprocess.run(['systemctl', 'is-active', service], 
                                      capture_output=True, text=True)
                if result.stdout.strip() == 'active':
                    self.log(f"MongoDB is running as {service} service", "SUCCESS")
                    mongodb_running = True
                    break
            except:
                continue
        
        # If systemd check failed, try connecting directly
        if not mongodb_running:
            try:
                # Try to connect to MongoDB
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('localhost', 27017))
                sock.close()
                
                if result == 0:
                    self.log("MongoDB is responding on port 27017", "SUCCESS")
                    mongodb_running = True
                else:
                    self.log("MongoDB is not responding on port 27017", "WARNING")
                    
            except Exception as e:
                self.log(f"Could not verify MongoDB connection: {e}", "WARNING")
        
        if not mongodb_running:
            self.log("MongoDB verification failed - manual intervention may be required", "WARNING")
    
    def setup_application(self):
        """Setup the Secret Poll application"""
        self.log("Setting up Secret Poll application", "STEP")
        
        # Create installation directory
        os.makedirs(self.install_dir, exist_ok=True)
        
        # Copy application files from current directory
        current_dir = Path(__file__).parent
        
        # Copy backend
        backend_src = current_dir / 'backend'
        backend_dst = Path(self.install_dir) / 'backend'
        if backend_src.exists():
            shutil.copytree(backend_src, backend_dst, dirs_exist_ok=True)
        
        # Copy frontend
        frontend_src = current_dir / 'frontend'
        frontend_dst = Path(self.install_dir) / 'frontend'
        if frontend_src.exists():
            shutil.copytree(frontend_src, frontend_dst, dirs_exist_ok=True)
        
        # Setup backend
        self.setup_backend()
        
        # Setup frontend
        self.setup_frontend()
        
        self.log("Application setup completed", "SUCCESS")
    
    def setup_backend(self):
        """Setup backend application"""
        self.log("Setting up backend", "INFO")
        
        backend_dir = Path(self.install_dir) / 'backend'
        os.chdir(backend_dir)
        
        # Create virtual environment
        self.run_command(['python3', '-m', 'venv', 'venv'], "Creating Python virtual environment")
        
        # Install Python dependencies
        pip_path = backend_dir / 'venv' / 'bin' / 'pip'
        self.run_command([str(pip_path), 'install', '--upgrade', 'pip'])
        self.run_command([str(pip_path), 'install', '-r', 'requirements.txt'], "Installing Python packages")
        
        # Create environment configuration
        self.create_backend_config()
    
    def setup_frontend(self):
        """Setup frontend application"""
        self.log("Setting up frontend", "INFO")
        
        frontend_dir = Path(self.install_dir) / 'frontend'
        os.chdir(frontend_dir)
        
        # Install Node.js dependencies and build
        if (frontend_dir / 'yarn.lock').exists():
            self.run_command(['npm', 'install', '-g', 'yarn'])
            self.run_command(['yarn', 'install'], "Installing frontend dependencies")
            self.run_command(['yarn', 'build'], "Building frontend application")
        else:
            self.run_command(['npm', 'install'], "Installing frontend dependencies")
            self.run_command(['npm', 'run', 'build'], "Building frontend application")
        
        # Create environment configuration
        self.create_frontend_config()
    
    def create_backend_config(self):
        """Create backend environment configuration"""
        backend_env_path = Path(self.install_dir) / 'backend' / '.env'
        
        cors_origins = f"http://{self.config['domain']}"
        if self.config['enable_ssl']:
            cors_origins += f",https://{self.config['domain']}"
        
        config_content = f"""# Secret Poll Backend Configuration
MONGO_URL=mongodb://localhost:27017/secret_poll
PORT=8001
ENVIRONMENT={self.config['environment']}
CORS_ORIGINS={cors_origins}
SECRET_KEY={self.generate_secret_key()}

# Generated on $(date)
"""
        
        with open(backend_env_path, 'w') as f:
            f.write(config_content)
        
        self.log("Backend configuration created", "SUCCESS")
    
    def create_frontend_config(self):
        """Create frontend environment configuration"""
        frontend_env_path = Path(self.install_dir) / 'frontend' / '.env'
        
        backend_url = f"http://{self.config['domain']}:8001"
        if self.config['web_server'] != 'standalone':
            backend_url = f"http{'s' if self.config['enable_ssl'] else ''}://{self.config['domain']}"
        
        config_content = f"""# Secret Poll Frontend Configuration
REACT_APP_BACKEND_URL={backend_url}
GENERATE_SOURCEMAP=false
NODE_ENV={self.config['environment']}

# Generated on $(date)
"""
        
        with open(frontend_env_path, 'w') as f:
            f.write(config_content)
        
        self.log("Frontend configuration created", "SUCCESS")
    
    def generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        try:
            result = subprocess.run(['openssl', 'rand', '-hex', '32'], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except:
            # Fallback to Python random
            import secrets
            return secrets.token_hex(32)
    
    def configure_web_server(self):
        """Configure the web server"""
        if self.config['web_server'] == 'standalone':
            self.log("Skipping web server configuration (standalone mode)", "INFO")
            return
        
        self.log(f"Configuring {self.config['web_server'].title()}", "STEP")
        
        if self.config['web_server'] == 'nginx':
            self.configure_nginx()
        elif self.config['web_server'] == 'apache':
            self.configure_apache()
    
    def configure_nginx(self):
        """Configure Nginx"""
        config_content = self.generate_nginx_config()
        config_path = f"/etc/nginx/sites-available/{self.service_name}"
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Enable site
        enabled_path = f"/etc/nginx/sites-enabled/{self.service_name}"
        if os.path.exists(enabled_path):
            os.remove(enabled_path)
        os.symlink(config_path, enabled_path)
        
        # Test configuration
        self.run_command(['nginx', '-t'], "Testing Nginx configuration")
        self.run_command(['systemctl', 'reload', 'nginx'], "Reloading Nginx")
        
        self.log("Nginx configured successfully", "SUCCESS")
    
    def generate_nginx_config(self) -> str:
        """Generate Nginx configuration"""
        domain = self.config['domain']
        install_dir = self.install_dir
        
        config = f"""# Secret Poll Nginx Configuration
server {{
    listen 80;
    server_name {domain};"""
        
        if self.config['enable_ssl']:
            config += f"""
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {domain};
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;"""
        
        config += f"""
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy strict-origin-when-cross-origin;
    
    # Frontend
    location / {{
        root {install_dir}/frontend/build;
        index index.html;
        try_files $uri $uri/ /index.html;
    }}
    
    # API routes
    location /api/ {{
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }}
    
    # Static assets caching
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {{
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }}
}}
"""
        return config
    
    def configure_apache(self):
        """Configure Apache"""
        # Enable required modules
        modules = ['rewrite', 'proxy', 'proxy_http', 'proxy_wstunnel', 'headers']
        for module in modules:
            self.run_command(['a2enmod', module])
        
        # Create site configuration
        config_content = self.generate_apache_config()
        config_path = f"/etc/apache2/sites-available/{self.service_name}.conf"
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        # Enable site
        self.run_command(['a2ensite', f'{self.service_name}.conf'])
        self.run_command(['systemctl', 'reload', 'apache2'])
        
        self.log("Apache configured successfully", "SUCCESS")
    
    def generate_apache_config(self) -> str:
        """Generate Apache configuration"""
        domain = self.config['domain']
        install_dir = self.install_dir
        
        config = f"""# Secret Poll Apache Configuration
<VirtualHost *:80>
    ServerName {domain}
    DocumentRoot {install_dir}/frontend/build
    
    # Security headers
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
    Header always set X-XSS-Protection "1; mode=block"
    
    # API proxy
    ProxyPreserveHost On
    ProxyPass /api/ http://localhost:8001/api/
    ProxyPassReverse /api/ http://localhost:8001/api/
    
    # WebSocket support
    ProxyPass /api/ws/ ws://localhost:8001/api/ws/
    ProxyPassReverse /api/ws/ ws://localhost:8001/api/ws/
    
    # Frontend routing
    <Directory {install_dir}/frontend/build>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
        
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\\.html$ - [L]
        RewriteCond %{{REQUEST_FILENAME}} !-f
        RewriteCond %{{REQUEST_FILENAME}} !-d
        RewriteRule . /index.html [L]
    </Directory>
    
    # Static files caching
    <FilesMatch "\\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$">
        ExpiresActive On
        ExpiresDefault "access plus 1 year"
    </FilesMatch>
    
    ErrorLog ${{APACHE_LOG_DIR}}/{self.service_name}_error.log
    CustomLog ${{APACHE_LOG_DIR}}/{self.service_name}_access.log combined
</VirtualHost>"""
        
        if self.config['enable_ssl']:
            config += f"""

<VirtualHost *:443>
    ServerName {domain}
    DocumentRoot {install_dir}/frontend/build
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/{domain}/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/{domain}/privkey.pem
    
    # Security headers
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
    Header always set X-XSS-Protection "1; mode=block"
    
    # API proxy
    ProxyPreserveHost On
    ProxyPass /api/ http://localhost:8001/api/
    ProxyPassReverse /api/ http://localhost:8001/api/
    
    # WebSocket support
    ProxyPass /api/ws/ ws://localhost:8001/api/ws/
    ProxyPassReverse /api/ws/ ws://localhost:8001/api/ws/
    
    # Frontend routing
    <Directory {install_dir}/frontend/build>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
        
        RewriteEngine On
        RewriteBase /
        RewriteRule ^index\\.html$ - [L]
        RewriteCond %{{REQUEST_FILENAME}} !-f
        RewriteCond %{{REQUEST_FILENAME}} !-d
        RewriteRule . /index.html [L]
    </Directory>
    
    ErrorLog ${{APACHE_LOG_DIR}}/{self.service_name}_ssl_error.log
    CustomLog ${{APACHE_LOG_DIR}}/{self.service_name}_ssl_access.log combined
</VirtualHost>"""
        
        return config
    
    def setup_ssl(self):
        """Setup SSL certificates with Let's Encrypt"""
        if not self.config['enable_ssl']:
            return
        
        self.log("Setting up SSL certificates", "STEP")
        
        # Install Certbot
        self.run_command(['apt-get', 'install', '-y', 'certbot'], "Installing Certbot")
        
        if self.config['web_server'] == 'nginx':
            self.run_command(['apt-get', 'install', '-y', 'python3-certbot-nginx'])
        elif self.config['web_server'] == 'apache':
            self.run_command(['apt-get', 'install', '-y', 'python3-certbot-apache'])
        
        # Obtain certificate
        domain = self.config['domain']
        email = self.config['ssl_email']
        
        certbot_cmd = [
            'certbot', 'certonly', '--webroot',
            '-w', f"{self.install_dir}/frontend/build",
            '-d', domain,
            '--email', email,
            '--agree-tos',
            '--non-interactive'
        ]
        
        self.run_command(certbot_cmd, "Obtaining SSL certificate")
        
        # Setup auto-renewal
        self.setup_ssl_renewal()
        
        self.log("SSL certificates configured successfully", "SUCCESS")
    
    def setup_ssl_renewal(self):
        """Setup SSL certificate auto-renewal"""
        renewal_script = f"""#!/bin/bash
certbot renew --quiet
systemctl reload {self.config['web_server']}
"""
        
        with open('/etc/cron.daily/certbot-renewal', 'w') as f:
            f.write(renewal_script)
        
        os.chmod('/etc/cron.daily/certbot-renewal', 0o755)
        
        self.log("SSL auto-renewal configured", "SUCCESS")
    
    def create_systemd_service(self):
        """Create systemd service for the application"""
        self.log("Creating systemd service", "STEP")
        
        service_content = f"""[Unit]
Description=Secret Poll Application
After=network.target mongodb.service
Requires=mongodb.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory={self.install_dir}/backend
Environment=PATH={self.install_dir}/backend/venv/bin
ExecStart={self.install_dir}/backend/venv/bin/python server.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        
        service_path = f"/etc/systemd/system/{self.service_name}.service"
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        # Set proper ownership
        self.run_command(['chown', '-R', 'www-data:www-data', self.install_dir])
        
        # Enable and start service
        self.run_command(['systemctl', 'daemon-reload'])
        self.run_command(['systemctl', 'enable', self.service_name])
        self.run_command(['systemctl', 'start', self.service_name])
        
        self.log("Systemd service created and started", "SUCCESS")
    
    def create_management_tools(self):
        """Create management scripts"""
        self.log("Creating management tools", "STEP")
        
        # Status script
        status_script = f"""#!/bin/bash
echo "Secret Poll Status"
echo "=================="
echo
systemctl status {self.service_name} --no-pager
echo
systemctl status mongodb --no-pager
echo
systemctl status {self.config['web_server']} --no-pager
echo
echo "Application Health:"
curl -s http://localhost:8001/api/health || echo "Backend not responding"
"""
        
        with open(f'{self.install_dir}/status.sh', 'w') as f:
            f.write(status_script)
        
        # Logs script
        logs_script = f"""#!/bin/bash
if [ "$1" = "follow" ]; then
    journalctl -u {self.service_name} -f
else
    journalctl -u {self.service_name} --no-pager
fi
"""
        
        with open(f'{self.install_dir}/logs.sh', 'w') as f:
            f.write(logs_script)
        
        # Restart script
        restart_script = f"""#!/bin/bash
systemctl restart {self.service_name}
systemctl restart {self.config['web_server']}
echo "Services restarted"
"""
        
        with open(f'{self.install_dir}/restart.sh', 'w') as f:
            f.write(restart_script)
        
        # Make scripts executable
        for script in ['status.sh', 'logs.sh', 'restart.sh']:
            os.chmod(f'{self.install_dir}/{script}', 0o755)
        
        self.log("Management tools created", "SUCCESS")
    
    def run_command(self, cmd: List[str], description: str = "", capture_output: bool = False, ignore_errors: bool = False) -> str:
        """Run a system command with error handling"""
        try:
            if description:
                self.log(description, "INFO")
            
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.stdout
            else:
                with open(self.log_file, 'a') as log_f:
                    result = subprocess.run(cmd, stdout=log_f, stderr=log_f, check=True)
                return ""
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {' '.join(cmd)}"
            if description:
                error_msg = f"{description} failed"
            
            self.log(error_msg, "ERROR" if not ignore_errors else "WARNING")
            self.log(f"Exit code: {e.returncode}", "ERROR" if not ignore_errors else "WARNING")
            
            if ignore_errors:
                self.log("Continuing despite error (ignore_errors=True)", "WARNING")
                return ""
            
            # Show recent log entries for debugging
            try:
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    print(f"\n{Colors.RED}Recent log entries:{Colors.END}")
                    for line in lines[-10:]:
                        print(line.rstrip())
            except:
                pass
            
            sys.exit(1)
        except FileNotFoundError:
            error_msg = f"Command not found: {cmd[0]}"
            self.log(error_msg, "ERROR" if not ignore_errors else "WARNING")
            
            if ignore_errors:
                return ""
            
            sys.exit(1)
    
    def verify_installation(self):
        """Verify the installation is working correctly"""
        self.log("Verifying installation", "STEP")
        
        # Wait for services to start
        import time
        time.sleep(5)
        
        # Check service status
        try:
            result = subprocess.run(['systemctl', 'is-active', self.service_name], 
                                  capture_output=True, text=True)
            if result.stdout.strip() == 'active':
                self.log("Secret Poll service is running", "SUCCESS")
            else:
                self.log("Secret Poll service is not running properly", "WARNING")
        except:
            self.log("Could not check service status", "WARNING")
        
        # Check API health
        try:
            import urllib.request
            with urllib.request.urlopen('http://localhost:8001/api/health', timeout=10) as response:
                if response.getcode() == 200:
                    self.log("API health check passed", "SUCCESS")
                else:
                    self.log("API health check failed", "WARNING")
        except Exception as e:
            self.log(f"Could not verify API: {e}", "WARNING")
        
        self.log("Installation verification completed", "SUCCESS")
    
    def show_final_instructions(self):
        """Show final instructions to the user"""
        protocol = 'https' if self.config['enable_ssl'] else 'http'
        domain = self.config['domain']
        
        print(f"""
{Colors.GREEN}╔═══════════════════════════════════════════════════════════════════════════════╗
║                           🎉 INSTALLATION COMPLETED!                         ║
╚═══════════════════════════════════════════════════════════════════════════════╝{Colors.END}

{Colors.CYAN}🌐 Your Secret Poll application is now ready!{Colors.END}

{Colors.BOLD}Access URLs:{Colors.END}
  • Application: {protocol}://{domain}/
  • API Health: {protocol}://{domain}/api/health

{Colors.BOLD}Management Commands:{Colors.END}
  • Check status: {self.install_dir}/status.sh
  • View logs: {self.install_dir}/logs.sh [follow]
  • Restart services: {self.install_dir}/restart.sh

{Colors.BOLD}Service Management:{Colors.END}
  • Application: systemctl {{start|stop|restart}} {self.service_name}
  • Web Server: systemctl {{start|stop|restart}} {self.config['web_server']}
  • Database: systemctl {{start|stop|restart}} mongodb

{Colors.BOLD}Log Files:{Colors.END}
  • Installation: {self.log_file}
  • Application: journalctl -u {self.service_name}
  • Web Server: /var/log/{self.config['web_server']}/

{Colors.BOLD}Configuration Files:{Colors.END}
  • Backend: {self.install_dir}/backend/.env
  • Frontend: {self.install_dir}/frontend/.env
""")
        
        if self.config['enable_ssl']:
            print(f"{Colors.CYAN}🔒 SSL Certificate auto-renewal is configured{Colors.END}")
        
        print(f"\n{Colors.GREEN}🎊 Your Secret Poll application is ready for production use!{Colors.END}")
    
    def run(self):
        """Main installation process"""
        try:
            self.print_header()
            self.check_root()
            self.check_system_requirements()
            self.collect_configuration()
            self.install_system_dependencies()
            self.setup_application()
            self.configure_web_server()
            self.setup_ssl()
            self.create_systemd_service()
            self.create_management_tools()
            self.verify_installation()
            self.show_final_instructions()
            
        except KeyboardInterrupt:
            self.log("Installation interrupted by user", "WARNING")
            sys.exit(1)
        except Exception as e:
            self.log(f"Installation failed: {str(e)}", "ERROR")
            sys.exit(1)

if __name__ == "__main__":
    installer = SecretPollInstaller()
    installer.run()