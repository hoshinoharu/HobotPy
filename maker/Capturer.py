# -*-coding:utf-8-*-
import json
import time
import traceback
import uuid
from threading import Lock

import _thread
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab, ImageTk, Image


class ScreenProvider:

    def __init__(self):
        pass

    def get_screen(self):
        pass


class CaptureImage:
    path = '',
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    resolution_width = 0,
    resolution_height = 0,

    def __init__(self, path, x, y, width, height, resolution_width, resolution_height):
        self.path = path
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.resolution_width = resolution_width
        self.resolution_height = resolution_height
        pass

    def dic(self):
        return {
            'path': self.path,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'resolution_width': self.resolution_width,
            'resolution_height': self.resolution_height,
        }


class ScreenCapturer:
    root = None,
    max_w = 0,
    max_h = 0,
    screen_canvas = None,
    screen_w = 0,
    screen_h = 0,
    capture_rect = None,
    capture_x = 0,
    cur_capture_x = 0,
    capture_y = 0,
    cur_capture_y = 0,
    capture_screen = None,
    is_capturing = False,
    ori_screen_img = None,
    capture_img = None
    screen_provider = None,
    capture_photo = None,
    screen_photo = None,
    capture_loc = None,
    touching = False
    save_btn = None
    operate_panel = None
    capture_img_list = []

    def __init__(self, screen_provider):
        self.screen_provider = screen_provider
        self.root = tk.Tk()
        self.max_w, self.max_h = self.root.maxsize()
        self.screen_h = self.max_h / 2
        self.screen_w = self.max_w / 2
        self.root.geometry("{}x{}".format(self.max_w, self.max_h))
        self.screen_canvas = tk.Canvas(self.root, bg='white', width=self.screen_w, height=self.screen_h)
        self.screen_canvas.bind('<Button-1>', func=self.start)
        self.screen_canvas.bind('<B1-Motion>', func=self.move)
        self.screen_canvas.bind('<ButtonRelease-1>', func=self.end)
        # self.screen_canvas.bind('<Double-Button-1>', func=self.double_screen)
        self.screen_canvas.grid(row=0, column=0)
        self.capture_screen = tk.Canvas(self.root, bg='white', width=self.screen_w, height=self.screen_h)
        self.capture_screen.grid(row=0, column=1)
        self.root.bind('<Left>', self.on_frame_move)
        self.root.bind('<Right>', self.on_frame_move)
        self.root.bind('<Down>', self.on_frame_move)
        self.root.bind('<Up>', self.on_frame_move)
        self.root.bind('<Alt-Left>', self.on_frame_change)
        self.root.bind('<Alt-Right>', self.on_frame_change)
        self.root.bind('<Alt-Down>', self.on_frame_change)
        self.root.bind('<Alt-Up>', self.on_frame_change)
        self.operate_panel = tk.Frame(self.root, height=self.screen_h)
        self.operate_panel.grid(row=1, column=0, columnspan=2, sticky=tk.E + tk.W)
        self.add_btn = tk.Button(self.operate_panel, text='添加')
        self.add_btn.bind('<Button-1>', func=self.save_capture)
        self.add_btn.grid(row=0, column=0)
        self.save_btn = tk.Button(self.operate_panel, text='保存')
        self.save_btn.grid(row=0, column=1)
        self.save_btn.bind('<Button-1>', func=self.save_all_capture)
        record_btn = tk.Button(self.operate_panel, text='(开启/关闭)录制')
        record_btn.grid(row=0, column=2)
        record_btn.bind('<Button-1>', func=self.toggle_record)
        pass

    def toggle_record(self, event):
        self.touching = not self.touching

    def on_frame_change(self, event):
        key = event.keysym
        key = str(key)
        offset = 0.1
        if self.has_capture_photo():
            if 'Up' == key:
                self.cur_capture_y -= offset
            elif key == 'Down':
                self.cur_capture_y += offset
            elif key == 'Left':
                self.cur_capture_x -= offset
            elif key == 'Right':
                self.cur_capture_x += offset
            self.cur_capture_x = self.judge_loc(self.cur_capture_x, self.screen_photo.width())
            self.cur_capture_y = self.judge_loc(self.cur_capture_y, self.screen_photo.height())
            self.do_draw_capture_frame()
            self.do_capture_photo()
            self.do_draw_capture()

    def on_frame_move(self, event):
        key = event.keysym
        key = str(key)
        offset = 0.1
        if self.has_capture_photo():
            if 'Up' == key:
                self.capture_y -= offset
                self.cur_capture_y -= offset
            elif key == 'Down':
                self.capture_y += offset
                self.cur_capture_y += offset
            elif key == 'Left':
                self.capture_x -= offset
                self.cur_capture_x -= offset
            elif key == 'Right':
                self.capture_x += offset
                self.cur_capture_x += offset

            self.capture_x = self.judge_loc(self.capture_x, self.screen_photo.width())
            self.capture_y = self.judge_loc(self.capture_y, self.screen_photo.height())
            self.cur_capture_x = self.judge_loc(self.cur_capture_x, self.screen_photo.width())
            self.cur_capture_y = self.judge_loc(self.cur_capture_y, self.screen_photo.height())
            self.do_draw_capture_frame()
            self.do_capture_photo()
            self.do_draw_capture()

    def judge_loc(self, loc, limit):
        if loc < 0:
            loc = 0
        elif loc > limit:
            loc = limit
        return loc

    def start(self, event):
        self.touching = True
        self.capture_x = event.x
        self.capture_y = event.y
        self.is_capturing = False
        if self.has_screen_photo():
            if self.capture_x <= self.screen_photo.width() and self.capture_y <= self.screen_photo.height():
                self.is_capturing = True
                self.cur_capture_x = event.x
                self.cur_capture_y = event.y
                self.do_draw_capture_frame()

    def move(self, event):
        self.cur_capture_x = event.x
        self.cur_capture_y = event.y
        if self.is_capturing:
            if self.cur_capture_x > self.screen_photo.width():
                self.cur_capture_x = self.screen_photo.width()
            if self.cur_capture_y > self.screen_photo.height():
                self.cur_capture_y = self.screen_photo.height()
        self.do_draw_capture_frame()
        try:
            self.do_capture_photo()
            self.do_draw_capture()
        except Exception as e:
            traceback.print_exc()

    def end(self, event):
        self.touching = False

    def do_capture_photo(self):
        if self.ori_screen_img is not None \
                and not isinstance(self.capture_x, tuple) \
                and not isinstance(self.cur_capture_x, tuple):
            x = self.ori_screen_img.width * self.capture_x / self.screen_photo.width()
            cx = self.ori_screen_img.width * self.cur_capture_x / self.screen_photo.width()
            y = self.ori_screen_img.height * self.capture_y / self.screen_photo.height()
            cy = self.ori_screen_img.height * self.cur_capture_y / self.screen_photo.height()
            self.capture_img = self.ori_screen_img.crop((x, y, cx, cy))
            if self.capture_img.width > 0 and self.capture_img.height > 0:
                self.capture_loc = (x, y)
                self.capture_photo = self.img_2_fix_center_photo(self.capture_img, self.screen_w, self.screen_h)

    def do_draw_capture(self):
        if self.has_capture_photo():
            self.capture_screen.create_image(self.capture_photo.width(), self.capture_photo.height(),
                                             image=self.capture_photo, anchor='se')

    def has_capture_photo(self):
        return self.capture_photo is not None and not isinstance(self.capture_photo, tuple)

    def do_draw_capture_frame(self):
        try:
            if self.capture_rect is not None and not isinstance(self.capture_rect, tuple):
                self.screen_canvas.delete(self.capture_rect)
            if self.is_capturing:
                self.capture_rect = self.screen_canvas.create_rectangle(self.capture_x, self.capture_y,
                                                                        self.cur_capture_x, self.cur_capture_y,
                                                                        outline='red')
        except Exception as e:
            traceback.print_exc()

    def auto_refresh_screen(self):
        if self.touching is False:
            try:
                self.refresh_screen(None)
                self.do_capture_photo()
                self.do_draw_capture()
            except Exception as e:
                traceback.print_exc()
                time.sleep(0.05)

    def refresh_screen(self, event):
        try:
            self.ori_screen_img = self.screen_provider.get_screen()
            self.screen_photo = self.img_2_fix_center_photo(self.ori_screen_img, self.screen_w, self.screen_h)
            self.do_draw_screen()
            self.do_draw_capture_frame()
        except Exception as e:
            traceback.print_exc()

    def img_2_fix_center_photo(self, ori_img, width, height):
        ori_w = ori_img.width
        ori_h = ori_img.height
        ori_factor = ori_w * 1.0 / ori_h
        factor = width * 1.0 / height
        if ori_factor < factor:
            tar_h = height
            tar_w = int(height * 1.0 / ori_h * ori_w)
        else:
            tar_w = width
            tar_h = int(width * 1.0 / ori_w * ori_h)
        img = ori_img.resize((tar_w, tar_h), Image.ANTIALIAS)
        return ImageTk.PhotoImage(img)

    def do_draw_screen(self):
        self.screen_canvas.create_image(self.screen_photo.width(), self.screen_photo.height(),
                                        image=self.screen_photo, anchor='se')

    def has_screen_photo(self):
        return isinstance(self.screen_photo, ImageTk.PhotoImage)

    def save_capture(self, event):
        save_path = '../resources/make/imgs/' + str(uuid.uuid1()) + '.png'
        if self.capture_img is not None:
            self.capture_img.save(save_path)
            capture = CaptureImage(save_path, self.capture_loc[0], self.capture_loc[1],
                                   self.capture_img.width, self.capture_img.height,
                                   self.ori_screen_img.width, self.ori_screen_img.height)
            print capture
            self.capture_img_list.append(capture.dic())

    def save_all_capture(self, event):
        print json.dumps(self.capture_img_list)
        self.capture_img_list = []

    def capture(self):
        self.root.mainloop()
