#!/usr/bin/python3

import loopablecamgear
import cv2
import numpy as np

import socket
import requests
import json
import math
import logging
from vidgear.gears.helper import logger_handler

from typing import Union, List


class VideoCapture:
    def __init__(self, source: Union[str, int], loop: bool = False) -> None:
        stream_mode = False
        options = {}
        if type(source) != int and "://" in source:
            stream_mode = True
            options = {"STREAM_RESOLUTION": "360p"}

        self.logger = logging.getLogger("VideoCapture")
        self.logger.propagate = False
        self.logger.addHandler(logger_handler())
        self.logger.setLevel(logging.DEBUG)

        try:
            self.video = loopablecamgear.LoopableCamGear(
                source=source,
                stream_mode=stream_mode,
                logging=True,
                loop=loop,
                **options
            ).start()
        except ValueError:
            self.logger.info("Source is not an URL that yt_dlp can handle.")
            self.video = loopablecamgear.LoopableCamGear(
                source=source,
                logging=True,
                loop=loop,
            ).start()


class WLEDStreamer:
    MESSAGE_TYPE_DNRGB = 4
    MAX_PIXELS_PER_FRAME = 480

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 21234,
        width: int = 0,
        height: int = 0,
        crop: List[int] = [],
        scale: str = "fill",
        interpolation: str = "smooth",
        gamma: float = 0.5,
    ) -> None:
        self.logger = logging.getLogger("WLEDStreamer")
        self.logger.propagate = False
        self.logger.addHandler(logger_handler())
        self.logger.setLevel(logging.DEBUG)

        self._wled_info = {}  # type: Dict[str, Any]

        self.ip = socket.gethostbyname(host)
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.width = width
        self.height = height
        if self.width == 0 or self.height == 0:
            self.logger.info("Getting dimensions from wled...")
            self.width, self.height = self._getDimensions()
            self.logger.debug("width: %d, height: %d" % (self.width, self.height))
            if self.width == 0 or self.height == 0:
                self.logger.error(
                    "Could not get width and/or height from wled instance."
                )
                sys.exit()
        self._display_ratio = self.width / self.height

        self.crop = crop
        self.scale = scale

        inverseGamma = 1 / gamma
        self._gamma_table = [((i / 255) ** inverseGamma) * 255 for i in range(256)]
        self._gamma_table = np.array(self._gamma_table, np.uint8)

        self._interpolation = (
            cv2.INTER_NEAREST if interpolation == "hard" else cv2.INTER_AREA
        )

    def close(self):
        self.socket.close()

    def cropFrame(self, frame: np.ndarray) -> np.ndarray:
        if self.crop:
            frame_height, frame_width = frame.shape[:2]
            frame = frame[
                self.crop[1] : frame_height - self.crop[3],
                self.crop[0] : frame_width - self.crop[2],
            ]

        return frame

    def scaleFrame(self, frame: np.ndarray) -> np.ndarray:
        frame_height, frame_width = frame.shape[:2]

        if self.scale == "stretch":
            frame = cv2.resize(
                frame, (self.width, self.height), interpolation=self._interpolation
            )
        else:
            if self.scale in ["fill", "fit"]:
                image_ratio = frame_width / frame_height

                if (self.scale == "fill" and image_ratio > self._display_ratio) or (
                    self.scale == "fit" and image_ratio < self._display_ratio
                ):
                    size = (math.floor(self.height * image_ratio), self.height)
                else:
                    size = (self.width, math.floor(self.width / image_ratio))
                frame = cv2.resize(frame, size, interpolation=self._interpolation)

            frame_height, frame_width = frame.shape[:2]
            left = math.floor((frame_width - self.width) / 2)
            top = math.floor((frame_height - self.height) / 2)
            frame = frame[top : (top + self.height), left : (left + self.width)]
            # NB: frame could now be smaller than self.width, self.height!
            # see extension below

        frame_height, frame_width = frame.shape[:2]
        if frame_width < self.width or frame_height < self.height:
            left = math.floor((self.width - frame_width) / 2)
            right = self.width - frame_width - left
            top = math.floor((self.height - frame_height) / 2)
            bottom = self.height - frame_height - top
            frame = cv2.copyMakeBorder(
                frame, top, bottom, left, right, cv2.BORDER_CONSTANT, 0
            )

        return frame

    def gammaCorrectFrame(self, frame: np.ndarray) -> np.ndarray:
        return cv2.LUT(frame, self._gamma_table)

    def sendFrame(self, frame: np.ndarray) -> None:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = frame.flatten()

        for start in range(0, int(frame.size / 3), self.MAX_PIXELS_PER_FRAME):
            start_h = start >> 8
            start_l = start & 0xFF

            message = (
                bytes([self.MESSAGE_TYPE_DNRGB, 2, start_h, start_l])
                + frame[(start * 3) : (start + self.MAX_PIXELS_PER_FRAME) * 3]
                .astype("int8")
                .tobytes()
            )

            self.socket.sendto(message, (self.ip, self.port))

    def _loadInfo(self) -> None:
        response = requests.get("http://" + self.ip + "/json/info", timeout=5)
        self._wled_info = json.loads(response.text)

    def _getDimensions(self) -> (int, int):
        if not self._wled_info:
            try:
                self._loadInfo()
            except Exception:
                self.logger.warning("Could not get information from WLED.")
                return 0, 0

        try:
            width = self._wled_info["leds"]["matrix"]["w"]
            height = self._wled_info["leds"]["matrix"]["h"]
        except Exception:
            self.logger.warning("Dimensions not found in info from WLED.")
            return 0, 0

        return width, height


if __name__ == "__main__":
    import sys
    import argparse
    import toml

    DEFAULT_CONFIG_FILE = "config.toml"
    CONFIG_DEFAULTS = {
        "source": "" if "--camera" not in sys.argv else 0,
        "loop": False,
        "camera": False,
        "debug": False,
    }
    STREAMER_CONFIG_DEFAULTS = {
        "host": "127.0.0.1",
        "port": 21234,
        "width": 0,
        "height": 0,
        "crop": [],
        "scale": "fill",
        "interpolation": "smooth",
        "gamma": 0.5,
    }

    parser = argparse.ArgumentParser()

    #
    # first parse arguments only for the config file
    #
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE)
    if "--help" not in sys.argv and "-h" not in sys.argv:
        args = parser.parse_known_args()

        try:
            config = toml.load(args[0].config)
        except FileNotFoundError:
            if args[0].config != DEFAULT_CONFIG_FILE:
                print("Specified config not found")
                sys.exit(0)
            config = {}
    else:
        config = {}

    try:
        stream_config = config["server"]
    except KeyError:
        stream_config = {}
    if isinstance(stream_config, List):
        stream_config = stream_config[0]
    if "server" not in config:
        config["server"] = [stream_config]

    #
    # parse the rest of the arguments
    #

    # utility method to parse crop arguments
    def cropArgument(argument: str) -> List[int]:
        if isinstance(argument, List):
            crop_amounts = [int(a) for a in argument]
        else:
            crop_amounts = [int(a) for a in argument.split(",")]

        if len(crop_amounts) == 1:
            crop_amounts = crop_amounts * 4
        elif len(crop_amounts) == 2:
            crop_amounts = crop_amounts * 2
        elif len(crop_amounts) in [0, 4]:
            pass
        else:
            raise ValueError

        return crop_amounts

    # get default from config file or from defaults
    def getDefault(key: str) -> Union[str, int, float, bool, List[int]]:
        return config[key] if key in config else CONFIG_DEFAULTS[key]

    def getStreamerDefault(key: str) -> Union[str, int, float, bool, List[int]]:
        return (
            stream_config[key]
            if key in stream_config
            else STREAMER_CONFIG_DEFAULTS[key]
        )

    parser.add_argument(
        "--host",
        default=getStreamerDefault("host"),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=getStreamerDefault("port"),
    )
    parser.add_argument(
        "--width",
        type=int,
        default=getStreamerDefault("width"),
        help="width of the LED matrix. If not specified, this will be automatically retreived from the WLED instance",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=getStreamerDefault("height"),
        help="height of the LED matrix. If not specified, this will be automatically retreived from the WLED instance",
    )

    parser.add_argument(
        "--crop",
        type=cropArgument,
        default=cropArgument(getStreamerDefault("crop")),
        help="pixels to crop from the image. Can be either 1, 2 or 4 integer values to crop from respectively cropping all sides by the same amount, different amount horizontally and vertically, or all sides individually",
    )
    parser.add_argument(
        "--scale",
        choices=["stretch", "fill", "fit", "crop"],
        default=getStreamerDefault("scale"),
        help="'stretch' stretches the video to the panel, disregarding aspect ratio, 'fill' scales the video so the whole panel is covered (default), 'fit' scales the whole video onto the panel adding black bars, 'crop' shows only the center of the video at 100%%",
    )
    parser.add_argument(
        "--interpolation",
        choices=["hard", "smooth"],
        default=getStreamerDefault("interpolation"),
        help="'smooth' uses pixel area relation when scaling the video (default), 'hard' uses nearest neighbour algorithm leading to crisper edges",
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=getStreamerDefault("gamma"),
        help="adjust for non-linearity of LEDs, defaults to 0.5",
    )

    parser.add_argument(
        "source",
        nargs="?" if "source" in config or "--camera" in sys.argv else 1,
        type=str if "--camera" not in sys.argv else int,
        default=getDefault("source"),
        help="The video file to stream (required unless a source is specified in the config file). If --camera is set, 'source' shall be the index of the camera source (defaulting to 0)",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        default=getDefault("loop"),
    )
    parser.add_argument(
        "--camera",
        action="store_true",
        default=getDefault("camera"),
        help="use a webcam instead of a video",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=getDefault("debug"),
        help="show the output in a window while streaming",
    )

    args = parser.parse_args()

    if args.source:
        if isinstance(args.source, list):
            source = args.source[0]
        else:
            source = args.source
    else:
        if args.camera:
            source = 0

    config["server"][0] = {
        "host": args.host,
        "port": args.port,
        "width": args.width,
        "height": args.height,
        "crop": args.crop,
        "scale": args.scale,
        "interpolation": args.interpolation,
        "gamma": args.gamma,
    }

    wled_streamers = []

    for stream in config["server"]:
        wled_streamers.append(WLEDStreamer(**stream))

    player = VideoCapture(source=source, loop=args.loop)

    while True:
        try:
            frame = player.video.read()
            if frame is None:
                break

            for index, wled_streamer in enumerate(wled_streamers):
                stream_frame = wled_streamer.cropFrame(frame)
                stream_frame = wled_streamer.scaleFrame(stream_frame)
                stream_frame = wled_streamer.gammaCorrectFrame(stream_frame)
                wled_streamer.sendFrame(stream_frame)

                if args.debug:
                    cv2.imshow("wledvideo %d" % index, stream_frame)
            if args.debug:
                if cv2.waitKey(1) & 255 in [27, ord("q")]:
                    break

        except (KeyboardInterrupt, SystemExit):
            break

    player.video.stop()
    cv2.destroyAllWindows()
    for wled_streamer in wled_streamers:
        wled_streamer.close()
