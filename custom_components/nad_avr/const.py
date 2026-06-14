"""Constants for the NAD AVR integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "nad_avr"
MANUFACTURER = "NAD"

CONF_CONNECTION_TYPE = "connection_type"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_MODEL = "model"
CONF_QUERY_ALL = "query_all"

CONNECTION_TELNET = "telnet"
CONNECTION_RS232 = "rs232"
CONNECTION_TYPES = [CONNECTION_TELNET, CONNECTION_RS232]

MODEL_AUTO = "auto"
MODELS = [MODEL_AUTO, "T187", "T777", "T787"]

DEFAULT_NAME = "NAD AVR"
DEFAULT_PORT = 23
DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 2.0
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_QUERY_ALL = False

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
]

CORE_VARIABLES = {
    "Main.Model",
    "Main.Power",
    "Main.Volume",
    "Main.Mute",
    "Main.Source",
    "Main.ListeningMode",
    "Main.AudioMode",
    "Main.VideoMode",
    "Main.Bass",
    "Main.Treble",
    "Main.CenterDialog",
    "Main.Dimmer",
    "DSP.Version",
    "Zone2.Power",
    "Zone2.Mute",
    "Zone2.Source",
    "Zone2.Volume",
    "Zone3.Power",
    "Zone3.Mute",
    "Zone3.Source",
    "Zone3.Volume",
    "Zone4.Power",
    "Zone4.Mute",
    "Zone4.Source",
    "Zone4.Volume",
}

SOURCE_MIN = 1
SOURCE_MAX = 10
VOLUME_MIN_DB = -99
VOLUME_MAX_DB = 19
