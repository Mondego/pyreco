__FILENAME__ = enums
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class Actions(object):
    Select = "Select"
    SelectMany = "SelectMany"
    Count = "Count"
    Max = "Max"
    Min = "Min"
    Sum = "Sum"
    Avg = "Avg"

########NEW FILE########
__FILENAME__ = expressions
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.guard import Guard

class Expression(object):
    def evaluate(self):
        raise NotImplementedError("The evaluate method needs to be overriden in a base class of Expression.")

class ConstantExpression(Expression):
    def __init__(self, value):
        '''Initializes the ConstantExpression with the specified value.
        Arguments:
            value - Value to initialize the ConstantExpression with.
        '''
        self.value = value

    def evaluate(self):
        '''Returns the value for this constant expression.'''
        return self.value

    def __unicode__(self):
        return unicode("%s" % self.value)
    __str__ = __unicode__

class NameExpression(Expression):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.__unicode__()
        
    def __unicode__(self):
        return unicode(self.name)

class GetAttributeExpression(Expression):
    def __init__(self, *args):
        Guard.against_empty(args, "In order to create a new attribute expression you need to provide some attributes.")
        self.attributes = []
        self.add_attributes(args)

    def add_attributes(self, attrs):
        for attr in attrs:
            if isinstance(attr, GetAttributeExpression):
                self.add_attributes(attr.attributes)
            else:
                self.attributes.append(attr)

    def __unicode__(self):
        return unicode(".".join([str(attr) for attr in self.attributes]))
    __str__ = __unicode__

class UnaryExpression(Expression):
    #operation types
    CollectionLength = "CollectionLength"
    Negate = "Negate"
    Not = "Not"
    
    #operation representations
    representations = {
                        CollectionLength:"len(%s)",
                        Negate:"negate(%s)",
                        Not:"(not %s)",
                      }
                      
    def __init__(self, node_type, rhs):
        '''Initializes the UnaryExpression with the specified arguments.
        Arguments:
            node_type - Specifies the type of operation that this UnaryExpression represents
            rhs - Right-hand site of the operation. Since this is an unary operation, this is the only argument.
        '''
        Guard.against_empty(node_type, "The UnaryExpression node type is required")
        if node_type == self.CollectionLength:
            Guard.accepts(rhs, (ConstantExpression,), "The CollectionLength unary expression can only take ConstantExpressions that hold tuples or lists as parameters.")
            if not isinstance(rhs.evaluate(), (list, tuple)):
                raise ValueError("The CollectionLength unary expression can only take ConstantExpressions that hold tuples or lists as parameters.")
        self.node_type = node_type
        self.rhs = rhs

    def __str__(self):
        '''Returns a string representing the expression.'''
        return self.representations[self.node_type] % str(self.rhs)
    
class BinaryExpression(Expression):
    #operation types
    
    #Arithmetic
    Add = "Add"
    Subtract = "Subtract"
    Multiply = "Multiply"
    Divide = "Divide"
    Power = "Power"
    Modulo = "Modulo"
    
    #Bitwise
    And = "And"
    Or = "Or"
        
    #Comparison Operators
    Equal = "Equal"
    NotEqual = "NotEqual"
    GreaterThan = "GreaterThan"
    GreaterThanOrEqual = "GreaterThanOrEqual"
    LessThan = "LessThan"
    LessThanOrEqual = "LessThanOrEqual"
    
    #operation representations
    representations = {
                        Add:"+",
                        Subtract:"-",
                        Multiply:"*",
                        Divide:"/",
                        Power:"**",
                        Modulo:"%",
                        And:"and",
                        Or: "or",
                        Equal: "==",
                        NotEqual: "!=",
                        GreaterThan: ">",
                        GreaterThanOrEqual: ">=",
                        LessThan: "<",
                        LessThanOrEqual: "<=",
                      }
    
    def __init__(self, node_type, lhs, rhs):
        '''Initializes the BinaryExpression with the specified arguments.
        Arguments:
            node_type - Specifies the type of operation that this BinaryExpression represents
            lhs - Left-hand side of the operation (as in the first argument)
            rhs - Right-hand site of the operation (as in the second argument)
        '''
        Guard.against_empty(node_type, "The BinaryExpression node type is required")
        Guard.accepts(lhs, (Expression,), "Lhs must be an expression (an instance of a class that inherits from pynq.Expression), but was %s" % lhs.__class__.__name__)
        Guard.accepts(rhs, (Expression,), "Rhs must be an expression (an instance of a class that inherits from pynq.Expression) but was %s" % rhs.__class__.__name__)
        self.node_type = node_type
        self.lhs = lhs
        self.rhs = rhs

    def __str__(self):
        '''Returns a string representing the expression.'''
        return "(%s %s %s)" % (str(self.lhs), 
                           self.representations[self.node_type], 
                           str(self.rhs))
                           

########NEW FILE########
__FILENAME__ = guard
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class Guard(object):
    @classmethod
    def against_empty(cls, argument, message=None):
        if argument is None or str(argument) == "":
            raise ValueError(message and message or "One of the arguments is required and was not filled.")
        if isinstance(argument, (list, tuple, dict)) and (not argument or not any(argument)):
            raise ValueError(message and message or "One of the arguments is required and was not filled.")
    
    @classmethod
    def against_none(cls, argument, message=None):
        if argument is None:
            raise ValueError(message and message or "One of the arguments is required and was not filled.")

    @classmethod
    def accepts(cls, argument, types, message=None):
        argument_is_of_types = False
        for argument_type in types:
            if isinstance(argument, argument_type):
                argument_is_of_types = True
                break

        if not argument_is_of_types:
            error_message = "One of the arguments should be of types %s and it isn't."
            raise ValueError(message and message or error_message % ", ".join([str(tp) for tp in types]))

    @classmethod
    def accepts_only(cls, arguments, types, message=None):
        all_arguments_are_of_type = True
        
        for argument in arguments:
            argument_is_of_types = False
            for argument_type in types:
                if isinstance(argument, argument_type):
                    argument_is_of_types = True
                    break
            if not argument_is_of_types:
                all_arguments_are_of_type = False
                break
        
        if not all_arguments_are_of_type:
            error_message = u"All arguments in the given collection should be of type(s) [%s] and at least one of them isn't."
            raise ValueError(message and message or error_message % ", ".join([tp.__name__ for tp in types]))


########NEW FILE########
__FILENAME__ = parser
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tokenize
from cStringIO import StringIO
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import ConstantExpression, BinaryExpression
from pynq.expressions import UnaryExpression, NameExpression, GetAttributeExpression

class ExpressionParser(object):
    def __init__(self):
        self.operators = {
            "+":OperatorAddToken,
            "-":OperatorSubToken,
            "*":OperatorMulToken,
            "/":OperatorDivToken,
            "%":OperatorModToken,
            "**":OperatorPowerToken,
            "and":OperatorAndToken,
            "or":OperatorOrToken,
            "==":OperatorEqualToken,
            "!=":OperatorNotEqualToken,
            ">":OperatorGreaterThanToken,
            ">=":OperatorGreaterThanOrEqualToken,
            "<":OperatorLessThanToken,
            "<=":OperatorLessThanOrEqualToken,
            "not":OperatorNotToken,
            ".":DotToken,
            "(":LeftParenthesisToken,
        }
    
    def advance(self, id=None):
        global token
        if id and token.id != id:
            raise SyntaxError("Expected %r" % id)
        token = next()
    
    def expression(self, rbp=0):
        global token
        t = token
        token = next()
        left = t.nud()

        while isinstance(left, RightParenthesisToken):
            token = next()
            left = t.nud()

        while rbp < token.lbp:
            t = token
            token = next()
            left = t.led(left)
        return left

    def parse(self, program):
        global token, next
        next = self.__tokenize(program).next
        token = next()
        return self.expression()

    def __tokenize(self, program):
        for id, value in self.__tokenize_python(program):
            if id == "(literal)":
                yield LiteralToken(id, self.expression, self.advance, value)
            elif value == ")":
                yield RightParenthesisToken(")", self.expression, self.advance)
            elif id == "(operator)" and self.operators.has_key(value):
                yield self.operators[value](id, self.expression, self.advance)
            elif id == "(end)":
                yield end_token(id, self.expression, self.advance)
            elif id == "(name)":
                yield NameToken(id, self.expression, self.advance, value)
            else:
                raise SyntaxError("unknown operator: %r %r" % (id, value))

    def __tokenize_python(self, program):
        type_map = {
            tokenize.NUMBER: "(literal)",
            tokenize.STRING: "(literal)",
            tokenize.OP: "(operator)",
            tokenize.NAME: "(name)",
        }
        
        special_operators = ("and","or","not")
        
        for t in tokenize.generate_tokens(StringIO(program).next):
            try:
                if t[0] == tokenize.NAME and t[1] in special_operators:
                    yield type_map[tokenize.OP], t[1]
                else:
                    yield type_map[t[0]], t[1]
            except KeyError:
                if t[0] == tokenize.ENDMARKER:
                    break
        yield "(end)", "(end)"

class BaseToken(object):
    def __init__(self, id, expression, advance):
        self.id = id
        self.expression = expression
        self.advance = advance

class LiteralToken(BaseToken):
    lbp = 0
    def __init__(self, id, expression, advance, value):
        super(LiteralToken, self).__init__(id, expression, advance)
        self.value = value

    def nud(self):
        return ConstantExpression(self.value)
        
class NameToken(BaseToken):
    def __init__(self, id, expression, advance, value):
        super(NameToken, self).__init__(id, expression, advance)
        self.value = value
    def nud(self):
        return NameExpression(self.value)

class OperatorAddToken(BaseToken):
    lbp = 110
    def led(self, left):
        return BinaryExpression(BinaryExpression.Add, left, self.expression(self.lbp))

class OperatorSubToken(BaseToken):
    lbp = 110
    def nud(self):
        return UnaryExpression(UnaryExpression.Negate, self.expression(self.lbp+20))
    def led(self, left):
        return BinaryExpression(BinaryExpression.Subtract, left, self.expression(self.lbp))

class OperatorMulToken(BaseToken):
    lbp = 120
    def led(self, left):
        return BinaryExpression(BinaryExpression.Multiply, left, self.expression(self.lbp))

class OperatorDivToken(BaseToken):
    lbp = 120
    def led(self, left):
        return BinaryExpression(BinaryExpression.Divide, left, self.expression(self.lbp))

class OperatorModToken(BaseToken):
    lbp = 130
    def led(self, left):
        return BinaryExpression(BinaryExpression.Modulo, left, self.expression(self.lbp))

class OperatorPowerToken(BaseToken):
    lbp = 140
    def led(self, left):
        return BinaryExpression(BinaryExpression.Power, left, self.expression(self.lbp-1))

class OperatorAndToken(BaseToken):
    lbp = 40
    def led(self, left):
        return BinaryExpression(BinaryExpression.And, left, self.expression(self.lbp-1))

class OperatorOrToken(BaseToken):
    lbp = 30
    def led(self, left):
        return BinaryExpression(BinaryExpression.Or, left, self.expression(self.lbp-1))

class OperatorEqualToken(BaseToken):
    lbp = 60
    def led(self, left):
        return BinaryExpression(BinaryExpression.Equal, left, self.expression(self.lbp))

class OperatorNotEqualToken(BaseToken):
    lbp = 60
    def led(self, left):
        return BinaryExpression(BinaryExpression.NotEqual, left, self.expression(self.lbp))

class OperatorGreaterThanToken(BaseToken):
    lbp = 60
    def led(self, left):
        return BinaryExpression(BinaryExpression.GreaterThan, left, self.expression(self.lbp))

class OperatorGreaterThanOrEqualToken(BaseToken):
    lbp = 60
    def led(self, left):
        return BinaryExpression(BinaryExpression.GreaterThanOrEqual, left, self.expression(self.lbp))

class OperatorLessThanToken(BaseToken):
    lbp = 60
    def led(self, left):
        return BinaryExpression(BinaryExpression.LessThan, left, self.expression(self.lbp))

class OperatorLessThanOrEqualToken(BaseToken):
    lbp = 60
    def led(self, left):
        return BinaryExpression(BinaryExpression.LessThanOrEqual, left, self.expression(self.lbp))

class OperatorNotToken(BaseToken):
    lbp = 60
    def nud(self):
        return UnaryExpression(UnaryExpression.Not, self.expression(self.lbp))

class DotToken(BaseToken):
    global token
    lbp = 150
    def led(self, left):
        first = left
        second = token
        if not isinstance(second, NameToken):
            error = u"Each part of a given get attribute expression (some.variable.value) needs to be a NameExpression."
            raise ValueError(error)
        second = NameExpression(second.value)
        self.advance()
        
        return GetAttributeExpression(first, second)

class LeftParenthesisToken(BaseToken):
    lbp = 150
    def nud(self):
        middle = self.expression()
        self.advance(")")
        return middle

class RightParenthesisToken(BaseToken):
    lbp = 0

class end_token(BaseToken):
    lbp = 0

########NEW FILE########
__FILENAME__ = partition_algorithm
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class EquivalenceClassSetPartition(object):
    
    @classmethod
    def partition(cls, collection, relation):
        dic = {}
        for item in collection:
            equivalence = relation(item)
            if not dic.has_key(equivalence):
                dic[equivalence] = []
            dic[equivalence].append(item)
        return dic

########NEW FILE########
__FILENAME__ = base
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import unittest
import re

class BaseUnitTest(unittest.TestCase):


    # Discussion
    #    assertRaisesEx() adds two optional arguments: "exc_args" 
    #    and "exc_pattern". "exc_args" is a tuple that is expected 
    #    to match the .args attribute of the raised exception. 
    #    "exc_pattern" is a compiled regular expression that the 
    #    stringified raised exception is expected to match.
    # Original url: http://code.activestate.com/recipes/307970/
    # Author: Trent Mick
    def assertRaisesEx(self, exception, callable, *args, **kwargs):
        if "exc_args" in kwargs:
            exc_args = kwargs["exc_args"]
            del kwargs["exc_args"]
        else:
            exc_args = None
        if "exc_pattern" in kwargs:
            exc_pattern = kwargs["exc_pattern"]
            del kwargs["exc_pattern"]
        else:
            exc_pattern = None

        argv = [repr(a) for a in args]\
               + ["%s=%r" % (k,v)  for k,v in kwargs.items()]
        callsig = "%s(%s)" % (callable.__name__, ", ".join(argv))

        try:
            callable(*args, **kwargs)
        except exception, exc:
            if exc_args is not None:
                self.failIf(exc.args != exc_args,
                            "%s raised %s with unexpected args: "\
                            "expected=%r, actual=%r"\
                            % (callsig, exc.__class__, exc_args, exc.args))
            if exc_pattern is not None:
                self.failUnless(exc_pattern.search(str(exc)),
                                "%s raised %s, but the exception "\
                                "does not match '%s': %r"\
                                % (callsig, exc.__class__, exc_pattern.pattern,
                                   str(exc)))
        except:
            exc_info = sys.exc_info()
            print exc_info
            self.fail("%s raised an unexpected exception type: "\
                      "expected=%s, actual=%s"\
                      % (callsig, exception, exc_info[0]))
        else:
            self.fail("%s did not raise %s" % (callsig, exception))


########NEW FILE########
__FILENAME__ = benchmark
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import time 
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq import From

ITERATIONS = 50000

class OtherValue(object):
    def __init__(self, value):
        self.value = value
        
class OneValue(object):
    def __init__(self, value):
        self.value = OtherValue(value)
        
class TwoValues(object):
    def __init__(self, value, value2):
        self.value = value
        self.value2 = value2

def main():
    run_many_small_collections()
    run_two_big_collections()
    select_expression_fields()

def run_many_small_collections():
    start_time = time.time()
    
    fixed_col = [OneValue(1), OneValue(2), OneValue(3)]
    
    for i in range(ITERATIONS):
        total = From(fixed_col).avg("item.value.value")

    print "AVG FIXED COL OPERATION - %d iterations took %.2f" % (ITERATIONS, (time.time() - start_time))

def run_two_big_collections():
    dynamic_col = [OneValue(item) for item in range(ITERATIONS/2)]

    start_time = time.time()

    for i in range(2):
        total = From(dynamic_col).avg("item.value.value")

    print "AVG %d ITEMS OPERATION - 2 iterations took %.2f" % (ITERATIONS/2, (time.time() - start_time))

def select_expression_fields():
    two_values_col = [TwoValues(item, item + 2) for item in range(ITERATIONS/2)]

    start_time = time.time()

    for i in range(2):
        total = From(two_values_col).select("item.value + item.value2", "item.value2 - item.value")

    print "Selecting Two Expression Fields %d ITEMS OPERATION - 2 iterations took %.2f" % (ITERATIONS/2, (time.time() - start_time))

if __name__ == '__main__':
    sys.exit(select_expression_fields())



########NEW FILE########
__FILENAME__ = test_binary_arithmetic_expressions
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import Expression, ConstantExpression, BinaryExpression
from base import BaseUnitTest

class TestBinaryArithmeticExpression(BaseUnitTest):

    def test_binary_expression_only_accepts_expressions_for_arguments(self):
        a = 10
        a_expr = ConstantExpression(10)
        b = "20"
        b_expr = ConstantExpression(20)
        node_type = BinaryExpression.Add

        self.assertRaisesEx(ValueError, BinaryExpression, node_type, a, b_expr, exc_pattern=re.compile("Lhs must be an expression \(an instance of a class that inherits from pynq.Expression\)"))
        self.assertRaisesEx(ValueError, BinaryExpression, node_type, a_expr, b, exc_pattern=re.compile("Rhs must be an expression \(an instance of a class that inherits from pynq.Expression\)"))
        self.assertRaisesEx(ValueError, BinaryExpression, None, a_expr, b_expr, exc_pattern=re.compile("The BinaryExpression node type is required"))

#Add
    def test_expression_for_addition_of_two_constants(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Add
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_for_addition_of_two_constants_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Add
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals("(10 + 20)", str(expr))

    def test_nested_addition_expression(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Add

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)

    def test_nested_addition_expression_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Add

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((10 + 20) + 30)", str(expr))

#Subtract

    def test_expression_for_substraction_of_two_constants(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Subtract
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_for_subtraction_of_two_constants_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Subtract
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals("(10 - 20)", str(expr))

    def test_nested_subtraction_expression(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Subtract

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)

    def test_nested_subtraction_expression_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Subtract

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((10 - 20) - 30)", str(expr))

#Multiply
    def test_expression_for_multiplication_of_two_constants(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Multiply
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_for_multiplication_of_two_constants_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Multiply
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals("(10 * 20)", str(expr))

    def test_nested_multiplication_expression(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Multiply

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)

    def test_nested_multiplication_expression_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Multiply

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((10 * 20) * 30)", str(expr))

#Divide
    def test_expression_for_division_of_two_constants(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Divide
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_for_division_of_two_constants_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Divide
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals("(10 / 20)", str(expr))

    def test_nested_division_expression(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Divide

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)

    def test_nested_division_expression_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Divide

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((10 / 20) / 30)", str(expr))

#Power
    def test_expression_for_power_of_two_constants(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Power
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_for_power_of_two_constants_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Power
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals("(10 ** 20)", str(expr))

    def test_nested_power_expression(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Power

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)

    def test_nested_power_expression_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Power

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((10 ** 20) ** 30)", str(expr))

#Modulus
    def test_expression_for_modulus_of_two_constants(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Modulo
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_for_modulus_of_two_constants_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        node_type = BinaryExpression.Modulo
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals("(10 % 20)", str(expr))

    def test_nested_modulus_expression(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Modulo

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)

    def test_nested_modulus_expression_representation(self):
        a = ConstantExpression(10)
        b = ConstantExpression(20)
        c = ConstantExpression(30)
        node_type = BinaryExpression.Modulo

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((10 % 20) % 30)", str(expr))


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = test_binary_bitwise_expressions
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import Expression, ConstantExpression, BinaryExpression
from base import BaseUnitTest

class TestBinaryBitwiseExpressions(BaseUnitTest):

#And
    def test_expression_and_of_two_constants(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.And
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_and_of_two_constants_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.And
        expr = BinaryExpression(node_type, a, b)
        
        self.assertEquals("(True and False)", str(expr))

    def test_nested_and_expression(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.And

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)
    
    def test_nested_and_expression_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.And

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((True and False) and None)", str(expr))
        
#Or
    def test_expression_or_of_two_constants(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.Or
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_or_of_two_constants_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.Or
        expr = BinaryExpression(node_type, a, b)
        
        self.assertEquals("(True or False)", str(expr))

    def test_nested_or_expression(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.Or

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)
    
    def test_nested_or_expression_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.Or

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((True or False) or None)", str(expr))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_binary_comparison_expressions
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import Expression, ConstantExpression, BinaryExpression
from base import BaseUnitTest

class TestBinaryBooleanExpressions(BaseUnitTest):

#Equals
    def test_expression_equal_of_two_constants(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.Equal
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_equal_of_two_constants_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.Equal
        expr = BinaryExpression(node_type, a, b)
        
        self.assertEquals("(True == False)", str(expr))

    def test_nested_equal_expression(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.Equal

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)
    
    def test_nested_equal_expression_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.Equal

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((True == False) == None)", str(expr))

#Not Equal
    def test_expression_not_equal_of_two_constants(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.NotEqual
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_not_equal_of_two_constants_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.NotEqual
        expr = BinaryExpression(node_type, a, b)
        
        self.assertEquals("(True != False)", str(expr))

    def test_nested_not_equal_expression(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.NotEqual

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)
    
    def test_nested_not_equal_expression_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.NotEqual

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((True != False) != None)", str(expr))

#Greater Than
    def test_expression_greater_than_of_two_constants(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.GreaterThan
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_greater_than_of_two_constants_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.GreaterThan
        expr = BinaryExpression(node_type, a, b)
        
        self.assertEquals("(True > False)", str(expr))

    def test_nested_greater_than_expression(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.GreaterThan

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)
    
    def test_nested_greater_than_expression_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.GreaterThan

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((True > False) > None)", str(expr))

#Greater Than or Equal
    def test_expression_greater_than_or_equal_of_two_constants(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.GreaterThanOrEqual
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_greater_than_or_equal_of_two_constants_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.GreaterThanOrEqual
        expr = BinaryExpression(node_type, a, b)
        
        self.assertEquals("(True >= False)", str(expr))

    def test_nested_greater_than_or_equal_expression(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.GreaterThanOrEqual

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)
    
    def test_nested_greater_than_or_equal_expression_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.GreaterThanOrEqual

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((True >= False) >= None)", str(expr))

#Less Than
    def test_expression_less_than_of_two_constants(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.LessThan
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_less_than_of_two_constants_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.LessThan
        expr = BinaryExpression(node_type, a, b)
        
        self.assertEquals("(True < False)", str(expr))

    def test_nested_less_than_expression(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.LessThan

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)
    
    def test_nested_less_than_expression_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.LessThan

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((True < False) < None)", str(expr))

#Less Than or Equal
    def test_expression_less_than_or_equal_of_two_constants(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.LessThanOrEqual
        expr = BinaryExpression(node_type, a, b)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.lhs, a)
        self.assertEquals(expr.rhs, b)

    def test_expression_less_than_or_equal_of_two_constants_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        node_type = BinaryExpression.LessThanOrEqual
        expr = BinaryExpression(node_type, a, b)
        
        self.assertEquals("(True <= False)", str(expr))

    def test_nested_less_than_or_equal_expression(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.LessThanOrEqual

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.lhs, BinaryExpression), "The left-hand side of the binary expression should be a binary expression as well, but is %s" % expr.lhs.__class__)
        self.assertEquals(expr.lhs.node_type, node_type)
        self.assertEquals(expr.lhs.lhs, a)
        self.assertEquals(expr.lhs.rhs, b)
        self.assertEquals(expr.rhs, c)
    
    def test_nested_less_than_or_equal_expression_representation(self):
        a = ConstantExpression(True)
        b = ConstantExpression(False)
        c = ConstantExpression(None)
        node_type = BinaryExpression.LessThanOrEqual

        expr = BinaryExpression(node_type, BinaryExpression(node_type, a, b), c)

        self.assertEquals("((True <= False) <= None)", str(expr))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_binary_expression
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import Expression, ConstantExpression, BinaryExpression
from base import BaseUnitTest

class TestBinaryExpression(BaseUnitTest):

    def test_binary_expression_only_accepts_expressions_for_arguments(self):
        a = 10
        a_expr = ConstantExpression(10)
        b = "20"
        b_expr = ConstantExpression(20)
        node_type = BinaryExpression.Add
        
        self.assertRaisesEx(ValueError, BinaryExpression, node_type, a, b_expr, exc_pattern=re.compile("Lhs must be an expression \(an instance of a class that inherits from pynq.Expression\)"))
        self.assertRaisesEx(ValueError, BinaryExpression, node_type, a_expr, b, exc_pattern=re.compile("Rhs must be an expression \(an instance of a class that inherits from pynq.Expression\)"))
        self.assertRaisesEx(ValueError, BinaryExpression, None, a_expr, b_expr, exc_pattern=re.compile("The BinaryExpression node type is required"))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_collection_provider
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
import re
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.providers import CollectionProvider
from pynq.enums import Actions
from pynq import From
from base import BaseUnitTest

class TestCollectionProvider(BaseUnitTest):

    def test_querying_with_invalid_action_raises(self):
        error = "Invalid action exception. invalid_action is unknown."
        q = From([1,2,3])
        provider = q.provider
        self.assertRaisesEx(ValueError, provider.parse, q, "invalid_action", exc_pattern=re.compile(error))

    def test_collection_provider_parses_query_and_returns_list(self):
        col = ["a", "b"]
        query = From(col).where("item == 'a'")
        provider = query.provider
        assert isinstance(provider.parse(query, Actions.SelectMany), list)
        
    def test_collection_provider_filters_using_binary_expression(self):
        col = ["a","b"]
        query = From(col).where("item == 'a'")
        provider = query.provider
        result = provider.parse(query, Actions.SelectMany)
        assert result == ['a'], "The collection was not filtered properly and now is: %s" % result

    def test_collection_provider_filters_using_binary_expression_for_numbers(self):
        col = [1, 2, 10, 11, 12]
        query = From(col).where("item > 10")
        provider = query.provider
        result = provider.parse(query, Actions.SelectMany)
        assert result == [11, 12], "The collection was not filtered properly and now is: %s" % result

    def test_collection_provider_parses_query_using_lesser_than(self):
        col = range(5)
        query = From(col).where("item <= 3")
        provider = query.provider
        result = provider.parse(query, Actions.SelectMany)
        assert result == range(4), "The collection was not filtered properly and now is: %s" % result

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_collection_provider_count
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq import From

class TestPynqFactoryCount(unittest.TestCase):

    def test_returns_right_count_for_full_collection(self):
        total = From([1,2,3]).count()
        assert total == 3, "Total should be 3 but was %s" % total
        
    def test_returns_right_count_for_filtered_collection(self):
        total = From([1,2,3]).where("item >= 2").count()
        assert total == 2, "Total should be 2 but was %s" % total
    
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_collection_provider_max_min
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)
import re

from pynq import From
from base import BaseUnitTest

class TestPynqFactoryMax(BaseUnitTest):

    def test_max_returns_right_amount_for_full_collection_with_no_keyword(self):
        value = From([1,2,3]).max()
        assert value == 3, "value should be 3 but was %s" % value

    def test_max_returns_right_amount_for_filtered_collection_with_no_keyword(self):
        value = From([1,2,3,4]).where("item <= 3").max()
        assert value == 3, "value should be 3 but was %s" % value

    def test_max_returns_right_amount_for_full_collection(self):
        value = From([1,2,3]).max("item")
        assert value == 3, "value should be 3 but was %s" % value

    def test_max_returns_right_amount_for_filtered_collection(self):
        value = From([1,2,3,4]).where("item <= 2").max("item")
        assert value == 2, "value should be 2 but was %s" % value

    def test_max_returns_right_amount_for_a_given_property(self):
        class OneValue(object):
            def __init__(self, value):
                self.value = value
        value = From([OneValue(1), OneValue(2), OneValue(3)]).max("item.value")
        assert value == 3, "value should be 3 but was %s" % value

    def test_max_returns_right_amount_for_a_given_sub_property(self):
        class OtherValue(object):
            def __init__(self, value):
                self.value = value
                
        class OneValue(object):
            def __init__(self, value):
                self.value = OtherValue(value)
                
        value = From([OneValue(1), OneValue(2), OneValue(3)]).max("item.value.value")
        assert value == 3, "value should be 3 but was %s" % value

    def test_max_raises_for_an_invalid_property(self):
        error_message = "The attribute '%s' was not found in the specified collection's items. If you meant to use the raw value of each item in the collection just use the word 'item' as a parameter to .max or use .max()"
        
        class OneValue(object):
            def __init__(self, value):
                self.value = value
        fr = From([OneValue(1), OneValue(2), OneValue(3)])
        self.assertRaisesEx(ValueError, fr.max, "value", exc_pattern=re.compile(error_message % "value"))
        self.assertRaisesEx(ValueError, fr.max, "item.dumb", exc_pattern=re.compile(error_message % "item.dumb"))
        self.assertRaisesEx(ValueError, fr.max, "", exc_pattern=re.compile(error_message % ""))
        self.assertRaisesEx(ValueError, fr.max, None, exc_pattern=re.compile(error_message % "None"))

class TestPynqFactoryMin(BaseUnitTest):

    def test_min_returns_right_amount_for_full_collection_with_no_keyword(self):
        value = From([1,2,3]).min()
        assert value == 1, "value should be 1 but was %s" % value

    def test_min_returns_right_amount_for_filtered_collection_with_no_keyword(self):
        value = From([1,2,3,4]).where("item >= 2").min()
        assert value == 2, "value should be 2 but was %s" % value

    def test_min_returns_right_amount_for_full_collection(self):
        value = From([1,2,3]).min("item")
        assert value == 1, "value should be 1 but was %s" % value

    def test_min_returns_right_amount_for_filtered_collection(self):
        value = From([1,2,3,4]).where("item > 2").min("item")
        assert value == 3, "value should be 3 but was %s" % value

    def test_min_returns_right_amount_for_a_given_property(self):
        class OneValue(object):
            def __init__(self, value):
                self.value = value
        value = From([OneValue(1), OneValue(2), OneValue(3)]).min("item.value")
        assert value == 1, "value should be 1 but was %s" % value

    def test_min_returns_right_amount_for_a_given_sub_property(self):
        class OtherValue(object):
            def __init__(self, value):
                self.value = value
                
        class OneValue(object):
            def __init__(self, value):
                self.value = OtherValue(value)
                
        value = From([OneValue(1), OneValue(2), OneValue(3)]).min("item.value.value")
        assert value == 1, "value should be 1 but was %s" % value

    def test_min_raises_for_an_invalid_property(self):
        error_message = "The attribute '%s' was not found in the specified collection's items. If you meant to use the raw value of each item in the collection just use the word 'item' as a parameter to .min or use .min()"
        
        class OneValue(object):
            def __init__(self, value):
                self.value = value
        fr = From([OneValue(1), OneValue(2), OneValue(3)])
        self.assertRaisesEx(ValueError, fr.min, "value", exc_pattern=re.compile(error_message % "value"))
        self.assertRaisesEx(ValueError, fr.min, "item.dumb", exc_pattern=re.compile(error_message % "item.dumb"))
        self.assertRaisesEx(ValueError, fr.min, "", exc_pattern=re.compile(error_message % ""))
        self.assertRaisesEx(ValueError, fr.min, None, exc_pattern=re.compile(error_message % "None"))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_collection_provider_sum_avg
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)
import re

from pynq import From
from base import BaseUnitTest

class TestPynqFactorySum(BaseUnitTest):

    def test_sum_returns_right_amount_for_full_collection_with_no_keyword(self):
        total = From([1,2,3]).sum()
        assert total == 6, "total should be 6 but was %s" % total

    def test_sum_returns_right_amount_for_filtered_collection_with_no_keyword(self):
        total = From([1,2,3,4]).where("item >= 2").sum()
        assert total == 9, "total should be 9 but was %s" % total

    def test_sum_returns_right_amount_for_full_collection(self):
        total = From([1,2,3]).sum("item")
        assert total == 6, "total should be 6 but was %s" % total

    def test_sum_returns_right_amount_for_filtered_collection(self):
        total = From([1,2,3,4]).where("item >= 2").sum("item")
        assert total == 9, "total should be 9 but was %s" % total

    def test_sum_returns_right_amount_for_a_given_property(self):
        class OneValue(object):
            def __init__(self, value):
                self.value = value
        total = From([OneValue(1), OneValue(2), OneValue(3)]).sum("item.value")
        assert total == 6, "total should be 6 but was %s" % total

    def test_sum_returns_right_amount_for_a_given_sub_property(self):
        class OtherValue(object):
            def __init__(self, value):
                self.value = value
                
        class OneValue(object):
            def __init__(self, value):
                self.value = OtherValue(value)
                
        total = From([OneValue(1), OneValue(2), OneValue(3)]).sum("item.value.value")
        assert total == 6, "total should be 6 but was %s" % total

    def test_sum_raises_for_an_invalid_property(self):
        error_message = "The attribute '%s' was not found in the specified collection's items. If you meant to use the raw value of each item in the collection just use the word 'item' as a parameter to .sum or use .sum()"
        
        class OneValue(object):
            def __init__(self, value):
                self.value = value
        fr = From([OneValue(1), OneValue(2), OneValue(3)])
        self.assertRaisesEx(ValueError, fr.sum, "value", exc_pattern=re.compile(error_message % "value"))
        self.assertRaisesEx(ValueError, fr.sum, "item.dumb", exc_pattern=re.compile(error_message % "item.dumb"))
        self.assertRaisesEx(ValueError, fr.sum, "", exc_pattern=re.compile(error_message % ""))
        self.assertRaisesEx(ValueError, fr.sum, None, exc_pattern=re.compile(error_message % "None"))

class TestPynqFactoryAvg(BaseUnitTest):

    def test_avg_returns_right_amount_for_full_collection_with_no_keyword(self):
        total = From([1,2,3]).avg()
        assert total == 2, "total should be 2 but was %s" % total

    def test_returns_right_amount_for_filtered_collection_with_no_keyword(self):
        total = From([1,2,3,4]).where("item >= 2").avg()
        assert total == 3, "total should be 3 but was %s" % total

    def test_avg_returns_right_amount_for_full_collection(self):
        total = From([1,2,3]).avg("item")
        assert total == 2, "total should be 2 but was %s" % total

    def test_returns_right_amount_for_filtered_collection(self):
        total = From([1,2,3,4]).where("item >= 2").avg("item")
        assert total == 3, "total should be 3 but was %s" % total

    def test_returns_right_amount_for_a_given_property(self):
        class OneValue(object):
            def __init__(self, value):
                self.value = value
        total = From([OneValue(1), OneValue(2), OneValue(3)]).avg("item.value")
        assert total == 2

    def test_returns_right_amount_for_a_given_sub_property(self):
        class OtherValue(object):
            def __init__(self, value):
                self.value = value
                
        class OneValue(object):
            def __init__(self, value):
                self.value = OtherValue(value)
                
        total = From([OneValue(1), OneValue(2), OneValue(3)]).avg("item.value.value")
        assert total == 2

    def test_raises_for_an_invalid_property(self):
        error_message = "The attribute '%s' was not found in the specified collection's items. If you meant to use the raw value of each item in the collection just use the word 'item' as a parameter to .avg or use .avg()"
        
        class OneValue(object):
            def __init__(self, value):
                self.value = value
        fr = From([OneValue(1), OneValue(2), OneValue(3)])
        self.assertRaisesEx(ValueError, fr.avg, "value", exc_pattern=re.compile(error_message % "value"))
        self.assertRaisesEx(ValueError, fr.avg, "item.dumb", exc_pattern=re.compile(error_message % "item.dumb"))
        self.assertRaisesEx(ValueError, fr.avg, "", exc_pattern=re.compile(error_message % ""))
        self.assertRaisesEx(ValueError, fr.avg, None, exc_pattern=re.compile(error_message % "None"))
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_constant_expression
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import Expression, ConstantExpression

class TestConstantExpression(unittest.TestCase):

    def test_constant_expression_is_subtype_of_expression(self):
        expr = ConstantExpression(100)
        self.failUnless(isinstance(expr, Expression), "The ConstantExpression class instances must inherit from Expression.")

    def test_constant_expression_returns_informed_value_as_integer(self):
        int_expr = ConstantExpression(45)
        self.assertEquals(45, int_expr.evaluate())

    def test_constant_expression_returns_informed_value_as_string(self):
        str_expr = ConstantExpression(u"str")
        self.assertEquals(u"str", str_expr.evaluate())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_equivalence_classes_algo
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

import unittest

from pynq.providers.partition_algorithm import EquivalenceClassSetPartition

class TestEquivalenceClassesAlgorithm(unittest.TestCase):

    def test_algorithm_returns_a_dictionary(self):
        partitioned = EquivalenceClassSetPartition.partition([1], lambda item: item)
        assert isinstance(partitioned, dict)
    
    def test_algorithm_returns_proper_equivalence_class(self):
        col = [10]
        r = lambda item: item * item
        
        partitioned = EquivalenceClassSetPartition.partition(col, r)
        
        assert partitioned.has_key(100)
    
    def test_algorithm_returns_a_list_for_given_equivalence_class(self):
        col = [10]
        r = lambda item: item * item
        
        partitioned = EquivalenceClassSetPartition.partition(col, r)
        
        assert isinstance(partitioned[100], list)
    
    def test_algorithm_returns_proper_number_of_items_for_given_equivalence_class(self):
        col = [10]
        r = lambda item: item * item
        
        partitioned = EquivalenceClassSetPartition.partition(col, r)
        
        assert len(partitioned[100]) == 1
    
    def test_algorithm_returns_the_item_in_the_list_for_given_equivalence_class(self):
        col = [10]
        r = lambda item: item * item
        
        partitioned = EquivalenceClassSetPartition.partition(col, r)
        
        assert partitioned[100][0] == 10
    
    def test_algorithm_returns_proper_sets_for_multiple_values(self):
        col = [1,2,3,4,5]
        r = lambda item: item % 2 == 0 and "even" or "odd"
        
        partitioned = EquivalenceClassSetPartition.partition(col, r)
        
        assert len(partitioned["even"]) == 2
        assert len(partitioned["odd"]) == 3
        
        assert partitioned["even"][0] == 2
        assert partitioned["even"][1] == 4
        assert partitioned["odd"][0] == 1
        assert partitioned["odd"][1] == 3
        assert partitioned["odd"][2] == 5
    
    def test_algorithm_returns_proper_sets_for_objects(self):
        class Value(object):
            def __init__(self, value):
                self.value = value
        
        col = [Value(1),Value(2),Value(3),Value(4),Value(5),]
        r = lambda item: item.value % 2 == 0 and "even" or "odd"
        
        partitioned = EquivalenceClassSetPartition.partition(col, r)
        
        assert len(partitioned["even"]) == 2
        assert len(partitioned["odd"]) == 3
        
        assert partitioned["even"][0].value == 2
        assert partitioned["even"][1].value == 4
        assert partitioned["odd"][0].value == 1
        assert partitioned["odd"][1].value == 3
        assert partitioned["odd"][2].value == 5        
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_expression
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import Expression

class TestExpresionBaseClass(unittest.TestCase):

    def test_evaluate_should_raise(self):
        expr = Expression()
        self.assertRaises(NotImplementedError, expr.evaluate)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_expression_parser
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
import re
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from base import BaseUnitTest
from pynq.parser import LiteralToken, DotToken
import pynq.parser

class TestExpressionParser(BaseUnitTest):

    def test_dot_token_raises_on_different_tokens(self):
        literal = LiteralToken(None, None, None, "1")
        pynq.parser.token = literal
        token = literal
        dot = DotToken(None, None, None)
        error = u"Each part of a given get attribute expression \(some.variable.value\) needs to be a NameExpression."
        self.assertRaisesEx(ValueError, dot.led, literal, exc_pattern=re.compile(error))
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_expression_parser_for_binary_expressions
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.parser import ExpressionParser
from pynq.expressions import BinaryExpression, ConstantExpression

parser = ExpressionParser()
operations_to_test = {
    BinaryExpression.Add : (("1+2", "1", "2"), ("1 + 2", "1", "2")),
    BinaryExpression.Subtract : (("1-2", "1", "2"), ("1 - 2", "1", "2")),
    BinaryExpression.Multiply : (("1*2", "1", "2"), ("1 * 2", "1", "2")),
    BinaryExpression.Divide : (("1/2", "1", "2"), ("1 / 2", "1", "2")),
    BinaryExpression.Power : (("1**2", "1", "2"), ("1 ** 2", "1", "2")),
    BinaryExpression.Modulo : (("1%2", "1", "2"), ("1 % 2", "1", "2")),
    BinaryExpression.And : (("1 and 2", "1", "2"),),
    BinaryExpression.Or : (("1 or 2", "1", "2"),),
    BinaryExpression.Equal : (("1==2", "1", "2"),("1 == 2", "1", "2"),),
    BinaryExpression.NotEqual : (("1!=2", "1", "2"),("1 != 2", "1", "2"),),
    BinaryExpression.GreaterThan : (("1>2", "1", "2"),("1 > 2", "1", "2"),),
    BinaryExpression.GreaterThanOrEqual : (("1>=2", "1", "2"),("1 >= 2", "1", "2"),),
    BinaryExpression.LessThan : (("1<2", "1", "2"),("1 < 2", "1", "2"),),
    BinaryExpression.LessThanOrEqual : (("1<=2", "1", "2"),("1 <= 2", "1", "2"),),
}

def test_for_null_for_binary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, lhs, rhs = combination
            yield assert_not_null, program, operation, lhs, rhs

def test_for_type_of_expression_for_binary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, lhs, rhs = combination
            yield assert_is_binary_expression, program, operation, lhs, rhs

def test_for_type_of_expression_for_binary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, lhs, rhs = combination
            yield assert_is_constant_expression_on_both_sides, program, operation, lhs, rhs

def test_for_values_for_binary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, lhs, rhs = combination
            yield assert_values_on_both_sides, program, operation, lhs, rhs

def test_for_node_type_for_binary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, lhs, rhs = combination
            yield assert_node_type, program, operation, lhs, rhs

#Asserts
def assert_not_null(program, node_type, lhs, rhs):
    tree = parser.parse(program)
    assert tree is not None, "The tree cannot be null after parsing for operation %s" % node_type

def assert_is_binary_expression(program, node_type, lhs, rhs):
    tree = parser.parse(program)
    assert isinstance(tree, BinaryExpression), "The tree for this operation (%s) should return a BinaryExpression" % node_type

def assert_is_constant_expression_on_both_sides(program, node_type, lhs, rhs):
    tree = parser.parse(program)
    assert isinstance(tree.lhs, ConstantExpression), "The lhs for this operation (%s) should be a ConstantExpression" % node_type
    assert isinstance(tree.rhs, ConstantExpression), "The rhs for this operation (%s) should be a ConstantExpression" % node_type

def assert_values_on_both_sides(program, node_type, lhs, rhs):
    tree = parser.parse(program)
    assert tree.lhs.value == lhs, "The value for the lhs when the operation is %s should be %s and was %s" % (node_type, lhs, tree.lhs.value)
    assert tree.rhs.value == rhs, "The value for the lhs when the operation is %s should be %s and was %s" % (node_type, rhs, tree.rhs.value)

def assert_node_type(program, node_type, lhs, rhs):
    tree = parser.parse(program)
    assert tree.node_type == node_type, "The tree node type should be %s and was %s" % (node_type, tree.node_type)

if __name__ == '__main__':
    import nose
    nose.main()

########NEW FILE########
__FILENAME__ = test_expression_parser_for_unary_expressions
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.parser import ExpressionParser
from pynq.expressions import UnaryExpression, ConstantExpression

parser = ExpressionParser()
operations_to_test = {
    UnaryExpression.Negate : (("-1", "1"),),
    UnaryExpression.Not : (("not 1", "1"),),
}

def test_for_null_for_unary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, rhs = combination
            yield assert_not_null, program, operation, rhs

def test_for_type_of_expression_for_unary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, rhs = combination
            yield assert_is_binary_expression, program, operation, rhs

def test_for_type_of_expression_for_unary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, rhs = combination
            yield assert_is_constant_expression_on_both_sides, program, operation, rhs

def test_for_value_for_unary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, rhs = combination
            yield assert_value, program, operation, rhs

def test_for_node_type_for_unary_expressions():
    for operation in operations_to_test.keys():
        for combination in operations_to_test[operation]:
            program, rhs = combination
            yield assert_node_type, program, operation, rhs

#Asserts
def assert_not_null(program, node_type, rhs):
    tree = parser.parse(program)
    assert tree is not None, "The tree cannot be null after parsing for operation %s" % node_type

def assert_is_unary_expression(program, node_type, rhs):
    tree = parser.parse(program)
    assert isinstance(tree, UnaryExpression), "The tree for this operation (%s) should return a UnaryExpression" % node_type

def assert_is_constant_expression_on_both_sides(program, node_type, rhs):
    tree = parser.parse(program)
    assert isinstance(tree.rhs, ConstantExpression), "The rhs for this operation (%s) should be a ConstantExpression" % node_type

def assert_value(program, node_type, rhs):
    tree = parser.parse(program)
    assert tree.rhs.value == rhs, "The value for the rhs when the operation is %s should be %s and was %s" % (node_type, rhs, tree.rhs.value)

def assert_node_type(program, node_type, rhs):
    tree = parser.parse(program)
    assert tree.node_type == node_type, "The tree node type should be %s and was %s" % (node_type, tree.node_type)

if __name__ == '__main__':
    import nose
    nose.main()

########NEW FILE########
__FILENAME__ = test_get_attribute_expression
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
import re
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import GetAttributeExpression
from base import BaseUnitTest

class TestGetAttributeExpression(BaseUnitTest):

    def test_get_attribute_expression_validates_against_empty_attributes(self):
        self.assertRaisesEx(ValueError, GetAttributeExpression, exc_pattern=re.compile("In order to create a new attribute expression you need to provide some attributes."))

    def test_get_attribute_expression_keeps_track_of_attributes(self):
        expression = GetAttributeExpression("some","expression")
        assert len(expression.attributes) == 2, "Length of attributes property should be 2 but was %d" % len(expression.attributes)
        assert expression.attributes[0] == "some"
        assert expression.attributes[1] == "expression"
    
    def test_nested_get_attribute_expressions_work_together(self):
        expression = GetAttributeExpression(GetAttributeExpression("some","weird"), "expression")
        assert len(expression.attributes) == 3
        assert expression.attributes[0] == "some"
        assert expression.attributes[1] == "weird"
        assert expression.attributes[2] == "expression"
        
    def test_get_attribute_returns_the_proper_representation(self):
        expression = GetAttributeExpression(GetAttributeExpression("some","weird"), "expression")
        assert str(expression) == "some.weird.expression"
    
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_group_by
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq import From
from pynq.expressions import NameExpression

class TestGroupBy(unittest.TestCase):

    class TestGroupByClass(object):
        def __init__(self, first, second, third):
            self.first = first
            self.second = second
            self.third = third

    def setUp(self):
        self.entity1 = self.TestGroupByClass(1, 2, 8)
        self.entity2 = self.TestGroupByClass(4, 5, 5)
        self.entity3 = self.TestGroupByClass(7, 5, 2)
        
        self.col = [self.entity3, self.entity1, self.entity2]
        
    def test_grouping_adds_right_expression_for_name_expression(self):
        query = From(self.col).group_by("second")
        assert isinstance(query.group_expression, NameExpression)
    
    def test_grouping_returns_two_keys_on_select_many(self):
        items = From(self.col).group_by("second").select_many()
        assert len(items.keys()) == 2
        
    def test_grouping_returns_the_two_right_keys_on_select_many(self):
        items = From(self.col).group_by("second").select_many()
        assert items.has_key(2)
        assert items.has_key(5)

    def test_grouping_returns_the_right_length_of_items_on_select_many(self):
        items = From(self.col).group_by("second").select_many()
        assert len(items[2]) == 1
        assert len(items[5]) == 2

    def test_grouping_returns_the_right_items_on_select_many(self):
        items = From(self.col).order_by("first").group_by("second").select_many()
        assert items[2][0].first == 1
        assert items[5][0].first == 4
        assert items[5][1].first == 7

    def test_grouping_returns_the_right_items_on_select_many(self):
        items = From(self.col).order_by("first").group_by("second").select("first", "second")
        assert items[2][0].first == 1
        assert items[2][0].second == 2
        assert items[5][0].first == 4
        assert items[5][0].second == 5
        assert items[5][1].first == 7
        assert items[5][1].second == 5
        assert not hasattr(items[2][0], "third")
        assert not hasattr(items[5][0], "third")
        assert not hasattr(items[5][1], "third")

    def test_grouping_with_strings_returns_the_right_items_on_select_many(self):
        new_col = [self.TestGroupByClass("a", "z", "a"), 
                   self.TestGroupByClass("b","w","b"), 
                   self.TestGroupByClass("c","z","c")]
        items = From(new_col).order_by("first").group_by("second").select_many()
        assert items["z"][0].first == "a"
        assert items["z"][1].first == "c"
        assert items["w"][0].first == "b"

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_guard
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.guard import Guard
from base import BaseUnitTest

class TestGuard(BaseUnitTest):

    def test_required_list_argument(self):
        class WithRequiredArgument:
            def __init__(self, a):
                Guard.against_empty(a, "Argument a is required")
                pass

        req = WithRequiredArgument(("some tuple",))
        self.assertRaisesEx(ValueError, WithRequiredArgument, tuple([]), exc_pattern=re.compile("Argument a is required"))
        self.assertRaisesEx(ValueError, WithRequiredArgument, [], exc_pattern=re.compile("Argument a is required"))
        self.assertRaisesEx(ValueError, WithRequiredArgument, {}, exc_pattern=re.compile("Argument a is required"))

    def test_required_list_argument_for_empty_content(self):
        class WithRequiredArgument:
            def __init__(self, a):
                Guard.against_empty(a, "Argument a is required")
                pass

        req = WithRequiredArgument(("some tuple",))
        self.assertRaisesEx(ValueError, WithRequiredArgument, tuple([None]), exc_pattern=re.compile("Argument a is required"))
        self.assertRaisesEx(ValueError, WithRequiredArgument, [None], exc_pattern=re.compile("Argument a is required"))
        self.assertRaisesEx(ValueError, WithRequiredArgument, {None:None}, exc_pattern=re.compile("Argument a is required"))

    def test_required_argument(self):
        class WithRequiredArgument:
            def do(self, a):
                Guard.against_empty(a, "Argument a is required")
                pass

        req = WithRequiredArgument()
        req.do("10")
        self.assertRaisesEx(ValueError, req.do, None, exc_pattern=re.compile("Argument a is required"))
        self.assertRaisesEx(ValueError, req.do, "", exc_pattern=re.compile("Argument a is required"))

    def test_required_argument_with_default_message(self):
        class WithRequiredArgument:
            def do(self, a):
                Guard.against_empty(a)
                pass

        req = WithRequiredArgument()
        req.do("10")
        self.assertRaisesEx(ValueError, req.do, None, exc_pattern=re.compile("One of the arguments is required and was not filled."))
        self.assertRaisesEx(ValueError, req.do, "", exc_pattern=re.compile("One of the arguments is required and was not filled."))

    def test_is_of_type(self):
        class WithTypeArgument:
            def do(self, a):
                Guard.accepts(a, (int, float), "Argument a must be an integer or a float")
                pass
        req = WithTypeArgument()
        req.do(10)
        req.do(10.0)
        self.assertRaisesEx(ValueError, req.do, "a", exc_pattern=re.compile("Argument a must be an integer or a float"))
        self.assertRaisesEx(ValueError, req.do, (10,20), exc_pattern=re.compile("Argument a must be an integer or a float"))

    def test_is_of_type_with_default_message(self):
        class WithTypeArgument:
            def do(self, a):
                Guard.accepts(a, (int, float))
                pass
                
        msg = "One of the arguments should be of types %s and it isn't." % ", ".join((str(int), str(float)))
        req = WithTypeArgument()
        req.do(10)
        req.do(10.0)
        self.assertRaisesEx(ValueError, req.do, "a", exc_pattern=re.compile(msg))
        self.assertRaisesEx(ValueError, req.do, (10,20), exc_pattern=re.compile(msg))
    
    def test_accepts_only_with_message(self):
        items = ["a", "b"]
        items_failing = ["a", "b", 1]
        message = "There should be only strings."
        
        Guard.accepts_only(items, [str], message)
        
        self.assertRaisesEx(ValueError, Guard.accepts_only, items_failing, [str], message, exc_pattern=re.compile(message))

    def test_accepts_only_without_message(self):
        items = ["a", "b"]
        items_failing = ["a", "b", 1]
        message = u"All arguments in the given collection should be of type\(s\) \[str\] and at least one of them isn't."
        
        Guard.accepts_only(items, [str])
        
        self.assertRaisesEx(ValueError, Guard.accepts_only, items_failing, [str], exc_pattern=re.compile(message))
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_i_pynq_provider
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.providers import IPynqProvider

class TestIPynqProvider(unittest.TestCase):

    def test_parse_from_IPynqProvider_does_nothing(self):
        provider = IPynqProvider()
        assert provider.parse(None) is None
        
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_name_expression
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import NameExpression

class TestNameExpression(unittest.TestCase):

    def test_name_expression(self):
        expression = NameExpression("somename")
        assert expression.name == "somename", "The name of the" \
                                               " variable in this expression should be" \
                                               " 'somename' but was %s" % expression.name
    
    def test_name_expression_string_repr(self):
        expression = NameExpression("somename")
        assert str(expression) == "somename"

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_order_by
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq import From
from pynq.expressions import NameExpression

class TestOrderBy(unittest.TestCase):

    class TestClass(object):
        def __init__(self, first, second, third):
            self.first = first
            self.second = second
            self.third = third

    def setUp(self):
        self.entity1 = self.TestClass(1, 2, 8)
        self.entity2 = self.TestClass(4, 5, 5)
        self.entity3 = self.TestClass(7, 5, 2)
        
        self.col = [self.entity3, self.entity1, self.entity2]

    def test_adding_order_adds_to_query(self):
        query = From([]).order_by("some")
        assert len(query.order_expressions) == 1

    def test_adding_order_creates_a_name_expression_in_query(self):
        query = From([]).order_by("some")
        assert isinstance(query.order_expressions[0], NameExpression)

    def test_adding_order_keeps_the_right_value_in_query(self):
        query = From([]).order_by("some")
        assert str(query.order_expressions[0]) == "some"

    def test_ordering_by_first_field_asc(self):
        result = From(self.col).order_by("first").select_many()
        assert result[0].first == 1
        assert result[1].first == 4
        assert result[2].first == 7

    def test_ordering_by_two_fields(self):
        result = From(self.col).order_by("second", "third").select_many()
        assert result[0].first == 1
        assert result[1].first == 7
        assert result[2].first == 4

    def test_desc_order(self):
        result = From(self.col).order_by("-first").select_many()
        assert result[0].first == 7
        assert result[1].first == 4
        assert result[2].first == 1

    def test_desc_order_for_many_fields(self):
        result = From(self.col).order_by("-second", "-third").select_many()
        assert result[0].first == 4
        assert result[1].first == 7
        assert result[2].first == 1

    def test_asc_order_for_expression(self):
        result = From(self.col).order_by("item.first + item.second").select_many()

        assert result[0].first == 1
        assert result[1].first == 4
        assert result[2].first == 7

    def test_desc_order_for_expression(self):
        result = From(self.col).order_by("-(item.first + item.second)").select_many()

        assert result[0].first == 7
        assert result[1].first == 4
        assert result[2].first == 1

    def test_mixed_expression_order(self):
        result = From(self.col).order_by("item.second + item.third", "item.first + item.second").select_many()

        assert result[0].first == 7
        assert result[1].first == 1
        assert result[2].first == 4

    def test_mixed_desc_expression_order(self):
        result = From(self.col).order_by("item.second + item.third", "-(item.first + item.second)").select_many()

        assert result[0].first == 7
        assert result[1].first == 4
        assert result[2].first == 1

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_parenthesized_expression
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.parser import ExpressionParser
from pynq.expressions import BinaryExpression, ConstantExpression

class TestParenthesizedExpression(unittest.TestCase):

    def test_basic_parenthesized_expression_returns_something(self):
        expression = "1 + (2 + 3)"
        parser = ExpressionParser()
        tree = parser.parse(expression)
        assert tree is not None, "The tree cannot be null after parsing"

    def test_basic_parenthesized_expression_returns_binary_expression(self):
        expression = "1 + (2 + 3)"
        parser = ExpressionParser()
        tree = parser.parse(expression)
        assert isinstance(tree, BinaryExpression), "The tree needs to be a binary expression"

    def test_basic_parenthesized_expression_returns_constant_expression_in_lhs(self):
        expression = "1 + (2 + 3)"
        parser = ExpressionParser()
        tree = parser.parse(expression)
        assert tree.lhs is not None, "The lhs for the tree cannot be null"
        assert isinstance(tree.lhs, ConstantExpression), "The lhs should be a constant expression"

    def test_basic_parenthesized_expression_returns_proper_value_in_lhs(self):
        expression = "1 + (2 + 3)"
        parser = ExpressionParser()
        tree = parser.parse(expression)
        assert tree.lhs.value == "1", "The lhs should contain the '1' value"

    def test_basic_parenthesized_expression_returns_binary_expression_in_rhs(self):
        expression = "1 + (2 + 3)"
        parser = ExpressionParser()
        tree = parser.parse(expression)
        assert isinstance(tree.rhs, BinaryExpression), "The rhs should be a BinaryExpression"

    def test_basic_parenthesized_expression_returns_not_null_expressions_inside_rhs(self):
        expression = "1 + (2 + 3)"
        parser = ExpressionParser()
        tree = parser.parse(expression)
        assert tree.rhs.lhs is not None, "The lhs of the rhs cannot be null"        
        assert tree.rhs.rhs is not None, "The rhs of the rhs cannot be null"

    def test_basic_parenthesized_expression_returns_constant_expressions_inside_rhs(self):
        expression = "1 + (2 + 3)"
        parser = ExpressionParser()
        tree = parser.parse(expression)
        assert isinstance(tree.rhs.lhs, ConstantExpression), "The lhs of the rhs should be a ConstantExpression"        
        assert isinstance(tree.rhs.rhs, ConstantExpression), "The rhs of the rhs should be a ConstantExpression"        

    def test_basic_parenthesized_expression_returns_proper_values_inside_rhs(self):
        expression = "1 + (2 + 3)"
        parser = ExpressionParser()
        tree = parser.parse(expression)
        assert tree.rhs.lhs.value == "2", "The lhs of the rhs should be 2 but was %s" % tree.rhs.lhs.value
        assert tree.rhs.rhs.value == "3", "The rhs of the rhs should be 3 but was %s" % tree.rhs.rhs.value

    def test_advanced_parenthesized_expression(self):
        expression = "(1 + 2 + 3) + ((2+3) + 1)"
        parser = ExpressionParser()
        tree = parser.parse(expression)

        assert str(tree) == "(((1 + 2) + 3) + ((2 + 3) + 1))", "The expression was not parsed correctly"
    
    def test_advanced_parenthesized_expression(self):
        expression = "(1 + (2 + 3)) + ((2+3) + 1)"
        parser = ExpressionParser()
        tree = parser.parse(expression)
        
        expected = "((1 + (2 + 3)) + ((2 + 3) + 1))"
        assert str(tree) == expected, "The expression was not parsed correctly. Expecting %s, Found %s" % (expected, str(tree))
    
if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_parser
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from base import BaseUnitTest
from pynq.parser import ExpressionParser

class TestParser(BaseUnitTest):

    def test_parser_raises_for_invalid_syntax(self):
        parser = ExpressionParser()

        self.assertRaisesEx(SyntaxError, parser.parse, "1 + lambda: x", exc_pattern=re.compile("unknown operator: '\(operator\)' ':'"))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_pynq_factory
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq import From, Query
from pynq.expressions import Expression, ConstantExpression, BinaryExpression, GetAttributeExpression, NameExpression
from pynq.providers import CollectionProvider
from base import BaseUnitTest

class TestPynqFactory(BaseUnitTest):

    def test_from_returns_query(self):
        query = From([])
        assert isinstance(query, Query)
    
    def test_from_with_empty_provider_raises(self):
        error = "The provider cannot be None. If you meant to use the CollectionProvider pass in a tuple or list"
        self.assertRaisesEx(ValueError, From, None, exc_pattern=re.compile(error))        
    
    def test_passing_tuple_returns_collection_provider(self):
        query = From(tuple([]))
        assert isinstance(query.provider, CollectionProvider)
        
    def test_passing_list_returns_collection_provider(self):
        query = From([])
        assert isinstance(query.provider, CollectionProvider)
    
    def test_specifying_provider_keeps_provider_in_the_tree(self):
        query = From("provider")
        assert query.provider == "provider"
        
    def test_where_binary_equals_returns_tree(self):
        col = []
        tree = From(col).where("some.other.property == 'Bernardo'")
        
        assert tree is not None, "The From method needs to return something"
        assert isinstance(tree, Query), "The lambda should have resolved to a LambdaExpression"

    def test_where_binary_equals_returns_binary_expression(self):
        col = []
        tree = From(col).where("some.other.property == 'Bernardo'")        

        assert len(tree.expressions) == 1, "There should be one where expression"
        assert isinstance(tree.expressions[0], BinaryExpression), \
                "The first expression of the tree should be a BinaryExpression"

    def test_where_binary_equals_returns_get_attribute_expression_on_lhs(self):
        col = []
        tree = From(col).where("some.other.property == 'Bernardo'")
        error = "Lhs should be GetAttributeExpression but was %s"
        class_name = tree.expressions[0].__class__.__name__
        assert isinstance(tree.expressions[0].lhs, GetAttributeExpression), \
                            error % class_name

    def test_where_binary_equals_returns_tree_name_expressions_as_attributes_on_lhs(self):
        col = []
        tree = From(col).where("some.other.property == 'Bernardo'")
        error_message = "There should be three attributes "\
                        "('some','other','property') in the GetAttributeExpression, "\
                        "but there was %d"
        assert len(tree.expressions[0].lhs.attributes) == 3, \
                error_message % len(tree.expressions[0].lhs.attributes)
        for i in range(3):
            error = "The %d parameter should be a NameExpression but was %s"
            class_name = tree.expressions[0].lhs.attributes[i].__class__.__name__
            assert isinstance(tree.expressions[0].lhs.attributes[i], NameExpression), \
                                error % (i, class_name)
    
    def test_where_binary_equals_returns_the_proper_node_type(self):
        col = []
        tree = From(col).where("some.other.property == 'Bernardo'")

        assert tree.expressions[0].node_type == BinaryExpression.Equal

    def test_where_binary_equals_returns_a_constant_expression_on_the_rhs(self):
        col = []
        tree = From(col).where("some.other.property == 'Bernardo'")

        assert isinstance(tree.expressions[0].rhs, ConstantExpression)

    def test_where_binary_equals_returns_the_right_value_on_the_rhs(self):
        col = []
        tree = From(col).where("some.other.property == 'Bernardo'")

        assert tree.expressions[0].rhs.value == "'Bernardo'"
        
    def test_select_many_returns_proper_results_for_numbers(self):
        items = From([1,2,3,4,5]).where("item > 2 and item < 4").select_many()
        assert items == [3], "Only item 3 should be in the resulting collection but it was %s." % ",".join(items)

    def test_select_many_returns_proper_results_for_sub_property(self):
        class SomeElement(object):
            def __init__(self, value):
                self.value = value
            def __str__(self):
                return str(self.value)
        
        col = [SomeElement(1), SomeElement(2), SomeElement(3), SomeElement(4), SomeElement(5)]
        
        items = From(col).where("item.value > 2 and item.value < 4").select_many()
        
        assert len(items) == 1, "Only item 3 should be in the resulting collection, but it has length of %d" % len(items)
        assert items[0].value == 3, "Only item 3 should be in the resulting collection but it was %s." % items[0].value

    class TwoValues(object):
        def __init__(self, value, value2):
            self.value = value
            self.value2 = value2

    def test_where_add_returns_proper_results(self):
        
        col = [self.TwoValues(1, 2), self.TwoValues(2, 3), self.TwoValues(3, 4), self.TwoValues(4, 5), self.TwoValues(5, 6)]
        
        items = From(col).where("item.value + item.value2 > 8").select_many()
        
        assert len(items) == 2, "Only items 4 and 5 should be in the resulting collection, but it has length of %d" % len(items)
        assert items[0].value == 4, "Item 4 should be in the resulting collection but it was %s." % items[0].value
        assert items[1].value == 5, "Item 5 should be in the resulting collection but it was %s." % items[1].value

    def test_where_power_returns_proper_results(self):
        col = [self.TwoValues(1, 2), self.TwoValues(2, 3), self.TwoValues(3, 4), self.TwoValues(4, 5), self.TwoValues(5, 6)]
        
        items = From(col).where("item.value ** item.value2 > 90").select_many()
        
        assert len(items) == 2, "Only items 4 and 5 should be in the resulting collection, but it has length of %d" % len(items)
        assert items[0].value == 4, "Item 4 should be in the resulting collection but it was %s." % items[0].value
        assert items[1].value == 5, "Item 5 should be in the resulting collection but it was %s." % items[1].value

    def test_where_not_returns_proper_results(self):
        col = [self.TwoValues(1, 2), self.TwoValues(2, 3), self.TwoValues(3, 4), self.TwoValues(4, 5), self.TwoValues(5, 6)]
        
        items = From(col).where("not (item.value < 4)").select_many()
        
        assert len(items) == 2, "Only items 4 and 5 should be in the resulting collection, but it has length of %d" % len(items)
        assert items[0].value == 4, "Item 4 should be in the resulting collection but it was %s." % items[0].value
        assert items[1].value == 5, "Item 5 should be in the resulting collection but it was %s." % items[1].value        
    
    def test_where_or_returns_proper_results(self):
        col = [self.TwoValues(1, 2), self.TwoValues(2, 3), self.TwoValues(3, 4), self.TwoValues(4, 5), self.TwoValues(5, 6)]
        
        items = From(col).where("item.value == 4 or item.value == 5").select_many()
        
        assert len(items) == 2, "Only items 4 and 5 should be in the resulting collection, but it has length of %d" % len(items)
        assert items[0].value == 4, "Item 4 should be in the resulting collection but it was %s." % items[0].value
        assert items[1].value == 5, "Item 5 should be in the resulting collection but it was %s." % items[1].value
        
    def test_where_and_returns_proper_results(self):
        col = [self.TwoValues(1, 2), self.TwoValues(2, 3), self.TwoValues(3, 4), self.TwoValues(4, 5), self.TwoValues(5, 6)]
        
        items = From(col).where("item.value > 2 and item.value2 < 6 ").select_many()
        
        assert len(items) == 2, "Only items 3 and 4 should be in the resulting collection, but it has length of %d" % len(items)
        assert items[0].value == 3, "Item 3 should be in the resulting collection but it was %s." % items[0].value
        assert items[1].value == 4, "Item 4 should be in the resulting collection but it was %s." % items[1].value

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_select_expressions
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import datetime
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq import From
from base import BaseUnitTest

class TestSelectFieldExpressions(BaseUnitTest):

    def test_select_field_operator_add(self):
        class Item:
            def __init__(self, name, value, value2):
                self.name = name
                self.value = value
                self.value2 = value2

        col = [Item("A", 10, 10), Item("B", 20, 20), Item("C", 30, 30)]
        mod = From(col).select("name", "item.value + item.value2")

        assert mod[0].name == "A"
        assert mod[0].dynamic_1 == 20

        assert mod[1].name == "B"
        assert mod[1].dynamic_1 == 40

        assert mod[2].name == "C"
        assert mod[2].dynamic_1 == 60

    def test_select_many_expressions_at_once(self):
        class Item:
            def __init__(self, name, value, value2):
                self.name = name
                self.value = value
                self.value2 = value2

        col = [Item("A", 10, 20), Item("B", 20, 30), Item("C", 30, 40)]
        mod = From(col).select("name", "item.value2 - item.value", "item.value * item.value2")

        assert mod[0].name == "A"
        assert mod[0].dynamic_1 == 10
        assert mod[0].dynamic_2 == 200

        assert mod[1].name == "B"
        assert mod[1].dynamic_1 == 10
        assert mod[1].dynamic_2 == 600

        assert mod[2].name == "C"
        assert mod[2].dynamic_1 == 10
        assert mod[2].dynamic_2 == 1200

########NEW FILE########
__FILENAME__ = test_select_fields
#!/usr/bin/env python
# -*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import datetime
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq import From
from base import BaseUnitTest

class TestSelectFields(BaseUnitTest):

    class TestClass(object):
        def __init__(self, first, second, third):
            self.first = first
            self.second = second
            self.third = third

    def setUp(self):
        self.entity1 = self.TestClass(1, 2, 3)
        self.entity2 = self.TestClass(4, 5, 6)
        self.entity3 = self.TestClass(7, 8, 9)
        
        self.col = [self.entity1, self.entity2, self.entity3]

    def test_select_returns_something(self):
        filtered = From(self.col).select("first","second")
        assert filtered is not None    

    def test_select_returns_three_elements(self):
        filtered = From(self.col).select("first","second")
        assert len(filtered) == 3, "There should be three items in the filtered collection."

    def test_select_returns_dynamic_items(self):
        filtered = From(self.col).select("first","second")
        for i in range(3):
            assert filtered[i].__class__.__name__ == "DynamicItem"

    def test_select_returns_proper_values(self):
        filtered = From(self.col).select("first","second")
        for i in range(3):
            assert filtered[i].first == i * 3 + 1
            assert filtered[i].second == i * 3 + 2

    def test_select_returns_class_without_third_attribute(self):
        filtered = From(self.col).select("first","second")
        for i in range(3):
            assert not hasattr(filtered[i], "third")
    
    def test_selecting_twice_returns_different_objects(self):
        filtered = From(self.col).select("first","second")
        filtered2 = From(self.col).select("first")
        
        for i in range(3):
            assert not hasattr(filtered2[i], "second")
            assert not hasattr(filtered2[i], "third")

    def test_selecting_no_fields_raises_value_error(self):
        fr = From(self.col)
        msg = re.compile("Selecting with no fields is not valid. " \
                         "When using From\(provider\).select method, " \
                         "please provide a list of expressions or strings as fields.")
        self.assertRaisesEx(ValueError, fr.select, None, exc_pattern=msg)
        self.assertRaisesEx(ValueError, fr.select, exc_pattern=msg)
        self.assertRaisesEx(ValueError, fr.select, [], exc_pattern=msg)
        self.assertRaisesEx(ValueError, fr.select, tuple([]), exc_pattern=msg)
 
    def test_selecting_with_invalid_type_raises_value_error(self):
        fr = From(self.col)  
        msg = re.compile("Selecting with invalid type. " \
                         "When using From\(provider\).select method, " \
                         "please provide a list of expressions or strings as fields.")
        self.assertRaisesEx(ValueError, fr.select, 1, exc_pattern=msg)
        self.assertRaisesEx(ValueError, fr.select, datetime.datetime.now(), exc_pattern=msg)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_unary_expressions
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
import re
import sys
from os.path import dirname, abspath, join
root_path = abspath(join(dirname(__file__), "../../"))
sys.path.insert(0, root_path)

from pynq.expressions import Expression, ConstantExpression, UnaryExpression
from base import BaseUnitTest

class TestUnaryExpressions(BaseUnitTest):

#CollectionLength
    def test_expression_length_of_constant(self):
        a = ConstantExpression(["a","b"])
        node_type = UnaryExpression.CollectionLength
        expr = UnaryExpression(node_type, a)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.rhs, a)

    def test_expression_equal_of_two_constants_representation(self):
        a = ConstantExpression(["a","b"])
        node_type = UnaryExpression.CollectionLength
        expr = UnaryExpression(node_type, a)

        self.assertEquals("len(['a', 'b'])", str(expr))
    
    def test_expression_length_can_only_accept_constant_expression_of_list_types(self):
        a = ConstantExpression(["a","b"])
        b = ConstantExpression("b")
        node_type = UnaryExpression.CollectionLength

        expr = UnaryExpression(node_type, a)
        self.assertRaisesEx(ValueError, UnaryExpression, node_type, "some string", exc_pattern=re.compile("The CollectionLength unary expression can only take ConstantExpressions that hold tuples or lists as parameters."))
        self.assertRaisesEx(ValueError, UnaryExpression, node_type, b, exc_pattern=re.compile("The CollectionLength unary expression can only take ConstantExpressions that hold tuples or lists as parameters."))

#Negate
    def test_expression_negate_of_a_constant(self):
        a = ConstantExpression(10)
        node_type = UnaryExpression.Negate
        expr = UnaryExpression(node_type, a)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.rhs, a)

    def test_expression_negate_of_a_constant_representation(self):
        a = ConstantExpression(10)
        node_type = UnaryExpression.Negate
        expr = UnaryExpression(node_type, a)
        
        self.assertEquals("negate(10)", str(expr))

    def test_nested_negate_expression(self):
        a = ConstantExpression(10)
        node_type = UnaryExpression.Negate

        expr = UnaryExpression(node_type, UnaryExpression(node_type, a))

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.rhs, UnaryExpression), "The right-hand side of the unary expression should be an unary expression as well, but is %s" % expr.rhs.__class__)
        self.assertEquals(expr.rhs.node_type, node_type)
        self.assertEquals(expr.rhs.rhs, a)
    
    def test_nested_negate_expression_representation(self):
        a = ConstantExpression(10)
        node_type = UnaryExpression.Negate

        expr = UnaryExpression(node_type, UnaryExpression(node_type, a))

        self.assertEquals("negate(negate(10))", str(expr))

#Negate
    def test_expression_not_of_a_constant(self):
        a = ConstantExpression(True)
        node_type = UnaryExpression.Not
        expr = UnaryExpression(node_type, a)

        self.assertEquals(expr.node_type, node_type)
        self.assertEquals(expr.rhs, a)

    def test_expression_not_of_a_constant_representation(self):
        a = ConstantExpression(True)
        node_type = UnaryExpression.Not
        expr = UnaryExpression(node_type, a)
        
        self.assertEquals("(not True)", str(expr))

    def test_nested_not_expression(self):
        a = ConstantExpression(True)
        node_type = UnaryExpression.Not

        expr = UnaryExpression(node_type, UnaryExpression(node_type, a))

        self.assertEquals(expr.node_type, node_type)
        self.failUnless(isinstance(expr.rhs, UnaryExpression), "The right-hand side of the unary expression should be an unary expression as well, but is %s" % expr.rhs.__class__)
        self.assertEquals(expr.rhs.node_type, node_type)
        self.assertEquals(expr.rhs.rhs, a)
    
    def test_nested_not_expression_representation(self):
        a = ConstantExpression(True)
        node_type = UnaryExpression.Not

        expr = UnaryExpression(node_type, UnaryExpression(node_type, a))

        self.assertEquals("(not (not True))", str(expr))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
