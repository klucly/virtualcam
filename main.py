import pyvirtualcam
import numpy as np
from PIL import Image
from random import random
from time import perf_counter, sleep
import math
import colorsys
from threading import Thread
from enum import Enum
import pyautogui

class Mode(Enum):
    NORMAL = 1
    NIGHT = 2
    PARTY = 3

cut_pony_to_size = lambda b: b.resize([b.size[0]-100, b.size[1]-100]).crop([-106, 50, 1280-106, 720+50])

BLINK_DURATION = 2

def dance_brightness(t: float):
    t = math.modf(2*t)[0]

    if t < 1:
        return 100**t/100
    else:
        return -t+2

class Main:
    def __init__(self, cam: pyvirtualcam.Camera) -> None:
        self.cam = cam
        self.mode = Mode.NORMAL
        self.input_thread = Thread(target = self.cmd_input, name = "cmd-input")
        self.input_thread.start()
        self.light_matrix = np.zeros((720, 1280, 4), dtype = np.uint8)
        self.screen_color = (0, 0, 0)
        
        self.screen_color_handler = Thread(target = self.handle_screen_color, name = "cmd-input")
        self.screen_color_handler.start()

        print("Generating light matrix...")
        for i in range(720):
            for j in range(1280):
                value = np.uint8(255/(((i-720/2)/400)**2+((j-1280/2)/400)**2+1)**2)
                self.light_matrix[i,j,0] = value
                self.light_matrix[i,j,1] = value
                self.light_matrix[i,j,2] = value
                self.light_matrix[i,j,3] = 255
        
        print("Light matrix generated")

        self.open_eyes_image = Image.open(".\\blink-nobg.png")
        self.open_eyes_image = cut_pony_to_size(self.open_eyes_image)

        self.closed_eyes_image = Image.open(".\\blink1-nobg.png")
        self.closed_eyes_image = cut_pony_to_size(self.closed_eyes_image)

        self.blink()
        print(f'Using virtual camera: {self.cam.device}')


    def handle_screen_color(self) -> None:
        while 1:
            if self.mode != Mode.NIGHT:
                sleep(1)
                continue

            myScreenshot = pyautogui.screenshot()

            r, g, b = myScreenshot.split()
            r, g, b = np.asarray(r), np.asarray(g), np.asarray(b)
            r, g, b = r.sum()/(1280*720), g.sum()/(1280*720), b.sum()/(1280*720)
            self.screen_color = (int(r), int(g), int(b))

            sleep(1)


    def blink(self) -> None:
        self.time_to_blink = random()*9 + 1
        self.last_blink = perf_counter()
        self.frames_blinked = BLINK_DURATION


    def cmd_input(self) -> None:
        while 1:
            try:
                cmd = input().lower()
            except:
                exit(0)

            if cmd == "mode=party":
                self.mode = Mode.PARTY
            elif cmd == "mode=normal":
                self.mode = Mode.NORMAL
            elif cmd == "mode=night":
                self.mode = Mode.NIGHT
            else:
                print("Command not found")


    def mainloop(self) -> bool:
        if self.mode == Mode.PARTY:
            time_unstable = perf_counter() - self.last_blink
            brightness = max(int(255*dance_brightness(time_unstable)),50)
            raw_color = colorsys.hsv_to_rgb(time_unstable, 1, brightness)
            color = (int(raw_color[0]), int(raw_color[1]), int(raw_color[2]), 255)
        elif self.mode == Mode.NIGHT:
            color = (25, 25, 25, 255)
        else:
            color = (255, 255, 255, 255)

        frame = Image.new("RGBA", (1280, 720), color)

        if self.frames_blinked:
            self.frames_blinked -= 1
            pony = self.closed_eyes_image
        else:
            pony = self.open_eyes_image

        if self.mode == Mode.PARTY:
            pony = np.asarray(pony).copy()
            pony[:, :, 0] = color[0]/255 * pony[:, :, 0]
            pony[:, :, 1] = color[1]/255 * pony[:, :, 1]
            pony[:, :, 2] = color[2]/255 * pony[:, :, 2]
            pony = Image.fromarray(pony)

        elif self.mode == Mode.NIGHT:
            pony = np.asarray(pony).copy()
            screen_color_matrix = np.asarray(Image.new("RGBA", (1280, 720), self.screen_color))
            pony = np.uint8(pony/255 * self.light_matrix * (np.maximum(screen_color_matrix*1.-25, 0)+25) /255)
            pony = Image.fromarray(pony)


        frame.alpha_composite(pony)
        frame = frame.convert("RGB")

        current_time = perf_counter()
        if self.time_to_blink < current_time - self.last_blink:
            self.blink()

        self.cam.send(np.asarray(frame))
        self.cam.sleep_until_next_frame()


if __name__ == "__main__":
    with pyvirtualcam.Camera(width=1280, height=720, fps=20) as cam:
        main = Main(cam)
        while not main.mainloop(): ...
