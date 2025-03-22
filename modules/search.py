# search.py
import os
import json
import requests
import markdown  # 新增导入
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView  # 关键修复

SEARCH_DATA_DIR = "data/search_sessions"
os.makedirs(SEARCH_DATA_DIR, exist_ok=True)



class StreamWorker(QThread):
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, api_key, messages, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.messages = messages

    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.api_key.strip()}"}
            data = {
                "messages": self.messages,
                "model": "deepseek-chat",
                "stream": True  # 启用流式传输
            }
            
            with requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=data,
                stream=True,
                timeout=10
            ) as response:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            chunk = decoded_line[6:]
                            if chunk == "[DONE]":
                                break
                            try:
                                chunk_json = json.loads(chunk)
                                content = chunk_json["choices"][0]["delta"].get("content", "")
                                self.chunk_received.emit(content)
                            except Exception as e:
                                self.error_occurred.emit(f"解析错误: {str(e)}")

        except requests.exceptions.ConnectionError:
            self.error_occurred.emit("网络连接失败，请检查网络设置")
        except requests.exceptions.Timeout:
            self.error_occurred.emit("请求超时，服务器未及时响应")
        except Exception as e:
            if "401" in str(e):
                self.error_occurred.emit("API密钥无效（错误代码401）")
            else:
                self.error_occurred.emit(f"未知错误: {str(e)}")
        finally:
            self.finished.emit()



class SearchModule(QWidget):
    new_note_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.sessions = []
        self.current_session_id = None
        self.api_key = ""
        self.stream_worker = None
        self.accumulated_response = ""
        self.init_ui()
        self.load_sessions()
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.execute_scroll)


    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # 左侧会话列表
        self.session_panel = QWidget()
        session_layout = QVBoxLayout(self.session_panel)
        
        # 搜索栏
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("搜索会话...")
        self.search_bar.textChanged.connect(self.filter_sessions)
        
        # 会话列表
        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self.load_session)
        self.session_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.session_list.customContextMenuRequested.connect(self.show_session_menu)
        
        # 新建会话按钮
        self.new_btn = QPushButton("新建会话")
        self.new_btn.clicked.connect(self.create_session)
        
        session_layout.addWidget(self.search_bar)
        session_layout.addWidget(self.session_list, 1)
        session_layout.addWidget(self.new_btn)

        # 右侧聊天区域
        self.chat_panel = QWidget()
        chat_layout = QVBoxLayout(self.chat_panel)
        
        # 聊天历史
        self.chat_history = QWebEngineView()
        self.chat_history.setHtml(self.get_base_html(""))
        
        # 输入区域
        input_layout = QHBoxLayout()
        self.input_field = QTextEdit()
        self.input_field.setMaximumHeight(100)
        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.send_btn)
        
        chat_layout.addWidget(self.chat_history, 1)
        chat_layout.addLayout(input_layout)

        main_layout.addWidget(self.session_panel, 1)
        main_layout.addWidget(self.chat_panel, 2)
        
        self.setStyleSheet("""
            QListWidget, QWebEngineView, QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QPushButton {
                padding: 8px;
                border-radius: 6px;
                background: #2196F3;
                color: white;
            }
        """)

    def show_session_menu(self, pos):
        item = self.session_list.itemAt(pos)
        menu = QMenu()
        
        delete_action = QAction("删除会话", self)
        delete_action.triggered.connect(lambda: self.delete_session(item))
        
        convert_action = QAction("转为笔记", self)
        convert_action.triggered.connect(lambda: self.convert_to_note(item))
        
        if item:
            menu.addActions([delete_action, convert_action])
        menu.exec_(self.session_list.mapToGlobal(pos))

    def create_session(self):
        session_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        session = {
            "id": session_id,
            "title": "新会话",
            "history": [],
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat()
        }
        self.sessions.append(session)
        self.save_session(session)
        self.update_session_list()
        self.current_session_id = session_id

    def delete_session(self, item):
        session_id = item.data(Qt.UserRole)
        confirm = QMessageBox.question(
            self, "删除确认", 
            "确定删除该会话？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            # 删除文件
            file_path = os.path.join(SEARCH_DATA_DIR, f"{session_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
            self.sessions = [s for s in self.sessions if s["id"] != session_id]
            self.update_session_list()

    def convert_to_note(self, item):
        session_id = item.data(Qt.UserRole)
        session = next((s for s in self.sessions if s["id"] == session_id), None)
        if not session:
            return

        # 弹出笔记设置对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("保存为笔记")
        layout = QFormLayout(dialog)
        
        title_input = QLineEdit(session["title"])
        tag_input = QLineEdit()
        folder_input = QComboBox()
        folder_input.addItems(self.get_folder_structure())  # 需要从notes模块获取
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        
        layout.addRow("标题:", title_input)
        layout.addRow("标签（逗号分隔）:", tag_input)
        layout.addRow("文件夹:", folder_input)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            separator = "\n\n---\n\n"  # Markdown水平线
            content = separator.join([
                    f"**{msg['role'].capitalize()}**: {msg['content']}" 
                    for msg in session["history"]
                ])
            
            note_data = {
                "title": title_input.text(),
                "content": content,
                "tags": [t.strip() for t in tag_input.text().split(",") if t.strip()],
                "path": folder_input.currentText()
            }
            self.new_note_signal.emit(note_data)
            QMessageBox.information(self, "成功", "笔记已保存！")

    def get_folder_structure(self):
        # 这里需要从notes模块获取文件夹结构，暂时返回示例数据
        return ["默认文件夹", "学习笔记", "工作记录"]

    def filter_sessions(self):
        keyword = self.search_bar.text().lower()
        for i in range(self.session_list.count()):
            item = self.session_list.item(i)
            item.setHidden(keyword not in item.text().lower())

    def load_sessions(self):
        self.sessions = []
        for file in os.listdir(SEARCH_DATA_DIR):
            if file.endswith(".json"):
                with open(os.path.join(SEARCH_DATA_DIR, file), "r") as f:
                    self.sessions.append(json.load(f))
        self.update_session_list()

    def update_session_list(self):
        self.session_list.clear()
        for session in sorted(self.sessions, 
                            key=lambda x: x["updated"], reverse=True)[:5]:
            item = QListWidgetItem(session["title"])
            item.setData(Qt.UserRole, session["id"])
            self.session_list.addItem(item)

    def save_session(self, session):
        file_path = os.path.join(SEARCH_DATA_DIR, f"{session['id']}.json")
        with open(file_path, "w") as f:
            json.dump(session, f, indent=2)

    def load_session(self, item):
        session_id = item.data(Qt.UserRole)
        session = next((s for s in self.sessions if s["id"] == session_id), None)
        if session:
            self.current_session_id = session_id
            html = self.get_base_html("\n".join(
                [f"<div class='{msg['role']}'>{msg['content']}</div>" 
                 for msg in session["history"]]
            ))
            self.chat_history.setHtml(html)

    def show_error(self, message):
        """统一错误提示方法"""
        QMessageBox.critical(
            self, 
            "错误", 
            f"{message}\n\n（建议检查API密钥或网络连接）",
            QMessageBox.Ok
        )

    # def send_message(self):
    #     if not self.current_session_id:
    #         QMessageBox.warning(self, "警告", "请先选择或创建一个会话")
    #         return
    #     if not self.api_key:
    #         QMessageBox.warning(self, "警告", "请先在设置中配置API密钥")
    #         return
            
    #     user_input = self.input_field.toPlainText().strip()
    #     if not user_input:
    #         QMessageBox.warning(self, "警告", "请输入消息内容")
    #         return

    #     try:
    #         session = next(s for s in self.sessions if s["id"] == self.current_session_id)
    #         session["history"].append({"role": "user", "content": user_input})
            
    #         headers = {"Authorization": f"Bearer {self.api_key.strip()}"}
    #         data = {
    #             "messages": session["history"][-5:],
    #             "model": "deepseek-chat"
    #         }
            
    #         response = requests.post(
    #             "https://api.deepseek.com/v1/chat/completions",
    #             headers=headers,
    #             json=data,
    #             timeout=10
    #         )
    #         # response.raise_for_status()
            
    #         response_data = response.json()
    #         if "choices" not in response_data or not response_data["choices"]:
    #             self.show_error("API返回无效数据")
    #             return
                
    #         result = response_data["choices"][0]["message"]
            
    #     except requests.exceptions.HTTPError as http_err:
    #         self.show_error(f"HTTP错误 {response.status_code}: {response.text[:200]}")
    #     except json.JSONDecodeError:
    #         self.show_error("API返回无效的JSON数据")
    #     except Exception as e:
    #         self.show_error(f"API请求失败: {str(e)}")
        
    #     else:
    #         # 成功时更新数据并刷新UI
    #         session["history"].append(result)
    #         session["updated"] = datetime.now().isoformat()
    #         self.save_session(session)
            
    #         # 更新会话列表并选中当前项
    #         self.update_session_list()
    #         for i in range(self.session_list.count()):
    #             item = self.session_list.item(i)
    #             if item.data(Qt.UserRole) == self.current_session_id:
    #                 self.session_list.setCurrentItem(item)
    #                 self.load_session(item)  # 强制刷新
    #                 break
    #         self.input_field.clear()

    def send_message(self):
        if not self.current_session_id:
            QMessageBox.warning(self, "警告", "请先选择或创建一个会话")
            return
        if not self.api_key:
            QMessageBox.warning(self, "警告", "请先在设置中配置API密钥")
            return
            
        user_input = self.input_field.toPlainText().strip()
        if not user_input:
            QMessageBox.warning(self, "警告", "请输入消息内容")
            return

        session = next(s for s in self.sessions if s["id"] == self.current_session_id)
        session["history"].append({"role": "user", "content": user_input})
        self.input_field.clear()
        self.send_btn.setEnabled(False)  # 禁用发送按钮

        # 创建流式工作线程
        self.stream_worker = StreamWorker(
            self.api_key,
            session["history"][-5:]
        )
        self.stream_worker.chunk_received.connect(self.handle_stream_chunk)
        self.stream_worker.finished.connect(self.handle_stream_finished)
        self.stream_worker.error_occurred.connect(self.handle_stream_error)
        self.stream_worker.start()

    def handle_stream_chunk(self, content):
        self.accumulated_response += content
        session = next(s for s in self.sessions if s["id"] == self.current_session_id)
        
        # 更新最后一条assistant消息
        if session["history"] and session["history"][-1]["role"] == "assistant":
            session["history"][-1]["content"] = self.accumulated_response
        else:
            session["history"].append({"role": "assistant", "content": self.accumulated_response})
        
        # 实时更新显示
        html = self.get_base_html("\n".join(
            [f"<div class='{msg['role']}'>{msg['content']}</div>" 
             for msg in session["history"]]
        ))
        self.chat_history.setHtml(html)
        self.chat_history.page().runJavaScript("window.scrollTo(0, document.body.scrollHeight);")
        self.scroll_timer.start(100) 

    def handle_stream_finished(self):
        session = next(s for s in self.sessions if s["id"] == self.current_session_id)
        session["updated"] = datetime.now().isoformat()
        self.save_session(session)
        self.update_session_list()
        self.accumulated_response = ""
        self.send_btn.setEnabled(True)

    def handle_stream_error(self, error_msg):
        self.show_error(error_msg)  # 现在可以正常调用
        self.send_btn.setEnabled(True)
        self.accumulated_response = ""
        
        # 清理无效的会话记录
        if self.current_session_id:
            session = next((s for s in self.sessions if s["id"] == self.current_session_id), None)
            if session and session["history"][-1]["role"] == "assistant":
                session["history"].pop()  # 删除不完整的回复
                self.save_session(session)

    def set_api_key(self, key):
        self.api_key = key

    def get_base_html(self, content):
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ 
                    font-family: Segoe UI; 
                    padding: 20px;
                    background: #f8f9fa;
                }}
                .user {{ 
                    background: #e3f2fd;
                    padding: 10px;
                    border-radius: 8px;
                    margin: 10px 0;
                }}
                .assistant {{
                    background: white;
                    padding: 10px;
                    border-radius: 8px;
                    margin: 10px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                pre {{ 
                    background: #f5f5f5;
                    padding: 15px;
                    border-radius: 8px;
                }}
            </style>
            <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
            <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        </head>
        <body>
            {content}
        </body>
        </html>
        """

    def execute_scroll(self):
        self.chat_history.page().runJavaScript("""
            let container = document.documentElement;
            if(container) {
                container.scrollTo({
                    top: container.scrollHeight,
                    behavior: 'smooth'
                });
            }
        """)