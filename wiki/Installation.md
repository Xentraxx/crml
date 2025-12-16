# Installation Guide

Complete guide to installing CRML on different platforms.

## Quick Install (Recommended)

```bash
pip install crml-lang
```

That's it! Verify with:
```bash
crml --version
```

---

## Platform-Specific Instructions

### macOS

**Option 1: Using pip (Recommended)**
```bash
# Install Python 3.8+ if needed
brew install python3

# Install CRML
pip3 install crml-lang

# Verify
crml --version
```

**Option 2: Using pipx (Isolated)**
```bash
# Install pipx
brew install pipx
pipx ensurepath

# Install CRML
pipx install crml-lang

# Verify
crml --version
```

---

### Linux (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install Python 3.8+
sudo apt install python3 python3-pip

# Install CRML
pip3 install crml-lang

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify
crml --version
```

---

### Windows

**Option 1: Using pip**
```powershell
# Install Python 3.8+ from python.org

# Install CRML
pip install crml-lang

# Verify
crml --version
```

**Option 2: Using Windows Terminal**
```powershell
# Install Python from Microsoft Store
# Then:
pip install crml-lang
```

---

## Web Platform Setup

### Prerequisites
- Node.js 18+ and npm
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/Faux16/crml.git
cd crml/web

# Install dependencies
npm install

# Run development server
npm run dev
```

Visit http://localhost:3000

---

## Docker Installation

```bash
# Pull image (when available)
docker pull ghcr.io/faux16/crml:latest

# Run
docker run -it ghcr.io/faux16/crml:latest crml --version
```

---

## Troubleshooting

See [Troubleshooting Guide](Reference/Troubleshooting) for common issues.
