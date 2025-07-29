# 🛠️ MongoDB Troubleshooting Guide

## Issue Fixed: GPG Command Error

**Problem**: Installation fails with GPG error during MongoDB setup:
```
usage: gpg [options] --dearmor [file]
ERROR: Command failed: gpg --dearmor /tmp/mongodb.asc -o /usr/share/keyrings/mongodb-server-7.0.gpg
```

**Solution**: ✅ **FIXED** - The installer now uses multiple fallback methods for MongoDB installation.

## 🔄 Installation Methods (Automatic Fallback)

The installer now tries these methods in order:

### Method 1: Official MongoDB Repository
- Downloads MongoDB GPG key
- Tries multiple GPG command variations
- Adds official MongoDB repository
- Installs latest MongoDB version

### Method 2: Ubuntu Repositories
- Uses `apt-get install mongodb`
- Works with older MongoDB versions
- More reliable on some systems

### Method 3: Snap Package
- Uses `snap install mongodb`
- Alternative package manager
- Works when APT fails

## 🧪 Manual MongoDB Installation

If the installer still fails, install MongoDB manually:

### Option 1: Ubuntu Repository
```bash
sudo apt-get update
sudo apt-get install -y mongodb
sudo systemctl enable mongodb
sudo systemctl start mongodb
```

### Option 2: Official MongoDB (Manual)
```bash
# Import GPG key manually
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg

# Add repository
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# Install
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl enable mongod
sudo systemctl start mongod
```

### Option 3: Docker MongoDB
```bash
# Run MongoDB in Docker
docker run -d --name mongodb -p 27017:27017 -v mongodb_data:/data/db mongo:7.0

# Update backend .env file
echo "MONGO_URL=mongodb://localhost:27017/secret_poll" >> /opt/secret-poll/backend/.env
```

## 🔍 Verification Commands

### Check MongoDB Status
```bash
# Check service status
sudo systemctl status mongod
sudo systemctl status mongodb

# Check if MongoDB is listening
netstat -tulpn | grep :27017
ss -tulpn | grep :27017

# Test connection
mongo --eval "db.adminCommand('ping')"
```

### Check Application Connection
```bash
# Test API health
curl http://localhost:8001/api/health

# Check application logs
journalctl -u secret-poll -f

# Check backend logs specifically
tail -f /opt/secret-poll/backend.log
```

## ⚙️ Configuration Files

### Backend Configuration (.env)
```bash
# Check current configuration
cat /opt/secret-poll/backend/.env

# Should contain:
MONGO_URL=mongodb://localhost:27017/secret_poll
```

### Service Configuration
```bash
# Check systemd service
systemctl cat secret-poll

# Check if MongoDB is a dependency
grep -i mongo /etc/systemd/system/secret-poll.service
```

## 🚨 Common Issues & Solutions

### Issue: "Connection refused to localhost:27017"
```bash
# Check if MongoDB is running
sudo systemctl status mongod mongodb

# Start MongoDB if needed
sudo systemctl start mongod

# Check firewall
sudo ufw status
```

### Issue: "Authentication failed"
```bash
# Check MongoDB configuration
sudo cat /etc/mongod.conf

# Disable auth temporarily for testing
sudo sed -i 's/#security:/security:\n  authorization: disabled/' /etc/mongod.conf
sudo systemctl restart mongod
```

### Issue: "Cannot connect to MongoDB"
```bash
# Check MongoDB logs
sudo journalctl -u mongod -f
sudo journalctl -u mongodb -f

# Check disk space
df -h

# Check permissions
ls -la /var/lib/mongodb
```

## 🔄 Restart Sequence

If MongoDB issues persist, try this restart sequence:

```bash
# 1. Stop all services
sudo systemctl stop secret-poll
sudo systemctl stop mongod mongodb

# 2. Clear MongoDB lock files (if needed)
sudo rm -f /var/lib/mongodb/mongod.lock

# 3. Start MongoDB
sudo systemctl start mongod

# 4. Verify MongoDB is running
sudo systemctl status mongod

# 5. Start the application
sudo systemctl start secret-poll

# 6. Check everything is working
curl http://localhost:8001/api/health
```

## 📧 Getting Help

If MongoDB still won't install:

1. **Check logs**: `/var/log/secret-poll-install.log`
2. **System info**: Run `lsb_release -a` and `uname -a`
3. **Create GitHub issue**: Include error logs and system info
4. **Alternative**: Use Docker MongoDB instead

## ✅ Success Indicators

MongoDB is working correctly when:
- ✅ Service status shows "active (running)"
- ✅ Port 27017 is listening
- ✅ API health check returns `{"status":"healthy"}`
- ✅ Application can create rooms and polls

---

**The installer has been updated to handle all these scenarios automatically!** 🎉