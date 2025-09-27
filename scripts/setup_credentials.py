#!/usr/bin/env python3
"""
Interactive Credentials Setup for env-agents

Guides users through setting up API keys and service accounts
for all environmental services and Earth Engine.

Usage:
    python scripts/setup_credentials.py
"""

import sys
from pathlib import Path
import yaml
import json
import getpass
from typing import Dict, Any

# Add env_agents to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core.config import get_config


def prompt_for_credentials() -> Dict[str, Any]:
    """Interactive credential collection"""
    
    print("🌍 env-agents Credentials Setup")
    print("=" * 40)
    print("This will help you configure API keys and service accounts for all services.")
    print("You can skip any service by pressing Enter without typing a value.")
    print()
    
    credentials = {}
    
    # NASA POWER / NOAA
    print("📡 NASA POWER (via NOAA API)")
    print("   Get your API key from: https://www.ncdc.noaa.gov/cdo-web/token")
    email = input("   Email address: ").strip()
    key = input("   API Key: ").strip()
    if email and key:
        credentials['NASA_POWER'] = {'email': email, 'key': key}
        print("   ✅ NASA POWER configured")
    else:
        print("   ⏭️  Skipped NASA POWER")
    print()
    
    # EIA
    print("⚡ US Energy Information Administration (EIA)")
    print("   Get your API key from: https://www.eia.gov/opendata/register.php")
    api_key = input("   API Key: ").strip()
    if api_key:
        credentials['US_EIA'] = {'api_key': api_key}
        print("   ✅ EIA configured")
    else:
        print("   ⏭️  Skipped EIA")
    print()
    
    # EPA AQS
    print("🏭 EPA Air Quality System (AQS)")
    print("   Register at: https://aqs.epa.gov/aqsweb/documents/data_api.html")
    email = input("   Email address: ").strip()
    key = input("   API Key: ").strip()
    if email and key:
        credentials['EPA_AQS'] = {'email': email, 'key': key}
        print("   ✅ EPA AQS configured")
    else:
        print("   ⏭️  Skipped EPA AQS")
    print()
    
    # OpenAQ
    print("🌬️  OpenAQ")
    print("   Get your API key from: https://docs.openaq.org/")
    api_key = input("   API Key: ").strip()
    if api_key:
        credentials['OpenAQ'] = {'api_key': api_key}
        print("   ✅ OpenAQ configured")
    else:
        print("   ⏭️  Skipped OpenAQ")
    print()
    
    # Earth Engine
    print("🌍 Google Earth Engine")
    print("   You need a service account with Earth Engine access.")
    print("   See: https://developers.google.com/earth-engine/guides/service_account")
    
    setup_gee = input("   Configure Earth Engine? (y/N): ").strip().lower()
    if setup_gee == 'y':
        project_id = input("   GEE Project ID: ").strip()
        service_account = input("   Service Account Email: ").strip()
        
        print("   Place your service account JSON file at: data/auth/gee_service_account.json")
        
        if project_id and service_account:
            credentials['EARTH_ENGINE'] = {
                'project_id': project_id,
                'service_account': service_account,
                'service_account_path': 'data/auth/gee_service_account.json'
            }
            print("   ✅ Earth Engine configured")
        else:
            print("   ⚠️  Incomplete Earth Engine setup")
    else:
        print("   ⏭️  Skipped Earth Engine")
    print()
    
    return credentials


def save_credentials(config_manager, credentials: Dict[str, Any]):
    """Save credentials to config file"""
    try:
        config_manager.save_credentials(credentials)
        print(f"✅ Credentials saved to: {config_manager.config_dir / 'credentials.yaml'}")
        
        # Create .gitignore entry
        gitignore_path = config_manager.base_dir / ".gitignore"
        gitignore_content = "\n# env-agents credentials\nconfig/credentials.yaml\ndata/auth/\n"
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                existing = f.read()
            if 'credentials.yaml' not in existing:
                with open(gitignore_path, 'a') as f:
                    f.write(gitignore_content)
                print("✅ Updated .gitignore")
        else:
            with open(gitignore_path, 'w') as f:
                f.write(gitignore_content)
            print("✅ Created .gitignore")
            
    except Exception as e:
        print(f"❌ Failed to save credentials: {e}")
        return False
    
    return True


def validate_setup(config_manager):
    """Validate the credential setup"""
    print("\n🔍 Validating Configuration...")
    
    issues = config_manager.validate_configuration()
    
    if not any(issues.values()):
        print("✅ All credentials configured correctly!")
        return True
    
    print("⚠️  Configuration Issues Found:")
    
    if issues['missing_credentials']:
        print(f"   Missing credentials for: {', '.join(issues['missing_credentials'])}")
    
    if issues['missing_files']:
        print(f"   Missing files: {', '.join(issues['missing_files'])}")
    
    return False


def show_next_steps():
    """Show next steps after setup"""
    print("\n🚀 Next Steps:")
    print("=" * 20)
    print("1. Test your configuration:")
    print("   python scripts/validate_config.py")
    print()
    print("2. Refresh metadata:")
    print("   python scripts/refresh_metadata.py")
    print()
    print("3. Test the framework:")
    print("   python -c \"from env_agents.core.config import get_config; print('✅ Configuration loaded')\"")
    print()
    print("4. Run the interactive testing notebook:")
    print("   jupyter notebook Interactive_Testing_Clean.ipynb")
    print()


def main():
    print("Starting env-agents credentials setup...")
    
    # Initialize config manager
    config = get_config()
    
    # Check if credentials already exist
    creds_file = config.config_dir / "credentials.yaml"
    if creds_file.exists():
        overwrite = input(f"Credentials file already exists at {creds_file}. Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    # Collect credentials
    credentials = prompt_for_credentials()
    
    if not credentials:
        print("No credentials configured. Exiting.")
        return
    
    # Save credentials
    if save_credentials(config, credentials):
        # Validate setup
        validate_setup(config)
        
        # Show next steps
        show_next_steps()
    
    print("\n✅ Credentials setup complete!")


if __name__ == "__main__":
    main()