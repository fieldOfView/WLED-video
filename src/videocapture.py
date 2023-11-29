from .loopablecamgear import LoopableCamGear

from .utils import logger_handler
import logging

from typing import Union

class VideoCapture(LoopableCamGear):
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
            super().__init__(
                source=source,
                stream_mode=stream_mode,
                logging=True,
                loop=loop,
                **options
            )
        except ValueError:
            self.logger.info("Source is not an URL that yt_dlp can handle.")
            super().__init__(
                source=source,
                logging=True,
                loop=loop,
            )
        self.start()