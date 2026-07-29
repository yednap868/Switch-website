# Playwright Installation with UV

## The Problem

When using `uv pip install playwright`, the package is installed in `uv`'s managed environment, **not** in the system Python (`/usr/bin/python3`).

So when you run `python3 -m playwright install chromium`, it fails because system Python doesn't have playwright.

## Solutions

### Solution 1: Use `uv run` (Recommended)

```bash
# Install Python package
uv pip install playwright

# Install browser binaries using uv's Python
uv run playwright install chromium
```

### Solution 2: Use `uv python`

```bash
# Check which Python uv uses
uv python --version

# Install browser binaries
uv python -m playwright install chromium
```

### Solution 3: Install in System Python

If your application uses system Python (`/usr/bin/python3`), install there instead:

```bash
# Install Python package in system Python
pip3 install playwright

# Install browser binaries
python3 -m playwright install chromium
```

## Which Solution to Use?

**Check which Python your application uses:**

```bash
# Check how your app starts
# Look for: python3 app.py, uv run app.py, or similar

# If using uv run:
uv run playwright install chromium

# If using system python3:
pip3 install playwright
python3 -m playwright install chromium
```

## Verify Installation

After installing, verify:

```bash
# If using uv:
uv run playwright install --dry-run chromium

# If using system Python:
python3 -m playwright install --dry-run chromium
```

## For FastAPI/Production

If your production app uses `uv` to run, then use:
```bash
uv run playwright install chromium
```

If your production app uses system Python, then use:
```bash
pip3 install playwright
python3 -m playwright install chromium
```

**Important:** The Python environment that runs your application **must** be the same one where you install the browser binaries.

