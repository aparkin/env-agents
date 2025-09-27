# Local Development Setup

This guide explains how to set up env-agents for secure local development while keeping your credentials safe.

## 🛡️ Security Architecture

env-agents uses a **three-layer security system**:

1. **Templates in Git** - Safe credential templates that can be committed
2. **Private credentials directory** - Your actual API keys stored outside Git tracking
3. **Symlinks for development** - Local links that Git ignores but code can access

```
env-agents/
├── config/
│   ├── templates/                     # ✅ Safe to commit
│   │   ├── credentials.yaml.template
│   │   └── google-earth-engine-*.template
│   ├── credentials.yaml -> ../credentials/credentials.yaml.backup  # Symlink (ignored)
│   └── your-gee-key.json -> ../credentials/your-gee-key.json       # Symlink (ignored)
├── credentials/                       # 🚫 NEVER committed (in .gitignore)
│   ├── credentials.yaml.backup        # Your actual API keys
│   ├── ecognita-*.json               # Your actual service account
│   └── env_agents_credentials_backup/ # Legacy backup
└── .gitignore                         # Protects credentials/ directory
```

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)
```bash
# Run the automated setup script
python scripts/setup_development_credentials.py
```

### Option 2: Manual Setup
```bash
# 1. Copy templates
cp config/templates/credentials.yaml.template credentials/credentials.yaml
cp config/templates/google-earth-engine-service-account.json.template credentials/your-gee-service-account.json

# 2. Create symlinks
ln -sf ../credentials/credentials.yaml config/credentials.yaml
ln -sf ../credentials/your-gee-service-account.json config/your-gee-service-account.json

# 3. Edit credentials
edit credentials/credentials.yaml  # Add your API keys
```

## 📊 Credential Status Check

Run this to check your current credential setup:

```python
import yaml
import os

# Check if credentials load
with open('config/credentials.yaml') as f:
    creds = yaml.safe_load(f)

print(f"✅ Found credentials for {len(creds)} services")
for service, config in creds.items():
    if config:
        keys = list(config.keys())
        print(f"  - {service}: {keys}")
    else:
        print(f"  - {service}: (public service)")
```

## 🧪 Testing Your Setup

### Test Credential Loading
```bash
python -c "
import yaml
with open('config/credentials.yaml') as f:
    creds = yaml.safe_load(f)
print('✅ Credentials loaded successfully!')
print(f'Found {len(creds)} services configured')
"
```

### Test Services
```bash
# Quick test of all services
python run_tests.py

# Test specific service
python -c "
from env_agents.adapters import CANONICAL_SERVICES
adapter = CANONICAL_SERVICES['NASA_POWER']()
caps = adapter.capabilities()
print(f'✅ NASA POWER: {len(caps[\"variables\"])} variables available')
"
```

## 🔧 Troubleshooting

### "No credentials found" errors
```bash
# Check if symlink exists and points to correct location
ls -la config/credentials.yaml

# Check if backup exists
ls -la credentials/credentials.yaml.backup

# Re-run setup if needed
python scripts/setup_development_credentials.py
```

### Git shows credential files
```bash
# Check .gitignore is working
git status --ignored

# If credentials appear in git status:
git rm --cached config/credentials.yaml  # Remove from Git if accidentally added
git status  # Should not show credential files now
```

### Service-specific auth failures
1. **NASA POWER**: Check email and key format
2. **EPA AQS**: Key is actually your username, not a traditional API key
3. **Google Earth Engine**: Ensure JSON file has correct service account permissions
4. **OpenAQ**: Check API key is active
5. **US EIA**: Verify API key is exactly 32 characters

## 🌐 Environment Variables (Alternative)

Instead of files, you can use environment variables:

```bash
# Set environment variables
export NASA_POWER_EMAIL="your-email@example.com"
export NASA_POWER_API_KEY="your-key"
export US_EIA_API_KEY="your-eia-key"
export EPA_AQS_EMAIL="your-email@example.com"
export EPA_AQS_KEY="your-username"
export OPENAQ_API_KEY="your-openaq-key"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

env-agents will automatically detect and use these environment variables.

## 📚 Related Documentation

- [CREDENTIALS.md](CREDENTIALS.md) - Where to get API keys for each service
- [EXTENDING_SERVICES.md](EXTENDING_SERVICES.md) - Adding new services
- [README.md](../README.md) - Project overview and quick start

## 💡 Pro Tips

1. **Keep backups**: Your `credentials/` directory contains valuable API keys
2. **Use environment variables** for production deployments
3. **Test regularly**: Run `python run_tests.py` to verify all services work
4. **Check quotas**: Most APIs have usage limits - monitor your usage
5. **Rotate keys**: Periodically refresh API keys for better security

---

**✅ With this setup, you can:**
- Develop locally with full API access
- Keep credentials completely secure (never in Git)
- Share the repository safely (no credential exposure)
- Onboard new developers easily with templates