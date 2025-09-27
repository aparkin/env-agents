#!/usr/bin/env python3
"""
Credential verification script for env-agents package.
Run this to verify all required credentials are properly bundled.
"""

import sys
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("🔐 VERIFYING ENV-AGENTS CREDENTIALS FOR ECOGNITA DEPLOYMENT")
    print("=" * 60)
    
    try:
        from env_agents.credentials import verify_credentials, get_earth_engine_credentials
        
        # Check all credentials
        status = verify_credentials()
        
        print(f"📊 CREDENTIAL STATUS:")
        for service, info in status.items():
            if info['available']:
                print(f"   ✅ {service.upper()}: Available")
                if 'service_account' in info:
                    print(f"      Account: {info['service_account']}")
                    print(f"      Key file: {info['key_file']}")
            else:
                print(f"   ❌ {service.upper()}: {info['error']}")
        
        # Test Earth Engine credentials specifically
        print(f"\n🌍 EARTH ENGINE CREDENTIAL TEST:")
        try:
            service_account, key_file = get_earth_engine_credentials()
            key_path = Path(key_file)
            
            print(f"   📧 Service Account: {service_account}")
            print(f"   🔑 Key File: {key_file}")
            print(f"   📁 File Exists: {'✅ Yes' if key_path.exists() else '❌ No'}")
            print(f"   📏 File Size: {key_path.stat().st_size} bytes" if key_path.exists() else "   📏 File Size: N/A")
            
            if key_path.exists():
                # Test if it's valid JSON
                import json
                with open(key_path) as f:
                    creds = json.load(f)
                    print(f"   🔍 Valid JSON: ✅ Yes")
                    print(f"   🏷️  Project ID: {creds.get('project_id', 'Not found')}")
                    print(f"   📧 Client Email: {creds.get('client_email', 'Not found')}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Package deployment readiness
        print(f"\n📦 ECOGNITA DEPLOYMENT READINESS:")
        
        all_available = all(info['available'] for info in status.values())
        if all_available:
            print(f"   🚀 READY: All credentials bundled and available")
            print(f"   📋 Package can be deployed to ECOGNITA without external dependencies")
            print(f"   ✅ Self-contained credential management")
        else:
            print(f"   ⚠️  NOT READY: Missing credentials detected")
            missing = [service for service, info in status.items() if not info['available']]
            print(f"   📝 Missing: {', '.join(missing)}")
        
        return 0 if all_available else 1
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("🔧 Make sure you're running from the env-agents directory")
        return 1
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    print(f"\n{'🎉 VERIFICATION COMPLETE' if exit_code == 0 else '⚠️ VERIFICATION FAILED'}")
    sys.exit(exit_code)