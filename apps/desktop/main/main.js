const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const pty = require('node-pty');
const { PROFILES, isCommandAllowed } = require('./terminal_profiles');
const { runMandatoryCliChecks } = require('./cli_checks');
const { buildWizardCliInstallPlan, runWizardCliInstall } = require('./wizard_cli_install');
const { resolveServiceLaunch } = require('./service_runtime');
const { getBackgroundServiceStatus, installBackgroundService } = require('./background_service_manager');

let mainWindow;
let serviceProc;
let terminalSession;
let activeServiceLaunch;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'preload.js')
    }
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
}

function startService() {
  if (serviceProc) return;
  const repoRoot = path.resolve(__dirname, '..', '..', '..');
  const launch = resolveServiceLaunch({
    env: process.env,
    platform: process.platform,
    isPackaged: app.isPackaged,
    resourcesPath: process.resourcesPath,
    repoRoot,
  });
  activeServiceLaunch = launch;

  serviceProc = spawn(launch.command, launch.args, {
    shell: false,
    env: {
      ...process.env,
      SMAP_SERVICE_PORT: String(launch.port || ''),
    },
  });
  console.log(`[SMAP] service launch mode=${launch.mode} source=${launch.source} command=${launch.command}`);

  serviceProc.on('exit', () => {
    serviceProc = null;
  });
}

function stopService() {
  if (!serviceProc) return;
  serviceProc.kill();
  serviceProc = null;
}

function startTerminalSession(options = {}) {
  stopTerminalSession();
  const profile = options.profile || 'ops_status';
  const advancedMode = Boolean(options.advancedMode);
  const shell = process.env.SHELL || '/bin/bash';
  const cols = Math.max(Number(options.cols) || 100, 40);
  const rows = Math.max(Number(options.rows) || 30, 10);

  const ptyProcess = pty.spawn(shell, [], {
    name: 'xterm-color',
    cols,
    rows,
    cwd: process.cwd(),
    env: process.env,
  });

  ptyProcess.onData((chunk) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('terminal-output', chunk);
    }
  });
  ptyProcess.onExit((event) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('terminal-exit', event);
    }
    terminalSession = null;
  });

  terminalSession = {
    profile,
    advancedMode,
    ptyProcess,
  };
  ptyProcess.write(`echo \"[SMAP] terminal started profile=${profile} advanced=${advancedMode}\"\\r`);
  return { ok: true, profile, advancedMode };
}

function stopTerminalSession() {
  if (!terminalSession) {
    return { ok: true };
  }
  try {
    terminalSession.ptyProcess.kill();
  } catch {
    // no-op: process may already be closed
  }
  terminalSession = null;
  return { ok: true };
}

app.whenReady().then(() => {
  createWindow();
  startService();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopTerminalSession();
    stopService();
    app.quit();
  }
});

ipcMain.handle('service-status', () => ({
  running: !!serviceProc,
  launch: activeServiceLaunch
    ? {
        ...activeServiceLaunch,
        baseUrl: `http://127.0.0.1:${activeServiceLaunch.port}`,
      }
    : null,
}));
ipcMain.handle('service-stop', () => {
  stopService();
  return { ok: true };
});
ipcMain.handle('service-start', () => {
  startService();
  return { ok: true };
});
ipcMain.handle('cli-checks', (_, payload) =>
  runMandatoryCliChecks({
    requiredCliIds: Array.isArray(payload?.requiredCliIds) ? payload.requiredCliIds : undefined,
  }),
);
ipcMain.handle('wizard-cli-install-plan', (_, payload) =>
  buildWizardCliInstallPlan({
    platform: process.platform,
    subscription: payload?.subscription,
    cliId: payload?.cliId,
  }),
);
ipcMain.handle('wizard-cli-install-run', async (_, payload) =>
  runWizardCliInstall({
    platform: process.platform,
    subscription: payload?.subscription,
    cliId: payload?.cliId,
  }),
);
ipcMain.handle('background-service-status', async () =>
  getBackgroundServiceStatus({
    platform: process.platform,
  }),
);
ipcMain.handle('background-service-install', async () => {
  const repoRoot = path.resolve(__dirname, '..', '..', '..');
  const launch = resolveServiceLaunch({
    env: process.env,
    platform: process.platform,
    isPackaged: app.isPackaged,
    resourcesPath: process.resourcesPath,
    repoRoot,
  });
  return installBackgroundService(launch, {
    platform: process.platform,
    isPackaged: app.isPackaged,
    resourcesPath: process.resourcesPath,
    mainDir: __dirname,
  });
});

ipcMain.handle('terminal-profiles', () => ({
  items: Object.entries(PROFILES).map(([key, value]) => ({
    key,
    description: value.description,
  })),
}));

ipcMain.handle('terminal-start', (_, options) => startTerminalSession(options));
ipcMain.handle('terminal-stop', () => stopTerminalSession());
ipcMain.handle('terminal-resize', (_, payload) => {
  if (!terminalSession) {
    return { ok: false, error: 'no_session' };
  }
  const cols = Math.max(Number(payload?.cols) || 100, 40);
  const rows = Math.max(Number(payload?.rows) || 30, 10);
  terminalSession.ptyProcess.resize(cols, rows);
  return { ok: true };
});
ipcMain.handle('terminal-write', (_, payload) => {
  if (!terminalSession) {
    return { ok: false, error: 'no_session' };
  }
  const command = String(payload?.command || '').trim();
  if (!command) {
    return { ok: false, error: 'empty_command' };
  }
  if (!terminalSession.advancedMode && !isCommandAllowed(terminalSession.profile, command)) {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send(
        'terminal-output',
        `\\r\\n[SMAP] blocked by profile '${terminalSession.profile}': ${command}\\r\\n`,
      );
    }
    return { ok: false, error: 'command_not_allowed' };
  }
  terminalSession.ptyProcess.write(`${command}\\r`);
  return { ok: true };
});
