// DOM 元素
const audioFileInput = document.getElementById('audio-file');
const browseFileBtn = document.getElementById('browse-file');
const modelPathSelect = document.getElementById('model-path');
const browseModelBtn = document.getElementById('browse-model');
const languageSelect = document.getElementById('language');
const translateCheckbox = document.getElementById('translate');
const enableVadCheckbox = document.getElementById('enable-vad');
const vadThresholdInput = document.getElementById('vad-threshold');
const vadThresholdValue = document.getElementById('vad-threshold-value');
const vadThresholdContainer = document.getElementById('vad-threshold-container');
const outputDirInput = document.getElementById('output-dir');
const browseOutputBtn = document.getElementById('browse-output');
const outputFormatRadios = document.getElementsByName('output-format');
const progressBar = document.querySelector('.progress-fill');
const progressText = document.querySelector('.progress-text');
const startButton = document.getElementById('start-button');
const stopButton = document.getElementById('stop-button');
const transcriptPreview = document.getElementById('transcript-preview');

// 创建状态消息元素
const statusContainer = document.createElement('div');
statusContainer.className = 'status-container';
document.querySelector('.progress-container').after(statusContainer);

// 应用状态
let audioFile = '';
let outputPath = '';
let isTranscribing = false;
let transcriptionLines = [];

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
  await loadSettings();
  setupEventListeners();
});

// 加载设置
async function loadSettings() {
  try {
    const settings = await window.api.getSettings();
    
    // 填充模型下拉列表
    if (settings.modelPaths && settings.modelPaths.length > 0) {
      modelPathSelect.innerHTML = '';
      const defaultOption = document.createElement('option');
      defaultOption.value = '';
      defaultOption.textContent = '-- 选择模型文件 --';
      modelPathSelect.appendChild(defaultOption);
      
      settings.modelPaths.forEach(path => {
        const option = document.createElement('option');
        option.value = path;
        option.textContent = getFileName(path);
        modelPathSelect.appendChild(option);
      });
      
      // 设置上次选择的模型
      if (settings.lastModelPath) {
        modelPathSelect.value = settings.lastModelPath;
      }
    }
    
    // 设置输出目录
    if (settings.lastOutputDir) {
      outputDirInput.value = settings.lastOutputDir;
      outputPath = settings.lastOutputDir;
    }
    
    // 设置输出格式
    if (settings.lastOutputFormat) {
      for (const radio of outputFormatRadios) {
        if (radio.value === settings.lastOutputFormat) {
          radio.checked = true;
          break;
        }
      }
    }
    
    // 设置VAD选项
    if (settings.hasOwnProperty('enableVad')) {
      enableVadCheckbox.checked = settings.enableVad;
      vadThresholdContainer.style.display = settings.enableVad ? 'block' : 'none';
    }
    
    if (settings.hasOwnProperty('vadThreshold')) {
      const threshold = settings.vadThreshold * 100;
      vadThresholdInput.value = threshold;
      vadThresholdValue.textContent = settings.vadThreshold.toFixed(2);
    }
  } catch (error) {
    showError('加载设置失败: ' + error.message);
  }
}

// 保存设置
async function saveSettings() {
  try {
    const outputFormat = getSelectedOutputFormat();
    const vadThreshold = parseFloat(vadThresholdInput.value) / 100;
    
    await window.api.saveSettings({
      lastModelPath: modelPathSelect.value,
      lastOutputFormat: outputFormat,
      lastOutputDir: outputPath,
      enableVad: enableVadCheckbox.checked,
      vadThreshold: vadThreshold
    });
  } catch (error) {
    console.error('保存设置失败:', error);
  }
}

// 设置事件监听器
function setupEventListeners() {
  // 浏览文件按钮
  browseFileBtn.addEventListener('click', async () => {
    try {
      const filePath = await window.api.selectFile();
      if (filePath) {
        audioFileInput.value = filePath;
        audioFile = filePath;
      }
    } catch (error) {
      showError('选择文件失败: ' + error.message);
    }
  });
  
  // 浏览模型按钮
  browseModelBtn.addEventListener('click', async () => {
    try {
      const filePath = await window.api.selectModel();
      if (filePath) {
        // 检查是否已存在
        let exists = false;
        for (const option of modelPathSelect.options) {
          if (option.value === filePath) {
            exists = true;
            modelPathSelect.value = filePath;
            break;
          }
        }
        
        // 如果不存在，添加新选项
        if (!exists) {
          const option = document.createElement('option');
          option.value = filePath;
          option.textContent = getFileName(filePath);
          modelPathSelect.appendChild(option);
          modelPathSelect.value = filePath;
        }
        
        saveSettings();
      }
    } catch (error) {
      showError('选择模型失败: ' + error.message);
    }
  });
  
  // 浏览输出目录按钮
  browseOutputBtn.addEventListener('click', async () => {
    try {
      const dirPath = await window.api.selectOutput();
      if (dirPath) {
        outputDirInput.value = dirPath;
        outputPath = dirPath;
        saveSettings();
      }
    } catch (error) {
      showError('选择输出目录失败: ' + error.message);
    }
  });
  
  // 开始转录按钮
  startButton.addEventListener('click', startTranscription);
  
  // 停止转录按钮
  stopButton.addEventListener('click', stopTranscription);
  
  // 输出格式更改时保存设置
  for (const radio of outputFormatRadios) {
    radio.addEventListener('change', saveSettings);
  }
  
  // 设置转录进度监听
  window.api.onTranscriptionProgress(updateProgress);
  
  // 设置转录行监听
  window.api.onTranscriptionLine(addTranscriptionLine);
  
  // VAD启用/禁用切换
  enableVadCheckbox.addEventListener('change', () => {
    vadThresholdContainer.style.display = enableVadCheckbox.checked ? 'block' : 'none';
    saveSettings();
  });
  
  // VAD阈值滑块
  vadThresholdInput.addEventListener('input', () => {
    const value = vadThresholdInput.value / 100;
    vadThresholdValue.textContent = value.toFixed(2);
  });
  
  vadThresholdInput.addEventListener('change', saveSettings);
  
  // 初始化VAD控件状态
  vadThresholdContainer.style.display = enableVadCheckbox.checked ? 'block' : 'none';
}

// 开始转录
async function startTranscription() {
  try {
    // 验证输入
    if (!audioFile) {
      showError('请选择音频或视频文件');
      return;
    }
    
    if (!modelPathSelect.value) {
      showError('请选择模型文件');
      return;
    }
    
    if (!outputPath) {
      showError('请选择输出目录');
      return;
    }
    
    // 更新UI状态
    isTranscribing = true;
    startButton.disabled = true;
    stopButton.disabled = false;
    
    // 清空预览
    transcriptPreview.innerHTML = '';
    transcriptionLines = [];
    updateProgress(0);
    
    // 处理视频文件（如果需要）
    let audioToProcess = audioFile;
    if (isVideoFile(audioFile)) {
      showStatus('正在从视频中提取音频...');
      audioToProcess = await window.api.extractAudio(audioFile);
    }
    
    // 检查音频格式
    showStatus('检查音频格式...');
    const formatInfo = await window.api.checkAudioFormat(audioToProcess);
    
    // 转换到16k采样率（如果需要）
    if (!formatInfo.is16k) {
      showStatus('正在转换音频格式到16kHz...');
      audioToProcess = await window.api.convertTo16k(audioToProcess);
    }
    
    // 准备VAD参数
    const enableVad = enableVadCheckbox.checked;
    const vadThreshold = enableVad ? parseFloat(vadThresholdInput.value) / 100 : 0;
    
    // 获取输出格式
    const outputFormat = getSelectedOutputFormat();
    
    // 获取输出文件名
    const baseFileName = getFileName(audioFile, false);
    const outputFilePath = `${outputPath}/${baseFileName}${outputFormat}`;
    
    // 开始转录
    showStatus('开始转录...');
    const transcription = await window.api.startTranscription({
      audioFile: audioToProcess,
      modelPath: modelPathSelect.value,
      language: languageSelect.value,
      translate: translateCheckbox.checked,
      outputFormat,
      enableVad: enableVad,
      vadThreshold: vadThreshold
    });
    
    // 保存转录结果
    await saveTranscription(transcription, outputFilePath, outputFormat);
    
    // 转录完成
    showStatus('转录完成!');
    updateProgress(100);
    
    // 重置UI状态
    isTranscribing = false;
    startButton.disabled = false;
    stopButton.disabled = true;
    
  } catch (error) {
    isTranscribing = false;
    startButton.disabled = false;
    stopButton.disabled = true;
    
    if (error.message === '转录已取消') {
      showStatus('转录已取消');
    } else {
      showError('转录失败: ' + error.message);
    }
  }
}

// 停止转录
async function stopTranscription() {
  try {
    await window.api.stopTranscription();
    stopButton.disabled = true;
  } catch (error) {
    showError('停止转录失败: ' + error.message);
  }
}

// 更新进度条
function updateProgress(progress) {
  progressBar.style.width = `${progress}%`;
  progressText.textContent = `${progress}%`;
}

// 添加转录行到预览
function addTranscriptionLine(line) {
  transcriptionLines.push(line);
  
  // 解析时间戳和文本
  const timestampMatch = line.match(/\[(\d{2}):(\d{2})\.(\d{3}) --> (\d{2}):(\d{2})\.(\d{3})\]/);
  if (timestampMatch) {
    const startTime = `${timestampMatch[1]}:${timestampMatch[2]}`;
    const textContent = line.split(']')[1].trim();
    
    const entryDiv = document.createElement('div');
    entryDiv.className = 'transcript-entry';
    
    const timestampSpan = document.createElement('span');
    timestampSpan.className = 'timestamp';
    timestampSpan.textContent = startTime;
    
    const textSpan = document.createElement('span');
    textSpan.className = 'text';
    textSpan.textContent = textContent;
    
    entryDiv.appendChild(timestampSpan);
    entryDiv.appendChild(textSpan);
    
    transcriptPreview.appendChild(entryDiv);
    
    // 滚动到底部
    transcriptPreview.scrollTop = transcriptPreview.scrollHeight;
  }
}

// 保存转录结果
async function saveTranscription(transcription, outputFilePath, outputFormat) {
  try {
    const result = await window.api.saveTranscription({
      transcription,
      outputPath: outputFilePath,
      format: outputFormat
    });
    
    if (result.success) {
      showStatus(`转录结果已保存到: ${result.path}`);
    }
  } catch (error) {
    showError('保存转录结果失败: ' + error.message);
  }
}

// 获取文件名
function getFileName(path, withExtension = true) {
  if (!path) return '';
  
  const fileName = path.split(/[\\/]/).pop();
  
  if (withExtension) {
    return fileName;
  }
  
  return fileName.split('.')[0];
}

// 检查是否为视频文件
function isVideoFile(filePath) {
  if (!filePath) return false;
  
  const extension = filePath.split('.').pop().toLowerCase();
  const videoExtensions = ['mp4', 'avi', 'mkv', 'mov', 'flv', 'wmv'];
  
  return videoExtensions.includes(extension);
}

// 获取选中的输出格式
function getSelectedOutputFormat() {
  for (const radio of outputFormatRadios) {
    if (radio.checked) {
      return radio.value;
    }
  }
  return '.srt'; // 默认
}

// 显示状态消息
function showStatus(message) {
  console.log(message);
  
  // 更新UI状态消息
  statusContainer.textContent = message;
  statusContainer.style.color = '';
  statusContainer.style.display = 'block';
  
  // 5秒后自动隐藏成功消息
  if (message.includes('完成') || message.includes('保存')) {
    setTimeout(() => {
      if (statusContainer.textContent === message) {
        statusContainer.style.display = 'none';
      }
    }, 5000);
  }
}

// 显示错误
function showError(message) {
  console.error(message);
  
  // 更新UI状态消息
  statusContainer.textContent = message;
  statusContainer.style.color = 'red';
  statusContainer.style.display = 'block';
  
  // 显示警告对话框
  alert(message);
} 