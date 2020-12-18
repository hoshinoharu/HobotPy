# encoding=utf-8
import base64
import codecs
import json
import socket
import threading
import time
import traceback
import uuid
from threading import Lock

import _thread
from flask import Flask, request, abort, jsonify, send_file, Response
from flask_cors import CORS
from android.Adb import AndroidDebugBridge
from geventwebsocket import WebSocketError
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from boot.Boot import AdbFlowBoot
from recog.Base import BaseRecognizer

android_adb = AndroidDebugBridge()

app = Flask(__name__)
mutex = Lock()
CORS(app, resources=r'/*')

cur_flow_boot = None


class FlowRunner(threading.Thread):
    def __init__(self, monitor):
        threading.Thread.__init__(self)
        self.monitor = monitor

    def run(self):
        AdbFlowBoot(AndroidDebugBridge()).execute(self.monitor)


def run_flow(monitor):
    print '执行流程'
    adb = AndroidDebugBridge()
    # adb.daemon_rotation()
    cur_flow_boot = AdbFlowBoot(adb).execute(monitor)


def receive_message(wsock):
    while True:
        try:
            message = wsock.receive()
            if message is not None:
                operation = json.loads(message)
                operate = operation['operate']
                content = operation['content']
                if operate == 'uploadFlowData':
                    save_flow_json(content)
                    print '保存节点数据成功'
                    wsock.send(json.dumps({
                        'operate': 'uploadFlowData',
                        'content': True,
                    }), False)
                elif operate == 'startFlow':
                    save_flow_json(content)
                    runner = FlowRunner(lambda node: {
                        wsock.send(json.dumps({
                            'operate': 'onNodeUpdate',
                            'content': node.__dict__,
                        }), False)
                    })
                    runner.start()

        except Exception as e:
            traceback.print_exc()
            break


def send_screen_shot(wsock):
    while True:
        try:
            shot = android_adb.screen_shot()
            if shot is not None:
                wsock.send(shot, True)
        except Exception as e:
            traceback.print_exc()
            break


flow_path = '../resources/flow.json'


def load_flow_json():
    with codecs.open(flow_path, 'r', 'utf-8') as f:
        return json.loads(f.read())


def save_flow_json(flow_data):
    with codecs.open(flow_path, 'w', 'utf-8') as f:
        f.write(json.dumps(flow_data))


@app.route('/img/base64', methods=['POST'])
def upload_img():
    data = request.get_data(as_text=True)
    param = json.loads(data)
    base64_img = param['content']
    base_split = base64_img.split(';base64,')
    # 文件后缀名
    ext = base_split[0].split('data:image/')[-1]
    id = str(uuid.uuid4())
    image_name = id + '.' + ext
    img_str = base_split[-1]
    img_str = base64.decodestring(img_str)
    with open('../resources/upload/imgs/' + image_name, 'wb') as f:
        f.write(img_str)
    return jsonify(code=200, success=True, message='success', data='/img/{}'.format(image_name))


@app.route('/img/<name>.<ext>', methods=['GET'])
def img(name, ext):
    image = file('../resources/upload/imgs/{}.{}'.format(name, ext), 'rb')
    return Response(image, mimetype="image/{}".format(ext.lower()))


@app.route('/adb/display/info', methods=['GET'])
def display_info():
    return jsonify(code=200, success=True, message='success', data=android_adb.get_display_info())


@app.route('/app')
def handle_websocket():
    wsock = request.environ.get('wsgi.websocket')
    if not wsock:
        abort(400, 'Expected WebSocket request.')
    wsock.send(json.dumps({
        'operate': 'initFlowData',
        'content': load_flow_json(),
    }), False)
    _thread.start_new_thread(send_screen_shot, (wsock,))
    receive_message(wsock)


# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# s.connect(('127.0.0.1', 6677))
# s.shutdown(2)

android_adb.daemon_rotation()
server = WSGIServer(("127.0.0.1", 6677), app, handler_class=WebSocketHandler)
server.serve_forever()
# def test(n):
#     pass

