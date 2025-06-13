import cv2
import numpy as np

import socket
import requests
import json
import struct

from typing import List

from .wledstreamer import WLEDStreamer


class UDPWLEDStreamer(WLEDStreamer):
    MAX_PIXELS_PER_DATAGRAM = 480

    VER1 = 0x40  # version=1
    PUSH = 0x01
    RGBTYPE = 0x01         # TTT=001 (RGB)
    PIXEL24 = 0x05         # SSS=5 (24 bits/pixel)
    SOURCE = 0x01

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4048,
        width: int = 0,
        height: int = 0,
        crop: List[int] = [],
        scale: str = "fill",
        interpolation: str = "smooth",
        gamma: float = 0.5,
    ) -> None:
        self._ip = socket.gethostbyname(host)
        self._port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self._sequenceNumber = 0

        WLEDStreamer.__init__(self, width, height, crop, scale, interpolation, gamma)

    def close(self):
        self._socket.close()

    def sendFrame(self, frame: np.ndarray) -> None:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = frame.flatten()

        for start in range(0, int(frame.size / 3), self.MAX_PIXELS_PER_DATAGRAM):
            data = frame[(start * 3) : (start + self.MAX_PIXELS_PER_DATAGRAM) * 3]

            push_bit = self.PUSH if (start + self.MAX_PIXELS_PER_DATAGRAM >= int(frame.size / 3)) else 0
            bytes_start = start * 3
            bytes_length = len(data)

            message = (
                struct.pack(
                    "!BBBBLH",
                    self.VER1 | push_bit,
                    self._sequenceNumber,
                    ((self.RGBTYPE << 3) & 0xff) | self.PIXEL24,
                    self.SOURCE,
                    bytes_start,
                    bytes_length,
                ) +
                data
                    .astype("int8")
                    .tobytes()
            )

            self._socket.sendto(message, (self._ip, self._port))

            self._sequenceNumber += 1
            if self._sequenceNumber > 15:
                self._sequenceNumber = 0

    def _loadInfo(self) -> None:
        response = requests.get("http://" + self._ip + "/json/info", timeout=5)
        self._wled_info = json.loads(response.text)
