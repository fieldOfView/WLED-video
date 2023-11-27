#!/usr/bin/python3

import tkinter as tk
from tkinter import ttk
from tkinter import Menu
import toml
import argparse
import sys


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("WLED video")
        self.resizable(False, False)

        self.create_menu()
        self.create_widgets()

    def create_menu(self):
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

    def create_widgets(self):
        source_container = ttk.LabelFrame(self, text="Source")
        source_container.grid(
            column=0, row=0, rowspan=2, sticky="N", padx=10, pady=10, ipady=5
        )

        source_type_container = ttk.Frame(source_container)
        source_type_container.grid(row=0, sticky="W", padx=5, pady=5)

        ttk.Radiobutton(source_type_container, text="Video", value="video").pack(
            side=tk.LEFT, padx=5
        )
        ttk.Radiobutton(source_type_container, text="Camera", value="camera").pack(
            side=tk.LEFT, padx=5
        )

        source_video_container = ttk.Frame(source_container)
        source_video_container.grid(row=1, sticky="W", padx=5, pady=5)
        ttk.Entry(source_video_container).pack(side=tk.LEFT, fill="x", expand=True)
        ttk.Button(source_video_container, text="Browse...").pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(source_container, text="Loop").grid(
            row=2, sticky="W", padx=5, pady=5
        )

        ttk.Spinbox(source_container, width=5, values=tuple(range(10))).grid(
            row=3, sticky="W", padx=5, pady=5
        )

        tk.Canvas(source_container, width=320, height=180, bg="black").grid(
            row=4, sticky="W", padx=5, pady=5
        )
        ttk.Button(source_container, text="Start").grid(
            row=5, sticky="E", padx=5, pady=5
        )

        streamers_container = ttk.LabelFrame(self, text="WLED instance(s)")
        streamers_container.grid(
            column=1, row=0, sticky="EW", padx=10, pady=10, ipadx=5
        )

        tk.Listbox(streamers_container, width=30, height=4).pack(side=tk.LEFT, expand=True, padx=5, pady=5)
        ttk.Button(streamers_container, text="Add").pack(side=tk.TOP, pady=5)
        ttk.Button(streamers_container, text="Remove").pack(side=tk.TOP, pady=5)

        config_container = ttk.LabelFrame(self, text="Configuration")
        config_container.grid(column=1, row=1, padx=10, pady=10)

        ttk.Label(config_container, text="Connection").grid(
            column=0, row=0, sticky="W", padx=5, pady=5
        )
        connection_container = ttk.Frame(config_container)
        connection_container.grid(column=1, row=0, sticky="W", padx=5, pady=5)

        connection_type_container = ttk.Frame(connection_container)
        connection_type_container.grid(column=0, row=0, sticky="W", padx=5, pady=5)

        ttk.Radiobutton(connection_type_container, text="Network", value="udp").pack(
            side=tk.LEFT, padx=5
        )
        ttk.Radiobutton(connection_type_container, text="Serial", value="serial").pack(
            side=tk.LEFT, padx=5
        )
        connection_udp_container = ttk.Frame(connection_container)
        connection_udp_container.grid(column=0, row=1, sticky="W", padx=5)

        ttk.Label(connection_udp_container, text="Host").grid(
            column=0, row=0, padx=2, pady=2
        )
        ttk.Entry(connection_udp_container).grid(column=1, row=0, padx=2, pady=2)
        ttk.Label(connection_udp_container, text="Port").grid(
            column=0, row=1, padx=2, pady=2
        )
        ttk.Entry(connection_udp_container, width=6).grid(
            column=1, row=1, sticky="W", padx=2, pady=2
        )

        connection_serial_container = ttk.Frame(connection_container)
        connection_serial_container.grid(column=0, row=2, sticky="W", padx=5)

        ttk.Label(connection_serial_container, text="Port").grid(
            column=0, row=0, sticky="W", padx=2, pady=2
        )
        ttk.Entry(connection_serial_container).grid(column=1, row=0, padx=2, pady=2)
        ttk.Label(connection_serial_container, text="Baudrate").grid(
            column=0, row=1, padx=2, pady=2
        )
        ttk.Entry(connection_serial_container, width=8).grid(
            column=1, row=1, sticky="W", padx=2, pady=2
        )

        ttk.Label(config_container, text="Dimensions").grid(
            column=0, row=1, sticky="W", padx=5, pady=5
        )
        size_container = ttk.Frame(config_container)
        size_container.grid(column=1, row=1, sticky="W", padx=5, pady=5)
        ttk.Label(size_container, text="Width").pack(side=tk.LEFT, padx=2)
        ttk.Entry(size_container, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(size_container, text="Height").pack(side=tk.LEFT, padx=2)
        ttk.Entry(size_container, width=5).pack(side=tk.LEFT, padx=2)

        ttk.Label(config_container, text="Crop").grid(
            column=0, row=2, sticky="W", padx=5, pady=5
        )
        crop_container = ttk.Frame(config_container)
        crop_container.grid(column=1, row=2, sticky="W", padx=5, pady=5)
        ttk.Label(crop_container, text="Top").grid(
            column=0, row=0, columnspan=2, sticky="W"
        )
        ttk.Entry(crop_container, width=5).grid(
            column=2, row=0, columnspan=3, padx=2, pady=2
        )
        ttk.Label(crop_container, text="Left").grid(column=0, row=1)
        ttk.Entry(crop_container, width=5).grid(
            column=1, row=1, columnspan=2, padx=2, pady=2
        )
        ttk.Label(crop_container, text="Right").grid(column=6, row=1)
        ttk.Entry(crop_container, width=5).grid(
            column=4, row=1, columnspan=2, padx=2, pady=2
        )
        ttk.Label(crop_container, text="Bottom").grid(
            column=0, row=2, columnspan=2, sticky="W"
        )
        ttk.Entry(crop_container, width=5).grid(
            column=2, row=2, columnspan=3, padx=2, pady=2
        )

        ttk.Label(config_container, text="Scale").grid(
            column=0, row=3, sticky="W", padx=5, pady=5
        )
        ttk.Combobox(
            config_container,
            state="readonly",
            values=["Stretch", "Fill", "Fit", "Crop"],
        ).grid(column=1, row=3, sticky="W", padx=5)

        ttk.Label(config_container, text="Interpolation").grid(
            column=0, row=4, sticky="W", padx=5, pady=5
        )
        ttk.Combobox(
            config_container, state="readonly", values=["Smooth", "Hard"]
        ).grid(column=1, row=4, sticky="W", padx=5)

        ttk.Label(config_container, text="Gamma").grid(
            column=0, row=5, sticky="W", padx=5, pady=5
        )
        ttk.Spinbox(
            config_container, width=3, values=tuple(i / 10 for i in range(1, 11))
        ).grid(column=1, sticky="W", row=5, padx=5)


if __name__ == "__main__":
    DEFAULT_CONFIG_FILE = "config.toml"
    CONFIG_DEFAULTS = {
        "source": "" if "--camera" not in sys.argv else 0,
        "loop": False,
        "camera": False,
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
    args = parser.parse_known_args()

    try:
        config = toml.load(args[0].config)
    except FileNotFoundError:
        if args[0].config != DEFAULT_CONFIG_FILE:
            print("Specified config not found")
            sys.exit(0)
        config = {}

    app = App()
    app.mainloop()
