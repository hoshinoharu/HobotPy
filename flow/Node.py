# -*-coding:utf-8-*-
import time
from datetime import datetime

from recog.Base import *


def get_image_src_name(img):
    return img['src'].split('img/')[-1].split('.')[0]


class FlowContextListener:

    def __init__(self):
        pass

    def on_get_screen_bytes(self, raw_screen):
        return raw_screen


class FlowContext:
    listenerMap = None  # type: dict[str, set[FlowContextListener]]

    def __init__(self, touch_executor, screen_provider):
        self.touch_executor = touch_executor
        self.raw_screen_bytes = None
        self.params = {}
        self.screen_provider = screen_provider
        self.currentNode = None
        self.listenerMap = {}

    def put_param(self, name, val):
        self.params[name] = val

    def get_param(self, name):
        if name in self.params:
            return self.params[name]
        else:
            return None

    def tap(self, loc):
        if self.touch_executor is not None:
            self.touch_executor.tap(loc)

    def swipe(self, bound):
        if self.touch_executor is not None:
            self.touch_executor.swipe(bound)

    def refresh_screen(self):
        self.raw_screen_bytes = self.screen_provider.get_screen()

    def get_screen_bytes(self):
        cur_listeners = self.get_node_action_listeners(self.currentNode)
        screen_bytes = self.raw_screen_bytes
        for listener in cur_listeners:
            screen_bytes = listener.on_get_screen_bytes(screen_bytes)
        return screen_bytes

    def notify_current_node(self, node):
        # type: (FlowNode) -> None
        self.currentNode = node

    # 注册节点行为监听器
    def register_node_action_listener(self, listener, target_nodes):
        # type: (FlowContextListener, list[Node]) -> None
        for node in target_nodes:
            if node.id in self.listenerMap:
                self.listenerMap[node.id].add(listener)
            else:
                self.listenerMap[node.id] = {listener}

    def get_node_action_listeners(self, node):
        # type: (FlowNode) -> list[FlowContextListener]
        return [] if node.id not in self.listenerMap else self.listenerMap[node.id]


class Node:
    id = None
    # 超时时间
    timeout = None
    first_judge_time = None
    # 节点是否完成
    finished = None
    # 父节点
    parent = None  # type: Node
    # 节点名称
    name = None
    children = None  # type: list[Node]
    # 计数器，当前节点执行的次数
    count = None

    previous_timeout = None
    enable = None

    def __init__(self):
        self.timeout = 20
        self.count = 0
        self.first_judge_time = None
        self.confirm_start_time = None
        self.name = ''
        self.finished = False
        self.parent = None
        self.children = []
        self.previous_timeout = 0
        self.enable = True
        self.id = None
        # 运行时的id 一个节点可能会被公用，但是每个节点的对象不是同一个
        self.run_id = None
        # 节点类型包括 成功节点以及失败节点，失败节点是在父节点execute失败时才会调用
        self.executed = False
        self.type = 'generic'
        # 排序
        self.order = 0
        # 是否执行过一次
        self.executeOnce = False
        # 是否尝试执行过
        self.tryExecuted = False
        # 是否被中断
        self.broken = False
        # 是否失败
        self.failed = False
        # 正在运行的子节点
        self.runningChild = None
        # 触发操作后是否会重新绘制界面
        self.repaint = True

    def __str__(self):
        return self.name

    def recover(self):
        self.finished = False
        self.previous_timeout = 0
        self.first_judge_time = None
        self.count = 0
        self.executed = False
        self.broken = False
        self.failed = False

        for child in self.children:
            if child.enable:
                child.recover()

    def can_execute(self, context):
        pass

    def execute(self, context):
        self.tryExecuted = True
        return True

    def idempotent_execution(self):
        return True

    def has_timeout(self):
        if self.timeout < 0 or self.finished:
            return False
        else:
            if self.first_judge_time is not None:
                now_time = datetime.now()
                interval = now_time - self.first_judge_time
                cur_timeout = (interval.seconds + interval.microseconds * 1.0 / 1000000) + self.previous_timeout
            else:
                cur_timeout = self.previous_timeout
            flag = cur_timeout > self.timeout
            self.log('{} 预设超时时间{}s，已超时{}s'.format(cur_timeout > self.timeout, self.timeout, cur_timeout))
            return flag

    # 选择一个未完成的子节点
    def pick_unfinished_child(self, pick_type=('generic', 'list', 'switch')):

        if isinstance(pick_type, str):
            pick_type = (pick_type)
        # 先按照执行次数排序，执行次数少的在前面，同样的执行次数按照order排序，order小的在前面
        self.children.sort(key=lambda node: (node.count, node.order))
        for child in self.children:
            if child.enable and not child.finished and child.type in pick_type:
                return child
        return None

    def pick_children(self, pick_type=('generic', 'list', 'switch')):
        picks = []
        self.children.sort(key=lambda node: (node.count, node.order))
        for child in self.children:
            if child.enable and child.type in pick_type:
                picks.append(child)
        return picks

    # 标记节点执行了一次
    def mark_execute(self):
        if not self.finished:
            interval = (datetime.now() - self.first_judge_time)
            timeout = interval.seconds + interval.microseconds * 1.0 / 1000000
            self.previous_timeout += timeout if timeout > 0 else 0.1
            self.log('历史超时时间：{}s'.format(self.previous_timeout))
            self.first_judge_time = None

    def log(self, msg):
        name_list = []
        node = self
        while node is not None:
            name_list.append(node.name)
            node = node.parent
        name_list.reverse()
        print '->'.join(name_list), ':', msg

    def confirm_execute(self, context):
        # type: (FlowContext) -> bool
        pass

    def run_child(self, context, child):
        # type: (FlowContext, Node) -> bool
        self.broken = False
        self.runningChild = child
        return child.run(context)

    # 流程节点运行的方法
    def run(self, context):
        # type: (FlowContext) -> bool
        if not self.enable:
            return False
        self.prepare_run(context)
        # 如果流程没有结束且没有超时
        if not self.finished and not self.has_timeout():
            if not self.executed:
                # 判断当前是否可以执行
                if self.can_execute(context):
                    if self.execute(context):
                        time.sleep(1)
                        self.start_confirm()
                        confirmed = False
                        while not self.has_confirm_timeout() and not confirmed:
                            # 检查是否执行成功
                            confirmed = self.confirm_execute(context)
                            if not confirmed:
                                if self.idempotent_execution():
                                    self.executed = False
                                    self.execute(context)
                                    time.sleep(1)
                            else:
                                self.executed = True
                        # 如果超时了还是没有确认执行成功
                        if not confirmed:
                            # 最后再检查一次执行状态
                            self.executed = self.confirm_execute(context)

            # 没有执行成功继续执行
            self.mark_execute()
        broken = self.broken
        if self.executed and not broken:
            broken = self.judge_break(context)

        if not broken and not self.finished and self.tryExecuted:
            if not self.executed:
                # 执行失败操作
                self.failed = True
                while True:
                    failedNode = self.pick_unfinished_child('failed')
                    if failedNode is None:
                        break
                    else:
                        self.run_child(context, failedNode)
                        if failedNode.finished:
                            self.finished = True
            else:
                # 如果当前节点执行成功，则执行子节点
                while not self.broken:
                    # 查找有无未结束的子任务节点
                    child = self.pick_unfinished_child()
                    if child is None:
                        break
                    else:
                        self.run_child(context, child)

        self.mark_finish(context)

        # 如果当前确认结束，执行结束节点的操作
        if self.finished and not self.broken:
            while True:
                # 选择未完成的终结节点任务
                child = self.pick_unfinished_child('finished')
                if child is None:
                    break
                else:
                    # 执行节点
                    self.run_child(context, child)

        # 通知父节点运行完成
        if self.parent is not None:
            self.parent.after_child_run(self, context)
        return True

    def mark_finish(self, context):
        # type: (FlowContext) -> None
        self.finished = self.executed
        pass

    def after_child_run(self, child, context):
        # type: (Node, FlowContext) -> None
        # 如果子节点执行失败，则当前节点也执行失败
        if child.name == u'远征中':
            print ''
        if child.failed:
            self.failed = True
        if child.broken:
            self.broken = True
            pass

    def has_confirm_timeout(self):
        if self.confirm_start_time is None:
            return False
        else:
            interval = (datetime.now() - self.confirm_start_time)
            timeout = interval.seconds + interval.microseconds * 1.0 / 1000000
            self.log('验证超时{}s,时间：{}s,预期时间：{}s'.format(timeout, timeout > self.timeout, self.timeout))
            if self.type == 'break':
                # 默认中断的超时时间为2秒
                return timeout > 5
            else:
                return timeout > self.timeout

    def start_confirm(self):
        self.confirm_start_time = datetime.now()
        pass

    def judge_break(self, context):
        # type: (FlowContext) -> bool
        pass

    def prepare_run(self, context):
        # type: (FlowContext) -> None
        context.notify_current_node(self)
        context.refresh_screen()
        self.count += 1
        self.first_judge_time = datetime.now()
        self.broken = False
        self.failed = False


class RootNode(Node):

    def __init__(self, child):
        Node.__init__(self)
        child.parent = self
        self.children.append(child)

    def can_execute(self, context):
        Node.can_execute(self, context)
        return True

    def confirm_execute(self, context):
        return True


class FlowNode(Node, FlowContextListener):
    skipImageHash = None  # type: list[ImageHash]

    def __init__(self):
        Node.__init__(self)
        self.actionImage = None
        self.landmarkImageGroups = []
        self.actionMarkIndex = 0
        self.landmarkRecognizeResult = []
        self.actionRecognizeResult = None

        # 列表行为
        self.listAction = None
        self.listRecognizer = None
        self.item_index = -1
        self.itemBounds = None
        self.swipeConfirmed = True
        # 滑动之前的界面
        self.swipeBefore = None
        # 滑动的范围，这里可以认为是列表的区域
        self.swipeBound = Bound()
        # 需要跳过的图片
        self.skipImageHash = []

    def __str__(self):
        if self.type == 'list':
            return u'{}, itemIndex:{}'.format(self.name, self.item_index)
        return self.name

    u'''
        是否可以执行当前节点
    '''

    def can_execute(self, context):
        Node.can_execute(self, context)
        if not self.executed:
            return self.recognize_landmark(context)
        return True

    def recognize_image(self, pic, img):
        recog = BaseRecognizer(img)
        tag = get_image_src_name(img) + '_judge'
        matchResult = recog.match_pic(pic, tag)
        if matchResult.possibility < 0.96 and not img['notExists']:
            return False
        else:
            return True

    def recognize_image_groups(self, pic, img_group):
        can = True
        for groupIndex, group in enumerate(img_group):
            can = True
            for img in group['images']:
                can = self.recognize_image(pic, img)
            # 多组识别，如果有一个组识别成功则整个匹配识别成功
            if can:
                break
        return can

    def recognize_landmark(self, context):
        can = True
        index = -1
        context.notify_current_node(self)
        for groupIndex, group in enumerate(self.landmarkImageGroups):
            can = True
            for img in group['images']:
                index += 1
                recog = BaseRecognizer(img)
                tag = get_image_src_name(img) + '_judge'
                matchResult = recog.match_pic(context.get_screen_bytes(), tag)
                resDic = {
                    'image': '/img/{}.png'.format(tag),
                    'possibility': matchResult.possibility,
                    'loc': matchResult.matchBound,
                    'x': matchResult.matchBound.x,
                    'y': matchResult.matchBound.y,
                }
                self.set_landmark_recognize_result(resDic, index)
                self.log(u'识别标识结果：{}'.format(resDic))
                notExist = img['notExists']
                if matchResult.possibility < 0.96:  # 匹配失败
                    if notExist:  # 如果就是判定不存在
                        can = True
                    else:
                        can = False
                else:  # 匹配成功
                    if notExist:  # 如果是判定不存，当前匹配失败
                        can = False
                    else:
                        can = True
                if can:
                    context.put_param('{}__index__{}'.format(str(self.id), index), matchResult.matchBound)
                else:
                    # 如果失败了不执行后面判断，判定失败
                    break
            # 多组识别，如果有一个组识别成功则整个匹配识别成功
            if can:
                break
        self.log('recognize_landmark：{}'.format(can))
        return can

    def set_landmark_recognize_result(self, result, index):
        # 保存匹配结果
        if index >= len(self.landmarkRecognizeResult):
            self.landmarkRecognizeResult.append(result)
        else:
            self.landmarkRecognizeResult[index] = result

    '''
        执行当前节点
    '''

    def prepare_run(self, context):
        Node.prepare_run(self, context)
        if self.type == 'list':
            # 注册节点监听器
            context.register_node_action_listener(self,
                                                  self.pick_children(pick_type=('generic', 'list', 'break', 'switch')))
        # 分支节点会注册父列表节点的监听器
        if self.type == 'switch' and self.parent.type == 'list':
            context.register_node_action_listener(self.parent, self.pick_children(pick_type=('generic', 'list', 'break',
                                                                                             'switch')))

    def on_get_screen_bytes(self, raw_screen):
        # 由于只有list节点会监听子节点的行为，所以这里直接切分
        screen = RecognizeBound()
        screen.image_bytes = raw_screen
        try:
            screen.image_bound = self.itemBounds[self.item_index]
        except Exception as e:
            print e
        return screen

    def execute(self, context):
        Node.execute(self, context)
        context.notify_current_node(self)
        if self.executed:
            return True
        success = False
        if self.type in ('generic', 'finished', 'failed', 'break', 'switch'):
            if self.actionMarkIndex >= 0:
                loc = context.get_param('{}__index__{}'.format(str(self.id), self.actionMarkIndex))
                if loc is not None:
                    self.log('点击tag_img:{}'.format(loc))
                    context.tap(loc)
                    success = True
            elif self.recognize_action(context):
                if self.actionRecognizeResult is not None:
                    loc = self.actionRecognizeResult['loc']
                    self.log('识别结果：{}\n点击tap_img'.format(self.actionRecognizeResult))
                    context.tap(loc)
                success = True
        elif self.type == 'list':
            if self.listRecognizer is None:
                self.listRecognizer = ListFrameRecognizer(self.listAction['listArea'], self.listAction['itemArea'])
            if self.itemBounds is None:
                # 获取所有item
                self.itemBounds = self.listRecognizer.find_item_bounds(context.get_screen_bytes())
            self.item_index += 1
            # 确保存在item
            if len(self.itemBounds) > 0:
                # 如果item索引不超过数组长度
                if self.item_index < len(self.itemBounds):
                    itemBound = self.itemBounds[self.item_index]
                    itemCut = Recognizer.cut(self.listRecognizer.pic_tpl, itemBound)
                    itemHash = Recognizer.hash(itemCut)
                    skip = False
                    for skipHash in self.skipImageHash:
                        res = skipHash.compare(itemHash)
                        self.log('与失败图片的哈希相似度：{}'.format(res))
                        # 表示两张图片一样 需要跳过
                        if res > 0.98:
                            skip = True
                            self.log('跳过当前item索引：{}'.format(self.item_index))
                            break

                    if not skip:
                        # 如果不需要跳过。直接返回成功
                        success = True
                        self.log(u'执行item：{}, itemBounds数量：{}'.format(self.item_index, len(self.itemBounds)))
                        # # 先进行item标识识别
                        # if self.recognize_image_groups(itemCut, self.listAction['itemLandmarkImageGroups']):
                        #     rec = BaseRecognizer(self.actionImage)
                        #     matchResult = rec.match_in_bound(self.listRecognizer.pic_tpl, itemBound, 'list')
                        #     # 如果没有找到action图片则需要跳过
                        #     if matchResult.possibility > 0.96:
                        #         context.tap(matchResult.matchBound)
                        #         success = True
                        #         self.executeOnce = True
                        #     else:
                        #         skip = True
                        # else:
                        #     skip = True
                    if skip:
                        # 如果需要则重新执行
                        # self.item_index += 1
                        success = self.execute(context)
                else:  # 需要滑动屏幕,滑动最后一个item的bottom到list的top
                    lastBound = self.itemBounds[-1]
                    lastBottom = lastBound.y + lastBound.height
                    listTop = self.listAction['listArea']['y'] - 10
                    distance = lastBottom - listTop

                    self.swipeBound.x = self.listAction['listArea']['x']
                    self.swipeBound.y = self.listAction['listArea']['y']
                    self.swipeBound.width = self.listAction['listArea']['width']
                    self.swipeBound.height = distance  # flip比例
                    # 获取滑动之前的列表图像
                    self.swipeBefore = Recognizer.cut(context.get_screen_bytes(), self.swipeBound)
                    # 滚动屏幕
                    context.swipe(self.swipeBound)
                    self.swipeConfirmed = False
                    success = True

        return success

    def after_child_run(self, child, context):
        Node.after_child_run(self, child, context)
        # 如果当前是分支节点
        if self.type == 'switch':
            # 如果有其中一个子节点执行完成，那么认为该分支子节点全部结束
            if child.finished:
                # 分支节点本身的属性除了是否可用，其他的都应该是当前执行完成的子节点的执行属性
                if child.executed:
                    self.failed = False
                self.repaint = child.repaint
                children = self.pick_children()
                for child in children:
                    child.finished = True

        if self.type == 'list':
            if child.repaint and child.finished and child.executed and not child.broken:
                # 子节点成功执行完成的话，刷新item索引
                self.item_index = -1
                self.itemBounds = None

    def mark_execute(self):
        Node.mark_execute(self)
        if self.type == 'list' and self.executed:
            # self.item_index += 1
            # self.log('当前item索引：{}'.format(self.item_index))
            for child in self.children:
                if child.enable:
                    child.recover()

    def judge_break(self, context):
        broken = False
        context.notify_current_node(self)
        # 执行中断节点
        breakChildren = self.pick_children(pick_type=('break'))
        for child in breakChildren:
            child.recover()
            self.run_child(context, child)
            if child.finished and child.executed:
                child.log('中断流程')
                broken = True
                # 如果中断类型的子节点执行成功，直接退出执行
                self.broken = True
                break
        return broken

    def recover(self):
        Node.recover(self)

    def confirm_execute(self, context):  # type: (FlowContext) -> bool
        confirm = False
        context.notify_current_node(self)
        # 刷新屏幕缓存
        context.refresh_screen()
        if not self.swipeConfirmed:
            # 获取图片相似度
            similarity = Recognizer.similarity_of_images(self.swipeBefore,
                                                         Recognizer.cut(context.get_screen_bytes(), self.swipeBound))
            self.log('滑动后图片相似度：{}'.format(similarity))
            # 标识两张图片不一样
            if similarity < 0.98:
                confirm = True
                # 重新初始化滑动相关参数
                self.swipeConfirmed = True
                self.item_index = -1
                # 重新识别边框
                self.listRecognizer = ListFrameRecognizer(self.listAction['listArea'], self.listAction['itemArea'])
                self.itemBounds = self.listRecognizer.find_item_bounds(context.get_screen_bytes())
                # 标识单次滑动操作执行完成
                self.finished = True
        else:
            # 没有行为直接确认执行
            if self.actionImage is None and self.actionMarkIndex < 0:
                return True

            broken = self.judge_break(context)
            confirm = broken
            # 没有中断再进行其他验证
            if not broken:
                # 验证执行结果
                # 优先获取verify子节点
                verifyChildren = self.pick_children(pick_type=('verify'))
                if len(verifyChildren) > 0:
                    self.log('执行验证节点')
                    for child in verifyChildren:
                        if isinstance(child, FlowNode):
                            child.log('执行验证识别')
                            confirm = child.recognize_landmark(context)
                            if confirm:
                                break
                else:
                    # 没有验证节点时，判断当前操作触发了子节点
                    pick_children = self.pick_children()
                    self.log('执行子节点验证节点')
                    for child in pick_children:
                        if isinstance(child, FlowNode):
                            child.log(u'{}执行子节点验证识别'.format(self.name))
                            if child.recognize_landmark(context):
                                confirm = True
                                break

                    if not confirm:
                        if not self.recognize_landmark(context):
                            confirm = True
                        else:
                            confirm = False

            self.log('验证执行:{}'.format('成功' if confirm else '失败'))

        if confirm and self.type == 'list':  # 如果执行确认成功，恢复所有子节点状态
            for child in self.children:
                if child.enable:
                    child.recover()

        return confirm

    def judge_not_timeout_by_second(self, pre, now, time_second):
        interval = now - pre
        second = interval.seconds + interval.microseconds * 1.0 / 1000000
        return time_second > second

    def recognize_action(self, context):
        self.actionRecognizeResult = None
        if self.actionImage is None:
            return True
        context.notify_current_node(self)
        recog = BaseRecognizer(self.actionImage)
        tag = get_image_src_name(self.actionImage) + '_execute'
        matchResult = recog.match_pic(context.get_screen_bytes(), tag)
        self.actionRecognizeResult = {
            'image': '/img/{}.png'.format(tag),
            'possibility': matchResult.possibility,
            'loc': matchResult.matchBound,
            'x': matchResult.matchBound.x,
            'y': matchResult.matchBound.y,
            'action': 'tap'
        }
        flag = matchResult.possibility > 0.95
        return flag

    def mark_finish(self, context):
        context.notify_current_node(self)
        Node.mark_finish(self, context)
        if self.type == 'list':
            # 如果当前需要跳过的item数量超过3个则表示超时，需要结束
            if len(self.skipImageHash) >= 6:
                self.log('当前跳过图片数量：{}'.format(len(self.skipImageHash)))
                self.finished = True
            else:
                # 如果当前item执行失败，保留当前节点hash放如跳过节点中
                if self.failed or self.broken:
                    if self.itemBounds is not None and len(self.itemBounds) > self.item_index >= 0:
                        preBound = self.itemBounds[self.item_index]
                        cutImage = Recognizer.cut(context.get_screen_bytes(), preBound)
                        imgHash = Recognizer.hash(cutImage)
                        has_appended = False
                        for has_h in self.skipImageHash:
                            # 判断是否包含
                            if has_h.compare(imgHash) > 0.98:
                                has_appended = True
                                break

                        # 不包含才添加
                        if not has_appended:
                            self.skipImageHash.append(imgHash)
                            self.log('增加失败图片hash')
                        # cv2.imwrite('skipItem_{}.png'.format(len(self.skipImageHash)), cutImage)

                if not self.swipeConfirmed:
                    # 如果滑动验证没有通过，表示无法继续滑动了，流程执行完成
                    self.executed = self.executeOnce
                    self.finished = True
                else:
                    # 执行完整的一次流程之后，恢复执行状态,再次执行
                    self.executed = False
                    self.finished = False
                    # 重置历史超时时间
                    self.previous_timeout = 0
                    self.broken = False

        else:

            if self.has_timeout():
                self.finished = True

    def idempotent_execution(self):
        if self.type == 'list':
            return False
        return True
