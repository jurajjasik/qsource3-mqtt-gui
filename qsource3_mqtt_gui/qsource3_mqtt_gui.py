import json
import logging
import os
import time

from engineering_notation import EngNumber
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLCDNumber,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .qsource3_mqtt_client_logic import QSource3_MQTTClientLogic

COLOR_VALID = "color: black"
COLOR_INVALID = "color: red"

logger = logging.getLogger(__name__)


def set_color(widget, color):
    widget.setStyleSheet(color)


class VLine(QFrame):
    # a simple VLine, like the one you get from designer
    def __init__(self):
        super(VLine, self).__init__()
        self.setFrameShape(self.VLine | self.Sunken)


class HLine(QFrame):
    # a simple HLine, like the one you get from designer
    def __init__(self):
        super(HLine, self).__init__()
        self.setFrameShape(self.HLine | self.Sunken)


# Initialize status bar with pernament widgets
# see: https://stackoverflow.com/questions/57943862/pyqt5-statusbar-separators
class StatusBarLogic:
    def __init__(self, statusBar):
        self.statusBar = statusBar

        # self.statusBar.showMessage("bla-bla bla")

        self.lbl_device = QLabel("QSource3: disconnected")
        # self.lbl_device.setStyleSheet('border: 0; color:  red;')

        self.lbl_mqtt = QLabel("MQTT: disconnected")
        # self.lbl_mqtt.setStyleSheet('border: 0; color:  red;')

        # self.statusBar.reformat()
        # self.statusBar.setStyleSheet('border: 0; background-color: #FFF8DC;')
        # self.statusBar.setStyleSheet("QStatusBar::item {border: none;}")

        self.statusBar.addPermanentWidget(VLine())  # <---
        self.statusBar.addPermanentWidget(self.lbl_device)
        self.statusBar.addPermanentWidget(VLine())  # <---
        self.statusBar.addPermanentWidget(self.lbl_mqtt)
        self.statusBar.addPermanentWidget(VLine())  # <---

    def set_device_status(self, status):
        self.lbl_device.setText(f"QSource3: {status}")

    def set_mqtt_status(self, status):
        self.lbl_mqtt.setText(f"MQTT: {status}")


class QSource3_MQTT_GUI(QMainWindow):
    def __init__(self, config):
        super().__init__()

        self.config = config

        self.client_logic = QSource3_MQTTClientLogic(config)

        self.setWindowTitle("QSource3 MQTT GUI")
        self.setWindowIcon(QIcon("icon.png"))

        self.init_ui()

        self.client_logic.start()

    def init_ui(self):
        # Create menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        open_action = file_menu.addAction("Open Settings")
        open_action.triggered.connect(self.open_settings)
        save_action = file_menu.addAction("Save Settings")
        save_action.triggered.connect(self.save_settings)
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.ask_exit)

        # Ask for confirmation when closing the window
        self.closeEvent = self.ask_exit

        # Create widgets
        self.lbl_range = QLabel("Mass Range:")
        self.list_range = QComboBox()
        for range in self.config["mass_ranges"]:
            self.list_range.addItem(range)

        self.lbl_max_mz = QLabel("Max m/z:")
        self.lbl_max_mz_value = QLabel("xxx.x")

        self.lbl_mz = QLabel("m/z:")
        self.spin_mz = QDoubleSpinBox()
        self.spin_mz.setRange(0, 2000)
        self.spin_mz.setSingleStep(0.1)
        self.spin_mz.setValue(0)

        self.lbl_dc_offst = QLabel("DC Offset:")
        self.spin_dc_offst = QDoubleSpinBox()
        self.spin_dc_offst.setRange(-100, 100)
        self.spin_dc_offst.setSingleStep(0.1)
        self.spin_dc_offst.setValue(0)

        self.lbl_dc_on = QLabel("DC On:")
        self.check_dc_on = QCheckBox()

        self.lbl_rod_polarity_positive = QLabel("Rod Pol. Pos.")
        self.check_rod_polarity_positive = QCheckBox()

        self.lbl_calib_points_mz = QLabel("Calib. Points m/z:")
        self.txt_calib_points_mz_value = QLineEdit()
        self.txt_calib_points_mz_value.setText("[[0, 0]]")

        self.lbl_calib_points_resolution = QLabel("Calib. Points Res.:")
        self.txt_calib_points_resolution_value = QLineEdit()
        self.txt_calib_points_resolution_value.setText("[[0, 0]]")

        self.lbl_freq = QLabel("Freq. [kHz]:")
        self.lbl_freq_value = QLabel("xxxx.xxx")

        self.lbl_rf_amplitude = QLabel("RF Amp 0-p [V]:")
        self.lbl_rf_amplitude_value = QLabel("xxx.xxx")

        self.lbl_dc1 = QLabel("DC1 [V]:")
        self.lbl_dc1_value = QLabel("xxx.xxx")

        self.lbl_dc2 = QLabel("DC2 [V]:")
        self.lbl_dc2_value = QLabel("xxx.xxx")

        self.lbl_current = QLabel("Current [mA]:")
        self.lbl_current_value = QLabel("xxx.xx")

        # Create grid layout
        self.grid = QGridLayout()
        self.grid.setSpacing(10)

        # add widgets to grid layout
        # 1st row
        self.grid.addWidget(self.lbl_range, 0, 0, Qt.AlignRight)
        self.grid.addWidget(self.list_range, 0, 1)

        self.grid.addWidget(VLine(), 0, 2)

        self.grid.addWidget(self.lbl_max_mz, 0, 3, Qt.AlignRight)
        self.grid.addWidget(self.lbl_max_mz_value, 0, 4)

        self.grid.addWidget(VLine(), 0, 5)

        self.grid.addWidget(self.lbl_mz, 0, 6, Qt.AlignRight)
        self.grid.addWidget(self.spin_mz, 0, 7)

        # 2nd row
        self.grid.addWidget(self.lbl_dc_offst, 1, 0, Qt.AlignRight)
        self.grid.addWidget(self.spin_dc_offst, 1, 1)

        self.grid.addWidget(VLine(), 1, 2)

        self.grid.addWidget(self.lbl_dc_on, 1, 3, Qt.AlignRight)
        self.grid.addWidget(self.check_dc_on, 1, 4)

        self.grid.addWidget(VLine(), 1, 5)

        self.grid.addWidget(self.lbl_rod_polarity_positive, 1, 6, Qt.AlignRight)
        self.grid.addWidget(self.check_rod_polarity_positive, 1, 7)

        # 3rd row
        self.grid.addWidget(self.lbl_calib_points_mz, 2, 0, Qt.AlignRight)
        self.grid.addWidget(self.txt_calib_points_mz_value, 2, 1, 1, 7)

        # 4th row
        self.grid.addWidget(self.lbl_calib_points_resolution, 3, 0, Qt.AlignRight)
        self.grid.addWidget(self.txt_calib_points_resolution_value, 3, 1, 1, 7)

        # 5th row
        # separator
        self.grid.addWidget(HLine(), 4, 0, 1, 8)

        # 6th row
        self.grid.addWidget(self.lbl_freq, 5, 0, Qt.AlignRight)
        self.grid.addWidget(self.lbl_freq_value, 5, 1)

        self.grid.addWidget(VLine(), 5, 2)

        self.grid.addWidget(self.lbl_rf_amplitude, 5, 3, Qt.AlignRight)
        self.grid.addWidget(self.lbl_rf_amplitude_value, 5, 4)

        # 7th row
        self.grid.addWidget(self.lbl_dc1, 6, 0, Qt.AlignRight)
        self.grid.addWidget(self.lbl_dc1_value, 6, 1)

        self.grid.addWidget(VLine(), 6, 2)

        self.grid.addWidget(self.lbl_dc2, 6, 3, Qt.AlignRight)
        self.grid.addWidget(self.lbl_dc2_value, 6, 4)

        # 8th row
        self.grid.addWidget(self.lbl_current, 7, 0, Qt.AlignRight)
        self.grid.addWidget(self.lbl_current_value, 7, 1)

        self.grid.addWidget(VLine(), 7, 2)

        self.grid.addWidget(QLabel(" "), 7, 3, 1, 5)

        # 9th row
        self.grid.addWidget(HLine(), 8, 0, 1, 8)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setLayout(self.grid)

        self.status_bar_logic = StatusBarLogic(self.statusBar())

        self.status_bar_logic.set_device_status("diconnected")
        self.status_bar_logic.set_mqtt_status("diconnected")

        # attach signals of widgets to slots
        self.list_range.currentIndexChanged.connect(self.on_range_changed)
        self.spin_mz.valueChanged.connect(self.on_mz_changed)
        self.spin_dc_offst.valueChanged.connect(self.on_dc_offst_changed)
        self.check_dc_on.stateChanged.connect(self.on_dc_on_changed)
        self.check_rod_polarity_positive.stateChanged.connect(
            self.on_rod_polarity_positive_changed
        )
        self.txt_calib_points_mz_value.textChanged.connect(
            self.on_calib_points_mz_changed
        )
        self.txt_calib_points_resolution_value.textChanged.connect(
            self.on_calib_points_resolution_changed
        )

        # connect signals from client_logic to slots
        self.client_logic.signal_device_status_changed.connect(
            self.status_bar_logic.set_device_status
        )

        self.client_logic.signal_mqtt_status_changed.connect(
            self.status_bar_logic.set_mqtt_status
        )

        self.client_logic.signal_max_mz_changed.connect(
            lambda x: self.lbl_max_mz_value.setText(f"{x:.1f}")
        )
        self.client_logic.signal_freq_changed.connect(
            lambda x: self.lbl_freq_value.setText(f"{(x/1000.0):.3f}")
        )
        self.client_logic.signal_rf_amp_changed.connect(
            lambda x: self.lbl_rf_amplitude_value.setText(f"{x:.2f}")
        )
        self.client_logic.signal_dc1_changed.connect(
            lambda x: self.lbl_dc1_value.setText(f"{x:.2f}")
        )
        self.client_logic.signal_dc2_changed.connect(
            lambda x: self.lbl_dc2_value.setText(f"{x:.2f}")
        )
        self.client_logic.signal_current_changed.connect(
            lambda x: self.lbl_current_value.setText(f"{x:.1f}")
        )

        self.client_logic.signal_mass_range_changed.connect(
            self.handle_signal_mass_range_changed
        )
        self.client_logic.signal_mz_changed.connect(self.handle_signal_mz_changed)
        self.client_logic.signal_dc_offst_changed.connect(
            self.handle_signal_dc_offst_changed
        )
        self.client_logic.signal_dc_on_changed.connect(self.handle_signal_dc_on_changed)
        self.client_logic.signal_rod_polarity_positive_changed.connect(
            self.handle_signal_rod_polarity_positive_changed
        )
        self.client_logic.signal_calib_points_mz_changed.connect(
            self.handle_signal_calib_points_mz_changed
        )
        self.client_logic.signal_calib_points_resolution_changed.connect(
            self.handle_signal_calib_points_resolution_changed
        )

    def open_settings(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Settings File", "", "JSON Files (*.json)"
        )
        if file_name:
            try:
                self.client_logic.load_settings(file_name)
            except ValueError as e:
                QMessageBox.critical(self, "Error", str(e))

    def save_settings(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Settings File", "", "JSON Files (*.json)"
        )
        if file_name:
            # if file exists, ask for confirmation
            if os.path.exists(file_name):
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    "Do you want to overwrite the file?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return
            self.client_logic.save_settings(file_name)

    def ask_exit(self, event=None):
        reply = QMessageBox.question(
            self,
            "Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if event:
                event.accept()
            self.close()
        else:
            if event:
                event.ignore()

    # slots for signals from widgets
    def on_range_changed(self, index):
        self.client_logic.publish_mass_range(index)

    def on_mz_changed(self, value):
        self.client_logic.publish_mz(value)

    def on_dc_offst_changed(self, value):
        self.client_logic.publish_dc_offst(value)

    def on_dc_on_changed(self, state):
        self.client_logic.publish_dc_on(self.check_dc_on.isChecked())

    def on_rod_polarity_positive_changed(self, state):
        self.client_logic.publish_rod_polarity_positive(
            self.check_rod_polarity_positive.isChecked()
        )

    def on_calib_points_mz_changed(self, text):
        try:
            calib_points = json.loads(text)
            self.client_logic.publish_calib_points_mz(calib_points)
            set_color(self.txt_calib_points_mz_value, COLOR_VALID)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(e)
            set_color(self.txt_calib_points_mz_value, COLOR_INVALID)

    def on_calib_points_resolution_changed(self, text):
        try:
            calib_points = json.loads(text)
            self.client_logic.publish_calib_points_resolution(calib_points)
            set_color(self.txt_calib_points_resolution_value, COLOR_VALID)
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(e)
            set_color(self.txt_calib_points_resolution_value, COLOR_INVALID)

    # slots for signals from client_logic
    def handle_signal_mass_range_changed(self, range: int):
        # disconnect signal to avoid infinite loop
        self.list_range.currentIndexChanged.disconnect(self.on_range_changed)
        self.list_range.setCurrentIndex(range)
        self.list_range.currentIndexChanged.connect(self.on_range_changed)

    def handle_signal_mz_changed(self, mz: float):
        self.spin_mz.valueChanged.disconnect(self.on_mz_changed)
        self.spin_mz.setValue(mz)
        self.spin_mz.valueChanged.connect(self.on_mz_changed)

    def handle_signal_dc_offst_changed(self, dc_offst: float):
        self.spin_dc_offst.valueChanged.disconnect(self.on_dc_offst_changed)
        self.spin_dc_offst.setValue(dc_offst)
        self.spin_dc_offst.valueChanged.connect(self.on_dc_offst_changed)

    def handle_signal_dc_on_changed(self, dc_on: bool):
        self.check_dc_on.stateChanged.disconnect(self.on_dc_on_changed)
        self.check_dc_on.setChecked(dc_on)
        self.check_dc_on.stateChanged.connect(self.on_dc_on_changed)

    def handle_signal_rod_polarity_positive_changed(self, rod_polarity_positive: bool):
        self.check_rod_polarity_positive.stateChanged.disconnect(
            self.on_rod_polarity_positive_changed
        )
        self.check_rod_polarity_positive.setChecked(rod_polarity_positive)
        self.check_rod_polarity_positive.stateChanged.connect(
            self.on_rod_polarity_positive_changed
        )

    def handle_signal_calib_points_mz_changed(self, calib_points: list):
        self.txt_calib_points_mz_value.textChanged.disconnect(
            self.on_calib_points_mz_changed
        )
        self.txt_calib_points_mz_value.setText(json.dumps(calib_points))
        self.txt_calib_points_mz_value.textChanged.connect(
            self.on_calib_points_mz_changed
        )

    def handle_signal_calib_points_resolution_changed(self, calib_points: list):
        self.txt_calib_points_resolution_value.textChanged.disconnect(
            self.on_calib_points_resolution_changed
        )
        self.txt_calib_points_resolution_value.setText(json.dumps(calib_points))
        self.txt_calib_points_resolution_value.textChanged.connect(
            self.on_calib_points_resolution_changed
        )
