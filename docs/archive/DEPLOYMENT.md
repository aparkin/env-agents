# Deployment Guide

**env-agents**: Environmental Data Retrieval Framework  
**Version**: 1.0.0-beta

Complete setup and configuration guide for deploying env-agents in development and production environments.

## 🚀 **Quick Setup**

### Prerequisites
- Python 3.9+
- pip or conda
- Git

### Installation
```bash
# Clone repository
git clone <repository-url>
cd env-agents

# Install in development mode
pip install -e .

# Install dependencies
pip install pandas>=2.0 pyarrow>=15 requests>=2.32 pydantic>=2.0 shapely>=2.0

# Optional: Earth Engine API
pip install earthengine-api
```

## 🔑 **Credentials Configuration**

### 1. Copy Template
```bash
cp config/credentials.yaml.template config/credentials.yaml
```

### 2. Add API Keys
Edit `config/credentials.yaml`:

```yaml
# Government APIs
OpenAQ:
  api_key: "your_openaq_api_key_here"

EPA_AQS:
  email: "your_email@example.com"
  key: "your_epa_aqs_key"

# Optional: Additional services
EIA:
  api_key: "your_eia_api_key"

GBIF:
  username: "your_username"
  password: "your_password"
```

### 3. Earth Engine Authentication

#### Option A: Service Account (Production)
```bash
# Place service account JSON file in credentials directory
cp your-service-account.json env_agents/credentials/
```

#### Option B: Interactive Authentication (Development)  
```bash
# Authenticate with Google account
python -c "import ee; ee.Authenticate(); ee.Initialize()"
```

## ⚙️ **Service Configuration**

### Default Configuration
The package includes sensible defaults in `config/services.yaml`:

```yaml
USGS_NWIS:
  base_url: "https://waterservices.usgs.gov/nwis/iv"
  timeout: 30
  supported_parameters: ["00060", "00065", "00010"]

OpenAQ:
  base_url: "https://api.openaq.org/v3"
  rate_limit:
    requests_per_minute: 300
  default_radius_m: 2000

NASA_POWER:
  base_url: "https://power.larc.nasa.gov/api/temporal/daily/point"
  timeout: 30
  default_community: "RE"
```

### Custom Configuration
Override defaults by creating `config/services.local.yaml`:

```yaml
# Custom rate limits
OpenAQ:
  rate_limit:
    requests_per_minute: 100  # More conservative

# Custom endpoints  
USGS_NWIS:
  base_url: "https://waterservices.usgs.gov/nwis/dv"  # Daily values
```

## 🧪 **Verification**

### Test Basic Functionality
```python
from env_agents import UnifiedEnvRouter

# Initialize router
router = UnifiedEnvRouter()

# Check service discovery
services = router.list_adapters()
print(f"Discovered {len(services)} services")

# Test metadata retrieval
capabilities = router.capabilities()
print(f"Retrieved metadata for {len(capabilities)} services")
```

### Test Data Retrieval
```python
from env_agents.core.models import RequestSpec, Geometry

# Test government API
spec = RequestSpec(
    geometry=Geometry(type="point", coordinates=[-121.5, 38.5]),
    variables=["00060"],
    time_range=("2024-01-01", "2024-01-02")
)

try:
    data = router.fetch("USGS_NWIS", spec)
    print(f"✅ USGS_NWIS: {len(data)} rows retrieved")
except Exception as e:
    print(f"❌ USGS_NWIS: {e}")
```

### Verify Credentials
```bash
# Run built-in credential verification
python verify_credentials.py
```

## 🐳 **Docker Deployment**

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy package
COPY . .

# Install package
RUN pip install -e .

# Install additional dependencies
RUN pip install earthengine-api

# Set environment
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "env_agents.cli.ea", "serve"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  env-agents:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config
      - ./data:/app/data
    environment:
      - ENV_AGENTS_CONFIG_PATH=/app/config
    restart: unless-stopped
```

## ☁️ **Cloud Deployment**

### AWS Lambda
```python
# lambda_handler.py
import json
from env_agents import UnifiedEnvRouter

def lambda_handler(event, context):
    router = UnifiedEnvRouter()
    
    # Parse request
    service_id = event['service_id']
    request_spec = event['request_spec']
    
    # Fetch data
    try:
        data = router.fetch(service_id, request_spec)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'data': data.to_dict('records'),
                'count': len(data)
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### Google Cloud Functions
```python
# main.py
import functions_framework
from env_agents import UnifiedEnvRouter

@functions_framework.http
def env_data(request):
    router = UnifiedEnvRouter()
    
    # Handle request
    data = request.get_json()
    service_id = data['service_id']
    spec = data['request_spec']
    
    # Fetch and return data
    try:
        result = router.fetch(service_id, spec)
        return {'data': result.to_dict('records')}
    except Exception as e:
        return {'error': str(e)}, 500
```

## 🔍 **Monitoring & Logging**

### Enable Logging
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set specific logger levels
logging.getLogger('env_agents.core.router').setLevel(logging.DEBUG)
logging.getLogger('env_agents.adapters').setLevel(logging.INFO)
```

### Health Monitoring
```python
from env_agents.core.service_health import ServiceHealthTracker

# Monitor service health
health_tracker = ServiceHealthTracker()
health_status = health_tracker.get_all_service_health()

for service_id, status in health_status.items():
    print(f"{service_id}: {status.reliability_score:.2f}")
```

## 🛠️ **Troubleshooting**

### Common Issues

#### 1. Import Errors
```bash
# Reinstall in development mode
pip install -e .

# Check Python path
python -c "import env_agents; print(env_agents.__file__)"
```

#### 2. Credential Issues
```bash
# Verify credential file exists
ls -la config/credentials.yaml

# Test specific service credentials
python -c "
from env_agents.core.config import get_config
config = get_config()
creds = config.get_service_credentials('OpenAQ')
print(creds)
"
```

#### 3. Earth Engine Authentication
```bash
# Re-authenticate
python -c "import ee; ee.Authenticate()"

# Check service account
python verify_credentials.py
```

#### 4. Service Timeouts
```yaml
# Increase timeouts in config/services.yaml
USGS_NWIS:
  timeout: 60  # Increase from 30
```

### Debug Mode
```python
from env_agents import UnifiedEnvRouter

# Enable debug logging
router = UnifiedEnvRouter()
router.set_debug_mode(True)

# This will print detailed request/response information
```

## 📈 **Performance Optimization**

### Enable Caching
```python
from env_agents.core.cache import enable_cache

# Enable response caching
enable_cache(ttl_hours=24)
```

### Concurrent Requests
```python
import asyncio
from env_agents.core.async_router import AsyncUnifiedRouter

async def fetch_multiple():
    router = AsyncUnifiedRouter()
    
    # Batch requests
    requests = [
        ("USGS_NWIS", spec1),
        ("OpenAQ", spec2),
        ("NASA_POWER", spec3)
    ]
    
    results = await router.batch_fetch(requests)
    return results
```

## 🔒 **Security Considerations**

### Credential Security
- Never commit credentials to version control
- Use environment variables in production
- Rotate API keys regularly
- Use service accounts with minimal permissions

### Network Security
- Use HTTPS for all API communications
- Implement rate limiting
- Monitor API usage for anomalies
- Use VPN for sensitive deployments

## 📊 **Production Metrics**

### Key Performance Indicators
- **Service Availability**: >99.5% uptime
- **Response Time**: <3s median
- **Success Rate**: >95% for all services
- **Error Rate**: <5% total requests

### Monitoring Dashboard
```python
from env_agents.core.metrics import MetricsDashboard

dashboard = MetricsDashboard()
dashboard.start(port=9090)  # Prometheus metrics endpoint
```

## 📞 **Support**

### Log Collection
```bash
# Collect debug information
python -c "
from env_agents.core.diagnostics import collect_debug_info
collect_debug_info('debug_report.json')
"
```

### Health Check Endpoint
```python
# Add to your application
@app.route('/health')
def health_check():
    router = UnifiedEnvRouter()
    health = router.check_health()
    return health, 200 if health['status'] == 'healthy' else 503
```

For additional support, see:
- [API Documentation](API.md)
- [Extension Guide](EXTENDING.md)  
- [GitHub Issues](https://github.com/your-org/env-agents/issues)