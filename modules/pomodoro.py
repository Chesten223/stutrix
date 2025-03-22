# pomodoro.py
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime
import math,os,json

class PomoModule(QWidget):
    timer_updated = pyqtSignal(int, str)  # 剩余时间(秒), 当前任务
    pomo_completed = pyqtSignal(dict)     # 完成数据
    task_started = pyqtSignal(str)        # 任务开始信号（带任务名称）
    task_stopped = pyqtSignal()           # 任务停止信号
    
    def __init__(self, todo_module):
        super().__init__()
        self.todo_module = todo_module
        self.records = []  # 存储所有完成的番茄钟记录
        self.is_working = True
        self.is_running = False
        self.work_duration = 25 * 60      # 默认25分钟
        self.break_duration = 5 * 60      # 默认5分钟
        self.remaining = self.work_duration
        self.current_task = None
        self.todo_module.task_updated.connect(self.update_task_list)
        self.init_ui()
        self.init_timer()
        self.update_display()
        self.load_data()  # 初始化时加载历史数据

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(40)

        # 左侧计时面板
        timer_panel = QFrame()
        timer_panel.setFixedWidth(400)
        timer_layout = QVBoxLayout(timer_panel)
        timer_layout.setContentsMargins(0, 0, 0, 0)
        timer_layout.setSpacing(20)

        # 进度圆环
        self.progress = PomoProgress(self)
        timer_layout.addWidget(self.progress, 0, Qt.AlignCenter)

        # 时间显示
        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                font: bold 36px Segoe UI;
                color: #333;
                margin-top: -20px;
            }
        """)
        timer_layout.addWidget(self.time_label)

        # 控制按钮
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self.toggle_timer)
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_timer)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.reset_btn)
        timer_layout.addLayout(btn_layout)

        # 右侧任务面板
        task_panel = QFrame()
        task_panel.setFixedWidth(300)
        task_layout = QVBoxLayout(task_panel)
        task_layout.setContentsMargins(20, 20, 20, 20)
        task_layout.setSpacing(15)

        # 任务选择
        self.task_combo = QComboBox()
        self.task_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border-radius: 6px;
                border: 1px solid #e0e0e0;
                font-size: 14px;
            }
        """)
        self.update_task_list()

        # 时间设置
        time_form = QFormLayout()
        self.work_time = QSpinBox()
        self.work_time.setRange(1, 60)
        self.work_time.setValue(25)
        self.work_time.valueChanged.connect(lambda v: setattr(self, 'work_duration', v*60))
        
        self.break_time = QSpinBox()
        self.break_time.setRange(1, 30)
        self.break_time.setValue(5)
        self.break_time.valueChanged.connect(lambda v: setattr(self, 'break_duration', v*60))
        
        time_form.addRow("工作时间（分钟）:", self.work_time)
        time_form.addRow("休息时间（分钟）:", self.break_time)

        task_layout.addWidget(QLabel("选择任务:"))
        task_layout.addWidget(self.task_combo)
        task_layout.addLayout(time_form)
        task_layout.addStretch()

        main_layout.addWidget(timer_panel)
        main_layout.addWidget(task_panel)

        # 样式设置
        self.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                border-radius: 8px;
                background: #2196F3;
                color: white;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover { background: #1976D2; }
            QPushButton:pressed { background: #0D47A1; }
            QFrame { 
                background: white; 
                border-radius: 16px;
                padding: 20px;
            }
        """)

    def init_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_timer)

    def update_task_list(self):
        """更新任务下拉列表"""
        self.task_combo.clear()
        self.task_combo.addItem("-- 选择任务 --", None)
        
        for todo in self.todo_module.todos:
            if not todo["done"]:
                self.task_combo.addItem(
                    f"{todo['text']} ({datetime.fromisoformat(todo['created']).strftime('%m/%d %H:%M')}",
                    todo["id"]
                )

    def toggle_timer(self):
        if self.task_combo.currentData() is None:
            QMessageBox.warning(self, "提示", "请先选择任务")
            return
            
        self.is_running = not self.is_running
        self.start_btn.setText("暂停" if self.is_running else "继续")
        
        if self.is_running:
            self.current_task = self.task_combo.currentText()
            self.task_started.emit(self.current_task)  # 发射带任务名称的信号
            self.timer.start()
        else:
            self.task_stopped.emit()  # 发射停止信号
            self.timer.stop()
            
        self.update_display()

    def reset_timer(self):
        self.is_running = False
        self.timer.stop()
        self.task_stopped.emit()  # 重要：重置时发射停止信号
        self.is_working = True
        self.remaining = self.work_duration
        self.update_display()
        self.start_btn.setText("开始")

    def update_timer(self):
        self.remaining -= 1
        if self.remaining <= 0:
            self.handle_complete()
        self.update_display()
        self.timer_updated.emit(self.remaining, self.current_task)

    def handle_complete(self):
        self.timer.stop()
        self.is_running = False
        
        # 记录当前完成的是工作阶段
        completed_is_work = self.is_working
        self.is_working = not self.is_working  # 切换阶段
        
        # 发送完成数据
        task_id = self.task_combo.currentData()
        if task_id and completed_is_work:  # 仅记录工作阶段
            duration = self.work_duration // 60
            record = {
                "task_id": task_id,
                "duration": duration,
                "timestamp": datetime.now().isoformat()
            }
            self.records.append(record)
            self.pomo_completed.emit(record)
            self.save_data()  # 每次完成时保存数据
        
        # 提示信息
        msg = QMessageBox()
        msg.setWindowTitle("周期完成" if completed_is_work else "休息结束")
        msg.setText("🎉 该休息一下了！" if completed_is_work else "🚀 开始新的工作周期！")
        msg.setIconPixmap(QPixmap("icons/success.png").scaled(64, 64))
        msg.exec_()
        self.task_stopped.emit()
        
        # 设置剩余时间
        self.remaining = self.break_duration if completed_is_work else self.work_duration
        self.start_btn.setText("开始")
        self.update_display()

    def save_data(self):
        """保存番茄钟数据到文件"""
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/pomo_data.json", "w") as f:
                json.dump(self.records, f, indent=2)
        except Exception as e:
            print("保存番茄钟数据失败:", e)

    def load_data(self):
        """加载番茄钟数据"""
        try:
            if os.path.exists("data/pomo_data.json"):
                with open("data/pomo_data.json", "r") as f:
                    self.records = json.load(f)
        except Exception as e:
            print("加载番茄钟数据失败:", e)

    def update_display(self):
        mins, secs = divmod(self.remaining, 60)
        self.time_label.setText(f"{mins:02}:{secs:02}")
        
        total = self.work_duration if self.is_working else self.break_duration
        self.progress.progress = 100 - (self.remaining / total) * 100
        self.progress.update()

class PomoProgress(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.progress = 0
        self.setFixedSize(300, 300)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取父模块状态
        pomo_module = self.parent().parent()  # 通过布局层级获取
        is_working = pomo_module.is_working if pomo_module else True

        # 绘制背景圆环
        painter.setPen(QPen(QColor("#e0e0e0"), 12))
        painter.drawEllipse(15, 15, 270, 270)

        # 绘制进度圆环
        gradient = QConicalGradient(150, 150, 90)
        gradient.setColorAt(0, QColor("#2196F3"))
        gradient.setColorAt(1, QColor("#9C27B0"))
        
        pen = QPen(gradient, 12)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        start_angle = 90 * 16
        span_angle = -int(self.progress * 3.6 * 16)
        painter.drawArc(15, 15, 270, 270, start_angle, span_angle)

        # 绘制中心文字
        painter.setFont(QFont("Segoe UI", 24, QFont.Bold))
        painter.setPen(QColor("#333"))
        painter.drawText(
            self.rect(),
            Qt.AlignCenter,
            "工作中" if is_working else "休息中"
        )

        # 绘制进度百分比
        painter.setFont(QFont("Segoe UI", 16))
        painter.drawText(
            QRect(0, 60, 300, 100),
            Qt.AlignCenter,
            f"{self.progress:.1f}%"
        )