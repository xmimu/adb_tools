import sys
from pathlib import Path
from typing import Optional
import scrcpy
from adbutils import adb, AdbDevice
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *


class PrintScreenWindow(QWidget):
    count = 0

    def __init__(self, device: AdbDevice):
        super().__init__()
        PrintScreenWindow.count += 1
        self.title_str = f'Print Screen {PrintScreenWindow.count}'
        self.setWindowTitle(self.title_str)
        # self.resize(600, 600)

        self.device = device
        self.img = self.device.screenshot()
        self.pix: QPixmap = self.img.toqpixmap()
        self.device_size = self.pix.size().toTuple()
        self.device_pos = (0, 0)
        self.start_pos = (0, 0)
        self.end_pos = (0, 0)
        self.box = (0, 0, 0, 0)
        self.is_choosing = False

        save_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        self.btn_save_box_local = QPushButton('local')
        self.btn_save_box_local.setIcon(save_icon)
        self.btn_save_box_device = QPushButton('device')
        self.btn_save_box_device.setIcon(save_icon)

        self.btn_save_screen_local = QPushButton('local')
        self.btn_save_screen_local.setIcon(save_icon)
        self.btn_save_screen_device = QPushButton('device')
        self.btn_save_screen_device.setIcon(save_icon)

        self.edit_box_local = QLineEdit('box.png')
        self.edit_box_device = QLineEdit('/sdcard/box.png')
        self.edit_screen_local = QLineEdit('screen.png')
        self.edit_screen_device = QLineEdit('/sdcard/screen.png')

        self.canvas = QLabel()
        self.canvas.resize(self.pix.size())
        self.area = QScrollArea()
        self.area.setStyleSheet('background:skyBlue')
        self.area.setWidget(self.canvas)

        head = QGridLayout()
        head.addWidget(self.edit_screen_local, 0, 0)
        head.addWidget(self.btn_save_screen_local, 0, 1)
        # head.addSpacing(50)
        head.addWidget(self.edit_screen_device, 0, 2)
        head.addWidget(self.btn_save_screen_device, 0, 3)
        # head.addSpacing(50)
        head.addWidget(self.edit_box_local, 1, 0)
        head.addWidget(self.btn_save_box_local, 1, 1)
        # head.addSpacing(50)
        head.addWidget(self.edit_box_device, 1, 2)
        head.addWidget(self.btn_save_box_device, 1, 3)

        layout = QVBoxLayout()
        layout.addLayout(head)
        layout.addWidget(self.area)
        self.setLayout(layout)

        self.canvas.paintEvent = self.canvasPaintEvent
        self.canvas.mousePressEvent = self.canvasMousePressEvent
        self.canvas.mouseMoveEvent = self.canvasMouseMoveEvent
        self.canvas.mouseReleaseEvent = self.canvasMouseReleaseEvent

        self.btn_save_box_local.clicked.connect(self.btn_save_box_local_clicked)
        self.btn_save_box_device.clicked.connect(self.btn_save_box_device_clicked)
        self.btn_save_screen_local.clicked.connect(self.btn_save_screen_local_clicked)
        self.btn_save_screen_device.clicked.connect(self.btn_save_screen_device_clicked)

    def btn_save_box_local_clicked(self):
        filename = self.edit_box_local.text().strip()
        if not filename: return
        if self.box == (0, 0, 0, 0): return
        try:
            self.img.crop(box=self.box).save(filename)
            QMessageBox.information(self, '提示', '文件已保存。')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存失败。\n{e}')

    def btn_save_box_device_clicked(self):
        filename = self.edit_box_device.text().strip()
        if not filename: return
        if self.box == (0, 0, 0, 0): return
        try:
            templ_path = Path('_templ_box.png')
            self.img.crop(box=self.box).save(templ_path)
            self.device.sync.push(templ_path, filename)
            templ_path.unlink()
            QMessageBox.information(self, '提示', '文件已保存。')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存失败。\n{e}')

    def btn_save_screen_local_clicked(self):
        filename = self.edit_screen_local.text().strip()
        if not filename: return
        try:
            self.img.save(filename)
            QMessageBox.information(self, '提示', '文件已保存。')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存失败。\n{e}')

    def btn_save_screen_device_clicked(self):
        filename = self.edit_screen_device.text().strip()
        if not filename: return
        try:
            templ_path = Path('_templ_screen.png')
            self.img.save(templ_path)
            self.device.sync.push(templ_path, filename)
            templ_path.unlink()
            QMessageBox.information(self, '提示', '文件已保存。')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存失败。\n{e}')

    def canvasPaintEvent(self, event: QPaintEvent):
        painter = QPainter(self.canvas)
        painter.drawPixmap(0, 0, self.pix)
        # draw rect
        painter.setPen(Qt.GlobalColor.red)
        rect = QRectF()
        rect.setLeft(self.start_pos[0])
        rect.setTop(self.start_pos[1])
        rect.setRight(self.end_pos[0])
        rect.setBottom(self.end_pos[1])
        painter.drawRect(rect)

        if self.start_pos == self.end_pos:
            self.btn_save_box_local.setEnabled(False)
            self.btn_save_box_device.setEnabled(False)
            self.box = (0, 0, 0, 0)
        else:
            self.btn_save_box_local.setEnabled(True)
            self.btn_save_box_device.setEnabled(True)
            self.box = (self.start_pos[0], self.start_pos[1], self.end_pos[0], self.end_pos[1])

        title = f'{self.title_str} ---- ' \
                f'Size: {self.device_size} ' \
                f'| Pos: {self.device_pos} ' \
                f'| Box: {self.box}'

        self.setWindowTitle(title)

    def canvasMousePressEvent(self, event: QMouseEvent):
        if not self.is_choosing:
            self.start_pos = event.position().toTuple()
            self.end_pos = self.start_pos
            self.is_choosing = True

        self.device_pos = event.position().toTuple()
        self.canvas.update()

    def canvasMouseMoveEvent(self, event: QMouseEvent):
        if self.is_choosing:
            self.end_pos = event.position().toTuple()

        self.device_pos = event.position().toTuple()
        self.canvas.update()

    def canvasMouseReleaseEvent(self, event: QMouseEvent):
        if self.is_choosing:
            self.end_pos = event.position().toTuple()
            self.is_choosing = False

        self.device_pos = event.position().toTuple()
        self.canvas.update()

    def closeEvent(self, event):
        PrintScreenWindow.count -= 1


class Worker(QObject):
    sig_get_frame_pix = Signal(QPixmap)

    def on_frame(self, frame):
        if frame is not None:
            image = QImage(
                frame,
                frame.shape[1],
                frame.shape[0],
                frame.shape[1] * 3,
                QImage.Format.Format_BGR888,
            )
            pix = QPixmap(image)
            self.sig_get_frame_pix.emit(pix)


class Window(QWidget):

    def __init__(self):
        super().__init__()
        self.ratio: float = 1
        self.worker: Worker = Worker(self)
        self.devices: list[str] = []
        self.device: Optional[AdbDevice] = None
        self.client: Optional[scrcpy.Client] = None
        self.print_window: Optional[PrintScreenWindow] = None

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

        self.btn_connect_clicked()
        self.resize(1280, 720)

    def create_widgets(self):
        self.btn_connect = QPushButton('Connect')
        self.btn_print_screen = QPushButton('Print Screen')
        self.devices_comb = QComboBox()
        self.devices_comb.setFixedWidth(150)
        self.btn_home = QPushButton('HOME')
        self.btn_back = QPushButton('BACK')
        self.btn_vol_up = QPushButton('VOL+')
        self.btn_vol_down = QPushButton('VOL-')

        # body
        self.canvas = QLabel()
        # self.canvas.setMouseTracking(True)
        self.area = QScrollArea()
        self.area.setStyleSheet('background:skyBlue')
        self.area.setWidget(self.canvas)

        # bottom
        self.btn_add = QPushButton('+')
        self.btn_add.setMaximumWidth(40)
        self.btn_sub = QPushButton('-')
        self.btn_sub.setMaximumWidth(40)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(20, 200)
        self.slider.setValue(100)
        self.slider.setMaximumWidth(100)
        self.status_label = QLabel('Status')
        self.status_label.setFixedWidth(300)
        self.ratio_label = QLabel('100%')

    def create_layouts(self):
        self.head_layout = QHBoxLayout()
        self.head_layout.setAlignment(Qt.AlignLeft)
        self.head_layout.addWidget(self.btn_connect)
        self.head_layout.addWidget(self.devices_comb)
        self.head_layout.addWidget(self.btn_print_screen)
        self.head_layout.addWidget(self.btn_home)
        self.head_layout.addWidget(self.btn_back)
        self.head_layout.addWidget(self.btn_vol_up)
        self.head_layout.addWidget(self.btn_vol_down)

        self.body_layout = QVBoxLayout()
        self.body_layout.addWidget(self.area)

        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.setAlignment(Qt.AlignLeft)
        self.bottom_layout.addWidget(self.status_label)
        self.bottom_layout.addWidget(self.btn_sub)
        self.bottom_layout.addWidget(self.slider)
        self.bottom_layout.addWidget(self.btn_add)
        self.bottom_layout.addWidget(self.ratio_label)

        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.head_layout)
        self.main_layout.addLayout(self.body_layout)
        self.main_layout.addLayout(self.bottom_layout)
        self.setLayout(self.main_layout)

    def create_connections(self):
        self.worker.sig_get_frame_pix.connect(self.get_frame_pix)
        self.btn_connect.clicked.connect(self.btn_connect_clicked)
        self.devices_comb.currentTextChanged.connect(self.choose_device)
        self.btn_print_screen.clicked.connect(self.btn_print_screen_clicked)
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.btn_add.clicked.connect(lambda: self.slider.setValue(self.slider.value() + 10))
        self.btn_sub.clicked.connect(lambda: self.slider.setValue(self.slider.value() - 10))

        # Bind controllers
        self.btn_home.clicked.connect(self.on_click_home)
        self.btn_back.clicked.connect(self.on_click_back)
        self.btn_vol_up.clicked.connect(self.on_click_vol_up)
        self.btn_vol_down.clicked.connect(self.on_click_vol_down)

        # Bind mouse event
        self.canvas.mousePressEvent = self.on_mouse_event(scrcpy.ACTION_DOWN)
        self.canvas.mouseMoveEvent = self.on_mouse_event(scrcpy.ACTION_MOVE)
        self.canvas.mouseReleaseEvent = self.on_mouse_event(scrcpy.ACTION_UP)

        # Keyboard event
        self.keyPressEvent = self.on_key_event(scrcpy.ACTION_DOWN)
        self.keyReleaseEvent = self.on_key_event(scrcpy.ACTION_UP)

    def list_devices(self):
        items = [i.serial for i in adb.device_list()]
        self.devices_comb.clear()
        self.devices_comb.addItems(items)
        return items

    def choose_device(self, device):
        if not device or not self.devices: return
        if device not in self.devices:
            msgBox = QMessageBox()
            msgBox.setText(f"Device serial [{device}] not found!")
            msgBox.exec()
            return

        # Restart service
        if getattr(self, "client", None):
            self.client.stop()
            self.client.device = adb.device(serial=device)
            self.client.start(threaded=True)
            self.slider.setValue(100)

    def btn_connect_clicked(self):
        self.devices = self.list_devices()
        self.device = adb.device(self.devices[0]) if self.devices else None
        if self.client is not None:
            self.client.stop()
        self.client = scrcpy.Client(device=self.device)
        # self.client.add_listener(scrcpy.EVENT_INIT, self.on_init)
        self.client.add_listener(scrcpy.EVENT_FRAME, self.worker.on_frame)
        self.client.start(threaded=True)

    def btn_print_screen_clicked(self):
        if self.devices is None: return

        self.print_window = PrintScreenWindow(self.device)
        self.print_window.show()

    def get_frame_pix(self, pix: QPixmap):
        w = int(pix.width() * self.ratio)
        h = int(pix.height() * self.ratio)
        pix = pix.scaled(w, h)
        self.canvas.setPixmap(pix)
        self.canvas.resize(pix.size())

    def slider_value_changed(self):
        slider: QSlider = self.sender()
        value = int(slider.value())
        self.ratio = value / 100
        self.ratio_label.setText(f'{value}%')

    def on_click_home(self):
        self.client.control.keycode(scrcpy.KEYCODE_HOME, scrcpy.ACTION_DOWN)
        self.client.control.keycode(scrcpy.KEYCODE_HOME, scrcpy.ACTION_UP)

    def on_click_back(self):
        self.client.control.back_or_turn_screen_on(scrcpy.ACTION_DOWN)
        self.client.control.back_or_turn_screen_on(scrcpy.ACTION_UP)

    def on_click_vol_up(self):
        self.client.control.keycode(scrcpy.KEYCODE_VOLUME_UP, scrcpy.ACTION_DOWN)
        self.client.control.keycode(scrcpy.KEYCODE_VOLUME_UP, scrcpy.ACTION_UP)

    def on_click_vol_down(self):
        self.client.control.keycode(scrcpy.KEYCODE_VOLUME_DOWN, scrcpy.ACTION_DOWN)
        self.client.control.keycode(scrcpy.KEYCODE_VOLUME_DOWN, scrcpy.ACTION_UP)

    def on_mouse_event(self, action=scrcpy.ACTION_DOWN):
        def handler(event: QMouseEvent):
            focused_widget = QApplication.focusWidget()
            if focused_widget is not None:
                focused_widget.clearFocus()

            pos = event.position().toPoint()  # label坐标
            device_x, device_y = event.position().x() / self.ratio, event.position().y() / self.ratio  # 设备实际坐标

            self.client.control.touch(
                event.position().x() / self.ratio, event.position().y() / self.ratio, action
            )
            self.status_label.setText(f'Device Pos: {(int(device_x), int(device_y))}')

        return handler

    def on_key_event(self, action=scrcpy.ACTION_DOWN):
        def handler(event: QKeyEvent):
            code = self.map_code(event.key())
            if code != -1:
                self.client.control.keycode(code, action)

        return handler

    def map_code(self, code):
        """
        Map qt keycode ti android keycode

        Args:
            code: qt keycode
            android keycode, -1 if not founded
        """

        if code == -1:
            return -1
        if 48 <= code <= 57:
            return code - 48 + 7
        if 65 <= code <= 90:
            return code - 65 + 29
        if 97 <= code <= 122:
            return code - 97 + 29

        hard_code = {
            32: scrcpy.KEYCODE_SPACE,
            16777219: scrcpy.KEYCODE_DEL,
            16777248: scrcpy.KEYCODE_SHIFT_LEFT,
            16777220: scrcpy.KEYCODE_ENTER,
            16777217: scrcpy.KEYCODE_TAB,
            16777249: scrcpy.KEYCODE_CTRL_LEFT,
        }
        if code in hard_code:
            return hard_code[code]

        print(f"Unknown keycode: {code}")
        return -1

    def mouseMoveEvent(self, event):
        self.status_label.setText(str(event.position().toPoint()))

    def closeEvent(self, event):
        if self.client is not None:
            self.client.stop()
        if self.print_window is not None:
            self.print_window.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    sys.exit(app.exec())
