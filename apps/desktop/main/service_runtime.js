const fs = require('fs');
const path = require('path');
const DEFAULT_SERVICE_PORT = 18787;

function serviceBinaryName(platform) {
  return platform === 'win32' ? 'smap-service.exe' : 'smap-service';
}

function resolveServiceLaunch(options = {}) {
  const env = options.env || process.env;
  const platform = options.platform || process.platform;
  const isPackaged = Boolean(options.isPackaged);
  const resourcesPath = options.resourcesPath || process.resourcesPath || '';
  const repoRoot = options.repoRoot || process.cwd();
  const existsSync = options.existsSync || fs.existsSync;
  const requestedPort = Number(env.SMAP_SERVICE_PORT || options.port || DEFAULT_SERVICE_PORT);
  const port = Number.isFinite(requestedPort) && requestedPort > 0 ? requestedPort : DEFAULT_SERVICE_PORT;

  if (env.SMAP_SERVICE_BIN) {
    return {
      command: env.SMAP_SERVICE_BIN,
      args: [],
      mode: 'env_override',
      source: 'SMAP_SERVICE_BIN',
      port,
    };
  }

  const binary = serviceBinaryName(platform);
  const candidates = [];

  if (isPackaged && resourcesPath) {
    candidates.push({
      path: path.join(resourcesPath, 'service', binary),
      source: 'packaged_resource',
      mode: 'bundled_binary',
    });
  }

  candidates.push({
    path: path.join(repoRoot, 'apps', 'service', 'dist', binary),
    source: 'repo_dist',
    mode: 'dev_binary',
  });

  for (const candidate of candidates) {
    if (existsSync(candidate.path)) {
      return {
        command: candidate.path,
        args: [],
        mode: candidate.mode,
        source: candidate.source,
        port,
      };
    }
  }

  return {
    command: 'python3',
    args: ['-m', 'uvicorn', 'smap_service.main:app', '--port', String(port)],
    mode: 'python_fallback',
    source: 'uvicorn_module',
    port,
  };
}

module.exports = {
  DEFAULT_SERVICE_PORT,
  resolveServiceLaunch,
  serviceBinaryName,
};
