import json
import logging
import socket

import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject, pyqtSignal

from .utils import (
    check_calib_points_mz,
    check_calib_points_resolution,
    check_dc_offst,
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
    signal_dc_offst_changed = pyqtSignal(float)
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
            "dc_offst": 0,
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
        self.client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
        self.client.loop_start()
        logger.debug("MQTT client started")

    def load_settings(self, json_file_name):
        with open(json_file_name, "r") as f:
            settings = json.load(f)

            # Verify the settings if they are valid
            check_mass_range(settings["mass_range"])
            check_mz(settings["mz"])
            check_dc_offst(settings["dc_offst"])
            check_dc_on(settings["dc_on"])
            check_rod_polarity_positive(settings["rod_polarity_positive"])
            check_calib_points_mz(settings["calib_points_mz"])
            check_calib_points_resolution(settings["calib_points_resolution"])

            self.settings = settings

            self.publish_mass_range(settings["mass_range"])
            self.publish_mz(settings["mz"])
            self.publish_dc_offst(settings["dc_offst"])
            self.publish_dc_on(settings["dc_on"])
            self.publish_rod_polarity_positive(settings["rod_polarity_positive"])
            self.publish_calib_points_mz(settings["calib_points_mz"])
            self.publish_calib_points_resolution(settings["calib_points_resolution"])

    def save_settings(self, json_file_name):
        # Save the settings to a JSON file
        with open(json_file_name, "w") as f:
            json.dump(self.settings, f)

    def on_connect(self, client, userdata, flags, rc):
        logger.debug(f"Connected with result code {rc}")

        subscription_topics = [
            f"{self.topic_base}/response/{self.device_name}/#",
            f"{self.topic_base}/connected/{self.device_name}",
            f"{self.topic_base}/error/{self.device_name}/#",
            f"{self.topic_base}/status/{self.device_name}/state",
        ]

        for topic in subscription_topics:
            self.client.subscribe(topic)
            logger.debug(f"Subscribed to {topic}")

        self.signal_mqtt_status_changed.emit(
            f"connected to broker {self.config['mqtt_broker']}:{self.config['mqtt_port']}"
        )

    def on_message(self, client, userdata, message):
        # logger.debug(f"Received message {message}")
        topic = message.topic
        logger.debug(f"Received message on topic {topic}")

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
        elif topic.endswith("state"):
            self.handle_device_state(payload)
        elif topic.endswith("range"):
            self.handle_range(payload)
        elif topic.endswith("mz"):
            self.handle_mz(payload)
        elif topic.endswith("dc_offst"):
            self.handle_dc_offst(payload)
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

        self.request_device_state()
        self.request_dc_offst()
        self.request_calib_points_mz()
        self.request_calib_points_resolution()

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
                logger.debug(f"Mass range: {payload['range']}")
            except ValueError as e:
                logger.debug(e)
        if "frequency" in payload:
            self.signal_freq_changed.emit(payload["frequency"])
            logger.debug(f"Frequency: {payload['frequency']}")
        if "rf_amp" in payload:
            self.signal_rf_amp_changed.emit(payload["rf_amp"])
            logger.debug(f"RF amplitude: {payload['rf_amp']}")
        if "dc1" in payload:
            self.signal_dc1_changed.emit(payload["dc1"])
            logger.debug(f"DC1: {payload['dc1']}")
        if "dc2" in payload:
            self.signal_dc2_changed.emit(payload["dc2"])
            logger.debug(f"DC2: {payload['dc2']}")
        if "current" in payload:
            self.signal_current_changed.emit(payload["current"])
            logger.debug(f"Current: {payload['current']}")
        if "mz" in payload:
            self.signal_mz_changed.emit(payload["mz"])
            logger.debug(f"m/z: {payload['mz']}")
        if "dc_offst" in payload:
            self.signal_dc_offst_changed.emit(payload["dc_offst"])
            logger.debug(f"DC offset: {payload['dc_offst']}")
        if "is_dc_on" in payload:
            self.signal_dc_on_changed.emit(payload["is_dc_on"])
            logger.debug(f"DC power on: {payload['is_dc_on']}")
        if "is_rod_polarity_positive" in payload:
            self.signal_rod_polarity_positive_changed.emit(
                payload["is_rod_polarity_positive"]
            )
            logger.debug(
                f"Rod polarity positive: {payload['is_rod_polarity_positive']}"
            )
        if "max_mz" in payload:
            self.signal_max_mz_changed.emit(payload["max_mz"])
            logger.debug(f"Max m/z: {payload['max_mz']}")

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
    def handle_dc_offst(self, payload):
        try:
            check_dc_offst(payload["value"])
            self.settings["dc_offst"] = payload["value"]
            self.signal_dc_offst_changed.emit(payload["value"])
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
    def publish_dc_offst(self, dc_offst: float):
        """
        Publishes the DC offset value to the MQTT broker.

        Args:
            dc_offst (float): The DC offset value to be published.

        Raises:
            ValueError: If the provided DC offset value is invalid.

        """
        check_dc_offst(dc_offst)
        self.settings["dc_offst"] = dc_offst
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/dc_offst",
            json.dumps({"value": dc_offst}),
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
    def publish_calib_points_resolution(self, calib_points_resolution):
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

    @client_connected
    @log_func
    def request_device_state(self):
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/state",
            json.dumps({}),
        )

    @client_connected
    @log_func
    def request_dc_offst(self):
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/dc_offst",
            json.dumps({}),
        )

    @client_connected
    @log_func
    def request_calib_points_mz(self):
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/calib_pnts_rf",
            json.dumps({}),
        )

    @client_connected
    @log_func
    def request_calib_points_resolution(self):
        self.client.publish(
            f"{self.topic_base}/cmnd/{self.device_name}/calib_pnts_dc",
            json.dumps({}),
        )
