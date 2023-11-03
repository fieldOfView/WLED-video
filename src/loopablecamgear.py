"""
===============================================
vidgear library source-code is deployed under the Apache 2.0 License:

Copyright (c) 2019 Abhishek Thakur(@abhiTronix) <abhi.una12@gmail.com>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
===============================================
"""

# import the necessary packages
import cv2
import time
import queue
import logging as log
from threading import Thread, Event

# import helper packages
from vidgear.gears.helper import (
    capPropId,
    logger_handler,
    check_CV_version,
    get_supported_resolution,
    check_gstreamer_support,
    import_dependency_safe,
    logcurr_vidgear_ver,
)

from vidgear.gears.camgear import (
    yt_dlp as yt_dlp,
    YT_backend as YT_backend
)

# define logger
logger = log.getLogger("LoopableCamGear")
logger.propagate = False
logger.addHandler(logger_handler())
logger.setLevel(log.DEBUG)


class LoopableCamGear:
    """
    CamGear supports a diverse range of video streams which can handle/control video stream almost any IP/USB Cameras, multimedia video file format (upto 4k tested),
    any network stream URL such as http(s), rtp, rtsp, rtmp, mms, etc. It also supports Gstreamer's RAW pipelines.

    CamGear API provides a flexible, high-level multi-threaded wrapper around OpenCV's VideoCapture API with direct access to almost all of its available parameters.
    It relies on Threaded Queue mode for threaded, error-free and synchronized frame handling.

    CamGear internally implements `yt_dlp` backend class for seamlessly pipelining live video-frames and metadata from various streaming services like YouTube, Dailymotion,
    Twitch, and [many more ➶](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md#supported-sites)
    """

    def __init__(
        self,
        source=0,
        stream_mode=False,
        backend=0,
        colorspace=None,
        logging=False,
        time_delay=0,
        loop=False,
        nosync=False,
        **options
    ):
        """
        This constructor method initializes the object state and attributes of the CamGear class.

        Parameters:
            source (based on input): defines the source for the input stream.
            stream_mode (bool): controls the exclusive **Stream Mode** for handling streaming URLs.
            backend (int): selects the backend for OpenCV's VideoCapture class.
            colorspace (str): selects the colorspace of the input stream.
            logging (bool): enables/disables logging.
            time_delay (int): time delay (in sec) before start reading the frames.
            options (dict): provides ability to alter Source Tweak Parameters.
        """
        # print current version
        logcurr_vidgear_ver(logging=logging)

        # enable logging if specified
        self.__logging = False
        if logging:
            self.__logging = logging
        # initialize global
        self.ytv_metadata = {}

        self.__loop = loop

        # check if Stream-Mode is ON (True)
        if stream_mode:
            # check GStreamer backend support
            gst_support = check_gstreamer_support(logging=logging)
            # handle special Stream Mode parameters
            stream_resolution = get_supported_resolution(
                options.pop("STREAM_RESOLUTION", "best"), logging=logging
            )
            # handle Stream-Mode
            if not (yt_dlp is None):
                # extract user-defined params
                yt_stream_params = options.pop("STREAM_PARAMS", {})
                if isinstance(yt_stream_params, dict):
                    yt_stream_params = {
                        str(k).strip(): v for k, v in yt_stream_params.items()
                    }
                else:
                    yt_stream_params = {}
                try:
                    # Validate source for Yt_dlp backend
                    logger.info(
                        "Verifying Streaming URL using yt-dlp backend. Please wait..."
                    )
                    # initialize YT_backend
                    ytbackend = YT_backend(
                        source_url=source, logging=logging, **yt_stream_params
                    )
                    if ytbackend:
                        # save video metadata
                        self.ytv_metadata = ytbackend.meta_data
                        # handle live-streams
                        if ytbackend.is_livestream:
                            # Throw warning for livestreams
                            logger.warning(
                                "Livestream URL detected. It is advised to use GStreamer backend(`cv2.CAP_GSTREAMER`) with it."
                            )
                        # check whether stream-resolution was specified and available
                        if not (stream_resolution in ytbackend.streams.keys()):
                            logger.warning(
                                "Specified stream-resolution `{}` is not available. Reverting to `best`!".format(
                                    stream_resolution
                                )
                            )
                            # revert to best
                            stream_resolution = "best"
                        else:
                            if self.__logging:
                                logger.debug(
                                    "Using `{}` resolution for streaming.".format(
                                        stream_resolution
                                    )
                                )
                        # extract stream URL as source using stream-resolution
                        source = ytbackend.streams[stream_resolution]
                        # log progress
                        self.__logging and logger.debug(
                            "YouTube source ID: `{}`, Title: `{}`, Quality: `{}`".format(
                                self.ytv_metadata["id"],
                                self.ytv_metadata["title"],
                                stream_resolution,
                            )
                        )
                except Exception as e:
                    # raise error if something went wrong
                    raise ValueError(
                        "[CamGear:ERROR] :: Stream Mode is enabled but Input URL is invalid!"
                    )
            else:
                # raise import errors
                import_dependency_safe("yt_dlp")

        # youtube mode variable initialization
        self.__youtube_mode = stream_mode

        # assigns special parameter to global variable and clear
        # Threaded Queue Mode
        self.__threaded_queue_mode = options.pop("THREADED_QUEUE_MODE", True)
        if not isinstance(self.__threaded_queue_mode, bool):
            # reset improper values
            self.__threaded_queue_mode = True
        # Thread Timeout
        self.__thread_timeout = options.pop("THREAD_TIMEOUT", None)
        if self.__thread_timeout and isinstance(self.__thread_timeout, (int, float)):
            # set values
            self.__thread_timeout = float(self.__thread_timeout)
        else:
            # defaults to 5mins timeout
            self.__thread_timeout = None

        self.__queue = None
        # initialize queue for video files only
        if self.__threaded_queue_mode and isinstance(source, str):
            # define queue and assign it to global var
            self.__queue = queue.Queue(maxsize=96)  # max bufferlen 96 to check overflow
            # log it
            self.__logging and logger.debug(
                "Enabling Threaded Queue Mode for the current video source!"
            )
        else:
            # otherwise disable it
            self.__threaded_queue_mode = False
            # log it
            self.__logging and logger.warning(
                "Threaded Queue Mode is disabled for the current video source!"
            )

        if self.__thread_timeout:
            logger.debug(
                "Setting Video-Thread Timeout to {}s.".format(self.__thread_timeout)
            )

        # stream variable initialization
        self.stream = None

        if backend and isinstance(backend, int):
            # add backend if specified and initialize the camera stream
            if check_CV_version() == 3:
                # Different OpenCV 3.4.x statement
                self.stream = cv2.VideoCapture(source + backend)
            else:
                # Two parameters are available since OpenCV 4+ (master branch)
                self.stream = cv2.VideoCapture(source, backend)
            logger.debug("Setting backend `{}` for this source.".format(backend))
        else:
            # initialize the camera stream
            self.stream = cv2.VideoCapture(source)

        # initializing colorspace variable
        self.color_space = None

        # apply attributes to source if specified
        options = {str(k).strip(): v for k, v in options.items()}
        for key, value in options.items():
            property = capPropId(key)
            if not (property is None):
                self.stream.set(property, value)

        # handle colorspace value
        if not (colorspace is None):
            self.color_space = capPropId(colorspace.strip())
            if self.__logging and not (self.color_space is None):
                logger.debug(
                    "Enabling `{}` colorspace for this video stream!".format(
                        colorspace.strip()
                    )
                )

        # initialize and assign frame-rate variable
        self.framerate = 0.0
        self.__period = 0
        _fps = self.stream.get(cv2.CAP_PROP_FPS)
        if _fps > 1.0:
            self.framerate = _fps
            if not nosync:
                self.__period = 1/_fps

        # applying time delay to warm-up webcam only if specified
        if time_delay and isinstance(time_delay, (int, float)):
            time.sleep(time_delay)

        # frame variable initialization
        (grabbed, self.frame) = self.stream.read()

        # check if valid stream
        if grabbed:
            # render colorspace if defined
            if not (self.color_space is None):
                self.frame = cv2.cvtColor(self.frame, self.color_space)

            if self.__threaded_queue_mode:
                # initialize and append to queue
                self.__queue.put(self.frame)
        else:
            raise RuntimeError(
                "[CamGear:ERROR] :: Source is invalid, CamGear failed to initialize stream on this source!"
            )

        # thread initialization
        self.__thread = None

        # initialize termination flag event
        self.__terminate = Event()

        # initialize stream read flag event
        self.__stream_read = Event()

    def start(self):
        """
        Launches the internal *Threaded Frames Extractor* daemon.

        **Returns:** A reference to the CamGear class object.
        """

        self.__thread = Thread(target=self.__update, name="CamGear", args=())
        self.__thread.daemon = True
        self.__thread.start()
        return self

    def __update(self):
        """
        A **Threaded Frames Extractor**, that keep iterating frames from OpenCV's VideoCapture API to a internal monitored queue,
        until the thread is terminated, or frames runs out.
        """

        # keep iterating infinitely
        # until the thread is terminated
        # or frames runs out
        # if the thread indicator variable is set, stop the thread
        while not self.__terminate.wait(self.__period):
            # stream not read yet
            self.__stream_read.clear()

            # otherwise, read the next frame from the stream
            (grabbed, frame) = self.stream.read()

            # stream read completed
            self.__stream_read.set()

            # check for valid frame if received
            if not grabbed:
                # no frames received, then safely exit
                if self.__threaded_queue_mode:
                    if self.__queue.empty():
                        if self.__loop:
                            self.stream.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            continue
                        else:
                            break
                    else:
                        continue
                else:
                    if self.__loop:
                        self.stream.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        break

            # apply colorspace to frames if valid
            if not (self.color_space is None):
                color_frame = None
                try:
                    if isinstance(self.color_space, int):
                        color_frame = cv2.cvtColor(frame, self.color_space)
                    else:
                        raise ValueError(
                            "Global color_space parameter value `{}` is not a valid!".format(
                                self.color_space
                            )
                        )
                except Exception as e:
                    # Catch if any error occurred
                    self.color_space = None
                    if self.__logging:
                        logger.exception(str(e))
                        logger.warning("Input colorspace is not a valid colorspace!")
                if not (color_frame is None):
                    self.frame = color_frame
                else:
                    self.frame = frame
            else:
                self.frame = frame

            # append to queue
            if self.__threaded_queue_mode:
                self.__queue.put(self.frame)

        # signal queue we're done
        self.__threaded_queue_mode and self.__queue.put(None)
        self.__threaded_queue_mode = False

        # indicate immediate termination
        self.__terminate.set()
        self.__stream_read.set()

        # release resources
        self.stream.release()

    def read(self):
        """
        Extracts frames synchronously from monitored queue, while maintaining a fixed-length frame buffer in the memory,
        and blocks the thread if the queue is full.

        **Returns:** A n-dimensional numpy array.
        """
        while self.__threaded_queue_mode and not self.__terminate.is_set():
            return self.__queue.get(timeout=self.__thread_timeout)
        # return current frame
        # only after stream is read
        return (
            self.frame
            if not self.__terminate.is_set()  # check if already terminated
            and self.__stream_read.wait(timeout=self.__thread_timeout)  # wait for it
            else None
        )

    def stop(self):
        """
        Safely terminates the thread, and release the VideoStream resources.
        """
        self.__logging and logger.debug("Terminating processes.")
        # terminate Threaded queue mode separately
        self.__threaded_queue_mode = False

        # indicate that the thread
        # should be terminated immediately
        self.__stream_read.set()
        self.__terminate.set()

        # wait until stream resources are released (producer thread might be still grabbing frame)
        if self.__thread is not None:
            if not (self.__queue is None):
                while not self.__queue.empty():
                    try:
                        self.__queue.get_nowait()
                    except queue.Empty:
                        continue
                    self.__queue.task_done()
            self.__thread.join()
