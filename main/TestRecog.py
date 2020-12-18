# coding=utf-8
import cv2

from recog.Base import BaseRecognizer

img = {
    "src": "/img/2e629b62-d92b-41e0-bd41-b4f6154aa95f.png",
    "resolution_width": 2232,
    "resolution_height": 1080,
    "height": 139,
    "width": 611,
    "y": 299,
    "x": 326,
    "notExists": True,
    "id": "44d52d60-3d33-11eb-ad83-7ffe3d148b41"
}

recog = BaseRecognizer(img)
matchResult = recog.match_pic(cv2.imread('list.png'), '000000')
print matchResult.possibility

