# -*-coding:utf-8-*-

import cv2
import numpy
import numpy as np
import math


# 均值哈希算法
class RecognizeBound:
    def __init__(self):
        self.image_bytes = None
        self.image_bound = None
        pass


def avg_hash(img):
    scale = 32
    # 缩放为8*8
    img = cv2.resize(img, (scale, scale))
    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # s为像素和初值为0，hash_str为hash值初值为''
    s = 0
    hash_str = ''
    # 遍历累加求像素和
    for i in range(scale):
        for j in range(scale):
            s = s + gray[i, j]
    # 求平均灰度
    avg = s / scale * scale
    # 灰度大于平均值为1相反为0生成图片的hash值
    for i in range(scale):
        for j in range(scale):
            if gray[i, j] > avg:
                hash_str = hash_str + '1'
            else:
                hash_str = hash_str + '0'
    return hash_str


# 差值感知算法
def diff_hash(img):
    scale = 32
    # 缩放8*8
    img = cv2.resize(img, (scale + 1, scale))
    # 转换灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hash_str = ''
    # 每行前一个像素大于后一个像素为1，相反为0，生成哈希
    for i in range(scale):
        for j in range(scale):
            if gray[i, j] > gray[i, j + 1]:
                hash_str = hash_str + '1'
            else:
                hash_str = hash_str + '0'
    return hash_str


# 感知哈希算法(pHash)
def perceive_hash(img):
    # 缩放32*32
    img = cv2.resize(img, (32, 32))  # , interpolation=cv2.INTER_CUBIC

    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 将灰度图转为浮点型，再进行dct变换
    dct = cv2.dct(np.float32(gray))
    # opencv实现的掩码操作
    dct_roi = dct[0:8, 0:8]

    hash = []
    avreage = np.mean(dct_roi)
    for i in range(dct_roi.shape[0]):
        for j in range(dct_roi.shape[1]):
            if dct_roi[i, j] > avreage:
                hash.append(1)
            else:
                hash.append(0)
    return hash


# 通过得到RGB每个通道的直方图来计算相似度
def classify_hist_with_split(image1, image2, size=(256, 256)):
    # 将图像resize后，分离为RGB三个通道，再计算每个通道的相似值
    image1 = cv2.resize(image1, size)
    image2 = cv2.resize(image2, size)
    sub_image1 = cv2.split(image1)
    sub_image2 = cv2.split(image2)
    sub_data = 0
    for im1, im2 in zip(sub_image1, sub_image2):
        sub_data += calculate(im1, im2)
    sub_data = sub_data / 3
    return sub_data


# 计算单通道的直方图的相似值
def calculate(image1, image2):
    hist1 = cv2.calcHist([image1], [0], None, [256], [0.0, 255.0])
    hist2 = cv2.calcHist([image2], [0], None, [256], [0.0, 255.0])
    # 计算直方图的重合度
    degree = 0
    for i in range(len(hist1)):
        if hist1[i] != hist2[i]:
            degree = degree + (1 - abs(hist1[i] - hist2[i]) / max(hist1[i], hist2[i]))
        else:
            degree = degree + 1
    degree = degree / len(hist1)
    return degree


# Hash值对比
def cmp_hash(hash1, hash2):
    n = 0
    # hash长度不同则返回-1代表传参出错
    if len(hash1) != len(hash2):
        return -1
    # 遍历判断
    for i in range(len(hash1)):
        # 不相等则n计数+1，n最终为相似度
        if hash1[i] != hash2[i]:
            n = n + 1
    return 1 - (n * 1.0 / len(hash1))


class TargetImage:

    @classmethod
    def convert_image_src(cls, src):
        return '../resources/upload/imgs/{}'.format(src.split('img/')[-1])

    def __init__(self, dic):
        self.src = None
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.resolution_width = None
        self.resolution_height = None
        # 是否降噪
        self.denoise = False
        self.__dict__ = dic

    def get_image_src(self):
        return TargetImage.convert_image_src(self.src)


    def get_bound(self):
        # type: () -> Bound
        bound = Bound()
        bound.x = self.x
        bound.y = self.y
        bound.width = self.width
        bound.height = self.height
        return bound


def bound_of_image_dict(image_dic):
    # type: (dict) -> Bound
    boud = Bound()
    boud.x = image_dic['x']
    boud.y = image_dic['y']
    boud.width = image_dic['width']
    boud.height = image_dic['height']
    return boud


class Bound:

    def __init__(self):
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0
        pass

    def get_area(self):
        return cv2.contourArea(self.get_numpy_array())

    def get_numpy_array(self):
        return numpy.array([
            [int(self.x), int(self.y)],
            [int(self.x + self.width), int(self.y)],
            [int(self.x + self.width), int(self.y + self.height)],
            [int(self.x), int(self.y + self.height)]
        ])

    def get_max_x(self):
        return self.x + self.width

    def get_max_y(self):
        return self.y + self.height

    def has_overlap(self, other):
        # type: (Bound) -> bool

        x01 = self.x
        y01 = self.y

        x02 = self.x + self.width
        y02 = self.y + self.height

        x11 = other.x
        x12 = other.x + other.width
        y11 = other.y
        y12 = other.y + other.height

        overlayW = (x02 - x01) + (x12 - x11) - (max(x02, x12) - min(x01, x11))
        overlayH = (y02 - y01) + (y12 - y11) - (max(y02, y12) - min(y01, y11))

        # zx = abs(x01 + x02 - x11 - x12)
        # x = abs(x01 - x02) + abs(x11 - x12)
        # zy = abs(y01 + y02 - y11 - y12)
        # y = abs(y01 - y02) + abs(y11 - y12)
        # if zx <= x and zy <= y:
        #     return True
        # else:
        #     return False
        return False if overlayW <= 0 or overlayH <= 0 else overlayW * overlayH > 0

    pass


class ContourBound(Bound):

    def __init__(self, cont_id, contour):
        Bound.__init__(self)
        self.point_count = len(contour)
        self.id = cont_id
        self.x, self.y, self.width, self.height = cv2.boundingRect(contour)
        self.parent = None

    def __str__(self):
        return 'id:{},parentId:{}, x:{}, y:{}'.format(self.id, -1 if self.parent is None else self.parent.id, self.x, self.y)


class MatchResult:
    matchBound = None  # type: Bound

    def __init__(self):
        self.possibility = 0
        self.matchBound = None

    pass


# hash值得包装参数，包含了多个hash的值
class ImageHash:

    def __init__(self, img):
        self.diffHash = diff_hash(img)
        self.perceiveHash = perceive_hash(img)
        self.avgHash = avg_hash(img)
        pass

    def compare(self, other):
        # type: (ImageHash) -> float
        res = 0
        avg = cmp_hash(self.avgHash, other.avgHash)
        dif = cmp_hash(self.diffHash, other.diffHash)
        per = cmp_hash(self.perceiveHash, other.perceiveHash)
        print u'图片差值比较', avg, dif, per
        complateCompare = 0.0
        maxComplateCompare = 3.0
        # 如果有一个是1直接返回1，表示图片是一样的
        if avg == 1:
            complateCompare += 0.5
        if dif == 1:
            complateCompare += 1
        if per == 1:
            complateCompare += 1

        res += avg
        res += dif
        res += per
        # 取三个hash的平均值
        percent = res / 3
        percent = (1 - percent) * (complateCompare / maxComplateCompare) + percent
        return percent

    pass


class Recognizer:

    def __init__(self):
        pass

    @classmethod
    def read_template(cls, template):
        if isinstance(template, str):
            np_arr = numpy.fromstring(template, numpy.uint8)
            tpl = cv2.imdecode(np_arr, cv2.COLOR_RGBA2RGB)
            return tpl
        else:
            return template

    u'''
        图片降噪
        参数1：InputArray类型的src，输入图像，填单通道，单8位浮点类型Mat即可。
        参数2：函数运算后的结果存放在这。即为输出图像（与输入图像同样的尺寸和类型）。
        参数3：预设满足条件的最大值。
        参数4：指定自适应阈值算法。可选择ADAPTIVE_THRESH_MEAN_C 或 ADAPTIVE_THRESH_GAUSSIAN_C两种。
        ADAPTIVE_THRESH_MEAN_C，为局部邻域块的平均值。该算法是先求出块中的均值，再减去常数C。
        ADAPTIVE_THRESH_GAUSSIAN_C ，为局部邻域块的高斯加权和。该算法是在区域中（x，y）周围的像素根据高斯函数按照他们离中心点的距离进行加权计算， 再减去常数C。
        参数5：指定阈值类型。可选择THRESH_BINARY或者THRESH_BINARY_INV两种。（即二进制阈值或反二进制阈值）。
        参数6：表示邻域块大小，用来计算区域阈值，一般选择为3、5、7......等。
        参数7：参数C表示与算法有关的参数，它是一个从均值或加权均值提取的常数，可以是负数。
    '''

    @classmethod
    def denoise(cls, img):
        img = cls.read_template(img)
        return cv2.adaptiveThreshold(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                     cv2.THRESH_BINARY, 11, 5)  # 换行符号

    @classmethod
    def match_template_in_bound(cls, target, target_bound, template, bound, denoise):
        # type: (object, Bound, object, Bound, bool) -> MatchResult
        target = cls.read_template(target)
        template = cls.read_template(template)
        matchResult = MatchResult()
        if template is not None:
            if bound is not None:
                template = cls.cut(template, bound)
            else:
                bound = Bound()

            if denoise:
                target = cls.denoise(target)
                template = cls.denoise(template)
                print '2222'

            tar_h, tar_w = target.shape[:2]
            result = cv2.matchTemplate(target, template, cv2.TM_SQDIFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            min_val = math.fabs(min_val)
            matchResult.possibility = 1 - min_val
            matchResult.matchBound = Bound()
            matchResult.matchBound.x = min_loc[0] + bound.x
            matchResult.matchBound.y = min_loc[1] + bound.y
            matchResult.matchBound.width = tar_w
            matchResult.matchBound.height = tar_h
            # 获取找到的目标点和原始预期点的距离
            op = np.array([target_bound.x, target_bound.y])
            rp = np.array([min_loc[0], min_loc[1]])
            pp = rp - op
            dis = math.hypot(pp[0], pp[1])
        return matchResult

    @classmethod
    def cut(cls, pic, bound):
        # type: (object, Bound) -> object
        pic = cls.read_template(pic)
        try:
            return pic[int(bound.y):int(bound.y + bound.height), int(bound.x):int(bound.x + bound.width)]
        except Exception as e:
            print e

    @classmethod
    def mark_bounds2file(cls, pic, bounds, name):
        pic = cls.read_template(pic)
        cnt = []
        for bound in bounds:
            cnt.append(bound.get_numpy_array())
        res = cv2.drawContours(pic, cnt, -1, (0, 0, 255), 2)
        cv2.imwrite('{}.png'.format(name), res)

    @classmethod
    def similarity_of_images(cls, one, other):
        one = cls.read_template(one)
        other = cls.read_template(other)
        return ImageHash(one).compare(ImageHash(other))

    # 计算图片哈希
    @classmethod
    def hash(cls, img):
        # type: (object) -> ImageHash
        img = cls.read_template(img)
        return ImageHash(img)

    pass


class BaseRecognizer(Recognizer):

    def __init__(self, img):
        Recognizer.__init__(self)
        self.targetImage = TargetImage(img)
        self.pic_tar = cv2.imread(self.targetImage.get_image_src(), cv2.COLOR_RGBA2RGB)
        self.tar_h, self.tar_w = self.pic_tar.shape[:2]
        self.tar_area = self.tar_w * self.tar_h

    def match_in_bound(self, template, bound, tag):
        # type: (object, Bound, str) -> MatchResult
        pic_tpl = self.read_template(template)
        matchResult = self.match_template_in_bound(self.pic_tar, self.targetImage.get_bound(), pic_tpl, bound,
                                                   self.targetImage.denoise)
        cv2.rectangle(pic_tpl, (matchResult.matchBound.x, matchResult.matchBound.y),
                      (matchResult.matchBound.get_max_x(), matchResult.matchBound.get_max_y()),
                      (0, 0, 225), 2)
        cv2.imwrite('../resources/upload/imgs/{}.png'.format(tag), pic_tpl)

        return matchResult

    def match_pic(self, template, tag):
        if isinstance(template, RecognizeBound):
            return self.match_in_bound(template.image_bytes, template.image_bound, tag)
        else:
            return self.match_in_bound(template, None, tag)


# 针对列表框架业务的识别器 适用于列表的item有明显外边框的场景
class ListFrameRecognizer(Recognizer):
    # 在图片范围内查找边框
    def __init__(self, list_image, item_image):
        # 列表区域
        Recognizer.__init__(self)
        self.listImage = TargetImage(list_image)
        # item区域
        self.itemImage = TargetImage(item_image)

        self.width_offset = 20
        self.height_offset = 20
        self.pic_tpl = None

    def list_picture(self, tpl):
        cut_bound = Bound()
        cut_bound.x = self.listImage.x
        cut_bound.y = self.listImage.y
        cut_bound.width = self.listImage.width
        cut_bound.height = self.listImage.height
        return self.cut(tpl, cut_bound)

    # 查找到列表区域中的所有的可以点击的item
    def find_item_bounds(self, template=None):
        # type: (object) -> list[ContourBound]
        # 转换成灰度图
        self.pic_tpl = self.read_template(template)
        list_tpl = self.list_picture(self.pic_tpl)
        gray = cv2.cvtColor(list_tpl, cv2.COLOR_RGB2GRAY)

        cv2.imwrite('gray.png', gray)
        # 二值化
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                       cv2.THRESH_BINARY, 11, 2)  # 换行符号

        cv2.imwrite('thresh.png', thresh)
        # 查找轮廓
        # binary-二值化结果，contours-轮廓信息，hierarchy-层级
        binary, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        target_bounds = []
        bounds = []
        cnt = []

        for index, cont in enumerate(contours):
            if len(cont) >= 4:
                contour_bound = ContourBound(index, cont)
                if abs(contour_bound.width - self.itemImage.width) < self.width_offset and abs(
                        contour_bound.height - self.itemImage.height) < self.height_offset:
                    bounds.append(contour_bound)
        bounds.sort(key=lambda bd: (bd.y, bd.x))
        # 去除相交的矩形,取面积较大的矩形
        for i, cont in enumerate(bounds):
            target_bound = None
            for j, other in enumerate(bounds):
                if cont is not other:
                    if cont.has_overlap(other):
                        if cont.get_area() >= other.get_area():
                            bound = cont
                        else:
                            target_bound = other
                            break
                        if target_bound is None or target_bound.get_area() < bound.get_area():
                            target_bound = bound
                    else:  # 没有相交使用当前轮廓
                        target_bound = cont
            if target_bound is cont:
                target_bounds.append(target_bound)
        target_bounds.sort(key=lambda bd: (bd.y, bd.x))
        for bound in target_bounds:
            bound.x += self.listImage.x
            bound.y += self.listImage.y
            cnt.append(bound.get_numpy_array())

        res2 = cv2.drawContours(self.pic_tpl, cnt, -1, (250, 255, 255), 2)
        cv2.imwrite('cnt.png', res2)
        return target_bounds

        # cnt = contours[8]
        # tmp2 = np.zeros(src.shape, np.uint8)
        # res2 = cv2.drawContours(tmp2, cnt, -1, (250, 255, 255), 2)
        # cv2.imwrite('cnt.png', res2)
        #
        # # 轮廓特征
        # # 面积
        # print(cv2.contourArea(cnt))
        # # 周长,第二个参数指定图形是否闭环,如果是则为True, 否则只是一条曲线.
        # print(cv2.arcLength(cnt, True))
        #
        # # 轮廓近似，epsilon数值越小，越近似
        # epsilon = 0.08 * cv2.arcLength(cnt, True)
        # approx = cv2.approxPolyDP(cnt, epsilon, True)
        # tmp2 = np.zeros(src.shape, np.uint8)
        # # 注意，这里approx要加中括号
        # res3 = cv2.drawContours(tmp2, [approx], -1, (250, 250, 255), 1)
        # cv2.imwrite('approx.png', res3)
        #
        # # 外接图形
        # x, y, w, h = cv2.boundingRect(cnt)
        # # 直接在图片上进行绘制，所以一般要将原图复制一份，再进行绘制
        # tmp3 = src.copy()
        # res4 = cv2.rectangle(tmp3, (x, y), (x + w, y + h), (0, 0, 255), 2)
        # cv2.imwrite('tms.png', res4)

        # cv2.waitKey()
        # cv2.destroyAllWindows()

    pass
