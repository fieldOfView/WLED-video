#!/usr/bin/python3

import cv2
import numpy as np
import socket
import math
import requests
import json


class WLEDVideo:
    MESSAGE_TYPE_DNRGB = 4
    MAX_PIXELS_PER_FRAME = 480
    RESAMPLING = cv2.INTER_AREA

    def __init__(
        self,
        video: str,
        host: str,
        port: int,
        width: int,
        height: int,
        scale: str,
        gamma: float,
        debug: bool,
    ) -> None:
        self._wled_info = {}  # type: Dict[str, Any]

        self.video = video

        self.ip = socket.gethostbyname(host)
        self.port = port

        self.width = width
        self.height = height
        if self.width == 0 or self.height == 0:
            print("Getting dimensions from wled...")
            self.width, self.height = self._getDimensions()
            print("width: %d, height: %d" % (self.width, self.height))
        self._display_ratio = self.width / self.height

        self.scale = scale

        inverseGamma = 1 / gamma
        self._gamma_table = [((i / 255) ** inverseGamma) * 255 for i in range(256)]
        self._gamma_table = np.array(self._gamma_table, np.uint8)

        self.debug = debug

    def stream(self) -> None:
        cap = cv2.VideoCapture(self.video)
        if not cap.isOpened():
            return

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame = self._scaleFrame(frame)
                frame = self._gammaCorrectFrame(frame)
                self._sendFrame(sock, frame)

                if self.debug:
                    cv2.imshow("Frame", frame)

                cv2.waitKey(25)

                # Press Q on keyboard to exit
                # if cv2.waitKey(25) & 0xFF == ord('q'):
                #    break

    def _scaleFrame(self, frame: np.ndarray) -> np.ndarray:
        frame_height, frame_width = frame.shape[:2]

        if self.scale == "stretch":
            frame = cv2.resize(
                frame, (self.width, self.height), interpolation=self.RESAMPLING
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
                frame = cv2.resize(frame, size, interpolation=self.RESAMPLING)

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

    def _gammaCorrectFrame(self, frame: np.ndarray) -> np.ndarray:
        return cv2.LUT(frame, self._gamma_table)

    def _sendFrame(self, sock: socket.socket, frame: np.ndarray) -> None:
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

            sock.sendto(message, (self.ip, self.port))

    def _loadInfo(self) -> None:
        response = requests.get("http://" + self.ip + "/json/info", timeout=5)
        self._wled_info = json.loads(response.text)

    def _getDimensions(self) -> (int, int):
        if not self._wled_info:
            self._loadInfo()

        width = self._wled_info["leds"]["matrix"]["w"]
        height = self._wled_info["leds"]["matrix"]["w"]

        return width, height


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=21324)
    parser.add_argument("--width", type=int, default=0)
    parser.add_argument("--height", type=int, default=0)
    parser.add_argument("--gamma", type=float, default=0.5)
    parser.add_argument(
        "--scale",
        choices=["stretch", "fill", "fit", "crop"],
        default="fill",
    )
    parser.add_argument(
        "video",
        nargs=1 if "--camera" not in sys.argv else "?",
        type=str if "--camera" not in sys.argv else int,
        help="if --camera is set, 'video' shall be the index of the camera source (defaults to 0)"
    )
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()
    if args.video:
        if isinstance(args.video, list):
            video = args.video[0]
        else:
            video = args.video
    else:
        if args.camera:
            video = 0

    player = WLEDVideo(
        video,
        args.host,
        args.port,
        args.width,
        args.height,
        args.scale,
        args.gamma,
        args.debug,
    )
    player.stream()
