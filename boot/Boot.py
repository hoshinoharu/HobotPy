# coding=utf-8
import copy
import json
import os
import time
import uuid

from flow.Node import FlowNode, FlowContext, RootNode, Node


def set_props(obj, name, prop_dic):
    if name in prop_dic:
        setattr(obj, name, prop_dic[name])


class FlowBoot:
    node_dic = None  # type: dict[str, FlowNode]

    def __init__(self, screen_provider, touch_executor):
        self.node_dic = {}
        # 共享的节点
        self.shared_node_dic = {}
        self.measure = None

        self.root_node = None
        self.context = FlowContext(touch_executor, screen_provider)
        self.init_node()
        self.clear_image()
        pass

    def execute(self, monitor):
        cur_node = self.find_cur_flow(self.root_node)
        if cur_node is None:
            cur_node = self.root_node

        while not cur_node.finished:
            cur_node.run(self.context)
        par_node = cur_node.parent
        while par_node is not None:
            par_node.executed = True
            par_node.tryExecuted = True
            par_node.run(self.context)
            par_node = par_node.parent
        # while cur_node is not None:
        #     self.context.refresh_screen()
        #     # 执行当前节点的判断
        #     if cur_node.can_execute(self.context):
        #         # 如果当前节点操作成功
        #         if cur_node.execute(self.context):
        #             # 选择一个未完成的节点
        #             node = cur_node.pick_unfinished_child()
        #             # 如果有未完成的子节点，直接执行子节点
        #             if node is not None:
        #                 cur_node = node
        #                 continue
        #             else:  # 如果没有未完成的子节点，表示当前节点执行完成
        #                 cur_node.finished = True
        #         else:
        #             cur_node.log('执行失败')
        #             # 执行失败选择一个处理失败的节点
        #             node = cur_node.pick_unfinished_child('failed')
        #             if node is not None:
        #                 cur_node = node
        #                 continue
        #
        #     cur_node.mark_execute()
        #     cur_node.log('标记执行完成')
        #
        #     # 如果当前节点不是完成状态，并且可以进入完成状态（超时状态），则强行停止，直接完成
        #     if not cur_node.finished and cur_node.has_timeout():
        #         cur_node.executed = False  # 未执行
        #         cur_node.finished = True  # 已结束
        #
        #     self.onUpdateNode(cur_node, monitor)
        #     # 节点执行完成之后需要执行完成流程后所需要的执行的流程
        #     if cur_node.finished:
        #         node = cur_node.pick_unfinished_child('finished')
        #         if node is not None:
        #             cur_node.log('执行完成之后的流程')
        #             cur_node = node
        #             continue
        #
        #     cur_node = cur_node.parent

    def onUpdateNode(self, node, monitor):
        node = copy.copy(node)
        node.parent = None
        node.children = None
        node.first_judge_time = None
        monitor(node)

    def init_node(self):
        with open('../resources/flow.json') as flow:
            flow_str = flow.read()
            dic = json.loads(flow_str, encoding='utf-8')
            self.measure = dic['measure']
            start_node = self.dic2node(dic['flow'])
            self.root_node = RootNode(start_node.children[0])

    def clear_image(self):
        img_set = set()
        for dp in self.measure:
            for img_id in self.measure[dp]:
                img_set.add(self.measure[dp][img_id]['src'].split('/img/')[-1])
        path = '../resources/upload/imgs'
        for img in os.listdir(path):
            if not img in img_set:
                img_path = os.path.join(path, img)
                print 'remove  {}'.format(img_path)
                # os.remove(img_path)

    def find_cur_flow(self, node):
        # type: (Node) -> Node
        self.context.notify_current_node(node)
        self.context.refresh_screen()
        # 不是跟节点
        if node.can_execute(self.context) and not isinstance(node, RootNode):
            return node
        else:
            # 根据order排序节点
            node.children.sort(key=lambda n: n.order)
            for child in node.children:
                if child.enable and child.type in ('generic', 'finished', 'list'):
                    tar = self.find_cur_flow(child)
                    if tar is not None:
                        if tar.type == 'finished':
                            for c_n in node.children:
                                if c_n is not tar:
                                    c_n.finished = True
                        return tar
        return None

    def dic2node(self, d):
        first_node = None
        for nd in d['nodeList']:
            flow_node = FlowNode()
            for key in nd:
                set_props(flow_node, key, nd)
            flow_node.children = []
            flow_node.init_runtime()
            # 初始化运行id
            if flow_node.run_id is None:
                flow_node.run_id = str(uuid.uuid4())

            self.node_dic[flow_node.id] = flow_node
            if first_node is None:
                first_node = flow_node
        for line in d['lineList']:
            if 'landmarkImageGroups' not in line or len(line['landmarkImageGroups']) == 0:
                for ld in d['lineList']:
                    # 如果两条线的目的地一样, 表示复用的节点,name节点的landmarkImage也应该一样
                    # 主要就是为了复用节点，只要节点的一条线有标识即可
                    if line is not ld and line['to'] == ld['to'] and 'landmarkImageGroups' in ld:
                        line['landmarkImageGroups'] = ld['landmarkImageGroups']

        for ld in d['lineList']:
            from_node = self.node_dic[ld['from']]
            to_node = self.node_dic[ld['to']]
            if to_node.id not in self.shared_node_dic:
                self.shared_node_dic[to_node.id] = [to_node]
            if to_node.parent is not None:
                # 如果一个节点被多个其他节点使用则需要拷贝一份
                to_node = copy.deepcopy(to_node)
                to_node.run_id = str(uuid.uuid4())
                self.shared_node_dic[to_node.id].append(to_node)
            to_node.parent = from_node
            to_node.landmarkImageGroups = ld['landmarkImageGroups']
            from_node.children.append(to_node)
            if from_node.id in self.shared_node_dic:
                for shared_node in self.shared_node_dic[from_node.id]:
                    if shared_node is not from_node:
                        shared_node.children = from_node.children
        cur_node = first_node
        while True:
            if cur_node.parent is None:
                return cur_node
            cur_node = cur_node.parent


class AdbFlowBoot(FlowBoot):
    def __init__(self, adb):
        FlowBoot.__init__(self, adb, adb)
        self.adb = adb
