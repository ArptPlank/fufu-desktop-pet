import sys
import os
import time
import subprocess
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QLineEdit, QPushButton, QTextEdit, QHBoxLayout, QCheckBox
from PyQt6.QtGui import QPixmap, QMouseEvent
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QThread
import threading
from get_response import Chat
from PIL import Image, ImageTk
import tkinter as tk
import warnings
from threading import Thread

from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

import pyaudio
import wave

class AnimationPlayer:
    def __init__(self, label, folder_paths, target_width, target_height):
        self.label = label
        self.folder_paths = folder_paths
        self.target_size = (target_width, target_height)
        self.animations = [
            [QPixmap(os.path.join(folder, img)).scaled(target_width, target_height,
                                                       Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                       Qt.TransformationMode.SmoothTransformation)
             for img in sorted(os.listdir(folder))]
            for folder in folder_paths
        ]
        self.current_animation = 0
        self.current_frame = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def start(self, animation_index=0, interval=100):
        self.current_animation = animation_index
        self.current_frame = 0
        self.timer.start(interval)

    def update_frame(self):
        frames = self.animations[self.current_animation]
        self.label.setPixmap(frames[self.current_frame])
        self.current_frame = (self.current_frame + 1) % len(frames)

    def switch_animation(self, index):
        """Switch to a different animation set."""
        if index != self.current_animation:
            self.current_animation = index
            self.current_frame = 0  # Reset frame index to start from the first frame of the new animation
            self.update_frame()  # Update immediately to display the first frame of the new animation


def show_image_with_pillow(image_path):
    # 创建一个Tkinter窗口
    root = tk.Tk()
    # 打开图像文件
    img = Image.open(image_path)
    # 使用Pillow的PhotoImage展示图像
    tkimage = ImageTk.PhotoImage(img)
    tk.Label(root, image=tkimage).pack()
    # 进入Tkinter事件循环
    root.mainloop()

class TransparentPNGWidget(QWidget):
    def __init__(self, folder_path_1,folder_path_2,chat):
        super().__init__()
        # 忽略警告
        warnings.filterwarnings("ignore")
        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 300, 350)
        self.chat = chat
        self.complete = True
        self.internet_search_enabled = False  # 初始不启用网络搜索

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True,
                                      frames_per_buffer=1024)
        self.is_saving = False
        self.record_frames = []
        self.start_continuous_recording()
        self.is_recording = False

        # 设置接受键盘焦点
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

        # 设置主布局
        main_layout = QVBoxLayout()
        # 添加一个水平布局，用于放置关闭按钮
        top_layout = QHBoxLayout()
        self.reset_button = QPushButton("清除记忆", self)
        self.reset_button.clicked.connect(self.reset_memory)
        self.reset_button.setStyleSheet("""
                    QPushButton {
                        background-color: #FF6347;
                        color: white;
                        border-radius: 10px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #FF4500;
                    }
        """)

        self.close_button = QPushButton("X", self)
        self.close_button.setFixedSize(30, 30)
        self.close_button.clicked.connect(QApplication.instance().quit)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: red; 
                color: white; 
                border: none; 
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: darkred;
            }
        """)
        self.internet_search_checkbox = QCheckBox("启用网络搜索", self)
        self.internet_search_checkbox.setStyleSheet("""
            QCheckBox {
                color: #1565C0; /* deep blue color for the text */
                font-weight: bold; /* make the text bold */
                spacing: 5px; /* space between checkbox and label text */
            }
            QCheckBox::indicator {
                width: 18px; /* width of the checkbox */
                height: 18px; /* height of the checkbox */
                border-radius: 9px; /* fully rounded corners */
                background-color: #BBDEFB; /* light blue background for the checkbox */
                border: 1px solid #42A5F5; /* blue border color */
            }
            QCheckBox::indicator:checked {
                background-color: #42A5F5; /* darker blue background when checked */
                image: url(:/icons/checked.svg); /* custom check mark */
            }
            QCheckBox::indicator:unchecked {
                background-color: #E3F2FD; /* lighter blue when unchecked */
            }
        """)
        self.internet_search_checkbox.stateChanged.connect(self.toggle_internet_search)
        top_layout.addWidget(self.internet_search_checkbox)
        top_layout.addWidget(self.reset_button)
        #推向右边
        top_layout.addStretch(1)
        top_layout.addWidget(self.close_button)
        top_layout.addStretch()

        main_layout.addLayout(top_layout)
        self.label = QLabel(self)
        main_layout.addWidget(self.label)
        self.animation_player = AnimationPlayer(self.label, [folder_path_1, folder_path_2],400,400)
        self.animation_player.start(0, 100)  # Start with the first animation

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #e0f7fa;
                color: #00796b;
                border: 1px solid #00796b;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        main_layout.addWidget(self.text_edit)

        input_layout = QHBoxLayout()
        self.input_field = QLineEdit(self)
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: #b2ebf2;
                color: #00796b;
                border: 1px solid #00796b;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        self.send_button = QPushButton("发送", self)
        self.send_button.clicked.connect(self.send_message)
        # 将输入框的returnPressed信号也连接到send_message方法
        self.input_field.returnPressed.connect(self.send_message)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #4dd0e1;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #0097a7;
            }
        """)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)

        main_layout.addLayout(input_layout)

        self.setLayout(main_layout)

        self.resize(300, 400)
        self.show()

        #self.timer = QTimer(self)
        #elf.timer.timeout.connect(self.update_image)
        self.playback_speed = 23  # 播放速度，单位为毫秒
        #self.timer.start(self.playback_speed)
        #初始化结束后自动发一段话
        self.send_message_headless(message="你好啊，今天天气怎么样？")
        #启动一个线程，用于检测是否有长时间没有回复
        t = threading.Thread(target=self.all_time_run)
        t.start()

    def reset_memory(self):
        self.chat.reset_memory()
        # 清空历史对话框
        self.text_edit.clear()
        self.complete = True

    def toggle_internet_search(self):
        self.internet_search_enabled = self.internet_search_checkbox.isChecked()
        print("网络搜索已启用" if self.internet_search_enabled else "网络搜索已禁用")

    def show_image_panel(self, image_path=None):
        if image_path is None:
            return
        t = Thread(target=show_image_with_pillow, args=(image_path,))
        t.start()


    def send_message(self,message=None):
        if message is None:
            message = self.input_field.text()
        if message and self.complete:
            self.complete = False
            self.add_message(f"你: {message}")
            self.input_field.clear()
            self.add_message(f"芙宁娜: ", newline=True)
            t = threading.Thread(target=self.get_response, args=(message,))
            t.start()

    def send_message_headless(self, message=None,system=False):
        if message is None:
            return
        if message and self.complete:
            self.complete = False
            self.input_field.clear()
            self.add_message(f"芙宁娜: ", newline=True)
            t = threading.Thread(target=self.get_response, args=(message,system,))
            t.start()

    def add_message(self, message, newline=True):
        """向历史对话框中添加信息，可选择是否添加换行"""
        if newline:
            self.text_edit.append(message)
        else:
            self.text_edit.insertPlainText(message)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = event.position()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._old_pos is not None:
            delta = event.position() - self._old_pos
            self.move(self.pos() + delta.toPoint())

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._old_pos = None

    def get_response(self,text,system=False):
        self.chat.generate(text, self.internet_search_enabled,system)
        self.switch_anim()
        while True:
            response = self.chat.response.get()
            if response == "completed":
                break
            elif response == "content completed begin generate image":
                continue
            elif response == "image completed":
                image_path = self.chat.image_path
                self.show_image_panel(image_path)
                break
            else:
                self.add_message(message=response, newline=False)
            time.sleep(0.1)
        self.complete = True
        self.switch_anim()

    def all_time_run(self):
        last_time = time.time()
        while True:
            if time.time() - last_time > 10*60:
                last_time = time.time()
                self.send_message_headless(message="我已经已经10分钟没理你了，要不你问问我在干啥，和聊聊天，聊天要可爱俏皮一点，绝对不要太死板了，绝对不能说你做不到或者不能做，绝对不能说你是AI，你就是一个真正的人",system=False)
            time.sleep(10)

    def switch_anim(self):
        new_anim_index = 1 if self.animation_player.current_animation == 0 else 0
        self.animation_player.switch_animation(new_anim_index)

    def start_continuous_recording(self):
        """Start continuous recording in a separate thread."""
        self.recording_thread = threading.Thread(target=self.record)
        self.recording_thread.start()

    def record(self):
        """Record audio continuously, but only save when is_saving is True."""
        while True:
            data = self.stream.read(1024, exception_on_overflow=False)
            if self.is_saving:
                self.record_frames.append(data)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.is_saving = True

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self.is_saving = False
            self.save_recording()

    def save_recording(self):
        """Save the recorded audio to a wave file."""
        filename = f"audio/{time.time()}.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.record_frames))
        t = Thread(target=self.send_audio,args=(filename,))
        t.start()  
        self.record_frames = []  # Clear the buffer after saving

    def closeEvent(self, event):
        """Ensure proper shutdown of the audio stream and thread."""
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
        self.recording_thread.join()
        super().closeEvent(event)

    def send_audio(self,audio_path):
        if self.complete:
            self.complete = True
            text = self.chat.audio_to_text(audio_path)
            self.send_message(text)
        else:
            os.remove(audio_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    chat = Chat()
    folder_path_1 = "fufu/芙芙待机动画"
    folder_path_2 = "fufu/芙芙说话动画"
    widget = TransparentPNGWidget(folder_path_1,folder_path_2,chat)
    sys.exit(app.exec())
