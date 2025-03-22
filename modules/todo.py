# todo.py
import json,os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime

TODO_FILE = "data/todos.json"

class TodoModule(QWidget):
    count_changed = pyqtSignal(int)  # 未完成任务数量变化信号
    task_updated = pyqtSignal()  # 新增信号

    def __init__(self):
        super().__init__()
        self.todos = []
        self.ensure_data_dir()
        self.load_data()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 时间轴显示
        self.timeline = TimelineWidget(self.todos)
        
        # 输入区域
        input_layout = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入新任务...")
        self.input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
            }
        """)
        self.input.returnPressed.connect(self.show_time_dialog)
        
        add_btn = QPushButton("📌 添加")
        add_btn.setFixedWidth(100)
        add_btn.clicked.connect(self.show_time_dialog)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover { background: #45a049; }
        """)
        
        input_layout.addWidget(self.input)
        input_layout.addWidget(add_btn)
        
        # 待办列表
        self.list = QListWidget()
        self.list.setStyleSheet("""
            QListWidget {
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
            }
            QListWidget::item {
                border-bottom: 1px solid #eee;
            }
        """)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.update_list()
        
        main_layout.addWidget(self.timeline, 1)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.list, 3)
        self.setLayout(main_layout)

    def show_time_dialog(self):
        text = self.input.text().strip()
        if not text:
            return
            
        dialog = TimeRangeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.add_todo(text, dialog.start_time, dialog.end_time)

    def add_todo(self, text, start_time, end_time):
        new_todo = {
            "id": datetime.now().timestamp(),
            "text": text,
            "done": False,
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "created": datetime.now().isoformat(),
            "completed": None
        }
        
        self.todos.append(new_todo)
        self.input.clear()
        self.save_data()
        self.update_list()
        self.count_changed.emit(self.pending_count())
        self.task_updated.emit()

    def toggle_done(self, item):
        todo = self.todos[self.list.row(item)]
        todo["done"] = not todo["done"]
        todo["completed"] = datetime.now().isoformat() if todo["done"] else None
        self.save_data()
        self.update_list()
        self.count_changed.emit(self.pending_count())

    def delete_todo(self, todo_id):
        """删除指定任务"""
        self.todos = [t for t in self.todos if t["id"] != todo_id]
        self.save_data()
        self.update_list()
        self.count_changed.emit(self.pending_count())
        self.task_updated.emit()

    def pending_count(self):
        return len([t for t in self.todos if not t["done"]])

    def update_list(self):
        self.list.clear()
        for todo in sorted(self.todos, key=lambda x: x["created"], reverse=True):
            item = QListWidgetItem()
            widget = TodoItemWidget(todo, self)
            item.setSizeHint(widget.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, widget)
        self.timeline.todos = self.todos  # 更新时间轴数据
        self.timeline.update()  # 强制重绘时间轴

    def ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(TODO_FILE), exist_ok=True)

    def load_data(self):
        """增强数据加载方法"""
        try:
            if os.path.exists(TODO_FILE):
                with open(TODO_FILE, "r") as f:
                    raw_data = json.load(f)
                    # 数据迁移和验证
                    self.todos = [self.validate_todo(t) for t in raw_data]
                    self.todos = [t for t in self.todos if t is not None]
            else:
                self.todos = []
        except Exception as e:
            QMessageBox.warning(self, "数据错误", f"加载待办数据失败：{str(e)}")
            self.todos = []

    def validate_todo(self, todo):
        """验证并修复单个待办项数据结构"""
        required_keys = ["id", "text", "done", "created"]
        try:
            # 补全缺失字段
            if "start" not in todo:
                todo["start"] = datetime.now().isoformat()
            if "end" not in todo:
                todo["end"] = datetime.now().isoformat()
            if "completed" not in todo:
                todo["completed"] = None
                
            # 转换旧版时间格式
            if isinstance(todo["created"], str):
                datetime.fromisoformat(todo["created"])  # 验证时间格式
            return todo
        except Exception as e:
            print(f"无效的待办项已忽略：{todo}，错误：{str(e)}")
            return None

    def save_data(self):
        """增强数据保存方法"""
        try:
            with open(TODO_FILE, "w") as f:
                # 转换为可序列化格式
                serializable_data = []
                for todo in self.todos:
                    data = todo.copy()
                    # 确保所有datetime对象转为字符串
                    for key in ["start", "end", "created", "completed"]:
                        if data[key] and isinstance(data[key], datetime):
                            data[key] = data[key].isoformat()
                    serializable_data.append(data)
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"无法保存待办事项：{str(e)}")


class TimeRangeDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("设置时间范围")
        layout = QVBoxLayout()
        
        # 时间选择器
        time_group = QGroupBox("时间设置")
        time_layout = QFormLayout()
        
        self.start_edit = QDateTimeEdit()
        self.start_edit.setDateTime(QDateTime.currentDateTime())
        self.start_edit.setCalendarPopup(True)
        
        self.end_edit = QDateTimeEdit()
        self.end_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.end_edit.setCalendarPopup(True)
        
        time_layout.addRow("开始时间:", self.start_edit)
        time_layout.addRow("结束时间:", self.end_edit)
        time_group.setLayout(time_layout)
        
        # 按钮组
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        
        layout.addWidget(time_group)
        layout.addWidget(btn_box)
        self.setLayout(layout)
    
    @property
    def start_time(self):
        return self.start_edit.dateTime().toPyDateTime()
    
    @property
    def end_time(self):
        return self.end_edit.dateTime().toPyDateTime()



class TodoItemWidget(QWidget):
    def __init__(self, todo, parent):
        super().__init__(parent)
        self.todo=todo
        self.todo_id = todo["id"]  # 保存任务ID
        self.parent = parent
        self.init_ui()
        self.setup_styles()
        self.calculate_height()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 15, 10, 15)
        layout.setSpacing(8)  # 减少内部间距

        # 头部操作栏
        header = QHBoxLayout()
        
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self.todo["done"])
        self.checkbox.stateChanged.connect(self.toggle_status)
        
        self.title = QLabel(self.todo["text"])
        self.title.setWordWrap(True)
        self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.clicked.connect(lambda: self.parent.delete_todo(self.todo["id"]))
        del_btn.setToolTip("删除任务")
        
        header.addWidget(self.checkbox)
        header.addWidget(self.title, 1)
        header.addWidget(del_btn)

        # 时间显示
        time_layout = QHBoxLayout()
        start = datetime.fromisoformat(self.todo["start"]).strftime("%m/%d %H:%M")
        end = datetime.fromisoformat(self.todo["end"]).strftime("%m/%d %H:%M")
        
        self.time_label = QLabel(f"🕒 {start} - {end}")
        self.time_label.setAlignment(Qt.AlignRight)
        
        time_layout.addWidget(QLabel("📌 任务时间:"))
        time_layout.addWidget(self.time_label)
        
        layout.addLayout(header)
        layout.addLayout(time_layout)
        self.setLayout(layout)
        self.checkbox.stateChanged.connect(self._handle_checkbox_change)

    def setup_styles(self):
        self.setStyleSheet("""
            QWidget {
                background: white;
                border-radius: 8px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QLabel {
                color: #333;
                font-size: 14px;
            }
            QPushButton {
                background: transparent;
                color: #666;
                font-size: 16px;
                padding: 0;
            }
            QPushButton:hover {
                color: #ff4444;
            }
        """)
        if self.todo["done"]:
            self.setProperty("done", True)
            self.style().polish(self)

    def calculate_height(self):
        fm = QFontMetrics(self.title.font())
        text_width = self.title.width() - 30
        text = self.todo['text']
        
        # 计算文本行数
        lines = text.split('\n')
        line_count = sum(fm.elidedText(line, Qt.ElideRight, text_width).count('\n') + 1 for line in lines)
        
        # 计算总高度
        line_height = fm.lineSpacing()
        time_height = 30  # 时间区域高度
        padding = 40      # 边距和间距
        total_height = (line_height * line_count) + time_height + padding
        
        self.setMinimumHeight(max(100, total_height))

    def toggle_status(self):
        """通过ID找到对应任务并更新状态"""
        for task in self.parent.todos:
            if task["id"] == self.todo_id:
                task["done"] = self.checkbox.isChecked()
                break
        self.parent.save_data()
        self.parent.timeline.update()  # 触发时间轴更新

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景效果
        if self.property("done"):
            painter.setBrush(QColor(240, 255, 240))
        else:
            painter.setBrush(QColor(255, 245, 245))
            
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 8, 8)

    def showEvent(self, event):
        # 窗口显示时重新计算高度
        self.calculate_height()
        super().showEvent(event)

    def _handle_checkbox_change(self, state):
        """处理复选框状态变更"""
        for todo in self.parent.todos:
            if todo["id"] == self.todo_id:
                todo["done"] = (state == Qt.Checked)
                break
        self.parent.save_data()
        self.parent.update_list()  # 更新整个列表
        self.parent.timeline.update()  # 更新时间轴

    def toggle_done(self):
        self.parent.toggle_done(self.parent.list.itemAt(self.pos()))

class TimelineWidget(QWidget):
    def __init__(self, todos):
        super().__init__()
        self.todos = todos
        self.hover_index = -1
        self.setMinimumHeight(120)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        if not self.todos:
            # 绘制提示信息
            painter.setFont(QFont("Segoe UI", 12))
            painter.setPen(QColor(150, 150, 150))
            painter.drawText(
                self.rect().adjusted(20, 20, -20, -20),
                Qt.AlignCenter | Qt.TextWordWrap,
                "暂无任务数据\n点击下方“添加”按钮创建新任务"
            )
            return
        # 绘制背景
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        if not self.todos:
            return
            
        # 计算时间范围
        times = [datetime.fromisoformat(t["start"]) for t in self.todos]
        times += [datetime.fromisoformat(t["end"]) for t in self.todos]
        min_time = min(times)
        max_time = max(times)
        total_sec = (max_time - min_time).total_seconds()
        
        # 绘制时间轴基线
        axis_y = self.height() - 40
        painter.setPen(QPen(QColor(200, 200, 200), 2))
        painter.drawLine(50, axis_y, self.width()-50, axis_y)
        
        # 绘制时间块
        for i, todo in enumerate(self.todos):
            start = datetime.fromisoformat(todo["start"])
            end = datetime.fromisoformat(todo["end"])
            
            x1 = 50 + ((start - min_time).total_seconds() / total_sec) * (self.width() - 100)
            x2 = 50 + ((end - min_time).total_seconds()) / total_sec * (self.width() - 100)
            
            # 颜色设置
            if todo["done"]:
                color = QColor(76, 175, 80)
            elif i == self.hover_index:
                color = QColor(255, 193, 7)
            else:
                color = QColor(244, 67, 54)
                
            # 绘制时间块
            gradient = QLinearGradient(x1, 0, x2, 0)
            gradient.setColorAt(0, color.lighter(120))
            gradient.setColorAt(1, color.darker(120))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(x1, axis_y-15, x2-x1, 30), 6, 6)
            
            # 绘制标签
            if (x2 - x1) > 80:
                painter.setPen(QColor(255, 255, 255))
                text = todo["text"][:8] + "..." if len(todo["text"]) > 8 else todo["text"]
                painter.drawText(QRectF(x1, axis_y-15, x2-x1, 30), Qt.AlignCenter, text)

    def mouseMoveEvent(self, event):
        if not self.todos:
            return
        pos = event.pos()
        min_time = min(datetime.fromisoformat(t["start"]) for t in self.todos)
        max_time = max(datetime.fromisoformat(t["end"]) for t in self.todos)
        total_sec = (max_time - min_time).total_seconds()
        
        # 检测悬停
        self.hover_index = -1
        for i, todo in enumerate(self.todos):
            start = datetime.fromisoformat(todo["start"])
            end = datetime.fromisoformat(todo["end"])

            pos = event.pos()
            min_time = min(datetime.fromisoformat(t["start"]) for t in self.todos)
            max_time = max(datetime.fromisoformat(t["end"]) for t in self.todos)

            x1 = 50 + ((start - min_time).total_seconds()) / total_sec * (self.width() - 100)
            x2 = 50 + ((end - min_time).total_seconds()) / total_sec * (self.width() - 100)
            
            if x1 <= pos.x() <= x2 and (self.height()-70) <= pos.y() <= (self.height()-10):
                self.hover_index = i
                break
        
        
        self.update()

    def leaveEvent(self, event):
        self.hover_index = -1
        self.update()
