import tkinter as tk
from tkinter import ttk, filedialog, messagebox, StringVar, BooleanVar
import subprocess
import json
import os
import threading
from tqdm import tqdm
from zhconv import convert
import sys
import queue
import time
from PyQt5.QtWidgets import QMainWindow, QAction, QMenu
from PyQt5.QtCore import QTimer
from updater import Updater
import logging
import traceback
import tempfile
import platform
# 在文件开头定义全局变量
audio_file_var = None
model_path_var = None
language_var = None
translate_var = None
output_path_var = None
progress_bar = None
start_button = None
stop_button = None
root = None
current_process = None  # 添加这行
should_stop = False

# 定义全局 languages 字典
languages = {
    "中文 (zh)": "zh",
    "英语 (en)": "en",
    "日语 (ja)": "ja",
    "韩语 (ko)": "ko",
    "法语 (fr)": "fr",
    "德语 (de)": "de",
    "西班牙语 (es)": "es",
    "意大利语 (it)": "it",
    "俄语 (ru)": "ru",
    "葡萄牙语 (pt)": "pt",
    "荷兰语 (nl)": "nl",
    "波兰语 (pl)": "pl",
    "土耳其语 (tr)": "tr",
    "阿拉伯语 (ar)": "ar",
    "印地 (hi)": "hi",
    "泰语 (th)": "th",
    "越南语 (vi)": "vi",
    "印尼语 (id)": "id",
    "马来语 (ms)": "ms",
    "希腊语 (el)": "el",
    "瑞典语 (sv)": "sv",
    "捷克语 (cs)": "cs",
    "丹麦语 (da)": "da",
    "芬兰语 (fi)": "fi"
}

def get_app_path():
    """获取应用程序路径"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_bin_path():
    """获取bin目录的路径"""
    return os.path.join(get_app_path(), 'bin')

def get_model_path():
    """获取model目录的路径"""
    return os.path.join(get_app_path(), 'model')

##打包相关
def resource_path(relative_path):
    """获取资源的绝对路径"""
    try:
        if hasattr(sys, '_MEIPASS'):
            # 打包后的环境
            base_path = sys._MEIPASS
            # 检查是否在 _internal 目录中
            internal_path = os.path.join(base_path, '_internal', os.path.basename(relative_path))
            if os.path.exists(internal_path):
                logging.info(f"在 _internal 中找到文件: {internal_path}")
                return internal_path
                
            # 检查是否在 bin 目录中
            bin_path = os.path.join(os.path.dirname(sys.executable), 'bin', os.path.basename(relative_path))
            if os.path.exists(bin_path):
                logging.info(f"在 bin 中找到文件: {bin_path}")
                return bin_path
                
            # 检查基础路径
            base_file = os.path.join(base_path, os.path.basename(relative_path))
            if os.path.exists(base_file):
                logging.info(f"在基础路径中找到文件: {base_file}")
                return base_file
                
            logging.error(f"找不到文件: {relative_path}")
            logging.error(f"已检查路径: {internal_path}, {bin_path}, {base_file}")
            return None
            
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if 'ffmpeg.exe' in relative_path or 'ffprobe.exe' in relative_path:
                full_path = os.path.join(base_path, 'bin', os.path.basename(relative_path))
            elif relative_path.startswith('model'):
                full_path = os.path.join(base_path, relative_path)
            else:
                full_path = os.path.join(base_path, os.path.basename(relative_path))
                
            logging.info(f"开发环境中的文件路径: {full_path}")
            return full_path
            
    except Exception as e:
        logging.error(f"解析资源路径时出错: {e}", exc_info=True)
        return None

def get_ffmpeg_path():
    """获取ffmpeg可执行文件的路径，优先使用环境变量中的ffmpeg"""
    try:
        # 首先检查环境变量
        if os.name == 'nt':  # Windows
            ffmpeg_cmd = 'where ffmpeg'
        else:  # Unix/Linux/Mac
            ffmpeg_cmd = 'which ffmpeg'
            
        result = subprocess.run(ffmpeg_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            ffmpeg_path = result.stdout.strip().split('\n')[0]
            logging.info(f"从环境变量找到ffmpeg: {ffmpeg_path}")
            return ffmpeg_path
            
        # 如果环境变量中没有找到，则使用bin目录中的ffmpeg
        ffmpeg_path = resource_path("ffmpeg.exe")
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            logging.info(f"使用bin目录中的ffmpeg: {ffmpeg_path}")
            return ffmpeg_path
            
        logging.error("未找到ffmpeg")
        return None
        
    except Exception as e:
        logging.error(f"获取ffmpeg路径时出错: {e}")
        return None

def get_ffprobe_path():
    """获取ffprobe可执行文件的路径，优先使用环境变量中的ffprobe"""
    try:
        # 首先检查环境变量
        if os.name == 'nt':  # Windows
            ffprobe_cmd = 'where ffprobe'
        else:  # Unix/Linux/Mac
            ffprobe_cmd = 'which ffprobe'
            
        result = subprocess.run(ffprobe_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            ffprobe_path = result.stdout.strip().split('\n')[0]
            logging.info(f"从环境变量找到ffprobe: {ffprobe_path}")
            return ffprobe_path
            
        # 如果环境变量中没有找到，则使用bin目录中的ffprobe
        ffprobe_path = resource_path("ffprobe.exe")
        if ffprobe_path and os.path.exists(ffprobe_path):
            logging.info(f"使用bin目录中的ffprobe: {ffprobe_path}")
            return ffprobe_path
            
        logging.error("未找到ffprobe")
        return None
        
    except Exception as e:
        logging.error(f"获取ffprobe路径时出错: {e}")
        return None

def check_audio_format(audio_file):
    """检测音频文件格式和采样率"""
    try:
        ffprobe_path = get_ffprobe_path()
        if not ffprobe_path:
            logging.error("找不到ffprobe")
            return False
            
        cmd = [ffprobe_path, "-v", "error", "-show_entries", 
               "stream=sample_rate", "-of", "default=noprint_wrappers=1", audio_file]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        sample_rate = int(result.stdout.strip().split('=')[-1])
        return sample_rate == 16000
    except Exception as e:
        logging.error(f"检测音频格式出错：{e}")
        return False
    

def convert_to_16k_wav(audio_file):
    """使用 FFmpeg 将音频转换为 16kHz WAV"""
    try:
        # 规范化音频文件路径
        audio_file = os.path.normpath(audio_file)
        
        # 获取并检查 ffmpeg 路径
        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            logging.error("找不到 ffmpeg")
            return None
            
        logging.info(f"当前工作目录: {os.getcwd()}")
        logging.info(f"FFmpeg 路径: {ffmpeg_path}")
        logging.info(f"FFmpeg 是否存在: {os.path.exists(ffmpeg_path)}")
        
        # 在系统临时目录生成临时文件
        temp_file = os.path.join(
            tempfile.gettempdir(), 
            f"whisper_temp_{int(time.time())}_{os.path.basename(audio_file)}_16k.wav"
        )
        temp_file = os.path.normpath(temp_file)
        
        cmd = [
            ffmpeg_path,
            "-i", audio_file,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-y",
            temp_file
        ]
        
        logging.info(f"执行转换命令: {' '.join(cmd)}")
        logging.info(f"输入文件是否存在: {os.path.exists(audio_file)}")
        logging.info(f"临时文件路径: {temp_file}")
        
        # 执行转换命令
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logging.error(f"FFmpeg 错误输出: {result.stderr}")
            return None
        
        if os.path.exists(temp_file):
            logging.info(f"音频转换成功: {temp_file}")
            return temp_file
        else:
            logging.error(f"音频转换失败: 未生成临时文件")
            return None
            
    except Exception as e:
        logging.error(f"音频转换出错", exc_info=True)
        return None

def parse_progress(line):
    """解析 whisper.cpp 的输出来获取进度"""
    if "whisper_full" in line:
        try:
            # whisper.cpp 输出格式类似：whisper_full: progress = XX% / XX tokens
            progress = float(line.split("progress = ")[1].split("%")[0])
            return progress
        except:
            return None
    return None

def get_audio_duration(audio_file):
    """获取音频文件总时长（秒）"""
    try:
        cmd = [resource_path("ffprobe.exe"), "-v", "error", "-show_entries", 
               "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"获取音频时长失败：{e}")
        return 0

def parse_timestamp(line):
    """解析whisper.cpp输出中的时间戳"""
    try:
        if "[" in line and "]" in line:
            # 时间戳格式通常类似 [00:00.000 --> 00:00.000]
            timestamp = line.split("[")[1].split("]")[0].split("-->")[0].strip()
            # 将戳转换为秒
            minutes, seconds = timestamp.split(":")
            total_seconds = float(minutes) * 60 + float(seconds)
            return total_seconds
    except Exception as e:
        return None
    return None




def run_whisper_cpp(audio_file, model_path, language, translate, output_format):
    """调用 Whisper.cpp 运行模型并保存输出"""
    global current_process, should_stop
    should_stop = False  # 重置停止标志
    
    def process_whisper():
        json_file_path = None
        result = None
        error_info = None  # 添加错误信息变量
        
        try:
            check_dll_loading()
            
            # 切换到 bin 目录
            bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin')
            os.chdir(bin_dir)
            print(f"当前工作目录: {os.getcwd()}")

            os.environ['PATH'] = f"{bin_dir};{os.environ.get('PATH', '')}"
        
        # 打印当前PATH环境变量
            logging.info(f"当前PATH环境变量: {os.environ['PATH']}")
            
            # 规范化路径
            audio_file_norm = os.path.normpath(audio_file)
            
            # 处理模型路径 - 使用绝对路径
            if not os.path.isabs(model_path):
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                model_path_norm = os.path.normpath(os.path.join(project_root, model_path))
            else:
                model_path_norm = os.path.normpath(model_path)
            
            print(f"检查模型文件: {model_path_norm}")
            print(f"模型文件是否存在: {os.path.exists(model_path_norm)}")
            
            if os.path.exists(model_path_norm):
                print(f"模型目录内容: {os.listdir(os.path.dirname(model_path_norm))}")
            else:
                print("模型文件不存在，尝试其他位置...")
                # 尝试其他可能的位
                possible_paths = [
                    os.path.join(project_root, 'model', os.path.basename(model_path)),
                    os.path.join(bin_dir, 'model', os.path.basename(model_path)),
                    os.path.join(project_root, os.path.basename(model_path)),
                    os.path.join(bin_dir, os.path.basename(model_path))
                ]
                for path in possible_paths:
                    print(f"检查路径: {path}")
                    if os.path.exists(path):
                        model_path_norm = path
                        print(f"找到模型文件: {path}")
                        break
            
            if not os.path.exists(model_path_norm):
                print("错误：无法找到模型文件")
                return None
            
            print(f"最终使用的模型路径: {model_path_norm}")
            print(f"检查音频文件: {audio_file_norm}")
            print(f"音频文件是否存在: {os.path.exists(audio_file_norm)}")
            
            # 生成输出JSON路径
            audio_dir = os.path.dirname(audio_file_norm)
            audio_filename = os.path.basename(audio_file_norm)
            json_file_path = os.path.join(audio_dir, f"{audio_filename}.json")
            
            cmd = [
                os.path.join(bin_dir, "main.exe"),
                "-m", model_path_norm,
                "-f", audio_file_norm,
                "--output-json", json_file_path,
                "-l", languages[language],
                "--print-progress",
                "-ml", "60"
            ]
            
            print(f"执行命令: {' '.join(cmd)}")
            
            # 创建进程时确保stderr是PIPE
            current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1,
                universal_newlines=True,
                cwd=bin_dir,
                env=os.environ.copy(),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
                    # 立即检查进程状态
            time.sleep(0.1)
            if current_process.poll() is not None:
                error_code = current_process.returncode
                error_output = current_process.stderr.read() if current_process.stderr else ""
                output = current_process.stdout.read() if current_process.stdout else ""
                
                error_info = {
                    'code': error_code,
                    'stdout': output,
                    'stderr': error_output,
                    'command': cmd,
                    'working_dir': bin_dir,
                    'system_info': platform.uname()._asdict()
                }
                
                logging.error(f"进程异常退出: {error_info}")
                return None, error_info
            # 收集所有输出信息
            stdout_data = []
            stderr_data = []
            
            def read_stderr():
                while current_process and current_process.poll() is None and not should_stop:
                    line = current_process.stderr.readline()
                    if line:
                        stderr_data.append(line)  # 保存错误输出
                        print(f"Whisper stderr: {line.strip()}")
                        if "progress =" in line:
                            try:
                                progress = float(line.split("progress =")[1].strip().replace('%', ''))
                                root.after(1, lambda p=progress: progress_bar.configure(value=min(p, 100)))
                            except Exception as e:
                                print(f"解析进度失败: {e}")
            
            def read_stdout():
                while current_process and current_process.poll() is None and not should_stop:
                    line = current_process.stdout.readline()
                    if line:
                        stdout_data.append(line)  # 保存标准输出
                        print(f"Whisper stdout: {line.strip()}")
            
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stdout_thread = threading.Thread(target=read_stdout, daemon=True)
            
            stderr_thread.start()
            stdout_thread.start()
            
            # 等待进程完成或被停止
            while current_process and current_process.poll() is None and not should_stop:
                time.sleep(0.1)
            
            if should_stop:
                print("检测到停止信号，正在终止进程...")
                current_process.terminate()
                try:
                    current_process.wait(timeout=5)
                except:
                    current_process.kill()
                return None, None
            
            stderr_thread.join(timeout=1)
            stdout_thread.join(timeout=1)
            
            print(f"进程已结束，返回码: {current_process.returncode}")
            
            if current_process.returncode != 0:
                error_info = {
                    'returncode': current_process.returncode,
                    'stdout': ''.join(stdout_data),
                    'stderr': ''.join(stderr_data)
                }
                logging.error(f"进程异常退出，返回码: {current_process.returncode}")
                logging.error(f"标准输出: {error_info['stdout']}")
                logging.error(f"错误输出: {error_info['stderr']}")
                return None, error_info
            
            # 读取JSON文件
            if os.path.exists(json_file_path):
                try:
                    with open(json_file_path, "r", encoding="utf-8") as f:
                        result = json.load(f)
                    logging.info("JSON文件读取成功")
                except Exception as e:
                    error_info = {
                        'error': str(e),
                        'traceback': traceback.format_exc()
                    }
                    logging.error(f"读取JSON文件失败: {e}")
                    result = None
            else:
                error_info = {'error': f"未找到JSON文件: {json_file_path}"}
                logging.error(f"未找到JSON文件: {json_file_path}")
                result = None
                
        except Exception as e:
            error_info = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            logging.error(f"处理过程出错: {e}")
            logging.error(f"错误详情: {traceback.format_exc()}")
            result = None
            
        finally:
            # 清理临时文件
            if json_file_path and os.path.exists(json_file_path):
                try:
                    os.remove(json_file_path)
                    logging.info(f"已删除JSON文件: {json_file_path}")
                except Exception as e:
                    logging.error(f"删除JSON文件失败: {e}")
            
            return result, error_info
    
    # 执行处理并返回结果
    return process_whisper()

def format_timestamp(seconds):
    """将秒数转换为 SRT 时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds % 1) * 1000)
    seconds = int(seconds)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def save_transcription(transcription, output_file):
    try:
        ext = os.path.splitext(output_file)[1].lower()
        content = ""
        
        if isinstance(transcription, dict):
            segments = transcription.get('transcription', [])
        elif isinstance(transcription, list):
            segments = transcription
        else:
            segments = []
            
        logging.debug(f"转录段落数量: {len(segments)}")
        
        if ext == '.srt':
            for i, segment in enumerate(segments, 1):
                # 从新的 JSON 结构中获取时间戳
                timestamps = segment.get('timestamps', {})
                start_time = timestamps.get('from', '00:00:00,000')
                end_time = timestamps.get('to', '00:00:00,000')
                                
                text = convert(segment.get('text', '').strip(), 'zh-cn')
                content += f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
                
                
        elif ext == '.txt':
            # 纯文本格式，将所有文本转换为简体
            content = "\n".join(convert(segment.get('text', '').strip(), 'zh-cn') 
                              for segment in segments)
                              
        else:
            # JSON 格式，转换所有文本为简体
            simplified_segments = []
            for segment in segments:
                simplified_segment = segment.copy()
                simplified_segment['text'] = convert(segment.get('text', ''), 'zh-cn')
                simplified_segments.append(simplified_segment)
            content = json.dumps({'transcription': simplified_segments}, 
                               ensure_ascii=False, indent=2)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logging.info(f"转录结果已保存到: {output_file}")
        
    except Exception as e:
        logging.error(f"保存文件时出错", exc_info=True)
        messagebox.showerror("错误", f"保存文件时出错: {str(e)}")

def check_dll_loading():
    """详细检查DLL加载情况"""
    import ctypes
    from ctypes import wintypes, get_last_error
    
    bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin')
    dlls_to_check = ['vcruntime140.dll', 'msvcp140.dll']
    
    for dll_name in dlls_to_check:
        try:
            # 首先检查bin目录中是否存在该DLL
            dll_path = os.path.join(bin_dir, dll_name)
            if os.path.exists(dll_path):
                logging.info(f"在bin目录找到 {dll_name}")
            else:
                logging.warning(f"bin目录中未找到 {dll_name}")
                continue
                
            # 尝试直接加载bin目录中的DLL
            try:
                dll = ctypes.CDLL(dll_path)
                logging.info(f"成功加载 {dll_path}")
            except Exception as e:
                error_code = get_last_error()
                logging.error(f"加载 {dll_path} 失败: {e} (错误码: {error_code})")
                
            # 尝试通过LoadLibrary加载
            try:
                handle = ctypes.windll.kernel32.LoadLibraryW(dll_path)
                if handle:
                    path_buffer = ctypes.create_unicode_buffer(1024)
                    ctypes.windll.kernel32.GetModuleFileNameW(handle, path_buffer, 1024)
                    actual_path = path_buffer.value
                    logging.info(f"{dll_name} 实际加载位置: {actual_path}")
                else:
                    error_code = get_last_error()
                    logging.error(f"LoadLibrary失败 {dll_name}: 错误码 {error_code}")
            except Exception as e:
                logging.error(f"检查 {dll_name} 加载位置时出错: {e}")
                
        except Exception as e:
            logging.error(f"处理 {dll_name} 时出错: {e}")
            
    # 列出bin目录中的所有文件
    try:
        files = os.listdir(bin_dir)
        logging.info(f"bin目录内容: {files}")
    except Exception as e:
        logging.error(f"无法列出bin目录内容: {e}")

def stop_transcription():
    """停止转录"""
    global current_process, should_stop
    try:
        should_stop = True  # 设置停止标志
        print("正在停止转录...")
        
        if current_process:
            print(f"正在终止进程 PID: {current_process.pid}")
            current_process.terminate()
            try:
                current_process.wait(timeout=5)
            except:
                current_process.kill()
            
            current_process = None
            
            # 重置界面
            start_button['state'] = 'normal'
            stop_button['state'] = 'disabled'
            progress_bar['value'] = 0
            root.update_idletasks()
            
            # 清理临时文件
            try:
                audio_file = audio_file_var.get()
                json_file = f"{audio_file}.json"
                if os.path.exists(json_file):
                    os.remove(json_file)
                    print(f"已删除临时JSON文件: {json_file}")
            except Exception as e:
                print(f"清理临时文件失败: {e}")
            
            messagebox.showinfo("提示", "转录已停止")
            
    except Exception as e:
        print(f"停止转录失败: {e}")
        messagebox.showerror("错误", f"停止转录失败: {e}")

def start_transcription_thread():
    """启动后台线程进行转录"""
    start_button['state'] = 'disabled'  # 禁用开始按钮
    stop_button['state'] = 'normal'     # 启用停止按钮
    threading.Thread(target=start_transcription).start()

def start_transcription():
    """开始转录"""
    global current_process, should_stop
    temp_audio = None
    
    try:
        input_file = audio_file_var.get()
        if not input_file:
            logging.error("未选择输入文件")
            messagebox.showerror("错误", "请选择输入文件")
            return False
            
        logging.info(f"开始处理文件: {input_file}")
            
        # 检查是否是视频文件
        if input_file.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
            logging.info("检测到视频文件，开始提取音频")
            temp_audio = extract_audio_from_video(input_file)
            if not temp_audio:
                logging.error("从视频提取音频失败")
                messagebox.showerror("错误", "从视频提取音频失败")
                return False
            input_file = temp_audio
            
        # 检查音频格式
        if not check_audio_format(input_file):
            logging.info("音频格式不符合要求，开始转换...")
            temp_audio = convert_to_16k_wav(input_file)
            if not temp_audio:
                logging.error("音频转换失败")
                root.after(0, lambda: messagebox.showerror("错误", "音频转换失败"))
                root.after(0, lambda: reset_buttons())
                return False
            logging.info(f"使用转换后的临时文件: {temp_audio}")
            audio_file_to_use = temp_audio
        else:
            audio_file_to_use = input_file
            
        # 从输出文件扩展名判断格式
        output_format = os.path.splitext(output_path_var.get())[1].lower()
        logging.info(f"输出格式: {output_format}")
        
        # 重置进度条
        root.after(0, lambda: update_progress_bar(0))
        
        # 运行转录
        logging.info("开始转录...")
        result, error_info = run_whisper_cpp(audio_file_to_use, model_path_var.get(), 
                                           language_var.get(), translate_var.get(), output_format)
        
        if result and 'transcription' in result:
            logging.info("转录完成，准备保存结果")
            def save_and_finish():
                save_transcription(result['transcription'], output_path_var.get())
                save_settings()
                logging.info("转录完成并保存")
                update_progress_bar(100)
                reset_buttons()
                messagebox.showinfo("完成", "转录已完成！")
            root.after(0, save_and_finish)
        else:
            # 构建详细的错误信息
            error_details = []
            if error_info:
                if 'returncode' in error_info:
                    error_details.append(f"进程返回码: {error_info['returncode']}")
                if 'stdout' in error_info:
                    error_details.append(f"标准输出:\n{error_info['stdout']}")
                if 'stderr' in error_info:
                    error_details.append(f"错误输出:\n{error_info['stderr']}")
                if 'error' in error_info:
                    error_details.append(f"错误信息: {error_info['error']}")
                if 'traceback' in error_info:
                    error_details.append(f"错误堆栈:\n{error_info['traceback']}")
            
            error_msg = "转录失败\n\n" + "\n\n".join(error_details)
            logging.error(error_msg)
            
            def show_error():
                messagebox.showerror("错误", error_msg)
                reset_buttons()
            root.after(0, show_error)
    
    except Exception as e:
        logging.error("转录过程出错", exc_info=True)
        error_msg = f"转录过程出错：{str(e)}\n\n详细错误：{traceback.format_exc()}"
        def show_error():
            messagebox.showerror("错误", error_msg)
            reset_buttons()
        root.after(0, show_error)
    
    finally:
        # 清理临时文件
        if temp_audio and os.path.exists(temp_audio):
            try:
                os.remove(temp_audio)
                logging.info(f"已删除临时音频文件: {temp_audio}")
            except Exception as e:
                logging.error(f"删除临时音频文件失败: {e}")
        
        # 恢复按钮状态
        root.after(0, lambda: reset_buttons())

def extract_audio_from_video(video_file):
    """从视频文件提取音频并转换为16kHz WAV"""
    try:
        # 使用系统临时目录
        temp_audio = os.path.join(
            tempfile.gettempdir(),
            f"whisper_temp_{int(time.time())}_{os.path.basename(video_file)}.wav"
        )
        
        # 获取ffmpeg路径
        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            logging.error("找不到 ffmpeg")
            return None
        
        # 使用ffmpeg提取音频并转换为16kHz
        cmd = [
            ffmpeg_path,
            "-i", video_file,
            "-vn",  # 不处理视频
            "-ar", "16000",  # 设置采样率
            "-ac", "1",  # 单声道
            "-c:a", "pcm_s16le",  # WAV格式
            "-y",  # 覆盖已存在的文件
            temp_audio
        ]
        
        logging.info(f"执行视频音频提取命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logging.error(f"音频提取失败: {result.stderr}")
            if os.path.exists(temp_audio):
                try:
                    os.remove(temp_audio)
                except:
                    pass
            return None
            
        logging.info(f"音频提取成功: {temp_audio}")
        return temp_audio
        
    except Exception as e:
        logging.error(f"视频处理出错: {e}")
        if os.path.exists(temp_audio):
            try:
                os.remove(temp_audio)
            except:
                pass
        return None

def browse_model():
    """浏览选择模型文件"""
    settings = load_settings()
    initial_dir = settings.get('last_model_dir', get_model_path())  # 使用 get 方法安全获取
    
    file_path = filedialog.askopenfilename(
        title="选择模型文件",
        initialdir=initial_dir,
        filetypes=[("GGML模型文件", "*.bin")]
    )
    
    if file_path:
        # 更新模型路径
        model_path_var.set(file_path)
        
        # 更新下拉框的值
        current_values = list(model_dropdown['values'])
        if file_path not in current_values:
            current_values.append(file_path)
            model_dropdown['values'] = current_values
        
        # 保存设置
        save_settings()

def browse_file():
    """浏览并选择音频文"""
    settings = load_settings()
    initial_dir = settings['last_audio_dir'] if settings['last_audio_dir'] else None
    
    file_path = filedialog.askopenfilename(
        title="选择音频文件",
        initialdir=initial_dir,
        filetypes=[("音频文件", "*.wav;*.mp3;*.m4a;*.flac"), ("所有文件", "*.*")]
    )
    
    if file_path:
        audio_file_var.set(file_path)
        save_settings()

def browse_model():
    """浏览并选择模型文件"""
    global model_dropdown
    settings = load_settings()
    initial_dir = settings['last_model_dir'] if settings['last_model_dir'] else None
    
    file_path = filedialog.askopenfilename(
        title="选择模型文件",
        initialdir=initial_dir,
        filetypes=[("模型文件", "*.bin")]
    )
    
    if file_path:
        model_path_var.set(file_path)
        # 扫描选中文件所在目录的所有模型文件
        model_dir = os.path.dirname(file_path)
        model_files = [f for f in os.listdir(model_dir) if f.endswith('.bin')]
        
        # 更新下拉列表
        current_values = list(model_dropdown['values'])
        for model_file in model_files:
            full_path = os.path.join(model_dir, model_file)
            if full_path not in current_values:
                current_values.append(full_path)
        
        model_dropdown['values'] = current_values
        save_settings()

def get_model_files():
    """获取model文件夹中的所有.bin文件"""
    try:
        # 获取正确的model目录路径
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            model_dir = os.path.join(get_app_path(), 'model')
        else:
            # 开发环境
            model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'model')
        
        print(f"当前model目录: {model_dir}")
        
        # 确保model目录存在
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
            print("创建model目录")
            return []
        
        # 获取所有.bin文件
        model_files = [f for f in os.listdir(model_dir) if f.endswith('.bin')]
        print(f"找到的模型文件: {model_files}")
        
        return model_files
        
    except Exception as e:
        print(f"获取模型文件失败: {e}")
        return []

def reset_buttons():
    """重置按钮状态"""
    start_button['state'] = 'normal'
    stop_button['state'] = 'disabled'
    progress_bar['value'] = 0
    root.update_idletasks()

def save_settings():
    """保存设置"""
    try:
        settings = {
            'model_paths': list(model_dropdown['values']) if model_dropdown else [],
            'last_model_path': model_path_var.get(),
            'last_model_dir': os.path.dirname(model_path_var.get()) if model_path_var.get() else get_model_path(),
            'last_output_format': os.path.splitext(output_path_var.get())[1] if output_path_var.get() else '.srt',
            'last_output_dir': os.path.dirname(output_path_var.get()) if output_path_var.get() else os.path.expanduser('~'),
            'last_media_dir': os.path.dirname(audio_file_var.get()) if audio_file_var.get() else os.path.expanduser('~')
        }
        
        # 确定设置文件路径
        if getattr(sys, 'frozen', False):
            # 打包环境
            settings_dir = os.path.join(os.path.dirname(sys.executable), 'config')
        else:
            # 开环境
            settings_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        # 确保配置目录存在
        os.makedirs(settings_dir, exist_ok=True)
        
        settings_file = os.path.join(settings_dir, 'settings.json')
        logging.info(f"保存设置到: {settings_file}")
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
            
        logging.info("设置保存成功")
        
    except Exception as e:
        logging.error(f"保存设置时出错", exc_info=True)
        print(f"保存设置时出错: {e}")

def load_settings():
    """加载设置"""
    try:
        # 确定设置文件路径
        if getattr(sys, 'frozen', False):
            settings_dir = os.path.join(os.path.dirname(sys.executable), 'config')
        else:
            settings_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        settings_file = os.path.join(settings_dir, 'settings.json')
        logging.info(f"尝试加载设置: {settings_file}")
        
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            logging.info("设置加载成功")
            
            # 确保所有必要的键都存在
            default_settings = {
                'model_paths': [],
                'last_model_path': '',
                'last_model_dir': get_model_path(),
                'last_output_format': '.srt',
                'last_output_dir': os.path.expanduser('~'),  # 默认用户目录
                'last_media_dir': os.path.expanduser('~')    # 默认用户目录
            }
            
            # 更新缺失的键
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
                    
            return settings
    except Exception as e:
        logging.error(f"加载设置时出错", exc_info=True)
        print(f"加载设置时出错: {e}")
    
    # 返回默认设置
    return {
        'model_paths': [],
        'last_model_path': '',
        'last_model_dir': get_model_path(),
        'last_output_format': '.srt',
        'last_output_dir': os.path.expanduser('~'),  # 默认用户目录
        'last_media_dir': os.path.expanduser('~')    # 默认用户目录
    }

def browse_output():
    """浏览选择输出文件"""
    settings = load_settings()
    initial_dir = settings.get('last_output_dir', os.path.expanduser('~'))
    initial_file = "output.srt"
    
    # 如果有输入文件，使用其名称作为基础
    if audio_file_var.get():
        base_name = os.path.splitext(os.path.basename(audio_file_var.get()))[0]
        initial_file = f"{base_name}_output.srt"
    
    file_path = filedialog.asksaveasfilename(
        title="选择保存位置",
        initialdir=initial_dir,
        initialfile=initial_file,
        defaultextension=".srt",
        filetypes=[
            ("字幕文件", "*.srt"),
            ("文本文件", "*.txt"),
            ("JSON文件", "*.json")
        ]
    )
    
    if file_path:
        output_path_var.set(file_path)
        # 保存设置
        save_settings()
        logging.info(f"已选择输出文件: {file_path}")

def update_gui():
    """定期更新GUI"""
    try:
        root.update()
    except Exception as e:
        print(f"GUI更新错误: {e}")
    finally:
        root.after(100, update_gui)  # 每100ms更新一次

def update_progress_bar(value):
    """更新进度条"""
    try:
        progress_bar['value'] = value
        root.update_idletasks()
    except Exception as e:
        print(f"更新进度条出错: {e}")

def setup_logging():
    """设置日志"""
    try:
        if getattr(sys, 'frozen', False):
            # 打包后的环境，使用程序所在目录
            base_dir = os.path.dirname(sys.executable)
            log_dir = os.path.join(base_dir, 'logs')
        else:
            # 开发环境
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_dir = os.path.join(base_dir, 'logs')
            
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'whisper_log.txt')
        
        # 配置日志
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logging.info("=== 程序启动 ===")
        logging.info(f"Python版本: {sys.version}")
        logging.info(f"运行模式: {'打包环境' if getattr(sys, 'frozen', False) else '开发环境'}")
        logging.info(f"日志文件位置: {log_file}")
        
    except Exception as e:
        print(f"设置日志时出错: {e}")
        # 如果设置日志失败，至少尝试输出到控制台
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logging.error(f"设置日志文件失败: {e}")
        
def browse_media():
    """浏览选择媒体文件"""
    file_path = filedialog.askopenfilename(
        title="选择媒体文件",
        filetypes=[
            ("所有支持的格式", "*.wav;*.mp3;*.m4a;*.mp4;*.avi;*.mkv;*.mov"),
            ("音频文件", "*.wav;*.mp3;*.m4a"),
            ("视频文件", "*.mp4;*.avi;*.mkv;*.mov"),
            ("所有文件", "*.*")
        ]
    )
    
    if file_path:
        audio_file_var.set(file_path)
        
        # 自动设置输出文件路径
        base_name = os.path.splitext(file_path)[0]
        output_path = f"{base_name}_output.srt"
        output_path_var.set(output_path)
        
        logging.info(f"已选择媒体文件: {file_path}")
        logging.info(f"自动设置输出路径: {output_path}")
# 创建 GUI 界面
def init_gui():
    """初始化GUI"""
    global audio_file_var, model_path_var, language_var, translate_var
    global output_path_var, progress_bar, start_button, stop_button, root
    global model_dropdown  # 添加这行，声明 model_dropdown 为全局变量
    
    root = tk.Tk()
    root.title("Whisper 音频转文字")

    # 初始化所有变量
    audio_file_var = StringVar()
    model_path_var = StringVar()
    language_var = StringVar(value="中文 (zh)")  # 修改默认值显示格式
    translate_var = BooleanVar()
    output_path_var = StringVar()
    
    # 美化主
    style = ttk.Style(root)
    style.theme_use('clam')

    # 设置窗口大小
    window_width = 470
    window_height = 250
    
    # 获取屏幕尺寸
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # 计算窗口居中的位置
    center_x = int((screen_width - window_width) / 2)
    center_y = int((screen_height - window_height) / 2)
    
    # 设置窗口大小和位置
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    # 禁止调整窗口大小
    root.resizable(False, False)
    


    # 媒体文件选择
    ttk.Label(root, text="媒体文件:").grid(row=0, column=0, sticky="e", padx=5)
    file_frame = ttk.Frame(root)
    file_frame.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
    
    ttk.Entry(file_frame, textvariable=audio_file_var, width=50).grid(row=0, column=0, sticky="ew")
    ttk.Button(file_frame, text="浏览", command=browse_media, width=8).grid(row=0, column=1, padx=(5, 0))
    file_frame.grid_columnconfigure(0, weight=1)
    
    # 添加文件格式提示
    file_tip = CreateToolTip(file_frame, 
        "支持的格式:\n" +
        "音频: MP3, WAV, M4A\n" +
        "视频: MP4, AVI, MKV, MOV\n" +
        "视频文件会自动提取音频")
    
    # 配置列权重
    file_frame.grid_columnconfigure(1, weight=1)

    # 模型文件选择
    ttk.Label(root, text="模型文件:").grid(row=1, column=0, sticky="e")
    model_frame = ttk.Frame(root)
    model_frame.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
    
    # 创建组合框和浏览按钮的容器
    model_path_var = StringVar()
    model_files = get_model_files()
    
    # 创建组合框
    global model_dropdown  # 在创建前声明
    if model_files:
        model_path_var.set(os.path.join("model", model_files[0]))
        model_dropdown = ttk.Combobox(
            model_frame, 
            textvariable=model_path_var,
            values=[os.path.join("model", f) for f in model_files],
            width=47
        )
    else:
        model_path_var.set("")
        model_dropdown = ttk.Combobox(
            model_frame,
            textvariable=model_path_var,
            values=[],  # 改为空列表
            width=47
        )
    
    model_dropdown.grid(row=0, column=0, sticky="ew")
    ttk.Button(model_frame, text="浏览", command=browse_model, width=8).grid(row=0, column=1, padx=(5, 0))
    model_frame.grid_columnconfigure(0, weight=1)
    
    # 语言选择
    ttk.Label(root, text="语言:").grid(row=2, column=0, sticky="e")
    language_menu = ttk.OptionMenu(
        root,
        language_var,
        "中文 (zh)",  # 默认值
        *languages.keys()  # 使用全局字典的键
    )
    language_menu.grid(row=2, column=1, sticky="w", padx=5, pady=5)

    # 当语言选择改变时更新实际使用的语言代码
    def on_language_change(*args):
        selected_display = language_var.get()
        actual_code = languages[selected_display]
        print(f"Selected language: {actual_code}")  # 用于调试

    language_var.trace('w', on_language_change)

    # # 停用翻译按钮
    # translate_var = BooleanVar()
    # ttk.Checkbutton(root, text="翻为英文", variable=translate_var).grid(row=3, column=1, sticky="w", padx=5, pady=5)

    # 输出文件选择
    ttk.Label(root, text="输出文件:").grid(row=3, column=0, sticky="e", padx=5)
    output_frame = ttk.Frame(root)
    output_frame.grid(row=3, column=1, columnspan=2, sticky="ew", padx=5, pady=5)
    
    ttk.Entry(output_frame, textvariable=output_path_var, width=50).grid(row=0, column=0, sticky="ew")
    ttk.Button(output_frame, text="浏览", command=browse_output, width=8).grid(row=0, column=1, padx=(5, 0))
    output_frame.grid_columnconfigure(0, weight=1)

    # 创建进度条
    style = ttk.Style()
    style.configure("TProgressbar", troughcolor='white', background='blue', thickness=20)

    progress_bar = ttk.Progressbar(
        root, 
        mode='determinate',
        length=300,
        maximum=100.0,  # 明确设置最大值为100
        style="TProgressbar"
    )
    progress_bar.grid(row=5, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
    progress_bar['value'] = 0  # 初始化为0
    
    # 按钮区域
    button_frame = ttk.Frame(root)
    button_frame.grid(row=6, column=1, pady=10)

    start_button = ttk.Button(button_frame, text="开始转录", command=start_transcription_thread)
    start_button.pack(side="left", padx=5)

    stop_button = ttk.Button(button_frame, text="停止", command=stop_transcription, state='disabled')
    stop_button.pack(side="left", padx=5)

    # 加载保存的设置
    settings = load_settings()
    
    # 设置模型下拉框的值
    if settings['model_paths']:
        model_dropdown['values'] = settings['model_paths']
        if settings['last_model_path']:
            model_path_var.set(settings['last_model_path'])
    
    # 设置默认输出格式
    if settings['last_output_format']:
        global default_output_format
        default_output_format = settings['last_output_format']
    
    # 启动GUI更新循环
    root.after(100, update_gui)

    # 配置窗口关闭事件
    def on_closing():
        if current_process:
            if messagebox.askokcancel("退出", "转录正在进行中，确定要退出吗？"):
                stop_transcription()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)

# 添加工具提示类
class CreateToolTip(object):
    """
    建工具提示
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     # 毫秒
        self.wraplength = 180   # 像素
        self.widget = widget
        self.text = text
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(1)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()

# 在程序启动时调用init_gui
if __name__ == "__main__":
    # 设置日志
    setup_logging()
    
    try:
        init_gui()
        root.mainloop()
    except Exception as e:
        logging.error("程序运行出错", exc_info=True)
        messagebox.showerror("错误", f"程序运行出错: {str(e)}")

