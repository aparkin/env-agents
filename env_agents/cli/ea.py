from __future__ import annotations
import argparse, json, os
from ..core.router import EnvRouter

def main():
    parser = argparse.ArgumentParser(prog="ea", description="env-agents CLI")
    parser.add_argument("--base-dir", default=os.path.dirname(os.path.dirname(__file__)))
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("list", help="List registered adapters")
    sub.add_parser("caps", help="Print capabilities JSON")
    args = parser.parse_args()
    router = EnvRouter(args.base_dir)

    # Register stubs
    from ..adapters.aqs import EpaAqsV3Adapter
    from ..adapters.openaq import OpenaqV3Adapter
    from ..adapters.nwis import UsgsNwisAdapter
    from ..adapters.wqp import UsgsWqpAdapter
    from ..adapters.power import NasaPowerAdapter
    from ..adapters.appeears import NasaAppeearsAdapter
    from ..adapters.firms import NasaFirmsAdapter
    from ..adapters.overpass import OsmOverpassAdapter
    from ..adapters.cropscape import UsdaCropscapeAdapter
    from ..adapters.eia_camd_tri import UsEnergyEmissionsAdapter
    from ..adapters.gbif import GbifAdapter

    for cls in [EpaAqsV3Adapter, OpenaqV3Adapter, UsgsNwisAdapter, UsgsWqpAdapter,
                NasaPowerAdapter, NasaAppeearsAdapter, NasaFirmsAdapter,
                OsmOverpassAdapter, UsdaCropscapeAdapter, UsEnergyEmissionsAdapter, GbifAdapter]:
        router.register(cls())

    if args.cmd == "list":
        print("\n".join(router.list_adapters()))
    elif args.cmd == "caps":
        print(json.dumps(router.capabilities(), indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
