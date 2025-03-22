# settings.py
import json
import shutil
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from datetime import datetime

class SettingsModule(QWidget):
    theme_changed = pyqtSignal(str)
    api_key_changed = pyqtSignal(str)
    data_imported = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.config = {}
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 分页选项卡
        tab = QTabWidget()
        
        # 通用设置
        general_tab = QWidget()
        self.init_general_tab(general_tab)
        tab.addTab(general_tab, "通用")

        # 账户设置
        account_tab = QWidget()
        self.init_account_tab(account_tab)
        tab.addTab(account_tab, "账户")

        # 数据管理
        data_tab = QWidget()
        self.init_data_tab(data_tab)
        tab.addTab(data_tab, "数据")

        # 关于
        about_tab = QWidget()
        self.init_about_tab(about_tab)
        tab.addTab(about_tab, "关于")

        main_layout.addWidget(tab)
        self.setLayout(main_layout)
        self.setStyleSheet("""
            QWidget { background: white; }
            QGroupBox { 
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)

    def init_general_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        # 主题设置
        theme_group = QGroupBox("界面主题")
        theme_layout = QHBoxLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认浅色", "深色模式", "护眼模式"])
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        theme_layout.addWidget(QLabel("主题选择:"))
        theme_layout.addWidget(self.theme_combo)
        theme_group.setLayout(theme_layout)

        # 字体设置
        font_group = QGroupBox("字体设置")
        font_layout = QFormLayout()
        self.font_size = QSpinBox()
        self.font_size.setRange(10, 20)
        self.font_family = QFontComboBox()
        font_layout.addRow("字体大小:", self.font_size)
        font_layout.addRow("字体类型:", self.font_family)
        font_group.setLayout(font_layout)

        layout.addWidget(theme_group)
        layout.addWidget(font_group)
        layout.addStretch()

    def init_account_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        # API密钥
        api_group = QGroupBox("API 设置")
        api_layout = QFormLayout()
        
        self.deepseek_key = QLineEdit()
        self.deepseek_key.setEchoMode(QLineEdit.Password)
        self.deepseek_key.textChanged.connect(self.save_api_key)  # 新增实时保存
        
        api_layout.addRow("DeepSeek API Key:", self.deepseek_key)
        api_group.setLayout(api_layout)

        layout.addWidget(api_group)
        layout.addStretch()

    def save_api_key(self):
        """实时保存API密钥"""
        self.config.setdefault('api_keys', {})['deepseek'] = self.deepseek_key.text().strip()
        self.api_key_changed.emit(self.deepseek_key.text())  # 发射信号
        self.save_settings()

    def init_data_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        # 数据操作
        btn_import = QPushButton("导入数据")
        btn_export = QPushButton("导出数据")
        btn_backup = QPushButton("创建备份")
        btn_restore = QPushButton("恢复备份")

        btn_import.clicked.connect(self.import_data)
        btn_export.clicked.connect(self.export_data)
        btn_backup.clicked.connect(self.create_backup)
        btn_restore.clicked.connect(self.restore_backup)

        # 路径设置
        path_group = QGroupBox("存储路径")
        path_layout = QHBoxLayout()
        self.data_path = QLineEdit()
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self.choose_data_path)
        path_layout.addWidget(self.data_path)
        path_layout.addWidget(btn_browse)
        path_group.setLayout(path_layout)

        layout.addWidget(path_group)
        layout.addWidget(btn_import)
        layout.addWidget(btn_export)
        layout.addWidget(btn_backup)
        layout.addWidget(btn_restore)
        layout.addStretch()

    def init_about_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        about_text = f"""
        <h3>学习套件 v1.0</h3>
        <p>开发者: DeepSeek & 青尘Chesten</p>
        <p>许可证: MIT</p>
        <p>项目主页: 
            </并没有>
        </p>
        <p>技术支持: Deepseek R1</p>
        """
        label = QLabel(about_text)
        label.setOpenExternalLinks(True)
        
        layout.addWidget(label)
        layout.addStretch()

    def load_settings(self):
        try:
            with open("data/settings.json") as f:
                self.config = json.load(f)
                self.theme_combo.setCurrentText(self.config.get("theme", "默认浅色"))
                self.font_size.setValue(self.config.get("font_size", 12))
                self.font_family.setCurrentFont(QFont(self.config.get("font", "Segoe UI")))
                self.deepseek_key.setText(self.config.get("api_keys", {}).get("deepseek", ""))
                self.data_path.setText(self.config.get("data_path", "./data"))
        except FileNotFoundError:
            self.config = {}

    def save_settings(self):
        self.config.update({
            "theme": self.theme_combo.currentText(),
            "font_size": self.font_size.value(),
            "font": self.font_family.currentFont().family(),
            "api_keys": {
                "deepseek": self.deepseek_key.text()
            },
            "data_path": self.data_path.text()
        })
        with open("data/settings.json", "w") as f:
            json.dump(self.config, f, indent=2)

    def change_theme(self, index):
        theme = self.theme_combo.itemText(index)
        self.theme_changed.emit(theme.lower())
        self.save_settings()

    def choose_data_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择数据存储路径")
        if path:
            self.data_path.setText(path)
            self.save_settings()

    def import_data(self):
        path = QFileDialog.getOpenFileName(self, "选择数据文件", "", "备份文件 (*.backup)")[0]
        if path:
            try:
                shutil.unpack_archive(path, self.data_path.text(), 'zip')
                self.data_imported.emit()
                QMessageBox.information(self, "导入成功", "数据已成功恢复！")
            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"错误：{str(e)}")

    def export_data(self):
        path = QFileDialog.getSaveFileName(self, "导出数据", "study_suite.backup", "备份文件 (*.backup)")[0]
        if path:
            try:
                shutil.make_archive(path.replace('.backup', ''), 'zip', self.data_path.text())
                QMessageBox.information(self, "导出成功", "数据已备份到指定路径")
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"错误：{str(e)}")

    # def create_backup(self):
    #     self.export_data()  # 复用导出逻辑
    # settings.py 中的备份方法
    def create_backup(self):
        backup_path = f"{self.data_path.text()}/backups"
        shutil.make_archive(f"{backup_path}/backup", 'zip', self.data_path.text())
    def restore_backup(self):
        self.import_data()  # 复用导入逻辑

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    # def init_audio_settings(self):
    #     group = QGroupBox("音频设置")
    #     layout = QVBoxLayout()
        
    #     # 选择首选音频格式
    #     self.format_combo = QComboBox()
    #     self.format_combo.addItems(["自动", "WAV优先", "MP3优先"])
    #     layout.addWidget(QLabel("首选播放格式:"))
    #     layout.addWidget(self.format_combo)
        
    #     # 启用/禁用硬件解码
    #     self.hw_accel_check = QCheckBox("启用硬件加速解码")
    #     layout.addWidget(self.hw_accel_check)
        
    #     group.setLayout(layout)
    #     return group

# 在main.py中的整合步骤：
# 1. 添加导入
# from settings import SettingsModule

# 2. 修改模块初始化
# self.modules["设置"] = SettingsModule(self)

# 3. 连接信号
# self.modules["设置"].theme_changed.connect(self.apply_theme)
# self.modules["设置"].api_key_changed.connect(self.modules["搜索"].set_api_key)
# self.modules["设置"].data_imported.connect(self.reload_all_data)

