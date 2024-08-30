# GUI applicaption to control JanasCard QSource3 over MQTT.

import logging
import sys

import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets
import yaml

from qsource3_mqtt_gui.qsource3_mqtt_gui import QSource3_MQTT_GUI

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main(config_file):
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("QSource3 MQTT GUI")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("JHI")
    app.setOrganizationDomain("jh-inst.cas.cz")

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    window = QSource3_MQTT_GUI(config)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    main(config_file)
