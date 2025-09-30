# env-agents Documentation

**Complete documentation for the env-agents environmental data integration framework**

---

## 🚀 Getting Started

**New to env-agents? Start here:**

1. **[Installation Guide](INSTALLATION.md)** - Set up the framework
2. **[Quick Start](QUICK_START.md)** - Your first query in 5 minutes
3. **[API Reference](API_REFERENCE.md)** - Complete API documentation

---

## 📖 Core Guides

### Working with Data

- **[Services Guide](SERVICES.md)** - All 16+ supported data sources and their capabilities
- **[Credentials Setup](CREDENTIALS.md)** - Configure API keys for services that require authentication
- **[API Reference](API_REFERENCE.md)** - Detailed API documentation with examples

### Extending the Framework

- **[Adding New Services](EXTENDING_SERVICES.md)** - How to create adapters for new data sources
- **[Local Development](development/LOCAL_DEVELOPMENT.md)** - Set up your development environment

---

## 🏭 Operations & Production

**Running env-agents in production:**

- **[Database Management](operations/DATABASE_MANAGEMENT.md)** - Managing SQLite databases, clearing data, checking status
- **[Pangenome Pipeline](operations/PANGENOME_PIPELINE.md)** - Production pipeline for 16 services across 4,789 clusters
- **[Earth Engine Operations](operations/EARTH_ENGINE_NOTES.md)** - Quota management, timeout handling, temporal fallback

---

## 🔧 Development

**For contributors and developers:**

- **[Architecture](development/ARCHITECTURE.md)** - System design and component overview
- **[Local Development](development/LOCAL_DEVELOPMENT.md)** - Development environment setup
- **[Lessons Learned](development/LESSONS_LEARNED.md)** - Best practices from production optimization

---

## 📚 Adapter-Specific Documentation

**Detailed guides for specific data sources:**

- **[MODIS Land Cover](adapters/MODIS_LANDCOVER.md)** - Interpreting MODIS MCD12Q1 categorical data
- **[USGS NWIS](adapters/USGS_NWIS.md)** - Stream gauge data and parameter codes

---

## 🗂️ Additional Resources

### Examples & Tutorials
- **[Jupyter Notebooks](../notebooks/README.md)** - Interactive demonstrations
- **[Example Scripts](../examples/README.md)** - Common usage patterns

### Testing
- **[Test Suite](../tests/README.md)** - Running and writing tests

### Project Info
- **[Contributing Guidelines](../CONTRIBUTING.md)** - How to contribute to the project
- **[Historical Documentation](archive/README.md)** - Archived docs from previous versions

---

## 🔍 Quick Links by Task

### I want to...

- **Get environmental data** → Start with [Quick Start](QUICK_START.md)
- **Add a new data source** → See [Extending Services](EXTENDING_SERVICES.md)
- **Run the production pipeline** → See [Pangenome Pipeline](operations/PANGENOME_PIPELINE.md)
- **Fix Earth Engine quota errors** → See [Earth Engine Operations](operations/EARTH_ENGINE_NOTES.md)
- **Understand the data schema** → See [API Reference](API_REFERENCE.md#data-schema)
- **Set up API credentials** → See [Credentials Setup](CREDENTIALS.md)
- **Contribute code** → See [Contributing Guidelines](../CONTRIBUTING.md)

---

## 📝 Documentation Organization

```
docs/
├── README.md                    # ← You are here
├── INSTALLATION.md              # Setup guide
├── QUICK_START.md               # 5-minute tutorial
├── API_REFERENCE.md             # Complete API docs
├── SERVICES.md                  # All data sources
├── EXTENDING_SERVICES.md        # Adding adapters
├── CREDENTIALS.md               # API key setup
│
├── operations/                  # Production operations
│   ├── DATABASE_MANAGEMENT.md
│   ├── PANGENOME_PIPELINE.md
│   └── EARTH_ENGINE_NOTES.md
│
├── adapters/                    # Adapter-specific docs
│   ├── MODIS_LANDCOVER.md
│   └── USGS_NWIS.md
│
├── development/                 # Developer docs
│   ├── ARCHITECTURE.md
│   ├── LOCAL_DEVELOPMENT.md
│   └── LESSONS_LEARNED.md
│
└── archive/                     # Historical docs
    └── README.md
```

---

**Questions or issues?** Check [Contributing Guidelines](../CONTRIBUTING.md) or open an issue on GitHub.