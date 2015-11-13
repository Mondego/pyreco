__FILENAME__ = Callable
'''
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''


class Callable(object):

    '''
    A decorator used to confer to Policy object what
    methods are callable.
    '''

    def __init__(self, method):
        '''
        Callable Initializer
        '''

        self.__method = method

    def __call__(self, *args):
        '''
        Wrapper to the callable method
        '''

        return self.__method(*args)

    def __get__(self, obj, obj_type):
        """
        PFM to get self of method decorated
        """

        if obj is None:
            return self

        new_method = self.__method.__get__(obj, obj_type)

        return self.__class__(new_method)

########NEW FILE########
__FILENAME__ = BagOfWool
"""
Copyright (c) 2011, Michael Joseph Walsh.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

'''
Created on Aug 29, 2011

@author: Michael Joseph Walsh
'''


class BagOfWool(object):
    '''
        Used to signify a bag of wool
    '''


    def __init__(self):
        '''
        BagsOfWool Initializer
        '''

########NEW FILE########
__FILENAME__ = BlackSheep
"""
Copyright (c) 2011, Michael Jospeh Walsh.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

'''
Created on Aug 18, 2011

@author: Michael Joseph Walsh
'''

import logging, time
import thread, random
from threading import Lock

from intellect.examples.bahBahBlackSheep.BagOfWool import BagOfWool

def grow_wool(sheep):
    while True:

        time.sleep(random.randint(2, 5))

        logging.getLogger("example").debug("{0}: Grew a bag of wool.".format(sheep.name))
        sheep.bags_of_wool.append(BagOfWool())

        if len(sheep.bags_of_wool) == 3:
            logging.getLogger("example").debug("{0}: Waiting around for retirement.".format(sheep.name))
            break

class BlackSheep():
    '''
        Used to signify a black sheep
    '''

    number = 0

    def __init__(self):
        '''
        BlackSheep Initializer
        '''
        self.bags_of_wool = []
        BlackSheep.number = BlackSheep.number + 1
        self.name = "Sheep #{0}".format(BlackSheep.number)

        logging.getLogger("example").debug("Creating {0}.".format(self.name))

        self.lock = Lock()
        thread.start_new_thread(grow_wool, (self,))


    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def bags_of_wool(self):
        return self._bags_of_wool

    @bags_of_wool.setter
    def bags_of_wool(self, value):
        self.lock.acquire()
        self._bags_of_wool = value
        self.lock.release()


if __name__ == '__main__':
    sheep = BlackSheep()

    while True:
        time.sleep(5)
        print len(sheep.bags_of_wool)

        if len(sheep.bags_of_wool) == 3:
            break

########NEW FILE########
__FILENAME__ = BuyOrder
"""
Copyright (c) 2011, Michael Joseph Walsh.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

'''
Created on Aug 18, 2011

@author: Michael Joseph Walsh
'''

import logging

class BuyOrder(object):
    '''
    Used to signify a buy order
    '''

    def __init__(self, count = 1):
        '''
        BuyOrder Initializer
        '''
        logging.getLogger("example").debug("Creating buy order for {0} sheep.".format(count))
        
        self.count = count

    @property
    def count(self):
        return self._count

    @count.setter
    def count(self, value):
        self._count = value
########NEW FILE########
__FILENAME__ = Example
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2011, Michael Joseph Walsh.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

'''
Created on Aug 17, 2011

@author: Michael Joseph Walsh
'''

import sys, logging, time, random

from intellect.Intellect import Intellect

from intellect.examples.bahBahBlackSheep.BuyOrder import BuyOrder

class MyIntellect(Intellect):
    pass


if __name__ == '__main__':

    # tune down logging inside Intellect
    logger = logging.getLogger('intellect')
    logger.setLevel(logging.ERROR)
    consoleHandler = logging.StreamHandler(stream=sys.stdout)
    consoleHandler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s%(message)s'))
    logger.addHandler(consoleHandler)

    # set up logging for the example
    logger = logging.getLogger('example')
    logger.setLevel(logging.DEBUG)

    consoleHandler = logging.StreamHandler(stream=sys.stdout)
    consoleHandler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s%(message)s'))
    logger.addHandler(consoleHandler)

    logging.getLogger("example").debug("Creating reasoning engine.")
    myIntellect = MyIntellect()

    logging.getLogger("example").debug("Asking the engine to learn my policy.")
    policy = myIntellect.learn(myIntellect.local_file_uri("./rulesets/example.policy"))

    #print myIntellect.policy.str_tree("semantic model:")

    max_buy_orders_to_start = input('Provide the maximum number possible buy orders to start with:  ')

    buy_order_to_start = random.randint(1, max_buy_orders_to_start)

    logging.getLogger("example").debug("Asking the engine to learn a BuyOrder for {0} sheep.".format(buy_order_to_start))
    myIntellect.learn(BuyOrder(buy_order_to_start))

    myIntellect.reason()

    while True:
        logging.getLogger("example").debug("{0} in knowledge.".format(myIntellect.knowledge))
        time.sleep(5)
        logging.getLogger("example").debug("Messaging reasoning engine to reason.")
        myIntellect.reason()

########NEW FILE########
__FILENAME__ = ClassA
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
ClassA

Description: Intellect test fact

Initial Version: Feb 2, 2011

@author: Michael Joseph Walsh
"""

class ClassA(object):
    '''
    An example fact
    '''

    globalInClassA_1 = "a global"
    globalInClassA_2 = "another global"

    def __init__(self, property0 = None, property1 = None):
        '''
        ClassA initializer
        '''
        self.attribute1 = "attribute1's value"
        self.__hiddenAttribute1 = "super secret hidden attribute. nah!"

        self.property0 = property0
        self.property1 = property1

        print "created an instance of ClassA"

    @property
    def property0(self):
        return self._property0

    @property0.setter
    def property0(self, value):
        self._property0 = value

    @property
    def property1(self):
        return self._property1

    @property1.setter
    def property1(self, value):
        self._property1 = value

    def someMethod(self):
        print("someMethod called")

    @staticmethod
    def classAStaticMethod(self):
        print("classAStaticMethod called")

    def classASomeOtherMethod(self):
        print("classASomeOtherMethd called")

    def __classAHiddenMethod(self):
        print("classAHiddenMethod called")
########NEW FILE########
__FILENAME__ = ClassCandD
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
ClassCandD

Description: Intellect test facts

Initial Version: Feb 2, 2011

@author: Michael Joseph Walsh
"""

class ClassC(object):
    '''
    An example fact.
    '''
    
    globalInClassC="a global only in ClassC"

    def __init__(self, property1 = None, property2 = None):
        '''
        ClassC initializer
        '''
        self.property1 = property1
        self.property2 = property2

    def someMethod(self):
        print("someMethod called")         

    @property
    def property1(self):
        return self._property1

    @property1.setter
    def property1(self, value):
        self._property1 = value

    @property1.deleter
    def property1(self):
        del self._property1

    @property
    def property2(self):
        return self._property2

    @property2.setter
    def property2(self, value):
        self._property2 = value

    @property2.deleter
    def property2(self):
        del self._property2
 
        
class ClassD(object):
    '''
    An example fact.
    '''
    
    globalInClassD="a global only in ClassD"
    
    def __init__(self, property1 = None):
        '''
        ClassD initializer
        '''
        self.property1 = property1

    def someMethod(self):
        print("someMethod called")  

    @property
    def property1(self):
        return self._property1

    @property1.setter
    def property1(self, value):
        self._property1 = value
        
    @property1.deleter
    def property1(self):
        del self._property1
########NEW FILE########
__FILENAME__ = ExerciseGrammar
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
ExerciseIntellect

Description: Exercises the Intellect grammar

Initial Version: Dec 29, 2011

@author: Michael Joseph Walsh
"""
import sys, traceback, logging

from intellect.Intellect import Intellect
from intellect.examples.testing.ClassA import ClassA

if __name__ == "__main__":

    # tune down logging inside Intellect
    logger = logging.getLogger('intellect')
    logger.setLevel(logging.DEBUG) # change this to ERROR for less output
    consoleHandler = logging.StreamHandler(stream=sys.stdout)
    consoleHandler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s%(message)s'))
    logger.addHandler(consoleHandler)

    # set up logging for the example
    logger = logging.getLogger('example')
    logger.setLevel(logging.DEBUG)

    consoleHandler = logging.StreamHandler(stream=sys.stdout)
    consoleHandler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s%(message)s'))
    logger.addHandler(consoleHandler)

    print "*"*80
    print """create an instance of MyIntellect extending Intellect, create some facts, and exercise the grammar"""
    print "*"*80

    try:
        myIntellect = Intellect()

        policy_a = myIntellect.learn(Intellect.local_file_uri("./rulesets/test_f.policy"))

        myIntellect.learn(ClassA(property1="apple"))
        #myIntellect.learn(ClassA( property1="pear"))
        #myIntellect.learn(ClassA( property1="grape"))

        #logger.debug("reasoning over policy w/ objects in memory")

        myIntellect.reason()
    except Exception as e:
        traceback.print_exc(limit=sys.getrecursionlimit(), file=sys.stdout)

########NEW FILE########
__FILENAME__ = ExerciseIntellect
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
ExerciseIntellect

Description: Exercises the Intellect object

Initial Version: Feb 9, 2011

@author: Michael Joseph Walsh
"""

import sys, traceback, logging

from intellect.Intellect import Intellect
from intellect.Intellect import Callable


class MyIntellect(Intellect):

    @Callable
    def bar(self):
        self.log(">>>>>>>>>>>>>>  called MyIntellect's bar method as it was decorated as callable.")


if __name__ == "__main__":

    try:
        # tune down logging inside Intellect
        logger = logging.getLogger('intellect')
        logger.setLevel(logging.DEBUG) # change this to ERROR for less output
        consoleHandler = logging.StreamHandler(stream=sys.stdout)
        consoleHandler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s%(message)s'))
        logger.addHandler(consoleHandler)

        # set up logging for the example
        logger = logging.getLogger('example')
        logger.setLevel(logging.DEBUG)

        consoleHandler = logging.StreamHandler(stream=sys.stdout)
        consoleHandler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s%(message)s'))
        logger.addHandler(consoleHandler)

        print "*"*80
        print """create an instance of MyIntellect extending Intellect, create some facts, and exercise the MyIntellect's ability to learn and forget"""
        print "*"*80

        myIntellect = MyIntellect()

        try:
            policy_bogus = myIntellect.learn(Intellect.local_file_uri("./rulesets/doesnt_exist.policy"))
        except IOError as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)

        policy_a = myIntellect.learn(Intellect.local_file_uri("./rulesets/test_a.policy"))
        policy_d = myIntellect.learn(Intellect.local_file_uri("./rulesets/test_d.policy"))

        myIntellect.reason(["test_d", "test_a"])

        myIntellect.forget_all()

        from intellect.examples.testing.subModule.ClassB import ClassB

        # keep an identifier (b1) around to a ClassB, to demonstrate that a rule
        # can modify the object and the change is reflected in b1
        b = ClassB(property1="apple", property2=11)
        myIntellect.learn(b)

        b = ClassB(property1="pear", property2=11)
        myIntellect.learn(b)

        # learn policy as a string
        policy_a = myIntellect.learn("""
from intellect.examples.testing.subModule.ClassB import ClassB
import intellect.examples.testing.Test as Test
import logging

fruits_of_interest = ["apple", "grape", "mellon", "pear"]
count = 5

rule rule_a:
    agenda-group test_a
    when:
        $classB := ClassB( property1 in fruits_of_interest and property2>count )
    then:
        # mark the 'ClassB' matches in memory as modified
        modify $classB:
            property1 = $classB.property1 + " pie"
            modified = True
            # increment the matche's 'property2' value by 1000
            property2 = $classB.property2 + 1000
        attribute count = $classB.property2
        print "count = {0}".format( count )
        # call MyIntellect's bar method as it is decorated as callable
        bar()
        log("rule_a fired")

rule rule_b:
    agenda-group test_a
    then:
        print "count = {0}".format( count )
        insert ClassB("water melon")
        # call MyIntellect's bar method as it is decorated as callable
        bar()
        log("rule_b fired")

rule rule_c:
    # on the MAIN agenda-group
    then:
        log("rule_c fired")

rule rule_d:
    agenda-group test_a
    then:
        attribute foo = "foo bar"
""")

        policy_b = myIntellect.learn(Intellect.local_file_uri("./rulesets/test_b.policy"))
        #print policy.str_tree()
        #print str(policy_a)

        for policy_file_paths in myIntellect.policy.file_paths:
            print "----------------- path:  {0}".format(policy_file_paths)

        myIntellect.forget(policy_b)

        for policy_file_paths in myIntellect.policy.file_paths:
            print "----------------- path:  {0}".format(policy_file_paths)

        policy_b = myIntellect.learn(Intellect.local_file_uri("./rulesets/test_b.policy"))

        for policy_file_paths in myIntellect.policy.file_paths:
            print "----------------- path:  {0}".format(policy_file_paths)

        myIntellect.forget(Intellect.local_file_uri("./rulesets/test_b.policy"))

        for policy_file_paths in myIntellect.policy.file_paths:
            print "----------------- path:  {0}".format(policy_file_paths)

        policy_b = myIntellect.learn(Intellect.local_file_uri("./rulesets/test_b.policy"))

        for policy_file_paths in myIntellect.policy.file_paths:
            print "----------------- path:  {0}".format(policy_file_paths)

        print "*"*80
        print "message MyIntellect to reason over the facts in knowledge"
        print "*"*80

        myIntellect.reason(["test_a"])

        print "*"*80
        print "facts in knowledge after applying policies"
        print "*"*80

        print  myIntellect.knowledge

        for fact in myIntellect.knowledge:
            print "type: {0}, __dict__: {1}".format(type(fact), fact.__dict__)

        print "*"*80
        print "forget all, learn a policy from a string"
        print "*"*80

        myIntellect.forget_all()

        policy = myIntellect.learn("""rule rule_inline:
        then:
            a = 1
            b = 2
            c = a + b
            print("{0} + {1} = {2}".format(a, b, c))
    """)

        myIntellect.reason()

        print "*"*80
        print 'forget all, learn test_c.policy, reason over ["1", "2", "3", "4", "5", "6"]'
        print "*"*80

        myIntellect.forget_all()

        policy_c = myIntellect.learn(Intellect.local_file_uri("./rulesets/test_c.policy"))

        myIntellect.reason(["1", "2", "3", "4", "5", "6"])

        myIntellect.forget_all()

        try:
            policy_bogus = myIntellect.learn(Intellect.local_file_uri("./rulesets/test_e.policy"))
        except Exception as e:
            print >> sys.stderr, "./rulesets/test_e.policy doesn't contain any actual policy text. exception trace follows:"
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
    except Exception as e:
        traceback.print_exc(limit=sys.getrecursionlimit(), file=sys.stdout)

########NEW FILE########
__FILENAME__ = ClassB
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
ClassB

Description: Intellect test fact

Initial Version: Feb 2, 2011

@author: Michael Joseph Walsh
"""

from intellect.examples.testing.ClassA import ClassA

class ClassB(ClassA):
    '''
    An example fact
    '''

    globalInClassB="a global only in class B"

    def __init__(self, property0 = None, property1 = None, property2 = None):
        '''
        ClassB initializer
        '''
        self.attribute2 = "attribute2's value"
        self.__hiddenAttribute2 = "another super secret hidden attribute. nah!"

        self.property0 = property0
        self.property1 = property1
        self.property2 = property2
        self.modified = False

        print "created an instance of ClassB"

    @property
    def property2(self):
        return self._property2

    @property2.setter
    def property2(self, value):
        print "setting property2 to {0}".format(value)
        self._property2 = value

    @property
    def modified(self):
        return self._modified

    @modified.setter
    def modified(self, value):
        print "setting modified to {0}".format(value)
        self._modified = value

    def aMethod(self):
        return "a"

    def trueValue(self):
        return True

    @staticmethod
    def classBStaticMethod(self):
        # and here
        print("classBStatciMethod called")

    def classBSomeOtherMethod(self):
        # and here
        print("classBSomeOtherMethod called")

    def __classBHiddenMethod(self):
        # something goes here
        print("classBHiddenMethod called")
########NEW FILE########
__FILENAME__ = Test
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
test

Description: Test module

Initial Version: Feb 23, 2011

@author: Michael Joseph Walsh
"""
def helloworld():
    """
    Returns "hello world" annd prints "returning 'hello world'" to the
        sys.stdout
    """
    print "returning 'hello world'"
    return "hello world"

def greaterThanTen(n):
    """
    Returns True if 'n' is greater than 10
    """
    return n>10


class MyClass(object):

    def __init__(self):
        self._globals = {}

    @property
    def globals(self):
        return self._globals

    @globals.setter
    def globals(self, value):
        self._globals = value


a = MyClass()

locals = {}

exec("a = 1" ,a.globals, locals)

print "globals = {0}".format([g for g in a.globals if not g.startswith("__")])
print "locals = {0}".format(locals)

exec("a += 1", a.globals, locals)

print "globals = {0}".format([g for g in a.globals if not g.startswith("__")])
print "locals = {0}".format(locals)

a.globals["b"] = 5

print "globals = {0}".format([g for g in a.globals if not g.startswith("__")])
print "locals = {0}".format(locals)

exec("global b;b += 1", a.globals, locals)
########NEW FILE########
__FILENAME__ = PolicyLexer
# $ANTLR 3.1.3 Mar 17, 2009 19:23:44 /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g 2013-03-25 15:29:48

import sys
from antlr3 import *
from antlr3.compat import set, frozenset


# for convenience in actions
HIDDEN = BaseRecognizer.HIDDEN

# token types
DOLLAR=79
DOUBLESLASH=67
MODIFY=32
SLASHEQUAL=38
BACKQUOTE=80
EXPONENT=84
CONTINUED_LINE=88
LBRACK=70
STAR=64
CIRCUMFLEXEQUAL=42
DOUBLESTAR=69
OBJECTBINDING=23
HALT=33
LETTER=82
ESC=87
TRIAPOS=85
ATTRIBUTE=25
GREATEREQUAL=52
COMPLEX=77
FLOAT=76
DEDENT=5
NOT=21
ASSIGNEQUAL=24
AND=48
RIGHTSHIFTEQUAL=44
LEARN=30
EOF=-1
LPAREN=9
INDENT=4
PLUSEQUAL=35
LEADING_WS=90
NOTEQUAL=55
AS=13
VBAR=58
MINUSEQUAL=36
RPAREN=10
IMPORT=7
NAME=12
SLASH=65
GREATER=50
IN=56
THEN=20
INSERT=31
COMMA=11
IS=57
AMPER=60
EQUAL=51
DOUBLESTAREQUAL=45
TILDE=68
LESS=49
LEFTSHIFTEQUAL=43
PLUS=62
LEFTSHIFT=61
DIGIT=83
EXISTS=22
DOT=14
COMMENT=91
AGENDAGROUP=18
RBRACK=71
PERCENT=66
RULE=15
LCURLY=72
INT=74
DELETE=29
MINUS=63
RIGHTSHIFT=27
SEMI=78
PRINT=26
TRIQUOTE=86
COLON=16
DOUBLESLASHEQUAL=46
WS=89
NEWLINE=6
AMPEREQUAL=40
WHEN=19
VBAREQUAL=41
RCURLY=73
OR=47
ASSIGN=34
LONGINT=75
FORGET=28
GLOBAL=81
FROM=8
PERCENTEQUAL=39
LESSEQUAL=53
STAREQUAL=37
CIRCUMFLEX=59
STRING=17
ALT_NOTEQUAL=54


class PolicyLexer(Lexer):

    grammarFileName = "/Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g"
    antlr_version = version_str_to_tuple("3.1.3 Mar 17, 2009 19:23:44")
    antlr_version_str = "3.1.3 Mar 17, 2009 19:23:44"

    def __init__(self, input=None, state=None):
        if state is None:
            state = RecognizerSharedState()
        super(PolicyLexer, self).__init__(input, state)


        self.dfa9 = self.DFA9(
            self, 9,
            eot = self.DFA9_eot,
            eof = self.DFA9_eof,
            min = self.DFA9_min,
            max = self.DFA9_max,
            accept = self.DFA9_accept,
            special = self.DFA9_special,
            transition = self.DFA9_transition
            )

        self.dfa16 = self.DFA16(
            self, 16,
            eot = self.DFA16_eot,
            eof = self.DFA16_eof,
            min = self.DFA16_min,
            max = self.DFA16_max,
            accept = self.DFA16_accept,
            special = self.DFA16_special,
            transition = self.DFA16_transition
            )

        self.dfa46 = self.DFA46(
            self, 46,
            eot = self.DFA46_eot,
            eof = self.DFA46_eof,
            min = self.DFA46_min,
            max = self.DFA46_max,
            accept = self.DFA46_accept,
            special = self.DFA46_special,
            transition = self.DFA46_transition
            )

        self.dfa47 = self.DFA47(
            self, 47,
            eot = self.DFA47_eot,
            eof = self.DFA47_eof,
            min = self.DFA47_min,
            max = self.DFA47_max,
            accept = self.DFA47_accept,
            special = self.DFA47_special,
            transition = self.DFA47_transition
            )


                             
        self.implicitLineJoiningLevel = 0
        self.startPosition = -1





    # $ANTLR start "LPAREN"
    def mLPAREN(self, ):

        try:
            _type = LPAREN
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:388:3: ( '(' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:388:5: '('
            pass 
            self.match(40)
            #action start
            self.implicitLineJoiningLevel += 1
            #action end



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LPAREN"



    # $ANTLR start "RPAREN"
    def mRPAREN(self, ):

        try:
            _type = RPAREN
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:392:3: ( ')' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:392:5: ')'
            pass 
            self.match(41)
            #action start
            self.implicitLineJoiningLevel -= 1
            #action end



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "RPAREN"



    # $ANTLR start "LBRACK"
    def mLBRACK(self, ):

        try:
            _type = LBRACK
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:396:3: ( '[' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:396:5: '['
            pass 
            self.match(91)
            #action start
            self.implicitLineJoiningLevel += 1
            #action end



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LBRACK"



    # $ANTLR start "RBRACK"
    def mRBRACK(self, ):

        try:
            _type = RBRACK
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:400:3: ( ']' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:400:5: ']'
            pass 
            self.match(93)
            #action start
            self.implicitLineJoiningLevel -= 1
            #action end



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "RBRACK"



    # $ANTLR start "LCURLY"
    def mLCURLY(self, ):

        try:
            _type = LCURLY
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:404:3: ( '{' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:404:5: '{'
            pass 
            self.match(123)
            #action start
            self.implicitLineJoiningLevel += 1
            #action end



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LCURLY"



    # $ANTLR start "RCURLY"
    def mRCURLY(self, ):

        try:
            _type = RCURLY
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:408:3: ( '}' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:408:5: '}'
            pass 
            self.match(125)
            #action start
            self.implicitLineJoiningLevel -= 1
            #action end



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "RCURLY"



    # $ANTLR start "COLON"
    def mCOLON(self, ):

        try:
            _type = COLON
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:412:3: ( ':' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:412:5: ':'
            pass 
            self.match(58)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "COLON"



    # $ANTLR start "COMMA"
    def mCOMMA(self, ):

        try:
            _type = COMMA
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:416:3: ( ',' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:416:5: ','
            pass 
            self.match(44)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "COMMA"



    # $ANTLR start "DOT"
    def mDOT(self, ):

        try:
            _type = DOT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:420:3: ( '.' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:420:5: '.'
            pass 
            self.match(46)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "DOT"



    # $ANTLR start "SEMI"
    def mSEMI(self, ):

        try:
            _type = SEMI
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:424:3: ( ';' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:424:5: ';'
            pass 
            self.match(59)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "SEMI"



    # $ANTLR start "PLUS"
    def mPLUS(self, ):

        try:
            _type = PLUS
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:428:3: ( '+' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:428:5: '+'
            pass 
            self.match(43)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "PLUS"



    # $ANTLR start "MINUS"
    def mMINUS(self, ):

        try:
            _type = MINUS
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:432:3: ( '-' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:432:5: '-'
            pass 
            self.match(45)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "MINUS"



    # $ANTLR start "STAR"
    def mSTAR(self, ):

        try:
            _type = STAR
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:436:3: ( '*' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:436:5: '*'
            pass 
            self.match(42)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "STAR"



    # $ANTLR start "DOLLAR"
    def mDOLLAR(self, ):

        try:
            _type = DOLLAR
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:440:3: ( '$' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:440:5: '$'
            pass 
            self.match(36)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "DOLLAR"



    # $ANTLR start "SLASH"
    def mSLASH(self, ):

        try:
            _type = SLASH
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:444:3: ( '/' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:444:5: '/'
            pass 
            self.match(47)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "SLASH"



    # $ANTLR start "VBAR"
    def mVBAR(self, ):

        try:
            _type = VBAR
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:448:3: ( '|' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:448:5: '|'
            pass 
            self.match(124)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "VBAR"



    # $ANTLR start "AMPER"
    def mAMPER(self, ):

        try:
            _type = AMPER
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:452:3: ( '&' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:452:5: '&'
            pass 
            self.match(38)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "AMPER"



    # $ANTLR start "LESS"
    def mLESS(self, ):

        try:
            _type = LESS
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:456:3: ( '<' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:456:5: '<'
            pass 
            self.match(60)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LESS"



    # $ANTLR start "GREATER"
    def mGREATER(self, ):

        try:
            _type = GREATER
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:460:3: ( '>' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:460:5: '>'
            pass 
            self.match(62)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "GREATER"



    # $ANTLR start "ASSIGN"
    def mASSIGN(self, ):

        try:
            _type = ASSIGN
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:464:3: ( '=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:464:5: '='
            pass 
            self.match(61)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "ASSIGN"



    # $ANTLR start "PERCENT"
    def mPERCENT(self, ):

        try:
            _type = PERCENT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:468:3: ( '%' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:468:5: '%'
            pass 
            self.match(37)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "PERCENT"



    # $ANTLR start "BACKQUOTE"
    def mBACKQUOTE(self, ):

        try:
            _type = BACKQUOTE
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:472:3: ( '`' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:472:5: '`'
            pass 
            self.match(96)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "BACKQUOTE"



    # $ANTLR start "CIRCUMFLEX"
    def mCIRCUMFLEX(self, ):

        try:
            _type = CIRCUMFLEX
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:476:3: ( '^' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:476:5: '^'
            pass 
            self.match(94)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "CIRCUMFLEX"



    # $ANTLR start "TILDE"
    def mTILDE(self, ):

        try:
            _type = TILDE
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:480:3: ( '~' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:480:5: '~'
            pass 
            self.match(126)



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "TILDE"



    # $ANTLR start "EQUAL"
    def mEQUAL(self, ):

        try:
            _type = EQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:484:3: ( '==' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:484:5: '=='
            pass 
            self.match("==")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "EQUAL"



    # $ANTLR start "ASSIGNEQUAL"
    def mASSIGNEQUAL(self, ):

        try:
            _type = ASSIGNEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:488:3: ( ':=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:488:5: ':='
            pass 
            self.match(":=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "ASSIGNEQUAL"



    # $ANTLR start "NOTEQUAL"
    def mNOTEQUAL(self, ):

        try:
            _type = NOTEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:492:3: ( '!=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:492:5: '!='
            pass 
            self.match("!=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "NOTEQUAL"



    # $ANTLR start "ALT_NOTEQUAL"
    def mALT_NOTEQUAL(self, ):

        try:
            _type = ALT_NOTEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:496:3: ( '<>' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:496:5: '<>'
            pass 
            self.match("<>")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "ALT_NOTEQUAL"



    # $ANTLR start "LESSEQUAL"
    def mLESSEQUAL(self, ):

        try:
            _type = LESSEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:500:3: ( '<=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:500:5: '<='
            pass 
            self.match("<=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LESSEQUAL"



    # $ANTLR start "LEFTSHIFT"
    def mLEFTSHIFT(self, ):

        try:
            _type = LEFTSHIFT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:504:3: ( '<<' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:504:5: '<<'
            pass 
            self.match("<<")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LEFTSHIFT"



    # $ANTLR start "GREATEREQUAL"
    def mGREATEREQUAL(self, ):

        try:
            _type = GREATEREQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:508:3: ( '>=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:508:5: '>='
            pass 
            self.match(">=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "GREATEREQUAL"



    # $ANTLR start "RIGHTSHIFT"
    def mRIGHTSHIFT(self, ):

        try:
            _type = RIGHTSHIFT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:512:3: ( '>>' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:512:5: '>>'
            pass 
            self.match(">>")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "RIGHTSHIFT"



    # $ANTLR start "PLUSEQUAL"
    def mPLUSEQUAL(self, ):

        try:
            _type = PLUSEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:516:3: ( '+=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:516:5: '+='
            pass 
            self.match("+=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "PLUSEQUAL"



    # $ANTLR start "MINUSEQUAL"
    def mMINUSEQUAL(self, ):

        try:
            _type = MINUSEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:520:3: ( '-=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:520:5: '-='
            pass 
            self.match("-=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "MINUSEQUAL"



    # $ANTLR start "DOUBLESTAR"
    def mDOUBLESTAR(self, ):

        try:
            _type = DOUBLESTAR
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:524:3: ( '**' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:524:5: '**'
            pass 
            self.match("**")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "DOUBLESTAR"



    # $ANTLR start "STAREQUAL"
    def mSTAREQUAL(self, ):

        try:
            _type = STAREQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:528:3: ( '*=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:528:5: '*='
            pass 
            self.match("*=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "STAREQUAL"



    # $ANTLR start "DOUBLESLASH"
    def mDOUBLESLASH(self, ):

        try:
            _type = DOUBLESLASH
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:532:3: ( '//' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:532:5: '//'
            pass 
            self.match("//")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "DOUBLESLASH"



    # $ANTLR start "SLASHEQUAL"
    def mSLASHEQUAL(self, ):

        try:
            _type = SLASHEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:536:3: ( '/=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:536:5: '/='
            pass 
            self.match("/=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "SLASHEQUAL"



    # $ANTLR start "VBAREQUAL"
    def mVBAREQUAL(self, ):

        try:
            _type = VBAREQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:540:3: ( '|=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:540:5: '|='
            pass 
            self.match("|=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "VBAREQUAL"



    # $ANTLR start "PERCENTEQUAL"
    def mPERCENTEQUAL(self, ):

        try:
            _type = PERCENTEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:544:3: ( '%=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:544:5: '%='
            pass 
            self.match("%=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "PERCENTEQUAL"



    # $ANTLR start "AMPEREQUAL"
    def mAMPEREQUAL(self, ):

        try:
            _type = AMPEREQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:548:3: ( '&=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:548:5: '&='
            pass 
            self.match("&=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "AMPEREQUAL"



    # $ANTLR start "CIRCUMFLEXEQUAL"
    def mCIRCUMFLEXEQUAL(self, ):

        try:
            _type = CIRCUMFLEXEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:552:3: ( '^=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:552:5: '^='
            pass 
            self.match("^=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "CIRCUMFLEXEQUAL"



    # $ANTLR start "LEFTSHIFTEQUAL"
    def mLEFTSHIFTEQUAL(self, ):

        try:
            _type = LEFTSHIFTEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:556:3: ( '<<=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:556:5: '<<='
            pass 
            self.match("<<=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LEFTSHIFTEQUAL"



    # $ANTLR start "RIGHTSHIFTEQUAL"
    def mRIGHTSHIFTEQUAL(self, ):

        try:
            _type = RIGHTSHIFTEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:560:3: ( '>>=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:560:5: '>>='
            pass 
            self.match(">>=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "RIGHTSHIFTEQUAL"



    # $ANTLR start "DOUBLESTAREQUAL"
    def mDOUBLESTAREQUAL(self, ):

        try:
            _type = DOUBLESTAREQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:564:3: ( '**=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:564:5: '**='
            pass 
            self.match("**=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "DOUBLESTAREQUAL"



    # $ANTLR start "DOUBLESLASHEQUAL"
    def mDOUBLESLASHEQUAL(self, ):

        try:
            _type = DOUBLESLASHEQUAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:568:3: ( '//=' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:568:5: '//='
            pass 
            self.match("//=")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "DOUBLESLASHEQUAL"



    # $ANTLR start "GLOBAL"
    def mGLOBAL(self, ):

        try:
            _type = GLOBAL
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:572:3: ( 'global' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:572:5: 'global'
            pass 
            self.match("global")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "GLOBAL"



    # $ANTLR start "ATTRIBUTE"
    def mATTRIBUTE(self, ):

        try:
            _type = ATTRIBUTE
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:576:3: ( 'attribute' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:576:5: 'attribute'
            pass 
            self.match("attribute")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "ATTRIBUTE"



    # $ANTLR start "RULE"
    def mRULE(self, ):

        try:
            _type = RULE
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:580:3: ( 'rule' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:580:5: 'rule'
            pass 
            self.match("rule")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "RULE"



    # $ANTLR start "AGENDAGROUP"
    def mAGENDAGROUP(self, ):

        try:
            _type = AGENDAGROUP
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:584:3: ( 'agenda-group' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:584:5: 'agenda-group'
            pass 
            self.match("agenda-group")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "AGENDAGROUP"



    # $ANTLR start "WHEN"
    def mWHEN(self, ):

        try:
            _type = WHEN
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:588:3: ( 'when' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:588:5: 'when'
            pass 
            self.match("when")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "WHEN"



    # $ANTLR start "EXISTS"
    def mEXISTS(self, ):

        try:
            _type = EXISTS
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:592:3: ( 'exists' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:592:5: 'exists'
            pass 
            self.match("exists")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "EXISTS"



    # $ANTLR start "THEN"
    def mTHEN(self, ):

        try:
            _type = THEN
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:596:3: ( 'then' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:596:5: 'then'
            pass 
            self.match("then")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "THEN"



    # $ANTLR start "MODIFY"
    def mMODIFY(self, ):

        try:
            _type = MODIFY
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:600:3: ( 'modify' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:600:5: 'modify'
            pass 
            self.match("modify")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "MODIFY"



    # $ANTLR start "INSERT"
    def mINSERT(self, ):

        try:
            _type = INSERT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:604:3: ( 'insert' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:604:5: 'insert'
            pass 
            self.match("insert")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "INSERT"



    # $ANTLR start "LEARN"
    def mLEARN(self, ):

        try:
            _type = LEARN
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:608:3: ( 'learn' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:608:5: 'learn'
            pass 
            self.match("learn")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LEARN"



    # $ANTLR start "DELETE"
    def mDELETE(self, ):

        try:
            _type = DELETE
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:612:3: ( 'delete' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:612:5: 'delete'
            pass 
            self.match("delete")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "DELETE"



    # $ANTLR start "FORGET"
    def mFORGET(self, ):

        try:
            _type = FORGET
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:616:3: ( 'forget' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:616:5: 'forget'
            pass 
            self.match("forget")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "FORGET"



    # $ANTLR start "HALT"
    def mHALT(self, ):

        try:
            _type = HALT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:620:3: ( 'halt' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:620:5: 'halt'
            pass 
            self.match("halt")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "HALT"



    # $ANTLR start "PRINT"
    def mPRINT(self, ):

        try:
            _type = PRINT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:624:3: ( 'print' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:624:5: 'print'
            pass 
            self.match("print")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "PRINT"



    # $ANTLR start "IMPORT"
    def mIMPORT(self, ):

        try:
            _type = IMPORT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:628:3: ( 'import' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:628:5: 'import'
            pass 
            self.match("import")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "IMPORT"



    # $ANTLR start "FROM"
    def mFROM(self, ):

        try:
            _type = FROM
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:632:3: ( 'from' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:632:5: 'from'
            pass 
            self.match("from")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "FROM"



    # $ANTLR start "AND"
    def mAND(self, ):

        try:
            _type = AND
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:636:3: ( 'and' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:636:5: 'and'
            pass 
            self.match("and")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "AND"



    # $ANTLR start "OR"
    def mOR(self, ):

        try:
            _type = OR
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:640:3: ( 'or' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:640:5: 'or'
            pass 
            self.match("or")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "OR"



    # $ANTLR start "IN"
    def mIN(self, ):

        try:
            _type = IN
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:644:3: ( 'in' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:644:5: 'in'
            pass 
            self.match("in")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "IN"



    # $ANTLR start "IS"
    def mIS(self, ):

        try:
            _type = IS
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:648:3: ( 'is' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:648:5: 'is'
            pass 
            self.match("is")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "IS"



    # $ANTLR start "AS"
    def mAS(self, ):

        try:
            _type = AS
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:652:3: ( 'as' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:652:5: 'as'
            pass 
            self.match("as")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "AS"



    # $ANTLR start "NOT"
    def mNOT(self, ):

        try:
            _type = NOT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:656:3: ( 'not' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:656:5: 'not'
            pass 
            self.match("not")



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "NOT"



    # $ANTLR start "LETTER"
    def mLETTER(self, ):

        try:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:661:3: ( ( 'a' .. 'z' | 'A' .. 'Z' ) )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:661:5: ( 'a' .. 'z' | 'A' .. 'Z' )
            pass 
            if (65 <= self.input.LA(1) <= 90) or (97 <= self.input.LA(1) <= 122):
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse





        finally:

            pass

    # $ANTLR end "LETTER"



    # $ANTLR start "DIGIT"
    def mDIGIT(self, ):

        try:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:666:3: ( ( '0' .. '9' ) )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:666:5: ( '0' .. '9' )
            pass 
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:666:5: ( '0' .. '9' )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:666:6: '0' .. '9'
            pass 
            self.matchRange(48, 57)







        finally:

            pass

    # $ANTLR end "DIGIT"



    # $ANTLR start "FLOAT"
    def mFLOAT(self, ):

        try:
            _type = FLOAT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:670:3: ( '.' ( DIGIT )+ ( EXPONENT )? | ( DIGIT )+ '.' EXPONENT | ( DIGIT )+ ( '.' ( ( DIGIT )+ ( EXPONENT )? )? | EXPONENT ) )
            alt9 = 3
            alt9 = self.dfa9.predict(self.input)
            if alt9 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:670:5: '.' ( DIGIT )+ ( EXPONENT )?
                pass 
                self.match(46)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:670:9: ( DIGIT )+
                cnt1 = 0
                while True: #loop1
                    alt1 = 2
                    LA1_0 = self.input.LA(1)

                    if ((48 <= LA1_0 <= 57)) :
                        alt1 = 1


                    if alt1 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:670:9: DIGIT
                        pass 
                        self.mDIGIT()


                    else:
                        if cnt1 >= 1:
                            break #loop1

                        eee = EarlyExitException(1, self.input)
                        raise eee

                    cnt1 += 1
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:670:16: ( EXPONENT )?
                alt2 = 2
                LA2_0 = self.input.LA(1)

                if (LA2_0 == 69 or LA2_0 == 101) :
                    alt2 = 1
                if alt2 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:670:17: EXPONENT
                    pass 
                    self.mEXPONENT()





            elif alt9 == 2:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:671:5: ( DIGIT )+ '.' EXPONENT
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:671:5: ( DIGIT )+
                cnt3 = 0
                while True: #loop3
                    alt3 = 2
                    LA3_0 = self.input.LA(1)

                    if ((48 <= LA3_0 <= 57)) :
                        alt3 = 1


                    if alt3 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:671:5: DIGIT
                        pass 
                        self.mDIGIT()


                    else:
                        if cnt3 >= 1:
                            break #loop3

                        eee = EarlyExitException(3, self.input)
                        raise eee

                    cnt3 += 1
                self.match(46)
                self.mEXPONENT()


            elif alt9 == 3:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:5: ( DIGIT )+ ( '.' ( ( DIGIT )+ ( EXPONENT )? )? | EXPONENT )
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:5: ( DIGIT )+
                cnt4 = 0
                while True: #loop4
                    alt4 = 2
                    LA4_0 = self.input.LA(1)

                    if ((48 <= LA4_0 <= 57)) :
                        alt4 = 1


                    if alt4 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:5: DIGIT
                        pass 
                        self.mDIGIT()


                    else:
                        if cnt4 >= 1:
                            break #loop4

                        eee = EarlyExitException(4, self.input)
                        raise eee

                    cnt4 += 1
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:12: ( '.' ( ( DIGIT )+ ( EXPONENT )? )? | EXPONENT )
                alt8 = 2
                LA8_0 = self.input.LA(1)

                if (LA8_0 == 46) :
                    alt8 = 1
                elif (LA8_0 == 69 or LA8_0 == 101) :
                    alt8 = 2
                else:
                    nvae = NoViableAltException("", 8, 0, self.input)

                    raise nvae

                if alt8 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:13: '.' ( ( DIGIT )+ ( EXPONENT )? )?
                    pass 
                    self.match(46)
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:17: ( ( DIGIT )+ ( EXPONENT )? )?
                    alt7 = 2
                    LA7_0 = self.input.LA(1)

                    if ((48 <= LA7_0 <= 57)) :
                        alt7 = 1
                    if alt7 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:18: ( DIGIT )+ ( EXPONENT )?
                        pass 
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:18: ( DIGIT )+
                        cnt5 = 0
                        while True: #loop5
                            alt5 = 2
                            LA5_0 = self.input.LA(1)

                            if ((48 <= LA5_0 <= 57)) :
                                alt5 = 1


                            if alt5 == 1:
                                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:18: DIGIT
                                pass 
                                self.mDIGIT()


                            else:
                                if cnt5 >= 1:
                                    break #loop5

                                eee = EarlyExitException(5, self.input)
                                raise eee

                            cnt5 += 1
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:25: ( EXPONENT )?
                        alt6 = 2
                        LA6_0 = self.input.LA(1)

                        if (LA6_0 == 69 or LA6_0 == 101) :
                            alt6 = 1
                        if alt6 == 1:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:26: EXPONENT
                            pass 
                            self.mEXPONENT()








                elif alt8 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:672:41: EXPONENT
                    pass 
                    self.mEXPONENT()





            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "FLOAT"



    # $ANTLR start "LONGINT"
    def mLONGINT(self, ):

        try:
            _type = LONGINT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:676:3: ( INT ( 'l' | 'L' ) )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:676:5: INT ( 'l' | 'L' )
            pass 
            self.mINT()
            if self.input.LA(1) == 76 or self.input.LA(1) == 108:
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse




            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LONGINT"



    # $ANTLR start "EXPONENT"
    def mEXPONENT(self, ):

        try:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:681:3: ( ( 'e' | 'E' ) ( '+' | '-' )? ( DIGIT )+ )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:681:5: ( 'e' | 'E' ) ( '+' | '-' )? ( DIGIT )+
            pass 
            if self.input.LA(1) == 69 or self.input.LA(1) == 101:
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:681:17: ( '+' | '-' )?
            alt10 = 2
            LA10_0 = self.input.LA(1)

            if (LA10_0 == 43 or LA10_0 == 45) :
                alt10 = 1
            if alt10 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:
                pass 
                if self.input.LA(1) == 43 or self.input.LA(1) == 45:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse




            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:681:32: ( DIGIT )+
            cnt11 = 0
            while True: #loop11
                alt11 = 2
                LA11_0 = self.input.LA(1)

                if ((48 <= LA11_0 <= 57)) :
                    alt11 = 1


                if alt11 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:681:32: DIGIT
                    pass 
                    self.mDIGIT()


                else:
                    if cnt11 >= 1:
                        break #loop11

                    eee = EarlyExitException(11, self.input)
                    raise eee

                cnt11 += 1




        finally:

            pass

    # $ANTLR end "EXPONENT"



    # $ANTLR start "INT"
    def mINT(self, ):

        try:
            _type = INT
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:685:3: ( '0' ( 'x' | 'X' ) ( DIGIT | 'a' .. 'f' | 'A' .. 'F' )+ | '0' ( DIGIT )* | '1' .. '9' ( DIGIT )* )
            alt15 = 3
            LA15_0 = self.input.LA(1)

            if (LA15_0 == 48) :
                LA15_1 = self.input.LA(2)

                if (LA15_1 == 88 or LA15_1 == 120) :
                    alt15 = 1
                else:
                    alt15 = 2
            elif ((49 <= LA15_0 <= 57)) :
                alt15 = 3
            else:
                nvae = NoViableAltException("", 15, 0, self.input)

                raise nvae

            if alt15 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:685:5: '0' ( 'x' | 'X' ) ( DIGIT | 'a' .. 'f' | 'A' .. 'F' )+
                pass 
                self.match(48)
                if self.input.LA(1) == 88 or self.input.LA(1) == 120:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse

                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:685:21: ( DIGIT | 'a' .. 'f' | 'A' .. 'F' )+
                cnt12 = 0
                while True: #loop12
                    alt12 = 4
                    LA12 = self.input.LA(1)
                    if LA12 == 48 or LA12 == 49 or LA12 == 50 or LA12 == 51 or LA12 == 52 or LA12 == 53 or LA12 == 54 or LA12 == 55 or LA12 == 56 or LA12 == 57:
                        alt12 = 1
                    elif LA12 == 97 or LA12 == 98 or LA12 == 99 or LA12 == 100 or LA12 == 101 or LA12 == 102:
                        alt12 = 2
                    elif LA12 == 65 or LA12 == 66 or LA12 == 67 or LA12 == 68 or LA12 == 69 or LA12 == 70:
                        alt12 = 3

                    if alt12 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:685:23: DIGIT
                        pass 
                        self.mDIGIT()


                    elif alt12 == 2:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:685:31: 'a' .. 'f'
                        pass 
                        self.matchRange(97, 102)


                    elif alt12 == 3:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:685:44: 'A' .. 'F'
                        pass 
                        self.matchRange(65, 70)


                    else:
                        if cnt12 >= 1:
                            break #loop12

                        eee = EarlyExitException(12, self.input)
                        raise eee

                    cnt12 += 1


            elif alt15 == 2:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:686:5: '0' ( DIGIT )*
                pass 
                self.match(48)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:686:9: ( DIGIT )*
                while True: #loop13
                    alt13 = 2
                    LA13_0 = self.input.LA(1)

                    if ((48 <= LA13_0 <= 57)) :
                        alt13 = 1


                    if alt13 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:686:9: DIGIT
                        pass 
                        self.mDIGIT()


                    else:
                        break #loop13


            elif alt15 == 3:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:687:5: '1' .. '9' ( DIGIT )*
                pass 
                self.matchRange(49, 57)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:687:14: ( DIGIT )*
                while True: #loop14
                    alt14 = 2
                    LA14_0 = self.input.LA(1)

                    if ((48 <= LA14_0 <= 57)) :
                        alt14 = 1


                    if alt14 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:687:14: DIGIT
                        pass 
                        self.mDIGIT()


                    else:
                        break #loop14


            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "INT"



    # $ANTLR start "COMPLEX"
    def mCOMPLEX(self, ):

        try:
            _type = COMPLEX
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:691:3: ( INT ( 'j' | 'J' ) | FLOAT ( 'j' | 'J' ) )
            alt16 = 2
            alt16 = self.dfa16.predict(self.input)
            if alt16 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:691:5: INT ( 'j' | 'J' )
                pass 
                self.mINT()
                if self.input.LA(1) == 74 or self.input.LA(1) == 106:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse



            elif alt16 == 2:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:692:5: FLOAT ( 'j' | 'J' )
                pass 
                self.mFLOAT()
                if self.input.LA(1) == 74 or self.input.LA(1) == 106:
                    self.input.consume()
                else:
                    mse = MismatchedSetException(None, self.input)
                    self.recover(mse)
                    raise mse



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "COMPLEX"



    # $ANTLR start "NAME"
    def mNAME(self, ):

        try:
            _type = NAME
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:696:3: ( ( LETTER | '_' ) ( LETTER | '_' | DIGIT )* )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:696:5: ( LETTER | '_' ) ( LETTER | '_' | DIGIT )*
            pass 
            if (65 <= self.input.LA(1) <= 90) or self.input.LA(1) == 95 or (97 <= self.input.LA(1) <= 122):
                self.input.consume()
            else:
                mse = MismatchedSetException(None, self.input)
                self.recover(mse)
                raise mse

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:696:21: ( LETTER | '_' | DIGIT )*
            while True: #loop17
                alt17 = 4
                LA17 = self.input.LA(1)
                if LA17 == 65 or LA17 == 66 or LA17 == 67 or LA17 == 68 or LA17 == 69 or LA17 == 70 or LA17 == 71 or LA17 == 72 or LA17 == 73 or LA17 == 74 or LA17 == 75 or LA17 == 76 or LA17 == 77 or LA17 == 78 or LA17 == 79 or LA17 == 80 or LA17 == 81 or LA17 == 82 or LA17 == 83 or LA17 == 84 or LA17 == 85 or LA17 == 86 or LA17 == 87 or LA17 == 88 or LA17 == 89 or LA17 == 90 or LA17 == 97 or LA17 == 98 or LA17 == 99 or LA17 == 100 or LA17 == 101 or LA17 == 102 or LA17 == 103 or LA17 == 104 or LA17 == 105 or LA17 == 106 or LA17 == 107 or LA17 == 108 or LA17 == 109 or LA17 == 110 or LA17 == 111 or LA17 == 112 or LA17 == 113 or LA17 == 114 or LA17 == 115 or LA17 == 116 or LA17 == 117 or LA17 == 118 or LA17 == 119 or LA17 == 120 or LA17 == 121 or LA17 == 122:
                    alt17 = 1
                elif LA17 == 95:
                    alt17 = 2
                elif LA17 == 48 or LA17 == 49 or LA17 == 50 or LA17 == 51 or LA17 == 52 or LA17 == 53 or LA17 == 54 or LA17 == 55 or LA17 == 56 or LA17 == 57:
                    alt17 = 3

                if alt17 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:696:23: LETTER
                    pass 
                    self.mLETTER()


                elif alt17 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:696:32: '_'
                    pass 
                    self.match(95)


                elif alt17 == 3:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:696:38: DIGIT
                    pass 
                    self.mDIGIT()


                else:
                    break #loop17



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "NAME"



    # $ANTLR start "OBJECTBINDING"
    def mOBJECTBINDING(self, ):

        try:
            _type = OBJECTBINDING
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:700:3: ( DOLLAR NAME )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:700:5: DOLLAR NAME
            pass 
            self.mDOLLAR()
            self.mNAME()



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "OBJECTBINDING"



    # $ANTLR start "STRING"
    def mSTRING(self, ):

        try:
            _type = STRING
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:704:3: ( ( 'r' | 'u' | 'ur' )? ( '\\'\\'\\'' ( options {greedy=false; } : TRIAPOS )* '\\'\\'\\'' | '\"\"\"' ( options {greedy=false; } : TRIQUOTE )* '\"\"\"' | '\"' ( ESC | ~ ( '\\\\' | '\\n' | '\"' ) )* '\"' | '\\'' ( ESC | ~ ( '\\\\' | '\\n' | '\\'' ) )* '\\'' ) )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:704:5: ( 'r' | 'u' | 'ur' )? ( '\\'\\'\\'' ( options {greedy=false; } : TRIAPOS )* '\\'\\'\\'' | '\"\"\"' ( options {greedy=false; } : TRIQUOTE )* '\"\"\"' | '\"' ( ESC | ~ ( '\\\\' | '\\n' | '\"' ) )* '\"' | '\\'' ( ESC | ~ ( '\\\\' | '\\n' | '\\'' ) )* '\\'' )
            pass 
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:704:5: ( 'r' | 'u' | 'ur' )?
            alt18 = 4
            LA18_0 = self.input.LA(1)

            if (LA18_0 == 114) :
                alt18 = 1
            elif (LA18_0 == 117) :
                LA18_2 = self.input.LA(2)

                if (LA18_2 == 114) :
                    alt18 = 3
                elif (LA18_2 == 34 or LA18_2 == 39) :
                    alt18 = 2
            if alt18 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:704:6: 'r'
                pass 
                self.match(114)


            elif alt18 == 2:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:704:10: 'u'
                pass 
                self.match(117)


            elif alt18 == 3:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:704:14: 'ur'
                pass 
                self.match("ur")



            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:705:5: ( '\\'\\'\\'' ( options {greedy=false; } : TRIAPOS )* '\\'\\'\\'' | '\"\"\"' ( options {greedy=false; } : TRIQUOTE )* '\"\"\"' | '\"' ( ESC | ~ ( '\\\\' | '\\n' | '\"' ) )* '\"' | '\\'' ( ESC | ~ ( '\\\\' | '\\n' | '\\'' ) )* '\\'' )
            alt23 = 4
            LA23_0 = self.input.LA(1)

            if (LA23_0 == 39) :
                LA23_1 = self.input.LA(2)

                if (LA23_1 == 39) :
                    LA23_3 = self.input.LA(3)

                    if (LA23_3 == 39) :
                        alt23 = 1
                    else:
                        alt23 = 4
                elif ((0 <= LA23_1 <= 9) or (11 <= LA23_1 <= 38) or (40 <= LA23_1 <= 65535)) :
                    alt23 = 4
                else:
                    nvae = NoViableAltException("", 23, 1, self.input)

                    raise nvae

            elif (LA23_0 == 34) :
                LA23_2 = self.input.LA(2)

                if (LA23_2 == 34) :
                    LA23_5 = self.input.LA(3)

                    if (LA23_5 == 34) :
                        alt23 = 2
                    else:
                        alt23 = 3
                elif ((0 <= LA23_2 <= 9) or (11 <= LA23_2 <= 33) or (35 <= LA23_2 <= 65535)) :
                    alt23 = 3
                else:
                    nvae = NoViableAltException("", 23, 2, self.input)

                    raise nvae

            else:
                nvae = NoViableAltException("", 23, 0, self.input)

                raise nvae

            if alt23 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:705:9: '\\'\\'\\'' ( options {greedy=false; } : TRIAPOS )* '\\'\\'\\''
                pass 
                self.match("'''")
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:705:18: ( options {greedy=false; } : TRIAPOS )*
                while True: #loop19
                    alt19 = 2
                    LA19_0 = self.input.LA(1)

                    if (LA19_0 == 39) :
                        LA19_1 = self.input.LA(2)

                        if (LA19_1 == 39) :
                            LA19_3 = self.input.LA(3)

                            if (LA19_3 == 39) :
                                alt19 = 2
                            elif ((0 <= LA19_3 <= 38) or (40 <= LA19_3 <= 65535)) :
                                alt19 = 1


                        elif ((0 <= LA19_1 <= 38) or (40 <= LA19_1 <= 65535)) :
                            alt19 = 1


                    elif ((0 <= LA19_0 <= 38) or (40 <= LA19_0 <= 65535)) :
                        alt19 = 1


                    if alt19 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:705:43: TRIAPOS
                        pass 
                        self.mTRIAPOS()


                    else:
                        break #loop19
                self.match("'''")


            elif alt23 == 2:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:706:9: '\"\"\"' ( options {greedy=false; } : TRIQUOTE )* '\"\"\"'
                pass 
                self.match("\"\"\"")
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:706:15: ( options {greedy=false; } : TRIQUOTE )*
                while True: #loop20
                    alt20 = 2
                    LA20_0 = self.input.LA(1)

                    if (LA20_0 == 34) :
                        LA20_1 = self.input.LA(2)

                        if (LA20_1 == 34) :
                            LA20_3 = self.input.LA(3)

                            if (LA20_3 == 34) :
                                alt20 = 2
                            elif ((0 <= LA20_3 <= 33) or (35 <= LA20_3 <= 65535)) :
                                alt20 = 1


                        elif ((0 <= LA20_1 <= 33) or (35 <= LA20_1 <= 65535)) :
                            alt20 = 1


                    elif ((0 <= LA20_0 <= 33) or (35 <= LA20_0 <= 65535)) :
                        alt20 = 1


                    if alt20 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:706:40: TRIQUOTE
                        pass 
                        self.mTRIQUOTE()


                    else:
                        break #loop20
                self.match("\"\"\"")


            elif alt23 == 3:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:707:9: '\"' ( ESC | ~ ( '\\\\' | '\\n' | '\"' ) )* '\"'
                pass 
                self.match(34)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:707:13: ( ESC | ~ ( '\\\\' | '\\n' | '\"' ) )*
                while True: #loop21
                    alt21 = 3
                    LA21_0 = self.input.LA(1)

                    if (LA21_0 == 92) :
                        alt21 = 1
                    elif ((0 <= LA21_0 <= 9) or (11 <= LA21_0 <= 33) or (35 <= LA21_0 <= 91) or (93 <= LA21_0 <= 65535)) :
                        alt21 = 2


                    if alt21 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:707:14: ESC
                        pass 
                        self.mESC()


                    elif alt21 == 2:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:707:18: ~ ( '\\\\' | '\\n' | '\"' )
                        pass 
                        if (0 <= self.input.LA(1) <= 9) or (11 <= self.input.LA(1) <= 33) or (35 <= self.input.LA(1) <= 91) or (93 <= self.input.LA(1) <= 65535):
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse



                    else:
                        break #loop21
                self.match(34)


            elif alt23 == 4:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:708:9: '\\'' ( ESC | ~ ( '\\\\' | '\\n' | '\\'' ) )* '\\''
                pass 
                self.match(39)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:708:14: ( ESC | ~ ( '\\\\' | '\\n' | '\\'' ) )*
                while True: #loop22
                    alt22 = 3
                    LA22_0 = self.input.LA(1)

                    if (LA22_0 == 92) :
                        alt22 = 1
                    elif ((0 <= LA22_0 <= 9) or (11 <= LA22_0 <= 38) or (40 <= LA22_0 <= 91) or (93 <= LA22_0 <= 65535)) :
                        alt22 = 2


                    if alt22 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:708:15: ESC
                        pass 
                        self.mESC()


                    elif alt22 == 2:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:708:19: ~ ( '\\\\' | '\\n' | '\\'' )
                        pass 
                        if (0 <= self.input.LA(1) <= 9) or (11 <= self.input.LA(1) <= 38) or (40 <= self.input.LA(1) <= 91) or (93 <= self.input.LA(1) <= 65535):
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse



                    else:
                        break #loop22
                self.match(39)






            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "STRING"



    # $ANTLR start "TRIQUOTE"
    def mTRIQUOTE(self, ):

        try:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:714:2: ( ( '\"' )? ( '\"' )? ( ESC | ~ ( '\\\\' | '\"' ) )+ )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:714:4: ( '\"' )? ( '\"' )? ( ESC | ~ ( '\\\\' | '\"' ) )+
            pass 
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:714:4: ( '\"' )?
            alt24 = 2
            LA24_0 = self.input.LA(1)

            if (LA24_0 == 34) :
                alt24 = 1
            if alt24 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:714:4: '\"'
                pass 
                self.match(34)



            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:714:9: ( '\"' )?
            alt25 = 2
            LA25_0 = self.input.LA(1)

            if (LA25_0 == 34) :
                alt25 = 1
            if alt25 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:714:9: '\"'
                pass 
                self.match(34)



            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:714:14: ( ESC | ~ ( '\\\\' | '\"' ) )+
            cnt26 = 0
            while True: #loop26
                alt26 = 3
                LA26_0 = self.input.LA(1)

                if (LA26_0 == 92) :
                    alt26 = 1
                elif ((0 <= LA26_0 <= 33) or (35 <= LA26_0 <= 91) or (93 <= LA26_0 <= 65535)) :
                    alt26 = 2


                if alt26 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:714:15: ESC
                    pass 
                    self.mESC()


                elif alt26 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:714:19: ~ ( '\\\\' | '\"' )
                    pass 
                    if (0 <= self.input.LA(1) <= 33) or (35 <= self.input.LA(1) <= 91) or (93 <= self.input.LA(1) <= 65535):
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse



                else:
                    if cnt26 >= 1:
                        break #loop26

                    eee = EarlyExitException(26, self.input)
                    raise eee

                cnt26 += 1




        finally:

            pass

    # $ANTLR end "TRIQUOTE"



    # $ANTLR start "TRIAPOS"
    def mTRIAPOS(self, ):

        try:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:719:3: ( ( '\\'' )? ( '\\'' )? ( ESC | ~ ( '\\\\' | '\\'' ) )+ )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:719:5: ( '\\'' )? ( '\\'' )? ( ESC | ~ ( '\\\\' | '\\'' ) )+
            pass 
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:719:5: ( '\\'' )?
            alt27 = 2
            LA27_0 = self.input.LA(1)

            if (LA27_0 == 39) :
                alt27 = 1
            if alt27 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:719:5: '\\''
                pass 
                self.match(39)



            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:719:11: ( '\\'' )?
            alt28 = 2
            LA28_0 = self.input.LA(1)

            if (LA28_0 == 39) :
                alt28 = 1
            if alt28 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:719:11: '\\''
                pass 
                self.match(39)



            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:719:17: ( ESC | ~ ( '\\\\' | '\\'' ) )+
            cnt29 = 0
            while True: #loop29
                alt29 = 3
                LA29_0 = self.input.LA(1)

                if (LA29_0 == 92) :
                    alt29 = 1
                elif ((0 <= LA29_0 <= 38) or (40 <= LA29_0 <= 91) or (93 <= LA29_0 <= 65535)) :
                    alt29 = 2


                if alt29 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:719:18: ESC
                    pass 
                    self.mESC()


                elif alt29 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:719:22: ~ ( '\\\\' | '\\'' )
                    pass 
                    if (0 <= self.input.LA(1) <= 38) or (40 <= self.input.LA(1) <= 91) or (93 <= self.input.LA(1) <= 65535):
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse



                else:
                    if cnt29 >= 1:
                        break #loop29

                    eee = EarlyExitException(29, self.input)
                    raise eee

                cnt29 += 1




        finally:

            pass

    # $ANTLR end "TRIAPOS"



    # $ANTLR start "ESC"
    def mESC(self, ):

        try:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:724:5: ( '\\\\' . )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:724:10: '\\\\' .
            pass 
            self.match(92)
            self.matchAny()




        finally:

            pass

    # $ANTLR end "ESC"



    # $ANTLR start "CONTINUED_LINE"
    def mCONTINUED_LINE(self, ):

        try:
            _type = CONTINUED_LINE
            _channel = DEFAULT_CHANNEL

            newline = None

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:728:3: ( '\\\\' ( '\\r' )? '\\n' ( ' ' | '\\t' )* (newline= NEWLINE | ) )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:728:5: '\\\\' ( '\\r' )? '\\n' ( ' ' | '\\t' )* (newline= NEWLINE | )
            pass 
            self.match(92)
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:728:10: ( '\\r' )?
            alt30 = 2
            LA30_0 = self.input.LA(1)

            if (LA30_0 == 13) :
                alt30 = 1
            if alt30 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:728:12: '\\r'
                pass 
                self.match(13)



            self.match(10)
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:728:25: ( ' ' | '\\t' )*
            while True: #loop31
                alt31 = 2
                LA31_0 = self.input.LA(1)

                if (LA31_0 == 9 or LA31_0 == 32) :
                    alt31 = 1


                if alt31 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:
                    pass 
                    if self.input.LA(1) == 9 or self.input.LA(1) == 32:
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse



                else:
                    break #loop31
            #action start
            _channel=HIDDEN 
            #action end
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:729:7: (newline= NEWLINE | )
            alt32 = 2
            LA32_0 = self.input.LA(1)

            if (LA32_0 == 10 or (12 <= LA32_0 <= 13)) :
                alt32 = 1
            else:
                alt32 = 2
            if alt32 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:729:9: newline= NEWLINE
                pass 
                newlineStart1557 = self.getCharIndex()
                self.mNEWLINE()
                newline = CommonToken(
                    input=self.input, 
                    type=INVALID_TOKEN_TYPE,
                    channel=DEFAULT_CHANNEL,
                    start=newlineStart1557,
                    stop=self.getCharIndex()-1
                    )
                #action start
                self.emit( ClassicToken( NEWLINE, newline.text ) ) 
                #action end


            elif alt32 == 2:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:731:9: 
                pass 





            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "CONTINUED_LINE"



    # $ANTLR start "NEWLINE"
    def mNEWLINE(self, ):

        try:
            _type = NEWLINE
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:735:3: ( ( ( '\\u000C' )? ( '\\r' )? '\\n' )+ )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:735:5: ( ( '\\u000C' )? ( '\\r' )? '\\n' )+
            pass 
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:735:5: ( ( '\\u000C' )? ( '\\r' )? '\\n' )+
            cnt35 = 0
            while True: #loop35
                alt35 = 2
                LA35_0 = self.input.LA(1)

                if (LA35_0 == 10 or (12 <= LA35_0 <= 13)) :
                    alt35 = 1


                if alt35 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:735:7: ( '\\u000C' )? ( '\\r' )? '\\n'
                    pass 
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:735:7: ( '\\u000C' )?
                    alt33 = 2
                    LA33_0 = self.input.LA(1)

                    if (LA33_0 == 12) :
                        alt33 = 1
                    if alt33 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:735:9: '\\u000C'
                        pass 
                        self.match(12)



                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:735:21: ( '\\r' )?
                    alt34 = 2
                    LA34_0 = self.input.LA(1)

                    if (LA34_0 == 13) :
                        alt34 = 1
                    if alt34 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:735:23: '\\r'
                        pass 
                        self.match(13)



                    self.match(10)


                else:
                    if cnt35 >= 1:
                        break #loop35

                    eee = EarlyExitException(35, self.input)
                    raise eee

                cnt35 += 1
            #action start
                                                   
            if self.startPosition == 0 or self.implicitLineJoiningLevel > 0:
                _channel=HIDDEN
                
            #action end



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "NEWLINE"



    # $ANTLR start "WS"
    def mWS(self, ):

        try:
            _type = WS
            _channel = DEFAULT_CHANNEL

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:742:3: ({...}? => ( ' ' | '\\t' )+ )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:742:5: {...}? => ( ' ' | '\\t' )+
            pass 
            if not ((self.startPosition > 0 )):
                raise FailedPredicateException(self.input, "WS", " self.startPosition > 0 ")

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:742:36: ( ' ' | '\\t' )+
            cnt36 = 0
            while True: #loop36
                alt36 = 2
                LA36_0 = self.input.LA(1)

                if (LA36_0 == 9 or LA36_0 == 32) :
                    alt36 = 1


                if alt36 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:
                    pass 
                    if self.input.LA(1) == 9 or self.input.LA(1) == 32:
                        self.input.consume()
                    else:
                        mse = MismatchedSetException(None, self.input)
                        self.recover(mse)
                        raise mse



                else:
                    if cnt36 >= 1:
                        break #loop36

                    eee = EarlyExitException(36, self.input)
                    raise eee

                cnt36 += 1
            #action start
            _channel=HIDDEN 
            #action end



            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "WS"



    # $ANTLR start "LEADING_WS"
    def mLEADING_WS(self, ):

        try:
            _type = LEADING_WS
            _channel = DEFAULT_CHANNEL

            spaces = 0 
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:747:3: ({...}? => ({...}? ( ' ' | '\\t' )+ | ( ' ' | '\\t' )+ ( ( '\\r' )? '\\n' )* ) )
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:747:5: {...}? => ({...}? ( ' ' | '\\t' )+ | ( ' ' | '\\t' )+ ( ( '\\r' )? '\\n' )* )
            pass 
            if not ((self.startPosition == 0 )):
                raise FailedPredicateException(self.input, "LEADING_WS", " self.startPosition == 0 ")

            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:748:7: ({...}? ( ' ' | '\\t' )+ | ( ' ' | '\\t' )+ ( ( '\\r' )? '\\n' )* )
            alt41 = 2
            LA41_0 = self.input.LA(1)

            if (LA41_0 == 32) :
                LA41_1 = self.input.LA(2)

                if ((self.implicitLineJoiningLevel > 0)) :
                    alt41 = 1
                elif (True) :
                    alt41 = 2
                else:
                    nvae = NoViableAltException("", 41, 1, self.input)

                    raise nvae

            elif (LA41_0 == 9) :
                LA41_2 = self.input.LA(2)

                if ((self.implicitLineJoiningLevel > 0)) :
                    alt41 = 1
                elif (True) :
                    alt41 = 2
                else:
                    nvae = NoViableAltException("", 41, 2, self.input)

                    raise nvae

            else:
                nvae = NoViableAltException("", 41, 0, self.input)

                raise nvae

            if alt41 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:748:9: {...}? ( ' ' | '\\t' )+
                pass 
                if not ((self.implicitLineJoiningLevel > 0)):
                    raise FailedPredicateException(self.input, "LEADING_WS", "self.implicitLineJoiningLevel > 0")

                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:748:46: ( ' ' | '\\t' )+
                cnt37 = 0
                while True: #loop37
                    alt37 = 2
                    LA37_0 = self.input.LA(1)

                    if (LA37_0 == 9 or LA37_0 == 32) :
                        alt37 = 1


                    if alt37 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:
                        pass 
                        if self.input.LA(1) == 9 or self.input.LA(1) == 32:
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse



                    else:
                        if cnt37 >= 1:
                            break #loop37

                        eee = EarlyExitException(37, self.input)
                        raise eee

                    cnt37 += 1
                #action start
                _channel=HIDDEN 
                #action end


            elif alt41 == 2:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:749:11: ( ' ' | '\\t' )+ ( ( '\\r' )? '\\n' )*
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:749:11: ( ' ' | '\\t' )+
                cnt38 = 0
                while True: #loop38
                    alt38 = 3
                    LA38_0 = self.input.LA(1)

                    if (LA38_0 == 32) :
                        alt38 = 1
                    elif (LA38_0 == 9) :
                        alt38 = 2


                    if alt38 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:749:16: ' '
                        pass 
                        self.match(32)
                        #action start
                        spaces += 1 
                        #action end


                    elif alt38 == 2:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:750:15: '\\t'
                        pass 
                        self.match(9)
                        #action start
                                            
                        spaces += 8
                        spaces -= (spaces % 8)
                                           
                        #action end


                    else:
                        if cnt38 >= 1:
                            break #loop38

                        eee = EarlyExitException(38, self.input)
                        raise eee

                    cnt38 += 1
                #action start
                self.emit(ClassicToken(LEADING_WS, ' '*spaces)) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:755:16: ( ( '\\r' )? '\\n' )*
                while True: #loop40
                    alt40 = 2
                    LA40_0 = self.input.LA(1)

                    if (LA40_0 == 10 or LA40_0 == 13) :
                        alt40 = 1


                    if alt40 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:755:18: ( '\\r' )? '\\n'
                        pass 
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:755:18: ( '\\r' )?
                        alt39 = 2
                        LA39_0 = self.input.LA(1)

                        if (LA39_0 == 13) :
                            alt39 = 1
                        if alt39 == 1:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:755:19: '\\r'
                            pass 
                            self.match(13)



                        self.match(10)
                        #action start
                                                       
                        if self._state.token is not None:
                            self._state.token.setChannel(99)
                        else:
                            _channel=HIDDEN
                        	               
                        #action end


                    else:
                        break #loop40






            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "LEADING_WS"



    # $ANTLR start "COMMENT"
    def mCOMMENT(self, ):

        try:
            _type = COMMENT
            _channel = DEFAULT_CHANNEL

            _channel=HIDDEN 
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:767:3: ({...}? => ( ' ' | '\\t' )* '#' (~ '\\n' )* ( '\\n' )+ | {...}? => '#' (~ '\\n' )* )
            alt46 = 2
            alt46 = self.dfa46.predict(self.input)
            if alt46 == 1:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:767:5: {...}? => ( ' ' | '\\t' )* '#' (~ '\\n' )* ( '\\n' )+
                pass 
                if not ((self.startPosition == 0 )):
                    raise FailedPredicateException(self.input, "COMMENT", " self.startPosition == 0 ")

                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:767:37: ( ' ' | '\\t' )*
                while True: #loop42
                    alt42 = 2
                    LA42_0 = self.input.LA(1)

                    if (LA42_0 == 9 or LA42_0 == 32) :
                        alt42 = 1


                    if alt42 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:
                        pass 
                        if self.input.LA(1) == 9 or self.input.LA(1) == 32:
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse



                    else:
                        break #loop42
                self.match(35)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:767:53: (~ '\\n' )*
                while True: #loop43
                    alt43 = 2
                    LA43_0 = self.input.LA(1)

                    if ((0 <= LA43_0 <= 9) or (11 <= LA43_0 <= 65535)) :
                        alt43 = 1


                    if alt43 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:767:54: ~ '\\n'
                        pass 
                        if (0 <= self.input.LA(1) <= 9) or (11 <= self.input.LA(1) <= 65535):
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse



                    else:
                        break #loop43
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:767:62: ( '\\n' )+
                cnt44 = 0
                while True: #loop44
                    alt44 = 2
                    LA44_0 = self.input.LA(1)

                    if (LA44_0 == 10) :
                        alt44 = 1


                    if alt44 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:767:62: '\\n'
                        pass 
                        self.match(10)


                    else:
                        if cnt44 >= 1:
                            break #loop44

                        eee = EarlyExitException(44, self.input)
                        raise eee

                    cnt44 += 1


            elif alt46 == 2:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:768:7: {...}? => '#' (~ '\\n' )*
                pass 
                if not ((self.startPosition > 0 )):
                    raise FailedPredicateException(self.input, "COMMENT", " self.startPosition > 0 ")

                self.match(35)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:768:42: (~ '\\n' )*
                while True: #loop45
                    alt45 = 2
                    LA45_0 = self.input.LA(1)

                    if ((0 <= LA45_0 <= 9) or (11 <= LA45_0 <= 65535)) :
                        alt45 = 1


                    if alt45 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:768:43: ~ '\\n'
                        pass 
                        if (0 <= self.input.LA(1) <= 9) or (11 <= self.input.LA(1) <= 65535):
                            self.input.consume()
                        else:
                            mse = MismatchedSetException(None, self.input)
                            self.recover(mse)
                            raise mse



                    else:
                        break #loop45


            self._state.type = _type
            self._state.channel = _channel

        finally:

            pass

    # $ANTLR end "COMMENT"



    def mTokens(self):
        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:8: ( LPAREN | RPAREN | LBRACK | RBRACK | LCURLY | RCURLY | COLON | COMMA | DOT | SEMI | PLUS | MINUS | STAR | DOLLAR | SLASH | VBAR | AMPER | LESS | GREATER | ASSIGN | PERCENT | BACKQUOTE | CIRCUMFLEX | TILDE | EQUAL | ASSIGNEQUAL | NOTEQUAL | ALT_NOTEQUAL | LESSEQUAL | LEFTSHIFT | GREATEREQUAL | RIGHTSHIFT | PLUSEQUAL | MINUSEQUAL | DOUBLESTAR | STAREQUAL | DOUBLESLASH | SLASHEQUAL | VBAREQUAL | PERCENTEQUAL | AMPEREQUAL | CIRCUMFLEXEQUAL | LEFTSHIFTEQUAL | RIGHTSHIFTEQUAL | DOUBLESTAREQUAL | DOUBLESLASHEQUAL | GLOBAL | ATTRIBUTE | RULE | AGENDAGROUP | WHEN | EXISTS | THEN | MODIFY | INSERT | LEARN | DELETE | FORGET | HALT | PRINT | IMPORT | FROM | AND | OR | IN | IS | AS | NOT | FLOAT | LONGINT | INT | COMPLEX | NAME | OBJECTBINDING | STRING | CONTINUED_LINE | NEWLINE | WS | LEADING_WS | COMMENT )
        alt47 = 80
        alt47 = self.dfa47.predict(self.input)
        if alt47 == 1:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:10: LPAREN
            pass 
            self.mLPAREN()


        elif alt47 == 2:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:17: RPAREN
            pass 
            self.mRPAREN()


        elif alt47 == 3:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:24: LBRACK
            pass 
            self.mLBRACK()


        elif alt47 == 4:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:31: RBRACK
            pass 
            self.mRBRACK()


        elif alt47 == 5:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:38: LCURLY
            pass 
            self.mLCURLY()


        elif alt47 == 6:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:45: RCURLY
            pass 
            self.mRCURLY()


        elif alt47 == 7:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:52: COLON
            pass 
            self.mCOLON()


        elif alt47 == 8:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:58: COMMA
            pass 
            self.mCOMMA()


        elif alt47 == 9:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:64: DOT
            pass 
            self.mDOT()


        elif alt47 == 10:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:68: SEMI
            pass 
            self.mSEMI()


        elif alt47 == 11:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:73: PLUS
            pass 
            self.mPLUS()


        elif alt47 == 12:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:78: MINUS
            pass 
            self.mMINUS()


        elif alt47 == 13:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:84: STAR
            pass 
            self.mSTAR()


        elif alt47 == 14:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:89: DOLLAR
            pass 
            self.mDOLLAR()


        elif alt47 == 15:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:96: SLASH
            pass 
            self.mSLASH()


        elif alt47 == 16:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:102: VBAR
            pass 
            self.mVBAR()


        elif alt47 == 17:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:107: AMPER
            pass 
            self.mAMPER()


        elif alt47 == 18:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:113: LESS
            pass 
            self.mLESS()


        elif alt47 == 19:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:118: GREATER
            pass 
            self.mGREATER()


        elif alt47 == 20:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:126: ASSIGN
            pass 
            self.mASSIGN()


        elif alt47 == 21:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:133: PERCENT
            pass 
            self.mPERCENT()


        elif alt47 == 22:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:141: BACKQUOTE
            pass 
            self.mBACKQUOTE()


        elif alt47 == 23:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:151: CIRCUMFLEX
            pass 
            self.mCIRCUMFLEX()


        elif alt47 == 24:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:162: TILDE
            pass 
            self.mTILDE()


        elif alt47 == 25:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:168: EQUAL
            pass 
            self.mEQUAL()


        elif alt47 == 26:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:174: ASSIGNEQUAL
            pass 
            self.mASSIGNEQUAL()


        elif alt47 == 27:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:186: NOTEQUAL
            pass 
            self.mNOTEQUAL()


        elif alt47 == 28:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:195: ALT_NOTEQUAL
            pass 
            self.mALT_NOTEQUAL()


        elif alt47 == 29:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:208: LESSEQUAL
            pass 
            self.mLESSEQUAL()


        elif alt47 == 30:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:218: LEFTSHIFT
            pass 
            self.mLEFTSHIFT()


        elif alt47 == 31:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:228: GREATEREQUAL
            pass 
            self.mGREATEREQUAL()


        elif alt47 == 32:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:241: RIGHTSHIFT
            pass 
            self.mRIGHTSHIFT()


        elif alt47 == 33:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:252: PLUSEQUAL
            pass 
            self.mPLUSEQUAL()


        elif alt47 == 34:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:262: MINUSEQUAL
            pass 
            self.mMINUSEQUAL()


        elif alt47 == 35:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:273: DOUBLESTAR
            pass 
            self.mDOUBLESTAR()


        elif alt47 == 36:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:284: STAREQUAL
            pass 
            self.mSTAREQUAL()


        elif alt47 == 37:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:294: DOUBLESLASH
            pass 
            self.mDOUBLESLASH()


        elif alt47 == 38:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:306: SLASHEQUAL
            pass 
            self.mSLASHEQUAL()


        elif alt47 == 39:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:317: VBAREQUAL
            pass 
            self.mVBAREQUAL()


        elif alt47 == 40:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:327: PERCENTEQUAL
            pass 
            self.mPERCENTEQUAL()


        elif alt47 == 41:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:340: AMPEREQUAL
            pass 
            self.mAMPEREQUAL()


        elif alt47 == 42:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:351: CIRCUMFLEXEQUAL
            pass 
            self.mCIRCUMFLEXEQUAL()


        elif alt47 == 43:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:367: LEFTSHIFTEQUAL
            pass 
            self.mLEFTSHIFTEQUAL()


        elif alt47 == 44:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:382: RIGHTSHIFTEQUAL
            pass 
            self.mRIGHTSHIFTEQUAL()


        elif alt47 == 45:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:398: DOUBLESTAREQUAL
            pass 
            self.mDOUBLESTAREQUAL()


        elif alt47 == 46:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:414: DOUBLESLASHEQUAL
            pass 
            self.mDOUBLESLASHEQUAL()


        elif alt47 == 47:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:431: GLOBAL
            pass 
            self.mGLOBAL()


        elif alt47 == 48:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:438: ATTRIBUTE
            pass 
            self.mATTRIBUTE()


        elif alt47 == 49:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:448: RULE
            pass 
            self.mRULE()


        elif alt47 == 50:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:453: AGENDAGROUP
            pass 
            self.mAGENDAGROUP()


        elif alt47 == 51:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:465: WHEN
            pass 
            self.mWHEN()


        elif alt47 == 52:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:470: EXISTS
            pass 
            self.mEXISTS()


        elif alt47 == 53:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:477: THEN
            pass 
            self.mTHEN()


        elif alt47 == 54:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:482: MODIFY
            pass 
            self.mMODIFY()


        elif alt47 == 55:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:489: INSERT
            pass 
            self.mINSERT()


        elif alt47 == 56:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:496: LEARN
            pass 
            self.mLEARN()


        elif alt47 == 57:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:502: DELETE
            pass 
            self.mDELETE()


        elif alt47 == 58:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:509: FORGET
            pass 
            self.mFORGET()


        elif alt47 == 59:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:516: HALT
            pass 
            self.mHALT()


        elif alt47 == 60:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:521: PRINT
            pass 
            self.mPRINT()


        elif alt47 == 61:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:527: IMPORT
            pass 
            self.mIMPORT()


        elif alt47 == 62:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:534: FROM
            pass 
            self.mFROM()


        elif alt47 == 63:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:539: AND
            pass 
            self.mAND()


        elif alt47 == 64:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:543: OR
            pass 
            self.mOR()


        elif alt47 == 65:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:546: IN
            pass 
            self.mIN()


        elif alt47 == 66:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:549: IS
            pass 
            self.mIS()


        elif alt47 == 67:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:552: AS
            pass 
            self.mAS()


        elif alt47 == 68:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:555: NOT
            pass 
            self.mNOT()


        elif alt47 == 69:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:559: FLOAT
            pass 
            self.mFLOAT()


        elif alt47 == 70:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:565: LONGINT
            pass 
            self.mLONGINT()


        elif alt47 == 71:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:573: INT
            pass 
            self.mINT()


        elif alt47 == 72:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:577: COMPLEX
            pass 
            self.mCOMPLEX()


        elif alt47 == 73:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:585: NAME
            pass 
            self.mNAME()


        elif alt47 == 74:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:590: OBJECTBINDING
            pass 
            self.mOBJECTBINDING()


        elif alt47 == 75:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:604: STRING
            pass 
            self.mSTRING()


        elif alt47 == 76:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:611: CONTINUED_LINE
            pass 
            self.mCONTINUED_LINE()


        elif alt47 == 77:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:626: NEWLINE
            pass 
            self.mNEWLINE()


        elif alt47 == 78:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:634: WS
            pass 
            self.mWS()


        elif alt47 == 79:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:637: LEADING_WS
            pass 
            self.mLEADING_WS()


        elif alt47 == 80:
            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:1:648: COMMENT
            pass 
            self.mCOMMENT()







    # lookup tables for DFA #9

    DFA9_eot = DFA.unpack(
        u"\3\uffff\1\4\2\uffff"
        )

    DFA9_eof = DFA.unpack(
        u"\6\uffff"
        )

    DFA9_min = DFA.unpack(
        u"\1\56\1\uffff\1\56\1\105\2\uffff"
        )

    DFA9_max = DFA.unpack(
        u"\1\71\1\uffff\2\145\2\uffff"
        )

    DFA9_accept = DFA.unpack(
        u"\1\uffff\1\1\2\uffff\1\3\1\2"
        )

    DFA9_special = DFA.unpack(
        u"\6\uffff"
        )

            
    DFA9_transition = [
        DFA.unpack(u"\1\1\1\uffff\12\2"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\3\1\uffff\12\2\13\uffff\1\4\37\uffff\1\4"),
        DFA.unpack(u"\1\5\37\uffff\1\5"),
        DFA.unpack(u""),
        DFA.unpack(u"")
    ]

    # class definition for DFA #9

    class DFA9(DFA):
        pass


    # lookup tables for DFA #16

    DFA16_eot = DFA.unpack(
        u"\7\uffff"
        )

    DFA16_eof = DFA.unpack(
        u"\7\uffff"
        )

    DFA16_min = DFA.unpack(
        u"\3\56\2\uffff\2\56"
        )

    DFA16_max = DFA.unpack(
        u"\1\71\1\170\1\152\2\uffff\2\152"
        )

    DFA16_accept = DFA.unpack(
        u"\3\uffff\1\2\1\1\2\uffff"
        )

    DFA16_special = DFA.unpack(
        u"\7\uffff"
        )

            
    DFA16_transition = [
        DFA.unpack(u"\1\3\1\uffff\1\1\11\2"),
        DFA.unpack(u"\1\3\1\uffff\12\5\13\uffff\1\3\4\uffff\1\4\15\uffff"
        u"\1\4\14\uffff\1\3\4\uffff\1\4\15\uffff\1\4"),
        DFA.unpack(u"\1\3\1\uffff\12\6\13\uffff\1\3\4\uffff\1\4\32\uffff"
        u"\1\3\4\uffff\1\4"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\3\1\uffff\12\5\13\uffff\1\3\4\uffff\1\4\32\uffff"
        u"\1\3\4\uffff\1\4"),
        DFA.unpack(u"\1\3\1\uffff\12\6\13\uffff\1\3\4\uffff\1\4\32\uffff"
        u"\1\3\4\uffff\1\4")
    ]

    # class definition for DFA #16

    class DFA16(DFA):
        pass


    # lookup tables for DFA #46

    DFA46_eot = DFA.unpack(
        u"\2\uffff\2\4\1\uffff"
        )

    DFA46_eof = DFA.unpack(
        u"\5\uffff"
        )

    DFA46_min = DFA.unpack(
        u"\1\11\1\uffff\2\0\1\uffff"
        )

    DFA46_max = DFA.unpack(
        u"\1\43\1\uffff\2\uffff\1\uffff"
        )

    DFA46_accept = DFA.unpack(
        u"\1\uffff\1\1\2\uffff\1\2"
        )

    DFA46_special = DFA.unpack(
        u"\1\2\1\uffff\1\1\1\0\1\uffff"
        )

            
    DFA46_transition = [
        DFA.unpack(u"\1\1\26\uffff\1\1\2\uffff\1\2"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\3\1\1\ufff5\3"),
        DFA.unpack(u"\12\3\1\1\ufff5\3"),
        DFA.unpack(u"")
    ]

    # class definition for DFA #46

    class DFA46(DFA):
        pass


        def specialStateTransition(self_, s, input):
            # convince pylint that my self_ magic is ok ;)
            # pylint: disable-msg=E0213

            # pretend we are a member of the recognizer
            # thus semantic predicates can be evaluated
            self = self_.recognizer

            _s = s

            if s == 0: 
                LA46_3 = input.LA(1)

                 
                index46_3 = input.index()
                input.rewind()
                s = -1
                if (LA46_3 == 10) and ((self.startPosition == 0 )):
                    s = 1

                elif ((0 <= LA46_3 <= 9) or (11 <= LA46_3 <= 65535)) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 3

                else:
                    s = 4

                 
                input.seek(index46_3)
                if s >= 0:
                    return s
            elif s == 1: 
                LA46_2 = input.LA(1)

                 
                index46_2 = input.index()
                input.rewind()
                s = -1
                if ((0 <= LA46_2 <= 9) or (11 <= LA46_2 <= 65535)) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 3

                elif (LA46_2 == 10) and ((self.startPosition == 0 )):
                    s = 1

                else:
                    s = 4

                 
                input.seek(index46_2)
                if s >= 0:
                    return s
            elif s == 2: 
                LA46_0 = input.LA(1)

                 
                index46_0 = input.index()
                input.rewind()
                s = -1
                if (LA46_0 == 9 or LA46_0 == 32) and ((self.startPosition == 0 )):
                    s = 1

                elif (LA46_0 == 35) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 2

                 
                input.seek(index46_0)
                if s >= 0:
                    return s

            nvae = NoViableAltException(self_.getDescription(), 46, _s, input)
            self_.error(nvae)
            raise nvae
    # lookup tables for DFA #47

    DFA47_eot = DFA.unpack(
        u"\7\uffff\1\64\1\uffff\1\66\1\uffff\1\70\1\72\1\75\1\76\1\102\1"
        u"\104\1\106\1\112\1\115\1\117\1\121\1\uffff\1\123\2\uffff\17\54"
        u"\2\152\1\54\4\uffff\1\163\1\165\3\uffff\1\166\5\uffff\1\171\4\uffff"
        u"\1\173\10\uffff\1\175\2\uffff\1\177\7\uffff\4\54\1\u0084\5\54\1"
        u"\u008b\1\54\1\u008d\6\54\1\u0094\1\54\2\uffff\1\166\1\152\3\uffff"
        u"\1\152\1\54\16\uffff\3\54\1\u00a3\1\uffff\6\54\1\uffff\1\54\1\uffff"
        u"\6\54\1\uffff\1\u00b1\3\152\1\166\2\uffff\1\166\2\uffff\1\166\3"
        u"\54\1\uffff\1\u00b8\1\u00b9\1\54\1\u00bb\6\54\1\u00c2\1\u00c3\1"
        u"\54\3\uffff\1\166\3\54\2\uffff\1\54\1\uffff\3\54\1\u00ce\2\54\2"
        u"\uffff\1\u00d1\1\uffff\1\166\1\u00d2\2\54\1\u00d5\1\u00d6\1\u00d7"
        u"\1\u00d8\1\uffff\1\u00d9\1\u00da\2\uffff\1\54\7\uffff\1\54\1\u00dd"
        u"\1\uffff"
        )

    DFA47_eof = DFA.unpack(
        u"\u00de\uffff"
        )

    DFA47_min = DFA.unpack(
        u"\1\11\6\uffff\1\75\1\uffff\1\60\1\uffff\2\75\1\52\1\101\1\57\2"
        u"\75\1\74\3\75\1\uffff\1\75\2\uffff\1\154\1\147\1\42\1\150\1\170"
        u"\1\150\1\157\1\155\2\145\1\157\1\141\2\162\1\157\2\56\1\42\4\uffff"
        u"\2\11\3\uffff\1\60\5\uffff\1\75\4\uffff\1\75\10\uffff\1\75\2\uffff"
        u"\1\75\7\uffff\1\157\1\164\1\145\1\144\1\60\1\154\1\145\1\151\1"
        u"\145\1\144\1\60\1\160\1\60\1\141\1\154\1\162\1\157\1\154\1\151"
        u"\1\60\1\164\1\60\1\uffff\1\60\1\56\1\uffff\1\53\1\uffff\1\56\1"
        u"\42\1\uffff\1\0\1\uffff\1\0\1\uffff\1\53\10\uffff\1\142\1\162\1"
        u"\156\1\60\1\uffff\1\145\1\156\1\163\1\156\1\151\1\145\1\uffff\1"
        u"\157\1\uffff\1\162\1\145\1\147\1\155\1\164\1\156\1\uffff\5\60\1"
        u"\53\2\60\1\uffff\2\60\1\141\1\151\1\144\1\uffff\2\60\1\164\1\60"
        u"\1\146\2\162\1\156\1\164\1\145\2\60\1\164\1\uffff\1\53\2\60\1\154"
        u"\1\142\1\141\2\uffff\1\163\1\uffff\1\171\2\164\1\60\1\145\1\164"
        u"\2\uffff\4\60\1\165\1\55\4\60\1\uffff\2\60\2\uffff\1\164\7\uffff"
        u"\1\145\1\60\1\uffff"
        )

    DFA47_max = DFA.unpack(
        u"\1\176\6\uffff\1\75\1\uffff\1\71\1\uffff\3\75\1\172\3\75\2\76\2"
        u"\75\1\uffff\1\75\2\uffff\1\154\1\164\1\165\1\150\1\170\1\150\1"
        u"\157\1\163\2\145\1\162\1\141\2\162\1\157\1\170\1\154\1\162\4\uffff"
        u"\2\43\3\uffff\1\152\5\uffff\1\75\4\uffff\1\75\10\uffff\1\75\2\uffff"
        u"\1\75\7\uffff\1\157\1\164\1\145\1\144\1\172\1\154\1\145\1\151\1"
        u"\145\1\144\1\172\1\160\1\172\1\141\1\154\1\162\1\157\1\154\1\151"
        u"\1\172\1\164\1\146\1\uffff\1\152\1\154\1\uffff\1\71\1\uffff\1\154"
        u"\1\47\1\uffff\1\0\1\uffff\1\0\1\uffff\1\71\10\uffff\1\142\1\162"
        u"\1\156\1\172\1\uffff\1\145\1\156\1\163\1\156\1\151\1\145\1\uffff"
        u"\1\157\1\uffff\1\162\1\145\1\147\1\155\1\164\1\156\1\uffff\1\172"
        u"\3\154\1\152\2\71\1\152\1\uffff\1\71\1\152\1\141\1\151\1\144\1"
        u"\uffff\2\172\1\164\1\172\1\146\2\162\1\156\1\164\1\145\2\172\1"
        u"\164\1\uffff\2\71\1\152\1\154\1\142\1\141\2\uffff\1\163\1\uffff"
        u"\1\171\2\164\1\172\1\145\1\164\2\uffff\1\172\1\71\1\152\1\172\1"
        u"\165\1\55\4\172\1\uffff\2\172\2\uffff\1\164\7\uffff\1\145\1\172"
        u"\1\uffff"
        )

    DFA47_accept = DFA.unpack(
        u"\1\uffff\1\1\1\2\1\3\1\4\1\5\1\6\1\uffff\1\10\1\uffff\1\12\13\uffff"
        u"\1\26\1\uffff\1\30\1\33\22\uffff\1\111\1\113\1\114\1\115\2\uffff"
        u"\1\120\1\32\1\7\1\uffff\1\11\1\41\1\13\1\42\1\14\1\uffff\1\44\1"
        u"\15\1\16\1\112\1\uffff\1\46\1\17\1\47\1\20\1\51\1\21\1\34\1\35"
        u"\1\uffff\1\22\1\37\1\uffff\1\23\1\31\1\24\1\50\1\25\1\52\1\27\26"
        u"\uffff\1\107\2\uffff\1\106\1\uffff\1\110\2\uffff\1\120\1\uffff"
        u"\1\117\1\uffff\1\105\1\uffff\1\55\1\43\1\56\1\45\1\53\1\36\1\54"
        u"\1\40\4\uffff\1\103\6\uffff\1\101\1\uffff\1\102\6\uffff\1\100\10"
        u"\uffff\1\116\5\uffff\1\77\15\uffff\1\104\6\uffff\1\61\1\63\1\uffff"
        u"\1\65\6\uffff\1\76\1\73\12\uffff\1\70\2\uffff\1\74\1\57\1\uffff"
        u"\1\62\1\64\1\66\1\67\1\75\1\71\1\72\2\uffff\1\60"
        )

    DFA47_special = DFA.unpack(
        u"\1\2\57\uffff\1\0\1\1\101\uffff\1\3\1\uffff\1\4\150\uffff"
        )

            
    DFA47_transition = [
        DFA.unpack(u"\1\61\1\57\1\uffff\2\57\22\uffff\1\60\1\31\1\55\1\62"
        u"\1\16\1\25\1\21\1\55\1\1\1\2\1\15\1\13\1\10\1\14\1\11\1\17\1\51"
        u"\11\52\1\7\1\12\1\22\1\24\1\23\2\uffff\32\54\1\3\1\56\1\4\1\27"
        u"\1\54\1\26\1\33\2\54\1\43\1\36\1\44\1\32\1\45\1\41\2\54\1\42\1"
        u"\40\1\50\1\47\1\46\1\54\1\34\1\54\1\37\1\53\1\54\1\35\3\54\1\5"
        u"\1\20\1\6\1\30"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\63"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\65"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\67"),
        DFA.unpack(u"\1\71"),
        DFA.unpack(u"\1\73\22\uffff\1\74"),
        DFA.unpack(u"\32\77\4\uffff\1\77\1\uffff\32\77"),
        DFA.unpack(u"\1\100\15\uffff\1\101"),
        DFA.unpack(u"\1\103"),
        DFA.unpack(u"\1\105"),
        DFA.unpack(u"\1\111\1\110\1\107"),
        DFA.unpack(u"\1\113\1\114"),
        DFA.unpack(u"\1\116"),
        DFA.unpack(u"\1\120"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\122"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\124"),
        DFA.unpack(u"\1\126\6\uffff\1\127\4\uffff\1\130\1\125"),
        DFA.unpack(u"\1\55\4\uffff\1\55\115\uffff\1\131"),
        DFA.unpack(u"\1\132"),
        DFA.unpack(u"\1\133"),
        DFA.unpack(u"\1\134"),
        DFA.unpack(u"\1\135"),
        DFA.unpack(u"\1\137\1\136\4\uffff\1\140"),
        DFA.unpack(u"\1\141"),
        DFA.unpack(u"\1\142"),
        DFA.unpack(u"\1\143\2\uffff\1\144"),
        DFA.unpack(u"\1\145"),
        DFA.unpack(u"\1\146"),
        DFA.unpack(u"\1\147"),
        DFA.unpack(u"\1\150"),
        DFA.unpack(u"\1\153\1\uffff\12\154\13\uffff\1\156\4\uffff\1\157"
        u"\1\uffff\1\155\13\uffff\1\151\14\uffff\1\156\4\uffff\1\157\1\uffff"
        u"\1\155\13\uffff\1\151"),
        DFA.unpack(u"\1\153\1\uffff\12\160\13\uffff\1\156\4\uffff\1\157"
        u"\1\uffff\1\155\30\uffff\1\156\4\uffff\1\157\1\uffff\1\155"),
        DFA.unpack(u"\1\55\4\uffff\1\55\112\uffff\1\161"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\61\1\164\2\uffff\1\164\22\uffff\1\60\2\uffff\1\162"),
        DFA.unpack(u"\1\61\1\164\2\uffff\1\164\22\uffff\1\60\2\uffff\1\162"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\12\65\13\uffff\1\167\4\uffff\1\157\32\uffff\1\167"
        u"\4\uffff\1\157"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\170"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\172"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\174"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\176"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u0080"),
        DFA.unpack(u"\1\u0081"),
        DFA.unpack(u"\1\u0082"),
        DFA.unpack(u"\1\u0083"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\1\u0085"),
        DFA.unpack(u"\1\u0086"),
        DFA.unpack(u"\1\u0087"),
        DFA.unpack(u"\1\u0088"),
        DFA.unpack(u"\1\u0089"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\22\54\1\u008a"
        u"\7\54"),
        DFA.unpack(u"\1\u008c"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\1\u008e"),
        DFA.unpack(u"\1\u008f"),
        DFA.unpack(u"\1\u0090"),
        DFA.unpack(u"\1\u0091"),
        DFA.unpack(u"\1\u0092"),
        DFA.unpack(u"\1\u0093"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\1\u0095"),
        DFA.unpack(u"\12\u0096\7\uffff\6\u0098\32\uffff\6\u0097"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\u0099\13\uffff\1\u009a\4\uffff\1\157\32\uffff\1"
        u"\u009a\4\uffff\1\157"),
        DFA.unpack(u"\1\153\1\uffff\12\154\13\uffff\1\156\4\uffff\1\157"
        u"\1\uffff\1\155\30\uffff\1\156\4\uffff\1\157\1\uffff\1\155"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u009b\1\uffff\1\u009b\2\uffff\12\u009c"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\153\1\uffff\12\160\13\uffff\1\156\4\uffff\1\157"
        u"\1\uffff\1\155\30\uffff\1\156\4\uffff\1\157\1\uffff\1\155"),
        DFA.unpack(u"\1\55\4\uffff\1\55"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\uffff"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\uffff"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u009e\1\uffff\1\u009e\2\uffff\12\u009f"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u00a0"),
        DFA.unpack(u"\1\u00a1"),
        DFA.unpack(u"\1\u00a2"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u00a4"),
        DFA.unpack(u"\1\u00a5"),
        DFA.unpack(u"\1\u00a6"),
        DFA.unpack(u"\1\u00a7"),
        DFA.unpack(u"\1\u00a8"),
        DFA.unpack(u"\1\u00a9"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u00aa"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u00ab"),
        DFA.unpack(u"\1\u00ac"),
        DFA.unpack(u"\1\u00ad"),
        DFA.unpack(u"\1\u00ae"),
        DFA.unpack(u"\1\u00af"),
        DFA.unpack(u"\1\u00b0"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\12\u0096\7\uffff\6\u0098\3\uffff\1\157\1\uffff\1\155"
        u"\24\uffff\6\u0097\3\uffff\1\157\1\uffff\1\155"),
        DFA.unpack(u"\12\u0096\7\uffff\6\u0098\3\uffff\1\157\1\uffff\1\155"
        u"\24\uffff\6\u0097\3\uffff\1\157\1\uffff\1\155"),
        DFA.unpack(u"\12\u0096\7\uffff\6\u0098\3\uffff\1\157\1\uffff\1\155"
        u"\24\uffff\6\u0097\3\uffff\1\157\1\uffff\1\155"),
        DFA.unpack(u"\12\u0099\13\uffff\1\u00b2\4\uffff\1\157\32\uffff\1"
        u"\u00b2\4\uffff\1\157"),
        DFA.unpack(u"\1\u00b3\1\uffff\1\u00b3\2\uffff\12\u00b4"),
        DFA.unpack(u"\12\u009c"),
        DFA.unpack(u"\12\u009c\20\uffff\1\157\37\uffff\1\157"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\u009f"),
        DFA.unpack(u"\12\u009f\20\uffff\1\157\37\uffff\1\157"),
        DFA.unpack(u"\1\u00b5"),
        DFA.unpack(u"\1\u00b6"),
        DFA.unpack(u"\1\u00b7"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\1\u00ba"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\1\u00bc"),
        DFA.unpack(u"\1\u00bd"),
        DFA.unpack(u"\1\u00be"),
        DFA.unpack(u"\1\u00bf"),
        DFA.unpack(u"\1\u00c0"),
        DFA.unpack(u"\1\u00c1"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\1\u00c4"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u00c5\1\uffff\1\u00c5\2\uffff\12\u00c6"),
        DFA.unpack(u"\12\u00b4"),
        DFA.unpack(u"\12\u00b4\20\uffff\1\157\37\uffff\1\157"),
        DFA.unpack(u"\1\u00c7"),
        DFA.unpack(u"\1\u00c8"),
        DFA.unpack(u"\1\u00c9"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u00ca"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u00cb"),
        DFA.unpack(u"\1\u00cc"),
        DFA.unpack(u"\1\u00cd"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\1\u00cf"),
        DFA.unpack(u"\1\u00d0"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\12\u00c6"),
        DFA.unpack(u"\12\u00c6\20\uffff\1\157\37\uffff\1\157"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\1\u00d3"),
        DFA.unpack(u"\1\u00d4"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u""),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u00db"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\u00dc"),
        DFA.unpack(u"\12\54\7\uffff\32\54\4\uffff\1\54\1\uffff\32\54"),
        DFA.unpack(u"")
    ]

    # class definition for DFA #47

    class DFA47(DFA):
        pass


        def specialStateTransition(self_, s, input):
            # convince pylint that my self_ magic is ok ;)
            # pylint: disable-msg=E0213

            # pretend we are a member of the recognizer
            # thus semantic predicates can be evaluated
            self = self_.recognizer

            _s = s

            if s == 0: 
                LA47_48 = input.LA(1)

                 
                index47_48 = input.index()
                input.rewind()
                s = -1
                if (LA47_48 == 35) and ((self.startPosition == 0 )):
                    s = 114

                elif (LA47_48 == 32) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 48

                elif (LA47_48 == 10 or LA47_48 == 13) and ((self.startPosition == 0 )):
                    s = 116

                elif (LA47_48 == 9) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 49

                else:
                    s = 115

                 
                input.seek(index47_48)
                if s >= 0:
                    return s
            elif s == 1: 
                LA47_49 = input.LA(1)

                 
                index47_49 = input.index()
                input.rewind()
                s = -1
                if (LA47_49 == 35) and ((self.startPosition == 0 )):
                    s = 114

                elif (LA47_49 == 32) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 48

                elif (LA47_49 == 10 or LA47_49 == 13) and ((self.startPosition == 0 )):
                    s = 116

                elif (LA47_49 == 9) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 49

                else:
                    s = 117

                 
                input.seek(index47_49)
                if s >= 0:
                    return s
            elif s == 2: 
                LA47_0 = input.LA(1)

                 
                index47_0 = input.index()
                input.rewind()
                s = -1
                if (LA47_0 == 40):
                    s = 1

                elif (LA47_0 == 41):
                    s = 2

                elif (LA47_0 == 91):
                    s = 3

                elif (LA47_0 == 93):
                    s = 4

                elif (LA47_0 == 123):
                    s = 5

                elif (LA47_0 == 125):
                    s = 6

                elif (LA47_0 == 58):
                    s = 7

                elif (LA47_0 == 44):
                    s = 8

                elif (LA47_0 == 46):
                    s = 9

                elif (LA47_0 == 59):
                    s = 10

                elif (LA47_0 == 43):
                    s = 11

                elif (LA47_0 == 45):
                    s = 12

                elif (LA47_0 == 42):
                    s = 13

                elif (LA47_0 == 36):
                    s = 14

                elif (LA47_0 == 47):
                    s = 15

                elif (LA47_0 == 124):
                    s = 16

                elif (LA47_0 == 38):
                    s = 17

                elif (LA47_0 == 60):
                    s = 18

                elif (LA47_0 == 62):
                    s = 19

                elif (LA47_0 == 61):
                    s = 20

                elif (LA47_0 == 37):
                    s = 21

                elif (LA47_0 == 96):
                    s = 22

                elif (LA47_0 == 94):
                    s = 23

                elif (LA47_0 == 126):
                    s = 24

                elif (LA47_0 == 33):
                    s = 25

                elif (LA47_0 == 103):
                    s = 26

                elif (LA47_0 == 97):
                    s = 27

                elif (LA47_0 == 114):
                    s = 28

                elif (LA47_0 == 119):
                    s = 29

                elif (LA47_0 == 101):
                    s = 30

                elif (LA47_0 == 116):
                    s = 31

                elif (LA47_0 == 109):
                    s = 32

                elif (LA47_0 == 105):
                    s = 33

                elif (LA47_0 == 108):
                    s = 34

                elif (LA47_0 == 100):
                    s = 35

                elif (LA47_0 == 102):
                    s = 36

                elif (LA47_0 == 104):
                    s = 37

                elif (LA47_0 == 112):
                    s = 38

                elif (LA47_0 == 111):
                    s = 39

                elif (LA47_0 == 110):
                    s = 40

                elif (LA47_0 == 48):
                    s = 41

                elif ((49 <= LA47_0 <= 57)):
                    s = 42

                elif (LA47_0 == 117):
                    s = 43

                elif ((65 <= LA47_0 <= 90) or LA47_0 == 95 or (98 <= LA47_0 <= 99) or (106 <= LA47_0 <= 107) or LA47_0 == 113 or LA47_0 == 115 or LA47_0 == 118 or (120 <= LA47_0 <= 122)):
                    s = 44

                elif (LA47_0 == 34 or LA47_0 == 39):
                    s = 45

                elif (LA47_0 == 92):
                    s = 46

                elif (LA47_0 == 10 or (12 <= LA47_0 <= 13)):
                    s = 47

                elif (LA47_0 == 32) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 48

                elif (LA47_0 == 9) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 49

                elif (LA47_0 == 35) and (((self.startPosition > 0 ) or (self.startPosition == 0 ))):
                    s = 50

                 
                input.seek(index47_0)
                if s >= 0:
                    return s
            elif s == 3: 
                LA47_115 = input.LA(1)

                 
                index47_115 = input.index()
                input.rewind()
                s = -1
                if ((self.startPosition > 0 )):
                    s = 157

                elif (((self.startPosition == 0 ) or (((self.startPosition == 0 )) and ((self.implicitLineJoiningLevel > 0))))):
                    s = 116

                 
                input.seek(index47_115)
                if s >= 0:
                    return s
            elif s == 4: 
                LA47_117 = input.LA(1)

                 
                index47_117 = input.index()
                input.rewind()
                s = -1
                if ((self.startPosition > 0 )):
                    s = 157

                elif (((self.startPosition == 0 ) or (((self.startPosition == 0 )) and ((self.implicitLineJoiningLevel > 0))))):
                    s = 116

                 
                input.seek(index47_117)
                if s >= 0:
                    return s

            nvae = NoViableAltException(self_.getDescription(), 47, _s, input)
            self_.error(nvae)
            raise nvae
 



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import LexerMain
    main = LexerMain(PolicyLexer)
    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = PolicyParser
# $ANTLR 3.1.3 Mar 17, 2009 19:23:44 /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g 2013-03-25 15:29:47

import sys
from antlr3 import *
from antlr3.compat import set, frozenset
         
from intellect.Node import *



# for convenience in actions
HIDDEN = BaseRecognizer.HIDDEN

# token types
SLASHEQUAL=38
BACKQUOTE=80
EXPONENT=84
STAR=64
CIRCUMFLEXEQUAL=42
LETTER=82
TRIAPOS=85
GREATEREQUAL=52
COMPLEX=77
ASSIGNEQUAL=24
NOT=21
EOF=-1
NOTEQUAL=55
LEADING_WS=90
MINUSEQUAL=36
VBAR=58
RPAREN=10
IMPORT=7
NAME=12
GREATER=50
INSERT=31
DOUBLESTAREQUAL=45
LESS=49
COMMENT=91
RBRACK=71
RULE=15
LCURLY=72
INT=74
DELETE=29
RIGHTSHIFT=27
DOUBLESLASHEQUAL=46
WS=89
VBAREQUAL=41
OR=47
LONGINT=75
FORGET=28
FROM=8
PERCENTEQUAL=39
LESSEQUAL=53
DOLLAR=79
MODIFY=32
DOUBLESLASH=67
LBRACK=70
CONTINUED_LINE=88
OBJECTBINDING=23
DOUBLESTAR=69
HALT=33
ESC=87
ATTRIBUTE=25
DEDENT=5
FLOAT=76
RIGHTSHIFTEQUAL=44
AND=48
LEARN=30
INDENT=4
LPAREN=9
PLUSEQUAL=35
AS=13
SLASH=65
THEN=20
IN=56
COMMA=11
IS=57
AMPER=60
EQUAL=51
TILDE=68
LEFTSHIFTEQUAL=43
LEFTSHIFT=61
PLUS=62
EXISTS=22
DIGIT=83
DOT=14
AGENDAGROUP=18
PERCENT=66
MINUS=63
SEMI=78
PRINT=26
COLON=16
TRIQUOTE=86
AMPEREQUAL=40
NEWLINE=6
WHEN=19
RCURLY=73
ASSIGN=34
GLOBAL=81
STAREQUAL=37
CIRCUMFLEX=59
STRING=17
ALT_NOTEQUAL=54

# token names
tokenNames = [
    "<invalid>", "<EOR>", "<DOWN>", "<UP>", 
    "INDENT", "DEDENT", "NEWLINE", "IMPORT", "FROM", "LPAREN", "RPAREN", 
    "COMMA", "NAME", "AS", "DOT", "RULE", "COLON", "STRING", "AGENDAGROUP", 
    "WHEN", "THEN", "NOT", "EXISTS", "OBJECTBINDING", "ASSIGNEQUAL", "ATTRIBUTE", 
    "PRINT", "RIGHTSHIFT", "FORGET", "DELETE", "LEARN", "INSERT", "MODIFY", 
    "HALT", "ASSIGN", "PLUSEQUAL", "MINUSEQUAL", "STAREQUAL", "SLASHEQUAL", 
    "PERCENTEQUAL", "AMPEREQUAL", "VBAREQUAL", "CIRCUMFLEXEQUAL", "LEFTSHIFTEQUAL", 
    "RIGHTSHIFTEQUAL", "DOUBLESTAREQUAL", "DOUBLESLASHEQUAL", "OR", "AND", 
    "LESS", "GREATER", "EQUAL", "GREATEREQUAL", "LESSEQUAL", "ALT_NOTEQUAL", 
    "NOTEQUAL", "IN", "IS", "VBAR", "CIRCUMFLEX", "AMPER", "LEFTSHIFT", 
    "PLUS", "MINUS", "STAR", "SLASH", "PERCENT", "DOUBLESLASH", "TILDE", 
    "DOUBLESTAR", "LBRACK", "RBRACK", "LCURLY", "RCURLY", "INT", "LONGINT", 
    "FLOAT", "COMPLEX", "SEMI", "DOLLAR", "BACKQUOTE", "GLOBAL", "LETTER", 
    "DIGIT", "EXPONENT", "TRIAPOS", "TRIQUOTE", "ESC", "CONTINUED_LINE", 
    "WS", "LEADING_WS", "COMMENT"
]




class PolicyParser(Parser):
    grammarFileName = "/Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g"
    antlr_version = version_str_to_tuple("3.1.3 Mar 17, 2009 19:23:44")
    antlr_version_str = "3.1.3 Mar 17, 2009 19:23:44"
    tokenNames = tokenNames

    def __init__(self, input, state=None, *args, **kwargs):
        if state is None:
            state = RecognizerSharedState()

        super(PolicyParser, self).__init__(input, state, *args, **kwargs)

        self.dfa34 = self.DFA34(
            self, 34,
            eot = self.DFA34_eot,
            eof = self.DFA34_eof,
            min = self.DFA34_min,
            max = self.DFA34_max,
            accept = self.DFA34_accept,
            special = self.DFA34_special,
            transition = self.DFA34_transition
            )

        self.dfa54 = self.DFA54(
            self, 54,
            eot = self.DFA54_eot,
            eof = self.DFA54_eof,
            min = self.DFA54_min,
            max = self.DFA54_max,
            accept = self.DFA54_accept,
            special = self.DFA54_special,
            transition = self.DFA54_transition
            )

        self.dfa59 = self.DFA59(
            self, 59,
            eot = self.DFA59_eot,
            eof = self.DFA59_eof,
            min = self.DFA59_min,
            max = self.DFA59_max,
            accept = self.DFA59_accept,
            special = self.DFA59_special,
            transition = self.DFA59_transition
            )

        self.dfa61 = self.DFA61(
            self, 61,
            eot = self.DFA61_eot,
            eof = self.DFA61_eof,
            min = self.DFA61_min,
            max = self.DFA61_max,
            accept = self.DFA61_accept,
            special = self.DFA61_special,
            transition = self.DFA61_transition
            )






                


        



    # $ANTLR start "file"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:61:1: file returns [object] : ( ( NEWLINE | statement )+ | EOF );
    def file(self, ):

        object = None

        statement1 = None


        object = File() 
        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:63:3: ( ( NEWLINE | statement )+ | EOF )
                alt2 = 2
                LA2_0 = self.input.LA(1)

                if ((NEWLINE <= LA2_0 <= LPAREN) or LA2_0 == NAME or LA2_0 == RULE or LA2_0 == STRING or LA2_0 == NOT or LA2_0 == OBJECTBINDING or (PLUS <= LA2_0 <= MINUS) or LA2_0 == TILDE or LA2_0 == LBRACK or LA2_0 == LCURLY or (INT <= LA2_0 <= COMPLEX)) :
                    alt2 = 1
                elif (LA2_0 == EOF) :
                    alt2 = 2
                else:
                    nvae = NoViableAltException("", 2, 0, self.input)

                    raise nvae

                if alt2 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:63:5: ( NEWLINE | statement )+
                    pass 
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:63:5: ( NEWLINE | statement )+
                    cnt1 = 0
                    while True: #loop1
                        alt1 = 3
                        LA1_0 = self.input.LA(1)

                        if (LA1_0 == NEWLINE) :
                            alt1 = 1
                        elif ((IMPORT <= LA1_0 <= LPAREN) or LA1_0 == NAME or LA1_0 == RULE or LA1_0 == STRING or LA1_0 == NOT or LA1_0 == OBJECTBINDING or (PLUS <= LA1_0 <= MINUS) or LA1_0 == TILDE or LA1_0 == LBRACK or LA1_0 == LCURLY or (INT <= LA1_0 <= COMPLEX)) :
                            alt1 = 2


                        if alt1 == 1:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:63:7: NEWLINE
                            pass 
                            self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_file78)


                        elif alt1 == 2:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:63:17: statement
                            pass 
                            self._state.following.append(self.FOLLOW_statement_in_file82)
                            statement1 = self.statement()

                            self._state.following.pop()
                            #action start
                            object.append_child( statement1 ) 
                            #action end


                        else:
                            if cnt1 >= 1:
                                break #loop1

                            eee = EarlyExitException(1, self.input)
                            raise eee

                        cnt1 += 1


                elif alt2 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:64:5: EOF
                    pass 
                    self.match(self.input, EOF, self.FOLLOW_EOF_in_file93)



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "file"


    # $ANTLR start "statement"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:67:1: statement returns [object] : ( importStmt | attributeStmt | ruleStmt );
    def statement(self, ):

        object = None

        importStmt2 = None

        attributeStmt3 = None

        ruleStmt4 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:68:3: ( importStmt | attributeStmt | ruleStmt )
                alt3 = 3
                LA3 = self.input.LA(1)
                if LA3 == IMPORT or LA3 == FROM:
                    alt3 = 1
                elif LA3 == LPAREN or LA3 == NAME or LA3 == STRING or LA3 == NOT or LA3 == OBJECTBINDING or LA3 == PLUS or LA3 == MINUS or LA3 == TILDE or LA3 == LBRACK or LA3 == LCURLY or LA3 == INT or LA3 == LONGINT or LA3 == FLOAT or LA3 == COMPLEX:
                    alt3 = 2
                elif LA3 == RULE:
                    alt3 = 3
                else:
                    nvae = NoViableAltException("", 3, 0, self.input)

                    raise nvae

                if alt3 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:68:5: importStmt
                    pass 
                    self._state.following.append(self.FOLLOW_importStmt_in_statement111)
                    importStmt2 = self.importStmt()

                    self._state.following.pop()
                    #action start
                    object = Statement( importStmt2, importStmt2.line, importStmt2.column ) 
                    #action end


                elif alt3 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:69:5: attributeStmt
                    pass 
                    self._state.following.append(self.FOLLOW_attributeStmt_in_statement120)
                    attributeStmt3 = self.attributeStmt()

                    self._state.following.pop()
                    #action start
                    object = Statement( attributeStmt3 ) 
                    #action end


                elif alt3 == 3:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:70:5: ruleStmt
                    pass 
                    self._state.following.append(self.FOLLOW_ruleStmt_in_statement129)
                    ruleStmt4 = self.ruleStmt()

                    self._state.following.pop()
                    #action start
                    object = Statement( ruleStmt4, ruleStmt4.line, ruleStmt4.column ) 
                    #action end



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "statement"


    # $ANTLR start "importStmt"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:73:1: importStmt returns [object] : ( importName | importFrom );
    def importStmt(self, ):

        object = None

        importName5 = None

        importFrom6 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:74:3: ( importName | importFrom )
                alt4 = 2
                LA4_0 = self.input.LA(1)

                if (LA4_0 == IMPORT) :
                    alt4 = 1
                elif (LA4_0 == FROM) :
                    alt4 = 2
                else:
                    nvae = NoViableAltException("", 4, 0, self.input)

                    raise nvae

                if alt4 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:74:5: importName
                    pass 
                    self._state.following.append(self.FOLLOW_importName_in_importStmt152)
                    importName5 = self.importName()

                    self._state.following.pop()
                    #action start
                    object = ImportStmt( children = importName5, line = importName5.line ) 
                    #action end


                elif alt4 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:75:5: importFrom
                    pass 
                    self._state.following.append(self.FOLLOW_importFrom_in_importStmt160)
                    importFrom6 = self.importFrom()

                    self._state.following.pop()
                    #action start
                    object = ImportStmt( children = importFrom6, line = importFrom6.line ) 
                    #action end



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "importStmt"


    # $ANTLR start "importName"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:78:1: importName returns [object] : IMPORT dottedAsNames NEWLINE ;
    def importName(self, ):

        object = None

        IMPORT7 = None
        dottedAsNames8 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:79:3: ( IMPORT dottedAsNames NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:79:5: IMPORT dottedAsNames NEWLINE
                pass 
                IMPORT7=self.match(self.input, IMPORT, self.FOLLOW_IMPORT_in_importName180)
                self._state.following.append(self.FOLLOW_dottedAsNames_in_importName182)
                dottedAsNames8 = self.dottedAsNames()

                self._state.following.pop()
                #action start
                object = ImportName( children = [IMPORT7.text, dottedAsNames8], line = IMPORT7.getLine() ) 
                #action end
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_importName186)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "importName"


    # $ANTLR start "importFrom"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:82:1: importFrom returns [object] : FROM dottedName IMPORT (importAsNames1= importAsNames | LPAREN importAsNames2= importAsNames RPAREN ) NEWLINE ;
    def importFrom(self, ):

        object = None

        FROM9 = None
        IMPORT11 = None
        LPAREN12 = None
        RPAREN13 = None
        importAsNames1 = None

        importAsNames2 = None

        dottedName10 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:83:3: ( FROM dottedName IMPORT (importAsNames1= importAsNames | LPAREN importAsNames2= importAsNames RPAREN ) NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:83:5: FROM dottedName IMPORT (importAsNames1= importAsNames | LPAREN importAsNames2= importAsNames RPAREN ) NEWLINE
                pass 
                FROM9=self.match(self.input, FROM, self.FOLLOW_FROM_in_importFrom204)
                #action start
                object = ImportFrom( children = FROM9.text, line = FROM9.getLine() ) 
                #action end
                self._state.following.append(self.FOLLOW_dottedName_in_importFrom208)
                dottedName10 = self.dottedName()

                self._state.following.pop()
                #action start
                object.append_child( dottedName10 ) 
                #action end
                IMPORT11=self.match(self.input, IMPORT, self.FOLLOW_IMPORT_in_importFrom212)
                #action start
                object.append_child( IMPORT11.text ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:84:7: (importAsNames1= importAsNames | LPAREN importAsNames2= importAsNames RPAREN )
                alt5 = 2
                LA5_0 = self.input.LA(1)

                if (LA5_0 == NAME) :
                    alt5 = 1
                elif (LA5_0 == LPAREN) :
                    alt5 = 2
                else:
                    nvae = NoViableAltException("", 5, 0, self.input)

                    raise nvae

                if alt5 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:84:9: importAsNames1= importAsNames
                    pass 
                    self._state.following.append(self.FOLLOW_importAsNames_in_importFrom226)
                    importAsNames1 = self.importAsNames()

                    self._state.following.pop()
                    #action start
                    object.append_child( importAsNames1 ) 
                    #action end


                elif alt5 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:85:9: LPAREN importAsNames2= importAsNames RPAREN
                    pass 
                    LPAREN12=self.match(self.input, LPAREN, self.FOLLOW_LPAREN_in_importFrom238)
                    self._state.following.append(self.FOLLOW_importAsNames_in_importFrom243)
                    importAsNames2 = self.importAsNames()

                    self._state.following.pop()
                    RPAREN13=self.match(self.input, RPAREN, self.FOLLOW_RPAREN_in_importFrom245)
                    #action start
                    object.append_children( [LPAREN12.text, importAsNames2, RPAREN13.text] ) 
                    #action end



                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_importFrom257)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "importFrom"


    # $ANTLR start "importAsNames"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:89:1: importAsNames returns [object] : importAsName1= importAsName ( COMMA importAsName2= importAsName )* ( COMMA )? ;
    def importAsNames(self, ):

        object = None

        importAsName1 = None

        importAsName2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:90:3: (importAsName1= importAsName ( COMMA importAsName2= importAsName )* ( COMMA )? )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:90:5: importAsName1= importAsName ( COMMA importAsName2= importAsName )* ( COMMA )?
                pass 
                self._state.following.append(self.FOLLOW_importAsName_in_importAsNames276)
                importAsName1 = self.importAsName()

                self._state.following.pop()
                #action start
                object=ImportAsNames( importAsName1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:91:7: ( COMMA importAsName2= importAsName )*
                while True: #loop6
                    alt6 = 2
                    LA6_0 = self.input.LA(1)

                    if (LA6_0 == COMMA) :
                        LA6_1 = self.input.LA(2)

                        if (LA6_1 == NAME) :
                            alt6 = 1




                    if alt6 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:91:9: COMMA importAsName2= importAsName
                        pass 
                        self.match(self.input, COMMA, self.FOLLOW_COMMA_in_importAsNames288)
                        self._state.following.append(self.FOLLOW_importAsName_in_importAsNames292)
                        importAsName2 = self.importAsName()

                        self._state.following.pop()
                        #action start
                        object.append_children( [",", importAsName2] ) 
                        #action end


                    else:
                        break #loop6
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:91:105: ( COMMA )?
                alt7 = 2
                LA7_0 = self.input.LA(1)

                if (LA7_0 == COMMA) :
                    alt7 = 1
                if alt7 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:91:107: COMMA
                    pass 
                    self.match(self.input, COMMA, self.FOLLOW_COMMA_in_importAsNames301)
                    #action start
                    object.append_child( "," ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "importAsNames"


    # $ANTLR start "importAsName"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:94:1: importAsName returns [object] : name1= NAME ( AS name2= NAME )? ;
    def importAsName(self, ):

        object = None

        name1 = None
        name2 = None
        AS14 = None

        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:95:3: (name1= NAME ( AS name2= NAME )? )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:95:5: name1= NAME ( AS name2= NAME )?
                pass 
                name1=self.match(self.input, NAME, self.FOLLOW_NAME_in_importAsName325)
                #action start
                object=ImportAsName( name1.text ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:95:56: ( AS name2= NAME )?
                alt8 = 2
                LA8_0 = self.input.LA(1)

                if (LA8_0 == AS) :
                    alt8 = 1
                if alt8 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:95:58: AS name2= NAME
                    pass 
                    AS14=self.match(self.input, AS, self.FOLLOW_AS_in_importAsName331)
                    name2=self.match(self.input, NAME, self.FOLLOW_NAME_in_importAsName335)
                    #action start
                    object.append_children( [AS14.text, name2.text] ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "importAsName"


    # $ANTLR start "dottedAsNames"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:98:1: dottedAsNames returns [object] : dottedAsName1= dottedAsName ( COMMA dottedAsName2= dottedAsName )* ;
    def dottedAsNames(self, ):

        object = None

        COMMA15 = None
        dottedAsName1 = None

        dottedAsName2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:99:3: (dottedAsName1= dottedAsName ( COMMA dottedAsName2= dottedAsName )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:99:5: dottedAsName1= dottedAsName ( COMMA dottedAsName2= dottedAsName )*
                pass 
                self._state.following.append(self.FOLLOW_dottedAsName_in_dottedAsNames359)
                dottedAsName1 = self.dottedAsName()

                self._state.following.pop()
                #action start
                object = DottedAsNames( dottedAsName1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:100:7: ( COMMA dottedAsName2= dottedAsName )*
                while True: #loop9
                    alt9 = 2
                    LA9_0 = self.input.LA(1)

                    if (LA9_0 == COMMA) :
                        alt9 = 1


                    if alt9 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:100:9: COMMA dottedAsName2= dottedAsName
                        pass 
                        COMMA15=self.match(self.input, COMMA, self.FOLLOW_COMMA_in_dottedAsNames371)
                        self._state.following.append(self.FOLLOW_dottedAsName_in_dottedAsNames375)
                        dottedAsName2 = self.dottedAsName()

                        self._state.following.pop()
                        #action start
                        object.append_children( [COMMA15.text, dottedAsName2] ) 
                        #action end


                    else:
                        break #loop9




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "dottedAsNames"


    # $ANTLR start "dottedAsName"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:103:1: dottedAsName returns [object] : dottedName ( AS NAME )? ;
    def dottedAsName(self, ):

        object = None

        AS17 = None
        NAME18 = None
        dottedName16 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:104:3: ( dottedName ( AS NAME )? )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:104:5: dottedName ( AS NAME )?
                pass 
                self._state.following.append(self.FOLLOW_dottedName_in_dottedAsName397)
                dottedName16 = self.dottedName()

                self._state.following.pop()
                #action start
                object = DottedAsName( dottedName16 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:104:65: ( AS NAME )?
                alt10 = 2
                LA10_0 = self.input.LA(1)

                if (LA10_0 == AS) :
                    alt10 = 1
                if alt10 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:104:67: AS NAME
                    pass 
                    AS17=self.match(self.input, AS, self.FOLLOW_AS_in_dottedAsName403)
                    NAME18=self.match(self.input, NAME, self.FOLLOW_NAME_in_dottedAsName405)
                    #action start
                    object.append_children( [AS17.text, NAME18.text] ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "dottedAsName"


    # $ANTLR start "dottedName"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:107:1: dottedName returns [object] : name1= NAME ( DOT name2= NAME )* ;
    def dottedName(self, ):

        object = None

        name1 = None
        name2 = None
        DOT19 = None

        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:108:3: (name1= NAME ( DOT name2= NAME )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:108:5: name1= NAME ( DOT name2= NAME )*
                pass 
                name1=self.match(self.input, NAME, self.FOLLOW_NAME_in_dottedName430)
                #action start
                object = DottedName( name1.text ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:109:7: ( DOT name2= NAME )*
                while True: #loop11
                    alt11 = 2
                    LA11_0 = self.input.LA(1)

                    if (LA11_0 == DOT) :
                        alt11 = 1


                    if alt11 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:109:9: DOT name2= NAME
                        pass 
                        DOT19=self.match(self.input, DOT, self.FOLLOW_DOT_in_dottedName442)
                        name2=self.match(self.input, NAME, self.FOLLOW_NAME_in_dottedName446)
                        #action start
                        object.append_children( [DOT19.text, name2.text] ) 
                        #action end


                    else:
                        break #loop11




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "dottedName"


    # $ANTLR start "attributeStmt"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:112:1: attributeStmt returns [object] : expressionStmt ;
    def attributeStmt(self, ):

        object = None

        expressionStmt20 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:113:3: ( expressionStmt )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:113:5: expressionStmt
                pass 
                self._state.following.append(self.FOLLOW_expressionStmt_in_attributeStmt469)
                expressionStmt20 = self.expressionStmt()

                self._state.following.pop()
                #action start
                object = AttributeStmt( expressionStmt20 ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "attributeStmt"


    # $ANTLR start "ruleStmt"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:116:1: ruleStmt returns [object] : RULE id COLON NEWLINE INDENT ( ruleAttribute )* ( when )? then DEDENT ;
    def ruleStmt(self, ):

        object = None

        RULE21 = None
        COLON23 = None
        id22 = None

        ruleAttribute24 = None

        when25 = None

        then26 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:117:3: ( RULE id COLON NEWLINE INDENT ( ruleAttribute )* ( when )? then DEDENT )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:117:5: RULE id COLON NEWLINE INDENT ( ruleAttribute )* ( when )? then DEDENT
                pass 
                RULE21=self.match(self.input, RULE, self.FOLLOW_RULE_in_ruleStmt489)
                self._state.following.append(self.FOLLOW_id_in_ruleStmt491)
                id22 = self.id()

                self._state.following.pop()
                COLON23=self.match(self.input, COLON, self.FOLLOW_COLON_in_ruleStmt493)
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_ruleStmt495)
                #action start
                object = RuleStmt( [ RULE21.text, id22, COLON23.text ], RULE21.getLine(), RULE21.getCharPositionInLine() ) 
                #action end
                self.match(self.input, INDENT, self.FOLLOW_INDENT_in_ruleStmt505)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:118:14: ( ruleAttribute )*
                while True: #loop12
                    alt12 = 2
                    LA12_0 = self.input.LA(1)

                    if (LA12_0 == AGENDAGROUP) :
                        alt12 = 1


                    if alt12 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:118:16: ruleAttribute
                        pass 
                        self._state.following.append(self.FOLLOW_ruleAttribute_in_ruleStmt509)
                        ruleAttribute24 = self.ruleAttribute()

                        self._state.following.pop()
                        #action start
                        object.append_child( ruleAttribute24 ) 
                        #action end


                    else:
                        break #loop12
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:119:14: ( when )?
                alt13 = 2
                LA13_0 = self.input.LA(1)

                if (LA13_0 == WHEN) :
                    alt13 = 1
                if alt13 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:119:16: when
                    pass 
                    self._state.following.append(self.FOLLOW_when_in_ruleStmt531)
                    when25 = self.when()

                    self._state.following.pop()
                    #action start
                    object.append_child( when25 ) 
                    #action end



                self._state.following.append(self.FOLLOW_then_in_ruleStmt551)
                then26 = self.then()

                self._state.following.pop()
                #action start
                object.append_child( then26 ) 
                #action end
                self.match(self.input, DEDENT, self.FOLLOW_DEDENT_in_ruleStmt556)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "ruleStmt"


    # $ANTLR start "id"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:123:1: id returns [object] : ( NAME | STRING );
    def id(self, ):

        object = None

        NAME27 = None
        STRING28 = None

        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:124:3: ( NAME | STRING )
                alt14 = 2
                LA14_0 = self.input.LA(1)

                if (LA14_0 == NAME) :
                    alt14 = 1
                elif (LA14_0 == STRING) :
                    alt14 = 2
                else:
                    nvae = NoViableAltException("", 14, 0, self.input)

                    raise nvae

                if alt14 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:124:5: NAME
                    pass 
                    NAME27=self.match(self.input, NAME, self.FOLLOW_NAME_in_id574)
                    #action start
                    object = Id( NAME27.text ) 
                    #action end


                elif alt14 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:125:5: STRING
                    pass 
                    STRING28=self.match(self.input, STRING, self.FOLLOW_STRING_in_id585)
                    #action start
                    object = Id( STRING28.text ) 
                    #action end



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "id"


    # $ANTLR start "ruleAttribute"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:128:1: ruleAttribute returns [object] : agendaGroup ;
    def ruleAttribute(self, ):

        object = None

        agendaGroup29 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:129:3: ( agendaGroup )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:129:5: agendaGroup
                pass 
                self._state.following.append(self.FOLLOW_agendaGroup_in_ruleAttribute606)
                agendaGroup29 = self.agendaGroup()

                self._state.following.pop()
                #action start
                object = RuleAttribute( agendaGroup29, agendaGroup29.line, agendaGroup29.column ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "ruleAttribute"


    # $ANTLR start "agendaGroup"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:132:1: agendaGroup returns [object] : AGENDAGROUP id NEWLINE ;
    def agendaGroup(self, ):

        object = None

        AGENDAGROUP30 = None
        id31 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:133:3: ( AGENDAGROUP id NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:133:5: AGENDAGROUP id NEWLINE
                pass 
                AGENDAGROUP30=self.match(self.input, AGENDAGROUP, self.FOLLOW_AGENDAGROUP_in_agendaGroup626)
                self._state.following.append(self.FOLLOW_id_in_agendaGroup628)
                id31 = self.id()

                self._state.following.pop()
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_agendaGroup630)
                #action start
                object = AgendaGroup( [ AGENDAGROUP30.text, id31 ], AGENDAGROUP30.getLine(), AGENDAGROUP30.getCharPositionInLine() ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "agendaGroup"


    # $ANTLR start "when"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:136:1: when returns [object] : WHEN COLON NEWLINE INDENT ( ruleCondition )? DEDENT ;
    def when(self, ):

        object = None

        WHEN32 = None
        COLON33 = None
        ruleCondition34 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:137:3: ( WHEN COLON NEWLINE INDENT ( ruleCondition )? DEDENT )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:137:5: WHEN COLON NEWLINE INDENT ( ruleCondition )? DEDENT
                pass 
                WHEN32=self.match(self.input, WHEN, self.FOLLOW_WHEN_in_when650)
                COLON33=self.match(self.input, COLON, self.FOLLOW_COLON_in_when652)
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_when654)
                #action start
                object = When( [WHEN32.text, COLON33.text], WHEN32.getLine(), WHEN32.getCharPositionInLine() ) 
                #action end
                self.match(self.input, INDENT, self.FOLLOW_INDENT_in_when664)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:138:14: ( ruleCondition )?
                alt15 = 2
                LA15_0 = self.input.LA(1)

                if (LA15_0 == NAME or (NOT <= LA15_0 <= OBJECTBINDING)) :
                    alt15 = 1
                if alt15 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:138:16: ruleCondition
                    pass 
                    self._state.following.append(self.FOLLOW_ruleCondition_in_when668)
                    ruleCondition34 = self.ruleCondition()

                    self._state.following.pop()
                    #action start
                    object.append_child( ruleCondition34 ) 
                    #action end



                self.match(self.input, DEDENT, self.FOLLOW_DEDENT_in_when675)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "when"


    # $ANTLR start "then"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:141:1: then returns [object] : THEN COLON NEWLINE INDENT ( action )+ DEDENT ;
    def then(self, ):

        object = None

        THEN35 = None
        COLON36 = None
        action37 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:142:3: ( THEN COLON NEWLINE INDENT ( action )+ DEDENT )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:142:5: THEN COLON NEWLINE INDENT ( action )+ DEDENT
                pass 
                THEN35=self.match(self.input, THEN, self.FOLLOW_THEN_in_then693)
                COLON36=self.match(self.input, COLON, self.FOLLOW_COLON_in_then695)
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_then697)
                #action start
                object = Then( [THEN35.text, COLON36.text], THEN35.getLine(), THEN35.getCharPositionInLine() ) 
                #action end
                self.match(self.input, INDENT, self.FOLLOW_INDENT_in_then707)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:143:14: ( action )+
                cnt16 = 0
                while True: #loop16
                    alt16 = 2
                    LA16_0 = self.input.LA(1)

                    if (LA16_0 == LPAREN or LA16_0 == NAME or LA16_0 == STRING or LA16_0 == NOT or LA16_0 == OBJECTBINDING or (ATTRIBUTE <= LA16_0 <= PRINT) or (FORGET <= LA16_0 <= HALT) or (PLUS <= LA16_0 <= MINUS) or LA16_0 == TILDE or LA16_0 == LBRACK or LA16_0 == LCURLY or (INT <= LA16_0 <= COMPLEX)) :
                        alt16 = 1


                    if alt16 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:143:16: action
                        pass 
                        self._state.following.append(self.FOLLOW_action_in_then711)
                        action37 = self.action()

                        self._state.following.pop()
                        #action start
                        object.append_child( action37 ) 
                        #action end


                    else:
                        if cnt16 >= 1:
                            break #loop16

                        eee = EarlyExitException(16, self.input)
                        raise eee

                    cnt16 += 1
                self.match(self.input, DEDENT, self.FOLLOW_DEDENT_in_then718)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "then"


    # $ANTLR start "ruleCondition"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:146:1: ruleCondition returns [object] : notCondition NEWLINE ;
    def ruleCondition(self, ):

        object = None

        notCondition38 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:147:3: ( notCondition NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:147:5: notCondition NEWLINE
                pass 
                self._state.following.append(self.FOLLOW_notCondition_in_ruleCondition736)
                notCondition38 = self.notCondition()

                self._state.following.pop()
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_ruleCondition738)
                #action start
                object = RuleCondition(notCondition38) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "ruleCondition"


    # $ANTLR start "notCondition"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:150:1: notCondition returns [object] : ( NOT )* condition ;
    def notCondition(self, ):

        object = None

        NOT39 = None
        condition40 = None


        object = NotCondition() 
        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:152:3: ( ( NOT )* condition )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:152:5: ( NOT )* condition
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:152:5: ( NOT )*
                while True: #loop17
                    alt17 = 2
                    LA17_0 = self.input.LA(1)

                    if (LA17_0 == NOT) :
                        alt17 = 1


                    if alt17 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:152:7: NOT
                        pass 
                        NOT39=self.match(self.input, NOT, self.FOLLOW_NOT_in_notCondition766)
                        #action start
                        object.append_child( NOT39.text ) 
                        #action end


                    else:
                        break #loop17
                self._state.following.append(self.FOLLOW_condition_in_notCondition773)
                condition40 = self.condition()

                self._state.following.pop()
                #action start
                object.append_child( condition40 ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "notCondition"


    # $ANTLR start "condition"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:155:1: condition returns [object] : ( EXISTS )? classConstraint ;
    def condition(self, ):

        object = None

        EXISTS41 = None
        classConstraint42 = None


        object = Condition() 
        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:157:3: ( ( EXISTS )? classConstraint )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:157:5: ( EXISTS )? classConstraint
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:157:5: ( EXISTS )?
                alt18 = 2
                LA18_0 = self.input.LA(1)

                if (LA18_0 == EXISTS) :
                    alt18 = 1
                if alt18 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:157:7: EXISTS
                    pass 
                    EXISTS41=self.match(self.input, EXISTS, self.FOLLOW_EXISTS_in_condition801)
                    #action start
                    object.append_child( EXISTS41.text ) 
                    #action end



                self._state.following.append(self.FOLLOW_classConstraint_in_condition808)
                classConstraint42 = self.classConstraint()

                self._state.following.pop()
                #action start
                object.append_child( classConstraint42 ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "condition"


    # $ANTLR start "classConstraint"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:160:1: classConstraint returns [object] : ( OBJECTBINDING ASSIGNEQUAL )? NAME LPAREN ( constraint )? RPAREN ;
    def classConstraint(self, ):

        object = None

        OBJECTBINDING43 = None
        ASSIGNEQUAL44 = None
        NAME45 = None
        LPAREN46 = None
        RPAREN48 = None
        constraint47 = None


        object = ClassConstraint() 
        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:162:3: ( ( OBJECTBINDING ASSIGNEQUAL )? NAME LPAREN ( constraint )? RPAREN )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:162:5: ( OBJECTBINDING ASSIGNEQUAL )? NAME LPAREN ( constraint )? RPAREN
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:162:5: ( OBJECTBINDING ASSIGNEQUAL )?
                alt19 = 2
                LA19_0 = self.input.LA(1)

                if (LA19_0 == OBJECTBINDING) :
                    alt19 = 1
                if alt19 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:162:7: OBJECTBINDING ASSIGNEQUAL
                    pass 
                    OBJECTBINDING43=self.match(self.input, OBJECTBINDING, self.FOLLOW_OBJECTBINDING_in_classConstraint836)
                    ASSIGNEQUAL44=self.match(self.input, ASSIGNEQUAL, self.FOLLOW_ASSIGNEQUAL_in_classConstraint838)
                    #action start
                    object.append_children( [ OBJECTBINDING43.text, ASSIGNEQUAL44.text] ) 
                    #action end



                NAME45=self.match(self.input, NAME, self.FOLLOW_NAME_in_classConstraint851)
                LPAREN46=self.match(self.input, LPAREN, self.FOLLOW_LPAREN_in_classConstraint853)
                #action start
                object.append_children( [NAME45.text, LPAREN46.text] ); 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:163:78: ( constraint )?
                alt20 = 2
                LA20_0 = self.input.LA(1)

                if (LA20_0 == LPAREN or LA20_0 == NAME or LA20_0 == STRING or LA20_0 == NOT or LA20_0 == OBJECTBINDING or (PLUS <= LA20_0 <= MINUS) or LA20_0 == TILDE or LA20_0 == LBRACK or LA20_0 == LCURLY or (INT <= LA20_0 <= COMPLEX)) :
                    alt20 = 1
                if alt20 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:163:80: constraint
                    pass 
                    self._state.following.append(self.FOLLOW_constraint_in_classConstraint859)
                    constraint47 = self.constraint()

                    self._state.following.pop()
                    #action start
                    object.append_child( constraint47 ) 
                    #action end



                RPAREN48=self.match(self.input, RPAREN, self.FOLLOW_RPAREN_in_classConstraint866)
                #action start
                object.append_child( RPAREN48.text ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "classConstraint"


    # $ANTLR start "action"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:166:1: action returns [object] : ( simpleStmt | attributeAction | learnAction | forgetAction | modifyAction | haltAction );
    def action(self, ):

        object = None

        simpleStmt49 = None

        attributeAction50 = None

        learnAction51 = None

        forgetAction52 = None

        modifyAction53 = None

        haltAction54 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:167:3: ( simpleStmt | attributeAction | learnAction | forgetAction | modifyAction | haltAction )
                alt21 = 6
                LA21 = self.input.LA(1)
                if LA21 == LPAREN or LA21 == NAME or LA21 == STRING or LA21 == NOT or LA21 == OBJECTBINDING or LA21 == PRINT or LA21 == PLUS or LA21 == MINUS or LA21 == TILDE or LA21 == LBRACK or LA21 == LCURLY or LA21 == INT or LA21 == LONGINT or LA21 == FLOAT or LA21 == COMPLEX:
                    alt21 = 1
                elif LA21 == ATTRIBUTE:
                    alt21 = 2
                elif LA21 == LEARN or LA21 == INSERT:
                    alt21 = 3
                elif LA21 == FORGET or LA21 == DELETE:
                    alt21 = 4
                elif LA21 == MODIFY:
                    alt21 = 5
                elif LA21 == HALT:
                    alt21 = 6
                else:
                    nvae = NoViableAltException("", 21, 0, self.input)

                    raise nvae

                if alt21 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:167:5: simpleStmt
                    pass 
                    self._state.following.append(self.FOLLOW_simpleStmt_in_action886)
                    simpleStmt49 = self.simpleStmt()

                    self._state.following.pop()
                    #action start
                    object = Action( simpleStmt49, simpleStmt49.line, simpleStmt49.column ) 
                    #action end


                elif alt21 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:168:5: attributeAction
                    pass 
                    self._state.following.append(self.FOLLOW_attributeAction_in_action900)
                    attributeAction50 = self.attributeAction()

                    self._state.following.pop()
                    #action start
                    object = Action( attributeAction50, attributeAction50.line, attributeAction50.column ) 
                    #action end


                elif alt21 == 3:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:169:5: learnAction
                    pass 
                    self._state.following.append(self.FOLLOW_learnAction_in_action909)
                    learnAction51 = self.learnAction()

                    self._state.following.pop()
                    #action start
                    object = Action( learnAction51, learnAction51.line, learnAction51.column ) 
                    #action end


                elif alt21 == 4:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:170:5: forgetAction
                    pass 
                    self._state.following.append(self.FOLLOW_forgetAction_in_action921)
                    forgetAction52 = self.forgetAction()

                    self._state.following.pop()
                    #action start
                    object = Action( forgetAction52, forgetAction52.line, forgetAction52.column ) 
                    #action end


                elif alt21 == 5:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:171:5: modifyAction
                    pass 
                    self._state.following.append(self.FOLLOW_modifyAction_in_action933)
                    modifyAction53 = self.modifyAction()

                    self._state.following.pop()
                    #action start
                    object = Action( modifyAction53, modifyAction53.line, modifyAction53.column ) 
                    #action end


                elif alt21 == 6:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:172:5: haltAction
                    pass 
                    self._state.following.append(self.FOLLOW_haltAction_in_action945)
                    haltAction54 = self.haltAction()

                    self._state.following.pop()
                    #action start
                    object = Action( haltAction54, haltAction54.line, haltAction54.column ) 
                    #action end



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "action"


    # $ANTLR start "simpleStmt"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:175:1: simpleStmt returns [object] : ( expressionStmt | printStmt );
    def simpleStmt(self, ):

        object = None

        expressionStmt55 = None

        printStmt56 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:176:3: ( expressionStmt | printStmt )
                alt22 = 2
                LA22_0 = self.input.LA(1)

                if (LA22_0 == LPAREN or LA22_0 == NAME or LA22_0 == STRING or LA22_0 == NOT or LA22_0 == OBJECTBINDING or (PLUS <= LA22_0 <= MINUS) or LA22_0 == TILDE or LA22_0 == LBRACK or LA22_0 == LCURLY or (INT <= LA22_0 <= COMPLEX)) :
                    alt22 = 1
                elif (LA22_0 == PRINT) :
                    alt22 = 2
                else:
                    nvae = NoViableAltException("", 22, 0, self.input)

                    raise nvae

                if alt22 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:176:5: expressionStmt
                    pass 
                    self._state.following.append(self.FOLLOW_expressionStmt_in_simpleStmt971)
                    expressionStmt55 = self.expressionStmt()

                    self._state.following.pop()
                    #action start
                    object = SimpleStmt( expressionStmt55 ) 
                    #action end


                elif alt22 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:177:5: printStmt
                    pass 
                    self._state.following.append(self.FOLLOW_printStmt_in_simpleStmt985)
                    printStmt56 = self.printStmt()

                    self._state.following.pop()
                    #action start
                    object = SimpleStmt( printStmt56, printStmt56.line, printStmt56.column ) 
                    #action end



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "simpleStmt"


    # $ANTLR start "attributeAction"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:180:1: attributeAction returns [object] : ATTRIBUTE expressionStmt ;
    def attributeAction(self, ):

        object = None

        ATTRIBUTE57 = None
        expressionStmt58 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:181:3: ( ATTRIBUTE expressionStmt )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:181:5: ATTRIBUTE expressionStmt
                pass 
                ATTRIBUTE57=self.match(self.input, ATTRIBUTE, self.FOLLOW_ATTRIBUTE_in_attributeAction1016)
                self._state.following.append(self.FOLLOW_expressionStmt_in_attributeAction1018)
                expressionStmt58 = self.expressionStmt()

                self._state.following.pop()
                #action start
                object = AttributeAction( [ ATTRIBUTE57.text, expressionStmt58 ] , ATTRIBUTE57.getLine(), ATTRIBUTE57.getCharPositionInLine() ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "attributeAction"


    # $ANTLR start "printStmt"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:184:1: printStmt returns [object] : PRINT (comparisonList1= comparisonList | RIGHTSHIFT comparisonList2= comparisonList )? NEWLINE ;
    def printStmt(self, ):

        object = None

        PRINT59 = None
        RIGHTSHIFT60 = None
        comparisonList1 = None

        comparisonList2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:185:3: ( PRINT (comparisonList1= comparisonList | RIGHTSHIFT comparisonList2= comparisonList )? NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:185:5: PRINT (comparisonList1= comparisonList | RIGHTSHIFT comparisonList2= comparisonList )? NEWLINE
                pass 
                PRINT59=self.match(self.input, PRINT, self.FOLLOW_PRINT_in_printStmt1038)
                #action start
                object = PrintStmt( PRINT59.text, PRINT59.getLine(), PRINT59.getCharPositionInLine() ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:186:7: (comparisonList1= comparisonList | RIGHTSHIFT comparisonList2= comparisonList )?
                alt23 = 3
                LA23_0 = self.input.LA(1)

                if (LA23_0 == LPAREN or LA23_0 == NAME or LA23_0 == STRING or LA23_0 == NOT or LA23_0 == OBJECTBINDING or (PLUS <= LA23_0 <= MINUS) or LA23_0 == TILDE or LA23_0 == LBRACK or LA23_0 == LCURLY or (INT <= LA23_0 <= COMPLEX)) :
                    alt23 = 1
                elif (LA23_0 == RIGHTSHIFT) :
                    alt23 = 2
                if alt23 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:186:9: comparisonList1= comparisonList
                    pass 
                    self._state.following.append(self.FOLLOW_comparisonList_in_printStmt1052)
                    comparisonList1 = self.comparisonList()

                    self._state.following.pop()
                    #action start
                    object.append_child( comparisonList1 ) 
                    #action end


                elif alt23 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:187:9: RIGHTSHIFT comparisonList2= comparisonList
                    pass 
                    RIGHTSHIFT60=self.match(self.input, RIGHTSHIFT, self.FOLLOW_RIGHTSHIFT_in_printStmt1064)
                    self._state.following.append(self.FOLLOW_comparisonList_in_printStmt1068)
                    comparisonList2 = self.comparisonList()

                    self._state.following.pop()
                    #action start
                    object.append_children( [RIGHTSHIFT60.text, comparisonList2] ) 
                    #action end



                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_printStmt1075)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "printStmt"


    # $ANTLR start "forgetAction"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:190:1: forgetAction returns [object] : ( FORGET | DELETE ) OBJECTBINDING NEWLINE ;
    def forgetAction(self, ):

        object = None

        FORGET61 = None
        DELETE62 = None
        OBJECTBINDING63 = None

        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:191:3: ( ( FORGET | DELETE ) OBJECTBINDING NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:191:5: ( FORGET | DELETE ) OBJECTBINDING NEWLINE
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:191:5: ( FORGET | DELETE )
                alt24 = 2
                LA24_0 = self.input.LA(1)

                if (LA24_0 == FORGET) :
                    alt24 = 1
                elif (LA24_0 == DELETE) :
                    alt24 = 2
                else:
                    nvae = NoViableAltException("", 24, 0, self.input)

                    raise nvae

                if alt24 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:191:7: FORGET
                    pass 
                    FORGET61=self.match(self.input, FORGET, self.FOLLOW_FORGET_in_forgetAction1095)
                    #action start
                    object = ForgetAction( FORGET61.text, FORGET61.getLine(), FORGET61.getCharPositionInLine() ) 
                    #action end


                elif alt24 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:192:9: DELETE
                    pass 
                    DELETE62=self.match(self.input, DELETE, self.FOLLOW_DELETE_in_forgetAction1107)
                    #action start
                    object = ForgetAction( DELETE62.text, DELETE62.getLine(), DELETE62.getCharPositionInLine() ) 
                    #action end



                OBJECTBINDING63=self.match(self.input, OBJECTBINDING, self.FOLLOW_OBJECTBINDING_in_forgetAction1120)
                #action start
                object.append_child( OBJECTBINDING63.text ) 
                #action end
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_forgetAction1124)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "forgetAction"


    # $ANTLR start "learnAction"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:196:1: learnAction returns [object] : ( LEARN | INSERT ) NAME LPAREN ( argumentList )? RPAREN NEWLINE ;
    def learnAction(self, ):

        object = None

        LEARN64 = None
        INSERT65 = None
        NAME66 = None
        LPAREN67 = None
        RPAREN69 = None
        argumentList68 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:197:3: ( ( LEARN | INSERT ) NAME LPAREN ( argumentList )? RPAREN NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:197:5: ( LEARN | INSERT ) NAME LPAREN ( argumentList )? RPAREN NEWLINE
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:197:5: ( LEARN | INSERT )
                alt25 = 2
                LA25_0 = self.input.LA(1)

                if (LA25_0 == LEARN) :
                    alt25 = 1
                elif (LA25_0 == INSERT) :
                    alt25 = 2
                else:
                    nvae = NoViableAltException("", 25, 0, self.input)

                    raise nvae

                if alt25 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:197:7: LEARN
                    pass 
                    LEARN64=self.match(self.input, LEARN, self.FOLLOW_LEARN_in_learnAction1144)
                    #action start
                    object = LearnAction( LEARN64.text, LEARN64.getLine(), LEARN64.getCharPositionInLine() ) 
                    #action end


                elif alt25 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:198:9: INSERT
                    pass 
                    INSERT65=self.match(self.input, INSERT, self.FOLLOW_INSERT_in_learnAction1156)
                    #action start
                    object = LearnAction( INSERT65.text, INSERT65.getLine(), INSERT65.getCharPositionInLine() ) 
                    #action end



                NAME66=self.match(self.input, NAME, self.FOLLOW_NAME_in_learnAction1171)
                LPAREN67=self.match(self.input, LPAREN, self.FOLLOW_LPAREN_in_learnAction1173)
                #action start
                object.append_children( [NAME66.text, LPAREN67.text] ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:200:9: ( argumentList )?
                alt26 = 2
                LA26_0 = self.input.LA(1)

                if (LA26_0 == LPAREN or LA26_0 == NAME or LA26_0 == STRING or LA26_0 == NOT or LA26_0 == OBJECTBINDING or (PLUS <= LA26_0 <= MINUS) or LA26_0 == TILDE or LA26_0 == LBRACK or LA26_0 == LCURLY or (INT <= LA26_0 <= COMPLEX)) :
                    alt26 = 1
                if alt26 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:200:11: argumentList
                    pass 
                    self._state.following.append(self.FOLLOW_argumentList_in_learnAction1187)
                    argumentList68 = self.argumentList()

                    self._state.following.pop()
                    #action start
                    object.append_child( argumentList68 ) 
                    #action end



                RPAREN69=self.match(self.input, RPAREN, self.FOLLOW_RPAREN_in_learnAction1194)
                #action start
                object.append_child( RPAREN69.text ) 
                #action end
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_learnAction1198)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "learnAction"


    # $ANTLR start "modifyAction"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:203:1: modifyAction returns [object] : MODIFY OBJECTBINDING COLON NEWLINE INDENT ( propertyAssignment )+ DEDENT ;
    def modifyAction(self, ):

        object = None

        MODIFY70 = None
        OBJECTBINDING71 = None
        COLON72 = None
        propertyAssignment73 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:204:3: ( MODIFY OBJECTBINDING COLON NEWLINE INDENT ( propertyAssignment )+ DEDENT )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:204:5: MODIFY OBJECTBINDING COLON NEWLINE INDENT ( propertyAssignment )+ DEDENT
                pass 
                MODIFY70=self.match(self.input, MODIFY, self.FOLLOW_MODIFY_in_modifyAction1216)
                OBJECTBINDING71=self.match(self.input, OBJECTBINDING, self.FOLLOW_OBJECTBINDING_in_modifyAction1218)
                COLON72=self.match(self.input, COLON, self.FOLLOW_COLON_in_modifyAction1220)
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_modifyAction1222)
                #action start
                object = ModifyAction( [MODIFY70.text, OBJECTBINDING71.text, COLON72.text], MODIFY70.getLine(), MODIFY70.getCharPositionInLine() ) 
                #action end
                self.match(self.input, INDENT, self.FOLLOW_INDENT_in_modifyAction1232)
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:205:14: ( propertyAssignment )+
                cnt27 = 0
                while True: #loop27
                    alt27 = 2
                    LA27_0 = self.input.LA(1)

                    if (LA27_0 == NAME) :
                        alt27 = 1


                    if alt27 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:205:16: propertyAssignment
                        pass 
                        self._state.following.append(self.FOLLOW_propertyAssignment_in_modifyAction1236)
                        propertyAssignment73 = self.propertyAssignment()

                        self._state.following.pop()
                        #action start
                        object.append_child( propertyAssignment73 ) 
                        #action end


                    else:
                        if cnt27 >= 1:
                            break #loop27

                        eee = EarlyExitException(27, self.input)
                        raise eee

                    cnt27 += 1
                self.match(self.input, DEDENT, self.FOLLOW_DEDENT_in_modifyAction1243)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "modifyAction"


    # $ANTLR start "haltAction"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:208:1: haltAction returns [object] : HALT NEWLINE ;
    def haltAction(self, ):

        object = None

        HALT74 = None

        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:209:3: ( HALT NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:209:5: HALT NEWLINE
                pass 
                HALT74=self.match(self.input, HALT, self.FOLLOW_HALT_in_haltAction1261)
                #action start
                object = HaltAction( HALT74.text, HALT74.getLine(), HALT74.getCharPositionInLine() ) 
                #action end
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_haltAction1265)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "haltAction"


    # $ANTLR start "propertyAssignment"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:212:1: propertyAssignment returns [object] : NAME assignment constraint NEWLINE ;
    def propertyAssignment(self, ):

        object = None

        NAME75 = None
        assignment76 = None

        constraint77 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:213:3: ( NAME assignment constraint NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:213:5: NAME assignment constraint NEWLINE
                pass 
                NAME75=self.match(self.input, NAME, self.FOLLOW_NAME_in_propertyAssignment1283)
                self._state.following.append(self.FOLLOW_assignment_in_propertyAssignment1285)
                assignment76 = self.assignment()

                self._state.following.pop()
                self._state.following.append(self.FOLLOW_constraint_in_propertyAssignment1287)
                constraint77 = self.constraint()

                self._state.following.pop()
                #action start
                object = PropertyAssignment( [NAME75.text, assignment76, constraint77] ) 
                #action end
                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_propertyAssignment1291)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "propertyAssignment"


    # $ANTLR start "expressionStmt"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:216:1: expressionStmt returns [object] : comparisonList1= comparisonList ( assignment comparisonList2= comparisonList )? NEWLINE ;
    def expressionStmt(self, ):

        object = None

        comparisonList1 = None

        comparisonList2 = None

        assignment78 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:217:3: (comparisonList1= comparisonList ( assignment comparisonList2= comparisonList )? NEWLINE )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:217:5: comparisonList1= comparisonList ( assignment comparisonList2= comparisonList )? NEWLINE
                pass 
                self._state.following.append(self.FOLLOW_comparisonList_in_expressionStmt1311)
                comparisonList1 = self.comparisonList()

                self._state.following.pop()
                #action start
                object = ExpressionStmt( comparisonList1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:218:7: ( assignment comparisonList2= comparisonList )?
                alt28 = 2
                LA28_0 = self.input.LA(1)

                if ((ASSIGN <= LA28_0 <= DOUBLESLASHEQUAL)) :
                    alt28 = 1
                if alt28 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:218:9: assignment comparisonList2= comparisonList
                    pass 
                    self._state.following.append(self.FOLLOW_assignment_in_expressionStmt1323)
                    assignment78 = self.assignment()

                    self._state.following.pop()
                    self._state.following.append(self.FOLLOW_comparisonList_in_expressionStmt1327)
                    comparisonList2 = self.comparisonList()

                    self._state.following.pop()
                    #action start
                    object.append_children( [assignment78, comparisonList2] ) 
                    #action end



                self.match(self.input, NEWLINE, self.FOLLOW_NEWLINE_in_expressionStmt1334)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "expressionStmt"


    # $ANTLR start "assignment"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:221:1: assignment returns [object] : ( ASSIGN | PLUSEQUAL | MINUSEQUAL | STAREQUAL | SLASHEQUAL | PERCENTEQUAL | AMPEREQUAL | VBAREQUAL | CIRCUMFLEXEQUAL | LEFTSHIFTEQUAL | RIGHTSHIFTEQUAL | DOUBLESTAREQUAL | DOUBLESLASHEQUAL );
    def assignment(self, ):

        object = None

        ASSIGN79 = None
        PLUSEQUAL80 = None
        MINUSEQUAL81 = None
        STAREQUAL82 = None
        SLASHEQUAL83 = None
        PERCENTEQUAL84 = None
        AMPEREQUAL85 = None
        VBAREQUAL86 = None
        CIRCUMFLEXEQUAL87 = None
        LEFTSHIFTEQUAL88 = None
        RIGHTSHIFTEQUAL89 = None
        DOUBLESTAREQUAL90 = None
        DOUBLESLASHEQUAL91 = None

        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:222:3: ( ASSIGN | PLUSEQUAL | MINUSEQUAL | STAREQUAL | SLASHEQUAL | PERCENTEQUAL | AMPEREQUAL | VBAREQUAL | CIRCUMFLEXEQUAL | LEFTSHIFTEQUAL | RIGHTSHIFTEQUAL | DOUBLESTAREQUAL | DOUBLESLASHEQUAL )
                alt29 = 13
                LA29 = self.input.LA(1)
                if LA29 == ASSIGN:
                    alt29 = 1
                elif LA29 == PLUSEQUAL:
                    alt29 = 2
                elif LA29 == MINUSEQUAL:
                    alt29 = 3
                elif LA29 == STAREQUAL:
                    alt29 = 4
                elif LA29 == SLASHEQUAL:
                    alt29 = 5
                elif LA29 == PERCENTEQUAL:
                    alt29 = 6
                elif LA29 == AMPEREQUAL:
                    alt29 = 7
                elif LA29 == VBAREQUAL:
                    alt29 = 8
                elif LA29 == CIRCUMFLEXEQUAL:
                    alt29 = 9
                elif LA29 == LEFTSHIFTEQUAL:
                    alt29 = 10
                elif LA29 == RIGHTSHIFTEQUAL:
                    alt29 = 11
                elif LA29 == DOUBLESTAREQUAL:
                    alt29 = 12
                elif LA29 == DOUBLESLASHEQUAL:
                    alt29 = 13
                else:
                    nvae = NoViableAltException("", 29, 0, self.input)

                    raise nvae

                if alt29 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:222:5: ASSIGN
                    pass 
                    ASSIGN79=self.match(self.input, ASSIGN, self.FOLLOW_ASSIGN_in_assignment1352)
                    #action start
                    object = Assignment( ASSIGN79.text ) 
                    #action end


                elif alt29 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:223:5: PLUSEQUAL
                    pass 
                    PLUSEQUAL80=self.match(self.input, PLUSEQUAL, self.FOLLOW_PLUSEQUAL_in_assignment1371)
                    #action start
                    object = Assignment( PLUSEQUAL80.text ) 
                    #action end


                elif alt29 == 3:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:224:5: MINUSEQUAL
                    pass 
                    MINUSEQUAL81=self.match(self.input, MINUSEQUAL, self.FOLLOW_MINUSEQUAL_in_assignment1387)
                    #action start
                    object = Assignment( MINUSEQUAL81.text ) 
                    #action end


                elif alt29 == 4:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:225:5: STAREQUAL
                    pass 
                    STAREQUAL82=self.match(self.input, STAREQUAL, self.FOLLOW_STAREQUAL_in_assignment1402)
                    #action start
                    object = Assignment( STAREQUAL82.text ) 
                    #action end


                elif alt29 == 5:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:226:5: SLASHEQUAL
                    pass 
                    SLASHEQUAL83=self.match(self.input, SLASHEQUAL, self.FOLLOW_SLASHEQUAL_in_assignment1418)
                    #action start
                    object = Assignment( SLASHEQUAL83.text ) 
                    #action end


                elif alt29 == 6:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:227:5: PERCENTEQUAL
                    pass 
                    PERCENTEQUAL84=self.match(self.input, PERCENTEQUAL, self.FOLLOW_PERCENTEQUAL_in_assignment1433)
                    #action start
                    object = Assignment( PERCENTEQUAL84.text ) 
                    #action end


                elif alt29 == 7:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:228:5: AMPEREQUAL
                    pass 
                    AMPEREQUAL85=self.match(self.input, AMPEREQUAL, self.FOLLOW_AMPEREQUAL_in_assignment1446)
                    #action start
                    object = Assignment( AMPEREQUAL85.text ) 
                    #action end


                elif alt29 == 8:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:229:5: VBAREQUAL
                    pass 
                    VBAREQUAL86=self.match(self.input, VBAREQUAL, self.FOLLOW_VBAREQUAL_in_assignment1461)
                    #action start
                    object = Assignment( VBAREQUAL86.text ) 
                    #action end


                elif alt29 == 9:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:230:5: CIRCUMFLEXEQUAL
                    pass 
                    CIRCUMFLEXEQUAL87=self.match(self.input, CIRCUMFLEXEQUAL, self.FOLLOW_CIRCUMFLEXEQUAL_in_assignment1477)
                    #action start
                    object = Assignment( CIRCUMFLEXEQUAL87.text ) 
                    #action end


                elif alt29 == 10:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:231:5: LEFTSHIFTEQUAL
                    pass 
                    LEFTSHIFTEQUAL88=self.match(self.input, LEFTSHIFTEQUAL, self.FOLLOW_LEFTSHIFTEQUAL_in_assignment1487)
                    #action start
                    object = Assignment( LEFTSHIFTEQUAL88.text ) 
                    #action end


                elif alt29 == 11:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:232:5: RIGHTSHIFTEQUAL
                    pass 
                    RIGHTSHIFTEQUAL89=self.match(self.input, RIGHTSHIFTEQUAL, self.FOLLOW_RIGHTSHIFTEQUAL_in_assignment1498)
                    #action start
                    object = Assignment( RIGHTSHIFTEQUAL89.text ) 
                    #action end


                elif alt29 == 12:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:233:5: DOUBLESTAREQUAL
                    pass 
                    DOUBLESTAREQUAL90=self.match(self.input, DOUBLESTAREQUAL, self.FOLLOW_DOUBLESTAREQUAL_in_assignment1508)
                    #action start
                    object = Assignment( DOUBLESTAREQUAL90.text ) 
                    #action end


                elif alt29 == 13:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:234:5: DOUBLESLASHEQUAL
                    pass 
                    DOUBLESLASHEQUAL91=self.match(self.input, DOUBLESLASHEQUAL, self.FOLLOW_DOUBLESLASHEQUAL_in_assignment1518)
                    #action start
                    object = Assignment( DOUBLESLASHEQUAL91.text ) 
                    #action end



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "assignment"


    # $ANTLR start "constraint"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:237:1: constraint returns [object] : orConstraint ;
    def constraint(self, ):

        object = None

        orConstraint92 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:238:3: ( orConstraint )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:238:5: orConstraint
                pass 
                self._state.following.append(self.FOLLOW_orConstraint_in_constraint1539)
                orConstraint92 = self.orConstraint()

                self._state.following.pop()
                #action start
                object = Constraint( orConstraint92 ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "constraint"


    # $ANTLR start "orConstraint"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:241:1: orConstraint returns [object] : constraint1= andConstraint ( OR constraint2= andConstraint )* ;
    def orConstraint(self, ):

        object = None

        OR93 = None
        constraint1 = None

        constraint2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:242:3: (constraint1= andConstraint ( OR constraint2= andConstraint )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:242:5: constraint1= andConstraint ( OR constraint2= andConstraint )*
                pass 
                self._state.following.append(self.FOLLOW_andConstraint_in_orConstraint1561)
                constraint1 = self.andConstraint()

                self._state.following.pop()
                #action start
                object = OrConstraint( constraint1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:243:7: ( OR constraint2= andConstraint )*
                while True: #loop30
                    alt30 = 2
                    LA30_0 = self.input.LA(1)

                    if (LA30_0 == OR) :
                        alt30 = 1


                    if alt30 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:243:9: OR constraint2= andConstraint
                        pass 
                        OR93=self.match(self.input, OR, self.FOLLOW_OR_in_orConstraint1573)
                        self._state.following.append(self.FOLLOW_andConstraint_in_orConstraint1577)
                        constraint2 = self.andConstraint()

                        self._state.following.pop()
                        #action start
                        object.append_children( [OR93.text, constraint2] ) 
                        #action end


                    else:
                        break #loop30




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "orConstraint"


    # $ANTLR start "andConstraint"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:246:1: andConstraint returns [object] : constraint1= notConstraint ( AND constraint2= notConstraint )* ;
    def andConstraint(self, ):

        object = None

        AND94 = None
        constraint1 = None

        constraint2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:247:3: (constraint1= notConstraint ( AND constraint2= notConstraint )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:247:5: constraint1= notConstraint ( AND constraint2= notConstraint )*
                pass 
                self._state.following.append(self.FOLLOW_notConstraint_in_andConstraint1602)
                constraint1 = self.notConstraint()

                self._state.following.pop()
                #action start
                object = AndConstraint( constraint1 )
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:248:7: ( AND constraint2= notConstraint )*
                while True: #loop31
                    alt31 = 2
                    LA31_0 = self.input.LA(1)

                    if (LA31_0 == AND) :
                        alt31 = 1


                    if alt31 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:248:9: AND constraint2= notConstraint
                        pass 
                        AND94=self.match(self.input, AND, self.FOLLOW_AND_in_andConstraint1614)
                        self._state.following.append(self.FOLLOW_notConstraint_in_andConstraint1618)
                        constraint2 = self.notConstraint()

                        self._state.following.pop()
                        #action start
                        object.append_children( [AND94.text, constraint2] ) 
                        #action end


                    else:
                        break #loop31




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "andConstraint"


    # $ANTLR start "notConstraint"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:251:1: notConstraint returns [object] : ( NOT )* comparison ;
    def notConstraint(self, ):

        object = None

        NOT95 = None
        comparison96 = None


        object = NotConstraint() 
        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:253:3: ( ( NOT )* comparison )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:253:5: ( NOT )* comparison
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:253:5: ( NOT )*
                while True: #loop32
                    alt32 = 2
                    LA32_0 = self.input.LA(1)

                    if (LA32_0 == NOT) :
                        alt32 = 1


                    if alt32 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:253:7: NOT
                        pass 
                        NOT95=self.match(self.input, NOT, self.FOLLOW_NOT_in_notConstraint1649)
                        #action start
                        object.append_child( NOT95.text ) 
                        #action end


                    else:
                        break #loop32
                self._state.following.append(self.FOLLOW_comparison_in_notConstraint1656)
                comparison96 = self.comparison()

                self._state.following.pop()
                #action start
                object.append_child( comparison96 ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "notConstraint"


    # $ANTLR start "comparison"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:256:1: comparison returns [object] : expression1= expression ( comparisonOperation expression2= expression )* ;
    def comparison(self, ):

        object = None

        expression1 = None

        expression2 = None

        comparisonOperation97 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:257:3: (expression1= expression ( comparisonOperation expression2= expression )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:257:5: expression1= expression ( comparisonOperation expression2= expression )*
                pass 
                self._state.following.append(self.FOLLOW_expression_in_comparison1678)
                expression1 = self.expression()

                self._state.following.pop()
                #action start
                object = Comparison( expression1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:258:5: ( comparisonOperation expression2= expression )*
                while True: #loop33
                    alt33 = 2
                    LA33_0 = self.input.LA(1)

                    if (LA33_0 == NOT or (LESS <= LA33_0 <= IS)) :
                        alt33 = 1


                    if alt33 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:258:7: comparisonOperation expression2= expression
                        pass 
                        self._state.following.append(self.FOLLOW_comparisonOperation_in_comparison1688)
                        comparisonOperation97 = self.comparisonOperation()

                        self._state.following.pop()
                        self._state.following.append(self.FOLLOW_expression_in_comparison1692)
                        expression2 = self.expression()

                        self._state.following.pop()
                        #action start
                        object.append_children( [ comparisonOperation97, expression2] ) 
                        #action end


                    else:
                        break #loop33




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "comparison"


    # $ANTLR start "comparisonOperation"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:261:1: comparisonOperation returns [object] : ( LESS | GREATER | EQUAL | GREATEREQUAL | LESSEQUAL | ALT_NOTEQUAL | NOTEQUAL | IN | NOT IN | IS | IS NOT ) ;
    def comparisonOperation(self, ):

        object = None

        LESS98 = None
        GREATER99 = None
        EQUAL100 = None
        GREATEREQUAL101 = None
        LESSEQUAL102 = None
        ALT_NOTEQUAL103 = None
        NOTEQUAL104 = None

        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:262:3: ( ( LESS | GREATER | EQUAL | GREATEREQUAL | LESSEQUAL | ALT_NOTEQUAL | NOTEQUAL | IN | NOT IN | IS | IS NOT ) )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:262:5: ( LESS | GREATER | EQUAL | GREATEREQUAL | LESSEQUAL | ALT_NOTEQUAL | NOTEQUAL | IN | NOT IN | IS | IS NOT )
                pass 
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:262:5: ( LESS | GREATER | EQUAL | GREATEREQUAL | LESSEQUAL | ALT_NOTEQUAL | NOTEQUAL | IN | NOT IN | IS | IS NOT )
                alt34 = 11
                alt34 = self.dfa34.predict(self.input)
                if alt34 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:262:7: LESS
                    pass 
                    LESS98=self.match(self.input, LESS, self.FOLLOW_LESS_in_comparisonOperation1717)
                    #action start
                    object = ComparisonOperation( LESS98.text ) 
                    #action end


                elif alt34 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:263:7: GREATER
                    pass 
                    GREATER99=self.match(self.input, GREATER, self.FOLLOW_GREATER_in_comparisonOperation1736)
                    #action start
                    object = ComparisonOperation( GREATER99.text ) 
                    #action end


                elif alt34 == 3:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:264:7: EQUAL
                    pass 
                    EQUAL100=self.match(self.input, EQUAL, self.FOLLOW_EQUAL_in_comparisonOperation1752)
                    #action start
                    object = ComparisonOperation( EQUAL100.text ) 
                    #action end


                elif alt34 == 4:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:265:7: GREATEREQUAL
                    pass 
                    GREATEREQUAL101=self.match(self.input, GREATEREQUAL, self.FOLLOW_GREATEREQUAL_in_comparisonOperation1770)
                    #action start
                    object = ComparisonOperation( GREATEREQUAL101.text ) 
                    #action end


                elif alt34 == 5:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:266:7: LESSEQUAL
                    pass 
                    LESSEQUAL102=self.match(self.input, LESSEQUAL, self.FOLLOW_LESSEQUAL_in_comparisonOperation1781)
                    #action start
                    object = ComparisonOperation( LESSEQUAL102.text ) 
                    #action end


                elif alt34 == 6:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:267:7: ALT_NOTEQUAL
                    pass 
                    ALT_NOTEQUAL103=self.match(self.input, ALT_NOTEQUAL, self.FOLLOW_ALT_NOTEQUAL_in_comparisonOperation1795)
                    #action start
                    object = ComparisonOperation( ALT_NOTEQUAL103.text ) 
                    #action end


                elif alt34 == 7:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:268:7: NOTEQUAL
                    pass 
                    NOTEQUAL104=self.match(self.input, NOTEQUAL, self.FOLLOW_NOTEQUAL_in_comparisonOperation1806)
                    #action start
                    object = ComparisonOperation( NOTEQUAL104.text ) 
                    #action end


                elif alt34 == 8:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:269:7: IN
                    pass 
                    self.match(self.input, IN, self.FOLLOW_IN_in_comparisonOperation1821)
                    #action start
                    object = ComparisonOperation( "in" ) 
                    #action end


                elif alt34 == 9:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:270:7: NOT IN
                    pass 
                    self.match(self.input, NOT, self.FOLLOW_NOT_in_comparisonOperation1842)
                    self.match(self.input, IN, self.FOLLOW_IN_in_comparisonOperation1844)
                    #action start
                    object = ComparisonOperation( "not in" ) 
                    #action end


                elif alt34 == 10:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:271:7: IS
                    pass 
                    self.match(self.input, IS, self.FOLLOW_IS_in_comparisonOperation1861)
                    #action start
                    object = ComparisonOperation( "is" ) 
                    #action end


                elif alt34 == 11:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:272:7: IS NOT
                    pass 
                    self.match(self.input, IS, self.FOLLOW_IS_in_comparisonOperation1882)
                    self.match(self.input, NOT, self.FOLLOW_NOT_in_comparisonOperation1884)
                    #action start
                    object = ComparisonOperation( "is not" ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "comparisonOperation"


    # $ANTLR start "expression"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:275:1: expression returns [object] : bitwiseOrExpr ;
    def expression(self, ):

        object = None

        bitwiseOrExpr105 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:276:3: ( bitwiseOrExpr )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:276:5: bitwiseOrExpr
                pass 
                self._state.following.append(self.FOLLOW_bitwiseOrExpr_in_expression1913)
                bitwiseOrExpr105 = self.bitwiseOrExpr()

                self._state.following.pop()
                #action start
                object = Expression( bitwiseOrExpr105 ) 
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "expression"


    # $ANTLR start "bitwiseOrExpr"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:279:1: bitwiseOrExpr returns [object] : expr1= bitwiseXorExpr ( VBAR expr2= bitwiseXorExpr )* ;
    def bitwiseOrExpr(self, ):

        object = None

        VBAR106 = None
        expr1 = None

        expr2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:280:3: (expr1= bitwiseXorExpr ( VBAR expr2= bitwiseXorExpr )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:280:5: expr1= bitwiseXorExpr ( VBAR expr2= bitwiseXorExpr )*
                pass 
                self._state.following.append(self.FOLLOW_bitwiseXorExpr_in_bitwiseOrExpr1935)
                expr1 = self.bitwiseXorExpr()

                self._state.following.pop()
                #action start
                object = BitwiseOrExpr( expr1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:281:7: ( VBAR expr2= bitwiseXorExpr )*
                while True: #loop35
                    alt35 = 2
                    LA35_0 = self.input.LA(1)

                    if (LA35_0 == VBAR) :
                        alt35 = 1


                    if alt35 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:281:9: VBAR expr2= bitwiseXorExpr
                        pass 
                        VBAR106=self.match(self.input, VBAR, self.FOLLOW_VBAR_in_bitwiseOrExpr1947)
                        self._state.following.append(self.FOLLOW_bitwiseXorExpr_in_bitwiseOrExpr1951)
                        expr2 = self.bitwiseXorExpr()

                        self._state.following.pop()
                        #action start
                        object.append_children( [VBAR106.text, expr2] ) 
                        #action end


                    else:
                        break #loop35




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "bitwiseOrExpr"


    # $ANTLR start "bitwiseXorExpr"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:284:1: bitwiseXorExpr returns [object] : expr1= bitwiseAndExpr ( CIRCUMFLEX expr2= bitwiseAndExpr )* ;
    def bitwiseXorExpr(self, ):

        object = None

        CIRCUMFLEX107 = None
        expr1 = None

        expr2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:285:3: (expr1= bitwiseAndExpr ( CIRCUMFLEX expr2= bitwiseAndExpr )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:285:5: expr1= bitwiseAndExpr ( CIRCUMFLEX expr2= bitwiseAndExpr )*
                pass 
                self._state.following.append(self.FOLLOW_bitwiseAndExpr_in_bitwiseXorExpr1976)
                expr1 = self.bitwiseAndExpr()

                self._state.following.pop()
                #action start
                object = BitwiseXorExpr( expr1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:286:7: ( CIRCUMFLEX expr2= bitwiseAndExpr )*
                while True: #loop36
                    alt36 = 2
                    LA36_0 = self.input.LA(1)

                    if (LA36_0 == CIRCUMFLEX) :
                        alt36 = 1


                    if alt36 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:286:9: CIRCUMFLEX expr2= bitwiseAndExpr
                        pass 
                        CIRCUMFLEX107=self.match(self.input, CIRCUMFLEX, self.FOLLOW_CIRCUMFLEX_in_bitwiseXorExpr1988)
                        self._state.following.append(self.FOLLOW_bitwiseAndExpr_in_bitwiseXorExpr1992)
                        expr2 = self.bitwiseAndExpr()

                        self._state.following.pop()
                        #action start
                        object.append_children( [CIRCUMFLEX107.text, expr2] ) 
                        #action end


                    else:
                        break #loop36




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "bitwiseXorExpr"


    # $ANTLR start "bitwiseAndExpr"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:289:1: bitwiseAndExpr returns [object] : expr1= shiftExpr ( AMPER expr2= shiftExpr )* ;
    def bitwiseAndExpr(self, ):

        object = None

        AMPER108 = None
        expr1 = None

        expr2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:290:3: (expr1= shiftExpr ( AMPER expr2= shiftExpr )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:290:5: expr1= shiftExpr ( AMPER expr2= shiftExpr )*
                pass 
                self._state.following.append(self.FOLLOW_shiftExpr_in_bitwiseAndExpr2017)
                expr1 = self.shiftExpr()

                self._state.following.pop()
                #action start
                object = BitwiseAndExpr( expr1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:291:7: ( AMPER expr2= shiftExpr )*
                while True: #loop37
                    alt37 = 2
                    LA37_0 = self.input.LA(1)

                    if (LA37_0 == AMPER) :
                        alt37 = 1


                    if alt37 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:291:9: AMPER expr2= shiftExpr
                        pass 
                        AMPER108=self.match(self.input, AMPER, self.FOLLOW_AMPER_in_bitwiseAndExpr2029)
                        self._state.following.append(self.FOLLOW_shiftExpr_in_bitwiseAndExpr2033)
                        expr2 = self.shiftExpr()

                        self._state.following.pop()
                        #action start
                        object.append_children( [AMPER108.text, expr2] ) 
                        #action end


                    else:
                        break #loop37




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "bitwiseAndExpr"


    # $ANTLR start "shiftExpr"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:294:1: shiftExpr returns [object] : expr1= arithExpr ( ( LEFTSHIFT | RIGHTSHIFT ) expr2= arithExpr )* ;
    def shiftExpr(self, ):

        object = None

        LEFTSHIFT109 = None
        RIGHTSHIFT110 = None
        expr1 = None

        expr2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:295:3: (expr1= arithExpr ( ( LEFTSHIFT | RIGHTSHIFT ) expr2= arithExpr )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:295:5: expr1= arithExpr ( ( LEFTSHIFT | RIGHTSHIFT ) expr2= arithExpr )*
                pass 
                self._state.following.append(self.FOLLOW_arithExpr_in_shiftExpr2058)
                expr1 = self.arithExpr()

                self._state.following.pop()
                #action start
                object = ShiftExpr( expr1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:296:7: ( ( LEFTSHIFT | RIGHTSHIFT ) expr2= arithExpr )*
                while True: #loop39
                    alt39 = 2
                    LA39_0 = self.input.LA(1)

                    if (LA39_0 == RIGHTSHIFT or LA39_0 == LEFTSHIFT) :
                        alt39 = 1


                    if alt39 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:296:9: ( LEFTSHIFT | RIGHTSHIFT ) expr2= arithExpr
                        pass 
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:296:9: ( LEFTSHIFT | RIGHTSHIFT )
                        alt38 = 2
                        LA38_0 = self.input.LA(1)

                        if (LA38_0 == LEFTSHIFT) :
                            alt38 = 1
                        elif (LA38_0 == RIGHTSHIFT) :
                            alt38 = 2
                        else:
                            nvae = NoViableAltException("", 38, 0, self.input)

                            raise nvae

                        if alt38 == 1:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:296:11: LEFTSHIFT
                            pass 
                            LEFTSHIFT109=self.match(self.input, LEFTSHIFT, self.FOLLOW_LEFTSHIFT_in_shiftExpr2072)
                            #action start
                            object.append_child( LEFTSHIFT109.text ) 
                            #action end


                        elif alt38 == 2:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:296:67: RIGHTSHIFT
                            pass 
                            RIGHTSHIFT110=self.match(self.input, RIGHTSHIFT, self.FOLLOW_RIGHTSHIFT_in_shiftExpr2078)
                            #action start
                            object.append_child( RIGHTSHIFT110.text ) 
                            #action end



                        self._state.following.append(self.FOLLOW_arithExpr_in_shiftExpr2096)
                        expr2 = self.arithExpr()

                        self._state.following.pop()
                        #action start
                        object.append_child( expr2 ) 
                        #action end


                    else:
                        break #loop39




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "shiftExpr"


    # $ANTLR start "arithExpr"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:300:1: arithExpr returns [object] : term1= term ( ( PLUS | MINUS ) term2= term )* ;
    def arithExpr(self, ):

        object = None

        PLUS111 = None
        MINUS112 = None
        term1 = None

        term2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:301:3: (term1= term ( ( PLUS | MINUS ) term2= term )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:301:5: term1= term ( ( PLUS | MINUS ) term2= term )*
                pass 
                self._state.following.append(self.FOLLOW_term_in_arithExpr2121)
                term1 = self.term()

                self._state.following.pop()
                #action start
                object = ArithExpr( term1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:302:7: ( ( PLUS | MINUS ) term2= term )*
                while True: #loop41
                    alt41 = 2
                    LA41_0 = self.input.LA(1)

                    if ((PLUS <= LA41_0 <= MINUS)) :
                        alt41 = 1


                    if alt41 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:302:9: ( PLUS | MINUS ) term2= term
                        pass 
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:302:9: ( PLUS | MINUS )
                        alt40 = 2
                        LA40_0 = self.input.LA(1)

                        if (LA40_0 == PLUS) :
                            alt40 = 1
                        elif (LA40_0 == MINUS) :
                            alt40 = 2
                        else:
                            nvae = NoViableAltException("", 40, 0, self.input)

                            raise nvae

                        if alt40 == 1:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:302:11: PLUS
                            pass 
                            PLUS111=self.match(self.input, PLUS, self.FOLLOW_PLUS_in_arithExpr2135)
                            #action start
                            object.append_child( PLUS111.text ) 
                            #action end


                        elif alt40 == 2:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:302:57: MINUS
                            pass 
                            MINUS112=self.match(self.input, MINUS, self.FOLLOW_MINUS_in_arithExpr2141)
                            #action start
                            object.append_child( MINUS112.text ) 
                            #action end



                        self._state.following.append(self.FOLLOW_term_in_arithExpr2159)
                        term2 = self.term()

                        self._state.following.pop()
                        #action start
                        object.append_child( term2 ) 
                        #action end


                    else:
                        break #loop41




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "arithExpr"


    # $ANTLR start "term"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:306:1: term returns [object] : factor1= factor ( ( STAR | SLASH | PERCENT | DOUBLESLASH ) factor2= factor )* ;
    def term(self, ):

        object = None

        STAR113 = None
        SLASH114 = None
        PERCENT115 = None
        DOUBLESLASH116 = None
        factor1 = None

        factor2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:307:3: (factor1= factor ( ( STAR | SLASH | PERCENT | DOUBLESLASH ) factor2= factor )* )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:307:5: factor1= factor ( ( STAR | SLASH | PERCENT | DOUBLESLASH ) factor2= factor )*
                pass 
                self._state.following.append(self.FOLLOW_factor_in_term2184)
                factor1 = self.factor()

                self._state.following.pop()
                #action start
                object = Term( factor1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:308:7: ( ( STAR | SLASH | PERCENT | DOUBLESLASH ) factor2= factor )*
                while True: #loop43
                    alt43 = 2
                    LA43_0 = self.input.LA(1)

                    if ((STAR <= LA43_0 <= DOUBLESLASH)) :
                        alt43 = 1


                    if alt43 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:308:9: ( STAR | SLASH | PERCENT | DOUBLESLASH ) factor2= factor
                        pass 
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:308:9: ( STAR | SLASH | PERCENT | DOUBLESLASH )
                        alt42 = 4
                        LA42 = self.input.LA(1)
                        if LA42 == STAR:
                            alt42 = 1
                        elif LA42 == SLASH:
                            alt42 = 2
                        elif LA42 == PERCENT:
                            alt42 = 3
                        elif LA42 == DOUBLESLASH:
                            alt42 = 4
                        else:
                            nvae = NoViableAltException("", 42, 0, self.input)

                            raise nvae

                        if alt42 == 1:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:308:10: STAR
                            pass 
                            STAR113=self.match(self.input, STAR, self.FOLLOW_STAR_in_term2197)
                            #action start
                            object.append_child( STAR113.text ) 
                            #action end


                        elif alt42 == 2:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:308:56: SLASH
                            pass 
                            SLASH114=self.match(self.input, SLASH, self.FOLLOW_SLASH_in_term2203)
                            #action start
                            object.append_child( SLASH114.text ) 
                            #action end


                        elif alt42 == 3:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:309:13: PERCENT
                            pass 
                            PERCENT115=self.match(self.input, PERCENT, self.FOLLOW_PERCENT_in_term2219)
                            #action start
                            object.append_child( PERCENT115.text ) 
                            #action end


                        elif alt42 == 4:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:309:65: DOUBLESLASH
                            pass 
                            DOUBLESLASH116=self.match(self.input, DOUBLESLASH, self.FOLLOW_DOUBLESLASH_in_term2225)
                            #action start
                            object.append_child( DOUBLESLASH116.text ) 
                            #action end



                        self._state.following.append(self.FOLLOW_factor_in_term2247)
                        factor2 = self.factor()

                        self._state.following.pop()
                        #action start
                        object.append_child( factor2 ) 
                        #action end


                    else:
                        break #loop43




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "term"


    # $ANTLR start "factor"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:313:1: factor returns [object] : ( PLUS factor1= factor | MINUS factor2= factor | TILDE factor3= factor | power );
    def factor(self, ):

        object = None

        PLUS117 = None
        MINUS118 = None
        TILDE119 = None
        factor1 = None

        factor2 = None

        factor3 = None

        power120 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:314:3: ( PLUS factor1= factor | MINUS factor2= factor | TILDE factor3= factor | power )
                alt44 = 4
                LA44 = self.input.LA(1)
                if LA44 == PLUS:
                    alt44 = 1
                elif LA44 == MINUS:
                    alt44 = 2
                elif LA44 == TILDE:
                    alt44 = 3
                elif LA44 == LPAREN or LA44 == NAME or LA44 == STRING or LA44 == OBJECTBINDING or LA44 == LBRACK or LA44 == LCURLY or LA44 == INT or LA44 == LONGINT or LA44 == FLOAT or LA44 == COMPLEX:
                    alt44 = 4
                else:
                    nvae = NoViableAltException("", 44, 0, self.input)

                    raise nvae

                if alt44 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:314:5: PLUS factor1= factor
                    pass 
                    PLUS117=self.match(self.input, PLUS, self.FOLLOW_PLUS_in_factor2270)
                    self._state.following.append(self.FOLLOW_factor_in_factor2275)
                    factor1 = self.factor()

                    self._state.following.pop()
                    #action start
                    object = Factor( [PLUS117.text, factor1] ) 
                    #action end


                elif alt44 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:315:5: MINUS factor2= factor
                    pass 
                    MINUS118=self.match(self.input, MINUS, self.FOLLOW_MINUS_in_factor2283)
                    self._state.following.append(self.FOLLOW_factor_in_factor2287)
                    factor2 = self.factor()

                    self._state.following.pop()
                    #action start
                    object = Factor( [MINUS118.text, factor2] ) 
                    #action end


                elif alt44 == 3:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:316:5: TILDE factor3= factor
                    pass 
                    TILDE119=self.match(self.input, TILDE, self.FOLLOW_TILDE_in_factor2295)
                    self._state.following.append(self.FOLLOW_factor_in_factor2299)
                    factor3 = self.factor()

                    self._state.following.pop()
                    #action start
                    object = Factor( [TILDE119.text, factor3] ) 
                    #action end


                elif alt44 == 4:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:317:5: power
                    pass 
                    self._state.following.append(self.FOLLOW_power_in_factor2307)
                    power120 = self.power()

                    self._state.following.pop()
                    #action start
                    object = Factor( power120 ) 
                    #action end



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "factor"


    # $ANTLR start "power"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:320:1: power returns [object] : atom ( trailer )* ( options {greedy=true; } : DOUBLESTAR factor )? ;
    def power(self, ):

        object = None

        DOUBLESTAR123 = None
        atom121 = None

        trailer122 = None

        factor124 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:321:3: ( atom ( trailer )* ( options {greedy=true; } : DOUBLESTAR factor )? )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:321:5: atom ( trailer )* ( options {greedy=true; } : DOUBLESTAR factor )?
                pass 
                self._state.following.append(self.FOLLOW_atom_in_power2327)
                atom121 = self.atom()

                self._state.following.pop()
                #action start
                object = Power( atom121 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:322:7: ( trailer )*
                while True: #loop45
                    alt45 = 2
                    LA45_0 = self.input.LA(1)

                    if (LA45_0 == LPAREN or LA45_0 == DOT or LA45_0 == LBRACK) :
                        alt45 = 1


                    if alt45 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:322:9: trailer
                        pass 
                        self._state.following.append(self.FOLLOW_trailer_in_power2339)
                        trailer122 = self.trailer()

                        self._state.following.pop()
                        #action start
                        object.append_child( trailer122 ) 
                        #action end


                    else:
                        break #loop45
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:323:7: ( options {greedy=true; } : DOUBLESTAR factor )?
                alt46 = 2
                LA46_0 = self.input.LA(1)

                if (LA46_0 == DOUBLESTAR) :
                    alt46 = 1
                if alt46 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:323:31: DOUBLESTAR factor
                    pass 
                    DOUBLESTAR123=self.match(self.input, DOUBLESTAR, self.FOLLOW_DOUBLESTAR_in_power2360)
                    self._state.following.append(self.FOLLOW_factor_in_power2362)
                    factor124 = self.factor()

                    self._state.following.pop()
                    #action start
                    object.append_children( [DOUBLESTAR123.text, factor124] ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "power"


    # $ANTLR start "atom"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:326:1: atom returns [object] : ( LPAREN (comparisonList1= comparisonList )? RPAREN | LBRACK ( listmaker )? RBRACK | LCURLY ( dictmaker )? RCURLY | NAME | OBJECTBINDING | INT | LONGINT | FLOAT | COMPLEX | ( STRING )+ );
    def atom(self, ):

        object = None

        LPAREN125 = None
        RPAREN126 = None
        LBRACK127 = None
        RBRACK129 = None
        LCURLY130 = None
        RCURLY132 = None
        NAME133 = None
        OBJECTBINDING134 = None
        INT135 = None
        LONGINT136 = None
        FLOAT137 = None
        COMPLEX138 = None
        STRING139 = None
        comparisonList1 = None

        listmaker128 = None

        dictmaker131 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:327:3: ( LPAREN (comparisonList1= comparisonList )? RPAREN | LBRACK ( listmaker )? RBRACK | LCURLY ( dictmaker )? RCURLY | NAME | OBJECTBINDING | INT | LONGINT | FLOAT | COMPLEX | ( STRING )+ )
                alt51 = 10
                LA51 = self.input.LA(1)
                if LA51 == LPAREN:
                    alt51 = 1
                elif LA51 == LBRACK:
                    alt51 = 2
                elif LA51 == LCURLY:
                    alt51 = 3
                elif LA51 == NAME:
                    alt51 = 4
                elif LA51 == OBJECTBINDING:
                    alt51 = 5
                elif LA51 == INT:
                    alt51 = 6
                elif LA51 == LONGINT:
                    alt51 = 7
                elif LA51 == FLOAT:
                    alt51 = 8
                elif LA51 == COMPLEX:
                    alt51 = 9
                elif LA51 == STRING:
                    alt51 = 10
                else:
                    nvae = NoViableAltException("", 51, 0, self.input)

                    raise nvae

                if alt51 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:327:5: LPAREN (comparisonList1= comparisonList )? RPAREN
                    pass 
                    LPAREN125=self.match(self.input, LPAREN, self.FOLLOW_LPAREN_in_atom2385)
                    #action start
                    object = Atom( LPAREN125.text ) 
                    #action end
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:328:23: (comparisonList1= comparisonList )?
                    alt47 = 2
                    LA47_0 = self.input.LA(1)

                    if (LA47_0 == LPAREN or LA47_0 == NAME or LA47_0 == STRING or LA47_0 == NOT or LA47_0 == OBJECTBINDING or (PLUS <= LA47_0 <= MINUS) or LA47_0 == TILDE or LA47_0 == LBRACK or LA47_0 == LCURLY or (INT <= LA47_0 <= COMPLEX)) :
                        alt47 = 1
                    if alt47 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:328:25: comparisonList1= comparisonList
                        pass 
                        self._state.following.append(self.FOLLOW_comparisonList_in_atom2424)
                        comparisonList1 = self.comparisonList()

                        self._state.following.pop()
                        #action start
                        object.append_child( comparisonList1 ) 
                        #action end



                    RPAREN126=self.match(self.input, RPAREN, self.FOLLOW_RPAREN_in_atom2453)
                    #action start
                    object.append_child( RPAREN126.text ) 
                    #action end


                elif alt51 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:330:5: LBRACK ( listmaker )? RBRACK
                    pass 
                    LBRACK127=self.match(self.input, LBRACK, self.FOLLOW_LBRACK_in_atom2461)
                    #action start
                    object = Atom( LBRACK127.text ) 
                    #action end
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:331:23: ( listmaker )?
                    alt48 = 2
                    LA48_0 = self.input.LA(1)

                    if (LA48_0 == LPAREN or LA48_0 == NAME or LA48_0 == STRING or LA48_0 == NOT or LA48_0 == OBJECTBINDING or (PLUS <= LA48_0 <= MINUS) or LA48_0 == TILDE or LA48_0 == LBRACK or LA48_0 == LCURLY or (INT <= LA48_0 <= COMPLEX)) :
                        alt48 = 1
                    if alt48 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:331:25: listmaker
                        pass 
                        self._state.following.append(self.FOLLOW_listmaker_in_atom2498)
                        listmaker128 = self.listmaker()

                        self._state.following.pop()
                        #action start
                        object.append_child( listmaker128 ) 
                        #action end



                    RBRACK129=self.match(self.input, RBRACK, self.FOLLOW_RBRACK_in_atom2527)
                    #action start
                    object.append_child( RBRACK129.text ) 
                    #action end


                elif alt51 == 3:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:333:5: LCURLY ( dictmaker )? RCURLY
                    pass 
                    LCURLY130=self.match(self.input, LCURLY, self.FOLLOW_LCURLY_in_atom2535)
                    #action start
                    object = Atom( LCURLY130.text ) 
                    #action end
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:334:23: ( dictmaker )?
                    alt49 = 2
                    LA49_0 = self.input.LA(1)

                    if (LA49_0 == LPAREN or LA49_0 == NAME or LA49_0 == STRING or LA49_0 == NOT or LA49_0 == OBJECTBINDING or (PLUS <= LA49_0 <= MINUS) or LA49_0 == TILDE or LA49_0 == LBRACK or LA49_0 == LCURLY or (INT <= LA49_0 <= COMPLEX)) :
                        alt49 = 1
                    if alt49 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:334:25: dictmaker
                        pass 
                        self._state.following.append(self.FOLLOW_dictmaker_in_atom2572)
                        dictmaker131 = self.dictmaker()

                        self._state.following.pop()
                        #action start
                        object.append_child( dictmaker131 ) 
                        #action end



                    RCURLY132=self.match(self.input, RCURLY, self.FOLLOW_RCURLY_in_atom2601)
                    #action start
                    object.append_child( RCURLY132.text ) 
                    #action end


                elif alt51 == 4:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:337:5: NAME
                    pass 
                    NAME133=self.match(self.input, NAME, self.FOLLOW_NAME_in_atom2610)
                    #action start
                    object = Atom( NAME133.text ) 
                    #action end


                elif alt51 == 5:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:338:5: OBJECTBINDING
                    pass 
                    OBJECTBINDING134=self.match(self.input, OBJECTBINDING, self.FOLLOW_OBJECTBINDING_in_atom2629)
                    #action start
                    object = Atom( OBJECTBINDING134.text ) 
                    #action end


                elif alt51 == 6:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:339:5: INT
                    pass 
                    INT135=self.match(self.input, INT, self.FOLLOW_INT_in_atom2639)
                    #action start
                    object = Atom( INT135.text ) 
                    #action end


                elif alt51 == 7:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:340:5: LONGINT
                    pass 
                    LONGINT136=self.match(self.input, LONGINT, self.FOLLOW_LONGINT_in_atom2659)
                    #action start
                    object = Atom( LONGINT136.text ) 
                    #action end


                elif alt51 == 8:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:341:5: FLOAT
                    pass 
                    FLOAT137=self.match(self.input, FLOAT, self.FOLLOW_FLOAT_in_atom2675)
                    #action start
                    object = Atom( FLOAT137.text ) 
                    #action end


                elif alt51 == 9:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:342:5: COMPLEX
                    pass 
                    COMPLEX138=self.match(self.input, COMPLEX, self.FOLLOW_COMPLEX_in_atom2693)
                    #action start
                    object = Atom( COMPLEX138.text ) 
                    #action end


                elif alt51 == 10:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:343:5: ( STRING )+
                    pass 
                    #action start
                    object = Atom() 
                    #action end
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:343:25: ( STRING )+
                    cnt50 = 0
                    while True: #loop50
                        alt50 = 2
                        LA50_0 = self.input.LA(1)

                        if (LA50_0 == STRING) :
                            alt50 = 1


                        if alt50 == 1:
                            # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:343:27: STRING
                            pass 
                            STRING139=self.match(self.input, STRING, self.FOLLOW_STRING_in_atom2713)
                            #action start
                            object.append_child( STRING139.text ) 
                            #action end


                        else:
                            if cnt50 >= 1:
                                break #loop50

                            eee = EarlyExitException(50, self.input)
                            raise eee

                        cnt50 += 1



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "atom"


    # $ANTLR start "listmaker"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:346:1: listmaker returns [object] : constraint1= constraint ( options {greedy=true; } : COMMA constraint2= constraint )* ( COMMA )? ;
    def listmaker(self, ):

        object = None

        constraint1 = None

        constraint2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:347:3: (constraint1= constraint ( options {greedy=true; } : COMMA constraint2= constraint )* ( COMMA )? )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:347:5: constraint1= constraint ( options {greedy=true; } : COMMA constraint2= constraint )* ( COMMA )?
                pass 
                self._state.following.append(self.FOLLOW_constraint_in_listmaker2738)
                constraint1 = self.constraint()

                self._state.following.pop()
                #action start
                object = ListMaker( constraint1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:348:7: ( options {greedy=true; } : COMMA constraint2= constraint )*
                while True: #loop52
                    alt52 = 2
                    LA52_0 = self.input.LA(1)

                    if (LA52_0 == COMMA) :
                        LA52_1 = self.input.LA(2)

                        if (LA52_1 == LPAREN or LA52_1 == NAME or LA52_1 == STRING or LA52_1 == NOT or LA52_1 == OBJECTBINDING or (PLUS <= LA52_1 <= MINUS) or LA52_1 == TILDE or LA52_1 == LBRACK or LA52_1 == LCURLY or (INT <= LA52_1 <= COMPLEX)) :
                            alt52 = 1




                    if alt52 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:348:31: COMMA constraint2= constraint
                        pass 
                        self.match(self.input, COMMA, self.FOLLOW_COMMA_in_listmaker2756)
                        self._state.following.append(self.FOLLOW_constraint_in_listmaker2760)
                        constraint2 = self.constraint()

                        self._state.following.pop()
                        #action start
                        object.append_children( [ ",", constraint2] ) 
                        #action end


                    else:
                        break #loop52
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:349:7: ( COMMA )?
                alt53 = 2
                LA53_0 = self.input.LA(1)

                if (LA53_0 == COMMA) :
                    alt53 = 1
                if alt53 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:349:9: COMMA
                    pass 
                    self.match(self.input, COMMA, self.FOLLOW_COMMA_in_listmaker2775)
                    #action start
                    object.append_child( "," ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "listmaker"


    # $ANTLR start "comparisonList"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:352:1: comparisonList returns [object] : constraint1= constraint ( options {k=2; } : COMMA constraint2= constraint )* ( COMMA )? ;
    def comparisonList(self, ):

        object = None

        constraint1 = None

        constraint2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:353:3: (constraint1= constraint ( options {k=2; } : COMMA constraint2= constraint )* ( COMMA )? )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:353:5: constraint1= constraint ( options {k=2; } : COMMA constraint2= constraint )* ( COMMA )?
                pass 
                self._state.following.append(self.FOLLOW_constraint_in_comparisonList2800)
                constraint1 = self.constraint()

                self._state.following.pop()
                #action start
                object = ComparisonList( constraint1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:354:7: ( options {k=2; } : COMMA constraint2= constraint )*
                while True: #loop54
                    alt54 = 2
                    alt54 = self.dfa54.predict(self.input)
                    if alt54 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:354:23: COMMA constraint2= constraint
                        pass 
                        self.match(self.input, COMMA, self.FOLLOW_COMMA_in_comparisonList2818)
                        self._state.following.append(self.FOLLOW_constraint_in_comparisonList2822)
                        constraint2 = self.constraint()

                        self._state.following.pop()
                        #action start
                        object.append_children( [",", constraint2] ) 
                        #action end


                    else:
                        break #loop54
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:355:7: ( COMMA )?
                alt55 = 2
                LA55_0 = self.input.LA(1)

                if (LA55_0 == COMMA) :
                    alt55 = 1
                if alt55 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:355:9: COMMA
                    pass 
                    self.match(self.input, COMMA, self.FOLLOW_COMMA_in_comparisonList2837)
                    #action start
                    object.append_child( "," ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "comparisonList"


    # $ANTLR start "trailer"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:358:1: trailer returns [object] : ( LPAREN ( argumentList )? RPAREN | LBRACK ( constraint )? RBRACK | DOT NAME );
    def trailer(self, ):

        object = None

        LPAREN140 = None
        RPAREN142 = None
        LBRACK143 = None
        RBRACK145 = None
        DOT146 = None
        NAME147 = None
        argumentList141 = None

        constraint144 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:359:3: ( LPAREN ( argumentList )? RPAREN | LBRACK ( constraint )? RBRACK | DOT NAME )
                alt58 = 3
                LA58 = self.input.LA(1)
                if LA58 == LPAREN:
                    alt58 = 1
                elif LA58 == LBRACK:
                    alt58 = 2
                elif LA58 == DOT:
                    alt58 = 3
                else:
                    nvae = NoViableAltException("", 58, 0, self.input)

                    raise nvae

                if alt58 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:359:5: LPAREN ( argumentList )? RPAREN
                    pass 
                    LPAREN140=self.match(self.input, LPAREN, self.FOLLOW_LPAREN_in_trailer2860)
                    #action start
                    object = Trailer( LPAREN140.text ) 
                    #action end
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:359:49: ( argumentList )?
                    alt56 = 2
                    LA56_0 = self.input.LA(1)

                    if (LA56_0 == LPAREN or LA56_0 == NAME or LA56_0 == STRING or LA56_0 == NOT or LA56_0 == OBJECTBINDING or (PLUS <= LA56_0 <= MINUS) or LA56_0 == TILDE or LA56_0 == LBRACK or LA56_0 == LCURLY or (INT <= LA56_0 <= COMPLEX)) :
                        alt56 = 1
                    if alt56 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:359:50: argumentList
                        pass 
                        self._state.following.append(self.FOLLOW_argumentList_in_trailer2865)
                        argumentList141 = self.argumentList()

                        self._state.following.pop()
                        #action start
                        object.append_child( argumentList141 ) 
                        #action end



                    RPAREN142=self.match(self.input, RPAREN, self.FOLLOW_RPAREN_in_trailer2872)
                    #action start
                    object.append_child( RPAREN142.text ) 
                    #action end


                elif alt58 == 2:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:360:5: LBRACK ( constraint )? RBRACK
                    pass 
                    LBRACK143=self.match(self.input, LBRACK, self.FOLLOW_LBRACK_in_trailer2880)
                    #action start
                    object = Trailer( LBRACK143.text ) 
                    #action end
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:360:49: ( constraint )?
                    alt57 = 2
                    LA57_0 = self.input.LA(1)

                    if (LA57_0 == LPAREN or LA57_0 == NAME or LA57_0 == STRING or LA57_0 == NOT or LA57_0 == OBJECTBINDING or (PLUS <= LA57_0 <= MINUS) or LA57_0 == TILDE or LA57_0 == LBRACK or LA57_0 == LCURLY or (INT <= LA57_0 <= COMPLEX)) :
                        alt57 = 1
                    if alt57 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:360:50: constraint
                        pass 
                        self._state.following.append(self.FOLLOW_constraint_in_trailer2885)
                        constraint144 = self.constraint()

                        self._state.following.pop()
                        #action start
                        object.append_child( constraint144 ) 
                        #action end



                    RBRACK145=self.match(self.input, RBRACK, self.FOLLOW_RBRACK_in_trailer2892)
                    #action start
                    object.append_child( RBRACK145.text ) 
                    #action end


                elif alt58 == 3:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:361:5: DOT NAME
                    pass 
                    DOT146=self.match(self.input, DOT, self.FOLLOW_DOT_in_trailer2900)
                    NAME147=self.match(self.input, NAME, self.FOLLOW_NAME_in_trailer2902)
                    #action start
                    object = Trailer( [DOT146.text, NAME147.text] ) 
                    #action end



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "trailer"


    # $ANTLR start "expressionList"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:364:1: expressionList returns [object] : expression1= expression ( options {k=2; } : COMMA expression2= expression )* ( COMMA )? ;
    def expressionList(self, ):

        object = None

        expression1 = None

        expression2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:365:3: (expression1= expression ( options {k=2; } : COMMA expression2= expression )* ( COMMA )? )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:365:5: expression1= expression ( options {k=2; } : COMMA expression2= expression )* ( COMMA )?
                pass 
                self._state.following.append(self.FOLLOW_expression_in_expressionList2925)
                expression1 = self.expression()

                self._state.following.pop()
                #action start
                object = ExpressionList( expression1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:366:7: ( options {k=2; } : COMMA expression2= expression )*
                while True: #loop59
                    alt59 = 2
                    alt59 = self.dfa59.predict(self.input)
                    if alt59 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:366:25: COMMA expression2= expression
                        pass 
                        self.match(self.input, COMMA, self.FOLLOW_COMMA_in_expressionList2945)
                        self._state.following.append(self.FOLLOW_expression_in_expressionList2949)
                        expression2 = self.expression()

                        self._state.following.pop()
                        #action start
                        object.append_children( [ ",", expression2 ] ) 
                        #action end


                    else:
                        break #loop59
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:367:7: ( COMMA )?
                alt60 = 2
                LA60_0 = self.input.LA(1)

                if (LA60_0 == COMMA) :
                    alt60 = 1
                if alt60 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:367:9: COMMA
                    pass 
                    self.match(self.input, COMMA, self.FOLLOW_COMMA_in_expressionList2964)
                    #action start
                    object.append_child( "," ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "expressionList"


    # $ANTLR start "dictmaker"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:370:1: dictmaker returns [object] : constraint1= constraint COLON constraint2= constraint ( options {k=2; } : COMMA constraint3= constraint COLON constraint4= constraint )* ( COMMA )? ;
    def dictmaker(self, ):

        object = None

        constraint1 = None

        constraint2 = None

        constraint3 = None

        constraint4 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:371:3: (constraint1= constraint COLON constraint2= constraint ( options {k=2; } : COMMA constraint3= constraint COLON constraint4= constraint )* ( COMMA )? )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:371:5: constraint1= constraint COLON constraint2= constraint ( options {k=2; } : COMMA constraint3= constraint COLON constraint4= constraint )* ( COMMA )?
                pass 
                self._state.following.append(self.FOLLOW_constraint_in_dictmaker2989)
                constraint1 = self.constraint()

                self._state.following.pop()
                #action start
                object = DictMaker( constraint1 ) 
                #action end
                self.match(self.input, COLON, self.FOLLOW_COLON_in_dictmaker2999)
                self._state.following.append(self.FOLLOW_constraint_in_dictmaker3003)
                constraint2 = self.constraint()

                self._state.following.pop()
                #action start
                object.append_children( [":", constraint2] ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:373:9: ( options {k=2; } : COMMA constraint3= constraint COLON constraint4= constraint )*
                while True: #loop61
                    alt61 = 2
                    alt61 = self.dfa61.predict(self.input)
                    if alt61 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:373:26: COMMA constraint3= constraint COLON constraint4= constraint
                        pass 
                        self.match(self.input, COMMA, self.FOLLOW_COMMA_in_dictmaker3024)
                        self._state.following.append(self.FOLLOW_constraint_in_dictmaker3028)
                        constraint3 = self.constraint()

                        self._state.following.pop()
                        self.match(self.input, COLON, self.FOLLOW_COLON_in_dictmaker3030)
                        self._state.following.append(self.FOLLOW_constraint_in_dictmaker3034)
                        constraint4 = self.constraint()

                        self._state.following.pop()
                        #action start
                        object.append_children( [",", constraint3, ":", constraint4] ) 
                        #action end


                    else:
                        break #loop61
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:374:9: ( COMMA )?
                alt62 = 2
                LA62_0 = self.input.LA(1)

                if (LA62_0 == COMMA) :
                    alt62 = 1
                if alt62 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:374:11: COMMA
                    pass 
                    self.match(self.input, COMMA, self.FOLLOW_COMMA_in_dictmaker3051)
                    #action start
                    object.append_child( "," ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "dictmaker"


    # $ANTLR start "argumentList"
    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:377:1: argumentList returns [object] : constraint1= constraint ( COMMA constraint2= constraint )* ( COMMA )? ;
    def argumentList(self, ):

        object = None

        constraint1 = None

        constraint2 = None


        try:
            try:
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:378:3: (constraint1= constraint ( COMMA constraint2= constraint )* ( COMMA )? )
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:378:5: constraint1= constraint ( COMMA constraint2= constraint )* ( COMMA )?
                pass 
                self._state.following.append(self.FOLLOW_constraint_in_argumentList3076)
                constraint1 = self.constraint()

                self._state.following.pop()
                #action start
                object = ArgumentList( constraint1 ) 
                #action end
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:379:7: ( COMMA constraint2= constraint )*
                while True: #loop63
                    alt63 = 2
                    LA63_0 = self.input.LA(1)

                    if (LA63_0 == COMMA) :
                        LA63_1 = self.input.LA(2)

                        if (LA63_1 == LPAREN or LA63_1 == NAME or LA63_1 == STRING or LA63_1 == NOT or LA63_1 == OBJECTBINDING or (PLUS <= LA63_1 <= MINUS) or LA63_1 == TILDE or LA63_1 == LBRACK or LA63_1 == LCURLY or (INT <= LA63_1 <= COMPLEX)) :
                            alt63 = 1




                    if alt63 == 1:
                        # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:379:9: COMMA constraint2= constraint
                        pass 
                        self.match(self.input, COMMA, self.FOLLOW_COMMA_in_argumentList3088)
                        self._state.following.append(self.FOLLOW_constraint_in_argumentList3092)
                        constraint2 = self.constraint()

                        self._state.following.pop()
                        #action start
                        object.append_children( [",", constraint2] ) 
                        #action end


                    else:
                        break #loop63
                # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:380:7: ( COMMA )?
                alt64 = 2
                LA64_0 = self.input.LA(1)

                if (LA64_0 == COMMA) :
                    alt64 = 1
                if alt64 == 1:
                    # /Users/walsh/Development/workspace/Intellect/intellect/grammar/Policy.g:380:9: COMMA
                    pass 
                    self.match(self.input, COMMA, self.FOLLOW_COMMA_in_argumentList3107)
                    #action start
                    object.append_child( "," ) 
                    #action end







            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return object

    # $ANTLR end "argumentList"


    # Delegated rules


    # lookup tables for DFA #34

    DFA34_eot = DFA.unpack(
        u"\15\uffff"
        )

    DFA34_eof = DFA.unpack(
        u"\15\uffff"
        )

    DFA34_min = DFA.unpack(
        u"\1\25\11\uffff\1\11\2\uffff"
        )

    DFA34_max = DFA.unpack(
        u"\1\71\11\uffff\1\115\2\uffff"
        )

    DFA34_accept = DFA.unpack(
        u"\1\uffff\1\1\1\2\1\3\1\4\1\5\1\6\1\7\1\10\1\11\1\uffff\1\13\1\12"
        )

    DFA34_special = DFA.unpack(
        u"\15\uffff"
        )

            
    DFA34_transition = [
        DFA.unpack(u"\1\11\33\uffff\1\1\1\2\1\3\1\4\1\5\1\6\1\7\1\10\1\12"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"\1\14\2\uffff\1\14\4\uffff\1\14\3\uffff\1\13\1\uffff"
        u"\1\14\46\uffff\2\14\4\uffff\1\14\1\uffff\1\14\1\uffff\1\14\1\uffff"
        u"\4\14"),
        DFA.unpack(u""),
        DFA.unpack(u"")
    ]

    # class definition for DFA #34

    class DFA34(DFA):
        pass


    # lookup tables for DFA #54

    DFA54_eot = DFA.unpack(
        u"\56\uffff"
        )

    DFA54_eof = DFA.unpack(
        u"\56\uffff"
        )

    DFA54_min = DFA.unpack(
        u"\2\6\54\uffff"
        )

    DFA54_max = DFA.unpack(
        u"\1\56\1\115\54\uffff"
        )

    DFA54_accept = DFA.unpack(
        u"\2\uffff\1\2\16\uffff\1\1\34\uffff"
        )

    DFA54_special = DFA.unpack(
        u"\56\uffff"
        )

            
    DFA54_transition = [
        DFA.unpack(u"\1\2\3\uffff\1\2\1\1\26\uffff\15\2"),
        DFA.unpack(u"\1\2\2\uffff\1\21\1\2\1\uffff\1\21\4\uffff\1\21\3\uffff"
        u"\1\21\1\uffff\1\21\12\uffff\15\2\17\uffff\2\21\4\uffff\1\21\1\uffff"
        u"\1\21\1\uffff\1\21\1\uffff\4\21"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"")
    ]

    # class definition for DFA #54

    class DFA54(DFA):
        pass


    # lookup tables for DFA #59

    DFA59_eot = DFA.unpack(
        u"\21\uffff"
        )

    DFA59_eof = DFA.unpack(
        u"\2\2\17\uffff"
        )

    DFA59_min = DFA.unpack(
        u"\1\13\1\11\17\uffff"
        )

    DFA59_max = DFA.unpack(
        u"\1\13\1\115\17\uffff"
        )

    DFA59_accept = DFA.unpack(
        u"\2\uffff\1\2\1\uffff\1\1\14\uffff"
        )

    DFA59_special = DFA.unpack(
        u"\21\uffff"
        )

            
    DFA59_transition = [
        DFA.unpack(u"\1\1"),
        DFA.unpack(u"\1\4\2\uffff\1\4\4\uffff\1\4\5\uffff\1\4\46\uffff\2"
        u"\4\4\uffff\1\4\1\uffff\1\4\1\uffff\1\4\1\uffff\4\4"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"")
    ]

    # class definition for DFA #59

    class DFA59(DFA):
        pass


    # lookup tables for DFA #61

    DFA61_eot = DFA.unpack(
        u"\22\uffff"
        )

    DFA61_eof = DFA.unpack(
        u"\22\uffff"
        )

    DFA61_min = DFA.unpack(
        u"\1\13\1\11\20\uffff"
        )

    DFA61_max = DFA.unpack(
        u"\1\111\1\115\20\uffff"
        )

    DFA61_accept = DFA.unpack(
        u"\2\uffff\1\2\1\1\16\uffff"
        )

    DFA61_special = DFA.unpack(
        u"\22\uffff"
        )

            
    DFA61_transition = [
        DFA.unpack(u"\1\1\75\uffff\1\2"),
        DFA.unpack(u"\1\3\2\uffff\1\3\4\uffff\1\3\3\uffff\1\3\1\uffff\1"
        u"\3\46\uffff\2\3\4\uffff\1\3\1\uffff\1\3\1\uffff\1\3\1\2\4\3"),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u""),
        DFA.unpack(u"")
    ]

    # class definition for DFA #61

    class DFA61(DFA):
        pass


 

    FOLLOW_NEWLINE_in_file78 = frozenset([1, 6, 7, 8, 9, 12, 15, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_statement_in_file82 = frozenset([1, 6, 7, 8, 9, 12, 15, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_EOF_in_file93 = frozenset([1])
    FOLLOW_importStmt_in_statement111 = frozenset([1])
    FOLLOW_attributeStmt_in_statement120 = frozenset([1])
    FOLLOW_ruleStmt_in_statement129 = frozenset([1])
    FOLLOW_importName_in_importStmt152 = frozenset([1])
    FOLLOW_importFrom_in_importStmt160 = frozenset([1])
    FOLLOW_IMPORT_in_importName180 = frozenset([12])
    FOLLOW_dottedAsNames_in_importName182 = frozenset([6])
    FOLLOW_NEWLINE_in_importName186 = frozenset([1])
    FOLLOW_FROM_in_importFrom204 = frozenset([12])
    FOLLOW_dottedName_in_importFrom208 = frozenset([7])
    FOLLOW_IMPORT_in_importFrom212 = frozenset([9, 12])
    FOLLOW_importAsNames_in_importFrom226 = frozenset([6])
    FOLLOW_LPAREN_in_importFrom238 = frozenset([12])
    FOLLOW_importAsNames_in_importFrom243 = frozenset([10])
    FOLLOW_RPAREN_in_importFrom245 = frozenset([6])
    FOLLOW_NEWLINE_in_importFrom257 = frozenset([1])
    FOLLOW_importAsName_in_importAsNames276 = frozenset([1, 11])
    FOLLOW_COMMA_in_importAsNames288 = frozenset([12])
    FOLLOW_importAsName_in_importAsNames292 = frozenset([1, 11])
    FOLLOW_COMMA_in_importAsNames301 = frozenset([1])
    FOLLOW_NAME_in_importAsName325 = frozenset([1, 13])
    FOLLOW_AS_in_importAsName331 = frozenset([12])
    FOLLOW_NAME_in_importAsName335 = frozenset([1])
    FOLLOW_dottedAsName_in_dottedAsNames359 = frozenset([1, 11])
    FOLLOW_COMMA_in_dottedAsNames371 = frozenset([12])
    FOLLOW_dottedAsName_in_dottedAsNames375 = frozenset([1, 11])
    FOLLOW_dottedName_in_dottedAsName397 = frozenset([1, 13])
    FOLLOW_AS_in_dottedAsName403 = frozenset([12])
    FOLLOW_NAME_in_dottedAsName405 = frozenset([1])
    FOLLOW_NAME_in_dottedName430 = frozenset([1, 14])
    FOLLOW_DOT_in_dottedName442 = frozenset([12])
    FOLLOW_NAME_in_dottedName446 = frozenset([1, 14])
    FOLLOW_expressionStmt_in_attributeStmt469 = frozenset([1])
    FOLLOW_RULE_in_ruleStmt489 = frozenset([12, 17])
    FOLLOW_id_in_ruleStmt491 = frozenset([16])
    FOLLOW_COLON_in_ruleStmt493 = frozenset([6])
    FOLLOW_NEWLINE_in_ruleStmt495 = frozenset([4])
    FOLLOW_INDENT_in_ruleStmt505 = frozenset([18, 19, 20])
    FOLLOW_ruleAttribute_in_ruleStmt509 = frozenset([18, 19, 20])
    FOLLOW_when_in_ruleStmt531 = frozenset([18, 19, 20])
    FOLLOW_then_in_ruleStmt551 = frozenset([5])
    FOLLOW_DEDENT_in_ruleStmt556 = frozenset([1])
    FOLLOW_NAME_in_id574 = frozenset([1])
    FOLLOW_STRING_in_id585 = frozenset([1])
    FOLLOW_agendaGroup_in_ruleAttribute606 = frozenset([1])
    FOLLOW_AGENDAGROUP_in_agendaGroup626 = frozenset([12, 17])
    FOLLOW_id_in_agendaGroup628 = frozenset([6])
    FOLLOW_NEWLINE_in_agendaGroup630 = frozenset([1])
    FOLLOW_WHEN_in_when650 = frozenset([16])
    FOLLOW_COLON_in_when652 = frozenset([6])
    FOLLOW_NEWLINE_in_when654 = frozenset([4])
    FOLLOW_INDENT_in_when664 = frozenset([5, 12, 21, 22, 23])
    FOLLOW_ruleCondition_in_when668 = frozenset([5])
    FOLLOW_DEDENT_in_when675 = frozenset([1])
    FOLLOW_THEN_in_then693 = frozenset([16])
    FOLLOW_COLON_in_then695 = frozenset([6])
    FOLLOW_NEWLINE_in_then697 = frozenset([4])
    FOLLOW_INDENT_in_then707 = frozenset([9, 12, 17, 21, 23, 25, 26, 28, 29, 30, 31, 32, 33, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_action_in_then711 = frozenset([5, 9, 12, 17, 21, 23, 25, 26, 28, 29, 30, 31, 32, 33, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_DEDENT_in_then718 = frozenset([1])
    FOLLOW_notCondition_in_ruleCondition736 = frozenset([6])
    FOLLOW_NEWLINE_in_ruleCondition738 = frozenset([1])
    FOLLOW_NOT_in_notCondition766 = frozenset([12, 21, 22, 23])
    FOLLOW_condition_in_notCondition773 = frozenset([1])
    FOLLOW_EXISTS_in_condition801 = frozenset([12, 21, 22, 23])
    FOLLOW_classConstraint_in_condition808 = frozenset([1])
    FOLLOW_OBJECTBINDING_in_classConstraint836 = frozenset([24])
    FOLLOW_ASSIGNEQUAL_in_classConstraint838 = frozenset([12])
    FOLLOW_NAME_in_classConstraint851 = frozenset([9])
    FOLLOW_LPAREN_in_classConstraint853 = frozenset([9, 10, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_constraint_in_classConstraint859 = frozenset([10])
    FOLLOW_RPAREN_in_classConstraint866 = frozenset([1])
    FOLLOW_simpleStmt_in_action886 = frozenset([1])
    FOLLOW_attributeAction_in_action900 = frozenset([1])
    FOLLOW_learnAction_in_action909 = frozenset([1])
    FOLLOW_forgetAction_in_action921 = frozenset([1])
    FOLLOW_modifyAction_in_action933 = frozenset([1])
    FOLLOW_haltAction_in_action945 = frozenset([1])
    FOLLOW_expressionStmt_in_simpleStmt971 = frozenset([1])
    FOLLOW_printStmt_in_simpleStmt985 = frozenset([1])
    FOLLOW_ATTRIBUTE_in_attributeAction1016 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_expressionStmt_in_attributeAction1018 = frozenset([1])
    FOLLOW_PRINT_in_printStmt1038 = frozenset([6, 9, 12, 17, 21, 23, 27, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_comparisonList_in_printStmt1052 = frozenset([6])
    FOLLOW_RIGHTSHIFT_in_printStmt1064 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_comparisonList_in_printStmt1068 = frozenset([6])
    FOLLOW_NEWLINE_in_printStmt1075 = frozenset([1])
    FOLLOW_FORGET_in_forgetAction1095 = frozenset([23])
    FOLLOW_DELETE_in_forgetAction1107 = frozenset([23])
    FOLLOW_OBJECTBINDING_in_forgetAction1120 = frozenset([6])
    FOLLOW_NEWLINE_in_forgetAction1124 = frozenset([1])
    FOLLOW_LEARN_in_learnAction1144 = frozenset([12])
    FOLLOW_INSERT_in_learnAction1156 = frozenset([12])
    FOLLOW_NAME_in_learnAction1171 = frozenset([9])
    FOLLOW_LPAREN_in_learnAction1173 = frozenset([9, 10, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_argumentList_in_learnAction1187 = frozenset([10])
    FOLLOW_RPAREN_in_learnAction1194 = frozenset([6])
    FOLLOW_NEWLINE_in_learnAction1198 = frozenset([1])
    FOLLOW_MODIFY_in_modifyAction1216 = frozenset([23])
    FOLLOW_OBJECTBINDING_in_modifyAction1218 = frozenset([16])
    FOLLOW_COLON_in_modifyAction1220 = frozenset([6])
    FOLLOW_NEWLINE_in_modifyAction1222 = frozenset([4])
    FOLLOW_INDENT_in_modifyAction1232 = frozenset([12])
    FOLLOW_propertyAssignment_in_modifyAction1236 = frozenset([5, 12])
    FOLLOW_DEDENT_in_modifyAction1243 = frozenset([1])
    FOLLOW_HALT_in_haltAction1261 = frozenset([6])
    FOLLOW_NEWLINE_in_haltAction1265 = frozenset([1])
    FOLLOW_NAME_in_propertyAssignment1283 = frozenset([34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46])
    FOLLOW_assignment_in_propertyAssignment1285 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_constraint_in_propertyAssignment1287 = frozenset([6])
    FOLLOW_NEWLINE_in_propertyAssignment1291 = frozenset([1])
    FOLLOW_comparisonList_in_expressionStmt1311 = frozenset([6, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46])
    FOLLOW_assignment_in_expressionStmt1323 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_comparisonList_in_expressionStmt1327 = frozenset([6])
    FOLLOW_NEWLINE_in_expressionStmt1334 = frozenset([1])
    FOLLOW_ASSIGN_in_assignment1352 = frozenset([1])
    FOLLOW_PLUSEQUAL_in_assignment1371 = frozenset([1])
    FOLLOW_MINUSEQUAL_in_assignment1387 = frozenset([1])
    FOLLOW_STAREQUAL_in_assignment1402 = frozenset([1])
    FOLLOW_SLASHEQUAL_in_assignment1418 = frozenset([1])
    FOLLOW_PERCENTEQUAL_in_assignment1433 = frozenset([1])
    FOLLOW_AMPEREQUAL_in_assignment1446 = frozenset([1])
    FOLLOW_VBAREQUAL_in_assignment1461 = frozenset([1])
    FOLLOW_CIRCUMFLEXEQUAL_in_assignment1477 = frozenset([1])
    FOLLOW_LEFTSHIFTEQUAL_in_assignment1487 = frozenset([1])
    FOLLOW_RIGHTSHIFTEQUAL_in_assignment1498 = frozenset([1])
    FOLLOW_DOUBLESTAREQUAL_in_assignment1508 = frozenset([1])
    FOLLOW_DOUBLESLASHEQUAL_in_assignment1518 = frozenset([1])
    FOLLOW_orConstraint_in_constraint1539 = frozenset([1])
    FOLLOW_andConstraint_in_orConstraint1561 = frozenset([1, 47])
    FOLLOW_OR_in_orConstraint1573 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_andConstraint_in_orConstraint1577 = frozenset([1, 47])
    FOLLOW_notConstraint_in_andConstraint1602 = frozenset([1, 48])
    FOLLOW_AND_in_andConstraint1614 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_notConstraint_in_andConstraint1618 = frozenset([1, 48])
    FOLLOW_NOT_in_notConstraint1649 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_comparison_in_notConstraint1656 = frozenset([1])
    FOLLOW_expression_in_comparison1678 = frozenset([1, 21, 49, 50, 51, 52, 53, 54, 55, 56, 57])
    FOLLOW_comparisonOperation_in_comparison1688 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_expression_in_comparison1692 = frozenset([1, 21, 49, 50, 51, 52, 53, 54, 55, 56, 57])
    FOLLOW_LESS_in_comparisonOperation1717 = frozenset([1])
    FOLLOW_GREATER_in_comparisonOperation1736 = frozenset([1])
    FOLLOW_EQUAL_in_comparisonOperation1752 = frozenset([1])
    FOLLOW_GREATEREQUAL_in_comparisonOperation1770 = frozenset([1])
    FOLLOW_LESSEQUAL_in_comparisonOperation1781 = frozenset([1])
    FOLLOW_ALT_NOTEQUAL_in_comparisonOperation1795 = frozenset([1])
    FOLLOW_NOTEQUAL_in_comparisonOperation1806 = frozenset([1])
    FOLLOW_IN_in_comparisonOperation1821 = frozenset([1])
    FOLLOW_NOT_in_comparisonOperation1842 = frozenset([56])
    FOLLOW_IN_in_comparisonOperation1844 = frozenset([1])
    FOLLOW_IS_in_comparisonOperation1861 = frozenset([1])
    FOLLOW_IS_in_comparisonOperation1882 = frozenset([21])
    FOLLOW_NOT_in_comparisonOperation1884 = frozenset([1])
    FOLLOW_bitwiseOrExpr_in_expression1913 = frozenset([1])
    FOLLOW_bitwiseXorExpr_in_bitwiseOrExpr1935 = frozenset([1, 58])
    FOLLOW_VBAR_in_bitwiseOrExpr1947 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_bitwiseXorExpr_in_bitwiseOrExpr1951 = frozenset([1, 58])
    FOLLOW_bitwiseAndExpr_in_bitwiseXorExpr1976 = frozenset([1, 59])
    FOLLOW_CIRCUMFLEX_in_bitwiseXorExpr1988 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_bitwiseAndExpr_in_bitwiseXorExpr1992 = frozenset([1, 59])
    FOLLOW_shiftExpr_in_bitwiseAndExpr2017 = frozenset([1, 60])
    FOLLOW_AMPER_in_bitwiseAndExpr2029 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_shiftExpr_in_bitwiseAndExpr2033 = frozenset([1, 60])
    FOLLOW_arithExpr_in_shiftExpr2058 = frozenset([1, 27, 61])
    FOLLOW_LEFTSHIFT_in_shiftExpr2072 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_RIGHTSHIFT_in_shiftExpr2078 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_arithExpr_in_shiftExpr2096 = frozenset([1, 27, 61])
    FOLLOW_term_in_arithExpr2121 = frozenset([1, 62, 63])
    FOLLOW_PLUS_in_arithExpr2135 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_MINUS_in_arithExpr2141 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_term_in_arithExpr2159 = frozenset([1, 62, 63])
    FOLLOW_factor_in_term2184 = frozenset([1, 64, 65, 66, 67])
    FOLLOW_STAR_in_term2197 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_SLASH_in_term2203 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_PERCENT_in_term2219 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_DOUBLESLASH_in_term2225 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_factor_in_term2247 = frozenset([1, 64, 65, 66, 67])
    FOLLOW_PLUS_in_factor2270 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_factor_in_factor2275 = frozenset([1])
    FOLLOW_MINUS_in_factor2283 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_factor_in_factor2287 = frozenset([1])
    FOLLOW_TILDE_in_factor2295 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_factor_in_factor2299 = frozenset([1])
    FOLLOW_power_in_factor2307 = frozenset([1])
    FOLLOW_atom_in_power2327 = frozenset([1, 9, 14, 69, 70])
    FOLLOW_trailer_in_power2339 = frozenset([1, 9, 14, 69, 70])
    FOLLOW_DOUBLESTAR_in_power2360 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_factor_in_power2362 = frozenset([1])
    FOLLOW_LPAREN_in_atom2385 = frozenset([9, 10, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_comparisonList_in_atom2424 = frozenset([10])
    FOLLOW_RPAREN_in_atom2453 = frozenset([1])
    FOLLOW_LBRACK_in_atom2461 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 71, 72, 74, 75, 76, 77])
    FOLLOW_listmaker_in_atom2498 = frozenset([71])
    FOLLOW_RBRACK_in_atom2527 = frozenset([1])
    FOLLOW_LCURLY_in_atom2535 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 73, 74, 75, 76, 77])
    FOLLOW_dictmaker_in_atom2572 = frozenset([73])
    FOLLOW_RCURLY_in_atom2601 = frozenset([1])
    FOLLOW_NAME_in_atom2610 = frozenset([1])
    FOLLOW_OBJECTBINDING_in_atom2629 = frozenset([1])
    FOLLOW_INT_in_atom2639 = frozenset([1])
    FOLLOW_LONGINT_in_atom2659 = frozenset([1])
    FOLLOW_FLOAT_in_atom2675 = frozenset([1])
    FOLLOW_COMPLEX_in_atom2693 = frozenset([1])
    FOLLOW_STRING_in_atom2713 = frozenset([1, 17])
    FOLLOW_constraint_in_listmaker2738 = frozenset([1, 11])
    FOLLOW_COMMA_in_listmaker2756 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_constraint_in_listmaker2760 = frozenset([1, 11])
    FOLLOW_COMMA_in_listmaker2775 = frozenset([1])
    FOLLOW_constraint_in_comparisonList2800 = frozenset([1, 11])
    FOLLOW_COMMA_in_comparisonList2818 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_constraint_in_comparisonList2822 = frozenset([1, 11])
    FOLLOW_COMMA_in_comparisonList2837 = frozenset([1])
    FOLLOW_LPAREN_in_trailer2860 = frozenset([9, 10, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_argumentList_in_trailer2865 = frozenset([10])
    FOLLOW_RPAREN_in_trailer2872 = frozenset([1])
    FOLLOW_LBRACK_in_trailer2880 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 71, 72, 74, 75, 76, 77])
    FOLLOW_constraint_in_trailer2885 = frozenset([71])
    FOLLOW_RBRACK_in_trailer2892 = frozenset([1])
    FOLLOW_DOT_in_trailer2900 = frozenset([12])
    FOLLOW_NAME_in_trailer2902 = frozenset([1])
    FOLLOW_expression_in_expressionList2925 = frozenset([1, 11])
    FOLLOW_COMMA_in_expressionList2945 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_expression_in_expressionList2949 = frozenset([1, 11])
    FOLLOW_COMMA_in_expressionList2964 = frozenset([1])
    FOLLOW_constraint_in_dictmaker2989 = frozenset([16])
    FOLLOW_COLON_in_dictmaker2999 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_constraint_in_dictmaker3003 = frozenset([1, 11])
    FOLLOW_COMMA_in_dictmaker3024 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_constraint_in_dictmaker3028 = frozenset([16])
    FOLLOW_COLON_in_dictmaker3030 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_constraint_in_dictmaker3034 = frozenset([1, 11])
    FOLLOW_COMMA_in_dictmaker3051 = frozenset([1])
    FOLLOW_constraint_in_argumentList3076 = frozenset([1, 11])
    FOLLOW_COMMA_in_argumentList3088 = frozenset([9, 12, 17, 21, 23, 62, 63, 68, 70, 72, 74, 75, 76, 77])
    FOLLOW_constraint_in_argumentList3092 = frozenset([1, 11])
    FOLLOW_COMMA_in_argumentList3107 = frozenset([1])



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import ParserMain
    main = ParserMain("PolicyLexer", PolicyParser)
    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)


if __name__ == '__main__':
    main(sys.argv)

########NEW FILE########
__FILENAME__ = Intellect
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import logging
import sys
import urllib
import urllib2
import os
import errno

from urlparse import urlparse

from antlr3 import CommonTokenStream, ANTLRStringStream

from intellect.grammar.PolicyParser import PolicyParser
from intellect.PolicyLexer import PolicyLexer
from intellect.Node import Policy
from intellect.Node import File
from intellect.PolicyTokenSource import PolicyTokenSource
from intellect.Callable import Callable
from intellect.IO import RedirectStdError



class Intellect(object):
    '''
    Rules engine.
    '''


    def __init__(self):
        '''
        Intellect initializer.
        '''

        # initialize list to hold learned objects
        self.knowledge = []

        # initialize the hold the combined sum of the policy files
        # as a single policy.
        self.policy = Policy()


    @property
    def knowledge(self):
        '''
        Returns the intellect's knowledge either a list of objects or an
            empty list.
        '''
        return self._knowledge


    @knowledge.setter
    def knowledge(self, one_or_more_objects):
        '''
        Keeper of knowledge.

        Holds facts aka objects in a list.

        Args:
            one_or_more_objects: Either a single facts or policy file or
                a list of facts and/or policy files.
        '''

        try:
            self.knowledge
        except AttributeError:
            self._knowledge = []

        if not isinstance(one_or_more_objects, list):
            self.knowledge.append(one_or_more_objects)
        elif one_or_more_objects != []:
            self.knowledge.extend(one_or_more_objects)


    @property
    def policy(self):
        '''
        Getter for the intellect's Policy object.
        '''
        return self._policy


    @policy.setter
    def policy(self, value):
        '''
        Setter for the intellect Policy object
        
        Args:
            value: a Policy object
        '''
        self._policy = value


    @staticmethod
    def local_file_uri(file_path):
        '''
        Helper/Utility method to take file system paths and return a file URI for use
        with learn, and learn_policy methods

        Args:
            file_path: The file path to the policy

        Returns:
            an equivalent file URI
        '''
        if os.path.isfile(file_path):
            try:
                with open(file_path):
                    pass

            except IOError:
                # Permission denied, cannot read file.
                raise IOError(errno.EACCES, "Permission denied to policy locate at: {0}".format(file_path))

        else:
            # Cannot find file.
            raise IOError(errno.ENOENT, "Cannot find policy located at:  {0}".format(file_path))

        full_path = urllib.pathname2url(os.path.abspath(file_path))
        if file_path.startswith("file://"):
            return full_path

        else:
            return "file://" + full_path


    @staticmethod
    def policy_from(urlstring):
        '''
        Helper/Utility method to retrieve a policy from a URL

        Uses proxies from environment.
        
        Args:
            urlstring: The URL to the policy file.
        
        Returns:
            The text of the policy.
        '''

        response = urllib2.urlopen(urlstring)

        return response.read()


    def learn(self, identifier):
        '''
        Learns an object fact, or learns a policy by messaging learn_policy
        method with the 'identifier' as a policy URL or the text of the policy,
        if the identifier is a string.

        Args:
            fact: an object or policy file/string to learn.  Typically objects have
                annotated properties and/or methods that return values.

        Raises:
            ValueError:  The fact or policy already exists in knowledge.
            TypeError:  Raised when parameter 'identifier' is a NoneType.
        '''
        if identifier:
            if isinstance(identifier, basestring):
                return self.learn_policy(identifier)
            elif self.knowledge.count(identifier) == 0:
                self.knowledge.append(identifier)
                self.log("Learned: {0}:{1}".format(type(identifier), identifier.__dict__))
            else:
                raise ValueError("{0}:{1} already exists in knowledge.".format(type(identifier), identifier.__dict__))
        else:
            raise TypeError("parameter 'identifier' cannot be a NoneType.")


    def learn_policy(self, identifier):
        '''
        Learn a policy file.

        Args:
            identifier: a string, either a URL to a policy file or the text of the policy itself.
            Keep in mind a policy can be comprised of more than one policy file (a file containing
            valid policy DSL) or string containing policy DSL.  This way you break your rule set,
            imports, and policy attributes across any number of files.  See reason-method for more.


        Returns:
            The resulting File Node.

        Raises:
            ValueError:  if the policy already exists in knowledge.
            TypeError:  if parameter 'identifier' is a NoneType, or is not a string representing
                either a file path to a policy or the text of the policy itself.
        '''

        is_file = False

        if identifier:
            if isinstance(identifier, basestring):
                if urlparse(identifier).scheme:

                    # Treat 'identifier' as an URL
                    self.log("Learning policy from URL: {0}".format(identifier))
                    stream = ANTLRStringStream(Intellect.policy_from(identifier))
                    is_file = True
                else:

                    #Treat 'identifier' as policy  string
                    self.log("Learning policy from string")
                    stream = ANTLRStringStream(identifier)

                lexer = PolicyLexer(stream)
                tokens = CommonTokenStream(lexer)
                tokens.discardOffChannelTokens = True
                indented_source = PolicyTokenSource(tokens)
                tokens = CommonTokenStream(indented_source)
                parser = PolicyParser(tokens)

                with RedirectStdError() as stderr:
                    try:
                        # ANTL3 may raise an exception, and doing so the stderror 
                        # will not be printed hiding the underlying problem.  GRRR!!!!
                        file_node = parser.file()
                    except Exception as e:
                        if stderr.getvalue().rstrip() != "":
                            trace = sys.exc_info()[2]
                            raise Exception(stderr.getvalue().rstrip()), None, trace
                        else:
                            raise e

                # The ANTLR3 Recognizer class prints a number of ANTLR3 Exceptions to
                # stderr vice throwing an exception, because it will try to recover and
                # continue parsing. 
                # 
                # In the case of NoViableAltException, I've chosen to raise an
                # exception.
                #
                # Otherwise, all the other error message that Recognizer writes to 
                # stderr will be returned for the benefit of the policy author.
                if stderr.getvalue().rstrip() != "":
                    # check for stderror msg indicating an NoViableAltException occured.
                    # if did raise an exception with the stderror message.
                    if "no viable alternative at input" in stderr.getvalue().rstrip():
                        raise Exception("Error parsing policy:  {0}\n{1}".format(identifier, stderr.getvalue().rstrip()))
                    else:
                        print >> sys.stderr, stderr.getvalue().rstrip()

                # set path attribute
                file_node.path = identifier if is_file else None

                # associate the path to all descendants
                file_node.set_file_on_descendants(file_node, file_node)

                try:
                    # determine if the policy already exists in knowledge
                    self.policy.files.index(file_node)
                    raise ValueError("Policy already exists in knowledge: {0}".format(identifier))
                except:
                    pass

                # store add the policy file to the policy
                self.policy.append_child(file_node)

                self.log("learned a policy file")

                return file_node

            else:
                raise TypeError("parameter 'identifier' must be a string, either a file path to a policy or the text of the policy itself")

        else:
            raise TypeError("parameter 'identifier' cannot be a NoneType.")


    def learn_fact(self, identifier):
        '''
        Wrapper for 'learn' method
        '''
        self.learn(identifier)


    def forget(self, identifier):
        '''
        Forgets an id() of a fact or policy, or a string representing the path
        of a policy, or a fact.

        Args:
            identifier: is an id() of a fact or policy, or a string
                representing the URL of a policy, or a fact.

        Raises:
            ValueError:  Raised when parameter 'identifier' has the right
                type but an inappropriate value.
            TypeError:  Raised when parameter 'identifier' is a NoneType.
        '''
        if identifier:
            if isinstance(identifier, int):
                # remove the fact from the knowledge
                for index, fact in enumerate(self.knowledge):
                    if identifier == id(fact):
                        self.log("Forgetting fact with id: {0} of type: {1} from knowledge. fact.__dict__: {2}".format(identifier, type(fact), fact.__dict__))
                        self.knowledge.remove(fact)
                        return
                # fact doesn't exist in memory, attempt to remove a policy file/String
                # from knowledge with this identifier
                for index, policy_file in self.policy.files:
                    if identifier == id(policy_file):
                        self.log("Forgetting policy loaded from file path : {0}".format(identifier.path))
                        self.policy.files.remove(policy_file)
                        return
                # neither fact nor policy so raise an exception
                raise ValueError("Fact with id: {0} is not in knowledge".format(identifier))
            elif isinstance(identifier, basestring):
                # remove the policy policy file from knowledge
                try:
                    for fileIndex, policy_file in enumerate(self.policy.files):
                        if policy_file.path == identifier:
                            self.policy.files.pop(fileIndex)

                    self.log("Forgetting policy loaded from file path : {0}".format(identifier))
                except KeyError:
                    raise ValueError("Policy for file path: {0} is not in knowledge".format(identifier))
            elif isinstance(identifier, File):
                try:
                    index = self.policy.files.index(identifier)
                    self.policy.files.pop(index)
                    self.log("Forgetting policy loaded from file path : {0}".format(identifier.path))
                except:
                    raise ValueError("Policy: {0} not in knowledge".format(identifier.path))
            else:
                try:
                    self.knowledge.remove(identifier)
                    self.log("Forgetting fact: {0}".format(identifier))
                except:
                    raise ValueError("Fact: {0} is not in knowledge".format(identifier))
        else:
            raise TypeError("Parameter 'identifier' cannot be a NoneType.")


    def forget_fact(self, identifier):
        '''
        Wrapper for 'forget' method

        Args:
            identifier: is the id() of the fact, or the fact itself to forget

        Raises:
            See forget-method 'raises'.
        '''
        self.forget(identifier)


    def forget_policy(self, identifier):
        '''
        Wrapper for 'forget' method

        Args:
            identifier: is the either the path to the policy to forget, or
            the Policy object itself.

        Raises:
            TypeError:  Raised when 'identifier' is not a basestring or Policy
                object.
            Also, see forget-method 'raises'.
        '''
        if isinstance(identifier, (basestring, File)):
            self.forget(identifier)
        else:
            raise TypeError("Parameter 'identifier': {0} was neither a path to the policy to forget, or a Policy object.".format(identifier))


    def forget_all(self):
        '''
        Forgets all facts in knowledge and the present policy
        '''
        self.knowledge = []
        self.policy = Policy()

        self.log("forgot all")


    def reason(self, agenda=None):
        '''
        Reasons across the facts in knowledge applying the policy.

        Args:
            agenda: is either the default of None or a list of agenda-group identifiers.
                If a rule is created with no agenda group attribute then the group will
                be associated with "MAIN" agenda group. If the 'agenda' attribute remains
                the default of None, then only the "MAIN" agenda group will fire.

            rule "flood the torpedo tubes":
                agenda group "firing sequence"
                when:
                  ...
                then:
                  ...

            So, in the scenario above an agenda may look like:

                agenda = ["targeting sequence", "firing sequence", "after firing sequence" ]

            First, all the rules associated with the "targeting sequence" agenda
            group will fire, then those associated with the "firing sequence"
            group...

            Note, any cumulative changes that occur to policy attributes are
            passed onto individual agenda groups.

            Remember, whatever is loaded last wins in terms of imports.  At present rule
            names are not evaluated.  So, it doesn't matter to the interpreter if you have
            two or more rules named the same, each will be evaluated.  Attributes and import
            statement are evaluated top to bottom.  Imports are evaluated first, then
            attributes, then rule statements.

        Raises:
            Any exceptions raised by the combined policy as it is evaluated will
            be raised here.
        '''

        #update the policy with the present Intellect
        self.policy.intellect = self

        # eval the policy using the described agenda
        self.policy.eval(agenda)


    @Callable
    def log(self, msg, name="intellect", level=logging.DEBUG):
        '''
        Logs at the 'level' for the messaged 'msg'

        Args:
            name: the name of the logger
            level:  must be either logging.DEBUG, logging.INFO, logging.WARNING,
                logging.ERROR, logging.CRITICAL
            msg: message string

        Raises:
            ValueError:  Raised when it receives an 'level' that is not either
                logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, or
                logging.CRITICAL.
        '''

        if level not in [logging.DEBUG, logging.INFO, logging.WARNING,
                logging.ERROR, logging.CRITICAL]:
            raise ValueError("A value of '{0}' for 'level' is invalid, must be either logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL".format(level))

        logging.getLogger(name).log(level, "{0}.{1} :: {2}".format(self.__class__.__module__, self.__class__.__name__, msg))

########NEW FILE########
__FILENAME__ = IO
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os
import sys
import StringIO


class RedirectStdError(object):

    def __init__(self):
        self._stderr = StringIO.StringIO()

    def __enter__(self):
        self.save_stderr = sys.stderr
        self.save_stderr.flush()
        sys.stderr = self._stderr

        return sys.stderr

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
        ):
        self._stderr.flush()
        sys.stderr = self.save_stderr


class RedirectStdOut(object):

    def __init__(self):
        self._stdout = StringIO.StringIO()

    def __enter__(self):
        self.save_stdout = sys.stdout
        self.save_stdout.flush()
        sys.stdout = self._stdout

        return sys.stdout

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
        ):
        self._stdout.flush()
        sys.stdout = self.save_stdout

########NEW FILE########
__FILENAME__ = Node
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


"""
Node

Description:
    Contains all the Node objects for the Policy grammar and forms the model.

Initial Version:
    Feb 9, 2011

@author: Michael Joseph Walsh
"""

import logging
import types
import collections
import keyword
import uuid
import sys

import intellect.reflection as reflection

from intellect.Callable import Callable
import intellect.IO as IO


class Node(object):
    '''
    All Policy Domain Specific Language (DSL) Nodes extend this node.
    '''

    def __init__(self, children=None, line=None, column=None):
        '''
        Node Initializer
        '''

        if not children:
            children = []
        elif not isinstance(children, list):
            children = [children]

        self._children = children
        self._line = line
        self._column = column

        self._file = None


    def __str__(self):
        '''
        Returns a str for this node and its children for what they represent
        in the policy.
        '''
        value = ""

        for child in self._children:

            value += str(child) + " "

        value = value.rstrip()

        return value


    def str_tree(self, text="", indentCount=0):
        '''
        Returns a textual tree representation of the Node and its
        children nodes.  Used for debugging purposes.
        '''
        text = text + "   "*indentCount + self.__class__.__name__ + "\n"

        for child in self._children:
            if isinstance(child, Node):
                text += child.str_tree("", indentCount + 1)
            else:
                text += "   "*(indentCount + 1) + child + "\n"

        return text


    @property
    def children(self):
        '''
        Returns a list, either empty or containing one or more children Node
        objects for this node.
        '''
        return self._children


    @children.setter
    def children(self, value):
        '''
        Sets the children list for this node.
        '''
        if not isinstance(value, (list, types.NoneType)):
            raise TypeError("Parameter 'value' must be a List or NoneType.")

        if value is None:
            value = []

        self._children = value


    def first_child(self):
        '''
        Returns the node's first child, if it has one; otherwise, None.
        '''
        if (not self.children):
            return None
        else:
            return self.children[0]


    def append_child(self, child):
        '''
        Appends a child to the node.  The child can be either a basestring
        or Node object, and nothing else.
        '''

        # cannot add None
        if not child:
            raise TypeError("Parameter 'child' cannot be None.")

        # must be either a basestring or Node object
        if not isinstance(child, (basestring, Node)):
            raise TypeError("Parameter 'child' must be a basetring or Node.")

        # if children is not yet a list, make it a list object
        if not self.children:
            self.children = []

        # append the bloody damn child
        self.children.append(child)


    def append_children(self, children):
        '''
        Append a list of siblings to the node
        '''

        # can't add None
        if not children:
            raise TypeError("Parameter 'children' cannot be an empty list.")

        # must be a list
        if not isinstance(children, list):
            raise TypeError("Parameter 'children' must be a list.")

        # iterate through the children to be added and
        # verify they are of the correct type, if not
        # raise a TypeError
        for child in children:
            if not isinstance(child, (basestring, Node)):
                raise TypeError(str(child) + " must be a basetring or Node.")

        # if children is not yet a list, make it a list object
        if not self.children:
            self.children = []

        # append the bloody damn siblings
        self.children.extend(children)


    def insert_child_at(self, index, child):
        '''
        Inserts a sibling at a given position. The first argument is the
        index of the element before which to insert, so a.insert(0, child)
        inserts at the front of the list of children, and
        a.insert(len(self.children), child) is equivalent to append_child(child).
        Parameter 'index' cannot be a value less than 0 or greater than
        len(self.children)
        '''

        # cann't add None
        if not child:
            raise TypeError("Parameter 'child' cannot be None.")

        # must be either a basestring or Node object
        if not isinstance(child, (basestring, Node)):
            raise TypeError("Parameter 'child' must be a basetring or Node.")

        # if children is not yet a list, make it a list object
        if not self.children:
            self.children = []

        if index > len(self.children) or index < 0:
            raise ValueError("Parameter 'index' cannot be a value less than 0 or greater than {0}. A value of {1} was passed.".format(len(self.children), index))

        self.children.insert(index, child)


    def insert_children_at(self, index, children):
        '''
        Inserts siblings at a given position. The first argument is the
        index of the element before which to insert, so a.insert(0, child)
        inserts at the front of the list of children, and
        a.insert(len(self.children), child) is equivalent to append_child(child).
        Index cannot be a value less than 0 or greater than len(self.children)
        '''

        # can't add None
        if not children:
            raise TypeError("Parameter 'children' cannot be an empty list.")

        # must be a list
        if not isinstance(children, list):
            raise TypeError("Parameter 'children' must be a list.")

        # iterate through the children to be added and
        # verify they are of the correct type, if not
        # raise a TypeError
        for child in children:
            if not isinstance(child, (basestring, Node)):
                raise TypeError(str(child) + " must be a basetring or Node.")

        # if children is not yet a list, make it a list object
        if not self.children:
            self.children = []

        # insert the bloody damn siblings
        for child in children:
            self.insert_child_at(index, children)
            index += 1


    @property
    def line(self):
        '''
        Get the int value for the line in the policy file
        corresponding to this node.

        Used when raising errors or debugging.
        '''
        return self._line


    @line.setter
    def line(self, value):
        '''
        Set the corresponding int value for the line
        in policy file that corresponds to this node.

        Used when raising errors or debugging.
        '''

        # must be a int or None object otherwise
        # raise a TypeError
        if isinstance(value, (int, types.NoneType)):
            self._line = value
        else:
            raise TypeError("Must be an int or NoneType.")


    @property
    def column(self):
        '''
        Get the corresponding int value for the column
        in policy file that begins this node.

        Used when raising errors or debugging.

        TODO:  The value I am getting from ANTLR3
        is off as I am post parsing the token stream.
        So, I stripped the code out of the
        grammar setting this value.
        '''
        return self._column


    @column.setter
    def column(self, value):
        '''
        Set int value for the column number in the policy
        file corresponding to this node. Used when raising
        errors or debugging.

        TODO:  The value I was getting from ANTLR3
        seemed off.  So, I stripped the code out of the
        grammar setting this value.
        '''
        if isinstance(value, (int, types.NoneType)):
            self._column = value
        else:
            raise TypeError("Must be an int.")


    @property
    def file(self):
        '''
        Returns the File Node that defines this Node.
        '''
        return self._file


    @file.setter
    def file(self, value):
        '''
        The File Node that defines this node
        '''
        if isinstance(value, File):
            self._file = value
        else:
            raise TypeError("'file' must be of type File.")


    def append_global(self, object_reference, value):
        #print locals()
        self.globals[object_reference] = value


    def log(self, msg, name="intellect", level=logging.DEBUG):
        '''
        Logs at the 'level' for the messaged 'msg'

        Args:
            name: the name of the logger
            level:  must be either logging.DEBUG, logging.INFO, logging.WARNING,
                logging.ERROR, logging.CRITICAL
            msg: message string
        '''

        if level not in [logging.DEBUG, logging.INFO, logging.WARNING,
                logging.ERROR, logging.CRITICAL]:
            raise ValueError("'level' must be either logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL")

        logging.getLogger(name).log(level, "{0}.{1} :: {2}".format(self.__class__.__module__, self.__class__.__name__, msg))


    @staticmethod
    def filter_to_list(type, node, list=None):
        '''
        Returns a list of nodes of 'type' parameter found
        in the tree who's parent node is the 'node' parameter.

        Args:
            node: The parent node to start from.
            type: A class which extends Node.
            list: Initially set to [], used to pass the
                list around so that matches can be appended
                to it.
        '''

        if list is None:
            list = []

        for child in node.children:
            if isinstance(child, Node):
                if isinstance(child, type):
                    list.append(child)
                Node.filter_to_list(type, child, list)

        return list


    @staticmethod
    def is_name(string):
        '''
        Returns True, if the string parameter is a grammar defined NAME token

        Args:
            string: str to validate
        '''
        if not isinstance(string, basestring):
            # Name tokens must be a str object.
            return False
        else:
            if not string:
                #Name tokens cannot be empty str object.
                return False

            if not string[0].isalpha() and string[0] != "_":
                #Name tokens must begin with an alpha character
                return False

            for char in string[1:]:
                if not char.isalpha() and char != "_" and not char.isdigit():
                    return False

        return True


    @staticmethod
    def unique_identifier(expressionStr, identifier):
        '''
        Returns a unique identifier protecting against collisions with
        'identifier' with identifiers found in 'expression'
        '''
        if expressionStr.find(identifier) == -1:
            return identifier

        keepTrying = True

        while (keepTrying):
            collisionProtectedIdentifier = ((identifier + "_") if identifier else "") + str(uuid.uuid1()).replace("-", "_")
            if expressionStr.find(collisionProtectedIdentifier) == -1:
                keepTrying = False

        return collisionProtectedIdentifier



# S P E C I F I C   N O D E   C L A S S E S

class Policy(Node):
    '''
    A Policy node. The entrant Node for the Policy DSL.
    Meaning: you start here to reason...
    '''


    def __str__(self):
        '''
        Returns a str representation of the policy.
        '''
        value = ""

        for child in self.children:
            value += str(child) + "\n"

        return value


    def __init__(self, children=None, line=None, column=None):

        super(Policy, self).__init__(children, line, column)

        self._intellect = None
        self._globals = {}
        self._halt = False


    @property
    def intellect(self):
        '''
        Returns the associated Intellect object executing the policy.
        '''
        return self._intellect


    @intellect.setter
    def intellect(self, value):
        '''
        Associates the Intellect object executing the policy to the policy so
        that the policy can call its methods, etc...
        '''
        if isinstance(value, reflection.class_from_str("intellect.Intellect.Intellect")):
            self._intellect = value
        else:
            raise TypeError("'intellect' must be of type Intellect.")


    @property
    def globals(self):
        '''
        Returns the policy's globals.

        Contains both imports and policy attributes.
        '''
        return self._globals


    @globals.setter
    def globals(self, value):
        '''
        Sets the policy's globals.
        '''
        if isinstance(value, dict):
            self._globals = value
        else:
            raise TypeError("'globals' must be of type dictionary.")


    @property
    def halt(self):
        '''
        Returns the policy's halt flag.
        '''
        return self._halt


    @halt.setter
    def halt(self, value):
        '''
        Sets the policy's halt flag.
        '''
        if isinstance(value, bool):
            self._halt = value
        else:
            raise TypeError("'halt' must be of type bool.")


    @property
    def files(self):
        '''
        A convenience method to return all the policy files
        comprising the policy.  Otherwise, once could simply
        call the children properties method on this instance.
        Calling this just makes the code more readable.
        '''
        return self.children


    @files.setter
    def files(self, value):
        '''
        A convenience method to set the policy files
        comprising the policy.  Otherwise, once could simply
        call the children setter method on this instance.
        Calling this just makes the code more readable.
        '''
        self.children = value


    @property
    def file_paths(self):
        '''
        A convenience method to return the policy file paths
        as a list.

        None is returned for file nodes learned from strings.
        '''
        return [file_node.path for file_node in self.files]


    @property
    def importStmts(self):
        '''
        Returns either an empty list or a list containing
        one or more ImportStmt objects
        '''

        importStmts = []

        for file in self.files:
            importStmts.extend(file.importStmts)

        return importStmts


    @property
    def ruleStmts(self):
        '''
        Returns either an empty list or a list containing
        one or more RuleStmt objects
        '''
        ruleStmts = []

        for file in self.files:
            ruleStmts.extend(file.ruleStmts)

        return ruleStmts


    @property
    def attributeStmts(self):
        '''
        Returns either an empty list or a list containing
        one or more AttributeStmts
        '''
        attributeStmts = []

        for file in self.files:
            attributeStmts.extend(file.attributeStmts)

        return attributeStmts


    def eval(self, agenda):
        '''
        Eval the policy
        '''

        # reset halt to false
        self.halt = False

        if not isinstance(agenda, (list, types.NoneType)):
            raise TypeError("Parameter 'agenda' must be a List or NoneType.")

        if not agenda:
            agenda = ["MAIN"]

        self.log("agenda: {0}".format(agenda))

        # put the imports into the policy's global namespace
        for importStmt in self.importStmts:
            try:
                self.log("Evaluating: {0}".format(importStmt))
                exec(str(importStmt), self.globals)
            except ImportError as error:
                exception_type, exception_value, exception_traceback = sys.exc_info()
                raise ImportError(error.message + " at line: {0} from policy file: '{1}'".format(importStmt.line, importStmt.file.path), exception_type, exception_value), None, exception_traceback

        # put the policy attributes into the policy's global namespace
        for attributeStmt in self.attributeStmts:
            # check for issues
            for atom in [atom for atom in Node.filter_to_list(Atom, attributeStmt.expressionStmt.children[0]) if len(atom.children) is 1]:
                if atom.first_child() in keyword.kwlist:
                    raise SyntaxError("invalid syntax:  global '{0}' is a reserved keyword: {1} from policy file: '{2}'.".format(atom.first_child(), attributeStmt.line, atom.file.path))

            # add globals to the namespace
            self.log("Evaluating: {0}".format(attributeStmt))
            exec(str(attributeStmt), self.globals)

        if self.ruleStmts:

            self.log("Evaluating ruleStmts")

            # fire the rules in order according to the agenda
            # until all fired or told to halt
            for agenda_group in agenda:

                iterator = iter(self.ruleStmts)

                while not self.halt:
                    try:
                        ruleStmt = iterator.next()
                    except StopIteration:
                        break

                    if (ruleStmt.agenda_group_id == agenda_group):
                        self.log("Evaluating: '{0}' from agenda group '{1}'".format(ruleStmt.id, ruleStmt.agenda_group_id))
                        ruleStmt.eval(self)
                    else:
                        self.log("Ignoring: '{0}' from agenda group '{1}' as it is not on the agenda".format(ruleStmt.id, ruleStmt.agenda_group_id))
                else:
                    self.log("Halting...")


class File(Node):
    '''
    A File Node containing zero or more ImportStmt or
    RuleStmt nodes.
    '''

    def __init__(self, children=None, line=None, column=None):

        super(File, self).__init__(children, line, column)

        self._path = None

    @property
    def path(self):
        '''
        Returns source file path this node is contained in
        '''
        return self._path


    @path.setter
    def path(self, value):
        '''
        Sets the source file path this node is contained in.
        None if created from dynamically from string.
        '''
        if isinstance(value, (basestring, types.NoneType)):
            self._path = value
        else:
            raise TypeError("'path' must be of type string or None.")


    @property
    def importStmts(self):
        '''
        Returns either an empty list or a list containing
        one or more ImportStmt objects
        '''
        return [child.first_child() for child in self.children if isinstance(child.first_child(), ImportStmt)]


    @property
    def ruleStmts(self):
        '''
        Returns either an empty list or a list containing
        one or more RuleStmt objects
        '''
        return [child.first_child() for child in self.children if isinstance(child.first_child(), RuleStmt)]


    @property
    def attributeStmts(self):
        '''
        Returns either an empty list or a list containing
        one or more AttributeStmts
        '''
        return [child.first_child() for child in self.children if isinstance(child.first_child(), AttributeStmt)]



    @staticmethod
    def set_file_on_descendants(node=None, file_node=None):
        '''
        Sets this node's file property and all its descendants'
        file property to file_node.
        '''

        if not isinstance(node, (Node, types.NoneType)):
            raise TypeError("'node' must be of type Node.")

        node.file = file_node

        for child in node.children:
            if isinstance(child, Node):
                child.file = file_node
                File.set_file_on_descendants(child, file_node)


class Statement(Node):
    '''
    A Statement Node containing an import or global or rule statement
    '''



class AttributeStmt(Statement):
    '''
    An AttributeStmt (Attribute Statement) Node for a Policy Node
    '''

    @property
    def expressionStmt(self):
        '''
        Returns the ExpressionStmt object for the global.
        '''
        return self.children[0]



class RuleStmt(Statement):
    '''
    A RuleStmt (Rule Statement) Node for a Policy Node
    '''

    def __str__(self):
        '''
        Returns a str representation of RuleStmt as it would be written in a policy.
        '''

        when = self.filter_to_list(When, self)
        then = self.filter_to_list(Then, self)

        print "when : {0}".format(when)
        print "then : {0}".format(then)

        value = "rule {0}:\n".format(self.children[1])

        if when != []:
            for line in str(when[0]).splitlines():
                value += "\t" + line + "\n"

        for line in str(then[0]).splitlines():
            value += "\t" + line + "\n"

        return value


    @property
    def id(self):
        '''
        Returns the Id object for the rule.
        '''
        return self.children[1]


    @property
    def ruleAttributes(self):
        '''
        Returns the RuleAttribute nodes associated with this rule.
        '''
        return [child for child in self.children if isinstance(child, RuleAttribute)]


    @property
    def agenda_group_id(self):
        '''
        Returns the agenda_group id for the rule.
        '''

        if self.ruleAttributes:
            agenda_group = [attribute.children[0] for attribute in self.ruleAttributes if isinstance(attribute.children[0], AgendaGroup)]

            if agenda_group:
                # the last one defined wins
                return str(agenda_group[-1].id)

        # otherwise return default
        return "MAIN"


    @property
    def when(self):
        '''
        Returns the When node, if it exists otherwise None as the When node
        is optional as per the grammar.
        '''
        whenChild = [child for child in self.children if isinstance(child, When)]

        if not whenChild:
            return None
        else:
            return whenChild[0]


    @property
    def then(self):
        '''
        Returns the mandatory Then node.
        '''
        return [child for child in self.children if isinstance(child, Then)][0]


    def eval(self, policy):
        '''
        Evaluate the RuleStmt over known objects held within the associated
        Intellect object.
        '''
        self.log("Evaluating rule: '{0}' from policy file: '{1}'".format(self.id, self.file.path))

        if self.when:
            whenResults = self.when.eval(policy, self)
        else:
            # Automatically fire the Then portion of the rule, if no When
            # portion exists.
            Result = collections.namedtuple('Result', 'fireThen, matches, objectBinding')

            whenResults = Result(fireThen=True, matches=[], objectBinding=None)

        self.log("When results for '{0}':  {1}".format(self.id, whenResults))

        if whenResults.fireThen:
            # fire the Then portion of the rule
            self.then.eval(policy, self, whenResults.matches, whenResults.objectBinding)
        else:
            self.log("When portion of {0} evaluated false, not firing Then portion".format(self.id))



class RuleAttribute(Node):
    '''
    A RuleAttribute Node containing an AgendaGroup attribute for a Rule Statement
    '''



class AgendaGroup(Node):
    '''
    An AgendaGroup Node
    '''

    @property
    def id(self):
        '''
        Returns the Id object for the AgendaGroup.
        '''
        return self.children[1]



class When(Node):
    '''
    A When Node for a RuleStmt Node.
    '''
    def __str__(self):
        '''
        Returns a str representation of When as it would be written in a policy.
        '''
        value = "when:\n"
        value += "\t{0}".format(self.ruleCondition)

        return value


    @property
    def ruleCondition(self):
        '''
        Returns a RuleCondition object.
        '''
        filter = [child for child in self.children if isinstance(child, RuleCondition)]

        if not filter:  # True, if filter is []
            return None
        else:
            return filter[0]


    @ruleCondition.setter
    def ruleCondition(self, value):
        raise NotImplementedError, "ruleCondition property cannot be set."


    def eval(self, policy, ruleStmt):
        '''
        Evaluate the when portion.
        '''

        # If True trigger the Then portion of the Rule; otherwise, don't.
        fireThen = False

        # Hold the learned object's matching the ClassConstraint.constraint
        matches = []

        # Holds the object binding for the ClassConstraint, if it exists;
        # otherwise is None
        objectBinding = None

        # Holds the Class-type described by ClassConstraint.name, if it exists;
        # otherwise is None
        klazz = None

        if self.ruleCondition:

            # The When portion of the rule has a RuleCondition

            classConstraint = self.ruleCondition.notCondition.condition.classConstraint

            #self.log(classConstraint.str_tree())

            # Determine the ClassConstraint.name'ed class-type
            klazz = reflection.class_from_string(classConstraint.name, policy)

            if classConstraint.constraint:

                # create 'localScope' dict and add 'policy' and 'klazz' to it
                localScope = {}
                localScope["policy"] = policy
                localScope["klazz"] = klazz

                # This is needed because for the reasons documented in reflection.is_instance
                localScope["reflection"] = reflection.module_from_str("intellect.reflection")

                # Rewrite the ClassConstraint.constraint
                rewrittenConstraint = When.rewrite(classConstraint.constraint, Constraint(), klazz)

                # Build the list comprehension used to filter the learned
                # objects down to matches for the ClassConstraint Constraint
                code = "matches = [fact for fact in policy.intellect.knowledge if "

                # Restrict the list comprehension to just the
                # ClassConstraint.name'ed class-type
                code += "reflection.is_instance(fact, klazz) and "

                # Append 'not' prior to the Constraint, if the negated
                code += "not (" if self.ruleCondition.notCondition.is_negated() else ""

                # Use the rewritten ClassConstraint Constraint to filter the
                # learned objects
                code += str(rewrittenConstraint) + (")" if self.ruleCondition.notCondition.is_negated() else "") + "]"

                self.log("Filter using the following list comprehension: {0}".format(code))

                try:
                    # Execute the dynamically built list comprehension code

                    self.log("policy.globals.keys = {0}".format(policy.globals.keys()))
                    self.log("localScope = {0}".format(localScope.keys()))
                    exec(code, policy.globals, localScope)

                    matches = localScope["matches"]

                except Exception as error:
                    exception_type, exception_value, exception_traceback = sys.exc_info()
                    raise SyntaxError, ("{0} in rule: '{1}', near line: {2} in policy file: '{3}'".format(error, ruleStmt.id, self.line, self.file.path), exception_type, exception_value), exception_traceback

                self.log("The matches found in memory: {0}".format(matches))
            else:
                # not having a ClassConstraint.constraint
                if not self.ruleCondition.notCondition.is_negated():
                    # match all the learned objects of ClassConstraint.name'ed class-type
                    self.log("match all the learned objects of ClassConstraint.name'ed class-type")
                    matches = [fact for fact in policy.intellect.knowledge if reflection.is_instance(fact, klazz)]
                else:
                    # match all the learned objects that are not the ClassConstraint.name'ed class -type
                    self.log("match all the learned objects that are not the ClassConstraint.name'ed class-type")
                    matches = [fact for fact in policy.intellect.knowledge if not reflection.is_instance(fact, klazz)]

                self.log("The matches found in memory: {0}".format(matches))

            if classConstraint.objectBinding:
                # hold the objectBinding, if it exists for later use
                objectBinding = classConstraint.objectBinding
                self.log("objectBinding is '{0}'".format(objectBinding))

            if self.ruleCondition.notCondition.condition.exists:
                #"The Condition holds an Exists token

                if not matches:
                    fireThen = False
                else:
                    # matches exist for the ClassConstraint.constraint,
                    # fire the Then portion of the rule
                    self.log("classConstraint prepended with 'exists'.")
                    fireThen = True
                    # the following no longer of relevance
                    matches = []
                    objectBinding = None
            else:
                # The Condition does not hold an Exists token
                if not matches:
                    fireThen = False
                    objectBinding = None
                else:
                    fireThen = True
        else:
            # The default is to fire then portion of the rule, if the When
            # portion of the rule has no RuleCondition
            fireThen = True

        # Create a new named tuple to hold the results
        Result = collections.namedtuple('Result', 'fireThen, matches, objectBinding')

        return Result(fireThen=fireThen, matches=matches, objectBinding=objectBinding)


    @staticmethod
    def rewrite(original, rewritten, klazz):
        '''
        A recursive method used to rewrite a Constraint object so that learned objects may
        be filtered.

        Args:
            original: Constraint to be rewritten.
            rewritten: used in recursion, the object to be written into.
            klazz: the object name by the ClassConstraint.name
        '''
        for child in original.children:
            if isinstance(child, Node):
                if isinstance(child, Power):
                    # inspect and rewrite, if necessary
                    if isinstance(child.first_child(), Atom) \
                        and Node.is_name(child.first_child().first_child()) \
                        and reflection.has_attribute(klazz, child.first_child().first_child()):
                        # The classConstraint.name used to signify the class the
                        # the constraint corresponds to has this (instance /
                        # class / static) method, property, or global.  So,
                        # rewrite the Constraint object by prepending "fact"
                        # before the first Atom object in this particular Power
                        # node.
                        #
                        # TODO: need a better string then "fact" as this may
                        # may already be used in the constraint
                        power = Power([Atom("fact"), Trailer([".", child.first_child().first_child()])])
                        rewritten.append_child(power)

                        if (len(child.children) > 1):
                            for c in child.children[1:]:
                                twin = type(c)()
                                power.append_child(When.rewrite(c, twin, klazz))
                    else:
                        # nothing matched to rewrite; so, clone
                        twin = type(child)()
                        rewritten.append_child(When.rewrite(child, twin, klazz))

                else:
                    # handle a child Node that is not of Power node
                    twin = type(child)()

                    rewritten.append_child(When.rewrite(child, twin, klazz))

            else:
                # handle a child that is a string
                rewritten.append_child(child)

        return rewritten



class Then(Node):
    '''
    A Then node for a RuleStmt Node.
    '''
    def __str__(self):
        '''
        Returns a str representation of Then as it would be written in a policy.
        '''
        value = "then:\n"

        for action in self.actions:
            for line in str(action).splitlines():
                value += "\t" + line + "\n"

        return value


    @property
    def actions(self):
        '''
        Returns a list of one one or more Action objects.
        '''
        return [child for child in self.children if isinstance(child, Action)]


    def eval(self, policy, ruleStmt, matches, objectBinding):
        '''
        Evaluate then portion.
        '''

        localScope = {}
        localScope["policy"] = policy

        # Insert into localScope all of Intellect's methods decorated as callable
        for method_name in [method_name for method_name in dir(policy.intellect) if isinstance(getattr(policy.intellect, method_name), Callable)]:
            if method_name in localScope:
                raise RuntimeWarning("'Intellect method {0}' is already in local scope of the Then portion of rule: '{1}', define near line: {2} in policy file: '{3}'.  Consider renaming method.".format(method_name, ruleStmt.id, ruleStmt.line, self.file.path))
            else:
                localScope[method_name] = getattr(policy.intellect, method_name)

        if matches != []:
            # fire each action in sequence for each match
            for match in matches:

                localScope["match"] = match

                # process the actions
                for action in self.actions:

                    # needed as the Action object wraps the actual Action
                    actualAction = action.action

                    if isinstance(actualAction, ForgetAction):
                        # search through the objects that have been learned
                        # and delete the match

                        policy.intellect.forget(match)

                    elif isinstance(actualAction, LearnAction):

                        # create a newObject with the arguments, if provided,
                        # and append it to learned objects in memory
                        #
                        # TODO: use of the identifier "newFact" may
                        # be a  problem down the road...
                        code = "new_fact" + " = " + actualAction.name + "(" + (str(actualAction.argList) if actualAction.argList != None else "") + ")"

                        self.log("Code to be run for learnAction in rule: '{0}' at line: {1} in the policy file: '{2}':\n{3}".format(ruleStmt.id, actualAction.line, self.file.path, code))

                        try:
                            # Execute the code
                            exec(str(code), policy.globals, localScope)
                        except Exception as error:
                            exception_type, exception_value, exception_traceback = sys.exc_info()
                            raise SyntaxError ("{0} in rule: '{1}' at line: {2} in the policy file: '{3}'".format(error, ruleStmt.id, actualAction.line, self.file.path), exception_type, exception_value), None, exception_traceback

                        policy.intellect.learn(localScope["new_fact"])

                    elif isinstance(actualAction, ModifyAction):

                        # enumerate through known objects looking for the
                        # match, once found modify it using the
                        # PropertyAssignments described by the
                        # ModifyAction statement
                        for knowledgeIndex, fact in enumerate(policy.intellect.knowledge):
                            # TODO: modify the line below
                            if id(match) == id(fact):

                                for propertyAssignment in actualAction.propertyAssignments:

                                    try:
                                        self.log("value" + " = " + str(Then.rewrite(propertyAssignment.constraint, Constraint(), objectBinding)))
                                        exec("value" + " = " + str(Then.rewrite(propertyAssignment.constraint, Constraint(), objectBinding)), policy.globals, localScope)
                                    except Exception as error:
                                        exception_type, exception_value, exception_traceback = sys.exc_info()
                                        raise SyntaxError("{0} in rule: '{1}' near line: {2} in the policy file: '{3}'".format(error, ruleStmt.id, actualAction.line, self.file.path), exception_type, exception_value), None, exception_traceback

                                    self.log("modifying {0} property {1} with value of {2} with assignment of {3}".format(objectBinding, propertyAssignment, localScope["value"], propertyAssignment.assignment))

                                    if (str(propertyAssignment.assignment) == "="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == "+="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) + localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == "-="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) - localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == "*="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) * localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == "/="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) / localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == "%="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) % localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == "&="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) & localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == "|="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) | localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == "^="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) ^ localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == "<<="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) << localScope["value"])
                                    elif  (str(propertyAssignment.assignment) == ">>="):
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) >> localScope["value"])
                                    else:
                                        setattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name, getattr(policy.intellect.knowledge[knowledgeIndex], propertyAssignment.name) // localScope["value"])

                                break

                    elif isinstance(actualAction, HaltAction):

                        policy.halt = True

                        self.log("Halt called in rule: '{0}' from policy file: '{1}'.".format(ruleStmt.id, self.file.path))

                        break

                    elif isinstance(actualAction, AttributeAction):

                        code = actualAction.write_prepend()
                        code += str(Then.rewrite(actualAction.children[1], SimpleStmt(), objectBinding))

                        self.execute(policy, ruleStmt, localScope, code)

                    else:

                        # Handle SimpleStmt

                        # Rewrite the statement
                        code = str(Then.rewrite(actualAction, SimpleStmt(), objectBinding))

                        self.execute(policy, ruleStmt, localScope, code)

        else:

            # fire each action in sequence, but only once

            for action in self.actions:

                # needed as the Action object wraps the actual Action
                actualAction = action.action

                if isinstance(actualAction, ForgetAction):

                    # As the ForgetAction acts on a specific match, one cannot
                    # have ForgetAction statements in then-portion of a rule
                    # who's when-portion evaluated on "exists".
                    raise SyntaxError("forgetAction cannot exist in then portion as when portion is written for '{0}' at line: {1} in Policy: {2}".format(ruleStmt.id, actualAction.line, self.file.path))

                elif isinstance(actualAction, LearnAction):

                    # create a newObject with the arguments, if provided,
                    # and append it to learned objects in memory
                    code = "new_fact" + " = " + actualAction.name + "(" + (str(actualAction.argList) if actualAction.argList != None else "") + ")"

                    self.log("Code to be run for learnAction in rule: '{0}' at line: {1} in the policy file: '{2}':\n{3}".format(ruleStmt.id, actualAction.line, self.file.path, code))

                    try:
                        # Execute the code
                        exec(str(code), policy.globals, localScope)
                    except Exception as error:
                        exception_value, exception_traceback = sys.exc_info()
                        raise SyntaxError("{0} in rule: '{1}' at line: {2} in the policy file: '{3}'".format(error, ruleStmt.id, actualAction.line, self.file.path), exception_type, exception_value), None, exception_traceback

                    policy.intellect.learn(localScope["new_fact"])

                elif isinstance(actualAction, ModifyAction):

                    # As the ModifyAction acts on a specific match, one cannot
                    # have ModifyeAction statements in then-portion of a rule
                    # who's when-portion evaluated on "exists".

                    raise SyntaxError("modifyAction cannot exist in then portion as when portion is written for '{0}' at line: {1} in Policy: {2}".format(ruleStmt.id, actualAction.line, self.file.path()))
                elif isinstance(actualAction, HaltAction):

                    policy.halt = True

                    self.log("Halt called in rule: '{0}' from policy file: '{1}'.".format(ruleStmt.id, self.file.path))

                    break

                elif isinstance(actualAction, AttributeAction):

                    code = actualAction.write_prepend()

                    # No rewriting is necessary as ObjectBindings are not used
                    # in Action statements when the when-portion evaluated on
                    # "exists".
                    code += str(actualAction.children[1])

                    self.execute(policy, ruleStmt, localScope, code)

                else:
                    # Handle SimpleStmt

                    # No rewriting is necessary as ObjectBindings are not used
                    # in Action statements when the when-portion evaluated on
                    # "exists".
                    code = str(actualAction)
                    self.execute(policy, ruleStmt, localScope, code)


    def execute(self, policy, ruleStmt, localScope, code):
        '''
        Executes the code
        '''

        self.log("Code to be run for simpleStatement in rule: '{0}' near line: {1} in the policy file: '{2}':\n{3}".format(ruleStmt.id, self.line, self.file.path, code))

        try:
            # Execute the code, wrapped to collect stdout
            with IO.RedirectStdOut() as stdout:
                exec(str(code), policy.globals, localScope)

            print stdout.getvalue()

        except Exception, error:
            exception_type, exception_value, exception_traceback = sys.exc_info()
            raise RuntimeError("{0} in rule: '{1}' near line: {2} in the policy file: '{3}'".format(error, ruleStmt.id, self.line, self.file.path), exception_type, exception_value), None, exception_traceback


    @staticmethod
    def rewrite(original, rewritten, objectBinding):
        '''
        A recursive method used to rewrite a SimpleStmt object using
        the objectBinding

        Args:
            original: the Node to be rewritten
            rewritten: rewritten: used in recursion, the object to be written into.
            objectBinding: the objectBinding to be replaced with string "match"

        Returns:
            The rewritten Node
        '''
        for child in original.children:

            if isinstance(child, Node):

                if isinstance(child, Atom):

                    # inspect and rewrite, if necessary
                    if child.first_child() == objectBinding:
                        # Replace the Atom containing the objectBinding with
                        # with an Atom containing simply the str "match"
                        #
                        # TODO: need a better string then "match" as this may
                        # may already be used in the constraint
                        rewritten.append_child(Atom("match"))
                    else:
                        # nothing matched to rewrite; so, clone
                        twin = type(child)()
                        rewritten.append_child(Then.rewrite(child, twin, objectBinding))

                else:
                    # handle a child Node that is not of Power node
                    twin = type(child)()

                    rewritten.append_child(Then.rewrite(child, twin, objectBinding))

            else:
                # handle a child that is a string
                rewritten.append_child(child)

        return rewritten



class Id(Node):
    '''
    A ID Node for a RuleStmt (Rule Statement) of GlobalStmt (Global Statement) Node.
    '''

    def __str__(self):
        '''
        A str representation of the node.

        Quotes around Strings are stripped.
        '''
        return str(self.first_child()).strip('"')



class RuleCondition(Node):
    '''
    A RuleCondition node for a RuleStmt node.
    '''

    @property
    def notCondition(self):
        return self.first_child()



class NotCondition(Node):
    '''
    A NotCondition node.
    '''

    def is_negated(self):
        '''
        Returns True if the Condition object is negated;
        otherwise, False.
        '''
        value = False

        for child in self.children:
            if (child == "not"):
                value = not value
            else:
                break

        return value


    @property
    def condition(self):
        '''
        Returns the Condition object
        '''
        return [child for child in self.children if isinstance(child, Condition)][0]



class Condition(Node):
    '''
    A Condition node.
    '''

    @property
    def exists(self):
        '''
        Returns to true if the ClassConstraint is prepended with "exists"
        '''
        return self.first_child() == "exists"


    @property
    def classConstraint(self):
        '''
        Returns the ClassConstraint object
        '''
        return [child for child in self.children if isinstance(child, ClassConstraint)][0]



class ClassConstraint(Node):
    '''
    A ClassConstraint node.
    '''

    @property
    def objectBinding(self):
        '''
        Return an objectBinding str, if one exists otherwise None
        '''
        if isinstance(self.first_child(), basestring) and self.first_child().startswith("$"):
            return self.first_child()
        else:
            return None


    @property
    def name(self):
        '''
        Returns the class name (as per the grammar a ClassConstraint must have one.)
        '''
        if self.children[1] == ":=":
            return self.children[2]
        else:
            return self.first_child()


    @property
    def constraint(self):
        '''
        Returns a Constraint object, if one exists otherwise None
        '''
        filtered = [child for child in self.children if isinstance(child, Constraint)]

        if not filtered:  # True, if filtered is []
            return None
        else:
            return filtered[0]



class Action(Node):
    '''
    An Action node.
    '''
    def __str__(self):
        '''
        Returns a str representation of Action as it would be written in a policy.
        '''
        value = str(self.action)

        return value


    @property
    def action(self):
        '''
        Returns either a ForgetAction, LearnAction, ModifyAction, or SimpleStmt
        object
        '''
        return self.first_child()



class SimpleStmt(Node):
    '''
    A SimpleStmt node.
    '''



class PrintStmt(Node):
    '''
    A PrintStmt node.
    '''



class AttributeAction(Node):
    '''
    An AttributeAction node.
    '''


    @property
    def expressionStmt(self):
        '''
        Returns the ExpressionStmt object for the attribute action.
        '''
        return self.children[1]


    def write_prepend(self):
        """
        Writes a prepend for the statement to allow it to be processed by a Python exec statement
        """
        returnStmt = "global "

        for object_reference in [atom.first_child() for atom in Node.filter_to_list(Atom, self.expressionStmt.children[0]) if len(atom.children) is 1]:
            returnStmt += object_reference + ", "

        return ("; ").join(returnStmt.rsplit(", ", 1))



class ForgetAction(Node):
    '''
    A ForgetAction node.
    '''
    @property
    def objectBinding(self):
        '''
        Returns a str representing the object binding to be forgotten/deleted
        '''
        return self.children[1]



class LearnAction(Node):
    '''
    An LearnAction node.
    '''
    @property
    def name(self):
        '''
        Returns the identifier of the object to be learned/inserted
        '''
        return self.children[1]


    @property
    def argList(self):
        '''
        Returns an ArgList object, if one exists otherwise None
        '''
        filtered = [child for child in self.children if isinstance(child, ArgumentList)]

        if not filtered:  # True, if filtered is []
            return None
        else:
            return filtered[0]



class ModifyAction(Node):
    '''
    A ModifyAction node.
    '''

    def __str__(self):
        '''
        Returns a str representation of Modify as it would be written in a policy.
        '''
        value = "modify {0}:\n".format(self.objectBinding)

        for propertyAssignment in self.propertyAssignments:
            value += "\t{0}\n".format(propertyAssignment)

        return value


    @property
    def objectBinding(self):
        '''
        Returns a str representing the object binding
        '''
        return self.children[1]


    @property
    def propertyAssignments(self):
        '''
        Returns a list of PropertyAssignment nodes
        '''
        return [child for child in self.children if isinstance(child, PropertyAssignment)]



class HaltAction(Node):
    '''
    A HaltAction node.
    '''


class PropertyAssignment(Node):
    '''
    A PropertyAssignment.
    '''

    @property
    def name(self):
        '''
        Returns the name of the property
        '''
        return self.first_child()


    @property
    def assignment(self):
        '''
        Returns an Assignment object
        '''
        return self.children[1]


    @property
    def constraint(self):
        '''
        Returns a Constraint object
        '''
        return self.children[2]



class ExpressionStmt(Node):
    '''
    An ExpressionStmt node.
    '''



class Assignment(Node):
    '''
    An Assignment node.
    '''



class ImportStmt(Node):
    '''
    An ImportStmt node
    '''

    @property
    def importStmt(self):
        return self.first_child()



class ImportName(Node):
    '''
    An ImportName node/
    '''

    @property
    def dottedAsNames(self):
        '''
        returns DottedAsNames object
        '''
        return self.children[1]



class ImportFrom(Node):
    '''
    An ImportFrom node
    '''

    @property
    def dottedName(self):
        '''
        returns DottedName object
        '''
        return self.children[1]


    @property
    def importAsNames(self):
        '''
        returns ImportAsNames object
        '''
        return [child for child in self.children if isinstance(child, ImportAsNames)][0]



class ImportAsNames(Node):
    '''
    An ImportAsNames node
    '''

    @property
    def importAsNames(self):
        '''
        Returns a list of ImportAsName objects
        '''
        return [child for child in self.children if isinstance(child, ImportAsName)]



class ImportAsName(Node):
    '''
    An ImportAsName node
    '''

    @property
    def identifier(self):
        '''
        Returns the source identifier/name of the class
        '''
        return self.first_child();


    @property
    def localName(self):
        '''
        Returns the local name used in the policy to refer to the class,
        or None meaning there is no local name.
        '''
        if len(self.children) == 3:
            return self.children[2]
        else:
            return None



class DottedAsNames(Node):
    '''
    A DottedAsNames node.
    '''

    @property
    def dottedAsNames(self):
        '''
        Returns a list of DottedAsName objects
        '''
        return [child for child in self.children if isinstance(child, DottedAsName)]



class DottedAsName(Node):
    '''
    A DottedAsName node.
    '''

    @property
    def dottedName(self):
        '''
        Returns a DottedName object
        '''
        return self.first_child();


    @property
    def localName(self):
        '''
        Returns the local name used in the policy to refer to the module,
        or None meaning there is no local name.
        '''
        if len(self.children) == 3:
            return self.children[2]
        else:
            return None



class DottedName(Node):
    '''
    A DottedName node.
    '''

    def __str__(self):
        '''
        returns dotted name as a string w/ no spaces around the dots
        '''
        return "".join(self.children)



class Constraint(Node):
    '''
    A Constraint node.
    '''



class OrConstraint(Node):
    '''
    An OrConstraint node.
    '''



class AndConstraint(Node):
    '''
    An AndConstraint node.
    '''



class NotConstraint(Node):
    '''
    A NotConstraint node.
    '''



class Comparison(Node):
    '''
    A Comparison node.
    '''



class ComparisonOperation(Node):
    '''
    A ComparisonOperation node.
    '''



class Expression(Node):
    '''
    An Expression node.
    '''



class BitwiseOrExpr(Node):
    '''
    A BitwiseOrExpr node.
    '''



class BitwiseXorExpr(Node):
    '''
    A BitwiseXorExpr node.
    '''



class BitwiseAndExpr(Node):
    '''
    A BitwiseAndExpr node.
    '''



class ShiftExpr(Node):
    '''
    A ShiftExpr node.
    '''



class ArithExpr(Node):
    '''
    A ArithExpr node.
    '''



class Term(Node):
    '''
    A Term node.
    '''



class Factor(Node):
    '''
    A Factor node.
    '''



class Power(Node):
    '''
    A Power node.
    '''

    def __str__(self):
        '''
        Returns a str for this the node and its children for what they represent
        in the policy.
        '''
        value = ""

        for child in self.children:
            value += str(child)

        return value


    @property
    def atom(self):
        '''
        Returns Atom object
        '''
        return self.first_child()


    @property
    def trailers(self):
        '''
        Return list of Trailer objects
        '''
        return [child for child in self.children if isinstance(child, Trailer)]


    @property
    def factor(self):
        '''
        Returns a Factor object, if one exists otherwise None
        '''
        filtered = [child for child in self.children if isinstance(child, Factor)]

        if not filtered:  # True, if filtered is []
            return None
        else:
            return filtered[0]



class Atom(Node):
    '''
    An Atom node.
    '''
    def __str__(self):
        '''
        Returns a str for this the node and its children for what they represent
        in the policy.
        '''
        value = ""

        for child in self.children:
            value += str(child)

        return value



class ListMaker(Node):
    '''
    A ListMaker node.
    '''
    def __str__(self):
        '''
        Returns a str representation of ListMaker as it would be written in a
        policy.
        '''
        value = ""

        for child in self.children:

            value += str(child)

            if (child == ","):
                value += " "

        value = value.rstrip()

        return value



class ComparisonList(Node):
    '''
    A ComparisonList node.
    '''

    def __str__(self):
        '''
        Returns a str representation of ComparisonList as it would be written
        in a policy.
        '''
        value = ""

        for child in self.children:

            value += str(child)

            if (child == ","):
                value += " "

        value = value.rstrip()

        return value



class Trailer(Node):
    '''
    A Trailer node.
    '''
    def __str__(self):
        '''
        Returns a str for this the node and its children for what they represent
        in the policy.
        '''
        value = ""

        for child in self.children:
            value += str(child)

        return value



class ExpressionList(Node):
    '''
    An ExpressionList Node.
    '''



class DictMaker(Node):
    '''
    A DictMaker node.
    '''



class ArgumentList(Node):
    '''
    An Argumentlist node.
    '''

    def __str__(self):
        '''
        Returns a str representation of ArgumentList as it would be written in a
        policy.
        '''
        value = ""

        for child in self.children:

            value += str(child)

            if (child == ","):
                value += " "

        value = value.rstrip()

        return value

########NEW FILE########
__FILENAME__ = PolicyLexer
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from intellect.grammar.PolicyLexer import PolicyLexer as AutoGeneratedLexer


class PolicyLexer(AutoGeneratedLexer):

    def nextToken(self):
        self.startPosition = self.getCharPositionInLine()
        return AutoGeneratedLexer.nextToken(self)


########NEW FILE########
__FILENAME__ = PolicyTokenSource
"""
Copyright (c) 2004 Terence Parr and Loring Craymer
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
 1. Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
 2. Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.
 3. The name of the author may not be used to endorse or promote products
    derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from antlr3.tokens import ClassicToken, EOF
from antlr3.recognizers import TokenSource

from intellect.grammar.PolicyParser import INDENT, DEDENT
from intellect.grammar.PolicyLexer import NEWLINE, LEADING_WS


class PolicyTokenSource(TokenSource):

    """
    Python does not explicitly provide begin and end nesting signals.
    Rather, the indentation level indicates when you begin and end.
    This is an interesting lexical problem because multiple DEDENT
    tokens should be sent to the parser sometimes without a corresponding
    input symbol!  Consider the following example:

    a=1
    if a>1:
        print a
    b=3

    Here the "b" token on the left edge signals that a DEDENT is needed
    after the "print a \n" and before the "b".  The sequence should be

    ... 1 COLON NEWLINE INDENT PRINT a NEWLINE DEDENT b ASSIGN 3 ...

    For more examples, see the big comment at the bottom of this file.

    This TokenStream normally just passes tokens through to the parser.
    Upon NEWLINE token from the lexer, however, an INDENT or DEDENT token
    may need to be sent to the parser.  The NEWLINE is the trigger for
    this class to do it's job.  NEWLINE is saved and then the first token
    of the next line is examined.  If non-leading-whitespace token,
    then check against stack for indent vs dedent.  If LEADING_WS, then
    the column of the next non-whitespace token will dictate indent vs
    dedent.  The column of the next real token is number of spaces
    in the LEADING_WS token + 1 (to move past the whitespace).  The
    lexer grammar must set the text of the LEADING_WS token to be
    the proper number of spaces (and do tab conversion etc...).

    A stack of column numbers is tracked and used to detect changes
    in indent level from one token to the next.

    A queue of tokens is built up to hold multiple DEDENT tokens that
    are generated.  Before asking the lexer for another token via
    nextToken(), the queue is flushed first one token at a time.

    Terence Parr and Loring Craymer
    February 2004
    """

    FIRST_CHAR_POSITION = 0

    def __init__(self, stream):

        # The stack of indent levels (column numbers)
        # "state" of indent level is FIRST_CHAR_POSITION

        self.indentStack = [self.FIRST_CHAR_POSITION]

        # The queue of tokens

        self.tokens = []

        # We pull real tokens from this lexer

        self.stream = stream

        self.lastTokenAddedIndex = -1

    def nextToken(self):
        """
            From http://www.python.org/doc/2.2.3/ref/indentation.html
    
         Before the first line of the file is read, a single zero is
         pushed on the stack; this will never be popped off again. The
         numbers pushed on the stack will always be strictly increasing
         from bottom to top. At the beginning of each logical line, the
         line's indentation level is compared to the top of the
         stack. If it is equal, nothing happens. If it is larger, it is
         pushed on the stack, and one INDENT token is generated. If it
         is smaller, it must be one of the numbers occurring on the
         stack; all numbers on the stack that are larger are popped
         off, and for each number popped off a DEDENT token is
         generated. At the end of the file, a DEDENT token is generated
         for each number remaining on the stack that is larger than
         zero.
    
            I use char position in line 0..n-1 instead.
    
            The DEDENTS possibly needed at EOF are gracefully handled by forcing
            EOF to have char pos 0 even though with UNIX it's hard to get EOF
            at a non left edge.
        """

        # if something in queue, just remove and return it

        if len(self.tokens) > 0:
            t = self.tokens.pop(0)
            return t

        self.insertImaginaryIndentDedentTokens()

        return self.nextToken()

    def insertImaginaryIndentDedentTokens(self):
        t = self.stream.LT(1)
        self.stream.consume()

        # if not a NEWLINE, doesn't signal indent/dedent work; just enqueue

        if t.getType() != NEWLINE:
            hiddenTokens = \
                self.stream.getTokens(self.lastTokenAddedIndex + 1,
                    t.getTokenIndex() - 1)

            if hiddenTokens is not None:
                self.tokens.extend(hiddenTokens)

            self.lastTokenAddedIndex = t.getTokenIndex()
            self.tokens.append(t)
            return

        # save NEWLINE in the queue
        # print "found newline: "+str(t)+" stack is "+self.stackString()

        hiddenTokens = self.stream.getTokens(self.lastTokenAddedIndex
                + 1, t.getTokenIndex() - 1)

        if hiddenTokens is not None:
            self.tokens.extend(hiddenTokens)

        self.lastTokenAddedIndex = t.getTokenIndex()
        self.tokens.append(t)

        # grab first token of next line

        t = self.stream.LT(1)
        self.stream.consume()

        # handle hidden tokens

        hiddenTokens = self.stream.getTokens(self.lastTokenAddedIndex
                + 1, t.getTokenIndex() - 1)

        if hiddenTokens is not None:
            self.tokens.extend(hiddenTokens)

        self.lastTokenAddedIndex = t.getTokenIndex()

        # compute cpos as the char pos of next non-WS token in line

        cpos = t.getCharPositionInLine()  # column dictates indent/dedent

        if t.getType() == EOF:
            cpos = -1  # pretend EOF always happens at left edge
        elif t.getType() == LEADING_WS:
            cpos = len(t.getText())

        # print "next token is: "+str(t)

        # compare to last indent level

        lastIndent = self.indentStack[-1]

        # print "cpos, lastIndent = "+str(cpos)+", "+str(lastIndent)

        if cpos > lastIndent:  # they indented; track and gen INDENT
            self.indentStack.append(cpos)

            # print self.indentStack
            # print "push("+str(cpos)+"): "+self.stackString()

            indent = ClassicToken(INDENT, '')
            indent.setCharPositionInLine(t.getCharPositionInLine())
            indent.setLine(t.getLine())
            self.tokens.append(indent)
        elif cpos < lastIndent:

                                # they dedented
            # how far back did we dedent?

            prevIndex = self.findPreviousIndent(cpos)

            # print "dedented; prevIndex of cpos="+str(cpos)+" is "+str(prevIndex)

            # generate DEDENTs for each indent level we backed up over

            while len(self.indentStack) > prevIndex + 1:
                dedent = ClassicToken(DEDENT, '')
                dedent.setCharPositionInLine(t.getCharPositionInLine())
                dedent.setLine(t.getLine())
                self.tokens.append(dedent)

                self.indentStack.pop(-1)  # pop those off indent level

                # print self.indentStack

        if t.getType() != LEADING_WS:  # discard WS
            self.tokens.append(t)

    #  T O K E N  S T A C K  M E T H O D S

    def findPreviousIndent(self, i):
        '''
        Return the index on stack of previous indent level == i else -1
        '''

        for (j, pos) in reversed(list(enumerate(self.indentStack))):
            if pos == i:
                return j

        return self.FIRST_CHAR_POSITION

    def stackString(self):
        return ' '.join([str(i) for i in reversed(self.indentStack)])

########NEW FILE########
__FILENAME__ = reflection
"""
Copyright (c) 2011, The MITRE Corporation.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. All advertising materials mentioning features or use of this software
   must display the following acknowledgement:
   This product includes software developed by the author.
4. Neither the name of the author nor the
   names of its contributors may be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY
EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

"""
reflection

Description: Functions for performing introspection

Initial Version: Feb 1, 2011

@author: Michael Joseph Walsh
"""

import inspect, os, sys, types, logging

FUNCTION = "function"
BUILTIN_FUNCTION = "built-in function"
INSTANCE_METHOD = "instance method"
CLASS_METHOD = classmethod
STATIC_METHOD = staticmethod
PROPERTY = property
DATA = "data"

def log(msg, name="intellect", level=logging.DEBUG):
    '''
    Logs at the 'level' for the messaged 'msg'

    Args:
        name: the name of the logger
        level:  must be either logging.DEBUG, logging.INFO, logging.WARNING,
            logging.ERROR, logging.CRITICAL
        msg: message string
    '''

    if level not in [logging.DEBUG, logging.INFO, logging.WARNING,
            logging.ERROR, logging.CRITICAL]:
        raise ValueError("'level' must be either logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL")

    logging.getLogger(name).log(level, "{0} :: {1}".format(__name__, msg))


def is_method(klazz, name):
    '''
    does this class have this method?
    '''
    return (inspect_class_for_attribute(klazz, name)[0] in [INSTANCE_METHOD, CLASS_METHOD, STATIC_METHOD])


def has_attribute(klazz, name):
    '''
    does this class have this attribute in other words does it have this
    (instance/class/static) method, property, or global?
    '''
    return (inspect_class_for_attribute(klazz, name)) != (None, None, None)


def is_instance_method(klazz, name):
    '''
    does this class have this method?
    '''
    return (inspect(klazz, name)[0] is INSTANCE_METHOD)


def is_class_method(klazz, name):
    '''
    does this class have this class method?
    '''
    return (inspect_class_for_attribute(klazz, name)[0] is CLASS_METHOD)


def is_static_method(klazz, name):
    '''
    does this class have this static method?
    '''
    return (inspect_class_for_attribute(klazz, name)[0] is STATIC_METHOD)


def is_property(klazz, name):
    '''
    does this class have this property?
    '''
    return (inspect_class_for_attribute(klazz, name)[0] is PROPERTY)


def is_data(klazz, name):
    '''
    does this class have this global or attribute?
    '''
    return (inspect_class_for_attribute(object, name)[0] is DATA)


def inspect_class_for_attribute(klazz, name):
    '''
    For a given class inspects it for the existence of named instance/class/static method,
    property, and data element (global or attribute) attribute; and returns in tuple form
    (kind, obj, homeClass)
    '''

    if inspect.isclass(klazz):
        if name in dir(klazz):
            if name in klazz.__dict__:
                obj = klazz.__dict__[name]
            else:
                obj = getattr(klazz, name)

            homeClass = getattr(obj, "__objclass__", None)

            if homeClass is None:
                for base in inspect.getmro(klazz):
                    if name in base.__dict__:
                        homeClass = base
                        break

            if ((homeClass is not None) and (name in homeClass.__dict__)):
                obj = homeClass.__dict__[name]
                obj_via_getattr = getattr(klazz, name)

            if isinstance(obj, staticmethod):
                kind = staticmethod
            elif isinstance(obj, classmethod):
                kind = CLASS_METHOD
            elif isinstance(obj, property):
                kind = PROPERTY
            elif (inspect.ismethod(obj_via_getattr) or
                  inspect.ismethoddescriptor(obj_via_getattr)):
                kind = INSTANCE_METHOD
            else:
                kind = DATA

            return (kind, obj, homeClass)
        else:
            return (None, None, None)
    else:
        raise TypeError("parameter 'klazz' must a class object, not an instance of a class.")


def inspect_module_for_attribute(module, name):
    '''
    For a given module inspects it for the existence of named built-in,
    functions, and data attributes; and returns in tuple form
    (kind, obj)
    '''
    if inspect.ismodule(module):

        names = dir(module)

        if name in names:

            if name in module.__dict__:
                obj = module.__dict__[name]
            else:
                obj = getattr(module, name)

            if isinstance(obj, types.FunctionType):
                kind = FUNCTION
            elif isinstance(obj, types.BuiltinFunctionType):
                kind = BUILTIN_FUNCTION
            else:
                kind = DATA

            return (kind, obj)
        else:
            return (None, None, None)
    else:
        raise TypeError("parameter 'module' must be a Module, not an instance of a class, nor a Class.")


def for_class_list(klazz, type):
    '''
    A wrapper to for_object_list-method for evaluating just Class-type objects
    '''
    if inspect.isclass(klazz):
        return for_object_list(klazz, type)
    else:
        raise TypeError("parameter 'klazz' was not a Class, but an instance object.")


def for_object_list(object, type):
    '''
    For a given object inspects it for the existence of named instance/class/static method,
    property, and data element (global or attribute) attribute; and returns in tuple form
    (kind, obj, homeClass)
    '''
    value = []
    names = dir(object)

    for name in names:
        if name in object.__dict__:
            obj = object.__dict__[name]
        else:
            obj = getattr(object, name)

        homeClass = getattr(obj, "__objclass__", None)

        if homeClass is None:
            for base in inspect.getmro(object):
                if name in base.__dict__:
                    homeClass = base
                    break

        if ((homeClass is not None) and (name in homeClass.__dict__)):
            obj = homeClass.__dict__[name]
            obj_via_getattr = getattr(object, name)

        if isinstance(obj, staticmethod):
            kind = staticmethod
        elif isinstance(obj, classmethod):
            kind = CLASS_METHOD
        elif isinstance(obj, property):
            kind = PROPERTY
        elif (inspect.ismethod(obj_via_getattr) or
              inspect.ismethoddescriptor(obj_via_getattr)):
            kind = INSTANCE_METHOD
        else:
            kind = DATA

        print name, kind, obj

        if (kind is type):
            value.append(name)

    return value


def for_module_list(module, type):
    '''
    For a given module list either the built-in or data attributes.

    Example:

    for_module_list(__builtins__, BUILTIN)

    Will return a list of all the Python interpreter built-in functions

    '''

    value = []

    if inspect.ismodule(module):
        names = dir(module)

        for name in names:

            if name in module.__dict__:
                obj = module.__dict__[name]
            else:
                obj = getattr(module, name)

            if isinstance(obj, types.FunctionType):
                kind = FUNCTION
            elif isinstance(obj, types.BuiltinFunctionType):
                kind = BUILTIN_FUNCTION
            else:
                kind = DATA

            if (kind is type):
                value.append(name)

    return value


def class_from_string(className, policy):
    """
    Returns class object

    Args:
        className: A string holding either the class identifier or local name.
        policy: Policy providing ImportFrom objects to inspect.

    Raises:
        SyntaxError, if the class wasn't declared in a fromImport statement in the policy file
    """

    identifier = ""
    dottedName = ""

    importFromClass = class_from_str("intellect.Node.ImportFrom")

    importFroms = [importStmt.importStmt for importStmt in policy.importStmts if isinstance(importStmt.importStmt, importFromClass)]

    if not importFroms:
        raise SyntaxError("{0} was not declared in a importFrom statement in the policy file: '{1}'".format(className, policy.path))
    else:
        for importFrom in reversed(importFroms):
            for importAsName in reversed(importFrom.importAsNames.importAsNames):
                if importAsName.localName is not None and importAsName.localName == className:
                    # finding a match matching the localname for the className,
                    # hold the class's dottedName and identifier for later use
                    matchedImportFrom = importFrom # used for raising SyntaxError
                    dottedName = importFrom.dottedName
                    identifier = importAsName.identifier
                    break
                elif importAsName.localName is None and importAsName.identifier == className:
                    # finding a match matching the localname for the className,
                    # hold the class's dottedName and identifier for later use
                    matchedImportFrom = importFrom # used for raising SyntaxError
                    dottedName = importFrom.dottedName
                    identifier = importAsName.identifier
                    break

            if identifier:
                break

        if not identifier:
            # the className was not imported, raise a SyntaxError
            # TODO: include the line to assist the policy author
            raise SyntaxError("{0} was not declared in a fromImport statement in the policy file: '{1}'".format(className, policy.path))
        else:
            # otherwise return the class

            try:
                module = __import__(str(dottedName), globals(), locals(), [identifier])
            except ImportError as detail:
                raise SyntaxError("{0} at line: {1} in policy file: {2}".format(detail, matchedImportFrom.line, policy.path))

            try:
                klazz = getattr(module, identifier)
            except AttributeError:
                raise SyntaxError("'{0}' does not exist in module imported from at line: {1} in policy file: '{2}'".format(identifier, matchedImportFrom.line, policy.path))

            # return the class
            log("returning {0} for '{1}'".format(klazz, className))

            return klazz


def module_from_string(moduleName, policy):
    """
    Returns module object

    Args:
        module: A string holding either the module identifier or local name.
        policy: Policy providing ImportFrom objects to inspect.

    Raises:
        SyntaxError, if the module wasn't declared in a importName statement in the policy file
    """

    dottedName = ""

    importNameClass = class_from_str("intellect.Node.ImportName")

    importNames = [importStmt.importStmt for importStmt in policy.importStmts if isinstance(importStmt.importStmt, importNameClass)]

    if not importNames:
        raise SyntaxError("{0} was not declared in a importName statement in the policy file: '{1}'".format(moduleName, policy.path))
    else:
        for importName in importNames:

            # first check all the localNames
            for dottedAsName in importName.dottedAsNames.dottedAsNames:
                if dottedAsName.localName is not None and dottedAsName.localName == moduleName:
                    # finding a match matching the localname for the moduleName,
                    # hold the module's dottedName for later use
                    matchedImportName = importName # used for raising SyntaxError
                    dottedName = dottedAsName.dottedName
                    break
                elif dottedAsName.dottedName == moduleName:
                        # finding a matching identifier,
                        # hold the class's dottedName and identifier for later use
                        matchedImportName = importName # used for raising PolicyException
                        dottedName = moduleName
                        break

            if dottedName:
                break

        if not dottedName:
            # the className was not imported, raise a SyntaxError
            # TODO: include the line to assist the policy author
            raise SyntaxError("{0} was not declared in a importName statement in the policy file: '{1}'".format(moduleName, policy.path))
        else:
            # otherwise return the module
            try:
                # return the package object
                module = __import__(str(dottedName))
                # then dynamically load the module from the package
                components = str(dottedName).split('.')
                for comp in components[1:]:
                    module = getattr(module, comp)

            except ImportError as detail:
                raise SyntaxError("{0} at line: {1} in policy file: '{2}'".format(detail, matchedImportName.line, policy.path))

            # returning the module, not the package...
            log("returning a {0}".format(module))

            return module


def module_from_str(name):
    '''
    Returns a Module object from dottedName.identifier str such as
    'intellect.reflection'.
    '''
    module = sys.modules[name]

    log("returning {0} for {1}".format(module, name))
    return module


def class_from_str(name):
    '''
    Returns a Class object from dottedName.identifier str such as
    'intellect.Intellect.Intellect'.
    '''

    dottedName, identifier = name.rsplit('.', 1)
    module = __import__(str(dottedName), globals(), locals(), [identifier])
    klazz = getattr(module, identifier)

    log("returning {0} for {1}".format(klazz, name))
    return klazz


def is_instance(instance, klazz):
    '''
    If the python interpreter is running a module as the main program,
    instances of the classes define in the same module will be instances
    of the scope (__main__) instead of what is expected.
    
    So, more work is needed to determine if the instance is of type klazz
    
    Returns True or False
    
    Args:
        instance: An object instance to introspect
        klazz: a class object.
    '''

    log("instance = {0}".format(instance))
    log("klazz = {0}".format(klazz))

    value = isinstance(instance, klazz)

    log("value = {0}".format(value))

    if (not value):
        path = sys.modules[instance.__module__].__file__.rsplit(".", 1)[0]
        pathComponents = path.split(os.sep)
        moduleName = pathComponents[len(pathComponents) - 1]

        del pathComponents[len(pathComponents) - 1:]

        path = "".join(path.rsplit(moduleName, 1)).rstrip(os.sep)

        while True:
            if os.path.exists(path + os.sep + "__init__.py"):
                log("{0} has a __init__.py file".format(path))
                moduleComponent = pathComponents[len(pathComponents) - 1]
                moduleName = moduleComponent + "." + moduleName
                path = "".join(path.rsplit(moduleComponent, 1)).rstrip(os.sep)

                del pathComponents[len(pathComponents) - 1:]
            else:
                log("{0} doesn't have a __init__.py file".format(path))
                break

        value = ((moduleName + '.' + instance.__class__.__name__) == (klazz.__module__ + '.' + klazz.__name__))

        log("value = {0}".format(value))

    return value


########NEW FILE########
