#!/usr/bin/python3

import cv2
import numpy as np
import socket
import math
import requests
import json

MESSAGE_TYPE_DNRGB = 4
MAX_PIXELS_PER_FRAME = 480


def gammaCorrect(src, gamma):
    invGamma = 1 / gamma

    table = [((i / 255) ** invGamma) * 255 for i in range(256)]
    table = np.array(table, np.uint8)

    return cv2.LUT(src, table)


def getDimensions(host):
    response = requests.get("http://" + host + "/json/info", timeout=5)
    info = json.loads(response.text)

    width = info["leds"]["matrix"]["w"]
    height = info["leds"]["matrix"]["w"]

    return width, height


def sendFrame(sock, destination, frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = frame.flatten()

    for start in range(0, int(frame.size / 3), MAX_PIXELS_PER_FRAME):
        start_h = start >> 8
        start_l = start & 0xFF

        message = (
            bytes([MESSAGE_TYPE_DNRGB, 2, start_h, start_l])
            + frame[(start * 3) : (start + MAX_PIXELS_PER_FRAME) * 3]
            .astype("int8")
            .tobytes()
        )

        sock.sendto(message, destination)


def showVideo(args):
    ip = socket.gethostbyname(args.host)

    width = args.width
    height = args.height
    if width == 0 or height == 0:
        print("Getting dimensions from wled...")
        width, height = getDimensions(ip)
        print("width: %d, height: %d" % (width, height))

    video = args.video

    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        return

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        screen_ratio = width / height
        resampling = cv2.INTER_AREA

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_height, frame_width = frame.shape[:2]

            if args.scale == "stretch":
                frame = cv2.resize(frame, (width, height), interpolation=resampling)
            else:
                if args.scale in ["fill", "fit"]:
                    image_ratio = frame_width / frame_height

                    if (args.scale == "fill" and image_ratio > screen_ratio) or (
                        args.scale == "fit" and image_ratio < screen_ratio
                    ):
                        size = (math.floor(height * image_ratio), height)
                    else:
                        size = (width, math.floor(width / image_ratio))
                    frame = cv2.resize(frame, size, interpolation=resampling)

                frame_height, frame_width = frame.shape[:2]
                left = math.floor((frame_width - width) / 2)
                top = math.floor((frame_height - height) / 2)
                frame = frame[top : (top + height), left : (left + width)]
                # NB: frame could now be smaller than width, height!
                # see extension below

            frame_height, frame_width = frame.shape[:2]
            if frame_width < width or frame_height < height:
                left = math.floor((width - frame_width) / 2)
                right = width - frame_width - left
                top = math.floor((height - frame_height) / 2)
                bottom = height - frame_height - top
                frame = cv2.copyMakeBorder(
                    frame, top, bottom, left, right, cv2.BORDER_CONSTANT, 0
                )

            frame = gammaCorrect(frame, args.gamma)
            sendFrame(sock, (ip, args.port), frame)

            if args.debug:
                cv2.imshow("Frame", frame)

            cv2.waitKey(25)

            # Press Q on keyboard to exit
            # if cv2.waitKey(25) & 0xFF == ord('q'):
            #    break


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
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
    parser.add_argument("video")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    showVideo(args)
