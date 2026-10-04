import test from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('Header component exports and contains core branding', (t) => {
  const headerPath = path.resolve(__dirname, 'Header.tsx');
  assert.ok(fs.existsSync(headerPath), 'Header.tsx must exist');

  const content = fs.readFileSync(headerPath, 'utf8');
  assert.ok(content.includes('export const Header'), 'Header component must be exported');
  assert.ok(content.includes('company-logo.svg'), 'Header must reference company logo');
});

test('App layout defines main dashboard view', (t) => {
  const appPath = path.resolve(__dirname, '../App.tsx');
  assert.ok(fs.existsSync(appPath), 'App.tsx must exist');

  const content = fs.readFileSync(appPath, 'utf8');
  assert.ok(content.includes('CodeGuard Dashboard'), 'App must render dashboard title');
  assert.ok(content.includes('<Header />'), 'App must render Header component');
});
