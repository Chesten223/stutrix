# main.py
import sys , os
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView

# 导入各功能模块
from modules.search import SearchModule
from modules.todo import TodoModule
from modules.card_memory import CardMemoryModule
from modules.notes import NotesModule
from modules.pomodoro import PomoModule
from modules.music import MusicModule
from modules.stats import StatsModule
from modules.settings import SettingsModule
from modules.data_manager import DataManager

import logging

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = {}
        self.todo_count = 0
        self.current_task = ""
        self.important_date = datetime.now() + timedelta(days=7)
        self.current_module = "首页"  # 当前模块名称
        self.active_pomo_task = None  # 新增：活动的番茄钟任务
        # 初始化前加载设置
        self.load_settings()
        self.data_manager = DataManager()  # 新增
        # 主窗口设置
        self.setWindowTitle("Stutrix")
        self.setGeometry(100, 100, 1400, 900)
        self.setup_ui()
        self.setup_modules()
        self.setup_signals()
        
        # 初始化样式
        self.apply_theme(self.settings.get("theme", "default"))

    def setup_ui(self):
        """初始化主界面布局"""
        # 主窗口中心部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航栏
        self.setup_navigation(main_layout)
        
        # 右侧堆叠窗口
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)
        
        # 顶部菜单栏
        self.setup_menu()
        
        # 底部状态栏
        self.setup_statusbar()

    def setup_navigation(self, parent_layout):
        """初始化左侧导航栏"""
        nav_frame = QFrame()
        nav_frame.setFixedWidth(80)
        nav_frame.setStyleSheet("""
            background: #f8f9fa;
            border-right: 1px solid #e0e0e0;
        """)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 20, 8, 20)
        nav_layout.setSpacing(12)

        # 导航项配置
        nav_items = [
            ("icons/search.svg", "搜索"),
            ("icons/todo.svg", "待办"),
            ("icons/cards.svg", "卡片"),
            ("icons/notes.svg", "笔记"),
            ("icons/pomo.svg", "番茄"),
            ("icons/music.svg", "音乐"),
            ("icons/stats.svg", "统计"),
            ("icons/settings.svg", "设置")
        ]

        self.nav_buttons = []
        for icon_path, text in nav_items:
            btn = NavButton(icon_path, text)
            btn.clicked.connect(lambda _, t=text: self.switch_module(t))
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()
        parent_layout.addWidget(nav_frame)

    def setup_menu(self):
        """初始化顶部菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        file_menu.addAction("新建会话", self.new_session)
        file_menu.addAction("导入数据...", self.import_data)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        # 视图菜单
        view_menu = menubar.addMenu("视图")
        view_menu.addAction("全屏模式", self.toggle_fullscreen)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        help_menu.addAction("用户手册", self.show_help)
        help_menu.addAction("关于", self.show_about)

    def setup_statusbar(self):
        """初始化底部状态栏"""
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #ffffff;
                border-top: 1px solid #eeeeee;
                font: 12px Segoe UI;
            }
        """)
        
        # 状态栏组件
        self.time_label = QLabel()
        self.task_label = QLabel()
        self.countdown_label = QLabel()
        
        self.status_bar.addPermanentWidget(self.time_label, 1)
        self.status_bar.addPermanentWidget(self.task_label, 2)
        self.status_bar.addPermanentWidget(self.countdown_label, 1)
        
        # 定时更新
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_status)
        self.timer.start(100)

    def setup_modules(self):
        """初始化各功能模块"""
        # 注意模块初始化顺序
        self.todo_module = TodoModule()
        self.modules = {
            "搜索": SearchModule(),
            "待办": self.todo_module,
            "卡片": CardMemoryModule(),
            "笔记": NotesModule(),
            "番茄": PomoModule(self.todo_module),
            "音乐": MusicModule(),
            "统计": StatsModule(),
            "设置": SettingsModule(self)
        }
        
        for name, module in self.modules.items():
            self.stack.addWidget(module)

    def setup_signals(self):
        """连接模块间信号"""
        # 搜索 -> 笔记
        self.modules["搜索"].new_note_signal.connect(self.modules["笔记"].add_note)
        # 连接番茄钟信号
        self.modules["番茄"].task_started.connect(self.on_pomo_task_start)
        self.modules["番茄"].task_stopped.connect(self.on_pomo_task_stop)
        # 待办 -> 状态栏
        self.todo_module.count_changed.connect(self.update_todo_count)
        # 确保连接待办模块的更新信号
        self.modules["待办"].task_updated.connect(
            lambda: self.modules["番茄"].update_task_list()
        )
        # 番茄钟 -> 统计
        self.modules["番茄"].pomo_completed.connect(
            lambda data: self.modules["统计"].add_pomo_record(data))
        # self.modules["统计"].refresh_data.connect(self.modules["统计"].refresh_data)
        # 设置 -> 全局
        self.modules["设置"].theme_changed.connect(self.apply_theme)
        self.modules["设置"].data_imported.connect(self.reload_all_data)

        self.modules["音乐"].play_state_changed.connect(
            lambda state: self.update_music_status(state))
        # main.py setup_signals方法中添加
        # self.modules["待办"].task_updated.connect(self.modules["统计"].refresh)
        # self.modules["卡片"].data_updated.connect(self.modules["统计"].refresh)
        # self.modules["笔记"].content_updated.connect(self.modules["统计"].refresh)
        # self.modules["番茄"].pomo_completed.connect(self.modules["统计"].refresh)
        # self.modules["设置"].data_imported.connect(self.modules["统计"].refresh)

    def on_pomo_task_start(self, task_name):
        """处理番茄任务开始"""
        self.active_pomo_task = task_name
        self.update_status()

    def on_pomo_task_stop(self):
        """处理番茄任务停止"""
        self.active_pomo_task = None
        self.update_status()

    def switch_module(self, module_name):
        """切换功能模块"""
        if module_name in self.modules:
            self.stack.setCurrentWidget(self.modules[module_name])
            self.current_module = module_name
            self.update_status()  # 更新状态栏但不影响番茄任务显示

    def update_status(self):
        """更新状态栏信息"""
        # 时间显示
        now = datetime.now()
        time_str = now.strftime("%Y-%m-%d %A %H:%M:%S.") + f"{now.microsecond//1000:03d}"
        self.time_label.setText(f"🕒 {time_str}")
        
        # 任务信息显示逻辑

        task_str = f"🧮 模块：{self.current_module}"
        if self.todo_count > 0:
            task_str += f" | 待办剩余：{self.todo_count}"
        if self.active_pomo_task !=None:    
            task_str += f"📌 当前任务：{self.active_pomo_task}"
        self.task_label.setText(task_str)


        # 倒计时
        delta = self.important_date - datetime.now()
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        countdown_str = (f"⏳ 重要日期倒计时: {days}d {hours:02}:{minutes:02}:{seconds:02}."
                        f"{delta.microseconds//1000:03d}")
        self.countdown_label.setText(countdown_str)

    def update_music_status(self, is_playing):
        """更新状态栏音乐图标"""
        icon = "▶️" if is_playing else "⏸️"
        self.status_bar.showMessage(f"{icon} 正在播放音乐", 2000)

    def apply_theme(self, theme_name):
        """应用主题设置"""
        palette = QPalette()
        if theme_name == "深色模式":
            palette.setColor(QPalette.Window, QColor(53,53,53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25,25,25))
            palette.setColor(QPalette.AlternateBase, QColor(53,53,53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53,53,53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Highlight, QColor(142,45,197).lighter())
            palette.setColor(QPalette.HighlightedText, Qt.black)
        else:  # 默认浅色
            palette = self.style().standardPalette()
        
        self.setPalette(palette)
        self.settings["theme"] = theme_name
        self.save_settings()

    def reload_all_data(self):
        """重新加载所有模块数据"""
        for module in self.modules.values():
            if hasattr(module, 'load_data'):
                module.load_data()

    def load_settings(self):
        """加载全局设置"""
        try:
            with open("data/settings.json") as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            self.settings = {"theme": "default"}

    def save_settings(self):
        """保存全局设置"""
        with open("data/settings.json", "w") as f:
            json.dump(self.settings, f, indent=2)

    # --------------------- 事件处理 ---------------------
    def closeEvent(self, event):
        """关闭事件处理"""
        # 保存所有模块数据
        for module in self.modules.values():
            if hasattr(module, 'save_data'):
                module.save_data()
        # 保存全局设置
        self.save_settings()
        super().closeEvent(event)

    def toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def update_todo_count(self, count):
        """更新待办计数"""
        self.todo_count = count

    def new_session(self):
        """新建会话"""
        self.reload_all_data()
        QMessageBox.information(self, "新建会话", "已重置所有模块到初始状态")

    def import_data(self):
        """导入数据"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "", "备份文件 (*.backup)")
        if path:
            # 实际导入操作在SettingsModule实现
            self.modules["设置"].import_data(path)

    def show_help(self):
        """显示帮助文档"""
        text = """快捷键指南：
        Ctrl+N - 新建会话
        Ctrl+S - 保存数据
        Ctrl+Q - 退出程序
        F11    - 全屏切换"""
        QMessageBox.information(self, "帮助", text)

    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(self, "关于", 
            "学习套件 v1.0\nDeveloped by DeepSeek")

class NavButton(QToolButton):
    """自定义导航按钮"""
    def __init__(self, icon_path, text):
        super().__init__()
        self.setIcon(QIcon(icon_path))
        self.setIconSize(QSize(32, 32))
        self.setToolTip(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QToolButton {
                background: transparent;
                padding: 12px;
                border-radius: 8px;
            }
            QToolButton:hover { background: #e3f2fd; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 加载自定义字体
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    #使用更可靠的播放后端
    os.environ["QT_MULTIMEDIA_PREFERRED_PLUGINS"] = "windowsmediafoundation"  # Windows系统
    # 初始化主窗口
    window = MainWindow()
    window.show()
    
    # 检查数据目录
    try:
        os.makedirs("data/backups", exist_ok=True)
    except Exception as e:
        QMessageBox.critical(None, "错误", f"无法创建数据目录: {str(e)}")
    
    sys.exit(app.exec_())