__FILENAME__ = conpig
#   Copyright 2013 Matthew Mirman
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import gevent
import signal

alive = 0

############################
## the periodic scheduler ##
############################
def next(argA = None, argB = None):
    try:
        if alive > 0:
            signal.setitimer(signal.ITIMER_REAL, 0.0005)
        else:
            signal.setitimer(signal.ITIMER_REAL, 0)

        gevent.sleep(0)
    except:
        pass

##############################
## initialize the scheduler ##
##############################
signal.signal(signal.SIGALRM, next)

#######################
## library functions ##
#######################


def removeOne(g):
    global alive
    alive -= 1

def spawn(method, *args, **kr):
    global alive
    
    g = gevent.spawn(method, *args,**kr)
    alive += 1
    next()
    g.link(removeOne)
    return g

def spawn_after(seconds, method, *args, **kwargs):
    global alive
    g = gevent.spawn_later(seconds, method, *args, **kr)
    alive += 1
    g.link(removeOne)
    return g

def spawn_n(method, *args, **kwargs):
    global alive
    g = gevent.spawn_raw(method, *args, **kr)
    alive += 1
    g.link(removeOne)

sleep = gevent.sleep
getcurrent = gevent.getcurrent

def wait_all():
    """ This is only meant to be run once at the end of the program.  
        It turns off the scheduler when all threads have halted.
        If your program runs on an infinite loop, it needs not be run at all.
    """
    global alive

    try:
        while alive > 0:
            gevent.sleep(1)
    finally: 
        signal.setitimer(signal.ITIMER_REAL, 0)
        

########NEW FILE########
__FILENAME__ = test0
#   Copyright 2013 Matthew Mirman
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import conpig

##################
##  TESTING IT  ##
##################

def test(arg):
    for i in range(0,4000):
        print arg


conpig.spawn(test, "X")    
conpig.spawn(test, "O")

conpig.wait_all()

########NEW FILE########
__FILENAME__ = test1
#   Copyright 2013 Matthew Mirman
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import conpig

##################
##  TESTING IT  ##
##################

def test(arg):
    for i in range(0,20):
        conpig.sleep(1)
        print arg

conpig.spawn(test, "X")    
conpig.spawn(test, "O")

conpig.wait_all()

########NEW FILE########
__FILENAME__ = test2
#   Copyright 2013 Matthew Mirman
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import conpig

##################
##  TESTING IT  ##
##################

def test(arg,ti):
    for i in range(0,20):
        conpig.sleep(ti)
        print arg

conpig.spawn(test, "X", 1)    
conpig.spawn(test, "O", 2)

conpig.wait_all()

########NEW FILE########
__FILENAME__ = test3
#   Copyright 2013 Matthew Mirman
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import conpig

##################
##  TESTING IT  ##
##################

def test(arg):
    for i in range(0,1000):
        print arg

conpig.spawn(test, "X")

test("O")


########NEW FILE########
__FILENAME__ = test4
#   Copyright 2013 Matthew Mirman
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import conpig

##################
##  TESTING IT  ##
##################

def test(arg,ti):
    for i in range(0,20):
        conpig.sleep(ti)
        print arg

conpig.spawn(test, "X", 1)    
test("O", 2)

########NEW FILE########
__FILENAME__ = test5
#   Copyright 2013 Matthew Mirman
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import conpig

##################
##  TESTING IT  ##
##################

def test1(arg):
    for i in range(0,5):
        conpig.sleep(1)
        print arg
    raise Hello    

def test2(arg):
    for i in range(0,10):
        conpig.sleep(1)
        print arg
        

conpig.spawn(test1, "X")    
conpig.spawn(test2, "H")    
test2("O")


conpig.wait_all()

########NEW FILE########
__FILENAME__ = test6
#   Copyright 2013 Matthew Mirman
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import conpig

##################
##  TESTING IT  ##
##################

def tester(arg):
    for i in xrange(1000):
        for j in xrange(1000000):
            i + j == -1

        print arg

conpig.spawn(tester, "O")
conpig.spawn(tester, "X")
conpig.spawn(tester, "T")

conpig.wait_all()

    

########NEW FILE########
