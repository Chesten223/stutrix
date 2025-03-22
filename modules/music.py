# music.py
import os,json
import mutagen
from datetime import datetime
from PyQt5.QtCore import QUrl, Qt, QDir, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QKeySequence,QDesktopServices
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist

class MusicModule(QWidget):
    play_state_changed = pyqtSignal(bool)
    meta_updated = pyqtSignal(dict)  # 新增元数据信号
    
    def __init__(self):
        super().__init__()
        # 初始化播放器
        self.player = QMediaPlayer()
        self.playlist = QMediaPlaylist()
        self.player.setPlaylist(self.playlist)
        self.player.error.connect(self.handle_media_error)  # 新增错误信号连接
        # 初始化属性
        self.play_modes = ["列表循环", "单曲循环", "随机播放"]
        self.current_mode = 0
        self.original_play_order = []
        self.liked_songs = []  # 修复收藏功能
        self.default_music_folder = os.path.join(QDir.homePath(), "Music")  # 默认音乐文件夹
        self.check_codec_support()
        # 创建默认目录（如果不存在）
        os.makedirs(self.default_music_folder, exist_ok=True)
        
        # 初始化界面
        self.init_ui()
        self.connect_signals()
        
        # 加载默认音乐
        self.load_default_music()

        # 添加快捷键
        self.play_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.play_shortcut.activated.connect(self.toggle_play)


    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 顶部控制栏
        control_bar = QHBoxLayout()
        
        self.play_btn = QPushButton()
        self.play_btn.setIcon(QIcon("icons/play.png"))
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.clicked.connect(self.toggle_play)
        
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(QIcon("icons/prev.png"))
        self.prev_btn.clicked.connect(self.prev_track)
        
        self.next_btn = QPushButton()
        self.next_btn.setIcon(QIcon("icons/next.png"))
        self.next_btn.clicked.connect(self.next_track)

        # 播放模式按钮
        self.mode_btn = QPushButton(self.play_modes[self.current_mode])
        self.mode_btn.clicked.connect(self.toggle_play_mode)
        self.mode_btn.setFixedSize(90, 30)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)
        
        control_bar.addWidget(self.prev_btn)
        control_bar.addWidget(self.play_btn)
        control_bar.addWidget(self.next_btn)
        control_bar.addWidget(self.mode_btn)
        control_bar.addStretch()
        control_bar.addWidget(QLabel("音量:"))
        control_bar.addWidget(self.volume_slider, 1)

        

        # 播放信息
        self.meta_label = QLabel("艺术家 - 标题")
        self.meta_label.setFont(QFont("Segoe UI", 10))
        self.meta_label.setAlignment(Qt.AlignCenter)
        
        self.song_label = QLabel("未选择音乐")
        self.song_label.setFont(QFont("Segoe UI", 8))
        self.song_label.setAlignment(Qt.AlignCenter)

        self.progress = QSlider(Qt.Horizontal)
        self.progress.sliderMoved.connect(self.seek_position)

        # 时间显示
        self.time_layout = QHBoxLayout()
        self.current_time = QLabel("00:00")
        self.total_time = QLabel("00:00")
        self.time_layout.addWidget(self.current_time)
        self.time_layout.addStretch()
        self.time_layout.addWidget(self.total_time)

        # 播放列表
        self.playlist_widget = QListWidget()
        self.playlist_widget.setAlternatingRowColors(True)
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected)
        
        # 底部工具栏
        toolbar = QHBoxLayout()
        open_btn = QPushButton("打开文件夹")
        open_btn.clicked.connect(self.open_folder)
        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self.clear_playlist)
        
        toolbar.addWidget(open_btn)
        toolbar.addStretch()
        toolbar.addWidget(clear_btn)

        main_layout.addLayout(control_bar)
        main_layout.addWidget(self.meta_label)
        main_layout.addWidget(self.song_label)
        main_layout.addLayout(self.time_layout)
        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.playlist_widget, 1)
        main_layout.addLayout(toolbar)

        self.set_style()

    def load_default_music(self):
        """自动加载默认音乐文件夹"""
        if os.path.exists(self.default_music_folder):
            success = self.load_music_files(self.default_music_folder)
            if not success:
                QMessageBox.information(
                    self, 
                    "提示", 
                    f"默认音乐文件夹为空:\n{self.default_music_folder}\n请通过[打开文件夹]添加音乐"
                )


    def set_style(self):
        self.setStyleSheet("""
            QWidget {
                background: white;
            }
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 5px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #e0e0e0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -6px 0;
                background: #2196F3;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #2196F3;
                border-radius: 3px;
            }
            QPushButton {
                border: none;
                background: transparent;
                padding: 5px;
                min-width: 60px;
            }
            QPushButton:hover {
                background: #f5f5f5;
                border-radius: 4px;
            }
            #mode_btn {
                background: #e3f2fd;
                border-radius: 15px;
            }
        """)
        self.meta_label.setStyleSheet("color: #2196F3;")
        self.song_label.setStyleSheet("color: #757575;")

    def connect_signals(self):
        self.player.positionChanged.connect(self.update_progress)
        self.player.durationChanged.connect(self.update_duration)
        self.player.stateChanged.connect(self.update_play_state)
        self.player.metaDataChanged.connect(self.update_metadata)
        self.playlist.currentIndexChanged.connect(self.update_current_song)
        self.playlist.currentIndexChanged.connect(self.save_play_order)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择音乐文件夹")
        if folder:
            self.current_folder = folder
            success = self.load_music_files(folder)
            if not success:
                QMessageBox.warning(self, "提示", "该文件夹没有支持的音频文件")

    def load_music_files(self, folder):
        self.playlist.clear()
        self.playlist_widget.clear()

        audio_exts = [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"]
        found_files = False

        try:
            for root, _, files in os.walk(folder):
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in audio_exts:
                        path = os.path.join(root, file)
                        # 验证文件可读性
                        if not self.validate_media_file(path):
                            print(f"跳过无效文件: {path}")
                            continue
                        self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(path)))
                        self.playlist_widget.addItem(file)
                        found_files = True
                        
            if self.playlist.mediaCount() > 0:
                self.playlist.setCurrentIndex(0)
                self.original_play_order = list(range(self.playlist.mediaCount()))
                
            return found_files
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"无法读取文件夹内容:\n{str(e)}")
            return False

    def toggle_play_mode(self):
        self.current_mode = (self.current_mode + 1) % len(self.play_modes)
        self.mode_btn.setText(self.play_modes[self.current_mode])
        
        if self.current_mode == 2:  # 随机播放
            import random
            random.shuffle(self.original_play_order)
            self.playlist.shuffle()
        else:
            self.playlist.setPlaybackMode(
                QMediaPlaylist.Loop if self.current_mode == 0 
                else QMediaPlaylist.CurrentItemInLoop
            )
    def toggle_like_status(self):
        """改进的收藏功能"""
        if not hasattr(self, 'liked_songs'):
            self.liked_songs = []
            
        current_song = self.get_current_song()
        if current_song == "未选择音乐":
            QMessageBox.warning(self, "操作失败", "请先选择要收藏的歌曲")
            return
            
        if current_song not in self.liked_songs:
            self.liked_songs.append(current_song)
            self.like_btn.setStyleSheet("color: #ff4444;")
            self.save_liked_songs()  # 持久化存储
            QMessageBox.information(self, "收藏成功", f"已收藏歌曲: {current_song}")
        else:
            self.liked_songs.remove(current_song)
            self.like_btn.setStyleSheet("")
            self.save_liked_songs()
            QMessageBox.information(self, "取消收藏", f"已移除歌曲: {current_song}")

    def save_liked_songs(self):
        """保存收藏列表到文件"""
        try:
            with open("data/liked_songs.json", "w", encoding='utf-8') as f:
                json.dump(self.liked_songs, f, ensure_ascii=False)
        except Exception as e:
            print(f"保存收藏列表失败: {str(e)}")

    def load_liked_songs(self):
        """从文件加载收藏列表"""
        try:
            with open("data/liked_songs.json", "r", encoding='utf-8') as f:
                self.liked_songs = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.liked_songs = []

    def update_metadata(self):
        meta = {
            "title": self.player.metaData("Title"),
            "artist": self.player.metaData("Artist"),
            "album": self.player.metaData("AlbumTitle"),
            "genre": self.player.metaData("Genre")
        }
        
        # 从文件读取元数据作为备用
        if not meta["title"]:
            try:
                audio = mutagen.File(self.player.currentMedia().canonicalUrl().toLocalFile())
                meta["title"] = audio.get("title", [""])[0]
                meta["artist"] = audio.get("artist", [""])[0]
            except:
                pass
        
        display_artist = meta["artist"] or "未知艺术家"
        display_title = meta["title"] or os.path.splitext(self.get_current_song())[0]
        
        self.meta_label.setText(f"{display_artist} - {display_title}")
        self.song_label.setText(f"专辑: {meta['album']} | 流派: {meta['genre']}")
        self.meta_updated.emit(meta)

    def save_play_order(self, index):
        if self.current_mode == 2 and index != -1:
            next_index = self.original_play_order.index(index)
            self.playlist.setCurrentIndex(next_index)

    def update_progress(self, position):
        self.progress.setValue(position)
        self.current_time.setText(self.format_time(position))

    def update_duration(self, duration):
        self.progress.setRange(0, duration)
        self.total_time.setText(self.format_time(duration))

    def format_time(self, ms):
        seconds = ms // 1000
        return f"{seconds // 60:02}:{seconds % 60:02}"

    def update_play_state(self, state):
        is_playing = state == QMediaPlayer.PlayingState
        self.play_btn.setIcon(QIcon("icons/pause.png" if is_playing else "icons/play.png"))
        self.play_state_changed.emit(is_playing)

    def update_current_song(self, index):
        if index >= 0:
            self.playlist_widget.setCurrentRow(index)
            self.update_metadata()

    def get_current_song(self):
        if self.playlist.currentMedia().isNull():
            return "未选择音乐"
        return os.path.basename(self.playlist.currentMedia().canonicalUrl().toLocalFile())

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def prev_track(self):
        if self.playlist.currentIndex() > 0:
            self.playlist.previous()

    def next_track(self):
        if self.playlist.currentIndex() < self.playlist.mediaCount()-1:
            self.playlist.next()

    def play_selected(self, item):
        index = self.playlist_widget.row(item)
        self.playlist.setCurrentIndex(index)
        self.player.play()

    def set_volume(self, value):
        self.player.setVolume(value)

    def seek_position(self, position):
        self.player.setPosition(position)

    def validate_media_file(self, path):
        """验证文件是否可播放"""
        try:
            # 快速验证文件头
            with open(path, 'rb') as f:
                header = f.read(16)
                if len(header) < 16:
                    return False
            return True
        except Exception as e:
            print(f"文件验证失败: {path} - {str(e)}")
            return False

    def check_codec_support(self):
        """检测解码器支持"""
        if not self.test_playback():
            reply = QMessageBox.question(
                self,
                "解码器缺失",
                "检测到系统可能缺少音频解码器，是否访问官方网站下载解码器包？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                QDesktopServices.openUrl(QUrl("https://codecguide.com/download_k-lite_codec_pack_basic.htm"))

    def test_playback(self):
        """测试播放系统默认提示音"""
        test_file = QUrl.fromLocalFile("C:/Windows/Media/notify.wav")  # 使用系统自带WAV文件
        temp_player = QMediaPlayer()
        temp_player.setMedia(QMediaContent(test_file))
        temp_player.play()
        return temp_player.state() == QMediaPlayer.PlayingState

    def update_play_state(self, state):
        is_playing = state == QMediaPlayer.PlayingState
        self.play_btn.setIcon(QIcon("icons/pause.png" if is_playing else "icons/play.png"))
        self.play_state_changed.emit(is_playing)

    def update_current_song(self, index):
        if index >= 0:
            self.playlist_widget.setCurrentRow(index)
            self.song_label.setText(self.get_current_song())

    def get_current_song(self):
        if self.playlist.currentMedia().isNull():
            return "未选择音乐"
        return os.path.basename(self.playlist.currentMedia().canonicalUrl().toLocalFile())

    def clear_playlist(self):
        self.playlist.clear()
        self.playlist_widget.clear()
        self.player.stop()

    def handle_media_error(self, error):
        """处理媒体播放错误"""
        error_msg = {
            QMediaPlayer.NoError: "无错误",
            QMediaPlayer.ResourceError: "资源错误（文件损坏或格式不支持）",
            QMediaPlayer.FormatError: "格式错误（解码器缺失）",
            QMediaPlayer.NetworkError: "网络错误",
            QMediaPlayer.AccessDeniedError: "访问被拒绝"
        }.get(error, "未知错误")
        
        current_file = self.get_current_song()
        QMessageBox.critical(
            self, 
            "播放错误", 
            f"无法播放文件: {current_file}\n错误类型: {error_msg}\n建议检查文件完整性或安装解码器"
        )
        self.playlist.removeMedia(self.playlist.currentIndex())  # 自动移除问题文件