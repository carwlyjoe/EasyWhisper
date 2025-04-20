const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, exec } = require('child_process');
const log = require('electron-log');
const Store = require('electron-store');
const ffmpeg = require('fluent-ffmpeg');

// 配置日志
log.transports.file.level = 'info';
log.info('应用启动');

// 创建配置存储
const store = new Store({
  name: 'settings',
  defaults: {
    modelPaths: [],
    lastModelPath: '',
    lastModelDir: '',
    lastOutputFormat: '.srt',
    lastOutputDir: '',
    lastMediaDir: ''
  }
});

// 获取应用资源路径
function getResourcePath(relativePath) {
  const isDev = !app.isPackaged;
  
  if (isDev) {
    return path.join(__dirname, relativePath);
  } else {
    return path.join(process.resourcesPath, relativePath);
  }
}

// 获取 FFmpeg 路径
function getFFmpegPath() {
  try {
    // 检查系统 FFmpeg
    const checkCmd = process.platform === 'win32' ? 'where ffmpeg' : 'which ffmpeg';
    const result = require('child_process').execSync(checkCmd, { encoding: 'utf8' }).trim();
    
    if (result) {
      log.info(`使用系统 FFmpeg: ${result.split('\n')[0]}`);
      return result.split('\n')[0];
    }
  } catch (error) {
    log.warn('系统中未找到 FFmpeg，将使用内置版本');
  }
  
  // 使用内置的 FFmpeg
  const ffmpegPath = getResourcePath(path.join('bin', process.platform === 'win32' ? 'ffmpeg.exe' : 'ffmpeg'));
  if (fs.existsSync(ffmpegPath)) {
    log.info(`使用内置 FFmpeg: ${ffmpegPath}`);
    return ffmpegPath;
  }
  
  log.error('未找到 FFmpeg');
  return null;
}

// 主窗口引用
let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 680,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.loadFile('index.html');
  
  if (process.env.NODE_ENV === 'development') {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

// 当前转录进程
let currentProcess = null;
let shouldStop = false;

// IPC 处理
ipcMain.handle('select-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: '音频和视频文件', extensions: ['mp3', 'wav', 'm4a', 'flac', 'mp4', 'avi', 'mkv', 'mov'] }
    ],
    defaultPath: store.get('lastMediaDir') || app.getPath('documents')
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    const filePath = result.filePaths[0];
    store.set('lastMediaDir', path.dirname(filePath));
    return filePath;
  }
  
  return null;
});

ipcMain.handle('select-model', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: '模型文件', extensions: ['bin'] }
    ],
    defaultPath: store.get('lastModelDir') || app.getPath('documents')
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    const filePath = result.filePaths[0];
    
    // 更新模型列表
    const modelPaths = store.get('modelPaths', []);
    if (!modelPaths.includes(filePath)) {
      modelPaths.push(filePath);
      store.set('modelPaths', modelPaths);
    }
    
    store.set('lastModelPath', filePath);
    store.set('lastModelDir', path.dirname(filePath));
    
    return filePath;
  }
  
  return null;
});

ipcMain.handle('select-output', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    defaultPath: store.get('lastOutputDir') || app.getPath('documents')
  });
  
  if (!result.canceled && result.filePaths.length > 0) {
    const dirPath = result.filePaths[0];
    store.set('lastOutputDir', dirPath);
    return dirPath;
  }
  
  return null;
});

ipcMain.handle('get-settings', () => {
  return {
    modelPaths: store.get('modelPaths', []),
    lastModelPath: store.get('lastModelPath', ''),
    lastOutputFormat: store.get('lastOutputFormat', '.srt'),
    lastOutputDir: store.get('lastOutputDir', '')
  };
});

ipcMain.handle('save-settings', (event, settings) => {
  store.set('lastModelPath', settings.lastModelPath);
  store.set('lastOutputFormat', settings.lastOutputFormat);
  if (settings.lastOutputDir) {
    store.set('lastOutputDir', settings.lastOutputDir);
  }
  return true;
});

// 提取音频
ipcMain.handle('extract-audio', async (event, videoFile) => {
  return new Promise((resolve, reject) => {
    try {
      const tempDir = app.getPath('temp');
      const outputFile = path.join(tempDir, `extracted_audio_${Date.now()}.wav`);
      
      ffmpeg(videoFile)
        .output(outputFile)
        .audioFrequency(16000)
        .audioChannels(1)
        .audioCodec('pcm_s16le')
        .on('end', () => {
          resolve(outputFile);
        })
        .on('error', (err) => {
          log.error('音频提取错误:', err);
          reject(err.message);
        })
        .run();
    } catch (error) {
      log.error('音频提取异常:', error);
      reject(error.message);
    }
  });
});

// 检查音频格式
ipcMain.handle('check-audio-format', async (event, audioFile) => {
  return new Promise((resolve, reject) => {
    try {
      ffmpeg.ffprobe(audioFile, (err, metadata) => {
        if (err) {
          reject(err.message);
          return;
        }
        
        const audioStream = metadata.streams.find(stream => stream.codec_type === 'audio');
        if (!audioStream) {
          reject('未找到音频流');
          return;
        }
        
        resolve({
          sampleRate: audioStream.sample_rate,
          is16k: audioStream.sample_rate === 16000
        });
      });
    } catch (error) {
      reject(error.message);
    }
  });
});

// 转换为16k采样率
ipcMain.handle('convert-to-16k', async (event, audioFile) => {
  return new Promise((resolve, reject) => {
    try {
      const tempDir = app.getPath('temp');
      const outputFile = path.join(tempDir, `converted_audio_${Date.now()}.wav`);
      
      ffmpeg(audioFile)
        .output(outputFile)
        .audioFrequency(16000)
        .audioChannels(1)
        .audioCodec('pcm_s16le')
        .on('end', () => {
          resolve(outputFile);
        })
        .on('error', (err) => {
          log.error('音频转换错误:', err);
          reject(err.message);
        })
        .run();
    } catch (error) {
      log.error('音频转换异常:', error);
      reject(error.message);
    }
  });
});

// 获取音频时长
ipcMain.handle('get-audio-duration', async (event, audioFile) => {
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(audioFile, (err, metadata) => {
      if (err) {
        reject(err.message);
        return;
      }
      
      if (metadata.format && metadata.format.duration) {
        resolve(parseFloat(metadata.format.duration));
      } else {
        reject('无法获取音频时长');
      }
    });
  });
});

// 运行whisper.cpp进行转录
ipcMain.handle('start-transcription', async (event, { audioFile, modelPath, language, translate, outputFormat, enableVad, vadThreshold }) => {
  shouldStop = false;
  
  // 获取whisper.cpp可执行文件路径
  const whisperPath = getResourcePath(path.join('bin', process.platform === 'win32' ? 'main.exe' : 'main'));
  
  if (!fs.existsSync(whisperPath)) {
    throw new Error(`未找到whisper执行文件: ${whisperPath}`);
  }

  // 创建临时输出文件路径
  const tempDir = app.getPath('temp');
  const tempOutputBase = path.join(tempDir, `whisper_output_${Date.now()}`);
  const tempOutputFile = tempOutputBase + (outputFormat === '.srt' ? '.srt' : '.txt');

  // 构建命令行参数
  const args = [
    '-m', modelPath,
    '-f', audioFile,
    '-l', language,
    '-of', tempOutputBase  // 指定输出文件基础名
  ];
  
  if (translate) {
    args.push('-tr');
  }
  
  // 添加输出格式参数
  if (outputFormat === '.srt') {
    args.push('-osrt');
  } else {
    args.push('-otxt');
  }
  
  // 添加额外参数以提高转录质量
  args.push('-pp');        // 打印进度
  args.push('-ml', '1024'); // 增加最大段落长度
  
  const stdoutChunks = [];
  
  return new Promise((resolve, reject) => {
    try {
      log.info(`运行转录命令: ${whisperPath} ${args.join(' ')}`);
      currentProcess = spawn(whisperPath, args);
      
      currentProcess.stdout.on('data', (data) => {
        const output = data.toString();
        stdoutChunks.push(output);
        
        // 解析进度信息并发送到渲染进程
        const progressMatch = output.match(/(\d+)%\|/);
        if (progressMatch && progressMatch[1]) {
          const progress = parseInt(progressMatch[1]);
          mainWindow.webContents.send('transcription-progress', progress);
        }
        
        // 解析时间戳和文本
        const lines = output.split('\n');
        for (const line of lines) {
          if (line.includes('[')) {
            mainWindow.webContents.send('transcription-line', line);
          }
        }
      });
      
      currentProcess.stderr.on('data', (data) => {
        const stderr = data.toString();
        log.warn(`stderr: ${stderr}`);
        // 有些版本会在stderr输出进度信息
        const progressMatch = stderr.match(/(\d+)%\|/);
        if (progressMatch && progressMatch[1]) {
          const progress = parseInt(progressMatch[1]);
          mainWindow.webContents.send('transcription-progress', progress);
        }
      });
      
      currentProcess.on('close', (code) => {
        currentProcess = null;
        
        if (shouldStop) {
          reject(new Error('转录已取消'));
          return;
        }
        
        if (code !== 0) {
          reject(new Error(`转录进程退出，代码 ${code}`));
          return;
        }
        
        // 从输出文件读取结果
        if (fs.existsSync(tempOutputFile)) {
          try {
            const fileContent = fs.readFileSync(tempOutputFile, 'utf8');
            log.info(`从文件读取转录结果: ${tempOutputFile}, 大小: ${fileContent.length}`);
            
            // 解析结果
            const result = parseFileContent(fileContent, outputFormat);
            
            // 如果启用了VAD，处理静音区间
            if (enableVad) {
              const vadResult = processVadFiltering(result, vadThreshold);
              resolve(vadResult);
            } else {
              resolve(result);
            }
          } catch (err) {
            log.error(`读取输出文件失败: ${err.message}`);
            // 如果读取文件失败，尝试从stdout解析
            const fullOutput = stdoutChunks.join('');
            const result = parseTranscription(fullOutput, outputFormat);
            
            // 如果启用了VAD，处理静音区间
            if (enableVad) {
              const vadResult = processVadFiltering(result, vadThreshold);
              resolve(vadResult);
            } else {
              resolve(result);
            }
          }
        } else {
          log.warn(`输出文件不存在: ${tempOutputFile}`);
          // 从stdout解析
          const fullOutput = stdoutChunks.join('');
          const result = parseTranscription(fullOutput, outputFormat);
          
          // 如果启用了VAD，处理静音区间
          if (enableVad) {
            const vadResult = processVadFiltering(result, vadThreshold);
            resolve(vadResult);
          } else {
            resolve(result);
          }
        }
      });
      
      currentProcess.on('error', (err) => {
        log.error('启动转录进程时出错:', err);
        currentProcess = null;
        reject(err);
      });
    } catch (error) {
      log.error('运行转录时出错:', error);
      reject(error);
    }
  });
});

// 停止转录
ipcMain.handle('stop-transcription', () => {
  if (currentProcess) {
    shouldStop = true;
    
    if (process.platform === 'win32') {
      exec(`taskkill /pid ${currentProcess.pid} /T /F`);
    } else {
      currentProcess.kill('SIGTERM');
    }
    
    log.info('转录已停止');
    return true;
  }
  return false;
});

// 解析转录结果
function parseTranscription(output, outputFormat) {
  const lines = output.split('\n');
  const transcription = [];
  let currentEntry = null;
  
  for (const line of lines) {
    // 解析时间戳行
    if (line.includes('[') && line.includes(']')) {
      const timestampMatch = line.match(/\[(\d{2}):(\d{2})\.(\d{3}) --> (\d{2}):(\d{2})\.(\d{3})\]/);
      if (timestampMatch) {
        // 保存前一个条目
        if (currentEntry) {
          // 只有当有文本内容时才添加条目
          if (currentEntry.text && currentEntry.text.trim() !== '') {
            transcription.push(currentEntry);
          }
        }
        
        // 创建新条目
        const startMinutes = parseInt(timestampMatch[1]);
        const startSeconds = parseInt(timestampMatch[2]);
        const startMillis = parseInt(timestampMatch[3]);
        const endMinutes = parseInt(timestampMatch[4]);
        const endSeconds = parseInt(timestampMatch[5]);
        const endMillis = parseInt(timestampMatch[6]);
        
        const startTime = startMinutes * 60 + startSeconds + startMillis / 1000;
        const endTime = endMinutes * 60 + endSeconds + endMillis / 1000;
        
        const textContent = line.split(']')[1].trim();
        
        // 确保文本不为空并且不仅包含空白字符
        if (!textContent || textContent === '') {
          currentEntry = null;
          continue;
        }
        
        currentEntry = {
          startTime,
          endTime,
          text: textContent
        };
      }
    } 
    // 追加多行文本
    else if (currentEntry && line.trim() !== '') {
      currentEntry.text += ' ' + line.trim();
    }
  }
  
  // 添加最后一个条目（如果有内容）
  if (currentEntry && currentEntry.text && currentEntry.text.trim() !== '') {
    transcription.push(currentEntry);
  }
  
  return transcription;
}

// 新增保存转录结果的处理函数
ipcMain.handle('save-transcription', async (event, { transcription, outputPath, format }) => {
  try {
    let content = '';
    
    if (!transcription || transcription.length === 0) {
      log.warn('保存转录结果：收到空的转录内容');
      throw new Error('转录内容为空');
    }
    
    log.info(`保存转录结果到: ${outputPath}, 格式: ${format}, 条目数: ${transcription.length}`);
    
    if (format === '.srt') {
      // SRT 格式
      content = formatSRT(transcription);
    } else {
      // 纯文本格式
      content = formatTXT(transcription);
    }
    
    if (!content || content.trim() === '') {
      log.warn('格式化后的内容为空');
      throw new Error('格式化转录内容失败，结果为空');
    }
    
    log.info(`写入文件，内容长度: ${content.length}`);
    fs.writeFileSync(outputPath, content, 'utf8');
    log.info(`转录结果已保存到: ${outputPath}`);
    
    return { success: true, path: outputPath };
  } catch (error) {
    log.error('保存转录结果失败:', error);
    throw error;
  }
});

// 格式化为SRT
function formatSRT(transcription) {
  // 确保转录按时间顺序排序
  transcription.sort((a, b) => a.startTime - b.startTime);
  
  let srtContent = '';
  
  // 添加序号，时间戳和文本
  transcription.forEach((entry, index) => {
    // 确保相邻条目之间有间隔（至少0.2秒）
    if (index > 0) {
      const prevEntry = transcription[index - 1];
      const gap = entry.startTime - prevEntry.endTime;
      if (gap < 0.2) {
        prevEntry.endTime = Math.max(prevEntry.startTime + 0.1, entry.startTime - 0.2);
      }
    }
    
    // 序号
    srtContent += (index + 1) + '\n';
    
    // 时间戳
    const startTime = formatSRTTimestamp(entry.startTime);
    const endTime = formatSRTTimestamp(entry.endTime);
    srtContent += `${startTime} --> ${endTime}\n`;
    
    // 文本
    srtContent += entry.text + '\n\n';
  });
  
  return srtContent;
}

// 格式化为纯文本
function formatTXT(transcription) {
  let txtContent = '';
  
  transcription.forEach(entry => {
    txtContent += entry.text + '\n';
  });
  
  return txtContent;
}

// 格式化SRT时间戳
function formatSRTTimestamp(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  const millis = Math.floor((seconds % 1) * 1000);
  
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')},${String(millis).padStart(3, '0')}`;
}

// 解析文件内容
function parseFileContent(content, format) {
  if (!content || content.trim() === '') {
    log.warn('输出文件内容为空');
    return [];
  }
  
  if (format === '.srt') {
    return parseSRTContent(content);
  } else {
    return parseTXTContent(content);
  }
}

// 解析SRT格式
function parseSRTContent(content) {
  const lines = content.split('\n');
  const result = [];
  let currentEntry = null;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // 序号行
    if (/^\d+$/.test(line)) {
      // 保存前一个条目
      if (currentEntry && currentEntry.text && currentEntry.text.trim() !== '') {
        result.push(currentEntry);
      }
      
      currentEntry = {
        startTime: 0,
        endTime: 0,
        text: ''
      };
      continue;
    }
    
    // 时间戳行
    if (line.includes('-->') && currentEntry) {
      const times = line.split('-->').map(t => t.trim());
      if (times.length === 2) {
        currentEntry.startTime = convertTimeToSeconds(times[0]);
        currentEntry.endTime = convertTimeToSeconds(times[1]);
      }
      continue;
    }
    
    // 文本行
    if (line !== '' && currentEntry) {
      if (currentEntry.text) {
        currentEntry.text += ' ' + line;
      } else {
        currentEntry.text = line;
      }
    }
  }
  
  // 保存最后一个条目
  if (currentEntry && currentEntry.text && currentEntry.text.trim() !== '') {
    result.push(currentEntry);
  }
  
  return result;
}

// 解析TXT格式
function parseTXTContent(content) {
  const lines = content.split('\n');
  const result = [];
  
  if (lines.length > 0) {
    // 简单处理：所有文本作为一个条目
    result.push({
      startTime: 0,
      endTime: 60, // 假设60秒
      text: content.trim()
    });
  }
  
  return result;
}

// 将SRT时间格式转换为秒
function convertTimeToSeconds(timeString) {
  const parts = timeString.split(',');
  const timeParts = parts[0].split(':');
  const hours = parseInt(timeParts[0]);
  const minutes = parseInt(timeParts[1]);
  const seconds = parseInt(timeParts[2]);
  const milliseconds = parseInt(parts[1]);
  
  return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
}

// 处理VAD过滤
function processVadFiltering(transcription, vadThreshold) {
  // 如果没有启用VAD或没有条目，直接返回
  if (!transcription || transcription.length === 0) {
    return transcription;
  }
  
  const filteredTranscription = [];
  const threshold = vadThreshold || 0.5; // 默认阈值为0.5
  
  // 第一步：根据语音密度过滤条目
  const densityFilteredEntries = [];
  
  for (const entry of transcription) {
    // 如果文本内容为空，直接跳过
    if (!entry.text || entry.text.trim() === '') {
      continue;
    }
    
    // 自定义评分机制：根据文本长度和持续时间计算"语音密度"
    const duration = entry.endTime - entry.startTime;
    const textLength = entry.text.trim().length;
    
    // 计算语音密度（每秒字符数）
    const speechDensity = textLength / duration;
    
    // 如果语音密度大于或等于阈值的话，保留这个字幕条目
    if (duration > 0 && (speechDensity >= threshold * 2 || textLength > threshold * 10)) {
      densityFilteredEntries.push(entry);
    }
  }
  
  // 如果过滤后为空，返回原始转录（避免全部被过滤掉）
  if (densityFilteredEntries.length === 0) {
    log.warn('所有字幕条目都被VAD过滤掉了，返回原始转录');
    return transcription;
  }
  
  // 第二步：确保条目之间有间隔（防止字幕连在一起）
  for (let i = 0; i < densityFilteredEntries.length; i++) {
    const currentEntry = densityFilteredEntries[i];
    
    // 检查和上一个条目的间隔
    if (i > 0) {
      const prevEntry = filteredTranscription[filteredTranscription.length - 1];
      const gap = currentEntry.startTime - prevEntry.endTime;
      
      // 如果两个条目之间的间隔小于阈值，调整时间戳
      const minGap = 0.3; // 最小间隔，单位为秒
      if (gap < minGap) {
        // 在两个条目之间创建间隔
        prevEntry.endTime = currentEntry.startTime - minGap;
        
        // 确保结束时间不小于开始时间
        if (prevEntry.endTime < prevEntry.startTime) {
          prevEntry.endTime = prevEntry.startTime + 0.1;
        }
      }
    }
    
    // 确保每个条目的持续时间不要太长
    // 中文平均阅读速度约每秒4-6个字，我们设定最大持续时间为每5个字1秒
    const maxDuration = Math.max(currentEntry.text.trim().length / 5, 1); // 最少1秒
    const actualDuration = currentEntry.endTime - currentEntry.startTime;
    
    if (actualDuration > maxDuration * 1.5) {
      currentEntry.endTime = currentEntry.startTime + maxDuration;
    }
    
    filteredTranscription.push(currentEntry);
  }
  
  return filteredTranscription;
} 