# Contributing to CRML

Thank you for your interest in contributing to CRML (Cyber Risk Modeling Language)! We welcome contributions from the community.

## 🎯 Ways to Contribute

### 1. Report Bugs
Found a bug? [Open an issue](https://github.com/Faux16/crml/issues/new) with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, CRML version)

### 2. Suggest Features
Have an idea? [Open an issue](https://github.com/Faux16/crml/issues/new) with:
- Use case description
- Proposed solution
- Examples of how it would work

### 3. Improve Documentation
- Fix typos or clarify existing docs
- Add examples and tutorials
- Improve API documentation
- Translate documentation

### 4. Submit Code
- Fix bugs
- Implement new features
- Improve performance
- Add tests

## 🚀 Getting Started

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/crml.git
   cd crml
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**:
   ```bash
   pip install -e .
   pip install -r requirements-dev.txt  # If available
   ```

4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Making Changes

1. **Write your code**
   - Follow Python PEP 8 style guidelines
   - Add docstrings to functions and classes
   - Keep functions focused and small

2. **Test your changes**
   ```bash
   # Test the validator
   crml validate spec/examples/qber-enterprise.yaml
   
   # Test with your own models
   crml validate path/to/your/test-model.yaml
   ```

3. **Update documentation**
   - Update README.md if needed
   - Add examples if applicable
   - Update CHANGELOG.md

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Add amazing feature"
   ```
   
   Use conventional commit messages:
   - `feat:` - New feature
   - `fix:` - Bug fix
   - `docs:` - Documentation changes
   - `test:` - Test additions/changes
   - `refactor:` - Code refactoring
   - `chore:` - Maintenance tasks

5. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a PR on GitHub with a clear description.

## 📋 Pull Request Guidelines

### Before Submitting
- [ ] Code follows PEP 8 style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] PR description explains what and why

### PR Description Should Include
- **What**: What does this PR do?
- **Why**: Why is this change needed?
- **How**: How does it work?
- **Testing**: How was it tested?
- **Screenshots**: If applicable (for UI/output changes)

## 🧪 Testing

### Manual Testing
```bash
# Validate example models
crml validate spec/examples/qber-enterprise.yaml
crml validate spec/examples/fair-baseline.yaml

# Test with invalid models
crml validate path/to/invalid-model.yaml  # Should fail gracefully
```

### Adding Tests
If you're adding new functionality, please add tests:
- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test function names

## 📝 Code Style

### Python Style
- Follow [PEP 8](https://pep8.org/)
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use meaningful variable names

### Example
```python
def validate_crml(path: str) -> bool:
    """
    Validate a CRML file against the schema.
    
    Args:
        path: Path to the CRML file
        
    Returns:
        True if valid, False otherwise
    """
    # Implementation
    pass
```

## 🎯 Priority Areas

We especially welcome contributions in these areas:

### High Priority
- 🧪 **Test Coverage**: Add unit and integration tests
- 📝 **Examples**: More real-world CRML models
- 🔧 **Integrations**: Connect CRML with risk platforms
- 📖 **Tutorials**: Step-by-step guides for beginners

### Medium Priority
- 🐛 **Bug Fixes**: Fix reported issues
- ⚡ **Performance**: Optimize validation speed
- 🌐 **Internationalization**: Translate docs
- 🎨 **CLI UX**: Improve command-line experience

### Feature Ideas
- CRML model visualization tools
- IDE plugins (VS Code, PyCharm)
- Web-based validator
- Model templates and generators
- Integration with popular risk frameworks

## 🤔 Questions?

- **General questions**: [Open a discussion](https://github.com/Faux16/crml/discussions)
- **Bug reports**: [Open an issue](https://github.com/Faux16/crml/issues)
- **Security issues**: Email research@zeron.one (do not open public issues)

## 📜 Code of Conduct

### Our Pledge
We are committed to providing a welcoming and inclusive environment for all contributors.

### Expected Behavior
- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information

## 📄 License

By contributing to CRML, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to CRML!** 🎉

Every contribution, no matter how small, makes a difference. We appreciate your time and effort in making CRML better for everyone.
