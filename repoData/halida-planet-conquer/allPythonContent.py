__FILENAME__ = ai_demo

########NEW FILE########
__FILENAME__ = ai_flreey
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: ai_flreey
"""
import json, time
import urllib, httplib, logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

SERVER = "localhost"
PORT = 9999
DIRS = [[-1, 0], [0, -1], [1, 0], [0, 1]]

class SimpleAI():
    def __init__(self):
        self.conn = httplib.HTTPConnection(SERVER, PORT)
        self.room = 0
        self.d = 0
        self.cmd_map()
        self.cmd_add()

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
                           dict(name = "Flreey", side='python'))
        return self.me
    
    def cmd_map(self):
        self.map = self.cmd("map")

    def cmd_info(self):
        self.info = self.cmd("info")

    def cmd_moves(self, moves):
        print self.me, moves
        return self.cmd("moves",
                        dict(id = self.me["id"],
                             moves = moves))

    def init_weight(self):
        all_res = 0
        all_cos = 0
        all_def = 0
        all_max = 0
        for planet in self.map['planets']:
            all_res += planet['res'] * 1.0
            all_cos += planet['cos'] * 1.0
            all_def += planet['def'] * 1.0
            all_max += planet['max'] * 1.0
        self.planets = [p.copy() for p in self.map['planets']]
        for planet in self.planets:
            planet['res'] /= all_res
            planet['cos'] /= all_cos
            planet['def'] /= all_def
            planet['max'] /= all_max

    def cal_weight(self):
        planets = [p.copy() for p in self.planets]

        for planet in planets:
            planet['weight'] = (planet['res'] * 0.5 + planet['cos'] * 0.1 +
                    planet['def'] * 0.2 + planet['max'] * 0.2)

        for n, hold in enumerate(self.info['holds']):
            if not hold[0]:
                planets[n]['weight'] *= 10

        return sorted(
                [(n, p['weight']) for n, p in enumerate(planets)],
                key=lambda x:x[1])

    def get_best_planets(self, planets, weight):
        """
        return planets pairs, [(1, 2, 2)] means
        would move armies from planet 1 to 2 and round is 2
        """
        adjacency_planets = {}
        [adjacency_planets.setdefault(p, [])  for p in planets]

        for r in self.map['routes']:
            if r[0] in planets:
                adjacency_planets[r[0]].append([r[1], r[2]])

        pairs = []
        #fight with enemy
        for planet_id, planet_weight in weight:
            for pid, ad_pids in adjacency_planets.iteritems():
                pids = [p[0] for p in ad_pids]
                if planet_id in pids:
                    pairs.append([
                        pid, planet_id,
                        ad_pids[pids.index(planet_id)][1]
                        ])

        #random to reinforece armies
        fight_armies = [p[0] for p in pairs]
        idle_armies = set(planets).difference(fight_armies)
        import random
        for idle in idle_armies:
            pairs.append(idle,
                    fight_armies[random.randint(0, len(fight_armies)-1)], -1)

        return pairs

    def cal_new_acount(self, current, planet, round):
        if round <= 0:
            return current if current < planet['max'] else planet['max']
        return self.cal_new_acount(
                int(current * planet['res'] + planet['cos']),
                planet, round -1)

    def move(self, pairs):
        holds = self.info['holds']
        planets = self.map['planets']
        moves = []
        for me, anemy, round in pairs:
            my_armies = holds[me][1]
            if round == -1:
                moves.append([int(holds[me][1] * 2.0 / 3), me, anemy])
                print 'reinforece', moves
                continue

            enemy_armies = self.cal_new_acount(holds[anemy][1], planets[anemy],
                    round)
            if my_armies > enemy_armies:
                send_armies = int(enemy_armies + (my_armies - enemy_armies) / 2.0)
                moves.append([send_armies, me, anemy])
                holds[me][1] -= send_armies

        print self.info, self.map, moves
        return moves

    def step(self):
        weight = self.cal_weight()
        my_planets = [n for n, h in enumerate(self.info['holds']) if h[0] ==
                self.me['seq']]
        plants_pair = self.get_best_planets(my_planets, weight)
        return self.move(plants_pair)

    def is_restart(self):
        current_round = self.info['round']
        return True if current_round < 0 else False

def main():
    rs = SimpleAI()
    rs.cmd_map()
    rs.init_weight()
    rs.cmd_info()
    pre_round = rs.info['round']

    while True:
        time.sleep(0.1)
        rs.cmd_info()
        current_round = rs.info['round']
        if current_round <= pre_round:
            continue
        else:
            pre_round = current_round

        result = rs.step()
        rs.cmd_moves(result)

if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = ai_flreeyv2
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: ai_flreeyv2
"""
import json, time
import urllib, httplib, logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

SERVER = "localhost"
PORT = 9999
DIRS = [[-1, 0], [0, -1], [1, 0], [0, 1]]

class SimpleAI():
    def __init__(self, ai_name, side='python', room=0):
        self.conn = httplib.HTTPConnection(SERVER, PORT)
        self.room = room
        self.d = 0
        self.name = ai_name
        self.side = side
        self.me = None
        self.round = None

    def init(self):
        #获取地图
        self.cmd_map()
        #更新地图信息
        self.cmd_info()

        #得到当前的回合
        self.round = self.info['round']
        self.init_weight()

    def is_next_round(self):
        self.cmd_info()
        if not self.me and self.info['status'] == 'waitforplayer':
            self.cmd_add()
            self.init()

        # if not self.round: return
        current_round = self.info['round']
        next_round = False
        if current_round > self.round:
            self.round = current_round
            next_round = True
        return next_round

    def is_restart(self):
        current_round = self.info['round']
        return True if current_round < 0 else False


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
        # logging.debug(result)
        return json.loads(result)

    def cmd_add(self):
        result = self.cmd("add",
                          dict(name = self.name, side=self.side))
        if result.has_key('id'):
            self.me = result
            return self.me
    
    def cmd_map(self):
        self.map = self.cmd("map")

    def cmd_info(self):
        self.info = self.cmd("info")

    def cmd_moves(self, moves):
        #print self.me, moves
        return self.cmd("moves",
                        dict(id = self.me["id"],
                             moves = moves))

    def init_weight(self):
        all_res = 0
        all_cos = 0
        all_def = 0
        all_max = 0
        for planet in self.map['planets']:
            all_res += planet['res'] * 1.0
            all_cos += planet['cos'] * 1.0
            all_def += planet['def'] * 1.0
            all_max += planet['max'] * 1.0
        self.planets = [p.copy() for p in self.map['planets']]
        for planet in self.planets:
            planet['res'] /= all_res
            planet['cos'] /= all_cos
            planet['def'] /= all_def
            planet['max'] /= all_max

    def cal_weight(self):
        planets = [p.copy() for p in self.planets]

        for planet in planets:
            planet['weight'] = (planet['res'] * 0.5 + planet['cos'] * 0.1 +
                    planet['def'] * 0.2 + planet['max'] * 0.2)

        for n, hold in enumerate(self.info['holds']):
            if hold[0] is None:
                planets[n]['weight'] *= 1.1

        #TODO: if planets near by high resources, acc it's weight
        return sorted(
                [(n, p['weight']) for n, p in enumerate(planets)],
                key=lambda x:x[1])

    def get_adjacency_planets(self, planet_ids):
        adjacency_planets = {}
        [adjacency_planets.setdefault(p, [])  for p in planet_ids]

        for r in self.map['routes']:
            if r[0] in planet_ids and r[0] != r[1]:
                adjacency_planets[r[0]].append([r[1], r[2]])
        return adjacency_planets

    def get_round(self, start, end):
        for r in self.map['routes']:
            if r[0] == start and r[1] == start:
                return r[3]

    def get_best_planets(self, planets, weight):
        """
        return planets pairs, [(1, 2, 2)] means
        would move armies from planet 1 to 2 and round is 2
        """
        adjacency_planets = self.get_adjacency_planets(planets)
        adjacency_planets_copy = adjacency_planets.copy()
        pairs = []
        slow_down_conquer = False

        if len(self.get_myplanets()) >= len(self.info['holds']):
            slow_down_conquer = True

        dangerous = self.would_be_attacked()
        fighting_armies = []

        #conquer planet
        for colony_planet_id, planet_weight in weight:
            keys = adjacency_planets.keys()
            for k in keys:
                pid = k
                if pid in dangerous:
                    fighting_armies.insert(0, pid)
                    #continue
                ad_info = adjacency_planets[k]
                adjacency_pids = [p[0] for p in ad_info]
                if (colony_planet_id in adjacency_pids and colony_planet_id not
                in planets):
                    pairs.append([
                        pid, colony_planet_id,
                        ad_info[adjacency_pids.index(colony_planet_id)][1]
                        ])
                    #only get once in this step
                    #if slow_down_conquer:
                        #adjacency_planets.pop(pid)

        #random to reinforece armies
        fighting_armies.extend([p[0] for p in pairs])
        idle_armies = set(planets).difference(fighting_armies)

        for idle in idle_armies:
            ad_info = adjacency_planets_copy[idle]
            adjacency_pids = [p[0] for p in ad_info]
            planet_needed_help = set(fighting_armies).intersection(adjacency_pids)
            if planet_needed_help:
                pairs.append([idle, planet_needed_help.pop(), -1])
            else:
                #get_nearest_planet(idle, fighting_armies)
                #dijkstra(idle, fighting_armies
                #TODO: get the paths to nearelest planet 
                pairs.append([idle, sorted(adjacency_pids, reverse=True)[0], -1])

        return pairs

    def cal_new_acount(self, current, planet, round):
        if round <= 0:
            current if current < planet['max'] else planet['max']
            current = current * planet['def']
            return current
        return self.cal_new_acount(
                int(current * planet['res'] + planet['cos']),
                planet, round -1)

    def move(self, pairs):
        holds = self.info['holds']
        planets = self.map['planets']
        moves = []
        for me, anemy, round in pairs:
            my_armies = holds[me][1]

            #reinforece my planets
            if round == -1:
                send = int(my_armies * 2.0 / 3)
                holds[me][1] -= send
                moves.append([send, me, anemy])
            #conquer planets
            else:
                send_armies = 0
                if holds[anemy][0] is None:
                    #not conquer empty planets until enemy planets which is
                    #near empyt planet less than 2
                    enemy_planets_nearby_my_planet = self.get_nearby_anemies(me)
                    armies_less_than_my_planets = filter(lambda
                            x:self.cal_new_acount(holds[x][1], planets[x],
                                self.get_round(me, x)) >
                            holds[x][1], enemy_planets_nearby_my_planet)
                    if enemy_planets_nearby_my_planet:
                        #print 'enemy_planets_nearby_my_planet', enemy_planets_nearby_my_planet, armies_less_than_my_planets
                        if armies_less_than_my_planets:
                            anemy = armies_less_than_my_planets[0]
                            send_armies = int(holds[anemy][1] + (my_armies -
                                holds[anemy][1]) / 2.0)
                    else:
                        send_armies = int(my_armies * 2.0 / 3)
                else:
                    enemy_armies = self.cal_new_acount(holds[anemy][1], planets[anemy],
                            round)
                    if my_armies > enemy_armies:
                        send_armies = int(enemy_armies + (my_armies - enemy_armies) / 2.0)

                moves.append([send_armies, me, anemy])
                holds[me][1] -= send_armies

        return moves

    def would_be_attacked(self):
        moves = self.info['moves']
        my_planets = self.get_myplanets()
        dangerous = filter(lambda x:x[0] is not self.me['seq'] and x[2] in
                my_planets, moves)
        #if planet weight is hight and has anemy nearby 
        #assert it would be attacked
        #only need top 4 planet
        #top4 = [w[0] for w in self.cal_weight()[0:4]]
        #warning_planets = filter(lambda x:x in my_planets, top4)
        #s = set()
        #[s.update(self.get_nearby_anemies(p)) for p in warning_planets]
        #dangerous.extend(list(s))
        return dangerous



        return [d[2] for d in dangerous]

    def get_nearby_anemies(self, planet):
        ps = self.get_adjacency_planets([planet])
        holds = self.info['holds']
        return filter(lambda x:holds[x][0] is not self.me['seq'] and holds[x][0]
                is not None,
                [adinfo[0] for adinfo in ps[planet]])

    def get_myplanets(self):
        return [n for n, h in enumerate(self.info['holds']) if h[0] ==
                self.me['seq']]
    def step(self):
        if self.info['status'] == 'finished' or self.info['status'] == 'waitforplayer':
            self.me = None
            return
        weight = self.cal_weight()
        my_planets = self.get_myplanets()
        plants_pair = self.get_best_planets(my_planets, weight)
        return self.move(plants_pair)

def main(room=0):
    rs = SimpleAI('flreeyv2', 'python', room)

    while True:
        #服务器每三秒执行一次，所以没必要重复发送消息
        #time.sleep(0.1)
        #rs = SimpleAI('flreeyv2', 'python')
        #start = time.time()
        ##计算自己要执行的操作
        ##print timeit.timeit(rs.step)
        #result = rs.step()
        #print time.time() - start, rs.info['round'], result
        ##把操作发给服务器
        #rs.cmd_moves(result)
        time.sleep(1.4)
        
        if rs.is_next_round():
            start = time.time()
            #计算自己要执行的操作
            #print timeit.timeit(rs.step)
            result = rs.step()
            if not result: continue

            print time.time() - start, rs.info['round'], result
            #把操作发给服务器
            rs.cmd_moves(result)

if __name__=="__main__":
    main()




########NEW FILE########
__FILENAME__ = ai_halida
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: ai_halida
"""
import json, time, random
import urllib, httplib, logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

SERVER = "localhost"
PORT = 9999
DIRS = [[-1, 0], [0, -1], [1, 0], [0, 1]]

class SimpleAI():
    def __init__(self, room):
        self.conn = httplib.HTTPConnection(SERVER, PORT)
        self.room = room
        self.d = 0

    def cmd(self, cmd, data={}):
        """
        发送命令给服务器
        """
        data['op'] = cmd
        data['room'] = self.room
        # logging.debug('post: %s : %s', cmd, data)
        self.conn.request("POST", '/cmd',
                          urllib.urlencode({'data': json.dumps(data)}),
                          {'Content-Type': 'application/x-www-form-urlencoded'})
        result = self.conn.getresponse().read()
        return json.loads(result)

    def cmd_add(self):
        self.me = self.cmd("add",
                           dict(name = "halida",
                                side='python'))
        if not self.me.has_key('seq'): return
        
        self.user_id = self.me['seq']
        return self.me
    
    def cmd_map(self):
        self.map = self.cmd("map")

    def cmd_info(self):
        self.info = self.cmd("info")

    def step(self):
        moves = []
        small_hold = 10
        cs = [(i, s) for i, s in enumerate(self.info['holds'])]
        random.shuffle(cs)
        for i, s in cs:
        # for i, s in enumerate(self.info['holds']):
            side, count = s
            # 寻找自己的星球
            if side != self.user_id: continue

            for route in self.map['routes']:
                # # 数量超过一定程度的时候, 才派兵
                if count < small_hold:
                    break
                # 当前星球的路径, 并且对方星球不是自己的星球
                _from, to, step = route
                if _from != i or self.info['holds'][to][0] == self.user_id:
                    continue

                if self.info['holds'][to][1] > count:
                    continue
                # 派兵!
                moves.append([count/2, _from, to])
                count -= count/2

        move = dict(id = self.me["id"], moves = moves)

        tactic = self.choose_tactic()
        if tactic:
            move['tactic'] = tactic
            
        print move
        return self.cmd("moves", move)

    def choose_tactic(self):
        # check can use terminator
        if self.info['players'][self.user_id]['points'] < 2: return
        
        # get max unit player
        target_player = None
        target_count = 0
        for i, player in enumerate(self.info['players']):
            if i == self.user_id: continue
            if player["units"] < target_count: continue
            target_player = i
            target_count = player["units"]
                
        if target_player == None: return
        
        # random planet
        ps = [ i
               for i, v in enumerate(self.info["holds"])
               if v[0] == target_player
               ]
        if len(ps) <= 0: return
        planet = ps[random.randint(0, len(ps)-1)]
        return dict(type='terminator', planet=planet)

    def is_restart(self):
        current_round = self.info['round']
        return True if current_round < 0 else False

def main(room=0):
    while True:
        time.sleep(3)
        rs = SimpleAI(room)
        rs.cmd_map()
        
        if not rs.cmd_add(): next
        
        while True:
            time.sleep(1.0)
            rs.cmd_info()
            if rs.info['status'] == 'finished': break
            try:
                result = rs.step()
                print result
                if result['status'] == 'noid': break
            except:
                raise
    
if __name__=="__main__":
    main()




########NEW FILE########
__FILENAME__ = ai_lastland
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
author: 梦里醉逍遥 <hnkfliyao@gmail.com>
module: ai_lastland
"""
import json, time
import urllib, httplib, logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

SERVER = "localhost"
PORT = 9999
DIRS = [[-1, 0], [0, -1], [1, 0], [0, 1]]

class SimpleAI():
    def __init__(self, ai_name, side='python'):
        self.conn = httplib.HTTPConnection(SERVER, PORT)
        self.room = 0
        self.d = 0
	self.name = ai_name
	self.side = side
	self.me = None
	self.cmd_add(self.name, self.side)
	self.init()

    def init(self):
        #获取地图
        self.cmd_map()
        #更新地图信息
        self.cmd_info()

        #得到当前的回合
        self.round = self.info['round']

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

    def cmd_add(self, ai_name, side):
        self.me = self.cmd("add",
                           dict(name=ai_name, side=side))
        return self.me
    
    def cmd_map(self):
        self.map = self.cmd("map")

    def cmd_info(self):
        self.info = self.cmd("info")

    def cmd_moves(self, moves):
        #print self.me, moves
        return self.cmd("moves",
                        dict(id = self.me["id"],
                             moves = moves))
    def is_next_round(self):
        self.cmd_info()
	if not self.me and self.info['status'] == 'waitforplayer':
	    self.cmd_add(self.name, self.side)
	    self.init()

        current_round = self.info['round']
        next_round = False
        if current_round > self.round:
            self.round = current_round
            next_round = True
        return next_round

    def count_growth(self, planet_count, planet):
	max = planet['max']
	res = planet['res']
	cos = planet['cos']
	new_count = int(planet_count * res + cos)
	if planet_count < max:
	    planet_count = min(new_count, max)
	elif new_count < planet_count:
	    planet_count = new_count
	return planet_count

    def battle(self, move):
        side, _from, to, count, _round = move
        planet_side, planet_count = self.info['holds'][to]
        _def = self.map['planets'][to]['def']

        if planet_side == None:
            # 如果星球没有驻军, 就占领
            planet_side = side
            planet_count = count
        elif side == planet_side:
            # 如果是己方, 就加入
            planet_count += count
        else:
            # 敌方战斗
            # 防守方加权
            planet_count *= _def
            if planet_count == count:
                # 数量一样的话, 同时全灭
                planet_side, planet_count = None, 0
            elif planet_count < count:
                # 进攻方胜利
                planet_side = side
                planet_count = count - int(planet_count**2/float(count))
            else:
                # 防守方胜利                
                planet_count -= int(count**2/float(planet_count))
                planet_count = int(planet_count / _def)
        return planet_side, planet_count

    def get_myplanets(self):
	return [n for n, h in enumerate(self.info['holds']) if h[0] == self.me['seq']]

    def get_frontline_planets(self):
	routes = self.map['routes']
	my_planets = self.get_myplanets()
	frontlines = filter(lambda x:x[0] in my_planets and x[1] not in my_planets, routes)
	return [p[0] for p in frontlines]

    def get_dangerous_planets(self):
        moves = self.info['moves']
        my_planets = self.get_myplanets()
        dangerous = filter(lambda x:x[0] is not self.me['seq'] and x[2] in my_planets, moves)
	return dangerous

    def get_frontline_value(self, frontlines):
	value = dict()
	stack = []
	for p in frontlines:
	    value[p] = 0
	    for _from, _to, step in self.map['routes']:
		if _from == p and _to not in value:
		    value[_to] = 1
		    stack.append(_to)
	i = 0
	while i < len(stack):
	    for _from, _to, step in self.map['routes']:
		if _from == stack[i] and _to not in value:
		    value[_to] = value[stack[i]] + 1
		    stack.append(_to)
	    i += 1
	return value

    def count_after_n_steps(self, planet_id, n):
	moves = self.info['moves']
	owner, count = self.info['holds'][planet_id]
	for i in range(n):
	    # production
	    count = self.count_growth(count, self.map['planets'][planet_id])
	    for move in moves:
		if move[2] == planet_id and move[4] == i + 1:
		    print "%d将在%d回合后发生战斗！守方:%d, 进攻:%d" % (planet_id, i + 1, count, move[3])
		    owner, count = self.battle(move)
	    # reinforcements
	    #for seq, _, target, cnt, step in moves:
		#if target != planet_id or seq != owner or step != i:
		    #continue
		#count += cnt
	    # battle loss

	return owner, count

    def no_enermies_around(self, planet_id):
	for _from, _to in routes:
	    if _from == planet_id and _to in self.info['holds']:
		return false
	return  true


    def step(self):
	if self.info['status'] == 'finished' or self.info['status'] == 'waitforplayer':
	    print "游戏结束了"
	    self.me = None
	    return

        moves = []
        small_hold = 50
	frontlines = self.get_frontline_planets()
	dangerous = self.get_dangerous_planets()
	frontline_value = self.get_frontline_value(frontlines)
	
	dangerous_enermies = dict()

	for _, _, s, cnt, step in dangerous:
	    print s, cnt, step
	    if step == 1:
		if s not in dangerous_enermies:
		    dangerous_enermies[s] = cnt
		else:
		    dangerous_enermies[s] += cnt

	for s, cnt in dangerous_enermies.items():
	    my_cnt = self.info['holds'][s][1]
	    print "%d处于危险！我方：%d, 对方：%d" % (s, my_cnt, cnt)
	    if self.count_after_n_steps(s, 1)[0] == self.me['seq']:
		continue
	    print "打不过！"
	    # 打不过， 跑
	    sended = my_cnt
	    for route in self.map['routes']:
		_from, _to, step = route
		next_owner, next_cnt = self.count_after_n_steps(_to, step)
		if _from == s and (self.info['holds'][_to][0] == self.me['seq'] or next_cnt < sended): 
		    moves.append([sended, _from, _to])
		    self.info['holds'][s][1] -= sended 
		    break

        for i, s in enumerate(self.info['holds']):
            side, count = s
	    planet = self.map['planets'][i]
            # 寻找自己的星球
            if side != self.me['seq']:
                continue

	    # 援军把兵力运往前线
	    if i not in frontlines and i not in dangerous_enermies:
		sended = 0
		targets = []
		if planet['res'] <= 1:
		    sended = count - 1
		elif planet['max'] <= count or planet['res'] * count + planet['cos'] > planet['max']:
		    sended = count - (planet['max'] - planet['cos']) / planet['res']
		for _from, _to, step in self.map['routes']:
		    if self.count_after_n_steps(_to, step)[0] != self.me['seq']:
			continue
		    if _from == i and frontline_value[_to] < frontline_value[i]:
			targets.append(_to)
		if (len(targets) <= 0):
		    continue
		sended_each = int(sended / len(targets))
		if sended_each <= 0:
		    continue
		for t in targets:
		    moves.append([sended_each, i, t])
		    self.info['holds'][i][1] -= sended_each

            for route in self.map['routes']:
                # 数量超过一定程度的时候, 才派兵
                if count < small_hold:
                    break
                sended = int(count * 0.6)
                # 当前星球的路径, 并且对方星球不是自己的星球
                _from, to, step = route
		owner_of_to, count_of_to = self.count_after_n_steps(to, step)
                if _from != i or self.info['holds'][to][0] == self.me['seq']:
                    continue
		if count < planet['max'] and (owner_of_to == self.me['seq'] or count_of_to >= sended):
		    continue
		if count_of_to >= sended: 
		    sended = int(count - (planet['max'] - planet['cos']) / planet['res'])

                # 派兵!
                moves.append([sended, _from, to])
                count -= sended

        return moves

    def is_restart(self):
        current_round = self.info['round']
        return True if current_round < 0 else False

def main(room=0):
    player_nickname = 'lastland'
    language = 'python' #ruby or python
    rs = SimpleAI(player_nickname, language)
    while True:
        #服务器每三秒执行一次，所以没必要重复发送消息
        time.sleep(1)
        #rs = SimpleAI()
        if rs.is_next_round():
            #计算自己要执行的操作
            result = rs.step()
            #把操作发给服务器
            rs.cmd_moves(result)

if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = ai_tutorial
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: ai_tutorial
"""
import json, time
import urllib, httplib, logging

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

SERVER = "localhost"
PORT = 9999
DIRS = [[-1, 0], [0, -1], [1, 0], [0, 1]]

class SimpleAI():
    def __init__(self, ai_name, side='python'):
        self.conn = httplib.HTTPConnection(SERVER, PORT)
        self.room = 0
        self.d = 0
        #加入房间
        self.cmd_add(ai_name, side)
        #获取地图
        self.cmd_map()
        #更新地图信息
        self.cmd_info()

        #得到当前的回合
        self.round = self.info['round']

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

    def cmd_add(self, ai_name, side):
        self.me = self.cmd("add",
                           dict(name=ai_name, side=side))
        return self.me
    
    def cmd_map(self):
        self.map = self.cmd("map")

    def cmd_info(self):
        self.info = self.cmd("info")

    def cmd_moves(self, moves):
        #print self.me, moves
        return self.cmd("moves",
                        dict(id = self.me["id"],
                             moves = moves))
    def is_next_round(self):
        self.cmd_info()
        current_round = self.info['round']
        next_round = False
        if current_round > self.round:
            self.round = current_round
            next_round = True
        return next_round

    def step(self):
        moves = []
        small_hold = 50

        for i, s in enumerate(self.info['holds']):
            side, count = s
            # 寻找自己的星球
            if side != self.me['seq']:
                continue

            for route in self.map['routes']:
                # 数量超过一定程度的时候, 才派兵
                if count < small_hold:
                    break
                sended = count / 2
                # 当前星球的路径, 并且对方星球不是自己的星球
                _from, to, step = route
                if _from != i or self.info['holds'][to][0] == self.me['seq']:
                    continue

                # 派兵!
                moves.append([sended, _from, to])
                count -= sended

        return moves

    def is_restart(self):
        current_round = self.info['round']
        return True if current_round < 0 else False

def main():
    player_nickname = 'tutorial'
    language = 'python' #ruby or python
    rs = SimpleAI(player_nickname, language)
    while True:
        #服务器每三秒执行一次，所以没必要重复发送消息
        time.sleep(1)
        rs = SimpleAI()
        if rs.is_next_round():
            #计算自己要执行的操作
            result = rs.step()
            #把操作发给服务器
            rs.cmd_moves(result)

if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = ai_yangchen
#-*- coding:utf-8 -*-
"""
author: yangchen <ignoramus365@gmail.com>
module: ai_tutorial
"""
import json, time
import urllib, httplib, logging

import copy

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

#SERVER = 'localhost'
#SERVER = "10.10.99.183"
#SERVER = "pythonvsruby.org"
SERVER = "localhost"
PORT = 9999
DIRS = [[-1, 0], [0, -1], [1, 0], [0, 1]]

def print_dict(d):
    for k in d:
        print k, ':', d[k]

class SimpleAI():
    def __init__(self, ai_name, side='python', room=0):
        self.conn = httplib.HTTPConnection(SERVER, PORT)
        self.room = room
        self.d = 0

        #加入房间
        self.cmd_add(ai_name, side)
        #获取地图
        self.cmd_map()
        #更新地图信息
        self.cmd_info()
        #得到当前的回合
        self.round = self.info['round']

        # constants

        self.M = 100

        # weights
        self.DANGER = 8
        self.FLEE = 9
        self.REIN = 10

        # seqs
        self.ME = set([self.me["seq"]])
        self.ALL = set([None, 0, 1, 2, 3])
        self.NOTME = self.ALL - self.ME

        if self.me["seq"] < 3:
            self.PRI = True
        else:
            self.PRI = False

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

    def cmd_add(self, ai_name, side):
        result = self.cmd("add",
                           dict(name=ai_name, side=side))

        if result.has_key('id'):
            self.me = result
            return self.me

    def cmd_map(self):
        self.map = self.cmd("map")

    def cmd_info(self):
        self.info = self.cmd("info")

    def cmd_moves(self, moves):
        return self.cmd("moves",
                        dict(id = self.me["id"],
                             moves = moves))

    def is_next_round(self):
        self.cmd_info()
        current_round = self.info['round']
        next_round = False
        if current_round > self.round:
            self.round = current_round
            next_round = True
        return next_round

    def get_myplanets(self):
        myplanets = {}
        for i, p in enumerate(self.info['holds']):
            if p[0] == self.me["seq"]:
                myplanets[i] = p[1]

        #self.myplanets = myplanets
        return myplanets

    def get_frontiers(self, myplanets = None):
        if myplanets == None:
            myplanets = self.myplanets
        frontiers = {}

        # find frontier planets
        for route in self.map["routes"]:
            if route[0] in myplanets and not route[1] in myplanets:
                fr = route[1]
                defence = self.exp_defence(fr, route[2])
                frontiers[fr] = defence

        #self.frontiers = frontiers
        return frontiers

    def get_positions(self):
        positions = {}
        for planet in self.frontiers:
            positions[planet] = 0

        totalnp = len(self.map["planets"])

        # ugly
        if len(positions) == 0:
            return dict([(i, 0) for i in range(totalnp)])

        #print 'totalnp', totalnp
        np = len(positions)
        dist = 1
        while np < totalnp:
            pos = {}
            for route in self.map["routes"]:
                if route[1] in positions and not route[0] in positions and not route[0] in pos:
                    pos[route[0]] = dist
                    np = np + 1
            dist = dist + 1
            positions = dict(positions.items() + pos.items())

        #self.positons = positions
        return positions

    def get_plweights(self):
        NUMweights = 12

        positions = self.get_positions()
        plweights = [[0] * NUMweights for i in range(len(self.map["planets"]))]
        for i, weight in enumerate(plweights):
            plweights[i][0] = i
            plweights[i][1] = positions[i]
            plweights[i][2] = self.info["holds"][i][1]
            plweights[i][3] = self.map["planets"][i]["def"]
            plweights[i][4] = self.map["planets"][i]["res"]
            plweights[i][5] = self.map["planets"][i]["max"]
            #plweights[i][6] = self.compute_geo(i)
            #plweights[i][7] = self.compute_hub(i)
            plweights[i][8] = False
            plweights[i][9] = False
            plweights[i][10] = False

        #self.plweights = plweights
        return plweights

    def get_emptyfrontiers(self):
        return [frontier for frontier in self.frontiers if self.info["holds"][frontier][1] == 0]

    def get_neighbors(self, planet):
        return [route[1] for route in self.map["routes"] if route[0] == planet]

    def get_dist(self, _from, _to):
        for r in self.map["routes"]:
            if r[0] == _from and r[1] == _to:
                return r[2]
        return self.M

    def get_movein(self, planet, seqs = []):
        movein = []
        for move in self.info["moves"]:
            if move[2] == planet and move[0] in seqs:
                    movein.append(move)

        return movein

    def compute_troopin(self, pl, seqs = [], rounds = None):
        if rounds == None:
            rounds = self.M
        if seqs == []:
            seqs = [self.info["holds"][pl][0]]

        movein = self.get_movein(pl, seqs)
        return sum([move[3] for move in movein if move[4] <= rounds])

    '''
    def compute_armyaround(self, pl, seqs = []):
        if seqs == []:
            seqs = [self.info["holds"][pl][0]]

        armyaround = 0
        for nb in self.get_neighbors(pl):
            if self.info["holds"][nb][0] in seqs:
                armyaround += self.info["holds"][nb][1]
        return armyaround
    '''

    def exp_env(self, pl, seqs = []):
    # weighted armyaround
        if seqs == []:
            seqs = [self.info["holds"][pl][0]]

        env = 0
        for nb in [i for i in self.get_neighbors(pl) if self.info["holds"][i][0] in seqs]:
            env += self.info["holds"][nb][1] / self.get_dist(nb, pl) ** 2
        return env

    def compute_defence(self, fr, rounds, acc = 0):
        dec = self.map["planets"][fr]["def"] 
        res = self.map["planets"][fr]["res"]
        cos = self.map["planets"][fr]["cos"]
        mam = self.map["planets"][fr]["max"]
        hold = self.info["holds"][fr][1]

        if hold > mam:
            return hold

        if acc == 0:
            acc = hold
        acc = min(mam, acc * res + cos)
        if rounds > 1:
            defence = self.compute_defence(fr, rounds - 1, acc)
        else:
            defence = dec * acc
        return defence

    def exp_doomday(self, pl):
        deff = self.exp_defence(pl, 1)
        moves = self.get_movein(pl, self.NOTME)
        moves = sorted(moves, key = lambda x: x[4])
        for move in moves:
            deff -= move[3]
            if deff < 0:
                return move[4], move[0]
        return self.M, self.me["seq"]

    def exp_defence(self, pl, rounds = None):
        dec = self.map["planets"][pl]["def"] 
        troopin = self.compute_troopin(pl, [self.info["holds"][pl][0]], rounds)
        return dec * troopin + self.compute_defence(pl, rounds)

    def exp_hold(self, pl, rounds = None):
        if rounds == None:
            rounds = self.M

        hold = self.info["holds"][pl][1]
        for move in self.info["moves"]:
            if move[2] == pl and move[0] == self.info["holds"][pl][0] and move[4] <= rounds:
                hold += move[3]
        return hold

    def compute_hub(self, planet):
        geo = 0
        for route in self.map["routes"]:
            if route[0] == planet and route[1] in self.myplanets and not self.plweights[route[1]][self.FLEE]:
                geo += 1
        return -geo

    def compute_geo(self, planet):  # 周围有更多我城
        oripl = set([pl for pl in self.myplanets if not self.plweights[pl][self.FLEE]]) - set([planet])
        exppl = oripl or set([planet])
        return len(self.get_frontiers(list(exppl))) - len(self.get_frontiers(list(oripl)))
        
    def compute_ext(self, planet):  # 周围有更多空城
        ext = 0
        for route in self.map["routes"]:
            if route[0] == planet and self.info["holds"][route[1]][0] == None:
                ext += 1
        return -ext


    def whether_transport(self, _from):
        small_hold = 150

        res = self.map["planets"][_from]["res"]
        cos = self.map["planets"][_from]["cos"]
        mam = self.map["planets"][_from]["max"]
        pos = self.plweights[_from][1]
        count = self.myplanets[_from]

        if self.plweights[_from][self.DANGER]:
            return False
        if pos == 1 and count >= mam and len(self.get_movein(_from, self.ME)) == 0 and len(self.get_movein(_from, self.NOTME)) == 0:
        # 前线调度
            return True
        if pos > 1 and res > 1 and count * res + cos >= 0.9 * mam:
            return True
        if pos > 1 and res <= 1 and count > min([small_hold - (pos - 2) * 30, mam * 2 / 3]):  
        # 运输：res 大的晚
            return True
        return False

    def where_transport(self, _from):
        pos = self.plweights[_from][1]

        dests = [self.plweights[i] for i in self.get_neighbors(_from) if i in self.myplanets]
        order = sorted(dests, key = lambda x: (x[1], self.compute_geo(x[0]), self.get_dist(_from, x[0]), -int(x[2]/100), -x[3]))  # 前线, 防高, 人多
        for wt in order:
            _to = wt[0]
            if not self.plweights[_to][self.DANGER] and len([i for i in self.roundmoves if i[2] == _to]) < 3 and len(self.get_movein(_to, self.NOTME)) == 0:
            #if not self.plweights[_to][self.DANGER]:
                return _to
        return None

    def amount_transport(self, _from):
        count = self.myplanets[_from]
        pos = self.plweights[_from][1]
        res = self.map["planets"][_from]["res"]
        cos = self.map["planets"][_from]["cos"]
        return min((res - 1) / res * count + cos + count * pos / 5, count * 9 / 10) # 越远越多

    def whether_dangerous(self, _from):
        atk = self.compute_troopin(_from, self.NOTME)
        if atk > self.exp_defence(_from, 1):
            return True
        return False

    def whether_flee(self, _from):
        ## Why same round 
        dec = self.map["planets"][_from]["def"]
        troopin = self.compute_troopin(_from, self.NOTME, 1)
        if self.exp_defence(_from, 2) < troopin:
            return True
        #if dec < 1 and self.exp_defence(_from, 2) < troopin / (dec + 0.1):  # def 越小越跑
        #    return True
        # ugly
        nbseqs = [self.info["holds"][i][0] for i in self.get_neighbors(_from)]
        if not None in nbseqs and not self.me["seq"] in nbseqs and len(self.get_movein(_from, self.ME)) == 0:
            return True
        return False

    def where_flee(self, _from):
        send = self.info["holds"][_from][1]

        _to = self.where_transport(_from)
        if _to != None:
            return _to

        _to = self.where_seize(_from, send)
        if _to != None and self.compute_hub(_to) <= -2:
            return _to

        _to = self.where_attack(_from, send)
        if _to != None and self.compute_hub(_to) <= -2:
            return _to

        return sorted([self.plweights[i] for i in self.get_neighbors(_from)], key = lambda x: (self.compute_hub(x[0]), x[2]))[0][0]

    def amount_attack(self, _from):
        dec = self.map["planets"][_from]["def"]

        maxhold = self.exp_hold(_from)
        atk = self.compute_troopin(_from, self.NOTME)
        hold = self.info["holds"][_from][1]

        # the less the def, the more out
        count = self.exp_defence(_from, 1) - atk - hold * dec * 0.4 + self.exp_env(_from, self.ME) - self.exp_env(_from, self.NOTME)
        return min(count, hold * 4 / 5)

    def where_seize(self, _from, send = 0):
        weights = [self.plweights[i] for i in self.get_neighbors(_from) if self.plweights[i][self.DANGER]]
        weakorder = sorted(weights, key = lambda x : (self.compute_geo(x[0]), self.compute_hub(x[0]), -x[4]))  # 地利，资高

        for wt in weakorder:
            _to = wt[0]
            if self.whether_seize(_from, _to, send):
                return _to
        return None

    def where_attack(self, _from, send = 0):
        neighbors = self.get_neighbors(_from)
        frweights = [self.plweights[i] for i in self.frontiers if i in neighbors]

        weakorder = sorted(frweights, key=lambda x : (self.compute_geo(x[0]), self.compute_hub(x[0]), int(self.frontiers[x[0]]/10), -x[4]))  # 地利，弱，资高

        for wt in weakorder:
            _to = wt[0]
            if self.whether_attack(_from, _to, send):
                return _to
        return None

    def is_enough(self, _to):
        already = len(self.get_movein(_to, self.ME))
        cround = len([i for i in self.roundmoves if i[2] == _to])
        if already >= 3:
            return True
        if cround >= 2:
            return True
        return False

    def whether_seize(self, _from, _to, send = 0):
        rounds, xseq = self.exp_doomday(_to)
        defc = self.map["planets"][_to]["def"]

        movein = self.get_movein(_to, self.NOTME)

        atk = self.compute_troopin(_to, self.NOTME) * 1.1 + self.exp_env(_to, self.NOTME)
        if atk < send and not self.is_enough(_to):
            if defc > 1 and self.get_dist(_from, _to) < rounds:
                self.plweights[_to][self.REIN] = True
                return True
            if defc < 1 and self.get_dist(_from, _to) > rounds + 1 and len(set([move[0] for move in movein])) == 1:
                return True
        return False

    def whether_attack(self, _from, _to, send = 0):
        defc = self.map["planets"][_to]["def"]

        moves = self.get_movein(_to, self.NOTME)
        moves = sorted(moves, key = lambda x: x[4])

        if len(moves) > 0:
            move = moves[0]
            move2 = moves[-1]
            #if (defc < 1 and self.get_dist(_from, _to) > move[4] and self.me["seq"] > move[0]) or (defc >= 1 and self.get_dist(_from, _to) < move[4] and self.me["seq"] > move[1]):
            if (defc < 1 and self.get_dist(_from, _to) > move2[4]) or (defc >= 1 and self.get_dist(_from, _to) < move[4]):
                pass
            else:
                return False

        deff = self.exp_defence(_to, self.get_dist(_from, _to)) * 1.1 + self.exp_env(_to) / 2
        if deff < send and not self.is_enough(_to):
            return True
        return False

    def update_moves(self, move):
        self.info["moves"] += [[self.me["seq"], move[1], move[2], move[0], self.get_dist(move[1], move[2])]]
        self.roundmoves.append(move)

    def race(self):
        racemoves = []

        for _from in self.myplanets:
            empty = [self.plweights[i] for i in self.get_neighbors(_from) if self.info["holds"][i][0] == None]
            count = self.myplanets[_from]
         
            for wt in sorted(empty, key=lambda x : (self.compute_ext(x[0]))):
                _to = wt[0]
                '''
                if len(self.get_movein(_to, self.NOTME)) > 0:
                    self.plweights[_to][self.DANGER] = True
                    continue
                '''
                if len(self.get_movein(_to, self.ME)) <= 2 and count > 1:
                    send = count * 2 / 3
                    count = count - send
                    racemoves.append([send, _from, _to])
                    self.update_moves([send, _from, _to])
                    
            self.myplanets[_from] = count

        #print 'race: ', moves
        return racemoves

    def attack(self):

        attackmoves = []

        for _from in self.myplanets:

            # dangerous planet should not attack
            if self.plweights[_from][self.DANGER]:
                continue

            send = self.amount_attack(_from)

            # seize
            _to = self.where_seize(_from, send)
            if _to != None:
                attackmoves.append([send, _from, _to])
                self.update_moves([send, _from, _to])
                self.myplanets[_from] -= send

            # invade
            _to = self.where_attack(_from, send)
            if _to != None:
                attackmoves.append([send, _from, _to])
                self.update_moves([send, _from, _to])
                self.myplanets[_from] -= send
                
        print 'attack', attackmoves
        return attackmoves

    def flee(self):
        fleemoves = []

        # find dangerous
        dangerous = []
        for _from in self.myplanets:
            if self.whether_dangerous(_from):
                self.plweights[_from][self.DANGER] = True
                dangerous.append(_from)

        # flee from
        flee = []
        for _from in self.myplanets:
            if self.whether_flee(_from):
                self.plweights[_from][self.FLEE] = True
                flee.append(_from)

        for _from in flee:
            _to = self.where_flee(_from)
            if _to != None:
                send = self.info["holds"][_from][1]
                fleemoves.append([send, _from, _to])
                self.update_moves([send, _from, _to])
                self.myplanets[_from] -= send

        print 'flee', fleemoves
        return fleemoves

    def deploy(self):

        deploymoves = []

        for _from in self.myplanets:
            if self.whether_transport(_from):
                _to = self.where_transport(_from)
                if _to != None:
                    send = self.amount_transport(_from)
                    deploymoves.append([send, _from, _to])
                    self.update_moves([send, _from, _to])
                    self.myplanets[_from] -= send

        deploymoves = sorted(deploymoves, key = lambda x: x[0], reverse = True)

        print 'deploy', deploymoves
        return deploymoves

    def init_round(self):
        self.roundmoves = []
        self.myplanets = self.get_myplanets()
        self.frontiers = self.get_frontiers()
        self.plweights = self.get_plweights()

    def step(self):

        self.init_round()

        moves = []
        moves = moves + self.flee()
        moves = moves + self.race()
        moves = moves + self.attack()
        moves = moves + self.deploy()

        print 'myplanets', self.myplanets
        print 'frontiers', self.frontiers
        print 'plweights', self.plweights

        print 'holds', self.info["holds"]
        print 'routes', self.map["routes"]
        print 'moves: ', self.info["moves"]


        print 'round moves: ', moves
        print 'total round moves: ', len(moves)
        return moves

    def is_restart(self):
        current_round = self.info['round']
        return True if current_round < 0 else False

def main(room = 0):
    player_nickname = 'yangchen'
    language = 'python' #ruby or python
    rs = SimpleAI(player_nickname, language, room)

    while True:
        #服务器每三秒执行一次，所以没必要重复发送消息
        time.sleep(1)
        #rs = SimpleAI(player_nickname, language)
        if rs.is_next_round():
            print 'round', ':', rs.round
            #计算自己要执行的操作
            result = rs.step()
            #把操作发给服务器
            rs.cmd_moves(result)
        '''
        try:
            #服务器每三秒执行一次，所以没必要重复发送消息
            time.sleep(1)
            #rs = SimpleAI(player_nickname, language)
            if rs.is_next_round():
                print 'round', ':', rs.round
                #计算自己要执行的操作
                result = rs.step()
                #把操作发给服务器
                rs.cmd_moves(result)
        except:
            continue
        '''

if __name__=="__main__":
    main()


########NEW FILE########
__FILENAME__ = libai
# -*- coding:utf-8 -*- #

import urllib, httplib, json

class Server(object):
    """docstring for Server"""
    def __init__(self):
        pass

    def _cmd(self, cmd, data={}):
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

    def add_player(self, ai_name, language):
        return self._cmd("add", dict(name=ai_name, side=language))

    def get_map(self):
        return self._cmd("map")

    def get_info(self):
        return self._cmd('info')

    def is_next_round(self):
        pass

########NEW FILE########
__FILENAME__ = running
import os, sys, time
from multiprocessing import Process, Queue

class Logger(object):
    def __init__(self, name):
        if not os.path.exists('log'):
            try:
                os.mkdir('log')
            except OSError:
                print 'can\'t make dir log'
                sys.exit(1)
        self.f = open(os.path.join('log', name), 'w')

    def write(self, s):
        self.f.write(s)
        self.f.flush()

    def __del__(self):
        self.f.close()

    def flush(self):
        self.f.flush()

def start_game(q):
    from srcs.zmq_game_server import Server
    sys.stdout = Logger('game.log')
    from srcs.lib import GEME_STEP_TIME
    Server().run(max_waits=GEME_STEP_TIME,
                 min_waits=GEME_STEP_TIME,
                 enable_no_resp_die=False,
                 msg_queue=q)

def start_http():
    from srcs import web_server
    sys.stdout = Logger('http.log')
    #application.settings['debug'] = False
    #application.listen(9999)
    #try:
        #ioloop.IOLoop.instance().start()
    #except KeyboardInterrupt:
        #print "bye!"

    web_server.main()

def start_ai(name, roomid):
    ai = __import__('examples.%s' % name, globals(), locals(), ['main'])
    sys.stdout = Logger('%s.log' % name)
    ai.main(roomid)

def start_brower():
    import webbrowser
    webbrowser.GenericBrowser('google-chrome').open('./website/build/room_0.html')

def start_room(roomid, rooms):
    ais = rooms.get(roomid)[0]
    ps = rooms.get(roomid)[1]
    if ps:
        stop_room(roomid, rooms)
    else:
        [ps.append(Process(target=start_ai, args=(ai, roomid))) for ai in ais]
        [p.start() for p in ps]

def stop_room(roomid, rooms):
    ps = rooms[roomid][1]
    [r.terminate() for r in ps]

def run_all():
    ps = []
    q = Queue()
    ps.append(Process(target=start_game, args=(q,)))
    ps.append(Process(target=start_http))
    # ps.append(Process(target=start_brower))

    for p in ps:
        time.sleep(1)
        p.start()

    rooms = {0: [['ai_flreeyv2', 'ai_flreeyv2', 'ai_flreeyv2', 'ai_flreeyv2'], []]}
    k = 4
    for i in range(k):
        rooms[i] = [['ai_flreeyv2','ai_flreeyv2','ai_flreeyv2','ai_flreeyv2'], []]
    # rooms.update({1: [['ai_flreeyv2', 'ai_flreeyv2'], []]})
    for i in range(k):
        start_room(i, rooms)
    #start_room(1, rooms)

    while True:
        try:
            roomid = q.get()
            stop_room(roomid, rooms)
            time.sleep(3)
            start_room(roomid, rooms)
        except KeyboardInterrupt:
            break

def kill_all():
    pass

def main():
    run_all()

if __name__ == '__main__':
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
__FILENAME__ = game
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: player_game
"""
from lib import *
from map.map import Map
from scores import add_score
import math

# 游戏状态
WAITFORPLAYER='waitforplayer'
RUNNING='running'
FINISHED='finished'
MAINTAIN_LEVEL_1 = 1.5
MAINTAIN_LEVEL_2 = 2

#DEFAULT_MAP = 'srcs/map/fight_here.yml'
DEFAULT_MAP = 'srcs/map/test.yml'

MAX_LOST_TURN = 3

TACTIC_COST = {
    'terminator': 3,
    }

class Player():
    def __init__(self, game, name="", side='python'):
        """设置player
        """
        self.game = game
        self.name = name
        self.side = side
        self.id = uuid.uuid4().hex
        self.alive = True

    def get_info(self):
        if self.alive:
            self.status = "alive"
        else:
            self.status = "dead"
        return dict(name=self.name,
                    side=self.side,
                    status=self.status)

class Game():
    """游戏场景"""
    # 记录分数
    def __init__(self,
                 enable_no_resp_die=True,
                 map=None):
        self.enable_no_resp_die = enable_no_resp_die

        if not map:
            m = Map.loadfile(DEFAULT_MAP)
        else:
            m = Map.loadfile(map)
            
        self.set_map(m)            
        
        self.map_max_units = m.max_sum
        self.maintain_fee = m.meta.get('maintain_fee', False)
        self.start()

    def log(self, msg):
        self.logs.append(dict(type='msg', msg=msg))
        # self.logs.append(msg)

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
        self.planets = self.map.planets
        self.routes = self.map.routes
        self.max_round = self.map.max_round

    def start(self):
        self.logs = []
        self.info = None

        self.round = 0
        self.moves = []
        self.players = []
        self.loop_count = 0
        
        self.player_ops = []
        self.player_points = []
        self.player_tactics = []
        
        self.status = WAITFORPLAYER

        self.holds = [[None, 0] for i in range(len(self.map.planets))]
        
    def add_player(self, name="unknown", side='python'):
        # 限制人数
        if len(self.players) >= self.map.max_player:
            return dict(status="full")
        # 生成玩家
        player = Player(self, name, side)
        self.players.append(player)
        self.player_ops.append(None)
        self.player_points.append(0)
        self.player_tactics.append(None)
        # 强制更新info
        self.info = None
        # 玩家加入地图
        player_id = len(self.players)-1
        planet_id = self.map.starts[player_id]
        self.holds[planet_id] = [player_id, self.map.meta['start_unit']]
        # 用户加入时调整维护费用
        self.adjust_mt_fee()
        # 返回玩家的顺序, 以及玩家的id(用来验证控制权限)
        return dict(seq=len(self.players) - 1, id=player.id)

    def adjust_mt_fee(self):
        """动态调整维修费用"""
        active_players = len([i for i in self.players if i.alive])
        self.mt_base_line = int(self.map_max_units / float(2) / active_players)

    def get_seq(self, id):
        """根据玩家的id获取seq"""
        for i, s in enumerate(self.players):
            if s.id == id:
                return i

    def set_player_op(self, id, kw):
        # 获取玩家的seq
        n = self.get_seq(id)
        if n == None:
            return "noid"
        # 检查玩家是否还活着
        if not self.players[n].alive:
            return "not alive"
        
        try:
            if kw['op'] == 'moves':
                return self.set_player_moves(n, kw)
            else:
                return 'wrong op: ' + kw['op']
        except Exception as e:
            return 'invalid command: ' + e.message

    def set_player_moves(self, n, kw):
        moves = []
        for count, _from, to in kw['moves']:
            count = int(count)
            if count <= 0: continue
            # 检查moves合法性
            owner, armies = self.holds[_from]
            if owner != n:
                self.log('not your planet, round=%s, move=[%s, %s, %s]') % (self.round, armies, _from, to)
                continue
            elif armies < count:
                self.log('not enuough armies, round=%s, move=[%s, %s, %s]') % (self.round, armies, _from, to)
                continue
            elif count < 1:
                self.log('no impositive armies, round=%s, move=[%s, %s, %s]') % (self.round, armies, _from, to)
                continue
            step = self.routes[(_from, to)]
            moves.append([n, _from, to, count, step])
            
        if kw.has_key('tactic'):
            tactic = kw['tactic']
            if tactic['type'] not in TACTIC_COST.keys():
                return "wrong tactic type: %s" % tactic['type']
            if TACTIC_COST[tactic['type']] > self.player_points[n]:
                return "no enough points"
            # todo check tactic
            self.player_tactics[n] = tactic
            
        self.player_ops[n] = moves
        #print 'set_player_op id:%s'% n, self.round, self.player_ops, moves
        return 'ok'

    def do_player_op(self, n):
        for move in self.player_ops[n]:
            # check count <= self.holds[_from]
            side, _from, _to, count, step = move
            if count <= self.holds[_from][1]:
                # go!
                self.holds[_from][1] -= count
                self.moves.append(move)
                self.logs.append(
                    {'type': 'move',
                     'side': side,
                     'from': _from,
                     'to': _to,
                     'count': count,
                     'step': step,
                     })

                # if all my armies gone?
                if self.holds[_from][1] <= 0:
                    self.holds[_from] = [None, 0]
        self.player_ops[n] = None

        if self.player_tactics[n]:
            tactic = self.player_tactics[n]
            if tactic["type"] == 'terminator':
                planet = tactic["planet"]
                self.holds[planet] = [None, 0]
                self.player_points[n] -= TACTIC_COST['terminator']
                self.logs.append({
                    'type': "tactic",
                    'tactic': tactic,
                    })
        self.player_tactics[n] = None
            

    def check_winner(self):
        """
        胜利判断按照: 星球总数, 单位数量, 玩家顺序 依个判断数值哪个玩家最高来算. (不会出现平局)
        同时计算最高分, 保存到历史中
        """
        scores = [
            [p['planets'], p['units'], i]
            for i, p in enumerate(self.get_player_infos())
            ]

        maxid = max(scores)[2]
        winner = self.players[maxid]
        self.log('game finished, winner: ' + winner.name)
        # 再加到最高分里面去
        add_score(datetime.datetime.now(), winner.name)
        return maxid

    def get_map(self):
        return dict(routes=self.map.seq_routes,
                    planets=self.planets,
                    max_round=self.max_round,
                    desc=self.map.desc,
                    name=self.map.name,
                    author=self.map.author,
                    map_size = self.map.map_size,
                    step = GEME_STEP_TIME,
                    )

    def get_player_infos(self):
        player_infos = [p.get_info() for p in self.players]
        # count planets and units
        for p in player_infos:
            p["planets"] = 0
            p["units"] = 0
        for side, count in self.holds:
            if side == None: continue
            player_infos[side]["planets"] += 1
            player_infos[side]["units"] += count
        for move in self.moves:
            side = move[0]
            count = move[3]
            player_infos[side]["units"] += count
        for side, points in enumerate(self.player_points):
            player_infos[side]['points'] = points
        return player_infos

    def get_info(self):
        if self.info:
            return self.info
        
        self.info = dict(round=self.round,
                         status=self.status,
                         players=self.get_player_infos(),
                         moves=self.moves,
                         holds=self.holds,
                         logs=self.logs)
        return self.info

    def check_finished(self):
        """
        检查游戏是否结束
        当回合限制到达或者只有一个玩家剩下的时候, 游戏结束.
        """
        if self.round > self.max_round:
            return True

        player_infos = self.get_player_infos()
        
        # save user alive status
        for i, p in enumerate(player_infos):
            self.players[i].alive = p['units'] > 0

        alives = [True
                  for p in player_infos
                  if p['units'] > 0]
        if sum(alives) <= 1:
            return True

    def move_stage(self):
        for i, d in enumerate(self.player_ops):
            player = self.players[i]
            if not player.alive: continue

            # 如果连续没有响应超过MAX_LOST_TURN次, 让玩家死掉
            if d == None and self.enable_no_resp_die:
                self.no_response_player_die(player, self.round)

            if d != None:
                self.do_player_op(i)

    def arrive_stage(self):
        # time steps
        for move in self.moves:
            move[-1] -= 1
        # find arrived units
        arrives = [move for move in self.moves
                   if move[-1]==0]
        # remove arrived moves
        self.moves = [move for move in self.moves
                      if move[-1]>0]
        return arrives
    
    def battle_stage(self, arrives):
        for i in range(len(self.holds)):
            # move[2] means destination of move
            arrive_moves = [move for move in arrives
	                  if move[2] == i]
            if len(arrive_moves) > 0:
                self.battle_multi(arrive_moves, i)

    def battle_multi(self, arrivemoves, to):
        # 按节点进行结算
        army = {}
        planet_side, planet_count = self.holds[to]
        _def = self.planets[to]['def']
        _old_planet_count = planet_count
        _reinforce_count = 0
        if planet_side != None:
            army[planet_side] = planet_count * _def

	for i,move in enumerate(arrivemoves):
            # move[0] is side of move
            if move[0] not in army:
                army[move[0]] = 0
            army[move[0]] += move[3]

        # 记录援军数量
        if planet_side != None:
            _reinforce_count = army[planet_side] - _old_planet_count * _def

	best_army = None
        for key in army:
            if best_army == None:
                best_army = key
            elif army[key] > army[best_army]:
                best_army = key

        if best_army == None:
            self.logs.append(dict(type = "army",armys = army))
            return
        planet_count = army[best_army]
        if len(army) > 1:
            for key in army:
                # 数量一样的话，全灭
                if key != best_army:
                    if army[key] == army[best_army]:
                        planet_side, planet_count = None, 0
                        break
                    planet_count -= int(math.ceil(army[key]**2/float(army[best_army]*(len(army)-1))))

        if planet_side == None:
            # 如果星球没有驻军, 就占领
            planet_side = best_army
            self.logs.append(dict(type= "occupy",
                                  side=planet_side,
                                  count=planet_count,
                                  planet=to)) 
        else:
            # 防守方加权
            if best_army == planet_side:
                _pre_battle = _old_planet_count * _def + _reinforce_count
                planet_count = int((_reinforce_count + _old_planet_count) *
                                   (planet_count / _pre_battle))
            planet_side = best_army

        self.holds[to] = [planet_side, planet_count]
        

    def mt_level(self, _side, base_line=2000):
        """
        根据 玩家 units & base_line 返回增长系数, 最高为 1
        """
        _units = self.get_info()['players'][_side]['units']
        if _units <= base_line:
            return float(1)
        elif _units <= base_line * MAINTAIN_LEVEL_1:
            return float(0.5)
        elif _units <= base_line * MAINTAIN_LEVEL_2:
            return float(0.25)
        else:
            return float(0)

    def next_round(self):
        # 生产回合
        for i, data in enumerate(self.holds):
            side, count = data
            if side == None: continue
            next = self.count_growth(count, self.planets[i], self.mt_level(side, self.mt_base_line))
            if next <= 0:
                side = None
                next = 0
            self.holds[i] = [side, next]
            self.logs.append(dict(type= "production",
                                  planet=i,
                                  side=side,
                                  count=next))
            
        self.round += 1
        self.player_op = [None, ] * len(self.players)

    def step(self):
        """
        游戏进行一步
        返回值代表游戏是否有更新
        """
        self.logs = []
        self.info = None
        # 如果游戏结束, 等待一会继续开始
        #if self.loop_count <= 10 and self.status in [FINISHED]:
            #self.loop_count += 1
            #return

        if self.status == FINISHED:
            self.loop_count = 0
            self.start()
            return True

        # 游戏开始的时候, 需要有N个以上的玩家加入.
        if self.status == WAITFORPLAYER:
            if len(self.players) < self.map.min_player: return
            self.status = RUNNING
            self.log('game running.')

        # 游戏结束判断
        if self.check_finished():
            self.status = FINISHED
            self.check_winner()
            self.loop_count = 0

        # points
        for i in range(len(self.player_points)):
            self.player_points[i] += 1

        # move stage
        self.move_stage()
        
        # arrive stage
        arrives = self.arrive_stage()
        
        # battle stage
        self.battle_stage(arrives)

        # next round
        self.next_round()
        return True

    def battle(self, move):
        """
        战斗阶段
        首先进行def加权, 星球的单位Xdef 当作星球的战斗力量.
        双方数量一样, 同时全灭, A>B的时候, B全灭, A-B/(A/B) (B/(A/B)按照浮点计算, 最后去掉小数部分到整数)
        如果驻守方胜利, 除回def系数, 去掉小数部分到整数作为剩下的数量.
        """
        side, _from, to, count, _round = move
        planet_side, planet_count = self.holds[to]
        _def = self.planets[to]['def']

        if planet_side == None:
            # 如果星球没有驻军, 就占领
            planet_side = side
            planet_count = count
            self.logs.append(dict(type= "occupy",
                                  side=side,
                                  count=count,
                                  planet=to)) 
        elif side == planet_side:
            # 如果是己方, 就加入
            planet_count += count
            self.logs.append(dict(type= "join",
                                  planet=to,
                                  side=side,
                                  count=count))
        else:
            # 敌方战斗
            # 防守方加权
            planet_count *= _def
            if planet_count == count:
                # 数量一样的话, 同时全灭
                planet_side, planet_count = None, 0
            elif planet_count < count:
                # 进攻方胜利
                planet_side = side
                planet_count = count - int(planet_count**2/float(count))
            else:
                # 防守方胜利                
                planet_count -= int(count**2/float(planet_count))
                planet_count = int(planet_count / _def)
            self.logs.append(dict(type= "battle",
                                  planet=to,
                                  attack=side,
                                  defence=planet_side,
                                  atk_count=count,
                                  def_count=planet_count,
                                  winner=planet_side))
        self.holds[to] = [planet_side, planet_count]

    def count_growth(self, planet_count, planet, mt_proc = 1):
        max = planet['max']
        res = planet['res']
        cos = planet['cos']
        # 兵力增量乘以维护费用水平(增长系数)
        new_armies = (planet_count * (res - 1) + cos)
        if self.maintain_fee: new_armies *= mt_proc
        new_count = int(planet_count + new_armies)
        if planet_count < max:
            planet_count = min(new_count, max)
        elif new_count < planet_count:
            planet_count = new_count
        return planet_count

    def alloped(self):
        """
        判断是否所有玩家都做过操作了
        """
        oped = [
            (not s.alive or op != None)
            for op, s in zip(self.player_op,
                             self.players)]
        return all(oped)

    def no_response_player_die(self, player, round):
        """
        如果连续没有响应超过MAX_LOST_TURN次, 让玩家死掉
        round是没有响应的轮数(用来检查是否连续没有响应)
        
        """
        # 初始化缓存
        if (not hasattr(player, 'no_resp_time') or
            player.no_resp_round != round - 1):
            player.no_resp_time = 1
            player.no_resp_round = round
            return
        # 次数更新
        player.no_resp_time += 1
        player.no_resp_round = round
        # 判断是否没有响应时间过长
        if player.no_resp_time >= MAX_LOST_TURN:
            player.alive = False
            # 用户丢失后调整维护费用
            self.adjust_mt_fee()
            logging.debug('kill no response player: %d' % \
                         self.players.index(player))
            self.log('kill player for no response %s: , round is %s, time is %s' % (player.name, round, player.no_resp_time))


def test():
    """
    # 初始化游戏
    >>> g = Game(enable_no_resp_die=False, map="srcs/map/test.yml")

    # 玩家加入
    >>> player1 = g.add_player('player1')
    >>> player1['seq'] == 0
    True
    >>> player2 = g.add_player('player2')
    >>> player2['seq'] == 1
    True
    >>> g.holds
    [[0, 100], [1, 100], (None, 0), (None, 0), (None, 0)]
    
    # 游戏可以开始了
    >>> g.status == WAITFORPLAYER
    True
    >>> g.round == 0
    True
    >>> g.step()
    True
    >>> g.round == 1
    True
    
    # 一个回合之后, 玩家的单位开始增长了
    >>> g.holds
    [[0, 110], [1, 110], (None, 0), (None, 0), (None, 0)]


    # 玩家开始出兵
    >>> g.set_player_op(player1['id'], {'op': 'moves', 'moves': [[100, 0, 4], ]})
    'ok'
    >>> g.set_player_op(player2['id'], {'op': 'moves', 'moves': [[10, 1, 4], ]})
    'ok'

    # 出兵到达目标星球
    >>> g.step()
    True
    >>> g.moves
    [[0, 0, 4, 100, 1], [1, 1, 4, 10, 1]]

    # 能够获取API
    >>> g.get_map()
    {'planets': [{'res': 1, 'cos': 10, 'pos': (0, 0), 'def': 2, 'max': 1000}, {'res': 1, 'cos': 10, 'pos': (4, 0), 'def': 2, 'max': 1000}, {'res': 1, 'cos': 10, 'pos': (0, 4), 'def': 2, 'max': 1000}, {'res': 1, 'cos': 10, 'pos': (4, 4), 'def': 2, 'max': 1000}, {'res': 1.5, 'cos': 0, 'pos': (2, 2), 'def': 0.5, 'max': 300}], 'name': 'test', 'map_size': (5, 5), 'author': 'halida', 'routes': [(0, 1, 4), (3, 2, 4), (1, 3, 4), (3, 4, 2), (3, 1, 4), (1, 4, 2), (2, 4, 2), (2, 0, 4), (2, 3, 4), (4, 3, 2), (0, 4, 2), (4, 2, 2), (1, 0, 4), (4, 1, 2), (0, 2, 4), (4, 0, 2)], 'max_round': 8000, 'desc': 'this the the standard test map.'}
    >>> g.get_info()
    {'status': 'running', 'players': [{'name': 'player1'}, {'name': 'player2'}], 'moves': [[0, 0, 4, 100, 1], [1, 1, 4, 10, 1]], 'logs': [], 'holds': [[0, 120], [1, 120], (None, 0), (None, 0), (None, 0)], 'round': 2}
    
    # 战斗计算
    >>> g.step()
    True
    >>> g.holds[4]
    [0, 96]

    # 再出一次兵，此时非法操作了
    >>> g.set_player_op(player1['id'], {'op': 'moves', 'moves': [[1000, 0, 4], ]})
    'no enough armies'
    >>> g.set_player_op(player2['id'], {'op': 'moves', 'moves': [[10, 0, 4], ]})
    'not your planet'

    # 结束逻辑测试
    >>> import copy

    # 只有一个玩家剩下的时候, 游戏结束
    >>> gend = copy.deepcopy(g)
    >>> gend.holds[1] = [None, 0]
    >>> gend.step()
    True
    >>> gend.status == FINISHED
    True
    >>> gend.check_winner()
    0
    
    # 回合数到的时候, 星球多的玩家胜利
    >>> gend = copy.deepcopy(g)
    >>> gend.round = 10000
    >>> gend.step()
    True
    >>> gend.status == FINISHED
    True
    >>> gend.check_winner()
    0
    
    # 回合数到的时候, 星球一样, 单位多的玩家胜利
    >>> gend = copy.deepcopy(g)
    >>> gend.round = 10000
    >>> gend.holds[4] = [None, 0]
    >>> gend.step()
    True
    >>> gend.status == FINISHED
    True
    >>> gend.check_winner()
    1
    
    # 回合数到的时候, 星球一样, 单位一样, 序号后面的玩家胜利
    >>> gend = copy.deepcopy(g)
    >>> gend.round = 10000
    >>> gend.holds[4] = [None, 0]
    >>> gend.holds[0] = [0, 100]
    >>> gend.holds[1] = [1, 100]
    >>> gend.step()
    True
    >>> gend.status == FINISHED
    True
    >>> gend.check_winner()
    1
    """
    import doctest
    doctest.testmod()
    
if __name__=="__main__":
    test()

########NEW FILE########
__FILENAME__ = game_controller
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: game_controller
游戏控制器.. 提供api级别的接口, 方便服务器调用game

"""
from game import *
import scores

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
            return self.game.add_player(data.get('name', 'unknown'), data.get('side', 'unknown'))
        
        elif op in ('moves'):
            if isinstance(data['moves'] , basestring):
                data['moves'] = json.loads(data['moves'])
            if data.has_key('tactic') and isinstance(data['tactic'] , basestring):
                data['tactic'] = json.loads(data['tactic'])
            return dict(status=self.game.set_player_op(data['id'], data))
        
        elif op == 'map':
            return self.game.get_map()

        elif op == 'setmap':
            return dict(status=self.game.user_set_map(data['data']))
        
        elif op == 'info':
            return self.game.get_info()
        
        elif op == 'history':
            return self.history()
        
        elif op == 'scores':
            return scores.scores()
        
        else:
            return dict(status='op error: %s' % op)

def test():
    """
    # 初始化
    >>> game = Game()
    >>> c = Controller(game)

    # 添加新玩家
    >>> result = c.op(dict(op='add', name='foo'))
    >>> result = c.op(dict(op='add', name='bar'))
    >>> id = result['id']
    >>> result['seq']
    1

    # 发送指令
    >>> result = c.op(dict(op='moves', id=id, moves=[]))

    # 获取地图信息
    >>> m = c.op(dict(op='map'))

    # 获取实时信息
    >>> info = c.op(dict(op='info'))

    # 获取得分
    >>> score = c.op({'op' : 'scores'})
    """
    import doctest
    doctest.testmod()

if __name__=="__main__":
    test()

########NEW FILE########
__FILENAME__ = game_test
# test_code for games

import game
import map.map
from map.map import Map
from game import Game, Player
from nose.tools import *

map.map.random_starts = False

def player_test():
    player = Player(game="game_instance", name="player_name")
    eq_(player.game, "game_instance")
    eq_(player.name, "player_name")
    assert player.alive

def game_init_test():
    g = Game()
    yield check_game_empty, g, game.WAITFORPLAYER

def check_game_empty(game, game_status):
    eq_(game.status, game_status)
    eq_(game.round, 0)
    eq_(game.moves, [])
    eq_(game.players, [])
    eq_(game.loop_count, 0)
    eq_(game.player_ops, [])

def count_growth_test():
    g = Game(enable_no_resp_die = False)
    # not growth:
    eq_( g.count_growth(12, dict(max=10, res=1, cos=5)), 12 )
    eq_( g.count_growth(12, dict(max=12, res=1, cos=5)), 12 )
    # normal growth: result = int(12 * 1.1 + 5) = 18
    eq_( g.count_growth(12, dict(max=100, res=1.1, cos=5)), 18)
    # dec
    eq_( g.count_growth(12, dict(max=100, res=0.5, cos=3)), 9)
    # dec even more than max
    eq_( g.count_growth(12, dict(max=5, res=0.5, cos=3)), 9 )
    # grownth should not beyond max
    eq_( g.count_growth(12, dict(max=15, res=2, cos=10)), 15)


def move_test():
    g = Game(enable_no_resp_die = False, map = "srcs/map/ut_test.yml")
    
    # add_player
    player1 = g.add_player('player1')
    eq_(player1['seq'], 0)
    player2 = g.add_player('player2')
    eq_(player2['seq'], 1)
    
    # add two action
    eq_(g.set_player_op(player1['id'], dict(op='moves', moves=[[50, 0, 4],[50, 0, 2],])), "ok")
    g.step()
    eq_(g.holds, [[None, 0], [1, 110], [None, 0], [None, 0], [0, 75]])
    

def move_zero_test():
    g = Game(enable_no_resp_die = False, map = "srcs/map/ut_test.yml")
    # add_player
    player1 = g.add_player('player1')
    eq_(player1['seq'], 0)
    player2 = g.add_player('player2')
    eq_(player2['seq'], 1)
    # add a empty move
    g.set_player_op(player1['id'], dict(op='moves', moves=[[0, 0, 4]]))
    g.move_stage()
    g.battle_stage(g.arrive_stage())
    eq_(g.holds, [[0, 100], [1, 100], [None, 0], [None, 0], [None, 0]])
    g.next_round()
    eq_(g.holds, [[0, 120], [1, 110], [None, 0], [None, 0], [None, 0]])
   
def multi_battle_case_test():
    g = Game(enable_no_resp_die = False, map = "srcs/map/ut_test.yml")
    yield check_game_empty, g, game.WAITFORPLAYER

    player1 = g.add_player('player1')
    eq_(player1['seq'], 0)
    player2 = g.add_player('player2')
    eq_(player2['seq'], 1)
    player3 = g.add_player('player3')
    eq_(player3['seq'], 2)
    
    #round 0:
    eq_(g.holds, [[0, 100],[1, 100], [2, 100], [None, 0], [None, 0]])
    eq_(g.status, game.WAITFORPLAYER)
    eq_(g.round, 0)
    #round 1:
    ok_(g.step())
    eq_(g.holds, [[0, 120], [1, 110], [2, 110], [None, 0], [None, 0]])
    #round 2:
    g.set_player_op(player1['id'], dict(op='moves', moves=[[50, 0, 4],]))
    #g.set_player_op(player1['id'], dict(op='moves', moves=[[100, 0, 4], ]))
    g.step()
    eq_(g.holds, [[0, 87], [1, 120], [2, 120], [None, 0], [0, 75]])
    #round 3:
    g.set_player_op(player1['id'], dict(op='moves', moves=[[50, 0, 4], ]))
    g.set_player_op(player2['id'], dict(op='moves', moves=[[100, 1, 4], ]))
    g.set_player_op(player3['id'], dict(op='moves', moves=[[110, 2, 4], ]))
    g.step()
    eq_(g.holds, [[0, 50], [1, 30], [2, 20], [None, 0], [2, 43]])
    #round 4:
    g.set_player_op(player1['id'], dict(op='moves', moves=[[21, 0, 4], ]))
    g.set_player_op(player2['id'], dict(op='moves', moves=[[10, 1, 4], ]))
    g.set_player_op(player3['id'], dict(op='moves', moves=[[1, 4, 2], ]))
    g.step()
    eq_(g.holds, [[0, 41], [1, 30], [2, 31], [None, 0], [None, 0]])
 
def play_game_case_test():
    # init game
    g = Game(enable_no_resp_die = False, map = "srcs/map/ut_test.yml")
    yield check_game_empty, g, game.WAITFORPLAYER
    
    # add_player
    player1 = g.add_player('player1')
    eq_(player1['seq'], 0)
    player2 = g.add_player('player2')
    eq_(player2['seq'], 1)
    # round 0:
    eq_(g.holds, [[0, 100], [1, 100], [None, 0], [None, 0], [None, 0]])
    eq_(g.status, game.WAITFORPLAYER)
    eq_(g.round, 0)
    # round 1:
    ok_(g.step())
    eq_(g.round, 1)
    eq_(g.holds, [[0, 120], [1, 110], [None, 0], [None, 0], [None, 0]])
    # round 2:
    ok_(g.step())
    eq_(g.holds, [[0, 142], [1, 120], [None, 0], [None, 0], [None, 0]])
    # round 3: test move & arrive
    g.set_player_op(player1['id'], dict(op='moves', moves=[[100, 0, 4], ]))
    g.step()
    eq_(g.holds, [[0, 56], [1, 130], [None, 0], [None, 0], [0, 150]])
    # round4: move all
    eq_(g.set_player_op(player1['id'], dict(op='moves', moves=[[56, 0, 4], ])), "ok")
    g.step()
    eq_(g.holds, [[None, 0], [1, 140], [None, 0], [None, 0], [0, 300]])
    # what for a long time:
    for i in range(100):
        g.step()
    eq_(g.holds, [[None, 0], [1, 1000], [None, 0], [None, 0], [0, 300]])
    # let's fight
    g.set_player_op(player2['id'], dict(op='moves', moves=[[100, 1, 4],]))
    g.step()
    # Attack: 100 Defence 150 => 150 - 100 * 100 / 150 = 84 ~ 168
    # growth: 168 * 1.5 = 252
    eq_(g.holds, [[None, 0], [1, 910], [None, 0], [None, 0], [0, 249]])
    g.step()
    eq_(g.holds, [[None, 0], [1, 920], [None, 0], [None, 0], [0, 300]])
    # get a new planet
    g.set_player_op(player1['id'], dict(op='moves', moves=[[1, 4, 0], ]))
    g.step()
    eq_(g.holds,[[0, 11], [1, 930], [None, 0], [None, 0], [0, 300]])
    g.step()
    eq_(g.holds,[[0, 22], [1, 940], [None, 0], [None, 0], [0, 300]])
    print g.moves
    
    


########NEW FILE########
__FILENAME__ = lib
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: lib
"""
import sys, os
import time, logging, json, random, uuid, datetime, copy, string

from datetime import date

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(message)s")

GEME_STEP_TIME = 2


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
__FILENAME__ = generator
import sys
from random import randint
import math

planet_string = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-*/!@#$%"

def main():
    
    map_name = sys.argv[1]
    planet_count = int(sys.argv[2])
    map_size = int (sys.argv[3])

    if map_size % 2 != 1:
        return

    fout = open(map_name + ".yml", "w")

    print >> fout, "name:", map_name
    print >> fout, """desc: auto generated map
author: generator(resty)
version: 0.1

max_round: 2000
max_player: 4
start_unit: 100
"""


    mid = int(map_size / 2)

    map = []
    for x in range(map_size):
        map.append([-1] * map_size)
    ed = []
    for x in range(map_size):
        ed.append([False] * map_size)

    ls = int(map_size / 2)
    planets = []
    for i in range(int(planet_count / 4) + 1):
        pos = [randint(0, ls), randint(0, ls)]
        if not pos in planets:
            planets.append(pos)

    start_id = randint(0, len(planets) - 1)
    print >> fout, """starts:
  - %s
  - %s
  - %s
  - %s
""" % (planet_string[start_id],
       planet_string[start_id + len(planets)],
       planet_string[start_id + 2 * len(planets)],
       planet_string[start_id + 3 * len(planets)])
    print >> fout, "planets:"
    for (i,p) in enumerate(planets):
        x = randint(0,5)
        if x == 0:
            def_ = 1.2
            res = 0.9
            cos = 0
            max = 1000
        elif x == 1:
            def_ = 0.3
            res = 1.5
            cos = 2
            max = 300
        else:
           def_ = 1.2
           res = 1
           cos = 5
           max = 1000
         
        if i == start_id:
            def_ = 1.5
            res = 1.4
            cos = 5
            max = 2000
        for k in xrange(4):
            print >> fout, "  %s:" % planet_string[i + k * len(planets)]
            print >> fout,"""    def: %.1f
    res: %f
    cos: %d
    max: %d""" % (def_, res, cos, max)
        ms = map_size - 1
        map[p[0]][p[1]] = i
        map[p[1]][ms- p[0]] = i + len(planets)
        map[ms - p[0]][ms - p[1]] = i + 2 * len(planets)
        map[ms - p[1]][p[0]] = i + 3 * len(planets)
        
    mid_planet = 4 * len(planets)
    map[mid][mid] = mid_planet
    print >> fout, "  %s:" % planet_string[mid_planet]
    print >> fout, """    def: 0.3
    res: 2
    cos: 20
    max: 400
"""

    print >> fout, "map: |"
    for i in xrange(map_size):
        s = "  "
        
        for j in xrange(map_size):
            if map[i][j] == -1:
                s += '.'
            else:
                s +=  planet_string[map[i][j]]
        print >> fout, "%s" % s

    mm = 100000000
    mi = -1
    for (i, p) in enumerate(planets):
        dist = abs(p[0] - mid) + abs(p[1] - mid)
        if dist < mm:
            mm = dist
            mi = i

    bd = int(dist / 3)
    print >> fout, "\nroutes:"
    
    for (i, p) in enumerate(planets):
        dist = abs(p[0] - mid) + abs(p[1] - mid)
        if (int(dist/3) == bd):
            for k in xrange(4):
                print >> fout, """  - - %s
    - %s
    - %d""" % ( planet_string[i + k * len(planets)], planet_string[mid_planet], int(dist / 2) + 1)
    sqr = lambda x : x*x
    for (i, p) in enumerate(planets):
        mm = 100000000000
        mj = -1
        for (j, q) in enumerate(planets):
            dist = sqr(p[0]-q[0]) + sqr(p[1]-q[1])
            if i!=j and dist < mm:
                mm = dist
                mj = j
        for k in range(4):
            print >> fout, """  - - %s
    - %s
    - %d""" % (planet_string[i + k * len(planets)],
               planet_string[mj + k * len(planets)],
               int(math.sqrt(mm)) + 1)
    
    fout.close()
    

    

main()

########NEW FILE########
__FILENAME__ = map
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
module: map
"""
import yaml, string, random

random_starts = True
class Map:
    # planet tokens
    planet_tokens = string.uppercase + string.lowercase

    def __init__(self):
        # default meta
        self.meta = dict(
            name = 'unknown',
            author = 'none',
            version = 1.0,
            max_round = 3000,
            start_unit = 100,
            max_player = 4,
            min_player = 2,
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
        # planets data
        self.planets = self.meta['planets'].items()
        self.planets.sort()
        self.planet_name_to_id = dict([(i[0], c)
                                       for c, i in enumerate(self.planets)])
        self.planets = [i[1] for i in self.planets]
        # set planet location
        x, y = 0, 0
        map = self.meta['map'].strip().split("\n")
        for line in map:
            x = 0
            for c in line:
                if c in self.planet_tokens:
                    id = self.planet_name_to_id[c]
                    self.planets[id]['pos'] = (x, y)
                x += 1
            y += 1
        self.map_size = (len(map[0]), len(map))
        
        # route data
        self.routes = {}
        for _from, to, step in self.meta['routes']:
            from_id = self.planet_name_to_id[_from]
            to_id   = self.planet_name_to_id[to]
            self.routes[(from_id, to_id)] = step
            self.routes[(to_id, from_id)] = step
        # only for transport to client
        self.seq_routes = [(t[0], t[1], step)
                           for t, step in self.routes.items()]
                       
        self.starts = [self.planet_name_to_id[name]
                       for name in self.meta['starts']]
        if random_starts:
            random.shuffle(self.starts)
        
        self.max_sum = 0
        # 计算 map 上所有星球的最大产兵量总和
        for i in self.planets:
            self.max_sum += int(i['max'])

def test():
    """
    >>> map = Map.loadfile("srcs/map/test.yml")
    >>> map.planets
    [{'res': 1, 'cos': 10, 'pos': (0, 0), 'def': 2, 'max': 1000}, {'res': 1, 'cos': 10, 'pos': (4, 0), 'def': 2, 'max': 1000}, {'res': 1, 'cos': 10, 'pos': (0, 4), 'def': 2, 'max': 1000}, {'res': 1, 'cos': 10, 'pos': (4, 4), 'def': 2, 'max': 1000}, {'res': 1.5, 'cos': 0, 'pos': (2, 2), 'def': 0.5, 'max': 300}]
    >>> map.starts
    [0, 1, 2, 3]
    """
    import doctest
    doctest.testmod()

if __name__=="__main__":
    test()

########NEW FILE########
__FILENAME__ = map_editor
#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
 MapEditor for Planet-Conquer
"""
from lib import *
import yaml
import pygame

DEFAULT_FILENAME = './map/fight_here.yml'

SIZE=40
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DES = ['def', 'res', 'cos', 'max']
class Editor:
    
    def __init__(self, filename=None):
        if filename:
            self.load_file(filename)

    def load_file(self, file_name):
        self.map = yaml.load(open(file_name).read())
        self.map['map'] = self.map['map'].strip().split('\n')

    def save_file(self, file_name):
        data = copy.deepcopy(self.map)
        data['map'] = string.join(data['map'], '\n')
        open(file_name, 'w').write(yaml.dump(data, default_flow_style=False))

    def create_planet(self, i, j):
        planet_name = self.generate_planet_name()
        if planet_name:
            self.map['map'][i] = self.map['map'][i][0:j]  + planet_name + self.map['map'][i][j+1:]
            self.map['planets'][planet_name] = {'def':0, 'res':1, 'cos':0, 'max':100 }

    def update_planet(self, planet_name, key, val):
        self.map['planets'][planet_name][key] = val

    def generate_planet_name(self):
        candi = string.uppercase + string.lowercase
        dis = self.map['planets'].keys()
        for i in candi:
            if i not in dis:
                return i
        return ''

    def toggle_starts(self, planet_name):
        if planet_name in self.map['planets'].keys():
            if planet_name in self.map['starts']:
                self.map['starts'].remove(planet_name)
            else:
                self.map['starts'].append(planet_name)


class EditorView:
    def __init__(self, editor):
        
        self.editor = editor
        self.map = editor.map
        map = self.map['map']
        
        self.h = len(map)
        self.w = len(map[0])
        self.selected_i = -1
        
        print map
        print self.h, self.w
        
        self.base_w = self.w*SIZE
        self.menu_id = 0
        self.on_input = False

        pygame.init()
        self.font = pygame.font.SysFont('sans', 12)
        self.screen = pygame.display.set_mode((self.base_w + 200, max(100, self.h*SIZE)))

    def get_map_pos_of_mouse(self):
        """
        mapping mouse position to map position, like:
        405, 205 => 10, 10
        """
        mx, my = pygame.mouse.get_pos()
        mx = mx / SIZE
        my = my / SIZE
        return mx, my

    def render_word(self, pos, color, word):
        self.screen.blit(self.font.render(word, True, color), pos)

    def is_valid_map_pos(self, x, y):
        return x >= 0 and x < self.w and y >= 0 and y < self.h

    def select_pos(self, x, y):
        self.selected_i, self.selected_j = x, y
        self.menu_id = 0

    def update(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = self.get_map_pos_of_mouse()
                if self.is_valid_map_pos(x, y):
                    self.select_pos(x, y)
                    
            elif event.type == pygame.KEYDOWN:
                
                if self.on_input:
                    if event.key == pygame.K_BACKSPACE:
                        # delete a char
                        if len(self.number) > 0:
                            self.number = self.number[:-1]
                            
                    elif event.key == pygame.K_RETURN:
                        # update planet attribute
                        try:
                            planet_name = self.map['map'][self.selected_j][self.selected_i]
                            self.editor.update_planet(planet_name, DES[self.menu_id], float(self.number))
                            self.on_input = False
                        except:
                            pass
                    else:
                        # input number
                        char = event.unicode.encode('ascii')
                        if char in ".1234567890":
                            self.number += char
                            
                else:
                    if event.key == pygame.K_UP:
                        self.menu_id = max(0, self.menu_id - 1)
                    elif event.key == pygame.K_DOWN:
                        self.menu_id = min(3, self.menu_id + 1)
                    elif event.key == pygame.K_RETURN:
                        self.on_key_ret()
                    elif event.key == pygame.K_t:
                        # toggle start planet
                        planet_name = self.map['map'][self.selected_j][self.selected_i]
                        if planet_name != '.':
                            self.editor.toggle_starts(planet_name)

    def on_key_ret(self):
        if self.selected_j == -1:
            return
        planet_name = self.map['map'][self.selected_j][self.selected_i]
        if planet_name == '.':
            self.editor.create_planet(self.selected_j, self.selected_i)
        else:
            self.on_input = True
            self.number = ''

    def pp(self, p):
        """planet position to screen planet center position"""
        return (p[0] * SIZE + SIZE / 2, p[1] * SIZE + SIZE / 2)

    def gp(self, p):
        """get planet position by planet name"""
        for i in xrange(self.w):
            for j in xrange(self.h):
                if self.map['map'][j][i] == p:
                    return (i, j)

    def render(self):
        self.update()
        self.screen.fill(BLACK)
        self.draw_routes()
        self.draw_planets()
        self.draw_planet_info()
        pygame.display.flip()

    def draw_routes(self):

        def draw_route(pos_s, pos_e, len):
            pygame.draw.line(self.screen,
                             (200, 255, 200),
                             self.pp(pos_s),
                             self.pp(pos_e))
                    
        for r in self.map['routes']:
            draw_route(self.gp(r[0]), self.gp(r[1]), r[2])

    def draw_planets(self):        
        mx, my = self.get_map_pos_of_mouse()

        for i in range(self.w):
            for j in range(self.h):
                planet_name = self.map['map'][j][i]
                
                if planet_name != '.':
                    # set planet color
                    color = (200, 200, 200)
                    if i == self.selected_i and j == self.selected_j:
                        color = (170, 255, 172)
                    elif i == mx and j == my:
                        color = (250, 170, 170)

                    # draw planet
                    pygame.draw.circle(self.screen,
                                       color,
                                       self.pp((i, j)),
                                       SIZE / 2 - 2)

                    # mark start planet
                    if planet_name in self.map['starts']:
                        pygame.draw.circle(self.screen,
                                           BLACK,
                                           (i * SIZE + SIZE / 2,
                                            j * SIZE + SIZE / 2),
                                           SIZE / 2 - 6, 2)
                    # show planet name
                    self.render_word((i * SIZE + SIZE / 2 - 6,
                                      j * SIZE + SIZE / 2 - 6),
                                     BLACK, planet_name)
        
    def draw_planet_info(self):
        if self.selected_j == -1:
            self.render_word((self.base_w + 2, 10), WHITE, 'no space selected.')
        else:
            planet_name = self.map['map'][self.selected_j][self.selected_i]
            if planet_name == '.':
                self.render_word((self.base_w + 2, 10), WHITE, 'empty space.')
            else:
                p = self.map['planets'][planet_name]
                pygame.draw.rect(self.screen, (100, 110, 100),
                                 pygame.Rect(self.base_w + 1, 26 + 15 * self.menu_id, 200, 13))
                planet_desc = planet_name
                if planet_name in self.map['starts']:
                    planet_desc += ' (start) '
                self.render_word((self.base_w + 2, 10), WHITE, 'Planet:%s' % planet_desc)
                self.render_word((self.base_w + 2, 25), WHITE, 'def: %f' % p['def'])
                self.render_word((self.base_w + 2, 40), WHITE, 'res: %f' % p['res'])
                self.render_word((self.base_w + 2, 55), WHITE, 'cos: %f' % p['cos'])
                self.render_word((self.base_w + 2, 70), WHITE, 'max: %f' % p['max'])

                if self.on_input:
                    self.render_word((self.base_w + 2, 90), WHITE, 'new_val: %s' % self.number)


def main():
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = DEFAULT_FILENAME
        
    view = EditorView(Editor(filename))
    c = Clock(30)
    
    while True:
        c.tick()
        view.render()
        

if __name__=='__main__':
    main()
    #e = Editor()
    #e.load_file('test.yml')
    #e.save_file('test2.yml')
    
    

            

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

SIZE = 40

def random_planet_color():
    return (random.randint(120, 225), random.randint(120, 225), random.randint(120, 225))

def random_player_color():
    return (random.randint(0, 120), random.randint(0, 120), random.randint(0, 120))

class Shower():
    def __init__(self, map):
        pygame.init()
        self.font = pygame.font.SysFont('sans', 12)
        self.set_map(map)
        self.player_colors = []

    def set_map(self, map):
        self.map = map
        size = self.map['map_size']
        self.screen = pygame.display.set_mode(
            (size[0]*SIZE, size[1]*SIZE))
        for s in self.map['planets']:
            s['color'] = random_planet_color()

    def flip(self, info):
        # 退出判断
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        # 给玩家加颜色
        while len(info['players']) > len(self.player_colors):
            self.player_colors.append(random_player_color())
        
        size = SIZE
        def pp(p):
            return (p[0] * SIZE + SIZE / 2, p[1] * SIZE + SIZE / 2)
        
        def drawRect(c, x, y, w, h):
            pygame.draw.rect(self.screen, c,
                             pygame.Rect(x, y, w, h))
        def drawCircle(c, pos):
            pygame.draw.circle(self.screen, c,
                               (pos[0]*SIZE+SIZE/2, pos[1]*SIZE+SIZE/2), SIZE/2)
        
        # draw map background
        self.screen.fill((200,200,200))
        for x, y, z in self.map['routes']:
            print x, y, z
            pygame.draw.line(self.screen, (0, 0, 0), pp(self.map['planets'][x]['pos']), pp(self.map['planets'][y]['pos']))
        
        # planets
        for i, s in enumerate(self.map['planets']):
            pos = s['pos']
            drawCircle(s['color'], s['pos'])
            
        # players
        for i, s in enumerate(info['holds']):
            player_id, count = s
            if player_id == None: continue
            sur = self.font.render(str(count), True, self.player_colors[player_id])
            planet_pos = self.map['planets'][i]['pos']
            self.screen.blit(sur,
                             (planet_pos[0]*SIZE,
                              planet_pos[1]*SIZE))
            
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
__FILENAME__ = scores
#!/usr/bin/env python
#-*- coding:utf-8 -*-
import db
import datetime

def scores():
    """
    获取游戏历史分数
    """
    d = datetime.date.today()
    today = datetime.datetime(d.year, d.month, d.day)
    dailys =  list(db.cursor.execute('select * from (select name, count(*) as count from scores where time > ? group by name) order by count desc limit 10', (today, )))
    weeklys = list(db.cursor.execute('select * from (select name, count(*) as count from scores where time > ? group by name) order by count desc limit 10', (today - datetime.timedelta(days=7), )))
    monthlys = list(db.cursor.execute('select * from (select name, count(*) as count from scores where time > ? group by name) order by count desc limit 10', (today - datetime.timedelta(days=30), )))
    return dict(dailys=dailys, weeklys=weeklys, monthlys=monthlys)
    
def add_score(game_time, winner_name):
    """
    追加一个比赛的结果到数据集中，保存winner的名字
    """
    db.cursor.execute('insert into scores values(?, ?)', (game_time, winner_name))
    db.db.commit()

        

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
        
        if data.has_key('data'):
            data = data['data']
        else:
            data = json.dumps(data)
            
        oper.send_unicode(data)
        result = oper.recv()
        print 'result', result
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
from game import *

context = zmq.Context()

# room的个数
ROOMS = 100

class Server():
    """
    游戏的服务器逻辑
    服务器提供2个队列:
    - game_puber队列(PUB), 当地图更新的时候, 发送info信息
    - game_oper队列(REP), 可以进行add/turn/map命令
    """
    def on_logic(self, g, ok):
        """判断定期更新的时间是否到了"""
        min_waits = self.min_waits
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


    def run(self, max_waits=10.0, enable_no_resp_die=True, min_waits=2.0,
            msg_queue=None):
        self.min_waits = min_waits
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
                    #如果有新的玩家加进来, 也pub一下
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

                print 'result', result
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
                print g.get_info()

                # 发送更新信息
                if updated:
                    logging.debug("room %d updated: %s" % (i, g.status))
                    self.pub_info(i)
                elif g.status == 'finished':
                    msg_queue.put(i)

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
        from lib import GEME_STEP_TIME
        Server().run(max_waits=GEME_STEP_TIME,
                     min_waits=GEME_STEP_TIME,
                     enable_no_resp_die=False)
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
