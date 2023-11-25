# WLED-video
A tool to stream video to WLED matrix displays

Video can be streamed from local files, from a local webcam, or directly from a website [compatible with yt-dlp](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) such as youtube, vimeo, etc.

WLED-video uses the [WARLS protocol over UDP](https://kno.wled.ge/interfaces/udp-realtime/) or the [tpm2 protocol over a serial connection](https://kno.wled.ge/interfaces/serial/) to the ESP running WLED. For the time being, the UDP connection seems to be much more stable and performant.

Sound is currently not handled.

The simplest invocation of the WLED-video commandline is as follows:

```
wledvideo --host 4.3.2.1 https://www.youtube.com/watch?v=yPYZpwSpKmA
```

To decrease the time-to-first-frame, you can use a local video and supply the width and height of your WLED matrix:

```
wledvideo --host 4.3.2.1 --width 32 --height 16 togetherforever.mp4
```

More options are available via `wledvideo --help`:

```
usage: wledvideo.py [-h] [--config CONFIG] [--host HOST] [--port PORT] [--serial SERIAL] [--baudrate BAUDRATE] [--width WIDTH] [--height HEIGHT] [--crop CROP] [--scale {stretch,fill,fit,crop}]
                    [--interpolation {hard,smooth}] [--gamma GAMMA] [--loop] [--camera] [--debug]
                    source

positional arguments:
  source                The video file to stream (required unless a source is specified in the config file). If --camera is set, 'source' shall be the index of the camera source (defaulting to 0)

options:
  -h, --help            show this help message and exit
  --config CONFIG
  --host HOST
  --port PORT
  --serial SERIAL
  --baudrate BAUDRATE
  --width WIDTH         width of the LED matrix. If not specified, this will be automatically retreived from the WLED instance
  --height HEIGHT       height of the LED matrix. If not specified, this will be automatically retreived from the WLED instance
  --crop CROP           pixels to crop from the image. Can be either 1, 2 or 4 integer values to crop from respectively cropping all sides by the same amount, different amount horizontally and
                        vertically, or all sides individually
  --scale {stretch,fill,fit,crop}
                        'stretch' stretches the video to the panel, disregarding aspect ratio, 'fill' scales the video so the whole panel is covered (default), 'fit' scales the whole video onto the
                        panel adding black bars, 'crop' shows only the center of the video at 100%
  --interpolation {hard,smooth}
                        'smooth' uses pixel area relation when scaling the video (default), 'hard' uses nearest neighbour algorithm leading to crisper edges
  --gamma GAMMA         adjust for non-linearity of LEDs, defaults to 0.5
  --loop
  --camera              use a webcam instead of a video
  --debug               show the output in a window while streaming

```