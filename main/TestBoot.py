# coding=utf-8
from android.Adb import AndroidDebugBridge
from boot.Boot import FlowBoot, AdbFlowBoot

adb = AndroidDebugBridge()

boot = AdbFlowBoot(adb)

boot.execute(None)
