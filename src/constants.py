import sys

DEFAULT_CONFIG_FILE = "config.toml"
CONFIG_DEFAULTS = {
    "source": "" if "--camera" not in sys.argv and "--display" not in sys.argv else 0,
    "loop": False,
    "camera": False,
    "display": False,
    "debug": False,
}
STREAMER_CONFIG_DEFAULTS = {
    "host": "127.0.0.1",
    "port": 21324,
    "serial": "",
    "baudrate": 115200,
    "width": 0,
    "height": 0,
    "crop": [],
    "scale": "fill",
    "interpolation": "smooth",
    "gamma": 0.5,
}
