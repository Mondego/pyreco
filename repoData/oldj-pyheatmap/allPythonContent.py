__FILENAME__ = make_test_data
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

import random

def main():

    width = 400
    height = 300

    # 随机生成测试数据
    data = []
    r = 50
    for i in range(4):
        data.append([
            random.randint(0, width - 1),
            random.randint(0, height - 1),
            ])
    for i in xrange(12):
        data2 = []
        for x, y in data:
            x2 = x + random.randint(-r, r)
            y2 = y + random.randint(-r, r)
            data2.append([x2, y2])
        data.extend(data2)
    print(len(data))

    f = open("test_data.txt", "w")
    for x, y in data:
        f.write("%d,%d\n" % (x, y))
    f.close()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

# -*- coding: utf-8 -*-

from pyheatmap.heatmap import HeatMap


def loadDataFromFile(fn):

    lines = open(fn).read().split("\n")
    data = []
    for ln in lines:
        a = ln.split(",")
        if len(a) != 2:
            continue
        a = [int(i) for i in a]
        data.append(a)

    return data


def example2():

    data_1 = loadDataFromFile("test_data.txt")
    data_2 = loadDataFromFile("test_data2.txt")

    hm = HeatMap(data_1)
    hit_img = hm.clickmap()
    hm2 = HeatMap(data_2)
    hit_img2 = hm2.clickmap(base=hit_img, color=(0, 0, 255, 255))
    hit_img2.save("hit2.png")


def example1():

    # 加载测试数据
    data = loadDataFromFile("test_data.txt")

    # 开始绘制
    hm = HeatMap(data)
    hm.clickmap(save_as="hit.png")
    hm.heatmap(save_as="heat.png")


def main():
#    example1()
    example2()


if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = heatmap
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

u"""
pyHeatMap
@link https://github.com/oldj/pyheatmap

"""

import os
import random
import Image
import ImageDraw2
from inc import cf


class HeatMap(object):

    def __init__(self,
                 data,
                 base=None,
                 width=0,
                 height=0
        ):
        u""""""

        assert type(data) in (list, tuple)
        assert base is None or os.path.isfile(base)
        assert type(width) in (int, long, float)
        assert type(height) in (int, long, float)
        assert width >= 0 and height >= 0

        count = 0
        data2 = []
        for hit in data:
            if len(hit) == 3:
                x, y, n = hit
            elif len(hit) == 2:
                x, y, n = hit[0], hit[1], 1
            else:
                raise Exception(u"length of hit is invalid!")

            data2.append((x, y, n))
            count += n

        self.data = data2
        self.count = count
        self.base = base
        self.width = width
        self.height = height

        if not self.base and (self.width == 0 or self.height == 0):
            w, h = cf.getMaxSize(data)
            self.width = self.width or w
            self.height = self.height or h

    def __mkImg(self, base=None):
        u"""生成临时图片"""

        base = base or self.base

        if base:
            self.__im = Image.open(base) if type(base) in (str, unicode) else base
            self.width, self.height = self.__im.size

        else:
            self.__im = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))

    def __paintHit(self, x, y, color):
        u"""绘制点击小叉图片"""

        im = self.__im
        width, height = self.width, self.height
        im.putpixel((x, y), color)

        for i in (1, 2):
            pos = (
                (x + i, y + i),
                (x + i, y - i),
                (x - i, y + i),
                (x - i, y - i),
            )
            for ix, iy in pos:
                if 0 <= ix < width and 0 <= iy < height:
                    im.putpixel((ix, iy), color)

    def clickmap(self, save_as=None, base=None, color=(255, 0, 0, 255), data=None):
        u"""绘制点击图片"""

        self.__mkImg(base)

        data = data or self.data
        for hit in data:
            x, y, n = hit
            if n == 0 or x < 0 or x >= self.width or y < 0 or y >= self.height:
                continue

            self.__paintHit(x, y, color)

        if save_as:
            self.save_as = save_as
            self.__save()

        return self.__im

    def __heat(self, heat_data, x, y, n, template):
        u""""""

        l = len(heat_data)
        width = self.width
        p = width * y + x

        for ip, iv in template:
            p2 = p + ip
            if 0 <= p2 < l:
                heat_data[p2] += iv * n

    def __paintHeat(self, heat_data, colors):
        u""""""

        import re

        im = self.__im
        rr = re.compile(", (\d+)%\)")
        dr = ImageDraw2.ImageDraw.Draw(im)
        width = self.width
        height = self.height

        max_v = max(heat_data)
        if max_v <= 0:
            # 空图片
            return

        r = 240.0 / max_v
        heat_data2 = [int(i * r) - 1 for i in heat_data]

        size = width * height
        for p in xrange(size):
            v = heat_data2[p]
            if v > 0:
                x, y = p % width, p // width
                color = colors[v]
                alpha = int(rr.findall(color)[0])
                if alpha > 50:
                    al = 255 - 255 * (alpha - 50) / 50
                    im.putpixel((x, y), (0, 0, 255, al))
                else:
                    dr.point((x, y), fill=color)

    def sample(self, max_count=None, rate=None):

        count = self.count
        if count == 0:
            return self.data

        if rate and 0 < rate < 1:
            count = int(self.count * rate)
        if max_count and count > max_count:
            count = max_count

        if count == 0 or count >= self.count:
            return self.data

        data = []
        for x, y, n in self.data:
            for i in xrange(n):
                data.append((x, y))

        sample = random.sample(data, count)
        data = {}
        for x, y in sample:
            key = (x, y)
            data[key] = data.get(key, 0) + 1

        data2 = []
        for key in data:
            x, y = key
            data2.append((x, y, data[key]))

        return data2

    def heatmap(self, save_as=None, base=None, data=None):
        u"""绘制热图"""

        self.__mkImg()

        circle = cf.mkCircle(10, self.width)
        heat_data = [0] * self.width * self.height

        data = data or self.data

        for hit in data:
            x, y, n = hit
            if x < 0 or x >= self.width or y < 0 or y >= self.height:
                continue

            self.__heat(heat_data, x, y, n, circle)

        self.__paintHeat(heat_data, cf.mkColors())

        if save_as:
            self.save_as = save_as
            self.__save()

        return self.__im

    def __save(self):

        save_as = os.path.join(os.getcwd(), self.save_as)
        folder, fn = os.path.split(save_as)
        if not os.path.isdir(folder):
            os.makedirs(folder)

        self.__im.save(save_as)
        self.__im = None


def test():
    u"""测试方法"""

    print("load data..")
    data = []
    f = open("../examples/test_data.txt")
    for ln in f:
        a = ln.split(",")
        if len(a) != 2:
            continue
        x, y = int(a[0]), int(a[1])
        data.append([x, y])
    f.close()

    print("painting..")
    # 开始绘制
    hm = HeatMap(data)
    hm.clickmap(save_as="hit.png")
    hm.heatmap(save_as="heat.png")

    print("done.")


if __name__ == "__main__":
    test()

########NEW FILE########
__FILENAME__ = cf
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#


def getMaxSize(data):
    max_w = 0
    max_h = 0

    for hit in data:
        w = hit[0]
        h = hit[1]
        if w > max_w:
            max_w = w
        if h > max_h:
            max_h = h

    return max_w, max_h


def mkCircle(r, w):
    u"""根据半径r以及图片宽度 w ，产生一个圆的list
    @see http://oldj.net/article/bresenham-algorithm/
    """

    #__clist = set()
    __tmp = {}

    def c8(ix, iy, v=1):
        # 8对称性
        ps = (
            (ix, iy),
            (-ix, iy),
            (ix, -iy),
            (-ix, -iy),
            (iy, ix),
            (-iy, ix),
            (iy, -ix),
            (-iy, -ix),
        )
        for x2, y2 in ps:
            p = w * y2 + x2
            __tmp.setdefault(p, v)
            #__clist.add((p, v))

    # 中点圆画法
    x = 0
    y = r
    d = 3 - (r << 1)
    while x <= y:
        for iy in range(x, y + 1):
            c8(x, iy, y + 1 - iy)
        if d < 0:
            d += (x << 2) + 6
        else:
            d += ((x - y) << 2) + 10
            y -= 1
        x += 1

    #__clist = __tmp.items()

    return __tmp.items()


def mkColors(n=240):
    u"""生成色盘
    @see http://oldj.net/article/heat-map-colors/

    TODO: 根据 http://oldj.net/article/hsl-to-rgb/ 将 HSL 转为 RGBA
    """

    colors = []
    n1 = int(n * 0.4)
    n2 = n - n1

    for i in range(n1):
        color = "hsl(240, 100%%, %d%%)" % (100 * (n1 - i / 2) / n1)
        #color = 255 * i / n1
        colors.append(color)
    for i in range(n2):
        color = "hsl(%.0f, 100%%, 50%%)" % (240 * (1.0 - float(i) / n2))
        colors.append(color)

    return colors


########NEW FILE########
