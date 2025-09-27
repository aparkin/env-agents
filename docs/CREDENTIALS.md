# Credential Setup Guide

**⚠️ SECURITY NOTICE: Never commit actual API keys or credentials to version control!**

This guide shows how to securely configure credentials for env-agents services that require authentication.

## 🛡️ Security First!

env-agents uses a **secure credential management system** that keeps your API keys completely separate from the codebase:

- ✅ **Templates only** in version control (safe to commit)
- ✅ **Actual credentials** stored outside Git tracking in `credentials/` directory
- ✅ **Symlinks** for local development that Git ignores
- ✅ **Comprehensive .gitignore** protection

## 🔐 Quick Setup

1. **Copy the template files:**
   ```bash
   cp config/templates/credentials.yaml.template config/credentials.yaml
   cp config/templates/google-earth-engine-service-account.json.template credentials/your-gee-service-account.json
   ```

2. **Fill in your API keys** in the copied files (see service-specific instructions below)

3. **Verify security:** Your actual credential files should be ignored by Git:
   ```bash
   git status  # Should not show any credential files
   ```

## 📊 Services Overview

| Service | Type | Required | Get Credentials From |
|---------|------|----------|---------------------|
| **NASA_POWER** | API Key + Email | Yes | https://power.larc.nasa.gov/common/php/APIApplication.php |
| **US_EIA** | API Key | Yes | https://www.eia.gov/opendata/register.php |
| **EPA_AQS** | API Key + Email | Yes | https://aqs.epa.gov/aqsweb/documents/data_api.html#signup |
| **OpenAQ** | API Key | Yes | https://docs.openaq.org/docs/getting-started |
| **NOAA_CDO** | Token | Optional | https://www.ncdc.noaa.gov/cdo-web/token |
| **EARTH_ENGINE** | Service Account JSON | Yes | https://console.cloud.google.com/ |
| **GBIF** | None | No | Public API |
| **SoilGrids** | None | No | Public WCS |
| **USGS_NWIS** | None | No | Public API |
| **WQP** | None | No | Public API |
| **OSM_Overpass** | None | No | Public API |
| **SSURGO** | None | No | Public API |

## 📋 Service-Specific Setup

### 🛰️ NASA POWER (Weather/Solar Data)
**Required for:** Solar irradiance, temperature, precipitation, wind data
1. **Get API key:** Visit [NASA POWER API Registration](https://power.larc.nasa.gov/common/php/APIApplication.php)
2. **Fill out form:** Provide your name, email, and intended use
3. **Configure:** Add to `config/credentials.yaml`:
   ```yaml
   NASA_POWER:
     email: "your-registration-email@example.com"
     key: "your-nasa-power-api-key-here"
   ```

### ⚡ US EIA (Energy Data)
**Required for:** Energy production, consumption, and pricing data
1. **Get API key:** Visit [EIA API Registration](https://www.eia.gov/opendata/register.php)
2. **Create account:** Register with email and receive instant API key
3. **Configure:** Add to `config/credentials.yaml`:
   ```yaml
   US_EIA:
     api_key: "your-32-character-eia-api-key"
   ```

### 🌬️ EPA AQS (Air Quality Data)
**Required for:** EPA air quality monitoring station data
1. **Get API key:** Visit [EPA AQS API Registration](https://aqs.epa.gov/aqsweb/documents/data_api.html#signup)
2. **Request access:** Email aqs.data.requests@epa.gov with your information
3. **Configure:** Add to `config/credentials.yaml`:
   ```yaml
   EPA_AQS:
     email: "your-registration-email@example.com"
     key: "your-epa-aqs-username"  # This is your username, not a traditional API key
   ```

### 🌍 OpenAQ (Global Air Quality)
**Required for:** Real-time global air quality measurements
1. **Get API key:** Visit [OpenAQ API Documentation](https://docs.openaq.org/docs/getting-started)
2. **Register:** Create account at https://openaq.org/
3. **Configure:** Add to `config/credentials.yaml`:
   ```yaml
   OpenAQ:
     api_key: "your-openaq-api-key-here"
   ```

### 🛰️ Google Earth Engine (Satellite Imagery)
**Required for:** Satellite imagery, climate data, land cover
1. **Create Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing one
2. **Enable Earth Engine API:**
   - Go to APIs & Services > Enable APIs
   - Search for "Earth Engine API" and enable it
3. **Create Service Account:**
   - Go to IAM & Admin > Service Accounts
   - Create new service account
   - Grant "Earth Engine Resource Viewer" role
   - Generate and download JSON key file
4. **Configure:**
   - Save JSON file as `credentials/your-project-service-account.json`
   - Add to `config/credentials.yaml`:
   ```yaml
   EARTH_ENGINE:
     service_account: "your-service-account@your-project.iam.gserviceaccount.com"
     service_account_path: "../credentials/your-project-service-account.json"
     project_id: "your-gcp-project-id"
   ```

### 🌡️ NOAA CDO (Historical Weather)
**Required for:** Historical weather station data (optional service)
1. **Get token:** Visit [NOAA CDO Token Request](https://www.ncdc.noaa.gov/cdo-web/token)
2. **Request access:** Fill out form with your contact information
3. **Configure:** Add to `config/credentials.yaml`:
   ```yaml
   NOAA_CDO:
     token: "your-noaa-cdo-token-here"
   ```

## 📁 File Structure

```
env-agents/
├── config/
│   ├── templates/                          # Template files (safe to commit)
│   │   ├── credentials.yaml.template
│   │   └── google-earth-engine-service-account.json.template
│   ├── credentials.yaml                    # Your actual credentials (NEVER commit)
│   ├── your-project-service-account.json   # Your GEE key (NEVER commit)
│   ├── defaults.yaml                       # Default settings (safe to commit)
│   ├── services.yaml                       # Service config (safe to commit)
│   └── earth_engine.yaml                   # Earth Engine config (safe to commit)
└── credentials/                            # Private backup directory (NEVER commit)
    └── *.backup                           # Your credential backups
```

## 🛡️ Security Best Practices

### ✅ Do:
- Copy templates before filling in credentials
- Keep credential files in `.gitignore`
- Use environment variables for deployment
- Rotate API keys regularly
- Use service accounts with minimal permissions

### ❌ Don't:
- Commit credential files to Git
- Share API keys in chat/email
- Use production keys for development
- Hard-code credentials in source code
- Grant excessive permissions to service accounts

## 🔧 Environment Variables (Alternative)

Instead of credential files, you can use environment variables:

```bash
export NASA_POWER_API_KEY="your-key"
export US_EIA_API_KEY="your-key"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export NOAA_CDO_TOKEN="your-token"
export EPA_AQS_EMAIL="your-email"
export EPA_AQS_KEY="your-key"
```

env-agents will automatically detect these environment variables.

## 🚨 Troubleshooting

### "No credentials found" errors:
1. Verify credential file exists: `ls -la config/credentials.yaml`
2. Check file permissions: `chmod 600 config/credentials.yaml`
3. Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('config/credentials.yaml'))"`

### Git shows credential files:
1. Check `.gitignore`: `grep -n credentials .gitignore`
2. Remove from Git if accidentally added: `git rm --cached config/credentials.yaml`
3. Verify exclusion: `git status` should not show credential files

### Service authentication failures:
1. Verify API key is active in service portal
2. Check API quotas and rate limits
3. Ensure service account has correct permissions (for GEE)

## 📞 Support

- **File issues:** [GitHub Issues](https://github.com/aparkin/env-agents/issues)
- **Security concerns:** Report privately via email to maintainers
- **Service-specific help:** Refer to individual service documentation

---

**Remember:** Your credentials are valuable! Treat them like passwords and never share or commit them publicly.