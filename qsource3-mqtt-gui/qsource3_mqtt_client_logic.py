import json
import logging

import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject, pyqtSignal

from .utils import (
    check_calib_points_mz,
    check_calib_points_resolution,
    check_dc_offset,
    check_dc_on,
    check_mass_range,
    check_mz,
    check_rod_polarity_positive,
    verify_calib_points,
)

logger = logging.getLogger(__name__)


# decorator to check if the client is connected
def client_connected(func):
    def wrapper(self, *args, **kwargs):
        if not self.client.is_connected():
            logger.warning("Client is not connected")
            return
        return func(self, *args, **kwargs)

    return wrapper


# decorator to log the function call
def log_func(func):
    def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        return func(*args, **kwargs)

    return wrapper


class QSource3_MQTTClientLogic(QObject):
    signal_device_status_changed = pyqtSignal(str)
    signal_mqtt_status_changed = pyqtSignal(str)

    signal_max_mz_changed = pyqtSignal(float)
    signal_freq_changed = pyqtSignal(float)
    signal_rf_amp_changed = pyqtSignal(float)
    signal_dc1_changed = pyqtSignal(float)
    signal_dc2_changed = pyqtSignal(float)
    signal_current_changed = pyqtSignal(float)

    signal_mass_range_changed = pyqtSignal(int)
    signal_mz_changed = pyqtSignal(float)
    signal_dc_offset_changed = pyqtSignal(float)
    signal_dc_on_changed = pyqtSignal(bool)
    signal_rod_polarity_positive_changed = pyqtSignal(bool)
    signal_calib_points_mz_changed = pyqtSignal(list)
    signal_calib_points_resolution_changed = pyqtSignal(list)

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.settings = {
            "mass_range": 0,
            "mz": 0,
            "dc_offset": 0,
            "dc_on": True,
            "rod_polarity_positive": True,
            "calib_points_mz": [[0, 0]],
            "calib_points_resolution": [[0, 0]],
        }

        self.topic_base = self.config["topic_base"]
        self.device_name = self.config["device_name"]

        self.client = mqtt.Client(
            clean_session=True,
        )

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        self.client.connect(
            self.config["mqtt_broker"],
            self.config["mqtt_port"],
            self.config["mqtt_connection_timeout"],
        )
        self.client.loop_start()

    def load_settings(self, json_file_name):
        with open(json_file_name, "r") as f:
            settings = json.load(f)

            # Verify the settings if they are valid
            check_mass_range(settings["mass_range"])
            check_mz(settings["mz"])
            check_dc_offset(settings["dc_offset"])
            check_dc_on(settings["dc_on"])
            check_rod_polarity_positive(settings["rod_polarity_positive"])
            check_calib_points_mz(settings["calib_points_mz"])
            check_calib_points_resolution(settings["calib_points_resolution"])

            self.settings = settings

            self.signal_mass_range_changed.emit(settings["mass_range"])
            self.signal_mz_changed.emit(settings["mz"])
            self.signal_dc_offset_changed.emit(settings["dc_offset"])
            self.signal_dc_on_changed.emit(settings["dc_on"])
            self.signal_rod_polarity_positive_changed.emit(
                settings["rod_polarity_positive"]
            )
            self.signal_calib_points_mz_changed.emit(settings["calib_points_mz"])
            self.signal_calib_points_resolution_changed.emit(
                settings["calib_points_resolution"]
            )

    def save_settings(self, json_file_name):
        # Save the settings to a JSON file
        with open(json_file_name, "w") as f:
            json.dump(self.settings, f)

    def on_connect(self, client, userdata, flags, rc):
        logger.debug(f"Connected with result code {rc}")

        self.client.subscribe(f"{self.topic_base}/response/{self.device_name}/#")
        self.client.subscribe(f"{self.topic_base}/connected/{self.device_name}")
        self.client.subscribe(f"{self.topic_base}/error/{self.device_name}")

        self.signal_mqtt_status_changed.emit(
            f"connected to broker {self.config['mqtt_broker']}:{self.config['mqtt_port']}"
        )

    def on_message(self, client, userdata, message):
        topic = message.topic
        try:
            payload = json.loads(message.payload.decode())
        except json.JSONDecodeError as e:
            logger.debug(f"Error decoding message payload: {e}")
            payload = {}

        logger.debug(f"Received message on topic {topic} with payload {payload}")

        if "/connected/" in topic:
            self.handle_device_connected(message)
        elif "/error/" in topic:
            self.handle_device_error(message)
        elif "/state/" in topic:
            self.handle_device_state(payload)
        elif topic.endswith("range"):
            self.handle_range(payload)
        elif topic.endswith("mz"):
            self.handle_mz(payload)
        elif topic.endswith("dc_offset"):
            self.handle_dc_offset(payload)
        elif topic.endswith("dc_on"):
            self.handle_dc_on(payload)
        elif topic.endswith("rod_polarity_positive"):
            self.handle_rod_polarity_positive(payload)
        elif topic.endswith("calib_points_mz"):
            self.handle_calib_points_mz(payload)
        elif topic.endswith("calib_points_resolution"):
            self.handle_calib_points_resolution(payload)
        elif topic.endswith("max_mz"):
            self.handle_max_mz(payload)

    # handle functions
    def handle_device_connected(self, message):
        logger.info("Device connected")
        self.signal_device_status_changed.emit("connected")

    def handle_device_error(self, message):
        logger.warning(f"Device error: {message.payload}")
        self.signal_device_status_changed.emit("IO error")

    @log_func
    def handle_device_state(self, payload):
        if "range" in payload:
            try:
                check_mass_range(payload["range"])
                self.settings["mass_range"] = payload["range"]
                self.signal_mass_range_changed.emit(payload["range"])
            except ValueError as e:
                logger.debug(e)
        if "frequency" in payload:
            self.signal_freq_changed.emit(payload["frequency"])
        if "rf_amp" in payload:
            self.signal_rf_amp_changed.emit(payload["rf_amp"])
        if "dc1" in payload:
            self.signal_dc1_changed.emit(payload["dc1"])
        if "dc2" in payload:
            self.signal_dc2_changed.emit(payload["dc2"])
        if "current" in payload:
            self.signal_current_changed.emit(payload["current"])
        if "mz" in payload:
            self.signal_mz_changed.emit(payload["mz"])
        if "is_dc_on" in payload:
            self.signal_dc_on_changed.emit(payload["is_dc_on"])
        if "is_rod_polarity_positive" in payload:
            self.signal_rod_polarity_positive_changed.emit(
                payload["is_rod_polarity_positive"]
            )
        if "max_mz" in payload:
            self.signal_max_mz_changed.emit(payload["max_mz"])

    @log_func
    def handle_range(self, payload):
        try:
            check_mass_range(payload["value"])
            self.settings["mass_range"] = payload["value"]
            self.signal_mass_range_changed.emit(payload["value"])
        except ValueError as e:
            logger.debug(e)

    @log_func
    def handle_mz(self, payload):
        try:
            check_mz(payload["value"])
            self.settings["mz"] = payload["value"]
            self.signal_mz_changed.emit(payload["value"])
        except ValueError as e:
            logger.debug(e)

    @log_func
    def handle_dc_offset(self, payload):
        try:
            check_dc_offset(payload["value"])
            self.settings["dc_offset"] = payload["value"]
            self.signal_dc_offset_changed.emit(payload["value"])
        except ValueError as e:
            logger.debug(e)

    @log_func
    def handle_dc_on(self, payload):
        try:
            check_dc_on(payload["value"])
            self.settings["dc_on"] = payload["value"]
            self.signal_dc_on_changed.emit(payload["value"])
        except ValueError as e:
            logger.debug(e)

    @log_func
    def handle_rod_polarity_positive(self, payload):
        try:
            check_rod_polarity_positive(payload["value"])
            self.settings["rod_polarity_positive"] = payload["value"]
            self.signal_rod_polarity_positive_changed.emit(payload["value"])
        except ValueError as e:
            logger.debug(e)

    @log_func
    def handle_calib_points_mz(self, payload):
        try:
            verify_calib_points(payload["value"])
            self.settings["calib_points_mz"] = payload["value"]
            self.signal_calib_points_mz_changed.emit(payload["value"])
        except ValueError as e:
            logger.debug(e)

    @log_func
    def handle_calib_points_resolution(self, payload):
        try:
            verify_calib_points(payload["value"])
            self.settings["calib_points_resolution"] = payload["value"]
            self.signal_calib_points_resolution_changed.emit(payload["value"])
        except ValueError as e:
            logger.debug(e)

    @log_func
    def handle_max_mz(self, payload):
        self.signal_max_mz_changed.emit(payload["value"])

    # publish functions
    @client_connected
    @log_func
    def publish_mass_range(self, range):
        """
        Publishes the mass range to the MQTT broker.

        Args:
            range (float): The mass range value to be published.

        Raises:
            ValueError: If the mass range is invalid.

        """
        check_mass_range(range)
        self.settings["mass_range"] = range
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/range",
            json.dumps({"value": range}),
        )

    @client_connected
    @log_func
    def publish_mz(self, mz: float):
        """
        Publishes the given mz value to the MQTT broker.

        Args:
            mz (float): The mz value to be published.

        Raises:
            ValueError: If the provided mz value is invalid.
        """
        check_mz(mz)
        self.settings["mz"] = mz
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/mz",
            json.dumps({"value": mz}),
        )

    @client_connected
    @log_func
    def publish_dc_offset(self, dc_offset: float):
        """
        Publishes the DC offset value to the MQTT broker.

        Args:
            dc_offset (float): The DC offset value to be published.

        Raises:
            ValueError: If the provided DC offset value is invalid.

        """
        check_dc_offset(dc_offset)
        self.settings["dc_offset"] = dc_offset
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/dc_offst",
            json.dumps({"value": dc_offset}),
        )

    @client_connected
    @log_func
    def publish_dc_on(self, dc_on: bool):
        """
        Publishes the state of the DC power on/off to the MQTT broker.

        Args:
            dc_on (bool): The state of the DC power. True for on, False for off.

        Raises:
            ValueError: If the `dc_on` parameter is not a boolean value.

        """
        check_dc_on(dc_on)
        self.settings["dc_on"] = dc_on
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/is_dc_on",
            json.dumps({"value": dc_on}),
        )

    @client_connected
    @log_func
    def publish_rod_polarity_positive(self, rod_polarity_positive: bool):
        """
        Publishes the rod polarity positive value to the MQTT broker.

        Args:
            rod_polarity_positive (bool): The value of rod polarity positive.

        Raises:
            ValueError: If the rod_polarity_positive value is not a boolean value.

        """
        check_rod_polarity_positive(rod_polarity_positive)
        self.settings["rod_polarity_positive"] = rod_polarity_positive
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/is_rod_polarity_positive",
            json.dumps({"value": rod_polarity_positive}),
        )

    @client_connected
    @log_func
    def publish_calib_points_mz(self, calib_points_mz: list):
        """
        Publish the calibration points for the mz values.

        Parameters:
        - calib_points_mz: A list of calibration points for the mz values.

        Raises:
        - TypeError: If the calibration points are not valid.

        Returns:
        - None
        """
        verify_calib_points(calib_points_mz)
        self.settings["calib_points_mz"] = calib_points_mz
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/calib_pnts_rf",
            json.dumps({"value": calib_points_mz}),
        )

    @client_connected
    @log_func
    def set_calib_points_resolution(self, calib_points_resolution):
        """
        Publish the calibration points for the resolution.

        Parameters:
        - calib_points_mz: A list of calibration points for resolution.

        Raises:
        - TypeError: If the calibration points are not valid.

        Returns:
        - None
        """
        verify_calib_points(calib_points_resolution)
        self.settings["calib_points_resolution"] = calib_points_resolution
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/calib_pnts_dc",
            json.dumps({"value": calib_points_resolution}),
        )
