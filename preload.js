const { contextBridge, ipcRenderer } = require('electron');

// 向渲染进程公开API
contextBridge.exposeInMainWorld('api', {
  // 文件选择
  selectFile: () => ipcRenderer.invoke('select-file'),
  selectModel: () => ipcRenderer.invoke('select-model'),
  selectOutput: () => ipcRenderer.invoke('select-output'),
  
  // 设置管理
  getSettings: () => ipcRenderer.invoke('get-settings'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),
  
  // 音频处理
  extractAudio: (videoFile) => ipcRenderer.invoke('extract-audio', videoFile),
  checkAudioFormat: (audioFile) => ipcRenderer.invoke('check-audio-format', audioFile),
  convertTo16k: (audioFile) => ipcRenderer.invoke('convert-to-16k', audioFile),
  getAudioDuration: (audioFile) => ipcRenderer.invoke('get-audio-duration', audioFile),
  
  // 转录功能
  startTranscription: (options) => ipcRenderer.invoke('start-transcription', options),
  stopTranscription: () => ipcRenderer.invoke('stop-transcription'),
  saveTranscription: (options) => ipcRenderer.invoke('save-transcription', options),
  
  // 事件监听
  onTranscriptionProgress: (callback) => 
    ipcRenderer.on('transcription-progress', (_, progress) => callback(progress)),
  onTranscriptionLine: (callback) =>
    ipcRenderer.on('transcription-line', (_, line) => callback(line)),
  
  // 移除事件监听
  removeAllListeners: () => {
    ipcRenderer.removeAllListeners('transcription-progress');
    ipcRenderer.removeAllListeners('transcription-line');
  }
}); 