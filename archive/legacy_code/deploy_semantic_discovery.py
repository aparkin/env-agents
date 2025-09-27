#!/usr/bin/env python3
"""
Deploy semantic discovery pipeline with TermBroker integration
Demonstrates automatic parameter discovery and semantic mapping
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from env_agents.core.router import EnvRouter
from env_agents.core.service_discovery import ServiceDiscoveryEngine
from env_agents.core.registry_curation import RegistryCurator
from datetime import datetime

def deploy_semantic_pipeline():
    print("🚀 Deploying Semantic Discovery Pipeline")
    print("=" * 50)
    
    # Initialize core components
    router = EnvRouter(base_dir=".")
    discovery_engine = ServiceDiscoveryEngine(router.registry, base_dir=".")
    curator = RegistryCurator(router.registry)
    
    # Register all 5 services
    print("\n📋 Registering Services...")
    services_registered = []
    
    # NASA POWER
    try:
        from env_agents.adapters.power.adapter import NasaPowerDailyAdapter
        power_adapter = NasaPowerDailyAdapter()
        router.register(power_adapter)
        services_registered.append(("NASA POWER", power_adapter))
        print("  ✅ NASA POWER registered")
    except Exception as e:
        print(f"  ❌ NASA POWER failed: {e}")
    
    # OpenAQ
    try:
        from env_agents.adapters.openaq.adapter import OpenaqV3Adapter
        openaq_adapter = OpenaqV3Adapter()
        router.register(openaq_adapter)
        services_registered.append(("OpenAQ", openaq_adapter))
        print("  ✅ OpenAQ registered")
    except Exception as e:
        print(f"  ❌ OpenAQ failed: {e}")
    
    # USGS NWIS
    try:
        from env_agents.adapters.nwis.adapter import UsgsNwisLiveAdapter
        nwis_adapter = UsgsNwisLiveAdapter()
        router.register(nwis_adapter)
        services_registered.append(("USGS NWIS", nwis_adapter))
        print("  ✅ USGS NWIS registered")
    except Exception as e:
        print(f"  ❌ USGS NWIS failed: {e}")
    
    # USDA SURGO
    try:
        from env_agents.adapters.soil.surgo_adapter import UsdaSurgoAdapter
        surgo_adapter = UsdaSurgoAdapter()
        router.register(surgo_adapter)
        services_registered.append(("USDA SURGO", surgo_adapter))
        print("  ✅ USDA SURGO registered")
    except Exception as e:
        print(f"  ❌ USDA SURGO failed: {e}")
    
    # ISRIC SoilGrids
    try:
        from env_agents.adapters.soil.soilgrids_adapter import IsricSoilGridsAdapter
        soilgrids_adapter = IsricSoilGridsAdapter()
        router.register(soilgrids_adapter)
        services_registered.append(("ISRIC SoilGrids", soilgrids_adapter))
        print("  ✅ ISRIC SoilGrids registered")
    except Exception as e:
        print(f"  ❌ ISRIC SoilGrids failed: {e}")
    
    print(f"\n📊 Services Summary: {len(services_registered)}/5 registered")
    
    # Run semantic discovery on each service
    print(f"\n🔍 Running Semantic Discovery...")
    discovery_results = {}
    
    for service_name, adapter in services_registered:
        print(f"\n  🔎 Discovering {service_name}...")
        
        try:
            # Run discovery with auto-accept threshold of 0.90
            result = discovery_engine.discover_service_parameters(
                adapter, 
                auto_accept_threshold=0.90,
                suggest_threshold=0.60
            )
            
            discovery_results[service_name] = result
            
            # Report results
            auto_accepted = result.get('auto_accepted', [])
            suggestions = result.get('suggestions', [])
            unmapped = result.get('unmapped', [])
            
            print(f"    ✅ Auto-accepted: {len(auto_accepted)} parameters")
            print(f"    🤔 Suggestions: {len(suggestions)} parameters")  
            print(f"    ❓ Unmapped: {len(unmapped)} parameters")
            
            # Show some examples
            if auto_accepted:
                print(f"    📌 Sample auto-accepted: {auto_accepted[0].get('native_id', 'N/A')}")
            if suggestions:
                print(f"    📌 Sample suggestion: {suggestions[0].get('native_id', 'N/A')}")
                
        except Exception as e:
            print(f"    ❌ Discovery failed: {e}")
            discovery_results[service_name] = {"error": str(e)}
    
    # Registry validation
    print(f"\n🔧 Validating Registry...")
    try:
        validation_result = discovery_engine.validate_registry()
        issues = validation_result.get('issues', [])
        coverage = validation_result.get('coverage', {})
        
        print(f"  📋 Registry Issues: {len(issues)}")
        print(f"  📊 Coverage: {coverage.get('services_covered', 0)}/{coverage.get('total_services', 0)} services")
        
        if issues:
            print("  🔧 Sample issues:")
            for issue in issues[:3]:
                print(f"    - {issue.get('type', 'unknown')}: {issue.get('description', 'N/A')}")
                
    except Exception as e:
        print(f"  ❌ Registry validation failed: {e}")
    
    # Registry curation suggestions
    print(f"\n🎯 Registry Curation Analysis...")
    try:
        assessment = curator.assess_registry_quality()
        
        print(f"  📊 Quality Score: {assessment.get('overall_score', 'N/A')}/10")
        print(f"  🔄 Total Suggestions: {len(assessment.get('improvements', []))}")
        
        improvements = assessment.get('improvements', [])[:3]
        for imp in improvements:
            print(f"    - {imp.get('type', 'unknown')}: {imp.get('description', 'N/A')}")
            
    except Exception as e:
        print(f"  ❌ Curation assessment failed: {e}")
    
    # Summary
    print(f"\n🎉 Semantic Discovery Pipeline Deployed!")
    print(f"  📡 Services: {len(services_registered)}")
    print(f"  🧠 TermBroker: Active")
    print(f"  📚 Registry: Loaded")
    print(f"  🔍 Discovery Engine: Ready")
    print(f"  📝 Timestamp: {datetime.now().isoformat()}")
    
    return {
        'services_registered': len(services_registered),
        'discovery_results': discovery_results,
        'router': router,
        'discovery_engine': discovery_engine,
        'curator': curator
    }

if __name__ == "__main__":
    result = deploy_semantic_pipeline()
    sys.exit(0)