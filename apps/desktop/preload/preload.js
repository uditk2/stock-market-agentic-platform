const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('smapBridge', {
  serviceStatus: () => ipcRenderer.invoke('service-status'),
  serviceStart: () => ipcRenderer.invoke('service-start'),
  serviceStop: () => ipcRenderer.invoke('service-stop')
});
