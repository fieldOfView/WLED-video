import cv2
import numpy as np

import socket
import requests
import json
import math
import logging
import sys

from typing import List

from vidgear.gears.helper import logger_handler


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
