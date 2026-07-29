# Playwright Installation Guide

## Why Both Steps Are Needed

Playwright requires **two components**:
1. **Python package** - `playwright` (installed via pip/uv)
2. **Browser binaries** - Chromium, Firefox, WebKit (installed separately)

Even if the Python package is installed, you **must** also install the browser binaries.

## Installation Steps

### On Server (Production)

If using `uv` (recommended):
```bash
# Install Python package
uv pip install playwright

# Install browser binaries (REQUIRED)
# Use python3 -m playwright instead of direct playwright command
python3 -m playwright install chromium
```

If using regular `pip`:
```bash
# Install Python package
pip install playwright

# Install browser binaries (REQUIRED)
playwright install chromium
# OR
python3 -m playwright install chromium
```

### Verify Installation

```bash
# Check Python package
python3 -c "import playwright; print(playwright.__version__)"

# Check if browsers are installed (use python3 -m)
python3 -m playwright install --dry-run chromium
```

If the dry-run shows "Already installed", you're good. If not, run `python3 -m playwright install chromium`.

## Troubleshooting

### Error: "playwright: command not found"

When using `uv pip install`, the `playwright` CLI might not be in your PATH. Use:
```bash
python3 -m playwright install chromium
```

Instead of:
```bash
playwright install chromium  # ❌ Won't work with uv
```

### Error: "Playwright not available"

This usually means:
1. **Python package not installed**: Run `pip install playwright` or `uv pip install playwright`
2. **Browser binaries not installed**: Run `python3 -m playwright install chromium`
3. **Wrong Python environment**: Make sure you're installing in the same environment your app runs in

### Check Server Environment

On the server, check which Python is being used:
```bash
which python3
python3 --version
```

Install Playwright in that environment:
```bash
# If using venv
source .venv/bin/activate
pip install playwright
python3 -m playwright install chromium

# If using uv
uv pip install playwright
python3 -m playwright install chromium
```

## For AI Job Application Feature

The `job_application_service` will only work if **both** are installed:
- ✅ Python package: `from playwright.async_api import async_playwright` must work
- ✅ Browser binaries: `python3 -m playwright install chromium` must have been run

Without both, the service will return:
```json
{
  "status": "error",
  "message": "Playwright not available. Please install: pip install playwright && playwright install"
}
```
