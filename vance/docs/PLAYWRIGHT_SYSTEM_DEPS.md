# Playwright System Dependencies Fix

## Error: `libnspr4.so: cannot open shared object file`

This error occurs when Chromium browser binaries are missing required system libraries.

## Solution: Install System Dependencies

On **Ubuntu/Debian** systems:

```bash
# Install required libraries
sudo apt-get update
sudo apt-get install -y \
  libnspr4 \
  libnss3 \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libcups2 \
  libdrm2 \
  libdbus-1-3 \
  libxkbcommon0 \
  libxcomposite1 \
  libxdamage1 \
  libxfixes3 \
  libxrandr2 \
  libgbm1 \
  libasound2 \
  libpango-1.0-0 \
  libcairo2

# Verify Chromium can launch
python3 -m playwright install chromium
```

On **CentOS/RHEL** systems:

```bash
sudo yum install -y \
  nss \
  nspr \
  atk \
  cups-libs \
  libdrm \
  libXkbcommon \
  libXcomposite \
  libXdamage \
  libXfixes \
  libXrandr \
  mesa-libgbm \
  alsa-lib \
  pango \
  cairo
```

## Verify Fix

After installing dependencies, test Playwright:

```bash
python3 -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://example.com')
        print('✅ Playwright works!')
        await browser.close()

asyncio.run(test())
"
```

## Alternative: Use Playwright's install-deps

Playwright provides a script to install system dependencies:

```bash
# For Ubuntu/Debian
python3 -m playwright install-deps chromium

# This installs all required system packages
```

**Note:** This requires `sudo` access. If you don't have sudo, you'll need to ask your system administrator to install the dependencies.

## For Docker/Container Environments

If running in a container, add to your `Dockerfile`:

```dockerfile
RUN apt-get update && apt-get install -y \
  libnspr4 \
  libnss3 \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libcups2 \
  libdrm2 \
  libdbus-1-3 \
  libxkbcommon0 \
  libxcomposite1 \
  libxdamage1 \
  libxfixes3 \
  libxrandr2 \
  libgbm1 \
  libasound2 \
  libpango-1.0-0 \
  libcairo2 \
  && rm -rf /var/lib/apt/lists/*
```

