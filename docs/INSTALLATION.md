# Installation Guide

**Getting env-agents up and running on your system**

---

## Prerequisites

- **Python 3.8+** (3.10+ recommended)
- **pip** package manager
- **git** (for installing from source)

---

## Installation Methods

### Method 1: Install from Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/aparkin/env-agents.git
cd env-agents

# Install in development mode
pip install -e .
```

**Why development mode (`-e`)?**
- Changes to code take effect immediately
- Easier for testing and customization
- Recommended for research and development use

### Method 2: Install from PyPI (Coming Soon)

```bash
# When available on PyPI
pip install env-agents
```

---

## Verify Installation

```bash
# Test import
python -c "from env_agents.core.models import RequestSpec; print('✓ Installation successful')"

# Run smoke test
python examples/quick_start.py
```

**Expected output:**
```
✓ Installation successful
Fetching NASA POWER data...
✓ Retrieved 365 observations
```

---

## Dependencies

### Core Dependencies (Auto-installed)

```
pandas>=2.0
pyarrow>=15
requests>=2.32
pydantic>=2.0
shapely>=2.0
```

### Optional Dependencies

#### Earth Engine (Satellite Data)
```bash
pip install earthengine-api
```

**Setup:**
1. Create a Google Earth Engine account at https://earthengine.google.com
2. Authenticate: `earthengine authenticate`
3. Or use service account (see [Credentials Guide](CREDENTIALS.md))

#### Jupyter Notebooks
```bash
pip install jupyter ipykernel matplotlib
```

#### Development Tools
```bash
pip install pytest black ruff mypy
```

---

## Platform-Specific Notes

### macOS

```bash
# If you encounter SSL errors
pip install --upgrade certifi

# For M1/M2 Macs with pandas issues
conda install pandas pyarrow -c conda-forge
```

### Linux

```bash
# Ubuntu/Debian: Install build tools if needed
sudo apt-get install python3-dev build-essential

# For spatial operations
sudo apt-get install libgeos-dev
```

### Windows

```bash
# Use Anaconda/Miniconda for easier dependency management
conda create -n env-agents python=3.10
conda activate env-agents
pip install -e .
```

---

## Configuration

### 1. Create Config Directory

```bash
mkdir -p config
```

### 2. Add Service Credentials (Optional)

Some services require API keys. See [Credentials Guide](CREDENTIALS.md) for details.

**Services requiring credentials:**
- Earth Engine (Google account or service account)
- EPA AQS (email for API key)

**Services with no authentication:**
- NASA POWER, GBIF, OpenAQ, USGS NWIS, WQP, SSURGO, OSM Overpass, SoilGrids

---

## Quick Test

Test a service that requires no authentication:

```python
from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.nasa_power import NASAPowerAdapter

# Create adapter
adapter = NASAPowerAdapter()

# Define request (San Francisco, June 2021)
spec = RequestSpec(
    geometry=Geometry(
        type="point",
        coordinates=[-122.4, 37.8]
    ),
    time_range=("2021-06-01", "2021-06-30")
)

# Fetch data
data = adapter.fetch(spec)
print(f"✓ Retrieved {len(data)} observations")
print(data.head())
```

**Expected:**
```
✓ Retrieved 180 observations
   observation_id  dataset  ...  value  unit
0  nasa_power_... NASA_POWER ... 18.5  degC
```

---

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'env_agents'`

**Solution:**
```bash
# Make sure you're in the env-agents directory
cd /path/to/env-agents
pip install -e .
```

### Dependency Conflicts

**Problem:** Version conflicts with pandas/numpy

**Solution:**
```bash
# Create a fresh virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

### Earth Engine Authentication

**Problem:** `EE initialization failed`

**Solution:** See [Credentials Guide - Earth Engine](CREDENTIALS.md#earth-engine) for detailed setup.

---

## Next Steps

✅ **Installation complete!**

Continue to:
- **[Quick Start Guide](QUICK_START.md)** - Your first query in 5 minutes
- **[Services Guide](SERVICES.md)** - Explore available data sources
- **[API Reference](API_REFERENCE.md)** - Learn the full API

---

## Uninstallation

```bash
pip uninstall env-agents
```

To remove all configuration:
```bash
rm -rf config/
rm -rf ~/.config/earthengine/
```