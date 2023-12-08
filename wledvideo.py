#!/usr/bin/python3

import sys
import argparse
import toml
import logging
import cv2

import src.displaycapture as displaycapture
import src.loopablecamgear as loopablecamgear
import src.udpstreamer as udpstreamer
import src.serialstreamer as serialstreamer

from src.utils import logger_handler

from typing import Union, List


class VideoCapture(loopablecamgear.LoopableCamGear):
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


if __name__ == "__main__":
    DEFAULT_CONFIG_FILE = "config.toml"
    CONFIG_DEFAULTS = {
        "source": "" if "--camera" not in sys.argv else 0,
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
        stream_config = config["wled"]
    except KeyError:
        stream_config = {}
    if isinstance(stream_config, List):
        stream_config = stream_config[0]
    if "wled" not in config:
        config["wled"] = [stream_config]

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
    parser.add_argument("--serial", default=getStreamerDefault("serial"))
    parser.add_argument(
        "--baudrate",
        type=int,
        default=getStreamerDefault("baudrate"),
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

    if "--display" not in sys.argv:
        parser.add_argument(
            "source",
            nargs="?" if "source" in config or "--camera" in sys.argv else 1,
            type=int if "--camera" in sys.argv else str,
            default=getDefault("source"),
            help="The video file to stream (required unless a source is specified in the config file). If --camera is set, 'source' shall be the index of the camera source (defaulting to 0)",
        )
    parser.add_argument(
        "--loop",
        action="store_true",
        default=getDefault("loop"),
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--camera",
        action="store_true",
        default=getDefault("camera"),
        help="use a webcam instead of a video",
    )
    source_group.add_argument(
        "--display",
        action="store_true",
        default=getDefault("display"),
        help="grab the desktop instead of a video",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=getDefault("debug"),
        help="show the output in a window while streaming",
    )

    args = parser.parse_args()

    if not args.display and args.source:
        if isinstance(args.source, list):
            source = args.source[0]
        else:
            source = args.source
    else:
        if args.camera or args.display:
            source = 0

    config["wled"][0] = {
        "width": args.width,
        "height": args.height,
        "crop": args.crop,
        "scale": args.scale,
        "interpolation": args.interpolation,
        "gamma": args.gamma,
    }

    if args.serial == "" and "serial" not in config["wled"][0]:
        config["wled"][0].update(
            {
                "host": args.host,
                "port": args.port,
            }
        )
    else:
        config["wled"][0].update(
            {
                "serialport": args.serial,
                "baudrate": args.baudrate,
            }
        )

    wled_streamers = []

    for stream_config in config["wled"]:
        if "serialport" in stream_config:
            streamer = serialstreamer.SerialWLEDStreamer(**stream_config)
        else:
            streamer = udpstreamer.UDPWLEDStreamer(**stream_config)
        wled_streamers.append(streamer)

    if not args.display:
        player = VideoCapture(source=source, loop=args.loop)
    else:
        player = displaycapture.DisplayCapture()

    while True:
        try:
            frame = player.read()
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

    if not args.display:
        player.stop()

    cv2.destroyAllWindows()
    for wled_streamer in wled_streamers:
        wled_streamer.close()
