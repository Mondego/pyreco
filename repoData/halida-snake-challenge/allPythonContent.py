__FILENAME__ = ailib
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: ailib
提供ai辅助的一些工具
"""
import sys, os
import urllib, httplib 
import time, logging, json, random, uuid, datetime
from datetime import date

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# 方向对应修改的坐标
DIRECT = (
    (-1, 0), (0, -1), (1, 0), (0, 1)
    )

class BaseAI():
    def setmap(self, map):
        pass
    def step(self, info):
        pass

def get_dirs(body):
    """
    输入蛇的body, 计算出对应有效的direction
    >>> get_dirs([[1, 2], [1, 3]])
    [(-1, 0), (0, -1), (1, 0)]
    """
    fx = body[0][0] - body[1][0]
    fy = body[0][1] - body[1][1]
    if fx > 1: fx = -1
    if fx < -1: fx = 1
    if fy > 1: fy = -1
    if fy < -1: fy = 1
    backward = -fx, -fy

    dirs = list(DIRECT)
    try:
        dirs.remove(backward)
    except:
        # in portal or some case, dirs is wrong
        pass
    return dirs

def near(a, b, size):
    ax, ay = a
    bx, by = b
    sw, sh = size
    nearx = (abs(ax-bx) <= 1) or (ax==0 and bx==sw-1) or (ax==sw-1 and bx==0)
    neary = (abs(ay-by) <= 1) or (ay==0 and by==sh-1) or (ay==sh-1 and by==0)
    if nearx and neary:
        return True

def get_next(a, d, size):
    return [(a[0] + d[0] + size[0])%size[0],
            (a[1] + d[1] + size[1])%size[1]
            ]

def get_nexts(n, a, d, size):
    result = []
    while n > 0:
        a = get_next(a, d, size)
        result.append(a)
        n -= 1
    return result

def get_distance(a, b, size):
    ax, ay = a
    bx, by = b
    sw, sh = size

    if ax == bx:
        disx, dirx = 0, 0
    else:
        dxs = [[(bx-ax+sw)%sw, -1],
               [(ax-bx+sw)%sw, +1]]
        disx, dirx = min(dxs)

    if ay == by:
        disy, diry = 0, 0
    else:
        dys = [[(by-ay+sh)%sh, -1],
               [(ay-by+sh)%sh, +1]]
        disy, diry = min(dys)
    
    return (disx, disy), (dirx, diry)

class WebController():
    """
    提供给ai操作的web接口
    """
    def __init__(self, room):
        self.addr = 'game.snakechallenge.org:9999'
        self.room = room
        self.conn = httplib.HTTPConnection(self.addr)

    def op(self, op, data={}):
        """
        发送命令给服务器
        """
        data['op'] = op
        data['room'] = self.room
        # logging.debug('post: %s : %s', op, data)
        self.conn.request("POST", '/cmd',
                          urllib.urlencode(data),
                          {'Content-Type': 'application/x-www-form-urlencoded'})
        result = self.conn.getresponse().read()
        return json.loads(result)

    def snake_op(self, data):
        data['id'] = self.me['id']
        return self.op(data['op'], data)

    def add(self, name, type):
        self.me = self.op("add",
                           dict(name = name,
                                type = type))
        return self.me
    
    def map(self):
        return self.op("map")

    def info(self):
        return self.op("info")

    def turn(self, dir):
        return self.op("turn",
                        dict(id = self.me["id"],
                             round = -1,
                             direction = dir))
    def sub_info(self):
        time.sleep(0.3)
        return self.info()


class ZeroController():
    """
    提供给ai操作的zeromq接口
    """
    def __init__(self, room):
        import zmq
        self.zmq = zmq
        context = zmq.Context()
        self.room = room
        # 用来接受info更新
        self.suber = context.socket(zmq.SUB)
        self.suber.connect('ipc:///tmp/game_puber.ipc')
        self.suber.setsockopt(zmq.SUBSCRIBE, 'room:%d '%room)
        # 用来与服务器交互
        self.oper = context.socket(zmq.REQ)
        self.oper.connect('ipc:///tmp/game_oper.ipc')
        # poller
        self.poller = zmq.Poller()
        self.poller.register(self.suber, zmq.POLLIN)

    def op(self, op, kw=None):
        if not kw: kw = dict()
        kw['op'] = op
        kw['room'] = self.room
        self.oper.send(json.dumps(kw))
        return json.loads(self.oper.recv())

    def snake_op(self, data):
        data['id'] = self.me['id']
        return self.op(data['op'], data)

    def map(self):
        return self.op('map')

    def add(self, name, type):
        self.me = self.op(
            'add', dict(name=name,
                        type=type))
        return self.me

    def info(self):
        return self.op('info')

    def sub_info(self):
        socks = dict(self.poller.poll(timeout=5000))
        if self.suber in socks and socks[self.suber] == self.zmq.POLLIN:
            info = self.suber.recv()
            info = info[info.index(' '):]
            info = json.loads(info)
        else:
            info = self.info()
        return info
    
    def turn(self, d, round=-1):
        return self.op(
            'turn', dict(id=self.me['id'],
                         direction=d,
                         round=round))


def run_ai(ai, controller):
    """
    执行ai
    """
    c = controller
    # 初始化状态
    NEED_ADDING, RUNNING = range(2)
    ai.status = NEED_ADDING
    
    while True:
        time.sleep(0.01)
        # 先获取场上的情况
        if False:#ai.status == NEED_ADDING:
            info = c.info()
        else:
            info = c.sub_info()

        # found me
        names = [s['name'] for s in info['snakes']]
        if ai.name in names:
            me = info['snakes'][names.index(ai.name)]
        else:
            me = None

        # need add to game
        if ai.status == NEED_ADDING:
            # if already added, not add again
            if me: continue
            
            # 游戏结束的时候就不上场了.
            if info['status'] == 'finished':
                logging.debug('finished, waiting for adding..')
                time.sleep(1)
                continue

            # add ai
            result = c.add(ai.name, ai.type)
            if not result.has_key('seq'): # cannot enter?
                continue
            ai.seq = result['seq']
            ai.id = result['id']
            ai.status = RUNNING
            # 告诉ai地图
            m = c.map()
            ai.setmap(m)
            logging.debug("add ai: %d" % ai.seq)
            continue

        if info['status'] == 'finished':
            # 游戏结束的话, 或者发现没有蛇的信息, ai复位..
            ai.status = NEED_ADDING
            # print "not me"
            continue
        if not me: continue

        # 如果自己死掉了, 那就不发出操作
        if not me['alive']:
            logging.debug(ai.name+' is dead.')
            ai.status = NEED_ADDING            
            # print "not alive"
            continue

        # 发出操作
        try:
            d = ai.step(info)
        except Exception as e:
            raise
            logging.debug(str(e))
            ai.status == NEED_ADDING
            continue
        result = c.snake_op(d)

        # 操作失败显示下
        if result['status'] != 'ok':
            logging.debug(result['status'])
        # logging.debug("turn: %d in round: %d", d, info['round'])

def cmd_run(AI):
    usage = """\
    $ %s [connect type] [room number] [ai number]
    connect type is in [web, zero]
        web means use Restful http API,
        zero means use zeromq.
        ai number means how much ai you are running
        """%sys.argv

    try:
        room = int(sys.argv[2])
    except:
        print usage
        
    if sys.argv[1] == 'web':
        C = WebController
    elif sys.argv[1] == 'zero':
        C = ZeroController
    else:
        print usage

    if len(sys.argv) > 3:
        def run():
            run_ai(AI(), C(room))
        import multiprocessing
        ps = [multiprocessing.Process(target=run, args=())
              for i in range(int(sys.argv[3]))]
        for p in ps: p.start()
        for p in ps: p.join()
    else:
        run_ai(AI(), C(room))

def main():
    import doctest
    doctest.testmod()

if __name__=="__main__":
    main()


########NEW FILE########
__FILENAME__ = ai_edward32tnt
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: ai_edward32tnt
"""
from ailib import *

LEFT, UP, RIGHT, DOWN = range(4)
class AI(BaseAI):
    def __init__(self):
        self.name = 'edward32tnt ai %d' % random.randint(1, 1000)
        types = ['python', 'ruby']
        self.type = types[random.randint(0, 1)]

    def setmap(self, map):
        self.map = map

    def get_nearest_bean(self, beans, head):
        bean, distance = None, None
        for b in beans:
            d = abs(head[0] - b[0]) ** 2 + \
                abs(head[1] - b[1]) ** 2
            if not bean or d < distance:
                bean = b
                distance = d
        return bean
        
    def step(self, info):
        """
        caculate next direction by use rating
        """
        self.info = info
        result =  self.cmd_turn()
        return result

############ 取得地图信息

    # 猜测敌人头附近的问题    
    def set_guess_posion(self):
        res = []
        for snake in self.info['snakes']:
            if self.head != snake['body'][0]:
                for point in self.get_around(snake['body'][0]):
                    res.append(point)
        return res       

            
    def set_others(self):
        self.other_head = []
        res = []
        for snake in self.info['snakes']:
            for body in snake['body']:
                res.append(body)
            if self.head != snake['body'][0]:
                self.other_head.append(snake['body'][0])
        return res
    
    def set_walls(self):
        res = []
        for w in self.map['walls']:
            res.append(w)
        return res
    
    def set_food(self):
        res = []
        if self.type == 'python':
            food = 'eggs'
        else:
            food = 'gems'
        for e in self.info[food]:
            if [x for x in self.get_around(e, steps=2) if x in self.other_head]: continue
            res.append(e)
        return res
    
    def set_posion(self):
        res = []
        if self.type != 'python':
            posion = 'eggs'
        else:
            posion = 'gems'
        for g in self.info[posion]:
            res.append(g)
        return res

    ###########    

    def cmd_turn(self):
        """
        控制蛇方向
        """
        direction = None
        self.head = self.info['snakes'][self.seq]['body'][0]
        others = self.set_others()
        walls = self.set_walls()
        food = self.set_food()
        posion = self.set_posion()
        guess_posion = self.set_guess_posion()

        mapx, mapy = self.map['size']
        startpoint = self.head


        # 第一次尝试绝对安全路线。
        # 如果没有路线，则尝试不安全路线。
        next = self.find_safe_path(startpoint, food, others, walls, posion, guess_posion)
        if next:
            direction = self.find_next_direction_by_point(self.head, next)
        else:
            next = self.find_no_safe_path(startpoint, food, others, walls)
            if next:
                direction = self.find_next_direction_by_point(self.head, next)
        #print mapdata[-mapx:]
        #print mapdata[-mapx:]
        #print mapw
        #print maph
        #print startpoint
        #print endpoint
            
        # 再没有路线则朝尾部方向寻找
        if direction is None:
            # 暂时先寻找自己尾部的方向移动拜托被围的问题
            if not food: 
                direction = random.randint(0, 3)
            else:
                direction = self.find_next_direction_by_point(self.head, self.info['snakes'][self.me['seq']]['body'][-1])
        return direction

################# 工具类可以转移出去
    def find_safe_path(self, startpoint, food, others, walls, posion, guess_posion):
        return self._get_path(startpoint, food, others, walls, posion, guess_posion)

    def find_no_safe_path(self, startpoint, food, others, walls):
        return self._get_path(startpoint, food, others, walls)
        
    def _get_path(self, startpoint, food, others, walls, posion=[], guess_posion=[]):
        counts = 0
        next = None
        for e in food:
            endpoint = e
            mapdata = []
            for y in range(self.map['size'][1]):
                for x in range(self.map['size'][0]):
                    rc = [x, y]
                    if rc == self.head:
                        mapdata.append(5)
                        continue
                    if rc == endpoint:
                        mapdata.append(6)
                        continue
                    if rc in others or rc in walls or rc in posion or rc in guess_posion:
                        mapdata.append(-1)
                        continue
                    mapdata.append(1)

            astar = AStar(SQ_MapHandler(mapdata, self.map['size'][0], self.map['size'][1]))
            start = SQ_Location(startpoint[0], startpoint[1])
            end = SQ_Location(endpoint[0], endpoint[1])
            
            p = astar.findPath(start, end)
            if not p:continue
            if len(p.nodes) < counts or next == None:
                counts = len(p.nodes)
                next = [p.nodes[0].location.x , p.nodes[0].location.y]
        return next 

    def find_next_direction_by_point(self, point, next):
        if point[0] < next[0]: return RIGHT
        if point[0] > next[0]: return LEFT
        if point[1] > next[1]: return UP
        if point[1] < next[1]: return DOWN

    def find_next_point_by_direction(self, point, direction, step):
        if direction == LEFT: return [point[0] - step, point[1]]
        if direction == RIGHT: return [point[0] + step, point[1]]
        if direction == UP: return [point[0], point[1] - step]
        if direction == DOWN: return [point[0], point[1] + step]
        
    def get_around(self, point, steps=1):
        for step in range(steps):
            for d in (LEFT, UP, RIGHT, DOWN):
                yield self.find_next_point_by_direction(point, d, step+1)

##############        ############


# Version 1.1
#
# Changes in 1.1: 
# In order to optimize the list handling I implemented the location id (lid) attribute.
# This will make the all list serahces to become extremely more optimized.

class Path:
    def __init__(self,nodes, totalCost):
        self.nodes = nodes;
        self.totalCost = totalCost;

    def getNodes(self): 
        return self.nodes    

    def getTotalMoveCost(self):
        return self.totalCost

class Node:
    def __init__(self,location,mCost,lid,parent=None):
        self.location = location # where is this node located
        self.mCost = mCost # total move cost to reach this node
        self.parent = parent # parent node
        self.score = 0 # calculated score for this node
        self.lid = lid # set the location id - unique for each location in the map

    def __eq__(self, n):
        if n.lid == self.lid:
            return 1
        else:
            return 0


class AStar:

    def __init__(self,maphandler):
        self.mh = maphandler
                
    def _getBestOpenNode(self):
        bestNode = None        
        for n in self.on:
            if not bestNode:
                bestNode = n
            else:
                if n.score<=bestNode.score:
                    bestNode = n
        return bestNode

    def _tracePath(self,n):
        nodes = [];
        totalCost = n.mCost;
        p = n.parent;
        nodes.insert(0,n);       
        
        while 1:
            if p.parent is None: 
                break

            nodes.insert(0,p)
            p=p.parent
        
        return Path(nodes,totalCost)

    def _handleNode(self,node,end):        
        i = self.o.index(node.lid)
        self.on.pop(i)
        self.o.pop(i)
        self.c.append(node.lid)

        nodes = self.mh.getAdjacentNodes(node,end)
                   
        for n in nodes:
            if n.location.x % self.mh.w == end.x and n.location.y % self.mh.h == end.y:
                # reached the destination
                return n
            elif n.lid in self.c:
                # already in close, skip this
                continue
            elif n.lid in self.o:
                # already in open, check if better score
                i = self.o.index(n.lid)
                on = self.on[i];
                if n.mCost<on.mCost:
                    self.on.pop(i);
                    self.o.pop(i);
                    self.on.append(n);
                    self.o.append(n.lid);
            else:
                # new node, append to open list
                self.on.append(n);                
                self.o.append(n.lid);

        return None

    def findPath(self,fromlocation, tolocation):
        self.o = []
        self.on = []
        self.c = []

        end = tolocation
        fnode = self.mh.getNode(fromlocation)
        self.on.append(fnode)
        self.o.append(fnode.lid)
        nextNode = fnode 
               
        while nextNode is not None: 
            finish = self._handleNode(nextNode,end)
            if finish:                
                return self._tracePath(finish)
            nextNode=self._getBestOpenNode()
                
        return None
      
class SQ_Location:
    """A simple Square Map Location implementation"""
    def __init__(self,x,y):
        self.x = x
        self.y = y

    def __eq__(self, l):
        """MUST BE IMPLEMENTED"""
        if l.x == self.x and l.y == self.y:
            return 1
        else:
            return 0

class SQ_MapHandler:
    """A simple Square Map implementation"""

    def __init__(self,mapdata,width,height):
        self.m = mapdata
        self.w = width
        self.h = height

    def getNode(self, location):
        """MUST BE IMPLEMENTED"""
        x = location.x
        y = location.y
        if x<0 or x>=self.w or y<0 or y>=self.h:
            #return None
            x = x % self.w
            y = y % self.h
            
        d = self.m[(y*self.w)+x]
        if d == -1:
            return None

        return Node(location,d,((y*self.w)+x));                

    def getAdjacentNodes(self, curnode, dest):
        """MUST BE IMPLEMENTED"""        
        result = []
       
        cl = curnode.location
        dl = dest
        
        n = self._handleNode(cl.x+1,cl.y,curnode,dl.x,dl.y)
        if n: result.append(n)
        n = self._handleNode(cl.x-1,cl.y,curnode,dl.x,dl.y)
        if n: result.append(n)
        n = self._handleNode(cl.x,cl.y+1,curnode,dl.x,dl.y)
        if n: result.append(n)
        n = self._handleNode(cl.x,cl.y-1,curnode,dl.x,dl.y)
        if n: result.append(n)
                
        return result

    def _handleNode(self,x,y,fromnode,destx,desty):
        n = self.getNode(SQ_Location(x,y))
        if n is not None:
            dx = min(abs(x - destx), self.w - abs(x-destx))
            dy = min(abs(y - desty), self.h - abs(y-desty))
            emCost = dx+dy
            n.mCost += fromnode.mCost                                   
            n.score = n.mCost+emCost
            n.parent=fromnode
            return n

        return None    
        

if __name__=="__main__":
    cmd_run(AI)

########NEW FILE########
__FILENAME__ = ai_halida
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: ai simple
a simple ai demo
"""
from ailib import *

class AI(BaseAI):
    def __init__(self):
        self.name = 'simple ai %d' % random.randint(1, 1000)
        types = ['python', 'ruby']
        self.type = types[random.randint(0, 1)]
        self.SPRINT = random.random() > 0.5
        self.count = 0
        self.round = -1

    def setmap(self, map):
        self.map = map

    def get_nearest_bean(self, beans, h, size):
        r_bean, r_dis, r_dir = None, None, None
        
        for b in beans:
            dis, dir = get_distance(b, h, size)
            
            if not r_bean or dis < r_dis:
                r_bean = b
                r_dis = dis
                r_dir = dir
                
        return r_bean, r_dir

    def check_hit(self, next):
        # it is bad to hit a wall
        if next in self.map['walls']:
            return True
        # also bad to hit another snake
        for s in self.info['snakes']:
            if next in s['body']:
                return True

    def step(self, info):
        """
        caculate next direction by use rating
        -10: wall, or hit
        x+1, y+1: target bean direction
        -1: not target bean 
        """
        self.info = info
        size = self.map['size']
        self_snake = info['snakes'][self.seq]
        head = self_snake['body'][0]
        w, h = self.map['size']
        dirs = get_dirs(self_snake['body'])

        # not check when cannot move
        if self_snake['sprint'] < 0:
            return {'op': 'turn', 'direction': 0}
        
        if self.type == 'python':
            target_beans, nontarget_beans = info['eggs'], info['gems']
        else:
            target_beans, nontarget_beans = info['gems'], info['eggs']
            
        # find the nearest bean, and target direction
        nearest_bean, bean_direction = self.get_nearest_bean(target_beans, head, size)

        # rating for each direction
        ratings = [0, ] * len(dirs)
        
        # sprint when torgeting bean and nears!
        if ( self.SPRINT and
             nearest_bean and 
             ((head[0] == nearest_bean[0] and self_snake['direction'] in (1, 3) and abs(head[1] - nearest_bean[1]) < 15) or
              (head[1] == nearest_bean[1] and self_snake['direction'] in (0, 2) and abs(head[0] - nearest_bean[0]) < 15)
              ) and
             not any([self.check_hit(n)
                      for n in get_nexts(6, head, DIRECT[self_snake['direction']], size)])
             ):
            # print get_nexts(6, head, d, size)
            # print [self.check_hit(n)
            #        for n in get_nexts(6, head, DIRECT[self_snake['direction']], size)]
            return {'op': 'sprint'}
                
        for i, d in enumerate(dirs):
            # it is good if targeting a bean
            if nearest_bean:
                if d[0] == bean_direction[0]: ratings[i] += 2
                if d[1] == bean_direction[1]: ratings[i] += 2

            # find next positon
            next = get_next(head, d, size)

            # it is bad to hit a target
            if self.check_hit(next):
                ratings[i] = -10
                continue

            # sprint check!
            if (self_snake['sprint'] > 1 and
                any([self.check_hit(n)
                     for n in get_nexts(2, next, d, size)])):
                print get_nexts(6, head, d, size)
                print [self.check_hit(n)
                       for n in get_nexts(6, head, d, size)]
                ratings[i] = -10
                continue

            # bad to near other snakes head
            for s in info['snakes']:
                if s == self_snake: continue
                if near(next, s['body'][0], size):
                    ratings[i] = -2
                    continue

            # bad to eat other types of bean
            if next in nontarget_beans: ratings[i] -= 2

            # bad to near too many walls
            # near_walls = sum([near(next, w, size)
            #                   for w in self.map['walls']])
            # ratings[i] -= near_walls

        # return the best direction
        d = max(zip(ratings, dirs), key=lambda x: x[0])[1]
        return {'op': 'turn', 'direction': DIRECT.index(d)}

    
if __name__=="__main__":
    cmd_run(AI)

########NEW FILE########
__FILENAME__ = AStar
# Version 1.1
#
# Changes in 1.1: 
# In order to optimize the list handling I implemented the location id (lid) attribute.
# This will make the all list serahces to become extremely more optimized.

class Path:
    def __init__(self,nodes, totalCost):
        self.nodes = nodes;
        self.totalCost = totalCost;

    def getNodes(self): 
        return self.nodes    

    def getTotalMoveCost(self):
        return self.totalCost

class Node:
    def __init__(self,location,mCost,lid,parent=None):
        self.location = location # where is this node located
        self.mCost = mCost # total move cost to reach this node
        self.parent = parent # parent node
        self.score = 0 # calculated score for this node
        self.lid = lid # set the location id - unique for each location in the map

    def __eq__(self, n):
        if n.lid == self.lid:
            return 1
        else:
            return 0

class AStar:

    def __init__(self,maphandler):
        self.mh = maphandler
                
    def _getBestOpenNode(self):
        bestNode = None        
        for n in self.on:
            if not bestNode:
                bestNode = n
            else:
                if n.score<=bestNode.score:
                    bestNode = n
        return bestNode

    def _tracePath(self,n):
        nodes = [];
        totalCost = n.mCost;
        p = n.parent;
        nodes.insert(0,n);       
        
        while 1:
            if p.parent is None: 
                break

            nodes.insert(0,p)
            p=p.parent
        
        return Path(nodes,totalCost)

    def _handleNode(self,node,end):        
        i = self.o.index(node.lid)
        self.on.pop(i)
        self.o.pop(i)
        self.c.append(node.lid)

        nodes = self.mh.getAdjacentNodes(node,end)
                   
        for n in nodes:
            if n.location.x % self.mh.w == end.x and n.location.y % self.mh.h == end.y:
                # reached the destination
                return n
            elif n.lid in self.c:
                # already in close, skip this
                continue
            elif n.lid in self.o:
                # already in open, check if better score
                i = self.o.index(n.lid)
                on = self.on[i];
                if n.mCost<on.mCost:
                    self.on.pop(i);
                    self.o.pop(i);
                    self.on.append(n);
                    self.o.append(n.lid);
            else:
                # new node, append to open list
                self.on.append(n);                
                self.o.append(n.lid);

        return None

    def findPath(self,fromlocation, tolocation):
        self.o = []
        self.on = []
        self.c = []

        end = tolocation
        fnode = self.mh.getNode(fromlocation)
        self.on.append(fnode)
        self.o.append(fnode.lid)
        nextNode = fnode 
               
        while nextNode is not None: 
            finish = self._handleNode(nextNode,end)
            if finish:                
                return self._tracePath(finish)
            nextNode=self._getBestOpenNode()
                
        return None
      
class SQ_Location:
    """A simple Square Map Location implementation"""
    def __init__(self,x,y):
        self.x = x
        self.y = y

    def __eq__(self, l):
        """MUST BE IMPLEMENTED"""
        if l.x == self.x and l.y == self.y:
            return 1
        else:
            return 0

class SQ_MapHandler:
    """A simple Square Map implementation"""

    def __init__(self,mapdata,width,height):
        self.m = mapdata
        self.w = width
        self.h = height

    def getNode(self, location):
        """MUST BE IMPLEMENTED"""
        x = location.x
        y = location.y
        if x<0 or x>=self.w or y<0 or y>=self.h:
            #return None
            x = x % self.w
            y = y % self.h
            
        d = self.m[(y*self.w)+x]
        if d == -1:
            return None

        return Node(location,d,((y*self.w)+x));                

    def getAdjacentNodes(self, curnode, dest):
        """MUST BE IMPLEMENTED"""        
        result = []
       
        cl = curnode.location
        dl = dest
        
        n = self._handleNode(cl.x+1,cl.y,curnode,dl.x,dl.y)
        if n: result.append(n)
        n = self._handleNode(cl.x-1,cl.y,curnode,dl.x,dl.y)
        if n: result.append(n)
        n = self._handleNode(cl.x,cl.y+1,curnode,dl.x,dl.y)
        if n: result.append(n)
        n = self._handleNode(cl.x,cl.y-1,curnode,dl.x,dl.y)
        if n: result.append(n)
                
        return result

    def _handleNode(self,x,y,fromnode,destx,desty):
        n = self.getNode(SQ_Location(x,y))
        if n is not None:
            dx = min(abs(x - destx), self.w - abs(x-destx))
            dy = min(abs(y - desty), self.h - abs(y-desty))
            emCost = dx+dy
            n.mCost += fromnode.mCost                                   
            n.score = n.mCost+emCost
            n.parent=fromnode
            return n

        return None    

########NEW FILE########
__FILENAME__ = astarsnake
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: random snake
用来作为示例代码
"""
import json, time, random, sys
import urllib, httplib
from AStar import AStar, SQ_MapHandler, SQ_Location

LEFT, UP, RIGHT, DOWN = range(4)
class RandomSnake():
    def __init__(self, room=0, mytype='python'):
        # 建立web连接
        self.conn = httplib.HTTPConnection('pythonvsruby.org')#"192.168.1.106")#"localhost:4567") 
        #self.conn = httplib.HTTPConnection("192.168.1.106")
	self.room = room
	self.mytype = mytype

    def post(self, cmd, data):
        """
        发送命令给服务器
        """
        self.conn.request("POST", '/room/%s/%s' % (self.room, cmd),
                          urllib.urlencode(data))
        result = self.conn.getresponse().read()
        return json.loads(result)

    def get(self, cmd):
        """
        获取信息
        """
        self.conn.request("GET", '/room/%s/%s' % (self.room, cmd))
        result = self.conn.getresponse().read()
        return json.loads(result)
    
    def cmd_add(self):
        """
        添加新的蛇
        """
        result = self.post("add",
                           dict(name = "astar test",
                                type = self.mytype))
        self.me, self.info = result[0], result[1]
        return self.me, self.info

############ 取得地图信息

    # 猜测敌人头附近的问题    
    def set_guess_posion(self):
        res = []
        for snake in self.info['snakes']:
            if self.head != snake['body'][0]:
                for point in self.get_around(snake['body'][0]):
                    res.append(point)
        return res       

            
    def set_others(self):
        self.other_head = []
        res = []
        for snake in self.info['snakes']:
            for body in snake['body']:
                res.append(body)
            if self.head != snake['body'][0]:
                self.other_head.append(snake['body'][0])
        return res
    
    def set_walls(self):
        self.cmd_map()
        res = []
        for w in self.map['walls']:
            res.append(w)
        return res
    
    def set_food(self):
        res = []
        if self.mytype == 'python':
            food = 'eggs'
        else:
            food = 'gems'
        for e in self.info[food]:
            if [x for x in self.get_around(e, steps=2) if x in self.other_head]: continue
            res.append(e)
        return res
    
    def set_posion(self):
        res = []
        if self.mytype != 'python':
            posion = 'eggs'
        else:
            posion = 'gems'
        for g in self.info[posion]:
            res.append(g)
        return res

    ###########    

    
    def cmd_turn(self):
        """
        控制蛇方向
        """
        direction = None
        self.head = self.info['snakes'][self.me['seq']]['body'][0]
        others = self.set_others()
        walls = self.set_walls()
        food = self.set_food()
        posion = self.set_posion()
        guess_posion = self.set_guess_posion()

        mapx, mapy = self.map['size']
        startpoint = self.head


        # 第一次尝试绝对安全路线。
        # 如果没有路线，则尝试不安全路线。
        next = self.find_safe_path(startpoint, food, others, walls, posion, guess_posion)
        if next:
            direction = self.find_next_direction_by_point(self.head, next)
        else:
            next = self.find_no_safe_path(startpoint, food, others, walls)
            if next:
                direction = self.find_next_direction_by_point(self.head, next)
        #print mapdata[-mapx:]
        #print mapdata[-mapx:]
        #print mapw
        #print maph
        #print startpoint
        #print endpoint
            
        # 再没有路线则朝尾部方向寻找
        if direction is None:
            # 暂时先寻找自己尾部的方向移动拜托被围的问题
            if not food: 
                direction = random.randint(0, 3)
            else:
                direction = self.find_next_direction_by_point(self.head, self.info['snakes'][self.me['seq']]['body'][-1])
        result = self.post("turn",
                           dict(id = self.me["id"],
                                round = self.info["round"],
                                direction = direction))
        self.turn, self.info = result[0], result[1]

################# 工具类可以转移出去
    def find_safe_path(self, startpoint, food, others, walls, posion, guess_posion):
        return self._get_path(startpoint, food, others, walls, posion, guess_posion)

    def find_no_safe_path(self, startpoint, food, others, walls):
        return self._get_path(startpoint, food, others, walls)
        
    def _get_path(self, startpoint, food, others, walls, posion=[], guess_posion=[]):
        counts = 0
        next = None
        for e in food:
            endpoint = e
            mapdata = []
            for y in range(self.map['size'][1]):
                for x in range(self.map['size'][0]):
                    rc = [x, y]
                    if rc == self.head:
                        mapdata.append(5)
                        continue
                    if rc == endpoint:
                        mapdata.append(6)
                        continue
                    if rc in others or rc in walls or rc in posion or rc in guess_posion:
                        mapdata.append(-1)
                        continue
                    mapdata.append(1)

            astar = AStar(SQ_MapHandler(mapdata, self.map['size'][0], self.map['size'][1]))
            start = SQ_Location(startpoint[0], startpoint[1])
            end = SQ_Location(endpoint[0], endpoint[1])
            
            p = astar.findPath(start, end)
            if not p:continue
            if len(p.nodes) < counts or next == None:
                counts = len(p.nodes)
                next = [p.nodes[0].location.x , p.nodes[0].location.y]
        return next 

    def find_next_direction_by_point(self, point, next):
        if point[0] < next[0]: return RIGHT
        if point[0] > next[0]: return LEFT
        if point[1] > next[1]: return UP
        if point[1] < next[1]: return DOWN

    def find_next_point_by_direction(self, point, direction, step):
        if direction == LEFT: return [point[0] - step, point[1]]
        if direction == RIGHT: return [point[0] + step, point[1]]
        if direction == UP: return [point[0], point[1] - step]
        if direction == DOWN: return [point[0], point[1] + step]
        
    def get_around(self, point, steps=1):
        for step in range(steps):
            for d in (LEFT, UP, RIGHT, DOWN):
                yield self.find_next_point_by_direction(point, d, step+1)

##############        ############

            
    def cmd_map(self):
        """
        获取地图信息
        """
        self.map = self.get("map")

    def cmd_info(self):
        """
        获取实时场景信息
        """
        self.info = self.get("info")

def main(argv):
    room = '0'
    snake_type = 'python'
    if len(argv) > 2:
        room = argv[1]
        snake_type = argv[2]
    
    rs = RandomSnake(room=room, mytype=snake_type)

    rs.cmd_add()
    while True:
        rs.cmd_turn()
    
if __name__=="__main__":
    main(sys.argv)



########NEW FILE########
__FILENAME__ = player
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: player
to run this player, use client.py for web or zmqclient.py for pygame mode
usage: python client.py ray.player <room> <ignore exception> <debug mode>
sample: 
1 python client.py ray.player 0 debug       # start player in room 0 in debug mode
2 python client.py ray.player 1 exception   # start player in room 1 in no-debug 
    and ignore exceptions mode
3 python client.py ray.player               # start player in room default room 0, no-debug,
    and allow exception thrown

"""
import random, os
import Image, ImageColor

class Player():
    offset = [(-1,0), (0,-1), (1,0), (0,1)]
    direction = {(-1,0):0, (0,-1):1, (1,0):2, (0,1):3}
    EMPTY, WALL, EGG, GEM, SNAKE = 0, 100, 40, 70, 10
    TYPE = [{'type':'python', 'bean':'eggs', 'beanw':EGG, 'opbean':'gems', 'opbeanw':GEM}, \
            {'type':'ruby', 'bean':'gems', 'beanw':GEM, 'opbean':'eggs', 'opbeanw':EGG}]
    TMP = 'ray/tmp'

    def __init__(self, debug=False):
        self.name = 'Ray Ling'
        self.typec = self.TYPE[0]
        self.type = self.typec['type']
        self.dead = []
        self.debug = debug
    
    def init(self, seq, map):
        self.seq = seq
        self.size = map['size']
        self.analmap = self.initmap(0)
        self.realmap = self.initmap(self.EMPTY)
        self.addwall(map['walls'], self.realmap, self.analmap) 
        # debug map
        if self.debug:
            if not os.path.exists(self.TMP):
                os.mkdir(self.TMP)
            #self.map2image(self.analmap, 'analmap', 100)
            self.map2image(self.realmap, 'realmap', 100)
        
    def turn(self, info):
        realmap, map = self.analyseMap(info)
        me = info['snakes'][self.seq]['body']
        ret = self.possible(me, realmap, info)
        #print "my length %s"%len(me)
        
        #debug info
        if self.debug:
            #self.info2txt(info,'info_%s'%info['round'])
            pass
        #print "ret %s" % ret
        
        path = self.analyseBean(info, realmap)
        
        if len(path) > 0:
            bestpath, bestv = None, (0,1000)
            for pk,pv in path.items():
                if bestv[0]<pv[0] and (bestv[0]-bestv[1])<=(pv[0]-pv[1]):
                    bestpath = pk
            dir = self.direction[self.sub(bestpath, me[0])]
            if dir in ret:
                return dir
        
        for r in ret[:]:
            pt = self.move(me[0], self.offset[r])
            if self.mapget(realmap, pt) == self.typec['opbeanw']:
                ret.remove(r)
            
        """
        find best ranked direction
        """
        #print "calculate rank: %s"%ret
        bestr, bestv = random.randint(0,3), 100000
        
        for r in ret:
            tpt = self.move(me[0], self.offset[r])
            v = 0
            for x in range(self.size[0]):
                for y in range(self.size[1]):
                    if x!=me[0][0] and y!=me[0][1]:
                        dist = self.mandist((x,y), tpt)
                        v += map[x][y] / (dist * dist)
            if v < bestv:
                bestr, bestv = r, v
            #print "dir %s - value %s"%(r,v)
        #print "select %s"%bestr
        return bestr
    
    def possible(self, me, realmap, info):        
        dir = [0, 1, 2, 3]        
        dir.remove(self.direction[self.sub(me[1], me[0])])
        
        for d in dir[:]:
            pt = self.move(me[0], self.offset[d])
            if self.mapget(realmap, pt) != self.EMPTY and \
                self.mapget(realmap, pt) != self.typec['beanw'] and \
                not (len(me)>7 and self.mapget(realmap, pt) == self.typec['opbeanw']):
                dir.remove(d)
                continue
            if len(dir)>0:
                for snake in info['snakes']:
                    body = snake['body']
                    if body == me: continue
                    if self.mandist(body[0], pt) == 1:
                        dir.remove(d)
                        break        
        return dir
        
    """
    analyse map
    """
    def analyseMap(self, info):
        map = self.mapcopy(self.analmap)
        realmap = self.mapcopy(self.realmap)
        
        for pt in info[self.typec['bean']]:
            self.radia(map, pt, -60, 2)
            self.mapset(realmap, pt, self.typec['beanw'])
        
        for pt in info[self.typec['opbean']]:
            self.radia(map, pt, 40, 2)
            self.mapset(realmap, pt, self.typec['opbeanw'])
            
        for id in range(len(info['snakes'])):
            if id in self.dead: continue
            snake = info['snakes'][id]
            if id != self.seq:
                if snake['alive']:
                    danger = 80
                    for pt in snake['body']:
                        self.radia(map, pt, danger, 2)
                        self.mapset(realmap, pt, self.SNAKE + id)
                        danger = max(0, danger-2)
                else:
                    self.dead.append(id)
                    self.addwall(snake['body'], self.realmap, self.analmap)
                    self.addwall(snake['body'], realmap, map)                    
            else:
                danger = 60
                for pt in snake['body']:
                    self.radia(map, pt, danger, 2)
                    self.mapset(realmap, pt, self.SNAKE + id)
                    danger = max(0, danger-2)
        
        if self.debug:
            self.map2image(realmap, 'realmap_%s'%info['round'], 100)
            self.map2image(map, 'analmap_%s'%info['round'], 300)
            pass
        return (realmap, map)
        
    """
    analyse beans
    """
    def analyseBean(self, info, realmap):        
        bfsmap, eat = [], []
        for snake in info['snakes']:
            if snake['type'] == self.type:
                bmap = self.bfs(realmap, snake['body'][0])
                bfsmap.append(bmap)
                toeat, mindist = [], self.size[0]*self.size[1]
                for bean in info[self.typec['bean']]:
                    v = self.mapget(bmap, bean)
                    if v<mindist:
                        toeat = [tuple(bean)]
                        mindist = v
                    elif v == mindist:
                        toeat.append(tuple(bean))
                eat.append((toeat,mindist))
            else:
                bfsmap.append(None)
                eat.append(([],0))
        
        opbfsmap = self.bfs(realmap, info['snakes'][self.seq]['body'][0], True)
        
        #print "eat:%s"%eat
        mine = {}
        for bean in info[self.typec['bean']]:
            mine[tuple(bean)] = self.mapget(bfsmap[self.seq], bean)
        
        #print 'before remove: %s'%mine
        for bs,v in eat: 
            for b in bs:
                if b in mine.keys() and mine[b] > v: 
                    opv = self.mapget(opbfsmap, b)
                    if opv < v and len(info['snakes'][self.seq]['body'])>10:
                        # even it cost a op bean, just go through
                        mine[b] = opv
                    else:
                        del mine[b]        
        #print 'after remove: %s'%mine
        
        for bean,dist in mine.items():
            bmap = self.bfs(realmap, bean)
            weight, blen = 0.0, len(info[self.typec['bean']])
            for obean in info[self.typec['bean']]:
                if tuple(obean) != bean:
                    weight += self.mapget(bmap, obean) * 1.0 / blen
                    blen -= 1
            mine[bean] = (dist, weight)
        
        #print 'mine %s'%mine
        
        cpath, weight = {}, 10000
        for bean,wt in mine.items():
            bwt = wt[0] #* 1.5 + wt[1]*0.5
            if bwt < weight:
                if self.mapget(bfsmap[self.seq], bean) == wt[0]:
                    cpath = self.path(bfsmap[self.seq], realmap, bean)
                else:
                    cpath = self.path(opbfsmap, realmap, bean)
                weight = bwt
        
        #print cpath
        return cpath
    
    """ 
    utilities 
    """
    def initmap(self, fill):
        return [[fill] * self.size[1] \
            for i in range(self.size[0])]
    
    def addwall(self, walls, realmap, map):
        for pt in walls:
            self.mapset(realmap, pt, self.WALL)
            self.radia(map, pt, 60, 4)
        moreWall = True
        while moreWall:
            moreWall = False
            for x in range(self.size[0]):
                for y in range(self.size[1]):
                    walls = 0
                    for oft in self.offset:
                        pt = self.move((x,y), oft)
                        if self.mapget(realmap, pt) == self.WALL:
                            walls += 1
                    if walls > 2 and self.mapget(realmap, (x,y)) != self.WALL:
                        self.mapset(realmap, (x,y), self.WALL)
                        moreWall = True
            
    
    def radia(self, map, pt, danger, factor):
        self.mapset(map, pt, danger)
        danger /= factor
        n = 1
        while abs(danger) > 1:
            for i in range(-n, n):
                self.mapadd(map, self.move(pt, (i, -n)), danger)
                self.mapadd(map, self.move(pt, (i, n)), danger)
                self.mapadd(map, self.move(pt, (-n, i)), danger)
                self.mapadd(map, self.move(pt, (n, i)), danger)
                
            danger /= factor
            n += 1
            
    def move(self, pt, oft, scale=1):
        return (((pt[0] + oft[0]*scale + self.size[0]) % self.size[0]) \
            , (pt[1] + oft[1]*scale + self.size[1]) % self.size[1])
        
    def mapget(self, map, pt):
        return map[pt[0]][pt[1]]
        
    def mapset(self, map, pt, v):
        map[pt[0]][pt[1]] = v
    
    def mapadd(self, map, pt, add):
        map[pt[0]][pt[1]] += add
    
    def mapcopy(self, map):
        ret = []
        for a in map:
            row = []
            for i in a:
                row.append(i)
            ret.append(row)
        return ret
        
    def mincord(self, pt1, pt2, cord):
        min1 = pt1[cord] - pt2[cord]
        min2 = pt1[cord] + self.size[cord] - pt2[cord]
        min3 = pt1[cord] - self.size[cord] - pt2[cord]
        if abs(min1) < abs(min2) and abs(min1) < abs(min3):
            min = min1
        elif abs(min2) < abs(min3):
            min = min2
        else:
            min = min3
        return min
    
    def sub(self, pt1, pt2):
        return (self.mincord(pt1,pt2,0), self.mincord(pt1,pt2,1))
    
    def mandist(self, pt1, pt2):
        return (abs(pt1[0]-pt2[0])+abs(pt1[1]-pt2[1]))
    
    def bfs(self, realmap, pt, op=False):        
        vmap = self.initmap(self.size[0] + self.size[1])      
        queue = [pt]
        self.mapset(vmap, pt, 0)
        while len(queue)>0:
            tp = queue.pop(0)
            tv = self.mapget(vmap, tp)
            for oft in self.offset:
                np = self.move(tp, oft)
                type = self.mapget(realmap, np)
                if (type == self.EMPTY or \
                    type == self.typec['beanw'] or \
                    (op and type == self.typec['opbeanw'])) and \
                    self.mapget(vmap, np) > tv+1:
                    self.mapset(vmap, np, tv+1)
                    queue.append(np)
        return vmap
    
    def path(self, map, realmap, pt):
        step = self.mapget(map, pt) - 1
        pt = tuple(pt)
        # path sturct: (points, eat my bean, eat op bean)
        path = {pt:(1,0)}
        while step>0:
            npath = {}
            for p,b in path.items():
                for oft in self.offset:
                    next = self.move(p, oft)
                    if self.mapget(map, next) == step:
                        tmy, top = b[0], b[1]
                        if self.mapget(realmap, next) == self.typec['beanw']:
                            tmy += 1
                        elif self.mapget(realmap, next) == self.typec['opbeanw']:
                            top += 1
                        if next not in npath.keys() or \
                            (npath[next][0] - npath[next][1] < tmy -top or\
                            npath[next][0] < tmy or npath[next][1] > top):
                            npath[next] = (tmy, top)
            path = npath
            step -= 1
        return path
    
    def pt2color(self, map, pt, max):
        v = self.mapget(map, pt)
        c = 100 - min(v,max) * 100 / max
        h = 3.6 * c
        
        return ImageColor.getcolor('hsl('+str(int(h))+','+str(c)+'%,'+str(c)+'%)', 'RGB')
    
    def map2image(self, map, imgname, max):
        data = []
        for y in range(self.size[1]):
            for x in range(self.size[0]):
                data.append(self.pt2color(map, (x,y), max))
        
        img = Image.new('RGB', (50,25))
        img.putdata(data)
        img.save('%s/%s.png'%(self.TMP,imgname))
        
    def info2txt(self, info, infoname):
        with open('%s/%s.txt'%(self.TMP, infoname), 'w') as f:
            f.write(str(info))
########NEW FILE########
__FILENAME__ = snake-ai
from utils import AIBase, startGame, dirVec
from copy import deepcopy
# weight:
kDanger = 100 # void danger
kArea = -0.3

def rd(w, x):
    return min(x, w - x)

class SnackAI(AIBase):
    def __init__(self):
        AIBase.__init__(self, "kitty-snake")
    
    def newRound(self, roundId):
        me = self.snakes[self.idx]
        if not me['alive']:
            print "new round: %d, dying" % roundId
            return
        print "new round: %d" % roundId
        body = me['body']
        x, y = body[0]
        tail = body[-1]
        myLen = len(body)
        m = self.buildMap(myLen < 5) # void gem when my len < 5
        fm = self.buildFakeMap(m)
        otherLen = 0
        for i in range(len(self.snakes)):
            if i != self.idx and self.snakes[i]['alive']:
                otherLen = max(otherLen, len(self.snakes[i]['body']))
        dir = me['direction']
        ntegg = 1000000
        valueK = 1
        if myLen - otherLen > 10:
            valueK = 0
        elif myLen > otherLen:
            valueK = (10 + otherLen - myLen) / 10
        for d, nx, ny in self.graph[me['direction']][x][y]:
            if m[nx][ny] != 0:
                print m[nx][ny], (x, y), 
                continue
            toegg, danger = self.calcValue(m, nx, ny, d, tail)
            value1 = toegg * valueK + danger * kDanger + self.sumArea(m, (nx, ny)) * kArea
            toegg, danger = self.calcValue(fm, nx, ny, d, tail)
            value2 = toegg * valueK + danger * kDanger + self.sumArea(m, (nx, ny)) * kArea
            finalValue = value1 + value2 * 0.5
            if finalValue < ntegg:
                ntegg = finalValue
                dir = d
        print (x, y), "ntegg=", ntegg
        self.turn(dir)

    def move(self, x, y, d):
        return [(x + dirVec[d][0] + self.w) % self.w, (y + dirVec[d][1] + self.h) % self.h]

    def dist(self, a, b):
        return rd(self.w, abs(a[0] - b[0])) + rd(self.h, abs(a[1] - b[1]))

    def calcValue(self, map, mx, my, d, t):
        g = self.graph
        value = 100
        x, y = mx, my
        if [x, y] in self.eggs:
            value = 0
        danger = 2
        v = ([], [], [], [])
        for i in range(4):
            for j in range(self.w):
                v[i].append([False] * self.h)

        # print d, x, y
        v[d][x][y] = True
        q = [(d, x, y, 1)]
        f = 0
        tailFlag = 0
        while f < len(q):
            d, x, y, st = q[f]
            # print f, d, x, y, st
            # print (x, y), st
            f += 1
            for nd, nx, ny in g[d][x][y]:
                # print "inloop:", nd, (nx, ny), map[nx][ny], v[nd][nx][ny]
                if not v[nd][nx][ny]:
                    if map[nx][ny] < st and map[nx][ny] >= 0:
                        v[nd][nx][ny] = True
                        q.append((nd, nx, ny, st+1))
                        if (nx, ny) == tuple(t):
                            tailFlag = 1
                        elif [nx, ny] in self.eggs:
                            value = min(value, st)
        danger -= tailFlag
        nearKill = 0
        for i in range(len(self.snakes)):
            if i != self.idx and self.snakes[i]['alive']:
                if self.snakes[i]['sprint'] == 0:
                    if self.dist((x, y), self.snakes[i]['body'][0]) <= 1:
                        nearKill = 1
                    else:
                        ex, ey = self.snakes[i]['body'][0]
                        for i in range(3):
                            ex, ey = self.move(ex, ey, self.snakes[i]['direction'])
                        if (ex, ey) == (x, y):
                            nearKill = 1
                elif self.snakes[i]['sprint'] > 0 and self.dist((x, y), self.snakes[i]['body'][0]) <= 3:
                    nearKill = 1
        danger += nearKill

        for i in range(len(self.snakes)):
            if i != self.idx:
                map[mx][my] = -1
                ret = self.checkAttack(map, self.snakes[i])
                map[mx][my] = 0
                if ret:
                    value = -1
	return value, danger

    def sumArea(self, map, st):
        v = []
        for i in range(self.w):
            v.append([False] * self.h)
        x, y = st
        v[x][y] = True
        q = [(x, y)]
        f = 0
        while f < len(q):
            x, y = q[f]
            f += 1
            for d in range(4):
                nx, ny = self.move(x, y, d)
                if not v[nx][ny] and map[nx][ny] == 0:
                    v[nx][ny] = True
                    q.append((nx, ny))
        #print "area:", f
        return f

    def checkAttack(self, map, snake):
        if not snake['alive']:
            return False
        return self.sumArea(map, snake['body'][0]) <= len(snake['body'])
        
    def buildMap(self, noGem):
        m = []
        for i in range(self.w):
            m.append([0] * self.h)
        for x, y in self.walls:
            m[x][y] = -1
        for snake in self.snakes:
            if snake['alive']:
                count = len(snake['body'])
                for x, y in snake['body']:
                    m[x][y] = count
                    count -= 1
            else:
                for x, y in snake['body']:
                    m[x][y] = -1
        if noGem:
            for x, y in self.gems:
                m[x][y] = -1
        # for i in m:
        #     print i
	return m

    def buildFakeMap(self, map):
        fakeMap = deepcopy(map)
        for i in range(len(self.snakes)):
            if i != self.idx and self.snakes[i]['alive'] and self.snakes[i]['sprint'] >= 0:
                hx, hy = self.snakes[i]['body'][0]
                val = len(self.snakes[i]['body']) + 1
                for d in self.getDirs(self.snakes[i]['direction']):
                    if fakeMap[hx][hy] >= 0 and fakeMap[hx][hy] <= val:
                        fakeMap[hx][hy] = val
        return fakeMap

    def buildGraph(self):
        # Build The Basic Graph for BFS
        # first: Dir 0 ~ 3
        # then x, y
        g = ([],[],[],[]) 
        for i in range(4):
            print "build-direction:", i
            for x in range(self.w):
                line = []
                for y in range(self.h):
                    cell = []
                    for d in self.getDirs(i):
                        if [x, y] in self.walls:
                            break
                        nx, ny = self.move(x, y, d)
                        for pi in range(len(self.portals)):
                            if (nx, ny) == tuple(self.portals[pi]):
                                print "detect portal: ", pi, (nx, ny)
                                if pi % 2 == 1: 
                                    di = pi - 1
                                else:
                                    di = pi + 1 
                                # set sx, sy to out portal addr
                                nx, ny = self.portals[di]
                                break

                        if [nx, ny] not in self.walls:
                            cell.append((d, nx, ny))
                        
                    line.append(cell)
                g[i].append(line)
        return g
                    
    def onUpdateMap(self):
        print "Building Graph..."
        self.graph = self.buildGraph()
        print "Building Graph finish."



host = 'localhost'
# host = 'game.snakechallenge.org'
startGame("ws://%s:9999/info" % host, 0, SnackAI())

########NEW FILE########
__FILENAME__ = utils
import websocket
import asyncore
import json
import logging
import traceback

logger = logging.getLogger()
fileHandler = logging.FileHandler('ai.log')
fileHandler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(fileHandler)
logger.setLevel(logging.DEBUG)

dirVec = ((-1, 0), (0, -1), (1, 0), (0, 1))

class AIBase:
    def __init__(self, name):
        self.name = name
        self.lastRoundId = -1
        self.added = False
        self.needAdd = True

    def getDirs(self, d):
        return filter(lambda x: abs(x-d)!=2, range(4)) 

    def newRound(self, roundId):
        return

    def addMe(self, type='python'):
        if not self.needAdd:
            return
        else:
            self.needAdd = False
        self.send({'op' : 'add',
                  'name': self.name,
                  'type': type})
	self.send({'op': 'info'})

    def turn(self, d):
        self.send({'op': 'turn',
                   'direction': d,
                   'round': -1})

    def sprint(self):
        self.send({'op' : 'sprint'})

    def setIndex(self, idx):
        print "My Index:", idx
        self.added = True
        self.idx = idx

    def setSender(self, sender):
        self.send = sender

    def onUpdateMap(self):
        return

    def setMap(self, size, walls, portals):
        self.w = size[0]
        self.h = size[1]
        self.walls = walls
        self.portals = portals
        self.onUpdateMap()

    def setStatus(self, data):
        if data['status'] == 'finished':
            self.added = False
            self.needAdd = True
            return
        if not self.added:
            self.addMe()
        self.eggs = data['eggs']
        self.gems = data['gems']
        self.snakes = data['snakes']
        print self.lastRoundId, data['round']
        if data['round'] != self.lastRoundId:
            self.lastRoundId = data['round']
            if self.added:
                try:
                    self.newRound(self.lastRoundId)
                except:
                    traceback.print_exc()
                    
        

class EventHandler:
    def __init__(self, url, room, ai):
        self.room = room
        self.ai = ai
        self.id = ""
        ai.setSender(self.aiSend)

    def send(self, data):
        self.sock.send(data)
   
    def aiSend(self, data):
        data['id'] = self.id
	data['room'] = self.room
	print "ai-send:", data
        return self.send(json.dumps(data))
    
    def onopen(self, ws):
        logger.info("connected, now send init info")
        self.send(json.dumps({'op': 'setroom', 'room': self.room}))
        self.send(json.dumps({'op': 'map', 'room': self.room}))
        self.send(json.dumps({'op': 'info', 'room': self.room}))

    def onmessage(self, ws, m):
        data = json.loads(str(m))
        if data['op']=='info':
            self.ai.setStatus(data)
        elif data['op']=='add':
            if 'status' in data:
                raise Exception(data['status'])
            self.ai.setIndex(data['seq'])
            self.id = data['id']
        elif data['op']=='map':
            self.ai.setMap(data['size'], data['walls'], data['portals'])
        else:
            logger.info("recv: " + str(data))


def on_error(ws, error):
    print error

def on_close(ws):
    print "### closed ###"

def startGame(url, room, ai):
#    websocket.enableTrace(True)
    handler = EventHandler(url, room, ai)
    sock = websocket.WebSocketApp(url, on_message = handler.onmessage,
                                  on_error = on_error,
                                  on_close = on_close)
    sock.on_open = handler.onopen
    handler.sock = sock
    sock.run_forever()


########NEW FILE########
__FILENAME__ = simple_snake
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: simple snake
用来作为示例代码
"""
import json, time
import urllib, httplib, logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

SERVER = "game.snakechallenge.org"
PORT = 9999
DIRS = [[-1, 0], [0, -1], [1, 0], [0, 1]]

class SimpleSnake():
    def __init__(self):
        self.conn = httplib.HTTPConnection(SERVER, PORT)
        self.room = 0
        self.d = 0

    def cmd(self, cmd, data={}):
        """
        发送命令给服务器
        """
        data['op'] = cmd
        data['room'] = self.room
        # logging.debug('post: %s : %s', cmd, data)
        self.conn.request("POST", '/cmd',
                          urllib.urlencode(data),
                          {'Content-Type': 'application/x-www-form-urlencoded'})
        result = self.conn.getresponse().read()
        return json.loads(result)

    def cmd_add(self):
        self.me = self.cmd("add",
                           dict(name = "SimplePython",
                                type = "python"))
        return self.me
    
    def cmd_map(self):
        self.map = self.cmd("map")

    def cmd_info(self):
        self.info = self.cmd("info")

    def cmd_turn(self, dir):
        return self.cmd("turn",
                        dict(id = self.me["id"],
                             round = -1,
                             direction = dir))

    def step(self):
        snake = self.info['snakes'][self.me["seq"]]
        head = snake['body'][0]
        dir = DIRS[self.d]
        nexts = [
            [head[0] + dir[0]*i,
             head[1] + dir[1]*i]
            for i in [1,2,3,4]
            ]
    
        blocks = []
        blocks += self.map['walls']
        for snake in self.info['snakes']:
            blocks += snake['body']
    
        # change direction when there is block ahead
        for n in nexts:
            for b in blocks:
                if b[0] == n[0] and b[1] == n[1]:
                    self.d = (self.d + 1) % 4
                    return self.d
          
        return self.d


def main():
    rs = SimpleSnake()
    rs.cmd_map()
    logging.debug(rs.cmd_add())
    while True:
        time.sleep(0.3)
        rs.cmd_info()
        logging.debug(rs.cmd_turn(rs.step()))
    
if __name__=="__main__":
    main()



########NEW FILE########
__FILENAME__ = db
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: db
"""
import sqlite3
db = sqlite3.connect('tmp/game.db')
cursor = db.cursor()
try:
    cursor.execute('create table scores (time, name)')
    cursor.execute('create index scores_time_index on scores(time)')
except:
    pass



########NEW FILE########
__FILENAME__ = dynamic_wall
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: dynamic wall samples
"""

from snakec.game import *

class FanWallGen(WallGen):    
    freq = 2    # fan frequence
    flen = 4    # fan length
    
    # fan movement offest
    offset = [[(-1,0), (1,0), (0,-1), (0,1)], \
            [(-1, -1), (-1,1), (1,-1), (1,1)]]
    
    def can(self, ctx):
        return ctx.round % self.freq == 0
        
    def gen(self, ctx):
        ct = [ctx.size[0]/2, ctx.size[1]/2]
        walls = [ct]
        ang = (ctx.round / self.freq) % 2
        
        def move(pt, of):
            return [pt[0]+of[0], pt[1]+of[1]]

        for of in self.offset[ang]:
            pt = ct[:]
            for i in range(self.flen):
                pt = move(pt, of)
                walls.append(pt[:])
        
        return walls
            
########NEW FILE########
__FILENAME__ = game
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: game core
"""

class BeanGen:
    def can(self, ctx):
        pass
    def gen(self, ctx):
        pass
        
class WallGen:
    def can(self, ctx):
        pass
    def gen(self, ctx):
        pass

########NEW FILE########
__FILENAME__ = game_controller
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: game_controller
游戏控制器.. 提供api级别的接口, 方便服务器调用game

"""
from snake_game import *

class RoomController():
    def __init__(self, games):
        self.games = games
        self.controllers = [Controller(g)
                            for g in self.games]
    def op(self, data):
        """
        分配room
        """
        # 检查room
        if not data.has_key('room'):
            return dict(status = "data has no room param.")
        
        try:
            room = int(data['room'])
        except Exception as e:
            return dict(status="room data (%s) error: %s" % (data['room'], str(e)))
        
        if not 0 <= room < len(self.games):
            return dict(status='room number error: %d'%room)
        # 分配处理
        return self.controllers[room].op(data)

class Controller():
    def __init__(self, game):
        self.game = game

    def op(self, data):
        """
        统一的op接口
        """
        op = data['op']
        if op == 'add':
            return self.game.add_snake(type=data['type'], name=data['name'])
        
        elif op in ('turn', 'sprint'):
            if not data.has_key(round): data['round'] = -1
            return dict(status=self.game.set_snake_op(data['id'], int(data['round']), data))
        
        elif op == 'map':
            return self.game.get_map()

        elif op == 'setmap':
            return dict(status=self.game.user_set_map(data['data']))
        
        elif op == 'info':
            return self.game.get_info()
        
        elif op == 'history':
            return self.history()
        
        elif op == 'scores':
            return self.game.scores()
        
        else:
            return dict(status='op error: %s' % op)

def test():
    """
    # 初始化
    >>> game = Game()
    >>> c = Controller(game)

    # 添加新的蛇
    >>> result = c.add(name='foo',type='python')
    >>> result = c.add(name='bar',type='python')
    >>> id = result['id']
    >>> result['seq']
    1

    # 控制蛇的方向
    >>> result = c.turn(id=id, d=0, round=-1)

    # 获取地图信息
    >>> m = c.map()

    # 获取实时信息
    >>> info = c.info()
    """
    import doctest
    doctest.testmod()

if __name__=="__main__":
    test()

########NEW FILE########
__FILENAME__ = lib
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: lib
"""
import sys, os
import time, logging, json, random, uuid, datetime
from datetime import date

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")


class Clock():
    """一个分时器，限制刷新率
    >>> c = Clock(20) # fps
    >>> c.tick(block=False)
    """
    def __init__(self, fps):
        self.set_fps(fps)

    def set_fps(self, fps):
        self.fps = fps
        self.interval = 1.0/float(fps)
        self.pre = time.time()

    def tick(self, block=True):
        """
        检查是否到了时间
        """
        mid = time.time() - self.pre
        if  mid < self.interval:
            if block:
                time.sleep(self.interval - mid)
            else:
                return
        self.pre = time.time()
        return True

########NEW FILE########
__FILENAME__ = image2map
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: convert image to snake challenge map, require PIL
"""

import sys
import Image

def color2map(color):
    if color[0] < 128 and color[1] < 128 and color[2] < 128:
        return 'W'
    elif color[0] > 128 and color[1] < 128 and color[2] < 128:
        return 'X'
    elif color[0] < 128 and color[1] < 128 and color[2] > 128:
        return 'S'
    else:
        return '.'

def image2map(file, size=None):
    map = []
    img = Image.open(file, 'r').convert("RGB")
    
    if size is not None:
        img = img.resize(size)
        
    data = img.load()
    for i in range(img.size[1]):
        mapscan = []
        for j in range(img.size[0]):
            color = data[j,i]
            mapscan.append(color2map(color))
        map.append(mapscan)
    return map
    
def mapconfigs():
    cfgs = ['author','version','name','snakelength','size','food','maxfoodvalue']
    meta = {}
    for cfg in cfgs:
        sys.stdout.write(cfg + ": ")
        input = sys.stdin.readline()
        meta[cfg] = input
    return meta
    
def writetofile(meta, map, file):
    with open(file, 'w') as f:
        for mk,mv in meta.items():
            f.write(mk+": "+mv)
        f.write("map:\n")
        for y in map:
            for x in y:
                f.write(x)
            f.write("\n")

def tosize(value):
    d = value.strip().split('x')
    return (int(d[0]), int(d[1]))

if __name__ == '__main__':
    meta = mapconfigs()
    try:
        size = tosize(meta['size'])
    except Exception:
        size = None
    print size
    map = image2map(sys.argv[1], size)
        
    writetofile(meta, map, sys.argv[2])
########NEW FILE########
__FILENAME__ = map
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: map
"""
import random, yaml, json
from game import *

class Map:
    walltoken = ['.','W','S']
    # portal tokens
    portal_token = ['A','B','C','D','E','F','G','H','I','J']

    def __init__(self):
        self.beangen = MapBeanGen(self)
        self.wallgen = MapWallGen(self)
        # default meta
        self.meta = dict(
            name = 'unknown',
            author = 'none',
            version = 1.0,
            round = 3000,

            snake_init = 5,
            snake_max = 30,
            food_max = 3,
            )
        
    @staticmethod
    def loadfile(filename):
        data = yaml.load(open(filename).read())
        return Map.loaddata(data)

    @staticmethod
    def loaddata(data):
        map = Map()
        map.load(data)
        return map

    def __getattr__(self, name):
        return self.meta[name]
    
    def load(self, data):
        for key in data:
            self.meta[key] = data[key]
        
        self.beangen.maxbean = self.meta['food_max']

        self.walls = []
        self.snakes = []
        self.portals = []

        # extract map data
        data = self.meta['map'].strip().split('\n')

        for y in range(self.meta['height']):
            for x in range(self.meta['width']):
                v = data[y][x]
                if v == 'W':
                    self.walls.append([x,y])
                elif v == 'S':
                    self.snakes.append([x,y])
                    
                elif v in self.portal_token:
                    idx = self.portal_token.index(v)
                    shortage = (idx+1)*2 - len(self.portals)
                    if shortage > 0:
                        self.portals.extend([None] * shortage)
                    if self.portals[2*idx]:
                        self.portals[2*idx+1] = [x,y]
                    else:
                        self.portals[2*idx] = [x,y]

class MapWallGen:
    def __init__(self, map):
        self.map = map
        
    def can(self, ctx):
        return ctx.round == 0 and ctx.status == 'initial'
    def gen(self, ctx):
        return self.map.walls

class MapBeanGen(BeanGen):
    def __init__(self, map):
        self.map = map
        self.maxbean = 1
        
    def can(self, ctx):
        return ctx.status == 'running' and (self.canEgg(ctx) or self.canGem(ctx))
        #return ctx.round % 4 == 0 and ctx.status == 'running'

    def gen(self, ctx):
        gems,eggs = [],[]
        needgem, needegg = self.maxbean - len(ctx.gems), self.maxbean - len(ctx.eggs)
        
        while needgem>0:
            gem = self.randomGen(ctx, gems)
            gems.append(gem)
            needgem -= 1
        
        while needegg>0:
            egg = self.randomGen(ctx, gems + eggs)
            eggs.append(egg)
            needegg -= 1
        
        return [eggs,gems]
    
    def canEgg(self, ctx):
        return len(ctx.eggs)<self.maxbean
    
    def canGem(self, ctx):
        return len(ctx.gems)<self.maxbean
    
    def randomGen(self, ctx, ban):
        beanx = range(0, self.map.meta['width'])
        random.shuffle(beanx)
        for x in beanx:
            beany = range(0, self.map.meta['height'])
            random.shuffle(beany)
            for y in beany:
                if not ctx.check_hit([x,y]) and not [x,y] in ban:
                    return [x,y]
            
        
        
        

########NEW FILE########
__FILENAME__ = pygame_show
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: pygame_show
用pygame来显示逻辑..
"""
from lib import *
import pygame

snake_colors = [(0xa5, 0xc9, 0xe7), (0x08, 0x46, 0x7b), (0x3e, 0x9b, 0xe9), (0x88, 0xdb, 0x99), (0x0e, 0x74, 0x83), (0x85, 0xf5, 0x6b), (0xa5, 0xc9, 0xe7), (0x0a, 0x48, 0x46), (0x3a, 0xe7, 0x12), (0x88, 0xdb, 0x99), (0xf3, 0xf0, 0x0a), (0x0d, 0xb0, 0x2c)]


SIZE = 10
class Shower():
    def __init__(self, map):
        pygame.init()
        self.font = pygame.font.SysFont('sans', 12)
        self.set_map(map)

    def set_map(self, map):
        self.map = map
        size = self.map['size']
        self.screen = pygame.display.set_mode(
            (size[0]*SIZE + 100,
             size[1]*SIZE))

    def flip(self, info):
        # 退出判断
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
        
        size = SIZE
        gem_color = (100,0,0)
        egg_color = (100,100,0)
        portal_color = (100, 0, 100)
        def drawRect(c, x, y, w, h):
            pygame.draw.rect(self.screen, c,
                             pygame.Rect(x, y, w, h))
        # draw map background
        self.screen.fill((200,200,200))
        
        # snakes
        y = 10
        for i, s in enumerate(info['snakes']):
            color = snake_colors[i]

            for dot in s['body']:
                drawRect(color,
                         dot[0] * size,
                         dot[1] * size,
                         size, size)
            # head
            dot = s['body'][0]
            hcolor = egg_color if s['type'] == 'python' else gem_color
            drawRect(hcolor,
                     dot[0] * size + 2,
                     dot[1] * size + 2,
                     size-4, size-4)

            # snake info
            drawRect(color,
                     self.map['size'][0]*size + 10, y, 
                     size, size)
            # text
            sur = self.font.render(s['name'], True, (0,0,0))
            self.screen.blit(sur,
                             (self.map['size'][0]*size + 30, y))
            y += size + 10
                
        # beans
        for bean in info['eggs']:
            drawRect(egg_color,
                     bean[0] * size,
                     bean[1] * size,
                     size, size)
        for bean in info['gems']:
            drawRect(gem_color,
                      bean[0] * size,
                      bean[1] * size,
                      size, size)
        
        # walls
        for wall in self.map['walls']:
            drawRect((0,0,0),
                     wall[0] * size,
                     wall[1] * size,
                     size, size)

        # portals
        for b in self.map['portals']:
            drawRect(portal_color,
                     b[0] * size,
                     b[1] * size,
                     size, size)

        pygame.display.flip()


def pygame_testai(ais):
    """
    输入ai列表, 跑一个pygame的测试游戏看看
    """
    from snake_game import Game
    from game_controller import Controller
    
    game = Game()
    c = Controller(game)
    m = c.map()
    for ai in ais:
        ai.setmap(m)
        result = c.add(ai.name, ai.type)
        ai.seq = result['seq']
        ai.id = result['id']

    clock = Clock(3)
    s = Shower(m)

    while True:
        clock.tick()
        
        info = c.info()
        for ai in ais:
            d = ai.onprocess(info)
            c.turn(ai.id, d, game.round)
        game.step()

        s.flip(info)


def main():
    from ai_simple import AI
    ais = [AI() for i in range(20)]
    pygame_testai(ais)

    
if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = random_wall
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: generate random wall
"""
import random
from game import *
        
class RandomWallGen(WallGen):
    offset = [[-1,0],[1,0],[0,-1],[0,1]]	# 4 directions
    minDensity, maxDensity = 0.05, 0.07		# in [0,1]
    discrete, straight = 0.15, 0.5			# in [0,1]
    
    
    def can(self, ctx):
        """
        in simple mode, only generate wall before game start
        """
        return ctx.round == 0 and ctx.status == 'initial'
    def gen(self, ctx):
        """
        generate random map
        """
        wall = self.genWall(ctx)
        #wall = [[12,13], [12,14], [12,15], [13,15], [14,15], [15,14], [15,13], [14,13], [13,13]]
        #wall = [[7,5],[6,6],[8,6],[5,7],[9,7],[6,8],[8,8],[7,9]]
        #wall = [[7,8],[8,8],[10,8],[5,9],[6,9],[8,9],[9,9],[10,9],[5,10],[6,10],[7,10],[9,10],[6,11],[8,11],[9,11]]
        return self.breakWall(ctx, wall)
        
        
    def genWall(self, ctx):
        """
        generate map with random algorithm
        """
        num = ctx.w * ctx.h * random.uniform(self.minDensity, self.maxDensity)
        walls = []
        
        # check point in bound or not
        def bound(pt):
            return pt[0]>=0 and pt[0]<ctx.w and pt[1]>=0 and pt[1]<ctx.h
        
        # pick a point from neighbours
        self.idxes = range(4)
        random.shuffle(self.idxes)
        def next(pt):
            if random.random() > self.straight:
                random.shuffle(self.idxes)
            for i in self.idxes:
                dt = self.offset[i]
                dp = [pt[0]+dt[0], pt[1]+dt[1]]
                if bound(dp):
                    for wp in walls:
                        if dp == wp: dp = None; break
                    if dp is not None:
                        return dp
            return None
        
        # generate num points to construct the walls
        while num>0:
            # start point of a wall
            pt = [random.randint(0, ctx.w-1), random.randint(0, ctx.h-1)]
            if pt in walls: continue
            walls += [pt]
            num -= 1
            
            # continue grow the wall
            while random.random()>self.discrete and num>0:
                np = next(pt)
                if np == None: break
                walls += [np]
                pt = np
                num -= 1
        
        return walls
    
    def breakWall(self, ctx, walls):
    	"""
    	break the closed area:
    	1. calculate union set of the area
    	2. break the wall between different area
    	"""
    	set = [ [j*ctx.h+i for i in range(ctx.h)] for j in range(ctx.w)]

        for pt in walls:
            set[pt[0]][pt[1]] = -1

        move = lambda pt,dt=(0,0): [(pt[0]+dt[0]+ctx.w)%ctx.w, (pt[1]+dt[1]+ctx.h)%ctx.h]
        inset = lambda pt: set[pt[0]][pt[1]]
        setv = lambda pt,v: set[pt[0]].__setitem__(pt[1], v)
        setvp = lambda pt,vp: set[pt[0]].__setitem__(pt[1], set[vp[0]][vp[1]])
        idxtopt = lambda idx: [idx/ctx.h, idx%ctx.h]
        parent = lambda pt: idxtopt(inset(pt))
        
        def root(pt):
            if inset(pt) < 0: return -1
            t = pt
            while parent(t) != t:
                t = parent(t)
            tp = pt
            while parent(tp) != t:
                pt, tp = tp, parent(tp)
                setvp(pt, t)
            return inset(t)

        def union(pt1, pt2):
            rt1, rt2 = root(pt1), root(pt2)
            if rt1 < rt2:
                setv(idxtopt(rt2), rt1)
            elif rt2 < rt1:
                setv(idxtopt(rt1), rt2)

        # union the connected points
        def connect(pt):
            if root(pt) < 0 : return

            pt1 = move(pt, (-1,0))
            pt2 = move(pt, (0,-1))
            if root(pt1)>=0:
                union(pt, pt1)
            if root(pt2)>=0:
                union(pt, pt2)

        # build connection relationship
        for y in range(ctx.h):
            for x in range(ctx.w):
                connect((x,y))

        rtcnt = {}
        for y in range(ctx.h):
            for x in range(ctx.w):
                rt = root((x,y))
                if rt < 0 : continue
                if rt in rtcnt.keys():
                    rtcnt[rt] += 1
                else:
                    rtcnt[rt] = 1

        maxrt, maxrtcnt = 0, 0
        for k,v in rtcnt.items():
            if v > maxrtcnt: maxrt, maxrtcnt = k, v

        # break the closed area by removing blocking wall
        while len(rtcnt)>1:
            for pt in walls:
                for dt in self.offset:
                    tp = move(pt, dt)
                    rt = root(tp)
                    if rt>=0 and rt!=maxrt:
                        walls.remove(pt)
                        setv(pt, rt)
                        break
                if root(pt)>=0:
                    for dt in self.offset:
                        tp = move(pt, dt)
                        root1, root2 = root(pt), root(tp)
                        if root1>=0 and root2>=0 and root1!=root2:
                            union(tp, pt)
                            del rtcnt[max(root1,root2)]
        return walls
    
if __name__ == '__main__':
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = simple
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: simple strategy for game
"""

from lib import *
from game import *

BEAN_TIME = 6

def simpleBeanGen(ctx):
    """
    随机获取一个空的位置
    可能是性能陷阱?
    """
    while True:
        p = [random.randint(0, ctx.w-1),
             random.randint(0, ctx.h-1)]
        # 不要和其他东西碰撞
        if ctx.check_hit(p):
            continue
        return p

class SimpleBeanGen(BeanGen):
    def can(self, ctx):
        return ctx.enable_bean and ctx.round % BEAN_TIME == 0
    def gen(self, ctx):
        ret = [[],[]]
        if self.canEgg(ctx):
            ret[0].append(simpleBeanGen(ctx))
        if self.canGem(ctx):
            ret[1].append(simpleBeanGen(ctx))
        if ret[0] == ret[1]:
            ret[random.randint(0,1)] = []
        return ret
        
    def canEgg(self, ctx):
        return len(ctx.eggs)<10
    def canGem(self, ctx):
        return len(ctx.gems)<10 
        
class SimpleWallGen(WallGen):
    def can(self, ctx):
        # in simple mode, only generate wall before game start
        return ctx.round == 0
    def gen(self, ctx):        
        # 因为js没有(), 只好用[]
        return [[10, i] for i in range(5, 35)]
    

########NEW FILE########
__FILENAME__ = snake_game
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: snake_game
"""
from lib import *
from simple import *
from map.map import Map
from random_wall import RandomWallGen
import db
# 蛇的方向
LEFT, UP, RIGHT, DOWN = range(4)

# 方向对应修改的坐标
DIRECT = (
    (-1, 0), (0, -1), (1, 0), (0, 1)
    )

# 检查hit时的标识
NULL, WALL, GEM, EGG, PORTAL = range(5)

# 游戏状态
INITIAL = 'initial'
WAITFORPLAYER='waitforplayer'
RUNNING='running'
FINISHED='finished'

# 蛇的种类
PYTHON = 'python'
RUBY = 'ruby'

#sprint
SPRINT_ROUND = 5 
SPRINT_STEP = 3 # sprint的时候, 每轮可以走的步数
SPRINT_REST = 20 # sprint之后需要休息的时间

DEFAULT_MAP = 'srcs/map/campain.yml'#'srcs/map/campain.yml'

class Snake():
    def __init__(self, game, type, direction, head, length, name=""):
        """设置snake
        """
        self.game = game
        self.type = type
        self.name = name
        self.w, self.h = self.game.size
        self.id = uuid.uuid4().hex

        self.alive = True
        self.direction = direction
        self.sprint = 0

        # 计算身体
        dx, dy = DIRECT[direction]
        self.body = [
            [(head[0] - dx * i + self.w) % self.w,
             (head[1] - dy * i + self.h) % self.h]
            for i in range(length)]

    def op(self, d):
        if not d: return
        op = d['op']
        if op == 'turn':
            d = d['direction']
            # no turn back
            if (self.direction != d and self.direction % 2 == d % 2): return
            self.direction = d
            
        elif op == 'sprint':
            if self.sprint: return
            self.sprint = SPRINT_ROUND

    def get_next(self):
        """获取蛇下一个移动到的位置"""
        head = self.body[0]
        dx, dy = DIRECT[self.direction]
        next = [(head[0] + dx) % self.w,
                (head[1] + dy) % self.h]
        return next

    def move(self):
        """移动蛇"""
        if not self.alive: return

        if self.sprint==0:
            return self.one_step()
        
        if self.sprint > 0:
            self.sprint -= 1
            for i in range(SPRINT_STEP):
                self.one_step()
            if self.sprint == 0:
                self.sprint -= SPRINT_REST

        if self.sprint < 0:
            self.sprint += 1
            return

    def one_step(self):
        """移动一步"""
        if not self.alive: return
        next = self.get_next()
        # 检查是否撞到东西
        what = self.game.check_hit(next)
        # 没有撞到
        if not what:
            self.body.pop(-1)
            self.body.insert(0, next)
            return

        # portal
        if what == PORTAL:
            portal_next = self.game.get_portal_next(next)
            # 检查是否portal对面是蛇
            portal_next_what = self.game.check_hit_snake(portal_next)
            if portal_next_what:
                self.hit_others(next, portal_next_what)
                return
            # 移动头部
            self.body.pop(-1)
            self.body.insert(0, portal_next)
            return

        # 撞死了
        if what not in (GEM, EGG):
            self.hit_others(next, what)
            return

        # 吃掉豆子
        if what == EGG:
            self.game.eggs.remove(next)
        elif what == GEM:
            self.game.gems.remove(next)
                
        # 吃错了就要减少长度
        if ((what == EGG and self.type == RUBY) or
            (what == GEM and self.type == PYTHON)):
            self.body.pop(-1)
            self.body.pop(-1)
            # 足够短就被饿死了..
            if self.length() < 3:
                self.alive = False
                self.game.log('snake die because of eat wrong type of bean: '+ self.name)
        # 吃完豆子, 再到新的长度..
        self.body.insert(0, next)

    def hit_others(self, next, what):
        self.alive = False
        self.game.log('snake hit and die: '+ self.name)
        # 如果撞到其他蛇的头部, 其他蛇也挂了
        if (isinstance(what, Snake)
            and what.head() == next):
            what.alive = False
            self.game.log('snake hit by others and die: '+ what.name)

    def head(self):
        """获取蛇的头部位置"""
        return self.body[0]

    def length(self):
        """获取蛇的长度"""
        return len(self.body)


class Game():
    """游戏场景"""
    # 记录分数
    def __init__(self,
                 enable_bean=True,
                 enable_wall=True,
                 enable_no_resp_die=True,
                 map=None):
        self.enable_bean = enable_bean
        self.enable_wall = enable_wall
        self.enable_no_resp_die = enable_no_resp_die

        if not map:
            map = Map.loadfile(DEFAULT_MAP)
        self.set_map(map)
        self.start()

    def log(self, msg):
        self.logs.append(msg)

    def user_set_map(self, data):
        if self.status != WAITFORPLAYER:
            return "only can set map when the game state is waitforplayer"

        try:
            m = Map.loaddata(data)
            self.set_map(m)
            self.start()
            return 'ok'
        except Exception as e:
            # if error, fall back to default map
            self.set_map(Map.loadfile(DEFAULT_MAP))
            self.start()
            return 'setmap error: ', str(e)
        
    def set_map(self, map):
        self.map = map
        self.MAX_ROUND = map.meta['round']
        self.wallgen = map.wallgen
        self.portals = map.portals
        self.size = self.w, self.h = map.meta['width'], map.meta['height']

    def start(self):
        '''
        # 因为js没有(), 只好用[]
        self.walls = [[10, i]
                      for i in range(5, 35)]
        '''
        self.logs = []
        self.info = None

        self.walls = [] # to pass unittest
        self.snakes = []
        self.round = 0
        self.snake_op = []
        self.bean_time = 4 # 多少轮会出现一个豆子
        self.eggs = []
        self.gems = []
        self.loop_count = 0
        self.status = WAITFORPLAYER
        #if self.wallgen.can(self):
        if self.enable_wall:
            self.walls = self.wallgen.gen(self)

    def add_snake(self,
                  type=PYTHON,
                  direction=DOWN,
                  head=None,
                  name="unknown"):
        length = self.map.meta['snake_init']
        # 检查蛇类型
        if type not in (PYTHON, RUBY):
            return dict(status='snake type error: %s' % type)
        # 检查蛇数量
        if len(self.snakes) >= self.map.meta['snake_max']:
            return dict(status='no place for new snake.')
        if self.status == FINISHED:
            return dict(stauts='cannot add snake when game is finished.')
        
        # 随机生成蛇的位置
        d = DIRECT[direction]
        if not head:
            while True:
                # 蛇所在的地点不能有东西存在..
                next = self.get_empty_place()
                for i in range(length + 1):
                    body = [(next[0] - d[0] * i) % self.w,
                            (next[1] - d[1] * i) % self.h]
                    if self.check_hit(body):
                        break
                # 如果检查没有发现任何一点重合, 就用改点了.
                else:
                    head = [(next[0] - d[0]) % self.w,
                            (next[1] - d[1]) % self.h]
                    break

        # 生成蛇
        snake = Snake(self, type, direction, head, length, name)
        self.snakes.append(snake)
        self.snake_op.append(dict(op='turn', direction=direction))
        # 强制更新info
        self.info = None
        # 返回蛇的顺序, 以及蛇的id(用来验证控制权限)
        return dict(seq=len(self.snakes) - 1, id=snake.id)

    def set_snake(self, n, snake):
        """设置蛇, 调试用"""
        self.snakes[n] = snake
        
    def get_seq(self, id):
        """根据蛇的id获取seq"""
        for i, s in enumerate(self.snakes):
            if s.id == id:
                return i

    def set_snake_op(self, id, round, kw):
        # 获取蛇的seq
        n = self.get_seq(id)
        if n == None:
            return "noid"
        # 检查轮数是否正确
        if round != -1 and self.round != round:
            return "round error, current round: %d" % self.round
        
        if kw['op'] == 'turn':
            kw['direction'] = int(kw['direction'])
            d = kw['direction']
            # 检查direction
            if not 0<=d<=3:
                return "direction error: %d" % d
            # check turn back
            sd = self.snakes[n].direction
        
            self.snake_op[n] = kw
            if (sd != d and sd % 2 == d % 2):
                return "noturnback"
            return 'ok'

        elif kw['op'] == 'sprint':
            self.snake_op[n] = kw
            return 'ok'
        else:
            return 'wrong op: ' + kw['op'] 

    def check_score(self):
        """计算最高分, 保存到历史中"""
        # 只统计活下来的蛇
        lives = [s
                 for s in self.snakes
                 if s.alive]
        if len(lives) <=0: return
        # 计算谁的分数最大
        highest = max(lives, key=lambda s: s.length())
        self.log('game finished, winner: ' + highest.name)
        # 再加到最高分里面去
        db.cursor.execute('insert into scores values(?, ?)', (datetime.datetime.now(), highest.name))
        db.db.commit()

    def scores(self):
        d = date.today()
        today = datetime.datetime(d.year, d.month, d.day)
        dailys =  list(db.cursor.execute('select * from (select name, count(*) as count from scores where time > ? group by name) order by count desc limit 10', (today, )))
        weeklys = list(db.cursor.execute('select * from (select name, count(*) as count from scores where time > ? group by name) order by count desc limit 10', (today - datetime.timedelta(days=7), )))
        monthlys = list(db.cursor.execute('select * from (select name, count(*) as count from scores where time > ? group by name) order by count desc limit 10', (today - datetime.timedelta(days=30), )))
        return dict(dailys=dailys, weeklys=weeklys, monthlys=monthlys)

    def get_map(self):
        return dict(walls=self.walls,
                    portals=self.portals,
                    size=self.size,
                    name=self.map.name,
                    author=self.map.author,
                    )

    def get_info(self):
        if self.info:
            return self.info
        snakes = [dict(direction=s.direction,
                       body=s.body,
                       name=s.name,
                       type=s.type,
                       sprint=s.sprint,
                       length=len(s.body),
                       alive=s.alive)
                  for s in self.snakes
                  ]
        self.info = dict(snakes=snakes,
                         status=self.status,
                         eggs=self.eggs,
                         gems=self.gems,
                         round=self.round,
                         logs=self.logs)
        return self.info

    def step(self):
        """游戏进行一步..."""
        self.logs = []
        self.info = None
        # 如果游戏结束或者waitforplayer, 等待一会继续开始
        if self.loop_count <= 50 and self.status in [FINISHED, WAITFORPLAYER]:
            self.loop_count += 1
            return

        if self.status == FINISHED:
            self.loop_count = 0
            self.start()
            return True

        # 游戏开始的时候, 需要有2条以上的蛇加入.
        if self.status == WAITFORPLAYER:
            if len(self.snakes) < 2: return
            self.status = RUNNING
            self.log('game running.')

        # 首先检查获胜条件:
        # 并且只有一个人剩余
        # 或者时间到
        alives = sum([s.alive for s in self.snakes])
        if alives <= 1 or(self.MAX_ROUND != 0 and self.round > self.MAX_ROUND):
            self.status = FINISHED
            self.loop_count = 0
            self.check_score()
            return True

        # 移动snake
        for i, d in enumerate(self.snake_op):
            snake = self.snakes[i]
            if not snake.alive: continue

            # 如果连续没有响应超过10次, 让蛇死掉
            if d == None and self.enable_no_resp_die:
                self.no_response_snake_die(snake, self.round)

            snake.op(d)
            snake.move()

        # 生成豆子
        if self.map.beangen.can(self):
            beans = self.map.beangen.gen(self)
            self.eggs += beans[0]
            self.gems += beans[1]
        
        #if self.round % self.bean_time == 0:
        #    self.create_bean()

        # next round
        self.round += 1
        self.snake_op = [None, ] * len(self.snakes)
        return True

    def get_portal_next(self, p):
        seq = self.portals.index(p)
        return self.portals[(seq / 2)*2 + ((seq%2)+1)%2 ]
    
    def create_bean(self):
        """生成豆子
        """
        if not self.enable_bean: return

        pos = self.get_empty_place()
        # 随机掉落豆子的种类
        if random.randint(0, 1):
            # 有豆子数量限制
            if len(self.gems) > 10: return
            self.gems.append(pos)
        else:
            if len(self.eggs) > 10: return
            self.eggs.append(pos)

    def check_hit(self, p):
        """检查p和什么碰撞了, 返回具体碰撞的对象"""
        if p in self.walls:
            return WALL
        if p in self.eggs:
            return EGG
        if p in self.gems:
            return GEM
        if p in self.portals:
            return PORTAL
        return self.check_hit_snake(p)

    def check_hit_snake(self, p):
        for snake in self.snakes:
            if p in snake.body:
                return snake

    def get_empty_place(self):
        """
        随机获取一个空的位置
        可能是性能陷阱?
        """
        while True:
            p = [random.randint(0, self.w-1),
                 random.randint(0, self.h-1)]
            # 不要和其他东西碰撞
            if self.check_hit(p):
                continue
            return p

    def alloped(self):
        """
        判断是否所有玩家都做过操作了
        """
        oped = [
            (not s.alive or op != None)
            for op, s in zip(self.snake_op,
                             self.snakes)]
        return all(oped)

    def no_response_snake_die(self, snake, round):
        """
        如果连续没有响应超过3次, 让蛇死掉
        round是没有响应的轮数(用来检查是否连续没有响应)
        
        """
        # 初始化缓存
        if (not hasattr(snake, 'no_resp_time') or
            snake.no_resp_round != round - 1):
            snake.no_resp_time = 1
            snake.no_resp_round = round
            return
        # 次数更新
        snake.no_resp_time += 1
        snake.no_resp_round = round            
        # 判断是否没有响应时间过长
        if snake.no_resp_time >= 5:
            snake.alive = False
            logging.debug('kill no response snake: %d' % \
                         self.snakes.index(snake))
            self.log('kill snake for no response: '+snake.name)
        
def test():
    """
    # 初始化游戏
    >>> game = Game((20,20),
    ...     enable_bean=False,
    ...     enable_wall=False,
    ...     enable_no_resp_die=False)
    
    >>> status, seq, id = game.add_snake(PYTHON, DOWN, (3, 4), 2)
    >>> status, seq, id = game.add_snake(PYTHON, DOWN, (18, 2), 4)
    >>> game.step()
    >>> game.status == RUNNING
    True

    # 基本的移动
    >>> game.snakes[1].alive
    True
    >>> game.step()
    >>> game.snakes[0].head()
    [3, 6]

    # 改变方向
    >>> game.turn_snake(0, LEFT, -1)
    'ok'
    >>> game.step()
    >>> game.snakes[0].head()
    [2, 6]
    >>> game.snakes[0].alive
    True

    # 超出地图会回转
    >>> game.step()
    >>> game.snakes[0].head()
    [1, 6]
    >>> game.step()
    >>> game.snakes[0].head()
    [0, 6]
    >>> game.step()
    >>> game.snakes[0].head()
    [19, 6]

    # 撞到其他snake会挂掉
    >>> game.set_snake(1, Snake(game, PYTHON, DOWN, (18, 7), 5))
    >>> game.step()
    >>> game.snakes[0].alive
    False
    >>> status, seq, id = game.add_snake()

    # 吃豆子
    >>> game.eggs.append([18, 9])
    >>> game.step()
    >>> len(game.eggs)
    0
    >>> game.snakes[1].length()
    6

    # python吃了gem会缩短(拉肚子)
    >>> s = game.snakes[1]
    >>> pos = s.get_next()
    >>> game.gems.append(pos)
    >>> game.step()
    >>> s.length()
    5
    >>> game.gems
    []

    # 缩短过度会死掉
    >>> s.body = s.body[:5]
    >>> pos = s.get_next()
    >>> game.gems.append(pos)
    >>> game.step()
    >>> s.alive
    False

    # 2条蛇头部相撞, 都死掉
    >>> game.set_snake(0, Snake(game, PYTHON, DOWN, (18, 6), 5))
    >>> game.set_snake(1, Snake(game, PYTHON, LEFT, (19, 7), 5))
    >>> game.step()
    >>> game.snakes[0].alive
    False
    >>> game.snakes[1].alive
    False

    # 算分
    >>> for s in game.snakes: s.alive = False
    >>> result = game.add_snake(name='no')
    >>> game.step()
    >>> game.status
    'finished'
    >>> ('no', 5) in game.scores
    True
    """
    import doctest
    doctest.testmod()

def main():
    test()
    
if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = snake_profile
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: snake_profile
用来测试profile功能

profile前数据:
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
  1000000    9.065    0.000    9.065    0.000 snake_game.py:290(check_hit)
   500000    2.525    0.000   15.162    0.000 snake_game.py:225(step)
  1000000    1.897    0.000   12.293    0.000 snake_game.py:66(move)
  1000000    0.834    0.000    0.834    0.000 snake_game.py:58(get_next)
"""
from snake_game import *

def main():
    game = Game((40,20),
                enable_bean=False,
                enable_wall=False,
                enable_no_resp_die=False)
    status, seq, id = game.add_snake(PYTHON, DOWN, (3, 4), 2)
    status, seq, id = game.add_snake(PYTHON, DOWN, (2, 2), 4)
    game.walls = [[i, j] for i in range(5, 19) for j in range(12)]
    for i in range(500):
        game.step()
    
    
if __name__=="__main__":
    for i in range(1000):
        main()

########NEW FILE########
__FILENAME__ = web_server
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: server
"""
from lib import *

import zmq
from zmq.eventloop import ioloop, zmqstream
# hack
ioloop.install()

import tornado
import tornado.web, tornado.websocket


context = zmq.Context()

# 用来接受info更新
suber = context.socket(zmq.SUB)
suber.connect('ipc:///tmp/game_puber.ipc')
# self.suber.setsockopt(zmq.SUBSCRIBE, 'room:%d '%room)
suber.setsockopt(zmq.SUBSCRIBE, '')


# 用来与服务器交互
oper = context.socket(zmq.REQ)
oper.connect('ipc:///tmp/game_oper.ipc')


class ChatRoomWebSocket(tornado.websocket.WebSocketHandler):
    connects = []
    chats = {}
    SAVED_CHATS = 30
    def open(self):
        self.name = '???'
        self.room = "root"
        # 显示现在已经在的人
        if len(self.connects) > 0:
            current_ins = ', '.join([u"%s in : %s" % (c.name, c.room)
                                     for c in self.connects])
        else:
            current_ins = 'none'
        self.write_message('current in: \n' + current_ins)
            
        self.connects.append(self)
        
    def on_message(self, message):
        data = json.loads(message)
        if data.has_key('name'):
            self.name = data['name']
            self.room = data['room']            
            self.broadcast(self.room, '<em>%s</em> enters the room: <em>%s</em>' % (self.name, self.room))
            # write some history chats
            for chat in self.chats.get(self.room, []):
                self.write_message(chat)
            return
        else:
            self.broadcast(self.room, '<em>%s</em> says: %s' % (self.name, data['msg']) )

    def broadcast(self, room, msg):
        # save chat
        if not self.chats.has_key(room):
            self.chats[room] = []
        room_chats = self.chats[room]
        room_chats.append(msg)
        if len(room_chats) > self.SAVED_CHATS:
            self.chats[room] = room_chats[-self.SAVED_CHATS:]
        
        for c in self.connects:
            if c.room != room:
                continue
            try:
                c.write_message(msg)
            except Exception as e:
                logging.debug(str(e))
                try:
                    self.connects.remove(c)
                except:
                    pass
            
    def on_close(self):
        self.connects.remove(self)
        self.broadcast(self.room, self.name + ' leaves.')

class Cmd(tornado.web.RequestHandler):
    def post(self):
        data = self.request.arguments
        # warp list
        for key in data:
            data[key] = data[key][0]
        data = json.dumps(data)
        oper.send_unicode(data)
        result = oper.recv()
        self.set_header("Content-Type", "application/json")
        self.write(result)

class InfoWebSocket(tornado.websocket.WebSocketHandler):
    
    connects = []
    room = -1

    @classmethod
    def check_info(cls, data):
        # 拆分掉room头信息
        data = data[0]
        i = data.index(' ')
        room = int(data[:i].split(':')[1])
        # 发送给所有注册到这个room的连接
        cls.send_info(room, data[i:])

    @classmethod
    def send_info(cls, room, info):
        for c in cls.connects[:]:
            if c.room == room:
                try:
                    c.write_message(info)
                except:
                    try:
                        cls.remove(c)
                    except:
                        pass
            
    def open(self):
        self.connects.append(self)
        
    def on_message(self, message):
        data = json.loads(message)
        if data.get('op') == 'setroom':
            self.room = int(data['room'])
        else:
            self.process_cmd(message)

    def process_cmd(self, message):
        # logging.debug(message)
        oper.send_unicode(message)
        result = oper.recv()
        self.write_message(result)

    def on_close(self):
        try:
            self.connects.remove(self)
        except:
            pass

stream = zmqstream.ZMQStream(suber)
stream.on_recv(InfoWebSocket.check_info)

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "cookie_secret": "61oETzKXQAGaYdkL5gEmGeJJFuYh7EQnp2XdTP1o/Vo=",
    # "login_url": "/login",
    # "xsrf_cookies": True,
    'debug' : True,
    # 'gzip' : True,
}

application = tornado.web.Application([
    (r"/info", InfoWebSocket),
    (r"/chatroom", ChatRoomWebSocket),
    (r"/cmd", Cmd),
    ], **settings)

def main():
    application.listen(9999)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        print "bye!"

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = zmq_game_server
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: server
"""
from lib import *
import zmq, json, random

import game_controller
from snake_game import *

context = zmq.Context()

ROOMS = 10

class Server():
    """
    游戏的服务器逻辑
    服务器提供2个队列:
    - game_puber队列(PUB), 当地图更新的时候, 发送info信息
    - game_oper队列(REP), 可以进行add/turn/map命令
    """
    def on_logic(self, g, ok):
        """判断定期更新的时间是否到了"""
        min_waits = 0.2
        max_waits = self.max_waits
        if not hasattr(g, 'pre'):
            g.pre = time.time()

        # 时间段不能小于min_waits, 不能大于max_waits
        now = time.time()
        if (now > g.pre + max_waits
            or (ok and now > g.pre + min_waits)
            ):
            g.pre = now
            return True
        
    def pub_info(self, i):
        info = self.controller.op(dict(room=i, op='info'))
        info['op'] = 'info'
        self.puber.send("room:%d "%i + json.dumps(info))


    def run(self, max_waits=10.0, enable_no_resp_die=True):
        self.max_waits = max_waits
        self.games = [Game(enable_no_resp_die=enable_no_resp_die)
                      for i in range(ROOMS)]
        self.controller = game_controller.RoomController(self.games)
        
        # 用来发布信息更新
        puber = context.socket(zmq.PUB)
        puber.bind('ipc:///tmp/game_puber.ipc')
        self.puber = puber

        # 用来处理
        oper = context.socket(zmq.REP)
        oper.bind('ipc:///tmp/game_oper.ipc')

        while True:
            time.sleep(0.001)
            
            # 处理op
            while True:
                try:
                    rc = oper.recv(zmq.NOBLOCK)
                # 处理完所有命令就跳出命令处理逻辑
                except zmq.ZMQError:
                    break

                try:
                    rc = json.loads(rc)
                    result = self.controller.op(rc)
                    result['op'] = rc['op']
                    #如果有新的蛇加进来, 也pub一下
                    if rc['op'] == 'add' and result.has_key('seq'):
                        self.pub_info(int(rc['room']))
                    #如果地图变动也pub
                    if rc['op'] == 'setmap' and result['status'] == 'ok':
                        self.pub_info(int(rc['room']))
                    # logging.debug('process op %s ', rc)
                    
                # 为了防止错误命令搞挂服务器, 加上错误处理
                except Exception as e:
                    error_msg = str(e)
                    result = dict(status=error_msg, data=rc)
                    logging.debug(error_msg)
                    
                oper.send(json.dumps(result))

            # 处理所有room的游戏id
            for i, g in enumerate(self.games):

                if g.status == RUNNING:
                    # 当游戏进行时, 需要等待所有活着的玩家操作完毕
                    ok = g.alloped()
                else:
                    # 其他状态的话, 最小时间的方式定时更新                    
                    ok = True
                    
                if not self.on_logic(g, ok):
                    continue
    
                # 游戏处理
                updated = g.step()

                # 发送更新信息
                if updated:
                    logging.debug("room %d updated: %s" % (i, g.status))
                    self.pub_info(i)

usage = """\
    $ zmq_game_server.py [type]
    type == web:
        server for snakechallenge.org, when game over, server start new round.
        because it is slow on internet, set wait time to 5.0 seconds
    type == local:
        local max_waits set to 1.0s
"""

def main():
    import sys
    if len(sys.argv) < 2: print usage
    cmd = sys.argv[1]
    if cmd == 'web':
        s = Server()
        s.run(max_waits=5.0, enable_no_resp_die=True)
    elif cmd == 'local':
        s = Server()
        s.run(max_waits=1.0, enable_no_resp_die=True)
    else:
        print usage
        
if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = zmq_logger
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: log_server
记录以及回放服务器
"""
from ailib import *

    
def logger(controller, filename="game.log", quit_on_finish=True):
    """
    用来记录log
    """
    c = controller
    # log file
    f = open(filename, 'w+')

    def save_map():
        m = c.map()
        logging.debug(m)
        f.write('map: ')
        f.write(json.dumps(m))
        f.write('\n')
        return m

    def save_info():
        info = c.info()
        logging.debug(info)
        f.write('info: ')
        f.write(json.dumps(info))
        f.write('\n')
        return info

    clock = Clock(30)
    info = None
    status = None
    round = -1
    
    while True:
        try:
            clock.tick()
            # get map on init
            if not status:
                save_map()

            # loop get info..
            info = c.info()
            if info['round'] == round:
                time.sleep(0.3)
                continue
            round = info['round']
            logging.debug(info)
            
            # get map again when start new game
            if status == 'finished' and info['status'] == 'waitforplayer':
                save_map()

            # save info
            f.write('info: ')
            f.write(json.dumps(info))
            f.write('\n')
            
            # quit on game finished
            if quit_on_finish and info['status'] == 'finished':
                f.close()
                return
            status = info['status']
        except KeyboardInterrupt:
            f.close()
            return

usage = """\
    $zmq_logger.py [connect type] [room number] [filename]
    connect type is in [web, zero]
"""

def main():
    if len(sys.argv) < 3: print usage
    controller = sys.argv[1]
    try:
        room = int(sys.argv[2])
    except:
        print usage
        
    if controller == 'web':
        Controller = WebController
    elif controller == 'zero':
        Controller = ZeroController
    else:
        print usage

    filename=sys.argv[3]
        
    logger(Controller(room),
           filename=filename,
           quit_on_finish=False)
    
if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = zmq_pygame_show
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: zmq_pygame_show
"""
from lib import *
from pygame_show import Shower

import zmq
context = zmq.Context()

usage = """
python zmq_pygame_show.py [room number]
"""

def show(room):
    """
    用来显示现在游戏状况的client
    """
    # 用来接受info更新
    suber = context.socket(zmq.SUB)
    suber.connect('ipc:///tmp/game_puber.ipc')
    suber.setsockopt(zmq.SUBSCRIBE, "room:%d " % room)
    # 用来与服务器交互
    oper = context.socket(zmq.REQ)
    oper.connect('ipc:///tmp/game_oper.ipc')
    # 获取map
    def get_map():
        req = dict(op='map', room=room)
        oper.send(json.dumps(req))
        return json.loads(oper.recv())
    m = get_map()

    clock = Clock(30)
    shower = Shower(m)
    info = None
    
    while True:
        clock.tick()
        # 等待地图更新...
        try:
            info = suber.recv(zmq.NOBLOCK)
            info = info[info.index(' ') : ]
            info = json.loads(info)
            # 如果游戏结束了, 获取map
            if info['status'] == 'waitforplayer':
                shower.set_map(get_map())
            
        except zmq.ZMQError as e:
            pass

        if info:
            shower.flip(info)


if __name__=="__main__":
    try:
        room = int(sys.argv[1])
    except:
        print usage
    show(room)

########NEW FILE########
__FILENAME__ = zmq_replayer
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: zmq_replayer
"""
from lib import *

import zmq
context = zmq.Context()


def replayer(filename="game.log", loop=False):
    """
    用来回放log, 默认room0
    """
    if loop: loop_count=0
    # 读取file
    datas = []
    with open(filename) as f:
        for line in f.readlines():
            p = line.find(': ')
            type = line[:p]
            data = line[p+len(': '):]
            data = json.loads(data)
            datas.append((type, data))

    # 用来发布信息更新
    puber = context.socket(zmq.PUB)
    puber.bind('ipc:///tmp/game_puber.ipc')

    # 用来处理
    oper = context.socket(zmq.REP)
    oper.bind('ipc:///tmp/game_oper.ipc')

    clock = Clock(2)
    i = 0
    map = None
    info = None
    
    while True:
        # 处理op
        while True:
            try:
                rc = json.loads(oper.recv(zmq.NOBLOCK))
                if rc['op'] not in ('map', 'info'):
                    result = 'this is replay server, only accept map and info'
                if rc['op'] == 'map':
                    result = map
                else:
                    result = info
                oper.send(json.dumps(result))
                logging.debug('process op %s ', rc['op'])
            except zmq.ZMQError:
                break
            
        #定时更新
        if not clock.tick(block=False):
            continue

        # get data
        type, data = datas[i]
        i += 1
        if i == len(datas): break
        
        if type == 'map':
            map = data
            continue
        else:
            info = data

        logging.debug("stepping:" + info['status'])
        # 发送更新信息
        puber.send("room:0 " + json.dumps(info))
        
        time.sleep(0.001)

usage = """\
    zmq_replayer.py [filename]
"""

if __name__=="__main__":
    if len(sys.argv) <1: print usage
    replayer(filename)

########NEW FILE########
