import tkinter as tk
from tkinter import ttk
from tkinter import Menu
from tkinter import filedialog
from PIL import Image, ImageTk


class UI:
    def __init__(self, app):
        self._app = app

        self._source_video_container = None
        self._source_camera_container = None
        self._source_display_container = None

        self._connection_udp_container = None
        self._connection_serial_container = None

        self._start_button = None
        self._stop_button = None

        self._remove_streamer_button = None

        self._canvas = None
        self._frame_image = None

    def createMenu(self):
        menubar = Menu(self._app)
        self._app.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=False)
        file_menu.add_command(label="New", accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", accelerator="Ctrl+O")
        file_menu.add_command(label="Save", accelerator="Ctrl+S")
        file_menu.add_command(label="Save as...", accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._app.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

    def createWidgets(self):
        source_container = ttk.LabelFrame(self._app, text="Source")
        source_container.grid(column=0, row=0, rowspan=2, sticky=tk.N, padx=10, pady=10)

        source_type_container = ttk.Frame(source_container)
        source_type_container.grid(row=0, sticky=tk.W, padx=5, pady=5)

        ttk.Radiobutton(
            source_type_container,
            text="Video",
            value="video",
            variable="source_type",
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            source_type_container,
            text="Camera",
            value="camera",
            variable="source_type",
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            source_type_container,
            text="Display",
            value="display",
            variable="source_type",
        ).pack(side=tk.LEFT, padx=5)

        self._source_video_container = ttk.Frame(source_container)
        self._source_video_container.grid(row=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(self._source_video_container, text="File/URL").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Entry(self._source_video_container, textvariable="source").pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        ttk.Button(
            self._source_video_container,
            text="Browse...",
            command=self._browseVideo,
        ).pack(side=tk.LEFT, padx=2)

        ttk.Checkbutton(
            self._source_video_container, text="Loop", variable="loop"
        ).pack(side=tk.LEFT, padx=5)

        self._source_camera_container = ttk.Frame(source_container)
        ttk.Label(self._source_camera_container, text="Camera index").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Spinbox(
            self._source_camera_container,
            width=5,
            values=tuple(range(10)),
            textvariable="camera_index",
        ).pack(side=tk.LEFT, padx=2)
        ttk.Label(self._source_camera_container, text="Width").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Entry(
            self._source_camera_container, width=5, textvariable="camera_width"
        ).pack(side=tk.LEFT, padx=2, pady=2)
        ttk.Label(self._source_camera_container, text="Height").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Entry(
            self._source_camera_container, width=5, textvariable="camera_height"
        ).pack(side=tk.LEFT, padx=2)

        self._source_display_container = ttk.Frame(source_container)

        self._canvas = tk.Canvas(
            source_container, width=480, height=270, bg="black"
        )
        self._canvas.grid(row=3, sticky=tk.W, padx=5, pady=5)

        play_controls_container = tk.Frame(source_container)
        play_controls_container.grid(row=4, sticky=tk.E, padx=5, pady=5)

        self._start_button = ttk.Button(
            play_controls_container, text="Start", command=self._app.startVideo
        )
        self._stop_button = ttk.Button(
            play_controls_container, text="Stop", command=self._app.stopVideo
        )
        self._start_button.pack(side=tk.LEFT, padx=5, pady=5)

        streamers_container = ttk.LabelFrame(self._app, text="WLED instance(s)")
        streamers_container.grid(column=1, row=0, sticky=tk.EW, padx=10, pady=10)

        self._app._streamer_selector = tk.Listbox(
            streamers_container,
            width=30,
            height=4,
            listvariable="streamer_labels",
        )
        self._app._streamer_selector.bind(
            "<<ListboxSelect>>", self._app._updateStreamerSelection
        )
        self._app._streamer_selector.pack(side=tk.LEFT, expand=True, padx=5, pady=5)
        ttk.Button(streamers_container, text="Add", command=self._app._addStreamer).pack(
            side=tk.TOP, pady=5
        )
        self._remove_streamer_button = ttk.Button(
            streamers_container, text="Remove", command=self._app._removeStreamer
        )
        self._remove_streamer_button.pack(side=tk.TOP)

        config_container = ttk.LabelFrame(self._app, text="Configuration")
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
            variable="connection_type",
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            connection_type_container,
            text="Serial",
            value="serial",
            variable="connection_type",
        ).pack(side=tk.LEFT)

        self._connection_udp_container = ttk.Frame(connection_container)
        self._connection_udp_container.grid(column=0, row=1, sticky=tk.W, padx=5)

        ttk.Label(self._connection_udp_container, text="Host").grid(
            column=0, row=0, sticky=tk.W, pady=2
        )
        ttk.Entry(
            self._connection_udp_container, width=18, textvariable="udp_host"
        ).grid(column=1, row=0, padx=2, pady=2)
        ttk.Label(self._connection_udp_container, text="Port").grid(
            column=0, row=1, sticky=tk.W, pady=2
        )
        ttk.Entry(
            self._connection_udp_container, width=6, textvariable="udp_port"
        ).grid(column=1, row=1, sticky=tk.W, padx=2, pady=2)

        self._connection_serial_container = ttk.Frame(connection_container)
        self._connection_serial_container.grid(column=0, row=2, sticky=tk.W, padx=5)

        ttk.Label(self._connection_serial_container, text="Port").grid(
            column=0, row=0, sticky=tk.W, pady=2
        )
        ttk.Entry(
            self._connection_serial_container,
            width=15,
            textvariable="serial_port",
        ).grid(column=1, row=0, padx=2, pady=2)
        ttk.Label(self._connection_serial_container, text="Baudrate").grid(
            column=0, row=1, sticky=tk.W, pady=2
        )
        ttk.Entry(
            self._connection_serial_container,
            width=8,
            textvariable="serial_baudrate",
        ).grid(column=1, row=1, sticky=tk.W, padx=2, pady=2)

        ttk.Label(config_container, text="Dimensions").grid(
            column=0, row=1, sticky=tk.W, padx=5, pady=5
        )
        size_container = ttk.Frame(config_container)
        size_container.grid(column=1, row=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(size_container, text="Width").pack(side=tk.LEFT, padx=2)
        ttk.Entry(size_container, width=5, textvariable="size_width").pack(
            side=tk.LEFT, padx=2
        )
        ttk.Label(size_container, text="Height").pack(side=tk.LEFT, padx=2)
        ttk.Entry(size_container, width=5, textvariable="size_height").pack(
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
        ttk.Entry(crop_container, width=5, textvariable="crop_top").grid(
            column=2, row=0, columnspan=3, padx=2, pady=2
        )
        ttk.Label(crop_container, text="Left").grid(column=0, row=1)
        ttk.Entry(crop_container, width=5, textvariable="crop_left").grid(
            column=1, row=1, columnspan=2, padx=2, pady=2
        )
        ttk.Label(crop_container, text="Right").grid(column=6, row=1)
        ttk.Entry(crop_container, width=5, textvariable="crop_right").grid(
            column=4, row=1, columnspan=2, padx=2, pady=2
        )
        ttk.Label(crop_container, text="Bottom").grid(
            column=0, row=2, columnspan=2, sticky=tk.W
        )
        ttk.Entry(crop_container, width=5, textvariable="crop_bottom").grid(
            column=2, row=2, columnspan=3, padx=2, pady=2
        )

        ttk.Label(config_container, text="Scale").grid(
            column=0, row=3, sticky=tk.W, padx=5, pady=5
        )
        ttk.OptionMenu(
            config_container,
            self._app._scale_type,
            "Fill",
            *["Stretch", "Fill", "Fit", "Crop"],
        ).grid(column=1, row=3, sticky=tk.EW, padx=5)

        ttk.Label(config_container, text="Interpolation").grid(
            column=0, row=4, sticky=tk.W, padx=5, pady=5
        )
        ttk.OptionMenu(
            config_container,
            self._app._interpolation_type,
            "Smooth",
            *["Smooth", "Hard"],
        ).grid(column=1, row=4, sticky=tk.EW, padx=5)

        ttk.Label(config_container, text="Gamma").grid(
            column=0, row=5, sticky=tk.W, padx=5, pady=5
        )
        ttk.Spinbox(
            config_container,
            width=5,
            values=tuple(i / 100 for i in range(1, 101)),
            textvariable="gamma",
        ).grid(column=1, sticky=tk.W, row=5, padx=5)

    def drawCanvasImage(self, frame):
        # convert BGR opencv image to RGB PIL image
        frame_image = Image.fromarray(frame[:, :, ::-1])

        frame_image = frame_image.resize(
            (self._canvas.winfo_width(), self._canvas.winfo_height())
        )
        self._frame_image = ImageTk.PhotoImage(image=frame_image)

        self._canvas.create_image(0, 0, image=self._frame_image, anchor=tk.NW)

    def clearCanvas(self):
        self._canvas.create_rectangle(
            0, 0, self._canvas.winfo_width(), self._canvas.winfo_height(), fill="black"
        )

    def createStreamerLabels(self, streamer_data):
        streamer_labels = []
        for streamer_config in streamer_data:
            if streamer_config["serial"]:
                label = f"{streamer_config['serial']}"
            else:
                label = f"{streamer_config['host']}:{streamer_config['port']}"
            streamer_labels.append(label)
        self._app.setvar("streamer_labels", tuple(streamer_labels))

        self._remove_streamer_button["state"] = (
            tk.NORMAL if len(streamer_labels) > 1 else tk.DISABLED
        )

    def updateType(self, var, index, mode):
        match var:
            case "source_type":
                match self._app.getvar("source_type"):
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
                if self._app.getvar("connection_type") == "udp":
                    self._connection_serial_container.grid_forget()
                    self._connection_udp_container.grid(
                        row=1, sticky=tk.W, padx=2, pady=5
                    )
                else:
                    self._connection_udp_container.grid_forget()
                    self._connection_serial_container.grid(
                        row=2, sticky=tk.W, padx=2, pady=5
                    )

    def updateStartStop(self, playing: bool):
        if playing:
            self._start_button.forget()
            self._stop_button.pack(side=tk.LEFT, padx=5, pady=5)
        else:
            self._stop_button.forget()
            self._start_button.pack(side=tk.LEFT, padx=5, pady=5)

    def _browseVideo(self):
        filename = filedialog.askopenfilename(
            filetypes=(
                ("Video", ("*.mp4", "*.mov", "*.avi", "*.mkv", "*.mpeg")),
                ("All Files", "*.*"),
            )
        )
        if filename:
            self._app.setvar("source", filename)
