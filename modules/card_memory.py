# card_memory.py
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

CARD_FILE = "data/card_data.json"

class CardMemoryModule(QWidget):
    data_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self.tags = []
        self.folders = ["默认文件夹"]
        self.current_folder = "默认文件夹"
        self.current_tag = ""
        self.init_ui()
        self.load_data()

    class Card:
        def __init__(self, title, answer, tags, folder, proficiency=0, last_practiced=None):
            self.title = title
            self.answer = answer
            self.tags = tags if isinstance(tags, list) else [tags]
            self.folder = folder
            self.proficiency = proficiency
            self.last_practiced = last_practiced or datetime.now()

        def update_proficiency(self, delta):
            self.proficiency = max(0, min(100, self.proficiency + delta))
            self.last_practiced = datetime.now()
            
        def decay_proficiency(self):
            if self.proficiency >= 100:
                return
            time_since = datetime.now() - self.last_practiced
            if time_since > timedelta(hours=6):
                decay = (time_since // timedelta(hours=6)) * 20
                self.proficiency = max(0, self.proficiency - decay)
                self.last_practiced = datetime.now()

        def to_dict(self):
            return {
                'title': self.title,
                'answer': self.answer,
                'tags': self.tags,
                'folder': self.folder,
                'proficiency': self.proficiency,
                'last_practiced': self.last_practiced.isoformat()
            }
        
        @classmethod
        def from_dict(cls, data):
            return cls(
                data['title'],
                data['answer'],
                data.get('tags', []),
                data.get('folder', '默认文件夹'),
                data.get('proficiency', 0),
                datetime.fromisoformat(data['last_practiced'])
            )

    class CardWidget(QWidget):
        rightClicked = pyqtSignal(object)
        doubleClicked = pyqtSignal(object)

        def __init__(self, card, parent=None):
            super().__init__(parent)
            self.card = card
            self.init_ui()
            self.setFixedSize(300, 180)
            self.setStyleSheet("""
                background: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            """)

        def init_ui(self):
            layout = QVBoxLayout()
            title = QLabel(self.card.title)
            title.setFont(QFont("Segoe UI", 14, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            
            progress = QProgressBar()
            progress.setValue(self.card.proficiency)
            progress.setTextVisible(False)
            progress.setStyleSheet("""
                QProgressBar {
                    height: 8px;
                    background: #e0e0e0;
                    border-radius: 4px;
                }
                QProgressBar::chunk {
                    background: #2196F3;
                    border-radius: 4px;
                }
            """)
            
            layout.addWidget(title)
            layout.addWidget(progress)
            self.setLayout(layout)

        def mousePressEvent(self, event):
            if event.button() == Qt.RightButton:
                self.rightClicked.emit(self.card)
                
        def mouseDoubleClickEvent(self, event):
            self.doubleClicked.emit(self.card)

    class NewCardDialog(QDialog):
        def __init__(self, folders, tags, card=None, parent=None):
            super().__init__(parent)
            self.setWindowTitle("编辑卡片" if card else "新建卡片")
            self.setFixedSize(400, 400)
            
            self.folder_combo = QComboBox()
            self.folder_combo.addItems(folders)
            self.title_input = QLineEdit()
            self.answer_input = QTextEdit()
            self.tag_list = QListWidget()
            self.tag_list.setSelectionMode(QListWidget.MultiSelection)
            self.tag_list.addItems(tags)

            if card:
                self.title_input.setText(card.title)
                self.answer_input.setPlainText(card.answer)
                self.folder_combo.setCurrentText(card.folder)
                for i in range(self.tag_list.count()):
                    item = self.tag_list.item(i)
                    item.setSelected(item.text() in card.tags)

            layout = QVBoxLayout()
            layout.addWidget(QLabel("文件夹:"))
            layout.addWidget(self.folder_combo)
            layout.addWidget(QLabel("标题:"))
            layout.addWidget(self.title_input)
            layout.addWidget(QLabel("标签:"))
            layout.addWidget(self.tag_list)
            layout.addWidget(QLabel("内容:"))
            layout.addWidget(self.answer_input)
            
            btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            btn_box.accepted.connect(self.accept)
            btn_box.rejected.connect(self.reject)
            layout.addWidget(btn_box)
            
            self.setLayout(layout)

        def get_card_data(self):
            return {
                'title': self.title_input.text().strip(),
                'answer': self.answer_input.toPlainText().strip(),
                'folder': self.folder_combo.currentText(),
                'tags': [item.text() for item in self.tag_list.selectedItems()]
            }

    class StudyDialog(QDialog):
        def __init__(self, cards, parent=None):
            super().__init__(parent)
            self.cards = cards
            self.current_index = 0
            self.init_ui()
            self.setup_shortcuts()
            self.show_card()

        def init_ui(self):
            self.setWindowTitle("学习模式")
            self.setMinimumSize(600, 400)
            layout = QVBoxLayout()
            
            self.title_label = QLabel()
            self.title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
            self.title_label.setAlignment(Qt.AlignCenter)
            
            self.answer_label = QLabel()
            self.answer_label.setFont(QFont("Segoe UI", 14))
            self.answer_label.setAlignment(Qt.AlignCenter)
            self.answer_label.hide()
            
            btn_layout = QHBoxLayout()
            buttons = [
                ("陌生 (1)", "#e74c3c", -20),
                ("不熟 (2)", "#f1c40f", 0),
                ("掌握 (3)", "#2ecc71", 20)
            ]
            
            for text, color, delta in buttons:
                btn = QPushButton(text)
                btn.setStyleSheet(f"background: {color}; color: white;")
                btn.clicked.connect(lambda _, d=delta: self.handle_answer(d))
                btn_layout.addWidget(btn)
            
            layout.addWidget(self.title_label)
            layout.addWidget(self.answer_label)
            layout.addLayout(btn_layout)
            self.setLayout(layout)

        def setup_shortcuts(self):
            QShortcut(QKeySequence("1"), self).activated.connect(lambda: self.handle_answer(-20))
            QShortcut(QKeySequence("2"), self).activated.connect(lambda: self.handle_answer(0))
            QShortcut(QKeySequence("3"), self).activated.connect(lambda: self.handle_answer(20))
            QShortcut(Qt.Key_Space, self).activated.connect(self.toggle_answer)

        def toggle_answer(self):
            self.answer_label.setVisible(not self.answer_label.isVisible())

        def show_card(self):
            card = self.cards[self.current_index]
            self.title_label.setText(card.title)
            self.answer_label.setText(card.answer)

        def handle_answer(self, delta):
            card = self.cards[self.current_index]
            card.update_proficiency(delta)
            self.current_index += 1
            if self.current_index < len(self.cards):
                self.show_card()
            else:
                self.parent().save_data()  # 学习完成后自动保存
                self.accept()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 左侧控制面板
        left_panel = QWidget()
        left_panel.setFixedWidth(250)
        left_layout = QVBoxLayout(left_panel)

        # 文件夹管理
        folder_group = QGroupBox("文件夹管理")
        folder_layout = QVBoxLayout()
        self.folder_list = QListWidget()
        self.folder_list.addItems(self.folders)
        self.folder_list.itemClicked.connect(self.filter_by_folder)
        self.folder_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folder_list.customContextMenuRequested.connect(self.show_folder_context_menu)
        self.btn_new_folder = QPushButton("新建文件夹")
        self.btn_new_folder.clicked.connect(self.create_folder)
        folder_layout.addWidget(self.folder_list)
        folder_layout.addWidget(self.btn_new_folder)
        folder_group.setLayout(folder_layout)

        # 标签管理
        tag_group = QGroupBox("标签管理")
        tag_layout = QVBoxLayout()
        self.tag_list = QListWidget()
        self.tag_list.addItems(self.tags)
        self.tag_list.itemClicked.connect(self.filter_by_tag)
        self.tag_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tag_list.customContextMenuRequested.connect(self.show_tag_context_menu)
        self.btn_new_tag = QPushButton("新建标签")
        self.btn_new_tag.clicked.connect(self.create_tag)
        tag_layout.addWidget(self.tag_list)
        tag_layout.addWidget(self.btn_new_tag)
        tag_group.setLayout(tag_layout)

        left_layout.addWidget(folder_group)
        left_layout.addWidget(tag_group)
        left_layout.addStretch()

        # 右侧卡片区域
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.card_container = QWidget()
        self.card_layout = QGridLayout()
        self.card_layout.setAlignment(Qt.AlignTop)
        self.card_container.setLayout(self.card_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.card_container)
        
        control_layout = QHBoxLayout()
        self.btn_new_card = QPushButton("新建卡片")
        self.btn_new_card.clicked.connect(self.create_card)
        self.btn_study = QPushButton("开始学习")
        self.btn_study.clicked.connect(self.start_study)
        control_layout.addWidget(self.btn_new_card)
        control_layout.addWidget(self.btn_study)
        
        right_layout.addLayout(control_layout)
        right_layout.addWidget(scroll)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)

    def show_folder_context_menu(self, pos):
        item = self.folder_list.itemAt(pos)
        if not item:
            return

        menu = QMenu()
        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(lambda: self.rename_folder(item))
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_folder(item))
        
        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.exec_(self.folder_list.viewport().mapToGlobal(pos))

    def rename_folder(self, item):
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "重命名文件夹", "新名称:", text=old_name)
        if ok and new_name and new_name != old_name:
            # 更新文件夹列表
            index = self.folders.index(old_name)
            self.folders[index] = new_name
            item.setText(new_name)
            
            # 更新相关卡片（关键修改：保持从属关系）
            for card in self.cards:
                if card.folder == old_name:
                    card.folder = new_name
            self.save_data()
            self.update_card_display()

    def delete_folder(self, item):
        folder_name = item.text()
        if folder_name == "默认文件夹":
            QMessageBox.warning(self, "警告", "默认文件夹不能删除")
            return

        # 移动卡片到默认文件夹
        for card in self.cards:
            if card.folder == folder_name:
                card.folder = "默认文件夹"
                
        self.folders.remove(folder_name)
        self.folder_list.takeItem(self.folder_list.row(item))
        self.save_data()
        self.update_card_display()

    def show_tag_context_menu(self, pos):
        item = self.tag_list.itemAt(pos)
        if not item:
            return

        menu = QMenu()
        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(lambda: self.rename_tag(item))
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_tag(item))
        
        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.exec_(self.tag_list.viewport().mapToGlobal(pos))

    def rename_tag(self, item):
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "重命名标签", "新名称:", text=old_name)
        if ok and new_name and new_name != old_name:
            # 更新标签列表
            index = self.tags.index(old_name)
            self.tags[index] = new_name
            item.setText(new_name)
            
            # 更新相关卡片
            for card in self.cards:
                if old_name in card.tags:
                    card.tags[card.tags.index(old_name)] = new_name
            self.save_data()
            self.update_card_display()

    def delete_tag(self, item):
        tag_name = item.text()
        # 从标签列表删除
        self.tags.remove(tag_name)
        self.tag_list.takeItem(self.tag_list.row(item))
        
        # 从所有卡片中移除该标签
        for card in self.cards:
            if tag_name in card.tags:
                card.tags.remove(tag_name)
        self.save_data()
        self.update_card_display()

    # 其余方法保持不变（create_folder, create_tag, filter_by_folder等）
    # ...（保持原有方法实现不变）
    def create_folder(self):
        folder, ok = QInputDialog.getText(self, "新建文件夹", "输入文件夹名称:")
        if ok and folder:
            if folder not in self.folders:
                self.folders.append(folder)
                self.folder_list.addItem(folder)
                self.save_data()

    def create_tag(self):
        tag, ok = QInputDialog.getText(self, "新建标签", "输入标签名称:")
        if ok and tag:
            if tag not in self.tags:
                self.tags.append(tag)
                self.tag_list.addItem(tag)
                self.save_data()

    def filter_by_folder(self, item):
        self.current_folder = item.text()
        self.update_card_display()

    def filter_by_tag(self, item):
        self.current_tag = item.text()
        self.update_card_display()

    def update_card_display(self):
        while self.card_layout.count():
            child = self.card_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        filtered = [
            c for c in self.cards 
            if c.folder == self.current_folder and 
            (not self.current_tag or self.current_tag in c.tags)
        ]
        
        row = col = 0
        max_cols = max(1, self.card_container.width() // 320)
        
        for card in filtered:
            widget = self.CardWidget(card)
            widget.doubleClicked.connect(lambda _, c=card: self.preview_card(c))
            widget.rightClicked.connect(lambda _, c=card: self.show_context_menu(c))
            self.card_layout.addWidget(widget, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1


    def create_card(self):
        dialog = self.NewCardDialog(self.folders, self.tags, parent=self)
        if dialog.exec_():
            new_data = dialog.get_card_data()
            if new_data['title'] and new_data['answer']:
                new_card = self.Card(
                    title=new_data['title'],
                    answer=new_data['answer'],
                    tags=new_data['tags'],
                    folder=new_data['folder'],
                    proficiency=0
                )
                self.cards.append(new_card)
                self.save_data()
                self.update_card_display()

    def load_data(self):
        try:
            with open(CARD_FILE, "r") as f:
                data = json.load(f)
                self.tags = data.get('tags', [])
                self.folders = data.get('folders', ["默认文件夹"])
                self.cards = [self.Card.from_dict(c) for c in data.get('cards', [])]
                self.folder_list.clear()
                self.folder_list.addItems(self.folders)
                self.tag_list.clear()
                self.tag_list.addItems(self.tags)
                self.update_card_display()
        except FileNotFoundError:
            pass

    def save_data(self):
        data = {
            'tags': self.tags,
            'folders': self.folders,
            'cards': [c.to_dict() for c in self.cards]
        }
        with open(CARD_FILE, "w") as f:
            json.dump(data, f, indent=2)
        self.data_updated.emit()

    # 其余方法保持不变（update_card_display, preview_card等）
    # ...（保持原有方法实现不变）
    def preview_card(self, card):
        dialog = QDialog(self)
        dialog.setWindowTitle(card.title)
        layout = QVBoxLayout()
        text = QTextEdit(card.answer)
        text.setReadOnly(True)
        layout.addWidget(text)
        dialog.setLayout(layout)
        dialog.exec_()

    def show_context_menu(self, card):
        menu = QMenu()
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(lambda: self.edit_card(card))
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_card(card))
        menu.addActions([edit_action, delete_action])
        menu.exec_(QCursor.pos())

    def edit_card(self, card):
        dialog = self.NewCardDialog(self.folders, self.tags, card, self)
        if dialog.exec_():
            new_data = dialog.get_card_data()
            card.title = new_data['title']
            card.answer = new_data['answer']
            card.tags = new_data['tags']
            card.folder = new_data['folder']
            self.save_data()
            self.update_card_display()

    def delete_card(self, card):
        confirm = QMessageBox.question(
            self, "删除确认", 
            f"确定删除卡片：{card.title}？",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.cards.remove(card)
            self.save_data()
            self.update_card_display()

    def start_study(self):
        if not self.tag_list.selectedItems():
            QMessageBox.warning(self, "错误", "请先选择要学习的标签")
            return
            
        selected_tag = self.tag_list.currentItem().text()
        filtered = [c for c in self.cards if selected_tag in c.tags]
        
        # 应用遗忘曲线
        for card in filtered:
            card.decay_proficiency()
        
        # 筛选需要复习的卡片
        to_study = [
            c for c in filtered 
            if c.proficiency < 100 or 
            (datetime.now() - c.last_practiced) > timedelta(days=3)
        ]
        
        if not to_study:
            QMessageBox.information(self, "提示", "当前没有需要复习的卡片")
            return
            
        study_dialog = self.StudyDialog(to_study, self)
        study_dialog.exec_()
        self.save_data()

    def resizeEvent(self, event):
        self.update_card_display()
        super().resizeEvent(event)
        
if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = CardMemoryModule()
    window.show()
    sys.exit(app.exec_())