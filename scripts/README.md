# Environmental Services Framework - Operational Scripts

This directory contains operational and maintenance scripts for the env-agents framework.

## 🔧 Available Scripts

### `refresh_metadata.py`
**Purpose**: Updates and maintains Earth Engine catalog and metadata system

**Usage**:
```bash
python scripts/refresh_metadata.py
```

**Function**:
- Downloads latest Earth Engine catalog from Google
- Updates asset metadata and discovery information
- Refreshes local catalog cache (997 assets)
- Essential for keeping Earth Engine service current

### `setup_credentials.py` 
**Purpose**: Interactive setup for service credentials and authentication

**Usage**:
```bash
python scripts/setup_credentials.py
```

**Function**:
- Guides through credential setup for all services
- Creates `config/credentials.yaml` with proper structure
- Sets up Earth Engine service account authentication
- Configures API keys for government and research services

## 🚀 Operational Usage

### Initial Setup
```bash
# 1. Set up credentials for services that require authentication
python scripts/setup_credentials.py

# 2. Refresh Earth Engine catalog (optional - already populated)
python scripts/refresh_metadata.py
```

### Maintenance Tasks
```bash
# Update Earth Engine catalog (recommended monthly)
python scripts/refresh_metadata.py

# Reconfigure credentials when adding new API keys
python scripts/setup_credentials.py
```

## 📋 Service Authentication Requirements

### Required Credentials (for full functionality):
- **EPA AQS**: Email address + API key (free registration)
- **Earth Engine**: Google Cloud service account (requires GCP project)

### Optional Credentials (services work without):
- **NASA POWER**: No authentication required
- **USGS NWIS**: No authentication required  
- **SSURGO**: No authentication required
- **SoilGrids**: No authentication required
- **GBIF**: No authentication required
- **WQP**: No authentication required
- **OpenAQ**: No authentication required
- **Overpass**: No authentication required

## 🔍 Metadata System

The refresh_metadata.py script maintains:
- `data/metadata/earth_engine/catalog.json`: Full Earth Engine catalog (734K+ lines)
- `data/metadata/earth_engine/asset_metadata.json`: Rich metadata for assets  
- `data/metadata/earth_engine/asset_discovery.json`: Discovery information
- `data/metadata/unified/all_services.json`: Cross-service metadata

This metadata system enables:
- Automatic Earth Engine asset discovery
- Rich semantic metadata for AI agents
- Service capability indexing
- Cross-service variable mapping

These scripts ensure the environmental services framework remains current and properly configured for production use.