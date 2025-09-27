# Proposed env-agents Configuration & Data Structure

```
env-agents/
├── env_agents/
│   ├── core/
│   │   ├── config.py           # Configuration management system
│   │   ├── metadata_manager.py # Metadata refresh and caching
│   │   └── ...
│   ├── adapters/
│   │   ├── earth_engine/
│   │   │   ├── gee_adapter.py   # Earth Engine unified adapter
│   │   │   └── gee_auth.py      # GEE authentication helpers
│   │   └── ...
│   └── ...
├── config/
│   ├── credentials.yaml         # All service credentials (git-ignored)
│   ├── services.yaml           # Service-specific parameters
│   ├── earth_engine.yaml      # GEE-specific configuration
│   └── defaults.yaml          # Default settings
├── data/
│   ├── metadata/
│   │   ├── earth_engine/
│   │   │   ├── catalog.json         # GEE asset catalog (997 assets)
│   │   │   ├── asset_metadata.json  # Rich scraped metadata
│   │   │   └── asset_discovery.json # Processed discovery info
│   │   ├── services/
│   │   │   ├── nasa_power_params.json
│   │   │   ├── epa_aqs_parameters.json
│   │   │   └── ...
│   │   └── unified/
│   │       ├── all_services.json    # Combined service catalog
│   │       └── service_metadata.json # Unified metadata
│   ├── cache/
│   │   ├── earth_engine/
│   │   ├── nasa_power/
│   │   ├── epa_aqs/
│   │   └── ...
│   └── auth/
│       ├── gee_service_account.json  # GEE service account key
│       └── .gitkeep
├── scripts/
│   ├── refresh_metadata.py     # Update all metadata from sources
│   ├── setup_credentials.py    # Interactive credential setup
│   └── validate_config.py      # Configuration validation
└── ...
```

## Key Design Principles

1. **📋 Centralized Configuration**: All credentials, parameters in `config/`
2. **🗄️ Organized Data Storage**: Separate metadata, cache, auth in `data/`
3. **🔄 Refresh Capabilities**: Scripts and methods to update external data
4. **🔒 Security**: Credentials in git-ignored files with template structure
5. **🎯 Service Discovery**: Unified catalog combining env-agents + GEE assets
6. **📝 Documentation**: Clear naming and structure for maintainability

## Configuration Layers

1. **credentials.yaml**: API keys, tokens, service accounts
2. **services.yaml**: Service-specific parameters, rate limits, endpoints
3. **earth_engine.yaml**: GEE asset lists, authentication, default parameters
4. **defaults.yaml**: Framework-wide defaults and fallbacks