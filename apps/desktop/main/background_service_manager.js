const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');
const {
  renderLinuxSystemdUnit,
  renderMacLaunchAgent,
  renderWindowsTaskXml,
} = require('./service_install_templates');

const SERVICE_IDENTIFIERS = {
  linux: 'smap-service.service',
  macos: 'com.smap.service',
  windows: 'SMAPService',
};

function runCommand(command, args) {
  return new Promise((resolve) => {
    const child = spawn(command, args, { shell: false });
    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });
    child.on('error', (error) => {
      resolve({ ok: false, exitCode: 1, stdout, stderr, error: String(error.message || error) });
    });
    child.on('close', (exitCode) => {
      resolve({ ok: exitCode === 0, exitCode, stdout: stdout.trim(), stderr: stderr.trim(), error: null });
    });
  });
}

async function getBackgroundServiceStatus(options = {}) {
  const platform = options.platform || process.platform;
  const run = options.run || runCommand;

  if (platform === 'linux') {
    const installedProbe = await run('systemctl', ['--user', 'cat', SERVICE_IDENTIFIERS.linux]);
    const activeProbe = await run('systemctl', ['--user', 'is-active', SERVICE_IDENTIFIERS.linux]);
    return {
      supported: true,
      manager: 'systemd-user',
      identifier: SERVICE_IDENTIFIERS.linux,
      installed: installedProbe.ok,
      running: activeProbe.ok && activeProbe.stdout.trim() === 'active',
      detail: activeProbe.stderr || activeProbe.stdout || installedProbe.stderr || '',
    };
  }

  if (platform === 'darwin') {
    const uid = process.getuid ? String(process.getuid()) : '501';
    const probe = await run('launchctl', ['print', `gui/${uid}/${SERVICE_IDENTIFIERS.macos}`]);
    return {
      supported: true,
      manager: 'launchd',
      identifier: SERVICE_IDENTIFIERS.macos,
      installed: probe.ok,
      running: probe.ok && probe.stdout.includes('state = running'),
      detail: probe.stderr || probe.stdout || '',
    };
  }

  if (platform === 'win32') {
    const probe = await run('schtasks', ['/Query', '/TN', SERVICE_IDENTIFIERS.windows]);
    return {
      supported: true,
      manager: 'task-scheduler',
      identifier: SERVICE_IDENTIFIERS.windows,
      installed: probe.ok,
      running: probe.ok && probe.stdout.toLowerCase().includes('running'),
      detail: probe.stderr || probe.stdout || '',
    };
  }

  return {
    supported: false,
    manager: 'unsupported',
    identifier: '',
    installed: false,
    running: false,
    detail: `Unsupported platform: ${platform}`,
  };
}

async function installOnLinux(launchSpec, run) {
  const workingDirectory = path.dirname(launchSpec.command || process.cwd());
  const systemdDir = path.join(os.homedir(), '.config', 'systemd', 'user');
  fs.mkdirSync(systemdDir, { recursive: true });
  const unitPath = path.join(systemdDir, SERVICE_IDENTIFIERS.linux);
  const unitContent = renderLinuxSystemdUnit({
    description: 'SMAP Background Service',
    workingDirectory,
    serviceBin: launchSpec.command,
    serviceArgs: launchSpec.args,
  });
  fs.writeFileSync(unitPath, unitContent, 'utf8');

  const daemonReload = await run('systemctl', ['--user', 'daemon-reload']);
  if (!daemonReload.ok) return daemonReload;
  const enable = await run('systemctl', ['--user', 'enable', '--now', SERVICE_IDENTIFIERS.linux]);
  return enable;
}

async function installOnMacOS(launchSpec, run) {
  const workingDirectory = path.dirname(launchSpec.command || process.cwd());
  const launchDir = path.join(os.homedir(), 'Library', 'LaunchAgents');
  fs.mkdirSync(launchDir, { recursive: true });
  const plistPath = path.join(launchDir, `${SERVICE_IDENTIFIERS.macos}.plist`);
  const plistContent = renderMacLaunchAgent({
    label: SERVICE_IDENTIFIERS.macos,
    workingDirectory,
    serviceBin: launchSpec.command,
    serviceArgs: launchSpec.args,
  });
  fs.writeFileSync(plistPath, plistContent, 'utf8');

  await run('launchctl', ['unload', plistPath]);
  return run('launchctl', ['load', plistPath]);
}

async function installOnWindows(launchSpec, run) {
  const workingDirectory = path.dirname(launchSpec.command || process.cwd());
  const tempPath = path.join(os.tmpdir(), 'smap-service-task.xml');
  const taskXml = renderWindowsTaskXml({
    description: 'SMAP Background Service Task',
    workingDirectory,
    serviceBin: launchSpec.command,
    serviceArgs: launchSpec.args,
  });
  fs.writeFileSync(tempPath, taskXml, 'utf16le');

  await run('schtasks', ['/Delete', '/TN', SERVICE_IDENTIFIERS.windows, '/F']);
  const create = await run('schtasks', ['/Create', '/TN', SERVICE_IDENTIFIERS.windows, '/XML', tempPath, '/F']);
  if (!create.ok) {
    return create;
  }
  return run('schtasks', ['/Run', '/TN', SERVICE_IDENTIFIERS.windows]);
}

async function installBackgroundService(launchSpec, options = {}) {
  const platform = options.platform || process.platform;
  const run = options.run || runCommand;

  let result;
  if (platform === 'linux') {
    result = await installOnLinux(launchSpec, run);
  } else if (platform === 'darwin') {
    result = await installOnMacOS(launchSpec, run);
  } else if (platform === 'win32') {
    result = await installOnWindows(launchSpec, run);
  } else {
    return {
      ok: false,
      exitCode: 1,
      stdout: '',
      stderr: `Unsupported platform: ${platform}`,
      status: await getBackgroundServiceStatus({ platform, run }),
    };
  }

  const status = await getBackgroundServiceStatus({ platform, run });
  return {
    ok: result.ok,
    exitCode: result.exitCode,
    stdout: result.stdout,
    stderr: result.stderr,
    status,
  };
}

module.exports = {
  SERVICE_IDENTIFIERS,
  getBackgroundServiceStatus,
  installBackgroundService,
};
