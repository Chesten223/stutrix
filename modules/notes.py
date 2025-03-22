# notes.py
import json
import os
import datetime
from datetime import datetime
import markdown
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWebEngineWidgets import QWebEngineView

NOTES_FILE = "data/notes_data.json"
NOTES_DIR = "data/notes"

class NotesModule(QWidget):
    content_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.notes = []
        self.tags = ["所有标签", "无标签"]
        self.current_note = None
        self.expanded_items = set()
        
        os.makedirs(NOTES_DIR, exist_ok=True)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # 左侧导航面板（保持不变）
        left_panel = self.create_left_panel()
        
        # 右侧编辑预览区（新增分栏布局）
        right_panel = self.create_right_panel()
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        self.setStyleSheet("""
            QTreeWidget, QListWidget {
                background: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
            QLineEdit, QTextEdit {
                padding: 8px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
        """)

    def create_left_panel(self):
        panel = QWidget()
        panel.setFixedWidth(300)
        layout = QVBoxLayout(panel)
        
        self.mode_tabs = QTabWidget()
        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.itemClicked.connect(self.load_note)
        self.folder_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        self.tag_list = QListWidget()
        self.tag_list.addItem("无标签")
        self.tag_list.itemClicked.connect(self.filter_by_tag)
        self.tag_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tag_list.customContextMenuRequested.connect(self.show_tag_context_menu)
        
        self.mode_tabs.addTab(self.folder_tree, "文件夹")
        self.mode_tabs.addTab(self.tag_list, "标签筛选")
        
        self.new_btn = QPushButton("新建笔记")
        self.new_btn.clicked.connect(self.create_note)
        self.new_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3;
                color: white;
                padding: 12px;
                border-radius: 8px;
                font-weight: 500;
            }
            QPushButton:hover { background: #1976D2; }
        """)
        
        layout.addWidget(self.mode_tabs)
        layout.addWidget(self.new_btn)
        return panel

    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 标题和标签水平布局
        header_layout = QHBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("输入标题...")
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("输入标签（逗号分隔）...")
        header_layout.addWidget(self.title_input, 3)
        header_layout.addWidget(self.tag_input, 2)
        
        # 统一标题栏
        titles_layout = QHBoxLayout()
        editor_title = QLabel("编辑区（支持Markdown + LaTeX）")
        preview_title = QLabel("预览区")
        for title in [editor_title, preview_title]:
            title.setStyleSheet("""
                QLabel {
                    font: bold 14px 'Segoe UI';
                    color: #2c3e50;
                    padding: 8px 0;
                }
            """)
        titles_layout.addWidget(editor_title, 1)
        titles_layout.addWidget(preview_title, 1)
        
        # 左右分栏布局
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧编辑区
        editor_box = QWidget()
        editor_layout = QVBoxLayout(editor_box)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QTextEdit()
        self.editor.textChanged.connect(self.update_preview)
        editor_layout.addWidget(self.editor)
        
        # 右侧预览区
        preview_box = QWidget()
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview = QWebEngineView()
        preview_layout.addWidget(self.preview)
        
        splitter.addWidget(editor_box)
        splitter.addWidget(preview_box)
        splitter.setSizes([500, 500])
        
        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.save_current)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #4CAF50;
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
            }
            QPushButton:hover { background: #45a049; }
        """)
        
        layout.addLayout(header_layout)
        layout.addLayout(titles_layout)  # 添加统一标题栏
        layout.addWidget(splitter, 1)
        layout.addWidget(self.save_btn)
        return panel

    def update_preview(self):
        content = self.editor.toPlainText()
        html = markdown.markdown(content, extensions=['extra', 'codehilite'])
        
        # 增强的LaTeX支持
        mathjax_config = """
        <script>
        MathJax = {
          tex: {
            inlineMath: [['$', '$'], ['\\(', '\\)']],
            displayMath: [['$$', '$$'], ['\\[', '\\]']],
            processEscapes: true,
            packages: {'[+]': ['amsmath']}
          },
          options: {
            ignoreHtmlClass: 'tex2jax_ignore',
            processHtmlClass: 'tex2jax_process'
          },
          loader: {load: ['[tex]/amsmath']},
          startup: {
            ready: () => {
              MathJax.startup.defaultReady();
              MathJax.startup.promise.then(() => {
                console.log('MathJax initial typesetting complete');
              });
            }
          }
        };
        </script>
        <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
        """
        
        self.preview.setHtml(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.5.0/styles/default.min.css">
                <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.5.0/highlight.min.js"></script>
                <style>
                    body {{ 
                        padding: 20px; 
                        font-family: Segoe UI; 
                        line-height: 1.6;
                        max-width: 800px;
                        margin: 0 auto;
                    }}
                    pre {{
                        background: #f8f9fa;
                        padding: 15px;
                        border-radius: 8px;
                        overflow-x: auto;
                    }}
                    .mathjax-block {{ 
                        padding: 10px;
                        margin: 20px 0;
                        background: #f3f4f6;
                        border-radius: 4px;
                    }}
                    code {{ font-family: 'Fira Code', monospace; }}
                </style>
                {mathjax_config}
            </head>
            <body>
                {html}
                <script>
                    document.addEventListener('DOMContentLoaded', (event) => {{
                        hljs.highlightAll();
                        // 自动重新渲染数学公式
                        if(typeof MathJax !== 'undefined') {{
                            MathJax.typesetPromise();
                        }}
                    }});
                </script>
            </body>
            </html>
        """)

    # 其余方法保持与之前相同（show_tree_context_menu、save_data、load_data等）
    # ...
    # （此处应包含之前版本的其他方法，保持原有功能不变）
    def show_tree_context_menu(self, pos):
        item = self.folder_tree.itemAt(pos)
        menu = QMenu()
        
        if item and item.parent():  # 笔记项
            edit_action = QAction("重命名", self)
            edit_action.triggered.connect(lambda: self.rename_note(item))
            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self.delete_note(item))
            menu.addActions([edit_action, delete_action])
        elif item:  # 文件夹项
            rename_action = QAction("重命名文件夹", self)
            rename_action.triggered.connect(lambda: self.rename_folder(item))
            menu.addAction(rename_action)
        else:  # 空白处
            new_folder_action = QAction("新建文件夹", self)
            new_folder_action.triggered.connect(self.create_folder)
            menu.addAction(new_folder_action)
            
        menu.exec_(self.folder_tree.viewport().mapToGlobal(pos))

    def show_tag_context_menu(self, pos):
        item = self.tag_list.itemAt(pos)
        menu = QMenu()
        if item and item.text() != "无标签":
            delete_action = QAction("删除标签", self)
            delete_action.triggered.connect(lambda: self.delete_tag(item))
            menu.addAction(delete_action)
        menu.exec_(self.tag_list.viewport().mapToGlobal(pos))

    def create_folder(self):
        folder_name, ok = QInputDialog.getText(self, "新建文件夹", "输入文件夹名称:")
        if ok and folder_name:
            root = self.folder_tree.invisibleRootItem()
            folder_item = QTreeWidgetItem(root, [folder_name])
            folder_item.setFlags(folder_item.flags() | Qt.ItemIsEditable)
            self.save_data()

    def rename_folder(self, item):
        old_name = item.text(0)
        new_name, ok = QInputDialog.getText(self, "重命名文件夹", "新名称:", text=old_name)
        if ok and new_name:
            item.setText(0, new_name)
            for note in self.notes:
                if note.get("path") == old_name:
                    note["path"] = new_name
            self.save_data()

    def rename_note(self, item):
        old_title = item.text(0)
        new_title, ok = QInputDialog.getText(self, "重命名笔记", "新标题:", text=old_title)
        if ok and new_title:
            note_id = item.data(0, Qt.UserRole)
            note = next((n for n in self.notes if n["id"] == note_id), None)
            if note:
                # 重命名对应的txt文件
                old_file = os.path.join(NOTES_DIR, f"{note['id']}.txt")
                new_file = os.path.join(NOTES_DIR, f"{note['id']}_{new_title}.txt")
                if os.path.exists(old_file):
                    os.rename(old_file, new_file)
                
                note["title"] = new_title
                item.setText(0, new_title)
                self.save_data()

    def delete_note(self, item):
        note_id = item.data(0, Qt.UserRole)
        confirm = QMessageBox.question(
            self, "删除确认", 
            "确定删除该笔记？此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            # 删除笔记文件
            note_file = os.path.join(NOTES_DIR, f"{note_id}.txt")
            if os.path.exists(note_file):
                os.remove(note_file)
                
            self.notes = [n for n in self.notes if n["id"] != note_id]
            self.update_views()
            self.save_data()

    def delete_tag(self, item):
        tag = item.text()
        if tag == "无标签":
            return
            
        # 从所有笔记中移除该标签
        for note in self.notes:
            if tag in note.get("tags", []):
                note["tags"].remove(tag)
        # 从标签列表移除
        self.tags.remove(tag)
        self.update_views()
        self.save_data()

    def load_data(self):
        try:
            with open(NOTES_FILE, "r") as f:
                data = json.load(f)
                self.notes = data.get("notes", [])
                # 合并标签并去重
                all_tags = {tag for note in self.notes for tag in note.get("tags", [])}
                self.tags = ["无标签"] + list(all_tags)
                
                # 加载时保留展开状态
                self.update_views(keep_expanded=True)
                
                # 加载txt文件内容
                for note in self.notes:
                    file_path = os.path.join(NOTES_DIR, f"{note['id']}.txt")
                    if os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            note["content"] = f.read()
        except FileNotFoundError:
            pass

    def save_data(self):
        # 保存到JSON
        data = {
            "notes": [{
                "id": n["id"],
                "title": n["title"],
                "tags": n.get("tags", []),
                "path": n.get("path", ""),
                "created": n.get("created", ""),
                "modified": datetime.now().isoformat()
            } for n in self.notes]
        }
        with open(NOTES_FILE, "w") as f:
            json.dump(data, f, indent=2)
            
        # 单独保存内容到txt
        for note in self.notes:
            file_path = os.path.join(NOTES_DIR, f"{note['id']}.txt")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(note.get("content", ""))

        self.content_updated.emit({"type": "notes", "data": data})

    def update_views(self, keep_expanded=False):
        # 记录当前展开状态
        if keep_expanded:
            self.expanded_items = {
                self.folder_tree.indexOfTopLevelItem(item) 
                for item in self.get_all_items(self.folder_tree) 
                if item.isExpanded()
            }
        
        # 更新树形结构
        self.folder_tree.clear()
        root = QTreeWidgetItem(self.folder_tree, ["所有笔记"])
        folders = {note.get("path", "") for note in self.notes}
        
        # 创建文件夹结构
        folder_map = {"": root}
        for folder in folders:
            if folder:
                parts = folder.split("/")
                current_path = ""
                for part in parts:
                    current_path = f"{current_path}/{part}" if current_path else part
                    if current_path not in folder_map:
                        parent = folder_map[current_path.rsplit("/", 1)[0]] if "/" in current_path else root
                        new_folder = QTreeWidgetItem(parent, [part])
                        folder_map[current_path] = new_folder
        
        # 添加笔记到对应文件夹
        for note in self.notes:
            folder_path = note.get("path", "")
            parent = folder_map.get(folder_path, root)
            item = QTreeWidgetItem(parent, [note["title"]])
            item.setData(0, Qt.UserRole, note["id"])
            item.setFlags(item.flags() | Qt.ItemIsEditable)
        
        # 恢复展开状态
        if keep_expanded:
            self.restore_expanded_state()
        
        # 更新标签列表（新增"所有标签"处理）
        self.tag_list.clear()
        all_tags = set()
        for note in self.notes:
            all_tags.update(note.get("tags", []))
        
        # 保持固定顺序：所有标签、无标签 + 其他标签
        self.tags = ["所有标签", "无标签"] + sorted(all_tags - {"所有标签", "无标签"})
        self.tag_list.addItems(self.tags)
        self.tag_list.item(0).setSelected(True)

    def get_all_items(self, tree):
        items = []
        iterator = QTreeWidgetItemIterator(tree)
        while iterator.value():
            items.append(iterator.value())
            iterator += 1
        return items

    def restore_expanded_state(self):
        for index in self.expanded_items:
            item = self.folder_tree.topLevelItem(index)
            if item:
                item.setExpanded(True)

    def create_note(self):
        note_id = datetime.now().timestamp()
        self.current_note = {
            "id": note_id,
            "title": "新笔记",
            "content": "",
            "tags": [],
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat()
        }
        self.notes.append(self.current_note)
        self.update_views()
        self.load_note_data()
        self.save_data()

    def load_note(self, item):
        note_id = item.data(0, Qt.UserRole)
        if note_id:
            self.current_note = next((n for n in self.notes if n["id"] == note_id), None)
            self.load_note_data()

    def load_note_data(self):
        if self.current_note:
            self.title_input.setText(self.current_note.get("title", ""))
            self.tag_input.setText(", ".join(self.current_note.get("tags", [])))
            self.editor.setPlainText(self.current_note.get("content", ""))
            self.update_preview()

    def update_preview(self):
        content = self.editor.toPlainText()
        html = markdown.markdown(content, extensions=['extra', 'codehilite'])
        self.preview.setHtml(f"""
            <html>
            <head>
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.5.0/styles/default.min.css">
                <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.5.0/highlight.min.js"></script>
                <style>
                    body {{ padding: 20px; font-family: Segoe UI; }}
                    pre {{ background: #f5f5f5; padding: 15px; border-radius: 8px; }}
                </style>
                <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
                <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
            </head>
            <body>
                {html}
                <script>hljs.highlightAll();</script>
            </body>
            </html>
        """)

    def add_note(self, note_data):
        if not isinstance(note_data, dict):
            raise ValueError("笔记数据必须是字典类型")  
        required_fields = ["title", "content"]
        if not all(field in note_data for field in required_fields):
            raise KeyError(f"缺少必要字段: {required_fields}")
        """新增笔记的核心方法"""
        try:
            new_note = {
                "id": datetime.now().timestamp(),
                "title": note_data["title"],
                "content": note_data["content"],
                "tags": note_data.get("tags", []),
                "created": datetime.now().isoformat(),
                "modified": datetime.now().isoformat()
            }
            self.notes.append(new_note)
            self.save_data()
            self.update_views()

            # 自动选中新建的笔记（修复部分）
            root = self.folder_tree.invisibleRootItem()
            iterator = QTreeWidgetItemIterator(self.folder_tree)
            while iterator.value():
                item = iterator.value()
                if item.data(0, Qt.UserRole) == new_note["id"]:
                    self.folder_tree.setCurrentItem(item)
                    self.folder_tree.scrollToItem(item)
                    break
                iterator += 1
        except KeyError as e:
            QMessageBox.critical(self, "错误", f"缺少必要字段: {str(e)}")

    def filter_by_tag(self, item):
        selected_tag = item.text()
        self.folder_tree.clear()
        root = QTreeWidgetItem(self.folder_tree, [f"标签: {selected_tag}"])
        
        if selected_tag == "所有标签":
            filtered = [n for n in self.notes if n.get("tags")]
        elif selected_tag == "无标签":
            filtered = [n for n in self.notes if not n.get("tags")]
        else:
            filtered = [n for n in self.notes if selected_tag in n.get("tags", [])]
            
        for note in filtered:
            QTreeWidgetItem(root, [note["title"]])
            
        root.setExpanded(True)

    def save_current(self):
        if self.current_note:
            # 处理LaTeX特殊字符转义
            content = self.editor.toPlainText()
            content = content.replace('\\', '\\\\')  # 转义反斜杠
            
            self.current_note.update({
                "title": self.title_input.text(),
                "tags": [t.strip() for t in self.tag_input.text().split(",") if t.strip()],
                "content": content,
                "modified": datetime.now().isoformat()
            })
            
            # 更新标签列表
            for tag in self.current_note["tags"]:
                if tag not in self.tags and tag != "无标签":
                    self.tags.append(tag)
            
            self.save_data()
            self.update_views(keep_expanded=True)
            
            # 定位当前笔记
            root = self.folder_tree.invisibleRootItem()
            iterator = QTreeWidgetItemIterator(self.folder_tree)
            while iterator.value():
                item = iterator.value()
                if item.data(0, Qt.UserRole) == self.current_note["id"]:
                    self.folder_tree.setCurrentItem(item)
                    break
                iterator += 1