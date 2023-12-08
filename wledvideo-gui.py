#!/usr/bin/python3

import tkinter as tk
from tkinter import ttk
from tkinter import Menu
from tkinter import filedialog

import toml
import argparse
import sys
import PIL.Image, PIL.ImageTk
import time

from typing import List

from src.videocapture import VideoCapture
from src.displaycapture import DisplayCapture
from src.udpstreamer import UDPWLEDStreamer
from src.serialstreamer import SerialWLEDStreamer
import src.constants as constants

from src.utils import logger_handler


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("WLED video")
        self.resizable(False, False)
        self.createMenu()

        # variables for configuration

        config = constants.CONFIG_DEFAULTS
        self._source_type = tk.StringVar(
            self,
            "video"
            if not config["camera"]
            else "camera"
            if not config["display"]
            else "display",
            "source_type",
        )
        self._source_type.trace("w", self._updateType)

        self._source = tk.StringVar(self, config["source"], "source")
        self._loop = tk.BooleanVar(self, config["loop"], "loop")
        self._camera_index = tk.IntVar(
            self,
            config["source"] if config["camera"] else 0,
            "camera_index",
        )
        self._camera_width = tk.IntVar(self, None, "camera_width")
        self._camera_height = tk.IntVar(self, None, "camera_height")

        # variables for selected streamers

        streamer_config = constants.STREAMER_CONFIG_DEFAULTS
        self._connection_type = tk.StringVar(
            self,
            "udp" if (streamer_config["host"] != "") else "serial",
            "connection_type",
        )
        self._connection_type.trace("w", self._updateType)

        self._udp_host = tk.StringVar(self, streamer_config["host"], "udp_host")
        self._udp_port = tk.StringVar(self, streamer_config["port"], "udp_port")
        self._serial_port = tk.StringVar(self, streamer_config["serial"], "serial_port")
        self._serial_baudrate = tk.IntVar(
            self, streamer_config["baudrate"], "serial_baudrate"
        )

        self._matrix_width = tk.IntVar(self, streamer_config["width"], "size_width")
        self._matrix_height = tk.IntVar(self, streamer_config["height"], "size_height")

        self._crop_left = tk.IntVar(self, 0, "crop_left")
        self._crop_top = tk.IntVar(self, 0, "crop_top")
        self._crop_right = tk.IntVar(self, 0, "crop_right")
        self._crop_bottom = tk.IntVar(self, 0, "crop_bottom")

        self._scale_type = tk.StringVar(
            self, streamer_config["scale"].title(), "scale_type"
        )
        self._interpolation_type = tk.StringVar(
            self,
            streamer_config["interpolation"].title(),
            "interpolation_type",
        )

        self._gamma = tk.DoubleVar(self, streamer_config["gamma"], "gamma")

        # forward declaration of UI elements for further manipulation

        self._source_video_container = None
        self._source_camera_container = None
        self._source_display_container = None

        self._connection_udp_container = None
        self._connection_serial_container = None

        self._start_button = None
        self._stop_button = None

        self._canvas = None
        self._frame_image = None

        self.createWidgets()

        self._updateType("source_type", "", "w")
        self._updateType("connection_type", "", "w")

        # set up app logic

        self._video_capture = None
        self._last_display_capture_time = time.time()

    def createMenu(self):
        menubar = Menu(self)
        self.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=False)
        file_menu.add_command(label="New", accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", accelerator="Ctrl+O")
        file_menu.add_command(label="Save", accelerator="Ctrl+S")
        file_menu.add_command(label="Save as...", accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

    def createWidgets(self):
        source_container = ttk.LabelFrame(self, text="Source")
        source_container.grid(column=0, row=0, rowspan=2, sticky=tk.N, padx=10, pady=10)

        source_type_container = ttk.Frame(source_container)
        source_type_container.grid(row=0, sticky=tk.W, padx=5, pady=5)

        ttk.Radiobutton(
            source_type_container,
            text="Video",
            value="video",
            variable=self._source_type,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            source_type_container,
            text="Camera",
            value="camera",
            variable=self._source_type,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            source_type_container,
            text="Display",
            value="display",
            variable=self._source_type,
        ).pack(side=tk.LEFT, padx=5)

        self._source_video_container = ttk.Frame(source_container)
        self._source_video_container.grid(row=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(self._source_video_container, text="File/URL").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Entry(self._source_video_container, textvariable=self._source).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(
            self._source_video_container, text="Browse...", command=self._browseVideo
        ).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(
            self._source_video_container, text="Loop", variable=self._loop
        ).pack(side=tk.LEFT, padx=5)

        self._source_camera_container = ttk.Frame(source_container)
        ttk.Label(self._source_camera_container, text="Camera index").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Spinbox(
            self._source_camera_container,
            width=5,
            values=tuple(range(10)),
            textvariable=self._camera_index,
        ).pack(side=tk.LEFT, padx=2)
        ttk.Label(self._source_camera_container, text="Width").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Entry(
            self._source_camera_container, width=5, textvariable=self._camera_width
        ).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Label(self._source_camera_container, text="Height").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Entry(
            self._source_camera_container, width=5, textvariable=self._camera_height
        ).pack(side=tk.LEFT, padx=2)

        self._source_display_container = ttk.Frame(source_container)

        self._canvas = tk.Canvas(source_container, width=480, height=270, bg="black")
        self._canvas.grid(row=3, sticky=tk.W, padx=5, pady=5)

        play_controls_container = tk.Frame(source_container)
        play_controls_container.grid(row=4, sticky=tk.E, padx=5, pady=5)

        self._start_button = ttk.Button(
            play_controls_container, text="Start", command=self._startVideo
        )
        self._stop_button = ttk.Button(
            play_controls_container, text="Stop", command=self._stopVideo
        )
        self._start_button.pack(side=tk.LEFT, padx=5, pady=5)

        streamers_container = ttk.LabelFrame(self, text="WLED instance(s)")
        streamers_container.grid(column=1, row=0, sticky=tk.EW, padx=10, pady=10)

        tk.Listbox(streamers_container, width=30, height=4).pack(
            side=tk.LEFT, expand=True, padx=5, pady=5
        )
        ttk.Button(streamers_container, text="Add").pack(side=tk.TOP, pady=5)
        ttk.Button(streamers_container, text="Remove").pack(side=tk.TOP)

        config_container = ttk.LabelFrame(self, text="Configuration")
        config_container.grid(column=1, row=1, padx=10, pady=10)

        ttk.Label(config_container, text="Connection").grid(
            column=0, row=0, sticky=tk.W, padx=5, pady=5
        )
        connection_container = ttk.Frame(config_container)
        connection_container.grid(column=1, row=0, sticky=tk.W, padx=5, pady=5)

        connection_type_container = ttk.Frame(connection_container)
        connection_type_container.grid(column=0, row=0, sticky=tk.W, pady=5)

        ttk.Radiobutton(
            connection_type_container,
            text="Network",
            value="udp",
            variable=self._connection_type,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            connection_type_container,
            text="Serial",
            value="serial",
            variable=self._connection_type,
        ).pack(side=tk.LEFT)

        self._connection_udp_container = ttk.Frame(connection_container)
        self._connection_udp_container.grid(column=0, row=1, sticky=tk.W, padx=5)

        ttk.Label(self._connection_udp_container, text="Host").grid(
            column=0, row=0, sticky=tk.W, pady=2
        )
        ttk.Entry(
            self._connection_udp_container, width=18, textvariable=self._udp_host
        ).grid(column=1, row=0, padx=2, pady=2)
        ttk.Label(self._connection_udp_container, text="Port").grid(
            column=0, row=1, sticky=tk.W, pady=2
        )
        ttk.Entry(
            self._connection_udp_container, width=6, textvariable=self._udp_port
        ).grid(column=1, row=1, sticky=tk.W, padx=2, pady=2)

        self._connection_serial_container = ttk.Frame(connection_container)
        self._connection_serial_container.grid(column=0, row=2, sticky=tk.W, padx=5)

        ttk.Label(self._connection_serial_container, text="Port").grid(
            column=0, row=0, sticky=tk.W, pady=2
        )
        ttk.Entry(
            self._connection_serial_container, width=15, textvariable=self._serial_port
        ).grid(column=1, row=0, padx=2, pady=2)
        ttk.Label(self._connection_serial_container, text="Baudrate").grid(
            column=0, row=1, sticky=tk.W, pady=2
        )
        ttk.Entry(
            self._connection_serial_container,
            width=8,
            textvariable=self._serial_baudrate,
        ).grid(column=1, row=1, sticky=tk.W, padx=2, pady=2)

        ttk.Label(config_container, text="Dimensions").grid(
            column=0, row=1, sticky=tk.W, padx=5, pady=5
        )
        size_container = ttk.Frame(config_container)
        size_container.grid(column=1, row=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(size_container, text="Width").pack(side=tk.LEFT, padx=2)
        ttk.Entry(size_container, width=5, textvariable=self._matrix_width).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Label(size_container, text="Height").pack(side=tk.LEFT, padx=2)
        ttk.Entry(size_container, width=5, textvariable=self._matrix_height).pack(
            side=tk.LEFT, padx=2
        )

        ttk.Label(config_container, text="Crop").grid(
            column=0, row=2, sticky=tk.W, padx=5, pady=5
        )
        crop_container = ttk.Frame(config_container)
        crop_container.grid(column=1, row=2, sticky=tk.W, padx=5, pady=5)
        ttk.Label(crop_container, text="Top").grid(
            column=0, row=0, columnspan=2, sticky=tk.W
        )
        ttk.Entry(crop_container, width=5, textvariable=self._crop_top).grid(
            column=2, row=0, columnspan=3, padx=2, pady=2
        )
        ttk.Label(crop_container, text="Left").grid(column=0, row=1)
        ttk.Entry(crop_container, width=5, textvariable=self._crop_left).grid(
            column=1, row=1, columnspan=2, padx=2, pady=2
        )
        ttk.Label(crop_container, text="Right").grid(column=6, row=1)
        ttk.Entry(crop_container, width=5, textvariable=self._crop_right).grid(
            column=4, row=1, columnspan=2, padx=2, pady=2
        )
        ttk.Label(crop_container, text="Bottom").grid(
            column=0, row=2, columnspan=2, sticky=tk.W
        )
        ttk.Entry(crop_container, width=5, textvariable=self._crop_bottom).grid(
            column=2, row=2, columnspan=3, padx=2, pady=2
        )

        ttk.Label(config_container, text="Scale").grid(
            column=0, row=3, sticky=tk.W, padx=5, pady=5
        )
        ttk.Combobox(
            config_container,
            state="readonly",
            values=["Stretch", "Fill", "Fit", "Crop"],
            textvariable=self._scale_type,
        ).grid(column=1, row=3, sticky=tk.W, padx=5)

        ttk.Label(config_container, text="Interpolation").grid(
            column=0, row=4, sticky=tk.W, padx=5, pady=5
        )
        ttk.Combobox(
            config_container,
            state="readonly",
            values=["Smooth", "Hard"],
            textvariable=self._interpolation_type,
        ).grid(column=1, row=4, sticky=tk.W, padx=5)

        ttk.Label(config_container, text="Gamma").grid(
            column=0, row=5, sticky=tk.W, padx=5, pady=5
        )
        ttk.Spinbox(
            config_container,
            width=5,
            values=tuple(i / 100 for i in range(1, 101)),
            textvariable=self._gamma,
        ).grid(column=1, sticky=tk.W, row=5, padx=5)

    def _updateType(self, var, index, mode):
        match var:
            case "source_type":
                match self._source_type.get():
                    case "video":
                        self._source_camera_container.grid_forget()
                        self._source_display_container.grid_forget()
                        self._source_video_container.grid(
                            row=1, sticky=tk.W, padx=5, pady=5
                        )
                    case "camera":
                        self._source_video_container.grid_forget()
                        self._source_display_container.grid_forget()
                        self._source_camera_container.grid(
                            row=2, sticky=tk.W, padx=5, pady=5
                        )
                    case "display":
                        self._source_video_container.grid_forget()
                        self._source_camera_container.grid_forget()
                        self._source_display_container.grid(
                            row=2, sticky=tk.W, padx=5, pady=5
                        )
            case "connection_type":
                if self._connection_type.get() == "udp":
                    self._connection_serial_container.grid_forget()
                    self._connection_udp_container.grid(
                        row=1, sticky=tk.W, padx=2, pady=5
                    )
                else:
                    self._connection_udp_container.grid_forget()
                    self._connection_serial_container.grid(
                        row=2, sticky=tk.W, padx=2, pady=5
                    )

    def _browseVideo(self):
        filename = filedialog.askopenfilename(
            filetypes=(
                ("Video", ("*.mp4", "*.mov", "*.avi", "*.mkv", "*.mpeg")),
                ("All Files", "*.*"),
            )
        )
        if filename:
            self._source.set(filename)

    def _startVideo(self):
        match self._source_type.get():
            case "video":
                self._video_capture = VideoCapture(self._source.get(), self._loop.get())
            case "camera":
                self._video_capture = VideoCapture(self._camera_index.get())
            case "display":
                self._video_capture = DisplayCapture()

        self._start_button.forget()
        self._stop_button.pack(side=tk.LEFT, padx=5, pady=5)

        self._updateVideo()

    def _stopVideo(self):
        if not self._video_capture:
            return

        self._video_capture.stop()
        self._video_capture = None

        self._stop_button.forget()
        self._start_button.pack(side=tk.LEFT, padx=5, pady=5)

        self._canvas.create_rectangle(
            0, 0, self._canvas.winfo_width(), self._canvas.winfo_height(), fill="black"
        )

    def _updateVideo(self):
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

        frame_image = PIL.Image.fromarray(frame[:, :, ::-1])
        frame_image = frame_image.resize(
            (self._canvas.winfo_width(), self._canvas.winfo_height())
        )
        self._frame_image = PIL.ImageTk.PhotoImage(image=frame_image)

        self._canvas.create_image(0, 0, image=self._frame_image, anchor=tk.NW)

        self.after(1, self._updateVideo)


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
        config = {}

    app = App()
    app.mainloop()
