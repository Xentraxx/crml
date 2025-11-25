# CRML v1.0.0 - Initial Release 🎉

We're excited to announce the first official release of **CRML (Cyber Risk Modeling Language)** - an open, declarative language for expressing cyber risk models, telemetry mappings, and simulation pipelines.

## 🚀 What's New

### PyPI Package Available
CRML is now available on PyPI! Install with:
```bash
pip install crml-lang
```

### Command-Line Tool
Use the `crml` CLI to validate your risk models:
```bash
crml validate path/to/your/model.yaml
```

### Key Features
- ✅ **Declarative YAML/JSON syntax** for cyber risk models
- ✅ **JSON Schema validation** for model correctness
- ✅ **Support for multiple frameworks**: QBER, FAIR, Monte Carlo engines
- ✅ **Implementation-agnostic** - works with any risk quantification platform
- ✅ **Python 3.7+** compatibility

## 📦 Installation Options

### Option 1: Install from PyPI (Recommended)
```bash
pip install crml-lang
```

### Option 2: Build from Source
```bash
git clone https://github.com/Faux16/crml.git
cd crml
pip install -e .
```

### Option 3: Download Release Assets
Download the source code or wheel from the assets below and install:
```bash
pip install crml_lang-1.0.0-py3-none-any.whl
```

## 📖 Quick Start

1. **Install CRML**:
   ```bash
   pip install crml-lang
   ```

2. **Validate an example model**:
   ```bash
   crml validate spec/examples/qber-enterprise.yaml
   ```

3. **Check out the documentation**:
   - [CRML Specification](spec/crml-1.0.md)
   - [Example Models](spec/examples/)
   - [Full Documentation](docs/)

## 🎯 Use Cases

CRML is designed for:
- **Bayesian cyber risk models** (QBER, MCMC-based)
- **FAIR-style Monte Carlo engines**
- **Insurance actuarial risk systems**
- **Enterprise cyber risk quantification platforms**
- **Regulatory or audit-ready risk engines**

## 🛠️ What's Included

### Package Structure
```
crml/
├── src/crml/              # Python package
│   ├── cli.py             # Command-line interface
│   ├── validator.py       # CRML validator
│   └── schema/            # JSON schema
├── spec/                  # CRML specification
│   ├── crml-1.0.md        # Full spec document
│   ├── crml-schema.json   # JSON schema
│   └── examples/          # Example models
├── docs/                  # Documentation
└── tools/                 # Legacy utilities
```

### Dependencies
- `pyyaml` - YAML parsing
- `jsonschema` - Schema validation

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Report Issues
Found a bug or have a feature request? [Open an issue](https://github.com/Faux16/crml/issues/new)

### Submit Pull Requests
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests if applicable
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Areas We Need Help
- 📝 **Documentation**: Improve examples, tutorials, and guides
- 🧪 **Testing**: Add test cases and improve coverage
- 🔧 **Tooling**: Build integrations with risk platforms
- 🌐 **Examples**: Share your CRML models and use cases
- 🐛 **Bug Fixes**: Help us squash bugs
- ✨ **Features**: Propose and implement new capabilities

## 📊 Example Model

Here's a simple CRML model:

```yaml
crml_version: "1.0"
model:
  name: "Basic Risk Model"
  description: "Example cyber risk model"
  
nodes:
  - id: threat_frequency
    type: distribution
    distribution:
      type: poisson
      lambda: 12
      
  - id: loss_magnitude
    type: distribution
    distribution:
      type: lognormal
      mu: 10
      sigma: 2

simulation:
  method: monte_carlo
  iterations: 10000
  seed: 42

outputs:
  - metric: annual_loss_expectancy
    aggregation: mean
```

## 🔗 Links

- **PyPI Package**: https://pypi.org/project/crml-lang/
- **Documentation**: [docs/](docs/)
- **Specification**: [spec/crml-1.0.md](spec/crml-1.0.md)
- **Examples**: [spec/examples/](spec/examples/)

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

Maintained by **Zeron Research Labs**

---

**Ready to get started?** Install CRML today:
```bash
pip install crml-lang
```

**Questions?** Open an issue or start a discussion!
