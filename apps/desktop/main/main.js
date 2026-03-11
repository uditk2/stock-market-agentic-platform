const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let serviceProc;

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
  const servicePath = process.env.SMAP_SERVICE_BIN || 'python3';
  const args = process.env.SMAP_SERVICE_BIN ? [] : ['-m', 'uvicorn', 'smap_service.main:app', '--port', '8787'];
  serviceProc = spawn(servicePath, args, { shell: false });

  serviceProc.on('exit', () => {
    serviceProc = null;
  });
}

function stopService() {
  if (!serviceProc) return;
  serviceProc.kill();
  serviceProc = null;
}

app.whenReady().then(() => {
  createWindow();
  startService();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopService();
    app.quit();
  }
});

ipcMain.handle('service-status', () => ({ running: !!serviceProc }));
ipcMain.handle('service-stop', () => {
  stopService();
  return { ok: true };
});
ipcMain.handle('service-start', () => {
  startService();
  return { ok: true };
});
