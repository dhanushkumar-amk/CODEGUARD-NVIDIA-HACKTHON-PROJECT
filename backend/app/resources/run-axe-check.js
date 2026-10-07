#!/usr/bin/env node
/**
 * CodeGuard Axe-Core Sandbox Runner
 * Starts target application dev server, navigates via Playwright headless Chromium,
 * executes axe-core accessibility audit, and emits structured JSON metrics.
 */

const fs = require('fs');
const http = require('http');
const { spawn } = require('child_process');

// Candidate dev ports to probe
const CANDIDATE_PORTS = [5173, 3000, 4173, 8080, 5174, 3001];

function checkUrl(url) {
  return new Promise((resolve) => {
    try {
      const parsed = new URL(url);
      const req = http.get(
        {
          hostname: parsed.hostname,
          port: parsed.port,
          path: parsed.pathname,
          timeout: 1500,
        },
        (res) => {
          resolve(true);
        }
      );
      req.on('error', () => resolve(false));
      req.on('timeout', () => {
        req.destroy();
        resolve(false);
      });
    } catch (e) {
      resolve(false);
    }
  });
}

async function waitForServer(detectedUrl, maxWaitMs = 30000) {
  const start = Date.now();
  const testUrls = detectedUrl ? [detectedUrl] : CANDIDATE_PORTS.map((p) => `http://localhost:${p}`);

  while (Date.now() - start < maxWaitMs) {
    for (const url of testUrls) {
      const isAlive = await checkUrl(url);
      if (isAlive) {
        return url;
      }
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  return null;
}

async function main() {
  let serverProcess = null;
  let browser = null;
  let detectedUrl = null;

  try {
    // 1. Detect dev command from package.json
    let pkg = {};
    if (fs.existsSync('package.json')) {
      try {
        pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
      } catch (e) {}
    }

    const scripts = pkg.scripts || {};
    let runCommandStr = 'npm run dev';
    if (scripts.dev) {
      runCommandStr = 'npm run dev';
    } else if (scripts.start) {
      runCommandStr = 'npm start';
    } else if (scripts.preview) {
      runCommandStr = 'npm run preview';
    } else {
      runCommandStr = 'npx vite';
    }

    // 2. Spawn dev server
    serverProcess = spawn(runCommandStr, {
      shell: true,
      detached: process.platform !== 'win32',
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, BROWSER: 'none', CI: 'true' },
    });

    const urlRegex = /https?:\/\/(?:localhost|127\.0\.0\.1|\[::1\]):(\d+)/i;

    serverProcess.stdout.on('data', (data) => {
      const text = data.toString();
      const match = text.match(urlRegex);
      if (match && !detectedUrl) {
        detectedUrl = `http://localhost:${match[1]}`;
      }
    });

    serverProcess.stderr.on('data', (data) => {
      const text = data.toString();
      const match = text.match(urlRegex);
      if (match && !detectedUrl) {
        detectedUrl = `http://localhost:${match[1]}`;
      }
    });

    // 3. Wait for dev server readiness
    const activeUrl = await waitForServer(detectedUrl, 30000);
    if (!activeUrl) {
      console.log(JSON.stringify({ error: 'server_failed_to_start' }));
      return;
    }

    // 4. Launch Playwright headless Chromium
    const { chromium } = require('playwright');
    browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    });

    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 },
    });
    const page = await context.newPage();

    // 5. Navigate to application
    await page.goto(activeUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    // Wait for React app container to render
    await page.waitForTimeout(1500);

    // 6. Inject and execute axe-core
    let axeSource = '';
    try {
      axeSource = require('axe-core').source;
    } catch (e) {
      // Fallback if not directly installed in sandbox node_modules
    }

    if (axeSource) {
      await page.evaluate(axeSource);
    } else {
      await page.addScriptTag({
        url: 'https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.0/axe.min.js',
      });
    }

    const axeResults = await page.evaluate(async () => {
      if (typeof window.axe === 'undefined') {
        throw new Error('axe-core failed to inject into page DOM');
      }
      return await window.axe.run(document, {
        runOnly: {
          type: 'tag',
          values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'],
        },
      });
    });

    // 7. Calculate compliance score
    const passesCount = Array.isArray(axeResults.passes) ? axeResults.passes.length : 0;
    const violations = Array.isArray(axeResults.violations) ? axeResults.violations : [];
    const incompleteCount = Array.isArray(axeResults.incomplete) ? axeResults.incomplete.length : 0;
    const totalCount = passesCount + violations.length;

    const score = totalCount > 0 ? Number(((passesCount / totalCount) * 100).toFixed(1)) : 100.0;

    const output = {
      violations,
      passes: passesCount,
      incomplete: incompleteCount,
      url_tested: activeUrl,
      score,
    };

    console.log(JSON.stringify(output));
  } catch (err) {
    console.log(JSON.stringify({ error: err.message || String(err) }));
  } finally {
    // 8. Clean up browser and child server processes
    if (browser) {
      try {
        await browser.close();
      } catch (e) {}
    }
    if (serverProcess) {
      try {
        if (process.platform === 'win32') {
          spawn('taskkill', ['/pid', serverProcess.pid, '/f', '/t']);
        } else {
          try {
            process.kill(-serverProcess.pid, 'SIGKILL');
          } catch (e) {
            serverProcess.kill('SIGKILL');
          }
        }
      } catch (e) {}
    }
  }
}

main().catch((err) => {
  console.log(JSON.stringify({ error: err.message || String(err) }));
  process.exit(0);
});
