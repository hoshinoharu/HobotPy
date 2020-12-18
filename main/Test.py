# coding=utf-8
import json
import math
import os
import re
from datetime import datetime

src_path = r'C:\Users\HP\Desktop\vmlogs'
dirs = os.listdir(unicode(src_path, 'utf-8'))
data_tpl = '2020-12-10 '
time_tpl = '09:57:51.634'

milepost = [
    # ['The function Process', 'start vm creation task', '虚机克隆完成耗时', 'vm creation finish', 'Apply virtual machine end'],
    ['The function Process', 'start vm creation task', '基于模板克隆虚拟机的任务执行成功', 'vm creation finish:', '更新虚拟机IP成功'],
]
milepost_time = [
]
case_name = []
mp_index = -1
for log in dirs:
    mp_index += 1
    if mp_index >= len(milepost):
        mp_index = len(milepost) - 1
    start_time = None
    p_i = 0
    mp_time = [0, 0, 0, 0, 0]
    case_name.append(str(log.encode('utf-8')))
    with open(src_path + '/' + log, 'r') as f:
        for line in f.readlines():
            if re.match(r'.*?\d+:\d+:\d+.\d{3}', line):
                log_time = datetime.strptime(line[len(data_tpl):len(data_tpl) + len(time_tpl)], '%H:%M:%S.%f')
                if start_time is None:
                    start_time = log_time
                interval = log_time - start_time
                sec = interval.seconds + interval.microseconds / 1000000.0
                # print line
                if p_i < len(milepost[mp_index]):
                    if p_i > 0:
                        if re.match(r'.*' + milepost[mp_index][p_i - 1] + '.*', line):
                            # print sec, line[12:]
                            mp_time[p_i] = sec - sum(mp_time[0:p_i])
                    if re.match(r'.*' + milepost[mp_index][p_i] + '.*', line):
                        # print sec, line[12:]
                        if p_i == 0:
                            mp_time[p_i] = sec
                        else:
                            mp_time[p_i] = sec - sum(mp_time[0:p_i])
                        p_i += 1

    milepost_time.append(mp_time)

print milepost_time
legend = ['系统准备时间', '云管业务流转', 'VC创建虚拟机', '同步虚机数据', '虚拟机创建流程结束']


class Serie:
    def __init__(self):
        self.name = ''
        self.type = 'bar'
        self.stack = '总量'
        self.label = {
            'show': True,
        }
        self.data = None
        pass


series = []
for i, le in enumerate(legend):
    se = Serie()
    se.name = legend[i]
    se.data = []
    for m_i in range(len(milepost_time)):
        se.data.append(int(math.ceil(milepost_time[m_i][i])))
    series.append(se.__dict__)

se = Serie()
se.name = ''
se.data = []
for m_i in range(len(milepost_time)):
    se.data.append(0)
series.append(se.__dict__)

print json.dumps(series)

print '['
for i, cn in enumerate(case_name):
    if i > 0:
        print ','
    print "'" + cn + "'"
print ']'
