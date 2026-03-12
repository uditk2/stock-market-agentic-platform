const test = require('node:test');
const assert = require('node:assert/strict');

const { resolveServiceLaunch } = require('./service_runtime');

function fakeExists(paths = []) {
  const set = new Set(paths);
  return (target) => set.has(target);
}

test('resolver prioritizes SMAP_SERVICE_BIN env override', () => {
  const result = resolveServiceLaunch({
    env: { SMAP_SERVICE_BIN: '/custom/smap-service' },
    platform: 'linux',
    isPackaged: true,
    resourcesPath: '/resources',
    repoRoot: '/repo',
    existsSync: fakeExists([]),
  });

  assert.equal(result.mode, 'env_override');
  assert.equal(result.command, '/custom/smap-service');
  assert.equal(result.port, 18787);
});

test('resolver uses packaged binary when available', () => {
  const result = resolveServiceLaunch({
    env: {},
    platform: 'linux',
    isPackaged: true,
    resourcesPath: '/resources',
    repoRoot: '/repo',
    existsSync: fakeExists(['/resources/service/smap-service']),
  });

  assert.equal(result.mode, 'bundled_binary');
  assert.equal(result.command, '/resources/service/smap-service');
  assert.equal(result.port, 18787);
});

test('resolver uses repo dist binary in unpackaged mode', () => {
  const result = resolveServiceLaunch({
    env: {},
    platform: 'win32',
    isPackaged: false,
    resourcesPath: 'C:/Resources',
    repoRoot: 'C:/repo',
    existsSync: fakeExists(['C:/repo/apps/service/dist/smap-service.exe']),
  });

  assert.equal(result.mode, 'dev_binary');
  assert.equal(result.command, 'C:/repo/apps/service/dist/smap-service.exe');
  assert.equal(result.port, 18787);
});

test('resolver falls back to python uvicorn when no binaries exist', () => {
  const result = resolveServiceLaunch({
    env: {},
    platform: 'linux',
    isPackaged: false,
    resourcesPath: '/resources',
    repoRoot: '/repo',
    existsSync: fakeExists([]),
  });

  assert.equal(result.mode, 'python_fallback');
  assert.equal(result.command, 'python3');
  assert.deepEqual(result.args, ['-m', 'uvicorn', 'smap_service.main:app', '--port', '18787']);
  assert.equal(result.port, 18787);
});
