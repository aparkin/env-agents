from env_agents.core.router import EnvRouter
from env_agents.adapters.aqs import EpaAqsV3Adapter
from env_agents.core.models import Geometry, RequestSpec

router = EnvRouter(base_dir=".")
router.register(EpaAqsV3Adapter())

spec = RequestSpec(geometry=Geometry(type="point", coordinates=[-122.27, 37.87]))
df = router.fetch("EPA_AQS_v3", spec)
print(df.head())
print(df.attrs.get("schema"))
