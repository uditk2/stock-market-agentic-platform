const fs = require('fs');
const path = require('path');

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

  if (env.SMAP_SERVICE_BIN) {
    return {
      command: env.SMAP_SERVICE_BIN,
      args: [],
      mode: 'env_override',
      source: 'SMAP_SERVICE_BIN',
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
      };
    }
  }

  return {
    command: 'python3',
    args: ['-m', 'uvicorn', 'smap_service.main:app', '--port', '8787'],
    mode: 'python_fallback',
    source: 'uvicorn_module',
  };
}

module.exports = {
  resolveServiceLaunch,
  serviceBinaryName,
};
