# -*-coding:utf-8-*-
import math
import os
import random
import subprocess
from io import BytesIO
from subprocess import Popen

import _thread
from PIL import Image
from airtest.core.android.rotation import XYTransformer
from airtest.core.android.touch_methods.base_touch import DownEvent, MoveEvent, UpEvent, SleepEvent
from airtest.core.android.touch_methods.minitouch import Minitouch

from maker.Capturer import ScreenProvider
from airtest.core.api import *
from airtest.core.android.minicap import *

from maker.Touch import TouchExecutor


class AndroidDebugBridge(ScreenProvider, TouchExecutor):
    adb_path = 'D:/Android/SDK/platform-tools/adb.exe'
    adb = None
    min_cap = None
    android_device = None
    rotation = None

    def __init__(self):
        ScreenProvider.__init__(self)
        # os.system(self.adb_path + ' devices')
        self.android_device = connect_device("Android:///")
        self.adb = self.android_device.adb
        self.miniTouch = None
        self.displayInfo = None

    def execute_cmd(self, cmd):
        p = Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        result = None
        if Popen.poll(p) is None:
            result = p.stdout.read()
        return result

    def screen_shot(self):
        if self.min_cap is None:
            self.min_cap = Minicap(self.adb)  # 分辨率可以适当修改，提高速度
        image_bytes = self.min_cap.get_frame_from_stream()
        return image_bytes
        # cmd = self.adb_path + ' exec-out screencap -p'
        # shot = self.execute_cmd(cmd)
        # with open('test.png', 'wb') as test:
        #     test.write(shot)
        # return shot

    def get_display_info(self):
        if self.displayInfo is None:
            self.displayInfo = self.adb.get_display_info()
        return self.displayInfo

    def get_screen(self):
        # # 将bytes结果转化为字节流
        # bytes_stream = BytesIO(self.screen_shot())
        # # 读取到图片
        # return Image.open(bytes_stream).copy()
        return self.screen_shot()

    def tap(self, bound):
        # 获取宽度的五分之一
        frag_w = bound.width * 1.0 / 5
        # 获取高度的三分之一
        frag_h = bound.height * 1.0 / 3
        factor_w = random.random()
        factor_h = random.random()
        x = bound.x + (2 + factor_w) * frag_w
        y = bound.y + (2 + factor_h) * frag_h
        if self.miniTouch is None:
            self.miniTouch = Minitouch(self.adb, ori_function=self.android_device.get_display_info,
                                       input_event=self.android_device.input_event)

        events = [
            DownEvent(self.ori_to_up(x, y), 0),
            SleepEvent(0.2),
            UpEvent(0)
        ]
        print 'execute_tap {}, {}'.format(x, y)
        self.miniTouch.perform(events, 0)

        # cmd = 'input tap {} {}'.format(x, y)
        # print cmd
        # self.android_device.shell(cmd)

    def ori_to_up(self, x, y):
        displayInfo = self.get_display_info()
        w = displayInfo['width']
        h = displayInfo['height']
        orientation = displayInfo['orientation']
        if orientation == 1:
            x, y = w - y, x
        elif orientation == 3:
            x, y = y, h - x
        return x, y

    def swipe(self, bound):
        if self.miniTouch is None:
            self.miniTouch = Minitouch(self.adb, ori_function=self.android_device.get_display_info,
                                       input_event=self.android_device.input_event)
        duration = random.randint(1000, 1200)
        topX = random.randint(int(bound.x + bound.width * 0.65), int(bound.x + bound.width * 0.9))
        bottomX = random.randint(int(bound.x + bound.width * 0.65), int(bound.x + bound.width * 0.9))
        # y轴偏移量
        yOffset = random.randint(0, 10)
        topY = bound.y + yOffset
        bottomY = bound.y + bound.height + yOffset
        gap_duration = 30
        gap_distance = (bottomY - topY) / (duration / gap_duration)
        cur_distance = 0
        events = [
            DownEvent(self.ori_to_up(bottomX, bottomY), 0)
        ]
        # 超出的距离
        overflowDistance = random.randint(25, 30)
        while cur_distance < bound.height + overflowDistance:
            events.extend([
                SleepEvent(gap_duration / 1000.0),
                MoveEvent(self.ori_to_up(bottomX + math.pow(cur_distance, 0.5), bottomY - cur_distance), 0)
            ])
            cur_distance += gap_distance

        while cur_distance > bound.height:
            cur_distance -= gap_distance
            events.extend([
                SleepEvent(gap_duration / 1000.0),
                MoveEvent(self.ori_to_up(bottomX + math.pow(cur_distance + random.randint(-3, 4), 0.5),
                                         bottomY - cur_distance), 0)
            ])

        events.extend([
            SleepEvent(gap_duration / 1000.0),
            MoveEvent(self.ori_to_up(bottomX + math.pow(bound.height, 0.5), bottomY - bound.height), 0),
            SleepEvent(0.4),
            UpEvent(0)
        ])
        # events = [
        #     DownEvent((0, 0), 1),
        # ]
        # for i in range(0, 100):
        #     events.append(MoveEvent((i * 10, i*20), 1))
        # events.append(UpEvent(1))
        self.miniTouch.perform(events, 0)
        # self.miniTouch.swipe_along()
        # cmd = 'input swipe {} {} {} {} {}'.format(bottomX, bottomY, topX, topY, duration)
        # self.android_device.shell(cmd)
        # time.sleep(duration / 1000.0)

    def check_rotation(self):
        while True:
            try:
                if self.min_cap is not None:
                    info = self.min_cap.get_display_info()
                    cur_rotation = info['rotation']
                    if self.rotation is not None and not self.rotation == cur_rotation:
                        self.min_cap.update_rotation(cur_rotation)
                    self.rotation = cur_rotation
            except Exception as e:
                pass
            time.sleep(1)

    def daemon_rotation(self):
        _thread.start_new_thread(self.check_rotation, ())
