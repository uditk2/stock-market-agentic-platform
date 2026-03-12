const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('smapBridge', {
  serviceStatus: () => ipcRenderer.invoke('service-status'),
  serviceStart: () => ipcRenderer.invoke('service-start'),
  serviceStop: () => ipcRenderer.invoke('service-stop'),
  terminalProfiles: () => ipcRenderer.invoke('terminal-profiles'),
  terminalStart: (options) => ipcRenderer.invoke('terminal-start', options),
  terminalStop: () => ipcRenderer.invoke('terminal-stop'),
  terminalResize: (size) => ipcRenderer.invoke('terminal-resize', size),
  terminalWrite: (payload) => ipcRenderer.invoke('terminal-write', payload),
  onTerminalOutput: (callback) => {
    const handler = (_, chunk) => callback(chunk);
    ipcRenderer.on('terminal-output', handler);
    return () => ipcRenderer.removeListener('terminal-output', handler);
  },
  onTerminalExit: (callback) => {
    const handler = (_, event) => callback(event);
    ipcRenderer.on('terminal-exit', handler);
    return () => ipcRenderer.removeListener('terminal-exit', handler);
  },
});
