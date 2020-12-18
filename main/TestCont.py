from android.Adb import AndroidDebugBridge
from boot.Boot import AdbFlowBoot
from recog.Base import *

flow = AdbFlowBoot(None)
node = flow.node_dic['96ece100-3249-11eb-bddc-03201143f505']
lr = ListFrameRecognizer(node.listAction['listArea'], node.listAction['itemArea'])
bounds = lr.find_item_bounds(cv2.imread('list.png'))
