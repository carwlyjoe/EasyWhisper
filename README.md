# EasyWhisper

一个基于 [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) 的语音转文字工具，提供图形界面，支持多种音视频格式转录。

## 功能特点

- 支持多种格式：
  - 音频：WAV、MP3、M4A、FLAC
  - 视频：MP4、AVI、MKV、MOV
- 支持输出为 SRT 字幕文件或纯文本
- 简单易用的图形界面
- 实时显示转录进度

## 使用前准备

### 1. 安装 FFmpeg

1. 下载并安装 [FFmpeg](https://ffmpeg.org/download.html)
2. 将 FFmpeg 添加到系统环境变量
3. 验证安装是否成功：
   ```bash
   ffmpeg -version
   ```
   如果显示版本信息，则表示安装成功

### 2. 安装 Python

1. 从 [Python 官网](https://www.python.org/downloads/) 下载并安装 Python 3.x
2. 验证安装：
   ```bash
   python --version
   ```
   如果显示版本信息，则表示安装成功

### 3. 下载语音模型

1. 访问 [Whisper.cpp 模型仓库](https://huggingface.co/ggerganov/whisper.cpp/tree/main)
2. 下载所需的 ggml 模型文件
   - 建议新手先尝试 `ggml-base.bin` 或 `ggml-small.bin`
   - 更大的模型（如 medium、large）准确度更高但速度更慢

### 4. 安装 EasyWhisper

1. 克隆仓库：
   ```bash
   git clone https://github.com/carwlyjoe/EasyWhisper.git
   ```

2. 进入项目目录：
   ```bash
   cd EasyWhisper
   ```

3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
   国内用户可使用镜像加速：
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

## 使用方法

1. 双击运行 `启动.bat`
2. 在打开的界面中：
   - 选择要转录的音频或视频文件
   - 选择下载好的模型文件
   - 设置输出文件的保存位置和格式
3. 点击"开始转录"
4. 等待进度条完成即可获得转录结果

## 界面预览

![EasyWhisper 界面](https://github.com/user-attachments/assets/76ceecff-0c5b-4fc8-ae36-2acd33ad2c0e)

## 注意事项

- 首次使用前请确保：
  - FFmpeg 已正确添加到系统环境变量
  - 已下载语音模型文件
- 转录速度受以下因素影响：
  - 选择的模型大小
  - 计算机性能
  - 音视频文件长度

## 问题反馈

如有问题或建议，欢迎在 GitHub Issues 中提出。
