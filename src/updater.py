import json
import requests
from packaging import version
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt
import sys
import os
import tempfile

class Updater:
    def __init__(self):
        self.current_version = "1.0.0"
        self.version_url = "https://raw.githubusercontent.com/your-repo/main/version.json"
    
    def check_for_updates(self, silent=False):
        """检查更新"""
        try:
            response = requests.get(self.version_url, timeout=5)
            if response.status_code != 200:
                if not silent:
                    QMessageBox.warning(None, "检查更新", "检查更新失败：无法连接到服务器")
                return False
                
            data = response.json()
            latest_version = data.get("version")
            
            if version.parse(latest_version) > version.parse(self.current_version):
                if not silent:
                    self._show_update_dialog(data)
                return True
            elif not silent:
                QMessageBox.information(None, "检查更新", "当前已是最新版本！")
            return False
            
        except Exception as e:
            if not silent:
                QMessageBox.warning(None, "检查更新", f"检查更新失败：{str(e)}")
            return False
    
    def _show_update_dialog(self, update_info):
        """显示更新对话框"""
        msg = f"""发现新版本！

当前版本：{self.current_version}
最新版本：{update_info['version']}

更新内容：
{update_info.get('release_notes', '暂无更新说明')}

是否立即更新？"""

        # 如果是强制更新
        if update_info.get('force_update', False):
            QMessageBox.warning(None, "强制更新", 
                f"发现重要更新，必须更新后才能继续使用！\n\n{msg}")
            self._download_and_install(update_info['download_url'])
            return

        # 普通更新
        reply = QMessageBox.question(None, "发现新版本", msg,
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self._download_and_install(update_info['download_url'])
    
    def _download_and_install(self, download_url):
        """下载并安装更新"""
        try:
            # 创建进度对话框
            progress = QProgressDialog("正在下载更新...", "取消", 0, 100)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("下载更新")
            progress.show()

            # 下载文件
            response = requests.get(download_url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024  # 1 KB
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, "EasyWhisper_Setup.exe")

            # 写入文件
            downloaded_size = 0
            with open(installer_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded_size += len(data)
                    f.write(data)
                    
                    # 更新进度
                    if total_size:
                        progress_value = int((downloaded_size / total_size) * 100)
                        progress.setValue(progress_value)
                    
                    # 检查是否取消
                    if progress.wasCanceled():
                        return

            progress.close()

            # 下载完成，运行安装程序
            reply = QMessageBox.information(None, "下载完成", 
                "更新已下载完成，点击确定开始安装。\n安装程序运行后，当前程序将自动关闭。",
                QMessageBox.Ok | QMessageBox.Cancel)
            
            if reply == QMessageBox.Ok:
                if sys.platform == 'win32':
                    os.startfile(installer_path)
                    sys.exit(0)  # 退出当前程序
                
        except Exception as e:
            QMessageBox.warning(None, "更新失败", f"下载或安装更新失败：{str(e)}")