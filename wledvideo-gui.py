#!/usr/bin/python3

from typing import Union, List, Dict, Any, Optional

import tkinter as tk

import argparse
import sys
import time
import toml

from src.videocapture import VideoCapture
from src.displaycapture import DisplayCapture
from src.wledstreamer import WLEDStreamer
from src.udpstreamer import UDPWLEDStreamer
from src.serialstreamer import SerialWLEDStreamer
from src.ui import UI
import src.constants as constants


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("WLED video")
        self.resizable(False, False)
        self._ui = UI(self)
        self._ui.createMenu()

        # variables for configuration

        source_config = dict(constants.CONFIG_DEFAULTS)
        self._source_type = tk.StringVar(
            self,
            "video"
            if not source_config["camera"]
            else "camera"
            if not source_config["display"]
            else "display",
            "source_type",
        )
        self._source_type.trace("w", self._ui.updateType)

        self._source = tk.StringVar(self, source_config["source"], "source")
        self._loop = tk.BooleanVar(self, source_config["loop"], "loop")
        self._camera_index = tk.IntVar(
            self,
            source_config["source"] if source_config["camera"] else 0,
            "camera_index",
        )
        self._camera_width = tk.IntVar(self, None, "camera_width")
        self._camera_height = tk.IntVar(self, None, "camera_height")

        self._streamer_labels = tk.Variable(self, (), "streamer_labels")

        # variables for selected streamer

        streamer_config = dict(constants.STREAMER_CONFIG_DEFAULTS)
        self._connection_type = tk.StringVar(
            self,
            "udp" if (streamer_config["host"] != "") else "serial",
            "connection_type",
        )
        self._connection_type.trace("w", self._ui.updateType)

        self._udp_host = tk.StringVar(self, streamer_config["host"], "udp_host")
        self._udp_port = tk.StringVar(self, streamer_config["port"], "udp_port")
        self._serial_port = tk.StringVar(self, streamer_config["serial"], "serial_port")
        self._serial_baudrate = tk.IntVar(
            self, streamer_config["baudrate"], "serial_baudrate"
        )

        self._matrix_width = tk.IntVar(self, streamer_config["width"], "size_width")
        self._matrix_height = tk.IntVar(self, streamer_config["height"], "size_height")
        self._matrix_width.trace("w", self._updateStreamerSetting)
        self._matrix_height.trace("w", self._updateStreamerSetting)

        self._crop_left = tk.IntVar(self, 0, "crop_left")
        self._crop_top = tk.IntVar(self, 0, "crop_top")
        self._crop_right = tk.IntVar(self, 0, "crop_right")
        self._crop_bottom = tk.IntVar(self, 0, "crop_bottom")
        self._crop_left.trace("w", self._updateStreamerSetting)
        self._crop_top.trace("w", self._updateStreamerSetting)
        self._crop_right.trace("w", self._updateStreamerSetting)
        self._crop_bottom.trace("w", self._updateStreamerSetting)

        self._scale_type = tk.StringVar(
            self, streamer_config["scale"].title(), "scale_type"
        )
        self._scale_type.trace("w", self._updateStreamerSetting)
        self._interpolation_type = tk.StringVar(
            self,
            streamer_config["interpolation"].title(),
            "interpolation_type",
        )
        self._interpolation_type.trace("w", self._updateStreamerSetting)

        self._gamma = tk.DoubleVar(self, streamer_config["gamma"], "gamma")
        self._gamma.trace("w", self._updateStreamerSetting)

        # forward declaration of UI elements for further manipulation

        self._streamer_selector = None

        # set up app logic

        self._streamer_data: List[Dict[str, Any]] = []
        self._streamers: List[WLEDStreamer] = []
        self._selected_streamer_index = -1

        self._ui.createWidgets()

        self._video_capture: Optional[Union[VideoCapture, DisplayCapture]] = None
        self._last_display_capture_time = time.time()

        self._addStreamer()

    def startVideo(self) -> None:
        match self._source_type.get():
            case "video":
                self._video_capture = VideoCapture(self._source.get(), self._loop.get())
            case "camera":
                self._video_capture = VideoCapture(self._camera_index.get())
            case "display":
                self._video_capture = DisplayCapture()

        self._ui.updateStartStop(playing=True)
        self._updateVideo()

    def stopVideo(self) -> None:
        if not self._video_capture:
            return

        self._video_capture.stop()
        self._video_capture = None

        self._ui.updateStartStop(playing=False)
        self._ui.clearCanvas()

    def _updateVideo(self) -> None:
        if not self._video_capture:
            return

        if (
            self._source_type.get() == "display"
            and time.time() - self._last_display_capture_time < 0.1
        ):
            self.after(1, self._updateVideo)
            return
        self._last_display_capture_time = time.time()

        frame = self._video_capture.read()
        if frame is None:
            self._stopVideo()

        self._ui.drawCanvasImage(frame)

        self.after(1, self._updateVideo)

    def _createStreamerFromConfig(self, streamer_config: Dict[str, Any]) -> Optional[WLEDStreamer]:
        streamer: Optional[WLEDStreamer] = None
        try:
            if streamer_config["serial"]:
                # streamer = SerialWLEDStreamer(**streamer_config)
                pass
            else:
                # streamer = UDPWLEDStreamer(**streamer_config)
                pass
        except Exception as e:
            print(e)
        
        return streamer

    def addStreamer(self) -> None:
        streamer_config = dict(constants.STREAMER_CONFIG_DEFAULTS)
        self._streamer_data.append(streamer_config)

        self._streamers.append(self._createStreamerFromConfig(streamer_config))
        self._ui.createStreamerLabels(self._streamer_data)

        # select newly created streamer
        self._streamer_selector.selection_clear(0, tk.END)
        self._streamer_selector.select_set(len(self._streamer_data) - 1)
        self._streamer_selector.event_generate("<<ListboxSelect>>")

    def removeStreamer(self) -> None:
        self._streamer_data.pop(self._selected_streamer_index)
        self._streamers.pop(self._selected_streamer_index)
        self._ui.createStreamerLabels(self._streamer_data)

        if self._selected_streamer_index >= len(self._streamer_data):
            self._streamer_selector.selection_clear(0, tk.END)
            self._streamer_selector.select_set(len(self._streamer_data) - 1)

        self._selected_streamer_index = -1
        self._streamer_selector.event_generate("<<ListboxSelect>>")

    def _updateStreamerSelection(self, event: tk.Event) -> None:
        selected_indices = self._streamer_selector.curselection()
        if not selected_indices:
            # if the user double-clicks on another widget, the listbox looses its selection
            self._streamer_selector.select_set(self._selected_streamer_index)
            return

        selected_index = int(self._streamer_selector.curselection()[0])

        if selected_index != self._selected_streamer_index:
            self._selected_streamer_index = selected_index
            streamer_data = self._streamer_data[selected_index]

            if streamer_data["serial"]:
                self._connection_type.set("serial")
            else:
                self._connection_type.set("udp")

            self._udp_host.set(streamer_data["host"])
            self._udp_port.set(streamer_data["port"])
            self._serial_port.set(streamer_data["serial"])
            self._serial_baudrate.set(streamer_data["baudrate"])
            self._matrix_width.set(streamer_data["width"])
            self._matrix_height.set(streamer_data["height"])

            crop_data = streamer_data["crop"]
            match len(crop_data):
                case 0:
                    self._crop_left.set(0)
                    self._crop_top.set(0)
                    self._crop_right.set(0)
                    self._crop_bottom.set(0)
                case 1:
                    self._crop_left.set(int(crop_data[0]))
                    self._crop_top.set(int(crop_data[0]))
                    self._crop_right.set(int(crop_data[0]))
                    self._crop_bottom.set(int(crop_data[0]))
                case 2:
                    self._crop_left.set(int(crop_data[0]))
                    self._crop_top.set(int(crop_data[1]))
                    self._crop_right.set(int(crop_data[0]))
                    self._crop_bottom.set(int(crop_data[1]))
                case 4:
                    self._crop_left.set(int(crop_data[0]))
                    self._crop_top.set(int(crop_data[1]))
                    self._crop_right.set(int(crop_data[2]))
                    self._crop_bottom.set(int(crop_data[3]))

            self._scale_type.set(streamer_data["scale"].title())
            self._interpolation_type.set(streamer_data["interpolation"].title())
            self._gamma.set(streamer_data["gamma"])

    def _updateStreamerSetting(self, var: str, index: int, mode: str) -> None:
        if self._selected_streamer_index < 0:
            return

        streamer_data = self._streamer_data[self._selected_streamer_index]
        streamer = self._streamers[self._selected_streamer_index]

        match var:
            case "size_width":
                try:
                    matrix_width = int(self._matrix_width.get())
                except (ValueError, tk.TclError):
                    return
                streamer_data["width"] = matrix_width

                if streamer:
                    streamer.setSize(streamer_data["width"], streamer_data["height"])

            case "size_height":
                try:
                    matrix_height = int(self._matrix_height.get())
                except (ValueError, tk.TclError):
                    return
                streamer_data["height"] = matrix_height

                if streamer:
                    streamer.setSize(streamer_data["width"], streamer_data["height"])

            case "scale_type":
                streamer_data["scale"] = self._scale_type.get().lower()
            
                if streamer:
                    streamer.setScale(streamer_data["scale"])

            case "interpolation_type":
                streamer_data["interpolation"] = self._interpolation_type.get().lower()
            
                if streamer:
                    streamer.setInterpolation(streamer_data["interpolation"])

            case "gamma":
                try:
                    gamma = float(self._gamma.get())
                except (ValueError, tk.TclError):
                    return
                streamer_data["gamma"] = gamma

                if streamer:
                    streamer.setGamma(gamma)

            case otherwise:
                print(var)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--config", default=constants.DEFAULT_CONFIG_FILE)
    args = parser.parse_known_args()

    try:
        config = toml.load(args[0].config)
    except FileNotFoundError:
        if args[0].config != constants.DEFAULT_CONFIG_FILE:
            print("Specified config not found")
            sys.exit(0)
        config:Dict[str, Any] = {}

    app = App()
    app.mainloop()
