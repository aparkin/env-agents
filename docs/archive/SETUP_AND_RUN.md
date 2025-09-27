# Setup and Run Instructions

## Quick Fix for ModuleNotFoundError

You're getting `ModuleNotFoundError: No module named 'env_agents.core'` because the package isn't properly installed. Here are the solutions:

### Option 1: Install the Package (Recommended)

```bash
# From the env-agents directory:
cd "/Users/aparkin/Arkin Lab Dropbox/Adam Arkin/Code/ENIGMA Project/analyses/2025-08-23-Soil Adaptor from GPT5/env-agents"

# Install in development mode
pip install -e .
```

This installs the package in "editable" mode so changes to the code are immediately available.

### Option 2: Use the Fixed Notebook 

I created `COMPREHENSIVE_SERVICES_NOTEBOOK_FIXED.py` which includes robust import handling and will work even if the package isn't installed.

### Option 3: Quick Python Path Fix

If you want to run the original notebook without installing, add this at the very beginning:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute()))
```

## Running the Comprehensive Services Notebook

### Using Jupyter:
```bash
jupyter notebook COMPREHENSIVE_SERVICES_NOTEBOOK_FIXED.py
```

### Using Python directly:
```bash
python COMPREHENSIVE_SERVICES_NOTEBOOK_FIXED.py
```

### Or copy-paste the cells into Jupyter

## What the Notebook Will Do

1. **Test all working services** (NASA POWER, USGS NWIS, OpenAQ, enhanced SURGO, ISRIC SoilGrids)
2. **Retrieve data from multiple California locations** (Davis, Salinas Valley, SF Bay, Sacramento River)  
3. **Display complete metadata** for all services and data
4. **Show data quality metrics** and sample data
5. **Create ready-to-analyze datasets** organized by domain
6. **Generate comprehensive performance reports**

## Expected Results

- **~80+ data points** from enhanced SURGO (all available properties)
- **Weather data** from NASA POWER for multiple locations
- **Water monitoring data** from USGS (location-dependent)
- **Air quality data** from OpenAQ (if API key provided)
- **Complete metadata and provenance** for all data
- **Performance analytics** across all services

The notebook handles import failures gracefully and will show you exactly what's working and what needs attention.