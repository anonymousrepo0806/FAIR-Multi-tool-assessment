# F-UJI's official image (ghcr.io/pangaea-data-publisher/fuji) ships without
# Playwright's Chromium binary, which its own app.py requires at startup
# (BrowserManager.init_browser() -> playwright.chromium.launch()). Without
# this, the container crash-loops on every start with:
#   "BrowserType.launch: Executable doesn't exist at .../chrome-headless-shell"
# This layer installs exactly what the upstream image's own error message
# asks for.
FROM ghcr.io/pangaea-data-publisher/fuji:latest

RUN pip install --no-cache-dir playwright \
    && playwright install --with-deps chromium
