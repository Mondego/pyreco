__FILENAME__ = AnalogFormulas
class OhmsLaw:

    '''
    This class implements Ohm's law for circuit analysis
    It requires any two parameters and it will calculate the other two.

    Example
    =======

    >>> myCalc = OhmsLaw()
    >>> myCalc.evaluate(p=1254.8,i=7.5)
    {'i': 7.5, 'p': 1254.8, 'r': 22.307555555555556, 'v': 167.30666666666667}

    Methods:
        evaluate(i=None,v=None,r=None,p=None)
    '''

    def evaluate(self, i=None, v=None, r=None, p=None):
        '''
        This method returns a dictionary of current, voltage, power,
        and resistance
        DictKeys: 'i', 'v', 'r', 'p'
        '''
        values = [i, v, r, p]
        if (any((j is not None and j < 0) for j in values)):
            raise Exception('enter positive values')
        else:
            if not p:
                if not r:
                    r = float(v / i)
                    p = float(v) * i
                if not v:
                    v = float(i) * r
                    p = float(i) ** 2 * r
                if not i:
                    i = float(v) / r
                    p = float(v) ** 2 / r
            else:
                if not v and not r:
                    v = float(p) / i
                    r = float(p) / i ** 2
                if not i and not r:
                    i = float(p) / v
                    r = float(p) / i ** 2
                if not i and not v:
                    i = sqrt(float(p) / r)
                    v = float(i) * r
            print(values)
            return {'i': i, 'v': v, 'r': r, 'p': p}


class OhmsLaw_AC:

    '''
    This class implements Ohm's law for circuit analysis using AC current
    It requires any three parameters and it will calculate the other two.

    How to use:
        >>> myCalc = OhmsLaw_AC()
        >>> myCalc.evaluate(p=1254.8,i=7.5,cos=2.0)
        >>> {'i': 7.5, 'p': 1254.8, 'r': 11.15, 'v': 83.625}

    Methods:
        evaluate(i=None,v=None,z=None,p=None,cos=None)
    '''

    def evaluate(self, i=None, v=None, z=None, p=None, c=None):
        '''
        This method returns a dictionary of current, voltage, power,
        resistance and cosine
        DictKeys: 'i', 'v', 'z', 'p','c'
        '''
        values = [i, v, z, p, c]
        if (any((j is not None and j < 0) for j in values)):
            raise Exception('enter positive values')
        else:
            if not p:
                if not z:
                    z = float(v) / i
                    p = float(v) * i * c
                if not v:
                    v = float(i) * z
                    p = float(i) ** 2 * z * c
                if not i:
                    i = float(v / z)
                    p = float((v ** 2 * c) / z)
                if not c:
                    raise Exception('Enter value of \'c\' .Since \'p\' \
                        and \'c\' cant be unknowns at the same time. ')
            else:
                if not v and not z:
                    v = float(p) / (i * c)
                    z = float(p) / (i ** 2)
                if not i and not z:
                    i = float(p) / v
                    z = float(p) / ((i ** 2) * c)
                if not i and not v:
                    i = sqrt(float(p) / (z * c))
                    v = float(i) * z
                if not c and not v:
                    c = float(p) / (i ** 2 * z)
                    v = float(i) * z
                if not c and not i:
                    i = float(v / z)
                    c = float(p / (v * i))
                if not c and not z:
                    z = float(v / i)
                    c = float(p / (v * i))
            print(values)
            return {'i': i, 'v': v, 'z': z, 'p': p, 'c': c}

########NEW FILE########
__FILENAME__ = ExpressionConvert
def makeCompatible(expr):
    '''Used by convertExpression to convert logical operators to english words.'''
    expr = expr.replace('~&', ' NAND ')
    expr = expr.replace('~|', ' NOR ')
    expr = expr.replace('~^', ' XNOR ')
    expr = expr.replace('&', ' AND ')
    expr = expr.replace('|', ' OR ')
    expr = expr.replace('~', ' NOT ')
    expr = expr.replace('^', ' XOR ')
    return '((' + expr + '))'


def createList(expr):
    '''Creates a list which can be used by convertExpression for conversion.'''
    list1 = expr.split('(')
    list2 = []
    list3 = []
    while ('' in list1):
        list1.remove('')

    for string in list1:
        l = string.split()
        list2.extend(l)

    for string in list2:
        sublist = []
        if ')' in string:
            while ')' in string:
                index = string.find(')')
                sublist.append(string[:index])
                sublist.append(')')
                string = string[index + 1:]
            sublist.append(string)
            list3.extend(sublist)
        else:
            list3.extend([string])

    while ('' in list3):
        list3.remove('')
    return (list3)


def mergeNot(case, expr):
    '''Combines NOR gate with othes to minimize the number of gates used.'''
    if expr[-1] == ')':
        index = expr.find('(')
        gate = expr[:index].upper()
        if gate == 'OR' and case == 'general':
            return 'NOR' + expr[index:]
        elif gate == 'AND' and case == 'general':
            return 'NAND' + expr[index:]
        elif gate == 'NOT':
            return expr[index + 1:-1]
        elif gate == 'XOR'and case == 'general':
            return 'XNOR' + expr[index:]
        elif gate == 'XNOR'and case == 'general':
            return 'XOR' + expr[index:]
        elif gate == 'NAND'and case == 'general':
            return 'AND' + expr[index:]
        elif gate == 'NOR'and case == 'general':
            return 'OR' + expr[index:]
    return 'NOT(' + expr + ')'


def to_and_or_not(gate, op1, op2):
    '''Converts a general two input gate and two of its operands to use only OR, NOT, or AND gates'''
    if gate == 'AND' or gate == 'OR':
        return gate + '(' + op1 + ', ' + op2 + ')'
    elif gate == 'NAND':
        return 'NOT(AND(' + '(' + op1 + ', ' + op2 + ')'
    elif gate == 'NOR':
        return 'NOT(OR(' + '(' + op1 + ', ' + op2 + ')'
    elif gate == 'XOR':
        return ('OR(AND(' + op1 + ', ' + mergeNot('general', op2)
                + '), AND(' + mergeNot('general', op1) + ', ' + op2 + '))')
    elif gate == 'XNOR':
        return (
            'OR(AND(' +
            mergeNot(
                'general',
                op1) +
            ', ' +
            mergeNot(
                'general',
                op2) +
            '), AND(' +
            op1 +
            ', ' +
            op2 +
            '))')


def to_nand(gate, op1, op2):
    '''Converts a general two input gate and two of its operands to use only NAND gates'''
    if gate == 'AND':
        return 'NOT(NAND(' + op1 + ', ' + op2 + '))'
    elif gate == 'OR':
        return ('NAND(' + mergeNot('special', op1) + ', '
                + mergeNot('special', op2) + ')')
    elif gate == 'NAND':
        return gate + '(' + op1 + ', ' + op2 + ')'
    elif gate == 'NOR':
        return 'NOT(' + to_nand('OR', op1, op2) + ')'
    elif gate == 'XOR':
        return (
            'NAND(NAND(' +
            op1 +
            ', NAND(' +
            op1 +
            ', ' +
            op2 +
            ')), NAND(' +
            op2 +
            ', NAND(' +
            op1 +
            ', ' +
            op2 +
            ')))')
    elif gate == 'XNOR':
        return 'NOT(' + to_nand('XOR', op1, op2) + ')'


def to_nor(gate, op1, op2):
    '''Converts a general two input gate and two of its operands to use only NOR gates'''
    if gate == 'OR':
        return 'NOT(NOR(' + op1 + ', ' + op2 + '))'
    elif gate == 'AND':
        return ('NOR(' + mergeNot('special', op1) + ', '
                + mergeNot('special', op2) + ')')
    elif gate == 'NOR':
        return gate + '(' + op1 + ', ' + op2 + ')'
    elif gate == 'NAND':
        return 'NOT(' + to_nor('AND', op1, op2) + ')'
    elif gate == 'XNOR':
        return ('NOR(NOR(' + op1 + ', NOR(' + op1 + ', '
                + op2 + ')), NOR(' + op2 + ', NOR(' + op1 + ', ' + op2 + ')))')
    elif gate == 'XOR':
        return 'NOT(' + to_nor('XNOR', op1, op2) + ')'


def remove_not(gate, exp):
    '''Converts a NOT gate and its operand to use the specified gate only.
    The input gate must be NAND or NOR only.'''
    while 'NOT' in exp:
        index = exp.find('NOT(')
        index2 = index
        index3 = exp.find('(', index)
        while True:
            index2 = exp.find(')', index2 + 1)
            index3 = exp.find('(', index3 + 1)
            if index3 == -1 or index3 > index2:
                break
        exp = exp[:index] + gate + '(' + exp[index + 4:index2] + \
            ', ' + exp[index + 4:index2] + ')' + exp[index2 + 1:]
    return exp


def convertExpression(expr, two_input=0, only_nand=0,
                      only_nor=0, only_and_or_not=0):
    ''' Converts logical expression to an implementable form.
    Make two_input 1 if only two input gates must be used.
    Make only_nand 1 if only 2 input nand gates must be used.
    Make only_nor 1 if only 2 input nor gates must be used.
    Make only_and_or_not 1 if only 2 input AND, OR and NOTs be used.
    Error occurs if more than one variable is put to 1.

    convertExpression('( NOT(a) and NOT(b)) or (C and Not(d) and E and F)')
    OR(AND(NOT(a), NOT(b)), AND(C, NOT(d), E, F))

    convertExpression('( NOT(a) and NOT(b)) or (C and Not(d) and E and F)', two_input=1)
    OR(AND(NOT(a), NOT(b)), AND(C, AND(NOT(d), E)))

    convertExpression('( NOT(a) and NOT(b)) or (C and Not(d) and E and F)', only_nand=1)
    NAND(NAND(NAND(a, a), NAND(b, b)), NAND(C, NAND(NAND(NAND(d, d), E), NAND(NAND(d, d), E))))

    convertExpression('( NOT(a) and NOT(b)) or (C and Not(d) and E and F)', only_nor=1)
    NOR(NOR(NOR(a, b), NOR(NOR(C, C), NOR(NOR(d, NOR(E, E)),...
    NOR(d, NOR(E, E))))), NOR(NOR(a, b), NOR(NOR(C, C), NOR(NOR(d, NOR(E, E)), NOR(d, NOR(E, E))))))

    convertExpression('( NOT(a) and NOT(b)) or (C and Not(d) and E and F)', only_and_or_not=1)
    OR(AND(NOT(a), NOT(b)), AND(C, AND(NOT(d), AND(E, F))))
    '''
    expr = makeCompatible(expr)
    list1 = createList(expr)
    while ')' in list1:
        index = list1.index(')')
        if index != len(list1) - 1 and list1[index + 1] == ')':
            last = 0
        else:
            last = 1
        if len(list1) > 1:
            op2 = list1.pop(index - 1)
            gate = list1.pop(index - 2)
            gate = gate.upper()
            if gate != 'NOT':
                try:
                    op1 = list1.pop(index - 3)
                except:
                    list1.insert(index - 1, gate)
                    list1.insert(index - 2, op2)
                    break
                previous_gate = op1[:len(gate)]
                previous_gate = previous_gate.upper()
                next_gate = op2[:len(gate)]
                next_gate = next_gate.upper()
                if (two_input == 0 and gate != 'NAND'and gate != 'NOR')and \
                        (only_nand == 0 and only_nor == 0 and only_and_or_not == 0):
                    if (gate == previous_gate) and (gate == next_gate.upper()):
                        new_element = gate + \
                            '(' + op1[len(gate) + 1:-1] + \
                            ', ' + op2[len(gate) + 1:-1] + ')'
                    elif (gate == previous_gate) and (gate != next_gate.upper()):
                        new_element = gate + \
                            '(' + op1[len(gate) + 1:-1] + ', ' + op2 + ')'
                    elif (gate != previous_gate) and (gate == next_gate.upper()):
                        new_element = gate + \
                            '(' + op1 + ', ' + op2[len(gate) + 1:-1] + ')'
                    else:
                        new_element = gate + '(' + op1 + ', ' + op2 + ')'
                else:
                    if only_nand == 0 and only_nor == 0 and only_and_or_not == 0:
                        new_element = gate + '(' + op1 + ', ' + op2 + ')'
                    elif only_nand == 1 and only_nor == 0 and only_and_or_not == 0:
                        new_element = to_nand(gate, op1, op2)
                    elif only_nand == 0 and only_nor == 1 and only_and_or_not == 0:
                        new_element = to_nor(gate, op1, op2)
                    elif only_nand == 0 and only_nor == 0 and only_and_or_not == 1:
                        new_element = to_and_or_not(gate, op1, op2)
                    else:
                        raise Exception("Invalid Input")
                list1.insert(index - 3, new_element)
                if (last != 1) or list1.index(')') == 1:
                    temp1 = list1.index(')')
                    temp2 = list1.pop(temp1)
            else:
                if only_nand == 0 and only_nor == 0 and only_and_or_not == 0:
                    new_element = mergeNot('general', op2)
                else:
                    new_element = mergeNot('special', op2)
                list1.insert(index - 2, new_element)
                temp1 = list1.index(')')
                temp2 = list1.pop(temp1)
            if list1.count(')') == len(list1) - 1:
                break
    if only_nand == 1:
        return (remove_not('NAND', list1[0]))
    elif only_nor == 1:
        return (remove_not('NOR', list1[0]))
    else:
        return (list1[0])

########NEW FILE########
__FILENAME__ = makebooleanfunction
from BinPy.Algorithms.ExpressionConvert import *
from BinPy.Algorithms.QuineMcCluskey import *
import sys


def make_boolean(vars, min_max, dont_care=None, **kwargs):
    """
    A function which takes in minterms/maxterms and
    returns the Boolean Function and implementable form
    Don't Care Conditions can also be provided (optional)

    Examples
    ========

    >>> from BinPy import *
    >>> le, gf = make_boolean(['A', 'B', 'C'], [1, 4, 7], minterms=True)
    >>> le
    '((A AND (NOT B) AND (NOT C)) OR (A AND B AND C) OR ((NOT A) AND (NOT B) AND C))'
    >>> gf
    'OR(AND(A, NOT(B), NOT(C)), AND(A, B, C), AND(NOT(A), NOT(B), C))'

    """

    ones = []
    while(True):
        if 'minterms' in kwargs:
            if kwargs['minterms'] is True:
                ones = min_max
                if ones[-1] >= pow(2, len(vars)):
                    raise Exception("Error: Invalid minterms")
                break
        elif 'maxterms' in kwargs:
            if kwargs['maxterms'] is True:
                zeros = min_max
                if zeros[-1] >= pow(2, len(vars)):
                    raise Exception("Error: Invalid maxterms")
                for i in range(pow(2, len(vars))):
                    if i not in zeros:
                        ones.append(i)
                break
    if dont_care is not None:
        _dont_care = list(map(int, dont_care))

    qm = QM(vars)
    if dont_care is not None:
        LogicalExpression = qm.get_function(qm.solve(ones, _dont_care)[1])
    else:
        LogicalExpression = qm.get_function(qm.solve(ones)[1])
    GateForm = convertExpression(LogicalExpression)
    return LogicalExpression, GateForm

########NEW FILE########
__FILENAME__ = MooreOptimizer
"""
This class implements a Moore state machine solver. Using the Quine-McCluskey
algorithm it minimizes the necessary next state and output functions for a
given state machine.
"""

from __future__ import print_function
import sys
import random
import itertools
from BinPy.Algorithms.QuineMcCluskey import QM


class StateMachineSolver:

    def __init__(self, state_tran, state_word_len, variables, outputs):
        """
        Initialize the Moore state machine optimizer.

        state_tran: a dictionary; key denotes the target state and value is a
        lambda expression that evaluates to True when the machine should move
        to this target state.
        state_word_len: an integer that holds the count of bits used for
        representing the state
        variables: a list containing the names of the input variables of the
        machine
        outputs: a list containing lambda expressions for calculating the
        outputs of the state machine
        """
        self.state_tran = state_tran
        self.state_word_len = state_word_len
        self.outputs = outputs
        self.next_state = self.InternalOptimizer(state_word_len, variables)
        self.output = self.InternalOptimizer(state_word_len, [])

    def solve(self, state_map):
        """
        Given a state map return the transition and output functions.

        state_map: a dictionary; key is the state and value is the value of the
        state word that identifies this state

        returns: a tuple a,b,c; a is the sum of the functions' complexities,
        b is the next state functions (one for each state word bit) and c is
        the output functions
        """
        self.next_state.state_map = state_map
        self.output.state_map = state_map

        state_bit_on = {}
        state_bit_off = {}
        for i in xrange(self.state_word_len):
            state_bit_on[i] = []
            state_bit_off[i] = []
            for k, v in state_map.iteritems():
                if v & (1 << i):
                    state_bit_on[i].append(k)
                else:
                    state_bit_off[i].append(k)

        total_complexity = 0
        next_state_results = []
        output_results = []
        for i in xrange(self.state_word_len):
            f_on = map(lambda x: self.state_tran[x], state_bit_on[i])
            f_off = map(lambda x: self.state_tran[x], state_bit_off[i])
            complexity, function = self.next_state.solve(f_on, f_off)
            total_complexity += complexity
            next_state_results.append(function)
        for i in xrange(len(self.outputs)):
            complexity, function = self.output.solve([self.outputs[i]])
            total_complexity += complexity
            output_results.append(function)
        return total_complexity, next_state_results, output_results

    def print_solution(self, state_map, solution):
        """ Print a solution. """

        complexity, next_state_funcs, output_funcs = solution

        print ('Complexity = %d' % complexity)
        for i in sorted(state_map.keys()):
            print ('State %d = %d' % (i, state_map[i]))
        for i in xrange(len(next_state_funcs)):
            f = self.next_state.get_function(next_state_funcs[i])
            print ('S%d = %s' % (i, f))
        for i in xrange(len(output_funcs)):
            f = self.output.get_function(output_funcs[i])
            print ('OUT%d = %s' % (i, f))
        print ('-' * 80)

    """ This class is used internally by the Moore state machine optimizer. """

    class InternalOptimizer:

        def __init__(self, state_word_len, variables):
            """ Initialize the internal helper class. """

            self.state_word_len = state_word_len
            self.variables = variables
            variable_names = map(
                lambda i: 'S%d' %
                i, xrange(
                    self.state_word_len))
            variable_names += self.variables
            self.qm = QM(variable_names)

        def solve(self, f_on, f_off=None):
            """
            Returns a function that satisfies the conditions given.

            f_on: a list of lambda expressions; if one of the lambda
            expressions evaluates to True then the requested function
            should evaluate to True
            f_off: a list of lambda expressions; if one of them evaluates
            to True then the requested function whould evaluate to False

            returns: a tuple a,b; a is the complexity of the function and
            b is the function
            """
            self.state_env = self.State()
            self.variables_env = self.Variables(self.variables)

            c = self.state_word_len
            d = len(self.variables)
            ones = []
            dc = set(i for i in xrange(1 << (d + c)))
            for variables_word in xrange(1 << d):
                self.variables_env.word = variables_word
                for state, state_word in self.state_map.iteritems():
                    self.state_env.state = state
                    on = self.evaluate(f_on)
                    if f_off is None:
                        off = not on
                    else:
                        off = self.evaluate(f_off)
                    assert not (on and off)
                    if on:
                        ones.append(variables_word << c | state_word)
                        dc.remove(variables_word << c | state_word)
                    elif off:
                        dc.remove(variables_word << c | state_word)

            dc = list(dc)
            return self.qm.solve(ones, dc)

        def evaluate(self, f_array):
            """
            Evaluates a list of lambda expressions in the state and variables
            environment. The lambda expressions are terms of an OR expression.

            f_array: a list of lambda expressions

            returns: the logical OR after evaluate the lambda expression in the
            setup environment
            """
            for f in f_array:
                if f(self.state_env, self.variables_env):
                    return True
            return False

        class State:

            """
            This class provides access to the state word from the lambda
            expressions.
            """

            def __getitem__(self, item):
                return self.state == item

        class Variables:

            """
            This class provides access to the input variables from the
            lambda expressions.
            """

            def __init__(self, variables):
                self.variables = {}
                for i in xrange(len(variables)):
                    self.variables[variables[i]] = 1 << i

            def __getitem__(self, item):
                return bool(self.word & self.variables[item])

        def get_function(self, minterms):
            """ Retrieve a human readable form of the given function. """

            return self.qm.get_function(minterms)


class StateMachineOptimizer:

    """ This class is the base for creating a Moore state machine
    optimizer.
    """

    def __init__(
            self,
            state_tran,
            state_word_len,
            variables,
            outputs,
            **kwargs):
        # Initialize the state machine optimizer.
        self.state_tran = state_tran
        self.state_word_len = state_word_len
        self.sms = StateMachineSolver(state_tran, state_word_len, variables,
                                      outputs)

        self.print_all = kwargs.get('print_all', False)
        self.print_best = kwargs.get('print_best', False)

    def calc_total(self):
        """
        Calculate the total count of possible permutations of state
        configurations.
        """
        total = 1
        begin = (1 << self.state_word_len) - len(self.state_tran) + 1
        end = (1 << self.state_word_len) + 1
        for i in xrange(begin, end):
            total *= i
        return total


class StateMachineOptimizer_AllPermutations(StateMachineOptimizer):

    """
    This class implements a Moore state machine optimizer that tries
    all possible permutations for assignment of state word values to
    states.
    """

    def optimize(self):
        total = self.calc_total()
        min_complexity = 99999999
        counter = 0
        elements = range(1 << self.state_word_len)
        for permutation in itertools.permutations(elements, len(self.state_tran)):
            counter += 1
            if counter & 0xff == 0:
                sys.stderr.write('%%%3.2f done\r' % (100.0 * counter / total))
            state_map = {}
            for i in xrange(len(self.state_tran)):
                state_map[i] = permutation[i]
            solution = self.sms.solve(state_map)
            if self.print_all:
                print ('%r' % ((state_map, solution),))
            if solution[0] < min_complexity:
                min_complexity = solution[0]
                if self.print_best:
                    self.sms.print_solution(state_map, solution)


class StateMachineOptimizer_Random(StateMachineOptimizer):

    """
    This class implements a Moore state machine optimizer that tries
    permutations at random.
    """

    def optimize(self, tries=1000):
        total = self.calc_total()

        min_complexity = 99999999
        for counter in xrange(tries):
            if counter & 0xff == 0:
                sys.stderr.write(
                    'Tried %d random permutations out of %d.\r' %
                    (counter, total))

            permutation = range(1 << self.state_word_len)
            random.shuffle(permutation)

            state_map = {}
            for i in xrange(len(self.state_tran)):
                state_map[i] = permutation[i]
            solution = self.sms.solve(state_map)
            if self.print_all:
                print ('%r' % ((state_map, solution),))

            if solution[0] < min_complexity:
                min_complexity = solution[0]
                if self.print_best:
                    self.sms.print_solution(state_map, solution)


class StateMachineOptimizer_FileAndVerify(StateMachineOptimizer):

    """
    This class is used for testing the state machine optimizer.
    """

    def optimize(self, file):
        for line in open(file, 'r').readlines():
            input, expected_output = eval(line)
            output = self.sms.solve(input)
            assert expected_output == output


def main():
    state_tran = {
        0: lambda s, v: s[5],
        1: lambda s, v: (s[0] and not v['A'])or(s[1] and not v['B']),
        2: lambda s, v: (s[0] and v['A'])or(s[2] and not v['B']),
        3: lambda s, v: s[1] and v['B'],
        4: lambda s, v: s[2] and v['B'],
        5: lambda s, v: s[3] or s[4],
    }

    outputs = [
        lambda s, v: not s[5],
        lambda s, v: s[1] or s[3],
        lambda s, v: s[2] or s[3] or s[4],
    ]

    variables = ['A', 'B']

    state_word_len = 3
    opti = StateMachineOptimizer_Random(
        state_tran,
        state_word_len,
        variables,
        outputs,
        print_best=True)
    opti.optimize()

    # state_word_len = 3
    # sms = StateMachineSolver(state_tran, state_word_len, variables, outputs)
    # state_map = {0:0,1:1,2:2,3:3,4:4,5:5}
    # solution = sms.solve(state_map)
    # sms.print_solution(state_map,solution)

    # state_word_len = 3
    # opti = StateMachineOptimizer_AllPermutations(state_tran, state_word_len, variables, outputs, print_best = True)
    # opti.optimize()

    # state_word_len = 4
    # opti = StateMachineOptimizer_Random(state_tran, state_word_len, variables, outputs, print_best = True)
    # opti.optimize(tries = 500)

    # state_word_len = 3
    # opti = StateMachineOptimizer_FileAndVerify(state_tran, state_word_len, variables, outputs)
    # opti.optimize('testdata.txt')

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = QuineMcCluskey
#!/usr/bin/env python

"""
This class implements the Quine-McCluskey algorithm for minimization of boolean
functions.

Based on code from Robert Dick <dickrp@eecs.umich.edu> and Pat Maupin
<pmaupin@gmail.com>. Most of the original code was re-written for performance
reasons.

>>> qm = QM(['A','B'])

>>> qm.get_function(qm.solve([])[1])
'0'
>>> qm.get_function(qm.solve([1,3],[0,2])[1])
'1'
>>> qm.get_function(qm.solve([0,1,2,3])[1])
'1'
>>> qm.get_function(qm.solve([3])[1])
'(A AND B)'
>>> qm.get_function(qm.solve([0])[1])
'((NOT A) AND (NOT B))'
>>> qm.get_function(qm.solve([1,3])[1])
'A'ls

>>> qm.get_function(qm.solve([1],[3])[1])
'A'
>>> qm.get_function(qm.solve([2,3])[1])
'B'
>>> qm.get_function(qm.solve([0,2])[1])
'(NOT A)'
>>> qm.get_function(qm.solve([0,1])[1])
'(NOT B)'
>>> qm.get_function(qm.solve([1,2,3])[1])
'(A OR B)'
>>> qm.get_function(qm.solve([0,1,2])[1])
'((NOT B) OR (NOT A))'
"""


class QM:

    def __init__(self, variables):
        """
    Initialize the Quine-McCluskey solver.

    variables: a list of strings that are the names of the variables used in
    the boolean functions
    """

        self.variables = variables
        self.numvars = len(variables)

    def solve(self, ones, dont_care=[]):
        """
    Executes the Quine-McCluskey algorithm and returns its results.

    ones: a list of indices for the minterms for which the function evaluates
    to 1
    dc: a list of indices for the minterms for which we do not care about the
    function evaluation

    returns: a tuple a,b; a is the complexity of the result and b is a list of
    minterms which is the minified boolean function expressed as a sum of
    products
    """

        # Handle special case for functions that always evaluate to True or
        # False.
        if len(ones) == 0:
            return 0, '0'
        if len(ones) + len(dont_care) == 1 << self.numvars:
            return 0, '1'

        primes = self.compute_primes(ones + dont_care)
        return self.unate_cover(list(primes), ones)

    def compute_primes(self, cubes):
        """
    Find all prime implicants of the function.

    cubes: a list of indices for the minterms for which the function evaluates
    to 1 or don't-care.
    """

        sigma = []
        for i in range(self.numvars + 1):
            sigma.append(set())
        for i in cubes:
            sigma[bitcount(i)].add((i, 0))

        primes = set()
        while sigma:
            nsigma = []
            redundant = set()
            for c1, c2 in zip(sigma[:-1], sigma[1:]):
                nc = set()
                for a in c1:
                    for b in c2:
                        m = merge(a, b)
                        if m is not None:
                            nc.add(m)
                            redundant |= set([a, b])
                nsigma.append(nc)
            primes |= set(c for cubes in sigma for c in cubes) - redundant
            sigma = nsigma
        return primes

    def unate_cover(self, primes, ones):
        """
    Use the prime implicants to find the essential prime implicants of the
    function, as well as other prime implicants that are necessary to cover
    the function. This method uses the Petrick's method, which is a technique
    for determining all minimum sum-of-products solutions from a prime implicant
    chart.

    primes: the prime implicants that we want to minimize.
    ones: a list of indices for the minterms for which we want the function to
    evaluate to 1.
    """

        chart = []
        for one in ones:
            column = []
            for i in range(len(primes)):
                if (one & (~primes[i][1])) == primes[i][0]:
                    column.append(i)
            chart.append(column)

        covers = []
        if len(chart) > 0:
            covers = [set([i]) for i in chart[0]]
        for i in range(1, len(chart)):
            new_covers = []
            for cover in covers:
                for prime_index in chart[i]:
                    x = set(cover)
                    x.add(prime_index)
                    append = True
                    for j in range(len(new_covers) - 1, -1, -1):
                        if x <= new_covers[j]:
                            del new_covers[j]
                        elif x > new_covers[j]:
                            append = False
                    if append:
                        new_covers.append(x)
            covers = new_covers

        min_complexity = 99999999
        for cover in covers:
            primes_in_cover = [primes[prime_index] for prime_index in cover]
            complexity = self.calculate_complexity(primes_in_cover)
            if complexity < min_complexity:
                min_complexity = complexity
                result = primes_in_cover

        return min_complexity, result

    def calculate_complexity(self, minterms):
        """
    Calculate the complexity of the given function. The complexity is calculated
    based on the following rules:
    A NOT gate adds 1 to the complexity.
    A n-input AND or OR gate adds n to the complexity.

    minterms: a list of minterms that form the function

    returns: an integer that is the complexity of the function

    >>> qm = QM(['A','B','C'])

    >>> qm.calculate_complexity([(1,6)])
    0
    >>> qm.calculate_complexity([(0,6)])
    1
    >>> qm.calculate_complexity([(3,4)])
    2
    >>> qm.calculate_complexity([(7,0)])
    3
    >>> qm.calculate_complexity([(1,6),(2,5),(4,3)])
    3
    >>> qm.calculate_complexity([(0,6),(2,5),(4,3)])
    4
    >>> qm.calculate_complexity([(0,6),(0,5),(4,3)])
    5
    >>> qm.calculate_complexity([(0,6),(0,5),(0,3)])
    6
    >>> qm.calculate_complexity([(3,4),(7,0),(5,2)])
    10
    >>> qm.calculate_complexity([(1,4),(7,0),(5,2)])
    11
    >>> qm.calculate_complexity([(2,4),(7,0),(5,2)])
    11
    >>> qm.calculate_complexity([(0,4),(7,0),(5,2)])
    12
    >>> qm.calculate_complexity([(0,4),(0,0),(5,2)])
    15
    >>> qm.calculate_complexity([(0,4),(0,0),(0,2)])
    17
    """

        complexity = len(minterms)
        if complexity == 1:
            complexity = 0
        mask = (1 << self.numvars) - 1
        for minterm in minterms:
            masked = ~minterm[1] & mask
            term_complexity = bitcount(masked)
            if term_complexity == 1:
                term_complexity = 0
            complexity += term_complexity
            complexity += bitcount(~minterm[0] & masked)

        return complexity

    def get_function(self, minterms):
        """
    Return in human readable form a sum of products function.

    minterms: a list of minterms that form the function

    returns: a string that represents the function using operators AND, OR and
    NOT.
    """

        if isinstance(minterms, str):
            return minterms

        def parentheses(glue, array):
            if len(array) > 1:
                return ''.join(['(', glue.join(array), ')'])
            else:
                return glue.join(array)

        or_terms = []
        for minterm in minterms:
            and_terms = []
            for j in range(len(self.variables)):
                if minterm[0] & 1 << j:
                    and_terms.append(self.variables[j])
                elif not minterm[1] & 1 << j:
                    and_terms.append('(NOT %s)' % self.variables[j])
            or_terms.append(parentheses(' AND ', and_terms))
        return parentheses(' OR ', or_terms)


def bitcount(i):
    """ Count set bits of the input. """

    res = 0
    while i > 0:
        res += i & 1
        i >>= 1
    return res


def is_power_of_two_or_zero(x):
    """
  Determine if an input is zero or a power of two. Alternative, determine if an
  input has at most 1 bit set.
  """

    return (x & (~x + 1)) == x


def merge(i, j):
    """ Combine two minterms. """
    if i[1] != j[1]:
        return None
    y = i[0] ^ j[0]
    if not is_power_of_two_or_zero(y):
        return None
    return (i[0] & j[0], i[1] | y)

########NEW FILE########
__FILENAME__ = base
from BinPy import *


class Resistor:

    """
    This Class implements the Resistor, having the following parameters:
    '+' : Resistor end at positive potential
    '-' : Resistor end at negative potential
    'r' : Resistance value
    'i' : Current flowing through the resistor

    Example:
        >>> from BinPy import *
        >>> params = {'r':5}
        >>> r = Resistor(params)
        >>> r.getParams()
        {'i': 0, '+': 0, 'r': 5, '-': 0}
        >>> r.setVoltage(Connector(5), Connector(0))
        {'i': 1.0, '+': 5, 'r': 5, '-': 0}
        >>> r.setCurrent(10)
        {'i': 10, '+': 50, 'r': 5, '-': 0}
        >>> r.setResistance(10)
        {'i': 5.0, '+': 50, 'r': 10, '-': 0}

    """

    def __init__(self, params):
        self.params = {'+': Connector(0), '-': Connector(0), 'i': 0, 'r':
                       0}
        for i in params:
            self.params[i] = params[i]

    def setResistance(self, value):
        self.params['r'] = value
        self.params['i'] = (
            self.params['+'].state - self.params['-'].state) / self.params['r']
        return self.params

    def getParams(self):
        return self.params

    def setCurrent(self, value):
        self.params['i'] = value
        self.params['+'].state = self.params['-'].state + \
            (self.params['i'] * self.params['r'])
        return self.params

    def setVoltage(self, val1, val2):
        if not(isinstance(val1, Connector) and isinstance(val2, Connector)):
            raise Exception(
                "Invalid Voltage Values, Expecting a Connector Class Object")
        self.params['+'] = val1
        self.params['-'] = val2
        self.params['i'] = (
            self.params['+'].state - self.params['-'].state) / self.params['r']
        return self.params

    def __repr__(self):
        return str(self.params['r'])

########NEW FILE########
__FILENAME__ = source
from math import *
from BinPy import *


class Source:

    "This class represents a base class for the signal source"

    def __init__(self, equation, params):
        self.params = params
        self.equation = equation

    def setParam(self, param, value):
        if not isinstance(self.params[param], type(value)):
            raise Exception("Invalid Value")
        self.params[param] = value
        self.trigger()

    def setParams(self, params):
        for i in params:
            self.setParam(i, params[i])

    def getParams(self):
        self.trigger()
        return self.params

    def setEquation(self, equation):
        self.equation = equation
        self.trigger()

    def evaluate(self):
        for i in self.params:
            exec("%s=%f" % (i, self.params[i]))
        self.val = eval(self.equation)
        return self.val

    def setoutput(self, param, value):
        if not isinstance(value, Connector):
            raise Exception("Expecting a Connector Class Object")
        self.params[param] = value


class VoltageSource(Source):

    def __init__(self, equation, params):
        Source.__init__(self, equation, params)
        self.params.update({'H': Connector(0), 'L': Connector(0)})
        self.trigger()

    def trigger(self):
        self.params['H'].state = self.evaluate() + self.params['L'].state


class CurrentSource(Source):

    def __init__(self, equation, params):
        Source.__init__(self, equation, params)
        self.params.update({'H': Connector(0), 'L': Connector(0)})
        self.trigger()

    def trigger(self):
        self.params['i'] = self.evaluate()


class SinWaveVoltageSource(VoltageSource):

    def __init__(self, amplitude=0, frequency=0, time=0, epoch=0):

        equation = 'V*round(sin(radians((w*t)+e)), 2)'
        params = {'V': amplitude, 'w': frequency, 't': time, 'e': epoch}
        VoltageSource.__init__(self, equation, params)


class CosWaveVoltageSource(VoltageSource):

    def __init__(self, amplitude=0, frequency=0, time=0, epoch=0):

        equation = 'V*round(cos(radians((w*t)+e)), 2)'
        params = {'V': amplitude, 'w': frequency, 't': time, 'e': epoch}
        VoltageSource.__init__(self, equation, params)


class SinWaveCurrentSource(CurrentSource):

    def __init__(self, amplitude=0, frequency=0, time=0, epoch=0):

        equation = 'I*round(sin(radians((w*t)+e)), 2)'
        params = {'I': amplitude, 'w': frequency, 't': time, 'e': epoch}
        CurrentSource.__init__(self, equation, params)


class CosWaveCurrentSource(CurrentSource):

    def __init__(self, amplitude=0, frequency=0, time=0, epoch=0):

        equation = 'I*round(cos(radians((w*t)+e)), 2)'
        params = {'I': amplitude, 'w': frequency, 't': time, 'e': epoch}
        CurrentSource.__init__(self, equation, params)

########NEW FILE########
__FILENAME__ = base
from __future__ import print_function
import warnings
import logging
import sys


consoleHandler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
consoleHandler.setFormatter(formatter)
logger = logging.getLogger('Main Logger')
logger.addHandler(consoleHandler)

try:
    import IPython
    ipython_version = IPython.__version__
except ImportError:
    ipython_version = None


def ipython_exception_handler(shell, excType, excValue, traceback, tb_offset=0):
    logger.error("", exc_info=(excType, excValue, traceback))


def init_logging(log_level):
    logger.setLevel(log_level)


def read_logging_level(log_level):
    levels_dict = {
        1: logging.DEBUG, "debug": logging.DEBUG,
        2: logging.INFO, "info": logging.INFO,
        3: logging.WARNING, "warning": logging.WARNING,
        4: logging.ERROR, "error": logging.ERROR,
        5: logging.CRITICAL, "critical": logging.CRITICAL
    }

    if isinstance(log_level, str):
        log_level = log_level.lower()

    if log_level in levels_dict:
        return levels_dict[log_level]
    else:
        print("The logging level given is not valid")
        return None


def get_logging_level():
    """
    This function prints the current logging level of the main logger.
    """
    levels_dict = {
        10: "DEBUG",
        20: "INFO",
        30: "WARNING",
        40: "ERROR",
        50: "CRITICAL"
    }

    print(
        "The current logging level is:",
        levels_dict[
            logger.getEffectiveLevel()])


def set_logging(log_level, myfilename=None):
    """
    This function sets the threshold for the logging system and, if desired,
    directs the messages to a logfile. Level options:

    'DEBUG' or 1
    'INFO' or 2
    'WARNING' or 3
    'ERROR' or 4
    'CRITICAL' or 5

    If the user is on the interactive shell and wants to log to file, a custom
    excepthook is set. By default, if logging to file is not enabled, the way
    errors are displayed on the interactive shell is not changed.
    """

    if myfilename and ipython_version:
        try:
            if ipython_version.startswith("0.10"):
                __IPYTHON__.set_custom_exc(
                    (Exception,), ipython_exception_handler)
            else:
                ip = get_ipython()
                ip.set_custom_exc((Exception,), ipython_exception_handler)
        except NameError:  # In case the interactive shell is not being used
            sys.exc_clear()

    level = read_logging_level(log_level)

    if level and myfilename:
        fileHandler = logging.FileHandler(filename=myfilename)
        fileHandler.setLevel(level)
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)
        logger.removeHandler(consoleHandler)  # Console logging is disabled.
        print("Now logging to", myfilename, "with level", log_level)
    elif level:
        print("Now logging with level", log_level)

    logger.setLevel(level)

########NEW FILE########
__FILENAME__ = combinational
from BinPy.Gates.gates import *
import math


class HalfAdder():

    """This Class implements Half Adder, Arithmetic sum of two bits and return its
    Sum and Carry
    Output: [CARRY, SUM]
    Example:
        >>> from BinPy import *
        >>> ha = HalfAdder(0, 1)
        >>> ha.output()
        [0, 1]

    """

    def __init__(self, *inputs):

        if len(inputs) is not 2:
            raise Exception("ERROR: Number of arguments not consistent")

        self.inputs = list(inputs[:])
        self.S = XOR(self.inputs[0], self.inputs[1])
        self.C = AND(self.inputs[0], self.inputs[1])

    def set_input(self, index, value):
        if index > 1 or index < 0:
            raise Exception("ERROR: Not a valid index value")
        self.inputs[index] = value
        if index == 0:
            self.S.setInput(0, self.inputs[0])
            self.C.setInput(0, self.inputs[0])
        elif index == 1:
            self.S.setInput(1, self.inputs[1])
            self.C.setInput(1, self.inputs[1])

    def set_inputs(self, *inputs):
        self.inputs = list(inputs)[:]
        self.S.setInputs(*inputs)
        self.C.setInputs(*inputs)

    def set_output(self, index, value):
        if not isinstance(value, Connector):
            raise Exception("ERROR: Expecting a Connector Class Object")
        if index == 0:
            self.C.setOutput(value)
        elif index == 1:
            self.S.setOutput(value)

    def output(self):
        return [self.C.output(), self.S.output()]


class FullAdder():

    """This Class implements Full Adder, Arithmetic sum of three bits and
    return its Sum and Carry
    Output: [CARRY, SUM]
    Example:
        >>> from BinPy import *
        >>> fa = FullAdder(0, 1, 1)
        >>> fa.output()
        [1, 0]
    """

    def __init__(self, *inputs):
        if len(inputs) is not 3:
            raise Exception("ERROR: Number of arguments are inconsistent")

        self.inputs = list(inputs)[:]
        # Connector Object to connect the two half adders
        self.con1 = Connector()
        self.ha1 = HalfAdder(self.inputs[0], self.inputs[1])
        self.ha1.set_output(1, self.con1)
        self.ha2 = HalfAdder(self.con1, self.inputs[2])
        self.con2 = Connector()
        self.con3 = Connector()
        self.ha1.set_output(0, self.con2)
        self.ha2.set_output(0, self.con3)
        self.or1 = OR(self.con2, self.con3)

    def set_input(self, index, value):
        if index > 3 or index < 0:
            raise Exception("ERROR: Not a valid index number")
        self.inputs[index] = value
        if index == 0:
            self.ha1.set_input(0, self.inputs[0])
        elif index == 1:
            self.ha1.set_input(1, self.inputs[1])
        elif index == 2:
            self.ha2.set_input(1, self.inputs[2])

    def set_inputs(self, *inputs):
        if len(inputs) is not 3:
            raise Exception("ERROR: Number of arguments are inconsistent")
        self.inputs = list(inputs)[:]
        self.ha1.set_inputs(self.inputs[0], self.inputs[1])
        self.ha2.set_input(1, self.inputs[2])

    def set_output(self, index, value):
        if not isinstance(value, Connector):
            raise Exception("ERROR: Expecting a Connector Class Object")

        if index == 0:
            self.or1.setOutput(value)
        elif index == 1:
            self.ha2.set_output(1, value)
        else:
            raise Exception("ERROR: Invalid index passed")

    def output(self):
        return [self.or1.output(), self.ha2.output()[1]]


class HalfSubtractor():

    """This Class implements Half Subtractor, Arithmetic difference of two bits and return its
    Difference and Borrow output
    Output: [BORROW, DIFFERENCE]
    Example:
        >>> from BinPy import *
        >>> hs = HalfSubtractor(0, 1)
        >>> hs.output()
        [1, 1]

    """

    def __init__(self, *inputs):
        if len(inputs) is not 2:
            raise Exception("Number of arguments are inconsistent")
        self.inputs = list(inputs)[:]
        self.D = XOR(self.inputs[0], self.inputs[1])
        self.N = NOT(self.inputs[0])
        self.con = Connector()
        self.N.setOutput(self.con)
        self.B = AND(self.con, self.inputs[1])

    def set_input(self, index, value):
        if index > 3 or index < 0:
            raise Exception("ERROR: Invalid Index passed")
        self.inputs[index] = value
        if index == 0:
            self.D.setInput(0, self.inputs[0])
            self.N.setInput(self.inputs[0])
        elif index == 1:
            self.D.setInput(1, self.inputs[1])
            self.B.setInput(1, self.inputs[1])

    def set_inputs(self, *inputs):
        if len(inputs) is not 2:
            raise Exception("Number of arguments are inconsistent")
        self.inputs = list(inputs)[:]
        self.D.setInputs(self.inputs[0], self.inputs[1])
        self.N.setInput(self.inputs[0])
        self.B.setInputs(self.con, self.inputs[1])

    def set_output(self, index, value):
        if not isinstance(value, Connector):
            raise Exception("ERROR: Expecting a Connector Class Object")
        if index == 0:
            self.B.setOutput(value)
        elif index == 1:
            self.D.setOutput(value)
        else:
            raise Exception("ERROR: Invalid Index passed")

    def output(self):
        return [self.B.output(), self.D.output()]


class FullSubtractor(GATES):

    """This Class implements Full Subtractor, Arithmetic difference of three bits and
    return its Difference and Borrow
    Output: [BORROW, DIFFERENCE]
    Example:
        >>> from BinPy import *
        >>> fs = FullSubtractor(0, 1, 1)
        >>> fs.output()
        [0, 1]
    """

    def __init__(self, *inputs):
        if len(inputs) is not 3:
            raise Exception("ERROR: Number of arguments inconsistent")
        self.inputs = list(inputs)[:]
        self.hs1 = HalfSubtractor(self.inputs[0], self.inputs[1])
        self.con1 = Connector()
        self.hs1.set_output(1, self.con1)
        self.hs2 = HalfSubtractor(self.con1, self.inputs[2])
        self.con2 = Connector()
        self.con3 = Connector()
        self.hs1.set_output(0, self.con1)
        self.hs2.set_output(0, self.con2)
        self.or1 = OR(self.con1, self.con2)

    def set_input(self, index, value):
        if index > 3 or index < 0:
            raise Exception("ERROR: Invalid Index passed")
        self.inputs[index] = value
        if index == 0:
            self.hs1.set_input(0, self.inputs[0])
        elif index == 1:
            self.hs1.set_input(1, self.inputs[1])
        elif index == 2:
            self.hs2.set_input(1, self.inputs[2])

    def set_inputs(self, *inputs):
        if len(inputs) is not 3:
            raise Exception("ERROR: Number of arguments inconsistent")
        self.inputs = list(inputs)[:]
        self.hs1.set_inputs(self.inputs[0], self.inputs[1])
        self.hs2.set_input(1, self.inputs[2])

    def set_output(self, index, value):
        if not isinstance(value, Connector):
            raise Exception("ERROR: Expecting a Connector Class Object")
        if index == 0:
            self.or1.setOutput(value)
        elif index == 1:
            self.hs2.set_output(1, value)
        else:
            raise Exception("ERROR: Invalid Index passed")

    def output(self):
        return [self.or1.output(), self.hs2.output()[1]]


class MUX(GATES):

    """
    This class can be used to create MUX in your circuit. MUX is used to select
    a single output line out of many inputs. This class can be used as any 2^n X
    n Multiplexer where n is the number of select lines used to select the input
    out of 2^n input lines.
    INPUT:          nth index has nth input value, input should be power of 2
    OUTPUT:         single output, 1 or 0
    SELECT LINES:   In binary form, select line for 4 will be 1 0 0

    Example:
        >>> from BinPy import *
        >>> mux = MUX(0, 1)            "MUX takes its 2^n inputs (digital or Connector)"
        >>> mux.selectLines(0)         "Put select Line"
        >>> mux.output()
        0
        >>> mux.selectLine(0, 1)       "Select line at index 0 is changed to 1"
        >>> mux.output()
        1
        >>> mux.setInput(1, 0)         "Input line at index 1 is changed to 0"
        >>> mux.output()
        0

    """

    def __init__(self, *inputs):
        if not (len(inputs) > 1 and (len(inputs) & (len(inputs) - 1) == 0)):
            raise Exception("ERROR: Number inputs should be a power of 2")
        self.selects = []
        GATES.__init__(self, list(inputs))

    def selectLines(self, *select):
        if not pow(2, len(select)) == len(self.inputs):
            raise Exception(
                "ERROR: No. of Select lines are inconsistent with the inputs")
        self.selects = list(select)
        self._updateSelectConnections()
        self.trigger()

    def selectLine(self, index, value):
        if index >= len(self.selects):
            self.selects.append(value)
        else:
            self.selects[index] = value
        if isinstance(value, Connector):
            value.tap(self, 'input')
            self.trigger()

    def setInput(self, index, value):
        if index >= len(self.inputs):
            self.inputs.append(value)
        else:
            self.inputs[index] = value
        if isinstance(value, Connector):
            value.tap(self, 'input')
            self.trigger()

    def trigger(self):
        if len(self.selects) == 0:
            return
        if not (len(self.inputs) > 1 and (len(self.inputs) & (len(self.inputs) - 1) == 0)):
            raise Exception("ERROR: Number of inputs should be a power of 2")
        bstr = ''
        for i in self.selects:
            if isinstance(i, Connector):
                bstr = bstr + str(i.state)
            else:
                bstr = bstr + str(i)
        try:
            if isinstance(self.inputs[int(bstr, 2)], Connector):
                self._updateResult(self.inputs[int(bstr, 2)].state)
            else:
                self._updateResult(self.inputs[int(bstr, 2)])
        except IndexError:
            raise Exception(
                "Error: Select lines are inconsistent with Input lines")
        if self.outputType:
            self.outputConnector.trigger()

    def _updateSelectConnections(self):
        for i in self.selects:
            if isinstance(i, Connector):
                i.tap(self, 'input')

    def __str__(self):
        return self.buildStr("MUX")


class DEMUX(GATES):

    """
    This class can be used to create DEMUX in your circuit. DEMUX is used to select
    It takes single input and n select lines and decode the select lines into BCD form
    base upon the input. In case of high input, it works as a decoder.
    INPUT:          Single Input, 1 or 0
    OUTPUT:         BCD form of select lines in case of high input, else low output
    SELECT LINES:   nth select line at nth index

    Example:
        >>> from BinPy import *
        >>> demux = DEMUX(0)             "DEMUX takes 1 input (digital or Connector)"
        >>> demux.selectLines(0)         "Put select Lines"
        >>> demux.output()
        [0, 0]
        >>> demux.selectLine(0, 1)       "Select line at index 0 is changed to 1"
        >>> demux.output()
        [0, 1]
    """

    def __init__(self, *inputs):
        if not len(inputs) == 1:
            raise Exception("ERROR: Input should be 0/1")
        self.selects = []
        GATES.__init__(self, list(inputs))
        self.outputType = []
        self.outputConnector = []

    def selectLines(self, *select):
        if not len(select) != 0:
            raise Exception(
                "ERROR: Number of select lines should be greater than zero")
        self.selects = list(select)
        for i in range(pow(2, len(select))):
            self.outputType.append(0)
            self.outputConnector.append(None)
        self._updateConnections()
        self.trigger()

    def selectLine(self, index, value):
        if index >= len(self.selects):
            self.selects.append(value)
            for i in range(len(self.outputType), pow(2, len(self.selects))):
                self.outputType.append(0)
                self.outputConnector.append(None)
        else:
            self.selects[index] = value
        if isinstance(value, Connector):
            value.tap(self, 'input')
            self.trigger()

    def setInput(self, index, value):
        if not index == 0:
            raise Exception("ERROR: There should be a single input")
        self.inputs[index] = value
        if isinstance(value, Connector):
            value.tap(self, 'input')
            self.trigger()

    def trigger(self):
        if len(self.selects) == 0:
            return
        out = []
        for i in range(pow(2, len(self.selects))):
            out.append(0)
            bstr = ''
        for i in self.selects:
            if isinstance(i, Connector):
                bstr = bstr + str(i.state)
            else:
                bstr = bstr + str(i)
        if isinstance(self.inputs[0], Connector):
            out[int(bstr, 2)] = self.inputs[0].state
            self._updateResult(out)
        else:
            out[int(bstr, 2)] = self.inputs[0]
            self._updateResult(out)

    def setInputs(self, *inputs):
        if not len(inputs) == 1:
            raise Exception("ERROR: There should be a single Input")
        self.inputs = list(inputs)
        self._updateConnections()
        self.trigger()

    def setOutput(self, index, value):
        if not isinstance(value, Connector):
            raise Exception("ERROR: Expecting a Connector Class Object")
        value.tap(self, 'output')
        self.outputType[index] = 1
        self.outputConnector[index] = value
        self.trigger()

    def _updateResult(self, value):
        self.result = value
        for i in range(len(value)):
            if self.outputType[i] == 1:
                self.outputConnector[i].state = value[i]

    def _updateSelectConnections(self):
        for i in self.selects:
            if isinstance(i, Connector):
                i.tap(self, 'input')

    def __str__(self):
        return self.buildStr("DEMUX")


class Decoder(GATES):

    """
    This class can be used to create decoder in your circuit.
    Input is taken as Binary String and returns the equivalent BCD form.
    INPUT:      n Binary inputs, nth input ant the nth index
    OUTPUT:     Gives equivalent BCD form

    Example:
        >>> decoder = Decoder(0)            "Decoder with 1 input, 0"
        >>> decoder.output()
        [1, 0]
        >>> decoder.setInputs(0, 1)         "sets the new inputs to the decoder"
        [0, 1, 0, 1]

    """

    def __init__(self, *inputs):
        if len(inputs) == 0:
            raise Exception("ERROR: Input Length should be greater than zero")
        GATES.__init__(self, list(inputs))
        self.outputType = []
        self.outputConnector = []
        for i in range(pow(2, len(inputs))):
            self.outputType.append(0)
            self.outputConnector.append(None)

    def trigger(self):
        if isinstance(self.outputType, int):
            return
        out = []
        for i in range(pow(2, len(self.inputs))):
            out.append(0)
            bstr = ''
        for i in self.inputs:
            if isinstance(i, Connector):
                bstr = bstr + str(i.state)
            else:
                bstr = bstr + str(i)
        out[int(bstr, 2)] = 1
        self._updateResult(out)

    def setInputs(self, *inputs):
        if len(inputs) == 0:
            raise Exception("ERROR: Input length must be greater than zero")
        self.inputs = list(inputs)
        for i in range(len(self.outputType), pow(2, len(self.inputs))):
            self.outputType.append(0)
            self.outputConnector.append(None)
        self._updateConnections()
        self.trigger()

    def setInput(self, index, value):
        if index >= len(self.inputs):
            self.inputs.append(value)
            for i in range(len(self.outputType), pow(2, len(self.inputs))):
                self.outputType.append(0)
                self.outputConnector.append(None)
        else:
            self.inputs[index] = value
        if isinstance(value, Connector):
            value.tap(self, 'input')
            self.trigger()

    def setOutput(self, index, value):
        if not isinstance(value, Connector):
            raise Exception("ERROR: Expecting a Connector Class Object")
        value.tap(self, 'output')
        self.outputType[index] = 1
        self.outputConnector[index] = value
        self.trigger()

    def _updateResult(self, value):
        self.result = value
        for i in range(len(value)):
            if self.outputType[i] == 1:
                self.outputConnector[i].state = value[i]

    def __str__(self):
        return self.buildStr("Decoder")


class Encoder(GATES):

    """
    This class can be used to create encoder in your circuit.
    It converts the input BCD form to binary output.
    It works as the inverse of the decoder
    INPUT:      Input in BCD form, length of input must me in power of 2
    OUTPUT:     Encoded Binary Form

    Example:
        >>> encoder = Encoder(0, 1)             "Encoder with BCD input 01 "
        >>> encoder.output()                    "Binary Form"
        [1]
        >>> encoder.setInputs(0, 0, 0, 1)       "Sets the new inputs"
        [1 , 1]
    """

    def __init__(self, *inputs):
        if not (len(inputs) > 1 and (len(inputs) & (len(inputs) - 1) == 0)):
            raise Exception("ERROR: Number of inputs should be a power of 2")
        if not (inputs.count(1) == 1 or list(x.state for x in
                                             filter(lambda i: isinstance(i, Connector), inputs)).count(1) == 1):
            raise Exception("Invalid Input")
        GATES.__init__(self, list(inputs))
        self.outputType = []
        self.outputConnector = []
        for i in range(int(math.log(len(self.inputs), 2))):
            self.outputType.append(0)
            self.outputConnector.append(None)

    def trigger(self):
        if isinstance(self.outputType, int):
            return
        if not (len(self.inputs) > 1 and (len(self.inputs) & (len(self.inputs) - 1) == 0)):
            raise Exception("ERROR: Number of inputs should be a power of 2")
        temp = self.inputs[:]
        for i in range(len(temp)):
            if isinstance(temp[i], Connector):
                temp[i] = temp[i].state
        bstr = bin(temp.index(1))[2:]
        while len(bstr) < math.log(len(self.inputs), 2):
            bstr = '0' + bstr
        out = list(bstr)
        out = map(int, out)
        self._updateResult(list(out))

    def setInputs(self, *inputs):
        if not (len(inputs) > 1 and (len(inputs) & (len(inputs) - 1) == 0)):
            raise Exception("ERROR: Number of inputs should be a power of 2")
        if not (inputs.count(1) == 1 or list(x.state for x in
                                             filter(lambda i: isinstance(i, Connector), inputs)).count(1) == 1):
            raise Exception("ERROR: Invalid Input")
        self.inputs = list(inputs)
        for i in range(len(self.outputType), int(math.log(len(self.inputs), 2))):
            self.outputType.append(0)
            self.outputConnector.append(None)
            self._updateConnections()
            self.trigger()

    def setInput(self, index, value):
        temp = self.inputs[:]
        if index >= len(temp):
            temp.append(value)
            if not (temp.count(1) == 1 or list(x.state for x in
                                               filter(lambda i: isinstance(i, Connector), temp)).count(1) == 1):
                raise Exception("ERROR: Invalid Input")
                self.inputs.append(value)
            for i in range(len(self.outputType), int(math.log(len(self.inputs), 2))):
                self.outputType.append(0)
                self.outputConnector.append(None)
        else:
            temp[index] = value
            if not (temp.count(1) == 1 or list(x.state for x in
                                               filter(lambda i: isinstance(i, Connector), temp)).count(1) == 1):
                raise Exception("ERROR: Invalid Input")
                self.inputs[index] = value

        if isinstance(value, Connector):
            value.tap(self, 'input')
            self.trigger()

    def setOutput(self, index, value):
        if not isinstance(value, Connector):
            raise Exception("ERROR: Expecting a Connector Class Object")
        value.tap(self, 'output')
        self.outputType[index] = 1
        self.outputConnector[index] = value
        self.trigger()

    def _updateResult(self, value):
        self.result = value
        for i in range(len(value)):
            if self.outputType[i] == 1:
                self.outputConnector[i].state = value[i]

    def __str__(self):
        return self.buildStr("Encoder")

########NEW FILE########
__FILENAME__ = constants
# Voltage Values for Logic States

LOGIC_HIGH_VOLT = 5
LOGIC_LOW_VOLT = 0

# Logic State values

LOGIC_HIGH_STATE = 1
LOGIC_LOW_STATE = 0
LOGIC_DONT_CARE_STATE = -1
LOGIC_HIGH_IMPEDANCE_STATE = None

# Logic Threshold value

LOGIC_THRESHOLD_VOLT = 2.5

########NEW FILE########
__FILENAME__ = parseEquation
from __future__ import print_function
from BinPy import *
import sys


class Expr:

    """
    This class is used to parse any expression which contain boolean variables.
    Input String can be in the form of logical operators which can be parsed to
    Gates by this class. This is also used to obtain the truth tables"

    Logical Operator form:  Function takes only equation as an input.
    Gates Form:             Needs The variable inputs also as an argument.
    Examples:
        >>> from BinPy import *
        >>> expr = Expr('A & B | C')
        >>> expr.parse()
        'AND(OR(C,B),A)'
        >>> expr.truthTable()
        A B C O
        0 0 0 0
        0 0 1 0
        0 1 0 0
        0 1 1 0
        1 0 0 0
        1 0 1 1
        1 1 0 1
        1 1 1 1
        >>> expr = Expr('AND(NOT(A), B)', 'A', 'B')
        >>> expr.parse()
        'AND(NOT(A),B)'
        >>> expr.truthTable()
        A B O
        0 0 0
        0 1 1
        1 0 0
        1 1 0
    """

    def __init__(self, equation, *var):
        try:
            self.no_error = True

            if len(var) > 0:
                self.var = list(var)
                self.equation = equation
            else:
                self.var = []
                self.equation = self.eqnParse(equation)
        except:
            print("Invalid Arguments")

    def parse(self):
        return self.equation

    def truthTable(self):
        for i in self.var:
            print(i, end=" ")
        print('O')
        for i in range(0, pow(2, len(self.var))):
            num = bin(i)[2:].zfill(len(self.var))
            num = list(map(int, list(num)))
            for j in range(len(num)):
                vars()[self.var[j]] = num[j]
                print(num[j], end=" ")
                if j == len(num) - 1:
                    if isinstance(eval(self.equation), GATES):
                        print(eval(self.equation).output())
                    else:
                        print(eval(self.equation))

    def removeBraces(self, position, equation):
        """
        Removes braces due to clubbing of the gates
        position indicates the index of the clubbed gate
        """
        eq = equation
        if position != -1:
            eq = equation[:position]
            stack = 0
            for i in equation[position:]:
                if (i == '(') and (stack != -1):
                    stack += 1
                    eq += i
                    # print i,stack,eq
                elif (i == ')') and (stack != -1):
                    stack -= 1
                    if stack == 0:
                        # If the current index corresponds to the ) of the
                        # removed gate.
                        stack = -1
                        # print i,stack,eq
                    else:
                        eq += i
                        # print i,stack,eq
                else:
                    eq += i
                    # print i,stack,eq
        return eq

    def findMatchingBrace(self, position, string):
        """
        Returns the index of the opposite matching brace for the brace at string[position]
        """
        # print eq
        stack = 0
        pos = position
        if position != -1:
            if string[pos] != '(':
                return -1
            for i in string[position:]:
                if (i == '(') and (stack != -1):
                    stack += 1
                if (i == ')') and (stack != -1):
                    stack -= 1
                    if stack == 0:
                        return pos
                pos += 1
        return -1

    def eqnParse(self, eqn, isOperandtype=str.isalpha):
        # The second parameter is to support the passing of equations for pin class [ only numbers ]
        # Removes white spaces
        eqn = eqn.replace(' ', '')
        equation_final = ''
        operators = []  # Stack of operators
        operands = []  # Stack of operands
        flag = False
        i = 0
        while i < len(eqn):
            # print eqn[i]
            if not self.no_error:
                break
            if eqn[i] in ['~', '&', '|', '^']:
                if flag:
                    operands.append(eqn[i - 1])
                    flag = False
                operators.append(eqn[i])
            elif eqn[i] == '(':
                if flag:
                    print('ERROR: Equation error at ' + eqn[i - 1:i + 1])
                    no_error = False
                    break
                pos = self.findMatchingBrace(i, eqn)
                if pos == -1:
                    print ('ERROR: Equation error - Unmatched braces')
                    no_error = False
                    break
                tmp = self.eqnParse(eqn[i + 1:pos])
                operands.append(tmp)
                i = pos
            elif isOperandtype(eqn[i]):
                if flag:
                    # 2 letter operand [ eg 12 --> corresponds to PIN 12 ]
                    operands.append(eqn[i - 1:i + 1])
                    flag = False
                else:
                    flag = True
                    # Check if the operand is a two letter operand, in the next
                    # iteration.
            else:
                print ('ERROR: Unrecognized characters in equation ' + eqn[i])
                self.no_error = False
            i += 1

        if flag:
            operands.append(eqn[-1])
            flag = False

        if not self.no_error:
            return
        self.var = operands[:]

        while len(operators) > 0:
            operator = operators.pop()
            if operator == '~':
                operands.append('NOT(' + operands.pop() + ')')
            elif operator == '&':
                operands.append(
                    'AND(' +
                    operands.pop() +
                    ', ' +
                    operands.pop() +
                    ')')
            elif operator == '|':
                operands.append(
                    'OR(' +
                    operands.pop() +
                    ', ' +
                    operands.pop() +
                    ')')
            elif operator == '^':
                operands.append(
                    'XOR(' +
                    operands.pop() +
                    ', ' +
                    operands.pop() +
                    ')')

        equation_final = operands.pop()

        # Optimizing the final equation by clubbing the gates together:

        unoptimized = True
        while unoptimized:
            unoptimized = False
            pos = equation_final.find('NOT(AND(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('NOT(AND(', 'NAND(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('NOT(OR(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('NOT(OR(', 'NOR(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('NOT(XOR(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('NOT(XOR(', 'XNOR(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('AND(AND(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('AND(AND(', 'AND(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('OR(OR(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('OR(OR(', 'OR(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('XOR(XOR(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('XOR(XOR(', 'XOR(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('NAND(NAND(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('NAND(NAND(', 'NAND(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('NOR(NOR(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('NOR(NOR(', 'NOR(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('XNOR(XNOR(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('XNOR(XNOR(', 'XNOR(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('NAND(AND(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('NAND(AND(', 'NAND(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

            pos = equation_final.find('NOR(OR(')
            if pos != -1:
                unoptimized = True
                equation_final = equation_final[
                    :pos] + equation_final[pos:].replace('NOR(OR(', 'NOR(', 1)
                equation_final = self.removeBraces(pos, equation_final)
                # print equation_final

        return equation_final if self.no_error else None

########NEW FILE########
__FILENAME__ = ExpressionConvertExample

# coding: utf-8

# An example to demostrate functionality of ExpressionConvert.py

# In[1]:

from __future__ import print_function
from BinPy.Algorithms.ExpressionConvert import *


# In[2]:

# Given Expression:
expr = '~(((A^B)|(~a^b^C))) ~^ c'


# In[3]:

# Obtained Expression
converted = convertExpression(expr)

print(converted)


# In[4]:

# Given Expression:
expr = '((A AND B)xor(NOT(B) and C) xor(C and NOT(D)))or   E or NOT(F)'


# In[5]:

# Obtained Expression
converted = convertExpression(expr)

print(converted)


# In[6]:

# Obtained Expression with two input gate contraint
converted2 = convertExpression(expr, two_input=1)

print(converted2)


# In[7]:

# Given Expression:
expr = '(A XOR B XOR C)'


# In[8]:

# Obtained Expression
converted = convertExpression(expr)

print(converted)


# In[9]:

# Obtained Expression with two input gate contraint
converted2 = convertExpression(expr, two_input=1)

print(converted2)


# In[10]:

# Equivalent Expression with only AND, OR & NOT gates
converted3 = convertExpression(expr, only_and_or_not=1)

print(converted3)


# In[11]:

# Given Expression
expr = 'A XOR B'


# In[12]:

# Equivalent Expression with only NAND gates
converted = convertExpression(expr, only_nand=1)

print(converted)


# In[13]:

# Equivalent Expression with only NOR gates
converted2 = convertExpression(expr, only_nor=1)

print(converted2)

########NEW FILE########
__FILENAME__ = BinaryAdder
from __future__ import print_function
from BinPy.Combinational.combinational import *
""" Examples for BinaryAdder class """
print ("\n---Initializing the BinaryAdder class--- ")
print (
    "\n---Input is of the form ([Binary number 1],[ BInary number 2], Carry]")
print ("ba = BinaryAdder([0, 1], [1, 0], 0)")
ba = BinaryAdder([0, 1], [1, 0], 0)
print ("\n---Output of BinaryAdder")
print ("ba.output()")
print (ba.output())
print("Output is of the form [ [SUM], CARRY]")
print ("\n---Input changes---")
print ("ba.setInput(1, [0]) #Input at index 1 is changed to 0")
ba.setInput(1, [0])
print ("\n---New Output of the BinaryAdder---")
print (ba.output())
print ("\n---Changing the number of inputs---")
print ("No need to set the number, just change the inputs")
print ("Input length must be three")
print ("ba.setInputs(1, 0, 1)")
ba.setInputs([1], [0], 1)
print ("\n---To get the input states---")
print ("ba.getInputStates()")
print (ba.getInputStates())
print ("\n---New output of BinaryAdder---")
print (ba.output())
print ("\n\n---Using Connectors as the input lines---")
print ("Take a Connector")
print ("conn = Connector()")
conn = Connector()
print ("\n---Set Output of Binary Adder to Connector conn---")
print ("ba.setOutput(0, conn) # sets the conn at index 0 ")
ba.setOutput(0, conn)
print ("\n---Put this connector as the input to gate1---")
print ("gate1 = AND(conn, 0)")
gate1 = AND(conn, 0)
print ("\n---Output of the gate1---")
print ("gate1.output()")
print (gate1.output())
print ("Information about Binary Adder instance can be found by")
print ("ba")
print (ba)

########NEW FILE########
__FILENAME__ = BinarySubtractor
from __future__ import print_function
from BinPy.Combinational.combinational import *
""" Examples for BinarySubtractor class """
print ("\n---Initializing the BinarySubtractor class--- ")
print (
    "\n---Input is of the form ([Binary number 1],[ Binary number 2], Carry]")
print ("bs = BinarySubtractor([0, 1], [1, 0], 0)")
bs = BinarySubtractor([0, 1], [1, 0], 0)
print ("\n---Output of BinarySubtractor")
print ("bs.output()")
print (bs.output())
print("Output is of the form [ [Difference], Borrow]")
print ("\n---Input changes---")
print ("bs.setInput(1, [0]) #Input at index 1 is changed to 0")
bs.setInput(1, [0])
print ("\n---New Output of the BinarySubtractor---")
print (bs.output())
print ("\n---Changing the number of inputs---")
print ("No need to set the number, just change the inputs")
print ("Input length must be three")
print ("bs.setInputs(1, 0, 1)")
bs.setInputs([1], [0], 1)
print ("\n---To get the input states---")
print ("bs.getInputStates()")
print (bs.getInputStates())
print ("\n---New output of BinarySubtractor---")
print (bs.output())
print ("\n\n---Using Connectors as the input lines---")
print ("Take a Connector")
print ("conn = Connector()")
conn = Connector()
print ("\n---Set Output of Binary Subtractor to Connector conn---")
print ("bs.setOutput(0, conn) # sets the conn at index 0 ")
bs.setOutput(0, conn)
print ("\n---Put this connector as the input to gate1---")
print ("gate1 = AND(conn, 0)")
gate1 = AND(conn, 0)
print ("\n---Output of the gate1---")
print ("gate1.output()")
print (gate1.output())
print ("Information about bs instance can be found by")
print ("bs")
print (bs)

########NEW FILE########
__FILENAME__ = Decoder

# coding: utf-8

# Example for Decoder class

# In[1]:

# Imports
from __future__ import print_function
from BinPy.Combinational.combinational import *


# In[2]:

# Initializing the Decoder class

decoder = Decoder(0, 1)

# Output of decoder

print (decoder.output())


# In[3]:

# Input changes

# Input at index 1 is changed to 0

decoder.setInput(1, 0)

# New Output of the decoder

print (decoder.output())


# In[4]:

# Changing the number of inputs
# No need to set the number, just change the inputs
# Input must be power of 2

decoder.setInputs(1, 0, 0)

# To get the input states

print (decoder.getInputStates())

# New output of decoder

print (decoder.output())


# In[5]:

# Using Connectors as the input lines

conn = Connector()

# Set Output of decoder to Connector conn

decoder.setOutput(1, conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 1)

# Output of the gate1

print (gate1.output())


# In[6]:

# Information about decoder instance can be found by

print (decoder)

########NEW FILE########
__FILENAME__ = DEMUX

# coding: utf-8

# Example for DEMUX class.

# In[1]:

from __future__ import print_function
from BinPy.Combinational.combinational import *


# In[2]:

# Initializing the DEMUX class

# Must be a single input

demux = DEMUX(1)

# Put select lines

# Select Lines must be power of 2

demux.selectLines(0)

# Output of demux

print (demux.output())


# In[3]:

# Input changes

# Input at index 1 is changed to 0

demux.setInput(0, 0)

# New Output of the demux

print (demux.output())


# In[4]:

# Get Input States

print (demux.getInputStates())


# In[5]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of demux to Connector conn

# sets conn as the output at index 0

demux.setOutput(0, conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 0)

# Output of the gate1

print (gate1.output())


# In[6]:

# Changing select lines

# selects input line 2

demux.selectLine(0, 1)

# New output of demux

print (demux.output())


# In[7]:

# Information about demux instance can be found by

print (demux)

########NEW FILE########
__FILENAME__ = Encoder

# coding: utf-8

# Example for Encoder class

# In[1]:

from __future__ import print_function
from BinPy.Combinational.combinational import *


# In[2]:

# Initializing the Encoder class

# Exacly 1 input must be 1

encoder = Encoder(0, 1)

# Output of encoder

print (encoder.output())


# In[3]:

# Changing the number of inputs

# No need to set the number, just change the inputs
# Input must be power of 2
# encoder.setInputs(1, 0, 0) #Inputs must be power of 2

encoder.setInputs(0, 0, 0, 1)

# To get the input states

print (encoder.getInputStates())


# In[4]:

# New output of encoder

print (encoder.output())


# In[5]:

# Using Connectors as the input lines
# Take a Connector

conn = Connector()

# Set Output of decoder to Connector conn

encoder.setOutput(1, conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 1)

# Output of the gate1

print (gate1.output())


# In[6]:

# Information about encoder instance can be found by

print (encoder)

########NEW FILE########
__FILENAME__ = FullAdder
from __future__ import print_function
from BinPy.Combinational.combinational import *
""" Examples for FullAdder class """
print ("\n---Initializing the FullAdder class--- ")
print ("\n---Input is of the form [Bit1, Bit2, Carry]")
print ("fa = FullAdder(0, 1, 0)")
fa = FullAdder(0, 1, 0)
print ("\n---Output of FullAdder")
print ("fa.output()")
print (fa.output())
print("Output is of the form [SUM, CARRY]")
print ("\n---Input changes---")
print ("fa.setInput(1, 0) #Input at index 1 is changed to 0")
fa.setInput(1, 0)
print ("\n---New Output of the FullAdder---")
print (fa.output())
print ("\n---Changing the number of inputs---")
print ("No need to set the number, just change the inputs")
print ("Input length must be three")
print ("fa.setInputs(1, 0, 1)")
fa.setInputs(1, 0, 1)
print ("\n---To get the input states---")
print ("fa.getInputStates()")
print (fa.getInputStates())
print ("\n---New output of FullAdder---")
print (fa.output())
print ("\n\n---Using Connectors as the input lines---")
print ("Take a Connector")
print ("conn = Connector()")
conn = Connector()
print ("\n---Set Output of Full Adder to Connector conn---")
print ("fa.setOutput(0, conn) # sets the conn at index 0 ")
fa.setOutput(0, conn)
print ("\n---Put this connector as the input to gate1---")
print ("gate1 = AND(conn, 0)")
gate1 = AND(conn, 0)
print ("\n---Output of the gate1---")
print ("gate1.output()")
print (gate1.output())
print ("Information about fa instance can be found by")
print ("fa")
print (fa)

########NEW FILE########
__FILENAME__ = FullSubtractor
from __future__ import print_function
from BinPy.Combinational.combinational import *
""" Examples for FullSubtractor class """
print ("\n---Initializing the FullSubtractor class--- ")
print ("\n---Input is of the form [Bit1, Bit2, Borrow]")
print ("fs = FullSubtractor(0, 1, 0)")
fs = FullSubtractor(0, 1, 0)
print ("\n---Output of FullSubtractor")
print ("fs.output()")
print (fs.output())
print("Output is of the form [Difference, Borrow")
print ("\n---Input changes---")
print ("fs.setInput(1, 0) #Input at index 1 is changed to 0")
fs.setInput(1, 0)
print ("\n---New Output of the FullSubtractor---")
print (fs.output())
print ("\n---Changing the number of inputs---")
print ("No need to set the number, just change the inputs")
print ("Input length must be three")
print ("fs.setInputs(1, 0, 1)")
fs.setInputs(1, 0, 1)
print ("\n---To get the input states---")
print ("fs.getInputStates()")
print (fs.getInputStates())
print ("\n---New output of FullSubtractor---")
print (fs.output())
print ("\n\n---Using Connectors as the input lines---")
print ("Take a Connector")
print ("conn = Connector()")
conn = Connector()
print ("\n---Set Output of Full Subtractor to Connector conn---")
print ("fs.setOutput(0, conn) # sets the conn at index 0 ")
fs.setOutput(0, conn)
print ("\n---Put this connector as the input to gate1---")
print ("gate1 = AND(conn, 0)")
gate1 = AND(conn, 0)
print ("\n---Output of the gate1---")
print ("gate1.output()")
print (gate1.output())
print ("Information about full subtractor instance can be found by")
print ("fs")
print (fs)

########NEW FILE########
__FILENAME__ = HalfAdder

# coding: utf-8

# Example for Half Adder class.

# In[1]:

# Imports

from __future__ import print_function
from BinPy.Combinational.combinational import *


# In[2]:

# Initializing the HalfAdder class

ha = HalfAdder(0, 1)

# Output of HalfAdder

print (ha.output())


# In[3]:

# The output is of the form [SUM, CARRY]"

# Input changes

# Input at index 1 is changed to 0

ha.setInput(1, 0)

# New Output of the HalfAdder

print (ha.output())


# In[4]:

# Changing the number of inputs

# No need to set the number, just change the inputs

# Input length must be two

ha.setInputs(1, 1)

# To get the input states

print (ha.getInputStates())


# In[5]:

# New output of HalfAdder

print (ha.output())


# In[6]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output at index to Connector conn

ha.setOutput(0, conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 0)

# Output of the gate1

print (gate1.output())


# In[7]:

# Information about ha instance can be found by

print (ha)

########NEW FILE########
__FILENAME__ = HalfSubtractor

# coding: utf-8

# Example for Half Subtractor class

# In[1]:

# Imports
from __future__ import print_function
from BinPy.Combinational.combinational import *


# In[2]:

# Initializing the HalfSubtractor class

hs = HalfSubtractor(0, 1)

# Output of HalfSubtractor

print (hs.output())


# In[3]:

# The output is of the form [DIFFERENCE, BORROW]

# Input changes

# Input at index 1 is changed to 0

hs.setInput(1, 0)

# New Output of the HalfSubtractor

print (hs.output())


# In[4]:

# Changing the number of inputs

# No need to set the number, just change the inputs

# Input length must be two

hs.setInputs(1, 1)

# To get the input states

print (hs.getInputStates())


# In[5]:

# New output of HalfSubtractor

print (hs.output())


# In[6]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output at index to Connector conn

hs.setOutput(0, conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 0)

# Output of the gate1

print (gate1.output())


# In[7]:

# Information about hs instance can be found by

print (hs)

########NEW FILE########
__FILENAME__ = MUX

# coding: utf-8

# Example for MUX class.

# In[1]:

# Imports
from __future__ import print_function
from BinPy.Combinational.combinational import *


# In[2]:

# Initializing the MUX class

mux = MUX(0, 1)

# Put select lines

mux.selectLines(0)

# Output of mux

print (mux.output())


# In[3]:

# Input changes

# Input at index 1 is changed to 0

mux.setInput(1, 0)

# New Output of the mux

print (mux.output())


# In[4]:

# Changing the number of inputs

# No need to set the number, just change the inputs

# Input must be power of 2

mux.setInputs(1, 0, 0, 1)

# To get the input states

print (mux.getInputStates())


# In[5]:

# New output of mux

print (mux.output())


# In[6]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of mux to Connector conn

mux.setOutput(conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 0)

# Output of the gate1

print (gate1.output())


# In[7]:

# Changing select lines

# Selects input line 2

mux.selectLine(0, 1)

# New output of mux

print (mux.output())


# In[8]:

# Information about mux instance can be found by

print (mux)

########NEW FILE########
__FILENAME__ = Expr

# coding: utf-8

# Examples for Expr class

# In[1]:

# imports
from __future__ import print_function
from BinPy.dev import *


# In[2]:

# Initializing the Expr class

expr = Expr('A & B | C')

# Parsing the expression

print (expr.parse())


# In[3]:

# Alternate way of defining an expression

# Input is of the format: Expr(expression, variables)

expr1 = Expr('AND(NOT(A), B)', 'A', 'B')

print (expr.parse())


# In[4]:

# Printing the truth table

print(expr.truthTable())

########NEW FILE########
__FILENAME__ = AND

# coding: utf-8

# Examples for AND class

# In[1]:

from __future__ import print_function
from BinPy.Gates import *


# In[2]:

# Initializing the AND class

gate = AND(0, 1)

# Output of the AND gate

print (gate.output())


# In[3]:

# Input changes

# Input at index 1 is changed to 0

gate.setInput(1, 0)

# New Output of the AND gate

print (gate.output())


# In[4]:

# Changing the number of inputs

# No need to set the number, just change the inputs

gate.setInputs(1, 1, 1, 1)


# In[5]:

# To get the input states

print (gate.getInputStates())


# In[6]:

# New output of the AND gate

print (gate.output())


# In[7]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of gate to Connector conn

gate.setOutput(conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 0)


# In[8]:

# Output of the gate1

print (gate1.output())


# In[9]:

# Information about gate instance

print (gate)

########NEW FILE########
__FILENAME__ = Connector

# coding: utf-8

# Examples for Connector class

# In[1]:

# imports
from __future__ import print_function
from BinPy.Gates import *


# In[2]:

# Initializing the Connector class
conn = Connector()

# Input contains the initial value of the Connector

# State of the Connector object

print (conn.state)


# In[3]:

# Calling the connector intance returns its state

print (conn())


# In[4]:

# Tapping the conector

gate = OR(0, 1)
conn.tap(gate, "output")


# In[5]:

# Untapping the connector

conn.untap(gate, "output")


# In[6]:

# Checking the relation ship of gate with the Connector 'conn'

print(conn.isOutputof(gate))

print(conn.isInputof(gate))


# In[7]:

# Set Output of gate to Connector conn

gate.setOutput(conn)


# In[8]:

# Checking the relation ship of gate with the Connector 'conn'

print(conn.isOutputof(gate))

print(conn.isInputof(gate))


# In[9]:

# Put this connector as the input to gate1

gate1 = AND(conn, 0)


# In[10]:

# Output of the gate1

print (gate1.output())


# In[11]:

# Information about conn instance

print (conn)

########NEW FILE########
__FILENAME__ = NAND

# coding: utf-8

# Examples for NAND class

# In[1]:

from __future__ import print_function
from BinPy.Gates import *


# In[2]:

# Initializing the NAND class

gate = NAND(0, 1)

# Output of the NAND gate

print (gate.output())


# In[3]:

# Input changes

# Input at index 1 is changed to 0

gate.setInput(1, 0)

# New Output of the NAND gate

print (gate.output())


# In[4]:

# Changing the number of inputs

# No need to set the number, just change the inputs

gate.setInputs(1, 1, 1, 1)

# To get the input states

print (gate.getInputStates())

# New output of the NAND gate

print (gate.output())


# In[5]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of gate to Connector conn

gate.setOutput(conn)
# Put this connector as the input to gate1

gate1 = NAND(conn, 0)

# Output of the gate1

print (gate1.output())


# In[6]:

# Information about gate instance

print (gate)

########NEW FILE########
__FILENAME__ = NOR

# coding: utf-8

# Examples for NOR class

# In[1]:

# imports
from __future__ import print_function
from BinPy.Gates import *


# In[2]:

# Initializing the NOR class

gate = NOR(0, 1)

# Output of the NOR gate

print (gate.output())


# In[3]:

# Input changes

# Input at index 1 is changed to 0

gate.setInput(1, 0)

# New Output of the NOR gate

print (gate.output())


# In[4]:

# Changing the number of inputs

# No need to set the number, just change the inputs

gate.setInputs(1, 1, 1, 1)

# To get the input states

print (gate.getInputStates())


# In[5]:

# New output of the NOR gate

print (gate.output())


# In[6]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of gate to Connector conn

gate.setOutput(conn)

# Put this connector as the input to gate1

gate1 = NOR(conn, 0)


# In[7]:

# Output of the gate1

print (gate1.output())


# In[8]:

# Information about gate instance

print (gate)

########NEW FILE########
__FILENAME__ = NOT

# coding: utf-8

# Examples for NOT class

# In[1]:

# imports
from __future__ import print_function
from BinPy.Gates import *


# In[2]:

# Initializing the NOT class

gate = NOT(0)

# Output of the NOT gate

print (gate.output())


# In[3]:

# Input is changed to 0

gate.setInput(1)

# To get the input states

print (gate.getInputStates())


# In[4]:

# New Output of the NOT gate

print (gate.output())


# In[5]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of gate to Connector conn

gate.setOutput(conn)

# Put this connector as the input to gate1

gate1 = NOT(conn)

# Output of the gate1

print (gate1.output())


# In[6]:

# Information about gate instance

print (gate)

########NEW FILE########
__FILENAME__ = OR

# coding: utf-8

# Examples for OR class

# In[1]:

# imports
from __future__ import print_function
from BinPy.Gates import *


# In[2]:

# Initializing the OR class

gate = OR(0, 1)

# Output of the OR gate

print (gate.output())


# In[3]:

# Input changes

# Input at index 1 is changed to 0

gate.setInput(1, 0)

# New Output of the OR gate

print (gate.output())


# In[4]:

# Changing the number of inputs

# No need to set the number, just change the inputs

gate.setInputs(1, 1, 1, 1)

# To get the input states

print (gate.getInputStates())


# In[5]:

# New output of the OR gate

print (gate.output())


# In[6]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of gate to Connector conn

gate.setOutput(conn)

# Put this connector as the input to gate1

gate1 = OR(conn, 0)

# Output of the gate1

print (gate1.output())


# In[7]:

# Information about gate instance

print (gate)

########NEW FILE########
__FILENAME__ = Tree

# coding: utf-8

# Examples for Tree class.

# In[1]:

from __future__ import print_function
from BinPy.Gates import *


# In[2]:

# Initializing the Tree class

# Initialize some gates to form a tree

# Input is of the form Tree(root element, depth of treversal)

g1 = AND(0, 1)
g2 = AND(1, 1)
g3 = AND(g1, g2)

tree = Tree(g3, 2)

# Backtrack traversal of tree upto a depth given

print (tree.backtrack())


# In[3]:

# Print tree traversed

# print (tree.printTree())


# In[4]:

# print (tree())


# In[5]:

print (tree)

########NEW FILE########
__FILENAME__ = XNOR

# coding: utf-8

# Examples for XNOR class.

# In[1]:

from __future__ import print_function
from BinPy.Gates import *


# In[2]:

# Initializing the XNOR class

gate = XNOR(0, 1)


# In[3]:

# Output of the XNOR gate

print (gate.output())


# In[4]:

# Input changes

# Input at index 1 is changed to 0

gate.setInput(1, 0)


# In[5]:

# New Output of the XNOR gate

print (gate.output())


# In[6]:

# Changing the number of inputs

# No need to set the number, just change the inputs

gate.setInputs(1, 1, 1, 1)


# In[7]:

# To get the input states

print (gate.getInputStates())


# In[8]:

# New output of the XNOR gate

print (gate.output())


# In[9]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()


# In[10]:

# Set Output of gate to Connector conn

gate.setOutput(conn)


# In[11]:

# Put this connector as the input to gate1

gate1 = XNOR(conn, 0)


# In[12]:

# Output of the gate1

print (gate1.output())


# In[13]:

# Information about gate instance

print (gate)

########NEW FILE########
__FILENAME__ = XOR

# coding: utf-8

# Examples for XOR class

# In[1]:

# imports
from __future__ import print_function
from BinPy.Gates import *


# In[2]:

# Initializing the XOR class

gate = XOR(0, 1)

# Output of the XOR gate

print (gate.output())


# In[3]:

# Input changes
# Input at index 1 is changed to 0

gate.setInput(1, 0)

# New Output of the XOR gate

print (gate.output())


# In[4]:

# Changing the number of inputs

# No need to set the number, just change the inputs

gate.setInputs(1, 1, 1, 1)

# To get the input states

print (gate.getInputStates())


# In[5]:

# New output of the XOR gate

print (gate.output())


# In[6]:

# Using Connectors as the input lines

# Take a Connector

conn = Connector()


# In[7]:

# Set Output of gate to Connector conn

gate.setOutput(conn)


# In[8]:

# Put this connector as the input to gate1

gate1 = XOR(conn, 0)


# In[9]:

# Output of the gate1

print (gate1.output())


# In[10]:

# Information about gate instance

print (gate)

########NEW FILE########
__FILENAME__ = IC4000
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4000

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4000:

ic = IC_4000()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {3: 1, 4: 1, 5: 1, 7: 0, 8: 1, 11: 0, 12: 0, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(9, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4001
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4001

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4001:

ic = IC_4001()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(13, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4002
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4002

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4002:

ic = IC_4002()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(13, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4011
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4011

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4011:

ic = IC_4011()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(11, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4012
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4012

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4012:

ic = IC_4012()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(13, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4023
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4023

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4023:

ic = IC_4023()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 7: 0, 8: 1, 11: 0, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(9, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4025
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4025

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4025:

ic = IC_4025()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 7: 0, 8: 1, 11: 0, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(9, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4068
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4068

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4068:

ic = IC_4068()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 1, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 0, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0}) -- \n

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(13, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4069
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4069

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4069:

ic = IC_4069()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0}) -- \n

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(2, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4070
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4070

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4070:

ic = IC_4070()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(3, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4071
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4071

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4071:

ic = IC_4071()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0}) -- \n

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(3, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4072
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4072

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4072:

ic = IC_4072()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0}) -- \n

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(13, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4073
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4073

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4073:

ic = IC_4073()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0}) -- \n

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(9, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4075
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4075

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4075:

ic = IC_4075()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 7: 0, 8: 1, 11: 0, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0}) -- \n

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(9, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4077
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4077

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4077:

ic = IC_4077()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0}) -- \n

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(11, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4078
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4078

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4078:

ic = IC_4078()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 0, 10: 0, 11: 0, 12: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0}) -- \n

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output -- ic.setOutput(8, c)
ic.setOutput(13, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4081
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4081

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4081:

ic = IC_4081()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0}) -- \n

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output -- ic.setOutput(8, c)
ic.setOutput(11, c)

print(c)

########NEW FILE########
__FILENAME__ = IC4082
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 4082

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 4082:

ic = IC_4082()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(13, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7400
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7400

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7400:

ic = IC_7400()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7401
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7401

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7401:

ic = IC_7401()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(1, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7402
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7402

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7402:

ic = IC_7402()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(1, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7403
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7403

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7403:

ic = IC_7403()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7404
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7404

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7404:

ic = IC_7404()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 3: 0, 5: 0, 7: 0, 9: 0, 11: 0, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7405
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7405

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7405:

ic = IC_7405()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7408
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7408

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7408:

ic = IC_7408()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7410
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7410

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7410:

ic = IC_7410()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7411
from __future__ import print_function
from BinPy import *
print ('Usage of IC 7411:\n')
ic = IC_7411()
print ('\nThe Pin configuration is:\n')
p = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}
print (p)
print ('\nPin initialization -using -- ic.setIC(p) --\n')
ic.setIC(p)
print ('\nPowering up the IC - using -- ic.setIC({14:1,7:0}) -- \n')
ic.setIC({14: 1, 7: 0})
print ('\nDraw the IC with the current configuration\n')
ic.drawIC()
print (
    '\nRun the IC with the current configuration using -- print ic.run() -- \n')
print (
    'Note that the ic.run() returns a dict of pin configuration similar to :')
print (ic.run())
print (
    '\nSeting the outputs to the current IC configuration using -- ic.setIC(ic.run()) --\n')
ic.setIC(ic.run())
print ('\nDraw the final configuration\n')
ic.drawIC()
print ('\nConnector Inputs\n')
print ('c = Connector(p[1])\np[1] = c\nic.setIC(p)\n')
c = Connector(p[1])
p[1] = c
ic.setIC(p)
print ('Run the IC\n')
print (ic.run())
print ('\nConnector Outputs')
print ('Set the output -- ic.setOutput(8, c)\n')
ic.setOutput(8, c)
print ('Run the IC\n')
print (ic.run())

########NEW FILE########
__FILENAME__ = IC7412
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7412

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7412:

ic = IC_7412()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7413
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7413

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7413:

ic = IC_7413()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC74138
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 74138

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 74138:

ic = IC_74138()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 1, 4: 0, 5: 0, 6: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({16: 1, 8: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(7, c)

print(c)

########NEW FILE########
__FILENAME__ = IC74139
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 74139

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 74139:

ic = IC_74139()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 0, 2: 0, 3: 0, 14: 0, 13: 1, 15: 0}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({16: 1, 8: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(9, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7415
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7415

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7415:

ic = IC_7415()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC74151A
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 74151A

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 74151A:

ic = IC_74151A()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {
    1: 1,
    2: 0,
    4: 1,
    3: 1,
    7: 0,
    9: 0,
    10: 0,
    11: 0,
    12: 0,
    13: 0,
    14: 1,
    15: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({16: 1, 8: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(5, c)

print(c)

########NEW FILE########
__FILENAME__ = IC74152
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 74152

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 74152:

ic = IC_74152()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 1, 4: 0, 5: 1, 8: 0, 9: 0, 10: 1, 11: 1, 12: 0, 13: 0}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(6, c)

print(c)

########NEW FILE########
__FILENAME__ = IC74153
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 74153

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 74153:

ic = IC_74153()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {
    1: 1,
    2: 1,
    3: 1,
    4: 0,
    5: 0,
    6: 0,
    10: 0,
    11: 1,
    12: 0,
    13: 0,
    14: 0,
    15: 0}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({16: 1, 8: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(9, c)

print(c)

########NEW FILE########
__FILENAME__ = IC74156
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 74156

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 74156:

ic = IC_74156()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 0, 13: 1, 8: 0, 16: 1, 15: 1, 14: 0}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(6, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7416
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7416

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7416:

ic = IC_7416()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7417
from __future__ import print_function
from BinPy import *
print ('Usage of IC 7417:\n')
ic = IC_7417()
print ('\nThe Pin configuration is:\n')
p = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}
print (p)
print ('\nPin initialization -using -- ic.setIC(p) --\n')
ic.setIC(p)
print ('\nPowering up the IC - using -- ic.setIC({14:1,7:0}) -- \n')
ic.setIC({14: 1, 7: 0})
print ('\nDraw the IC with the current configuration\n')
ic.drawIC()
print (
    '\nRun the IC with the current configuration using -- print ic.run() -- \n')
print (
    'Note that the ic.run() returns a dict of pin configuration similar to :')
print (ic.run())
print (
    '\nSeting the outputs to the current IC configuration using -- ic.setIC(ic.run()) --\n')
ic.setIC(ic.run())
print ('\nDraw the final configuration\n')
ic.drawIC()
print ('\nConnector Inputs\n')
print ('c = Connector(p[1])\np[1] = c\nic.setIC(p)\n')
c = Connector(p[1])
p[1] = c
ic.setIC(p)
print ('Run the IC\n')
print (ic.run())
print ('\nConnector Outputs')
print ('Set the output -- ic.setOutput(8, c)\n')
ic.setOutput(8, c)
print ('Run the IC\n')
print (ic.run())

########NEW FILE########
__FILENAME__ = IC7418
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7418

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7418:

ic = IC_7418()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {
    1: 1,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    7: 0,
    9: 1,
    10: 1,
    11: 1,
    12: 1,
    13: 1,
    14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7419
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7419

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7419:

ic = IC_7419()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7420
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7420

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7420:

ic = IC_7420()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7421
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7421

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7421:

ic = IC_7421()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7422
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7422

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7422:

ic = IC_7422()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7424
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7424

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7424:

ic = IC_7424()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7425
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7425

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7425:

ic = IC_7425()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    7: 0,
    9: 1,
    10: 1,
    11: 1,
    12: 1,
    13: 1,
    14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7426
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7426

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7426:

ic = IC_7426()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7427
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7427

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7427:

ic = IC_7427()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7428
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7428

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7428:

ic = IC_7428()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(1, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7430
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7430

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7430:

ic = IC_7430()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 0, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 0, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7431
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7431

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7431:

ic = IC_7431()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 3: 1, 5: 0, 6: 0, 8: 0, 10: 1, 11: 1, 13: 0, 15: 1, 16: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(9, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7432
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7432

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7432:

ic = IC_7432()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7433
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7433

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7433:

ic = IC_7433()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {2: 0, 3: 0, 5: 0, 6: 0, 7: 0, 8: 1, 9: 1, 11: 1, 12: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(1, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7437
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7437

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7437:

ic = IC_7437()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7440
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7400

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7440:

ic = IC_7440()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7442
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7442

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7442:

ic = IC_7442()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {8: 0, 12: 0, 13: 0, 14: 0, 15: 1, 16: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(1, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7443
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7443

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7443:

ic = IC_7443()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {8: 0, 12: 0, 13: 1, 14: 0, 15: 1, 16: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(1, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7444
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7444

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7444:

ic = IC_7444()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {8: 0, 12: 0, 13: 1, 14: 0, 15: 1, 16: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(1, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7445
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7445

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7445:

ic = IC_7445()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {8: 0, 12: 0, 13: 1, 14: 0, 15: 0, 16: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(1, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7451
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7451

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7451:

ic = IC_7451()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {
    1: 1,
    2: 1,
    3: 0,
    4: 0,
    5: 0,
    7: 0,
    9: 0,
    10: 0,
    11: 0,
    12: 1,
    13: 1,
    14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7454
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7454

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7454:

ic = IC_7454()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 0, 4: 0, 7: 0, 9: 1, 10: 1, 11: 0, 12: 0, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(6, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7455
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7455

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7455:

ic = IC_7455()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 3: 0, 4: 0, 7: 0, 9: 1, 10: 1, 11: 0, 12: 0, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7458
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7458

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7458:

ic = IC_7458()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {
    1: 1,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    7: 0,
    9: 0,
    10: 0,
    11: 0,
    12: 1,
    13: 1,
    14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7464
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7464

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7464:

ic = IC_7464()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 7: 0, 11: 1, 12: 1, 13: 1, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = IC7486
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Usage of IC 7486

# <codecell>

from __future__ import print_function
from BinPy import *

# <codecell>

# Usage of IC 7486:

ic = IC_7486()

print(ic.__doc__)

# <codecell>

# The Pin configuration is:

inp = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}

# Pin initinalization

# Powering up the IC - using -- ic.setIC({14: 1, 7: 0})

ic.setIC({14: 1, 7: 0})

# Setting the inputs of the ic

ic.setIC(inp)

# Draw the IC with the current configuration\n

ic.drawIC()

# <codecell>

# Run the IC with the current configuration using -- print ic.run() --

# Note that the ic.run() returns a dict of pin configuration similar to

print (ic.run())

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --\n

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# <codecell>

# Seting the outputs to the current IC configuration using --
# ic.setIC(ic.run()) --

ic.setIC(ic.run())

# Draw the final configuration

ic.drawIC()

# Run the IC

print (ic.run())

# <codecell>

# Connector Outputs
c = Connector()

# Set the output connector to a particular pin of the ic
ic.setOutput(8, c)

print(c)

########NEW FILE########
__FILENAME__ = truthtable
from BinPy import *


print ('Initialising IC_4001:\n-- t = IC4001()\n')
t = IC_4001()
print ('\nGiving a pinConfig in the form of a dict:')
p = {'i': [13, 12], 'o': [11]}
print ('--p =') + (str(p))
print ('\nRunning the truthtable method:\n-- t.truthtable(p)\n')

t.truthtable(p)

########NEW FILE########
__FILENAME__ = Operations

# coding: utf-8

# Examples for operations class

# In[1]:

from __future__ import print_function
from BinPy.Operations.operations import *


# In[2]:

# Initialize the operation class

op = Operations()

# Binary Addition

print (op.ADD('0', '1'), op.ADD('00', '10'), op.ADD('010', '100'))


# In[3]:

# Binary Subtraction

print (op.SUB('1', '0'), op.SUB('00', '10'), op.SUB('010', '100'))


# In[4]:

# Binary Multiplication

print (op.MUL('0', '1'), op.MUL('00', '10'), op.MUL('010', '100'))


# In[5]:

# Binary Division

print (op.DIV('0', '1'), op.DIV('00', '10'), op.DIV('010', '100'))


# In[6]:

# Binary Complement

print (
    op.COMP(
        '0', '1'), op.COMP(
        '00', '1'), op.COMP(
        '00', '2'), op.COMP(
        '010', '1'))


# In[7]:

# Conversion from binary to decimal

print (Operations.binToDec('111'))


# In[8]:

# Conversion from decimal to binary

print (Operations.decToBin(12))

########NEW FILE########
__FILENAME__ = BinaryCounter

# coding: utf-8

# Example for Binary Counter [ A 2 bit Ripple Counter ]

# In[1]:

# Imports

from __future__ import print_function
from BinPy.tools.clock import Clock
from BinPy.Sequential.counters import BinaryCounter
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope
import time


# In[2]:

# A clock of 1 hertz frequency  With initial value as 0

clock = Clock(0, 1)
clock.start()
clk_conn = clock.A


# In[3]:

# Initializing Binary Counter with 2 bits and clock_conn
b = BinaryCounter(2, clk_conn)

# Initializing the Oscillioscope
o = Oscilloscope((clk_conn, 'CLK'), (b.out[0], 'MSB'), (b.out[1], 'LSB'))

# Starting the oscillioscope
o.start()

# Set scale by trial and error.
o.setScale(0.15)

# Set the width of the oscilloscope [ To fit the ipython Notebook ]
o.setWidth(100)


# In[4]:

# Then unhold [ Run the Oscilloscope ]
o.unhold()

print(b.state())

# Triggering the Binary Counter 10 times.
for i in range(10):
    b.trigger()
    print (b.state())

# Display the time-Waveform.
o.display()

# Kill the oscilloscope thread.
o.kill()


# In[5]:

# Calling the instance will also trigger the counter.
print("b()")


# In[6]:

# Setting the Counter

b.setCounter()

print(b.state())


# In[7]:

# Resetting the Counter

b.resetCounter()

print(b.state())


# In[8]:

# Disabling the Counter

b.disable()

# Now triggering it has no effect.

b.trigger()

print(b.state())


# In[9]:

# Enabling the Counter

b.enable()
b.trigger()

print(b.state())


# In[10]:

# Kill the clock thread.
clock.kill()

########NEW FILE########
__FILENAME__ = DecadeCounter

# coding: utf-8

# Example for Decade Counter.

# In[27]:

# imports

from __future__ import print_function
from BinPy.tools import Clock
from BinPy.Sequential.counters import DecadeCounter
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope


# In[28]:

# Initialize a toggle connectr for inpput in TFlipFlop

toggle = Connector(1)


# In[29]:

# Initializing the Clock
# A clock of 5 hertz frequency

clock = Clock(1, 5)

clock.start()

clk_conn = clock.A


# In[30]:

# Initialize enable

enable = Connector(1)


# In[31]:

# Initializing the counter

# Initializing DecadeCounter with clock_conn

b = DecadeCounter(clk_conn)


# In[32]:

# Initiating the oscilloscope

o = Oscilloscope((clk_conn, 'CLK'), (b.out[0], 'BIT3'), (b.out[1], 'BIT2'), (
    b.out[2], 'BIT1'), (b.out[3], 'BIT0'), (enable, 'EN1'))

# starting the oscillioscope thread - This does not initiate the recording.

o.start()

# setting the scale

o.setScale(0.05)  # Set scale by trial and error.

# Set the width of the oscilloscope to fit the ipython notebook.

o.setWidth(100)


# In[33]:

# unhold the oscilloscope to start the recording.

o.unhold()

# Initial State

print (b.state())

# Triggering the counter sequentially 2^4 times

for i in range(1, 2 ** 4):
    b.trigger()
    print (b.state())

# Display the oscilloscope - Implicitly the o.hold() will be called first
# to stop the recording.

o.display()


# In[34]:

# Calling the instance will trigger

b()

print(b.state())


# In[35]:

# Setting the Counter

b.setCounter()

print(b.state())


# In[36]:

# Resetting the Counter

b.resetCounter()

print(b.state())


# In[37]:

# Disabling the Counter

b.disable()

b.trigger()

print(b.state())


# In[38]:

# Enabling the Counter

b.enable()

b.trigger()

print(b.state())


# In[39]:

# Kill the oscilloscope thread

o.kill()

# Kill the clock thread

clock.kill()

########NEW FILE########
__FILENAME__ = JohnsonCounter

# coding: utf-8

# Example for N Bit Johnson Counter.

# In[1]:

# imports

from __future__ import print_function
from BinPy.tools import Clock
from BinPy.Sequential.counters import JohnsonCounter
from BinPy.Gates import Connector


# In[2]:

# Initializing the Clock
# A clock of 50 hertz frequency

clock = Clock(1, 50)
clock.start()


# In[3]:

# Initialize enable

enable = Connector(1)

# Initializing the counter

# Initializing Johnson with 8 bits and clock

b = JohnsonCounter(8, clock)

# Initial State

print (b.state())


# In[4]:

# Triggering the counter 24 times

for i in range(24):
    b.trigger()
    print (b.state())

# Calling the instance will trigger

b()

print(b.state())


# In[5]:

# Setting the Counter

# b.setCounter()

print(b.state())


# In[6]:

# Resetting the Counter

# b.resetCounter()

print(b.state())


# In[7]:

# Disabling the Counter

b.disable()

b.trigger()

print(b.state())


# In[8]:

# Enabling the Counter

b.enable()

b.trigger()

print(b.state())


# In[9]:

# Kill the clock thread after use

clock.kill()

########NEW FILE########
__FILENAME__ = NBitDownCounter

# coding: utf-8

# Example for N Bit Binary Down Counter.

# In[1]:

# imports
from __future__ import print_function
from BinPy.tools import Clock
from BinPy.Sequential.counters import NBitDownCounter
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope


# In[2]:

# Initialize a toggle connectr for inpput in TFlipFlop

toggle = Connector(1)

# Initializing the Clock
# A clock of 10 hertz frequency

clock = Clock(1, 10)
clock.start()

clk_conn = clock.A


# In[3]:

# Initialize enable

enable = Connector(1)


# In[4]:

# Setting No of Bits to 4

# Initializing Down Counter with 4 bits and clock_conn

b = NBitDownCounter(4, clk_conn)


# In[5]:

# Initiating the oscilloscope

# starting the oscillioscope

# setting the scale

o = Oscilloscope((clk_conn, 'CLK'), (b.out[0], 'BIT3'), (b.out[1], 'BIT2'), (
    b.out[2], 'BIT1'), (b.out[3], 'BIT0'), (enable, 'EN1'))

o.start()

o.setScale(0.035)  # Set scale by trial and error.

# Set the width of the oscilloscope
o.setWidth(100)

o.unhold()


# In[6]:

# Initial State

print (b.state())


# In[7]:

# Triggering the counter sequentially 2^4 + 2 times

for i in range(1, 2 ** 4 + 2):
    b.trigger()
    print (b.state())

o.display()


# In[8]:

# Calling the instance will trigger

b()

print(b.state())


# In[9]:

# Setting the Counter

b.setCounter()

print(b.state())


# In[10]:

# Resetting the Counter

b.resetCounter()

print(b.state())


# In[11]:

# Disabling the Counter

b.disable()
b.trigger()

print(b.state())


# In[12]:

# Enabling the Counter

b.enable()
b.trigger()

print(b.state())


# In[13]:

# Kill the clock and the oscilloscope thread after use

o.kill()

clock.kill()

########NEW FILE########
__FILENAME__ = NBitRippleCounter

# coding: utf-8

# Example for N Bit Binary Ripple Counter.

# In[1]:

# imports
from __future__ import print_function
from BinPy.tools import Clock
from BinPy.Sequential.counters import NBitRippleCounter
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope


# In[2]:

# Initialize a toggle connectr for inpput in TFlipFlop

toggle = Connector(1)

# Initializing the Clock
# A clock of 10 hertz frequency

clock = Clock(1, 10)
clock.start()
clk_conn = clock.A

# Initialize enable

enable = Connector(1)


# In[3]:

# Setting No of Bits to 4

# Clock frequency is 10 Hz

# Initializing Ripple Counter with 4 bits and clock_conn

b = NBitRippleCounter(4, clk_conn)

# Initiating the Oscilloscope

o = Oscilloscope((clk_conn, 'CLK'), (b.out[0], 'BIT3'), (b.out[1], 'BIT2'), (
    b.out[2], 'BIT1'), (b.out[3], 'BIT0'), (enable, 'EN1'))

o.start()

o.setScale(0.035)  # Set scale by trial and error.

o.setWidth(100)

o.unhold()

# Initial State

print (b.state())

# Triggering the counter sequentially 2^4 + 1 times

for i in range(1, 2 ** 4 + 1):
    b.trigger()
    print (b.state())

o.display()


# In[4]:

# Calling the instance will trigger

b()

print(b.state())


# In[5]:

# Setting the Counter

b.setCounter()

print(b.state())


# In[6]:

# Resetting the Counter

b.resetCounter()

print(b.state())


# In[7]:

# Disabling the Counter

b.disable()
b.trigger()

print(b.state())


# In[8]:

# Enabling the Counter

b.enable()
b.trigger()

print(b.state())


# In[9]:

# Kill the clock and the oscilloscope threads.

o.kill()
clock.kill()

########NEW FILE########
__FILENAME__ = OctalCounter

# coding: utf-8

# Example for Octal Counter.

# In[1]:

# imports
from __future__ import print_function
from BinPy.tools import Clock
from BinPy.Sequential.counters import OctalCounter
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope


# In[2]:

# Initialize a toggle connectr for inpput in TFlipFlop

toggle = Connector(1)

# Initializing the Clock
# A clock of 5 hertz frequency

clock = Clock(1, 5)
clock.start()

# Initialize enable

enable = Connector(1)

# Initializing OctalCounter with 4 bits and clock

b = OctalCounter(clock.A)


# In[3]:

# Initializing the Oscillioscope

# starting the oscillioscope
# setting the scale

o = Oscilloscope((clock.A, 'CLK'), (b.out[0], 'BIT3'), (b.out[1], 'BIT2'), (
    b.out[2], 'BIT1'), (b.out[3], 'BIT0'), (enable, 'EN1'))

o.start()

o.setWidth(100)

o.setScale(0.05)  # Set scale by trial and error.

o.unhold()


# In[4]:

# Initial State

print (b.state())


# In[5]:

# Triggering the counter sequentially 2^4 + 2 times

for i in range(1, 2 ** 4 + 2):
    b.trigger()
    print (b.state())

o.display()


# In[6]:

# Calling the instance will trigger

b()

print(b.state())


# In[7]:

# Setting the Counter

b.setCounter()

print(b.state())


# In[8]:

# Resetting the Counter

b.resetCounter()

print(b.state())


# In[9]:

# Disabling the Counter

b.disable()
b.trigger()

print(b.state())


# In[10]:

# Enabling the Counter

b.enable()
b.trigger()

print(b.state())


# In[11]:

# Kill the oscilloscope and the clock threads after use.

o.kill()
clock.kill()

########NEW FILE########
__FILENAME__ = RingCounter

# coding: utf-8

# Example for N Bit Ring Counter.

# In[1]:

# imports
from __future__ import print_function
from BinPy.tools import Clock
from BinPy.Sequential.counters import RingCounter
from BinPy.Gates import Connector


# In[2]:

# Initializing the Clock
# Clock frequency is 50 Hz

clock = Clock(1, 50)
clock.start()


# In[3]:

# Initialize enable

enable = Connector(1)


# In[4]:

# Initializing RingCounter with 8 bits and clock

b = RingCounter(8, clock)


# In[5]:

# Initial State

print (b.state())


# In[6]:

# Triggering the counter 8 times

for i in range(8):
    b.trigger()
    print (b.state())


# In[7]:

# Calling the instance will trigger

b()

print(b.state())


# In[8]:

# Setting the Counter

# b.setCounter()

print(b.state())


# In[9]:

# Resetting the Counter

# b.resetCounter()

print(b.state())


# In[10]:

# Disabling the Counter

b.disable()
b.trigger()

print(b.state())


# In[11]:

# Enabling the Counter

b.enable()
b.trigger()

print(b.state())


# In[12]:

# Kill the clock thread.

clock.kill()

########NEW FILE########
__FILENAME__ = Stage14Counter

# coding: utf-8

# Example for Stage14Counter.

# In[1]:

# imports
from __future__ import print_function
from BinPy.tools import Clock
from BinPy.Sequential.counters import Stage14Counter
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope


# In[2]:

# Initialize a toggle connectr for inpput in TFlipFlop

toggle = Connector(1)

# Initializing the Clock
# A clock of 5 hertz frequency

clock = Clock(1, 5)
clock.start()
clk_conn = clock.A


# In[3]:

# Initialize enable

enable = Connector(1)


# In[4]:

# Initializing Stage14Counter with 4 bits and clock_conn

b = Stage14Counter(clk_conn)


# In[5]:

# Initializing the Oscillioscope

# setting the scale

o = Oscilloscope((clk_conn, 'CLK'), (b.out[0], 'BIT3'), (b.out[1], 'BIT2'), (
    b.out[2], 'BIT1'), (b.out[3], 'BIT0'), (enable, 'EN1'))

o.start()

o.setWidth(100)

o.setScale(0.07)  # Set scale by trial and error.

o.unhold()


# In[6]:

# Initial State

print (b.state())


# In[7]:

# Triggering the counter sequentially 2^4 + 2 times

for i in range(1, 2 ** 4 + 2):
    b.trigger()
    print (b.state())

o.display()


# In[8]:

# Calling the instance will trigger

b()

print(b.state())


# In[9]:

# Setting the Counter

b.setCounter()

print(b.state())


# In[10]:

# Resetting the Counter

b.resetCounter()

print(b.state())


# In[11]:

# Disabling the Counter

b.disable()
b.trigger()

print(b.state())


# In[12]:

# Enabling the Counter

b.enable()
b.trigger()

print(b.state())


# In[13]:

# Kills the oscilloscope and the clock threads after use.
o.kill()
clock.kill()

########NEW FILE########
__FILENAME__ = DFlipFlop
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Example for DFlipFlop

# <codecell>

from __future__ import print_function
from BinPy.Sequential.sequential import DFlipFlop
from BinPy.tools.clock import Clock
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope

# <codecell>

data = Connector(1)

p = Connector(0)
q = Connector(1)

# <codecell>

# Initialize the clock
clock = Clock(1, 5)
clock.start()
# A clock of 10 hertz frequency
clk_conn = clock.A

enable = Connector(1)

# <codecell>

# Initialize the D-FlipFlop
dff = DFlipFlop(data, enable, clk_conn, a=p, b=q)
# To connect different set of connectors use :
# dff.setInputs(conn1,enab,clk)
# To connect different outputs use s.setOutputs(op1,op2)
dff.setOutputs(A=p, B=q)

# <codecell>

# Initiating the oscilloscope
o = Oscilloscope((clk_conn, 'CLK'), (data, 'DATA'), (
    p, 'OUT'), (q, 'OUT!'), (enable, 'ENABLE'))
o.start()
o.setScale(0.01)  # Set scale by trial and error.
o.setWidth(100)
o.unhold()

# <codecell>

print ("Data is 1")
data.state = 1
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        dff.trigger()
        break
print (dff.state())

# Sending a positive edge to dff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        dff.trigger()
        break

# <codecell>

print ("Data is 0")
data.state = 0
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        dff.trigger()
        break
print (dff.state())
# Sending a positive edge to dff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        dff.trigger()
        break

# <codecell>

print ("Data is 1")
data.state = 1
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        dff.trigger()
        break
print (dff.state())
# Sending a positive edge to dff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        dff.trigger()
        break

# <codecell>

# Display the oscilloscope
o.display()

# <codecell>

# Kill the oscilloscope and clock threads after usage
o.kill()
clock.kill()

########NEW FILE########
__FILENAME__ = JKFlipFlop
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Example for JKFlipFlop

# <codecell>

from __future__ import print_function
from BinPy.Sequential.sequential import JKFlipFlop
from BinPy.tools.clock import Clock
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope

# <codecell>

j = Connector(1)
k = Connector(0)

p = Connector(0)
q = Connector(1)

# <codecell>

# Initialize the clock
clock = Clock(1, 4)
clock.start()

# A clock of 4 hertz frequency initialized to 1
clk_conn = clock.A

enable = Connector(1)

jkff = JKFlipFlop(j, k, enable, clk_conn, clear=enable)

# To connect outputs use s.setOutputs(op1,op2)
jkff.setOutputs(A=p, B=q)

# <codecell>

# Initiating the oscilloscope

o = Oscilloscope((clk_conn, 'CLK'), (j, 'J'), (
    k, 'k'), (p, 'OUT'), (q, 'OUT!'), (enable, 'ENABLE'))

o.start()
o.setScale(0.02)  # Set scale by trial and error.
o.setWidth(100)
o.unhold()

# <codecell>

print ("SET STATE - J = 1, K = 0")

# Set State
j.state = 1
k.state = 0

# The same thing can also be done by --> jkff.setInputs(j = 1, k = 0)
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        jkff.trigger()
        break
print (jkff.state())

# Sending a positive edge to jkff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        jkff.trigger()
        break

# <codecell>

print ("RESET STATE - J = 0, K = 1")

# Reset State
j.state = 0
k.state = 1

# The same thing can also be done by --> jkff.setInputs(j = 1, k = 0)
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        jkff.trigger()
        break

        print (
            "[Printing the output using the output connectors:]\n",
            p(),
            q())

# Sending a positive edge to jkff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        jkff.trigger()
        break

# <codecell>

print ("TOGGLE STATE - J = 1, K = 1")
# Toggle State
j.state = 1
k.state = 1
# The same thing can also be done by --> jkff.setInputs(j = 1, k = 0)
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        jkff.trigger()
        break
print (jkff.state())

# Sending a positive edge to jkff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        jkff.trigger()
        break

# <codecell>

print ("NO CHANGE STATE - J = 0, K = 0")
# No change state
j.state = 0
k.state = 0
# The same thing can also be done by --> jkff.setInputs(j = 1, k = 0)
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        jkff.trigger()
        break
print (jkff.state())

# Sending a positive edge to jkff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        jkff.trigger()
        break

# To connect different set of connectors use s.setInputs(conn1,conn2,enab)

# <codecell>

# Display the oscilloscope
o.display()

# <codecell>

# Kill the oscilloscope and clock threads
o.kill()
clock.kill()

########NEW FILE########
__FILENAME__ = SRLatch
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Example for SRLatch

# <codecell>

from __future__ import print_function
from BinPy.Sequential.sequential import SRLatch
from BinPy.tools.clock import Clock
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope

# <codecell>

s = Connector(1)
r = Connector(0)

p = Connector(0)
q = Connector(1)

# <codecell>

# Initialize the clock
clock = Clock(1, 4)
clock.start()
# A clock of 1 hertz frequency
clk_conn = clock.A

enable = Connector(1)

# <codecell>

# Initialize the sr latch
srff = SRLatch(s, r, enable, clk_conn)

# To connect outputs use s.setOutputs(op1,op2)
srff.setOutputs(A=p, B=q)

# <codecell>

# Initialize the oscilloscope

o = Oscilloscope((clk_conn, 'CLK'), (s, 'S'), (
    r, 'R'), (p, 'OUT'), (q, 'OUT!'), (enable, 'ENABLE'))
o.start()
o.setScale(0.015)  # Set scale by trial and error.
o.setWidth(100)
o.unhold()

# <codecell>

print ("SET STATE - S = 1, R = 0")
# Set State
s.state = 1
r.state = 0
# The same thing can also be done by --> srff.setInputs(s = 1, r = 0)
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        srff.trigger()
        break
print (srff.state())
# Sending a positive edge to srff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        srff.trigger()
        break

# <codecell>

print ("RESET STATE - S = 0, R = 1")
# Reset State
s.state = 0
r.state = 1
# The same thing can also be done by --> srff.setInputs(s = 1, r = 0)
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        srff.trigger()
        break
# Displaying the output using the connector instances
print ("[", p(), ",", q(), "]")

# Sending a positive edge to srff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        srff.trigger()
        break

# <codecell>

print ("INVALID STATE - S = 1, R = 1")
# Invalid state
s.state = 1
r.state = 1
# The same thing can also be done by --> srff.setInputs(s = 1, r = 1)
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        srff.trigger()
        break
print (srff.state())

# Sending a positive edge to srff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        srff.trigger()
        break

# <codecell>

print ("2nd INVALID STATE - S = 0, R = 0")
# Invalid state
s.state = 1
r.state = 1
# The same thing can also be done by --> srff.setInputs(s = 1, r = 1)
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        srff.trigger()
        break
print (srff.state())

# Sending a positive edge to srff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        srff.trigger()
        break

# <codecell>

# Display the oscilloscope
o.display()

# <codecell>

# Kill the clock and the oscilloscope threads after use
o.kill()
clock.kill()

########NEW FILE########
__FILENAME__ = TFlipFlop
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Example for TFlipFlop

# <codecell>

from __future__ import print_function
from BinPy.Sequential.sequential import TFlipFlop
from BinPy.tools.clock import Clock
from BinPy.Gates import Connector
from BinPy.tools.oscilloscope import Oscilloscope

# <codecell>

toggle = Connector(1)

p = Connector(0)
q = Connector(1)

# <codecell>

# Initialize the clock
clock = Clock(1, 4)
clock.start()
# A clock of 4 hertz frequency
clk_conn = clock.A

enable = Connector(1)

# <codecell>

# Initialize the T-FlipFlop
tff = TFlipFlop(toggle, enable, clk_conn, a=p, b=q)

# To connect different set of connectors use :
# tff.setInputs(conn1,enab,clk)
# To connect different outputs use:
tff.setOutputs(A=p, B=q)

# <codecell>

# Initialize the oscilloscope
o = Oscilloscope((clk_conn, 'CLK'), (toggle, 'TOGGLE'), (
    p, 'OUT'), (q, 'OUT!'), (enable, 'ENABLE'))
o.start()
o.setScale(0.01)  # Set scale by trial and error.
o.setWidth(100)
o.unhold()

# <codecell>

print ("Toggle is 1")
toggle.state = 1
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        tff.trigger()
        break
print (tff.state())

# Sending a positive edge to ff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        tff.trigger()
        break

# <codecell>

print ("Toggle is 1")
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        tff.trigger()
        break
print (tff.state())

# Sending a positive edge to ff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        tff.trigger()
        break

# <codecell>

print ("Toggle is 1")
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        tff.trigger()
        break
print (tff.state())

# Sending a positive edge to ff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        tff.trigger()
        break

# <codecell>

print ("Toggle is 0")
toggle.state = 0
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        tff.trigger()
        break
print (tff.state())

# Sending a positive edge to ff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        tff.trigger()
        break

# <codecell>

print ("Toggle is 0")
while True:
    if clk_conn.state == 0:
        # Falling edge will trigger the FF
        tff.trigger()
        break
print (tff.state())

# Sending a positive edge to ff
while True:
    if clk_conn.state == 1:
        # Falling edge will trigger the FF
        tff.trigger()
        break

# <codecell>

# Display the oscilloscope
o.display()

# <codecell>

# Kill the oscilloscope and clock threads after use
o.kill()
clock.kill()

########NEW FILE########
__FILENAME__ = FourBitLoadRegister
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Examples for FourBitLoadRegister class

# <codecell>

from __future__ import print_function
from BinPy.Sequential import *

# <codecell>

# Initialise clock c = Clock(1, 500)"

c = Clock(1, 500)
c.start()

# <codecell>

# Initializing the FourBitLoadRegister class
# Input is of the form (A0, A1, A2, A3, CLOCK, CLEAR, LOAD

fr = FourBitLoadRegister(1, 0, 1, 1, c, 1, 1)

# <codecell>

# Output of the register
print (fr.output())

# <codecell>

# Input changes
# Input at index 1 is changed to 0
fr.setInput(1, 0)

# New Output of the register
print (fr.output())

# <codecell>

# Changing the inputs all at once
# No need to set the number, just change the inputs

fr.setInputs(1, 1, 1, 1)

# Changing the load value

fr.setLoad(0)

# New Output of the register

print (fr.output())

# <codecell>

# To get the input states

print (fr.getInputStates())

# <codecell>

# New output of the register

print (fr.output())

# <codecell>

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of gate to Connector conn

fr.setOutput(2, conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 0)
# Output of the gate1

print (gate1.output())

########NEW FILE########
__FILENAME__ = FourBitRegister
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Examples for FourBitRegister class

# <codecell>

from __future__ import print_function
from BinPy.Sequential import *

# <codecell>

# Initialise clock

c = Clock(1, 500)
c.start()

# Initializing the FourBitRegister class
# Input is of the form (A0, A1, A2, A3, CLOCK, CLEAR)

fr = FourBitRegister(1, 0, 1, 1, c, 1)

# Output of the register

print (fr.output())

# <codecell>

# Input changes

# Input at index 1 is changed to 0

fr.setInput(1, 0)

# New Output of the register

print (fr.output())

# <codecell>

# Changing the inputs

# No need to set the number, just change the inputs

fr.setInputs(1, 1, 1, 1)

# To get the input states

print (fr.getInputStates())

# <codecell>

# New output of the register

print (fr.output())

# <codecell>

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of gate to Connector conn

fr.setOutput(2, conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 0)

# Output of the gate1

print (gate1.output())

########NEW FILE########
__FILENAME__ = ShiftRegister
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Examples for ShiftRegister class

# <codecell>

from __future__ import print_function
from BinPy.Sequential import *

# <codecell>

# Initializing the ShiftRegister class

# Input is of the form ([A0, A1, A2, A3], CLOCK, CIRCULAR)

# Initialise clock

c = Clock(1, 500)
c.start()

# Simple shift register

fr = ShiftRegister([1, 0, 1, 1], c, 0)

# Output of the register

print (fr.output())

# <codecell>

# Circular shift register

fr = ShiftRegister([1, 0, 1, 1], c, 1)

# Output of the register

print (fr.output())

# <codecell>

# Input changes

# Input at index 1 is changed to 0

fr.setInput(1, 0)

# New Output of the register

print (fr.output())

# <codecell>

#  Changing the inputs

# No need to set the number, just change the inputs

fr.setInputs(1, 1, 1, 1)

# To get the input states

print (fr.getInputStates())

# <codecell>

# New output of the register

print (fr.output())

# <codecell>

# Using Connectors as the input lines

# Take a Connector

conn = Connector()

# Set Output of gate to Connector conn

fr.setOutput(2, conn)

# Put this connector as the input to gate1

gate1 = AND(conn, 0)

# Output of the gate1

print (gate1.output())

########NEW FILE########
__FILENAME__ = multivibrator_mode1
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Monostable Multivibrator - Multivibrator in Mode 1

# <codecell>

from __future__ import print_function
from BinPy.tools.clock import Clock
from BinPy.Gates import Connector
from BinPy.tools.multivibrator import Multivibrator
from BinPy.tools.oscilloscope import Oscilloscope
import time

# <codecell>

# MODE selects the mode of operation of the multivibrator.

# Mode No. :  Description
#   1          Monostable
#   2          Astable
#   3          Bistable

out = Connector()

# <codecell>

# Initialize mutivibrator in MODE 1

m = Multivibrator(0, mode=1, time_period=1)
m.start()
m.setOutput(out)

# <codecell>

# Initialize the oscilloscope
o = Oscilloscope((out, 'OUT'))
o.start()
o.setScale(0.005)  # Set scale by trial and error.
o.setWidth(100)
o.unhold()
time.sleep(0.1)
m.trigger()  # Also works with m()
time.sleep(0.1)

# <codecell>

# Display the oscilloscope
o.display()

# <codecell>

# Kill the multivibrator and the oscilloscope threads
m.kill()
o.kill()

########NEW FILE########
__FILENAME__ = multivibrator_mode2
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Astable Multivibrator - Multivibrator in Mode 2

# <codecell>

from __future__ import print_function
from BinPy.tools.clock import Clock
from BinPy.Gates import Connector
from BinPy.tools.multivibrator import Multivibrator
from BinPy.tools.oscilloscope import Oscilloscope
import time

# <codecell>

# MODE selects the mode of operation of the multivibrator.

# Mode No. :  Description
#   1          Monostable
#   2          Astable
#   3          Bistable

out = Connector()

# <codecell>

# Initialize mutivibrator in MODE 2 with the adequate on_time and off_time

m = Multivibrator(0, mode=2, on_time=0.2, off_time=0.8)
m.start()
m.setOutput(out)

# <codecell>

# Initialize the oscilloscope
o = Oscilloscope((out, 'OUT'))
o.start()
o.setScale(0.05)  # Set scale by trial and error.
o.setWidth(100)
o.unhold()
time.sleep(0.1)
m.trigger()  # Also works with m()
time.sleep(5)

# <codecell>

# Display the oscilloscope
o.display()

# <codecell>

# Kill the multivibrator and the oscilloscope threads
m.kill()
o.kill()

########NEW FILE########
__FILENAME__ = multivibrator_mode3
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <headingcell level=2>

# Bistable Multivibrator - Multivibrator in Mode 3

# <codecell>

from __future__ import print_function
from BinPy.tools.clock import Clock
from BinPy.Gates import Connector
from BinPy.tools.multivibrator import Multivibrator
from BinPy.tools.oscilloscope import Oscilloscope
import time

# <codecell>

# MODE selects the mode of operation of the multivibrator.

# Mode No. :  Description
#   1          Monostable
#   2          Astable
#   3          Bistable

out = Connector(0)

# <codecell>

# Initialize mutivibrator in MODE 3

m = Multivibrator(0, mode=3)
m.start()
m.setOutput(out)

# <codecell>

# Initialize the oscilloscope
o = Oscilloscope((out, 'OUT'))
o.start()
o.setScale(0.05)
o.setWidth(100)
o.unhold()
# This is done to let the oscilloscope thread to synchronize with the main
# thread...
time.sleep(0.001)

# <codecell>

# Trigger the multivibrator to change the state
print(out())
time.sleep(0.1)
m.trigger()

time.sleep(0.001)  # This is done to synchronize the multivibrator thread ...

print(out())
time.sleep(0.5)
m.trigger()

time.sleep(0.001)  # This is done to synchronize the multivibrator thread ...

print(out())
time.sleep(1)
m.trigger()

time.sleep(0.001)  # This is done to synchronize the multivibrator thread ...

print(out())
time.sleep(2)
m.trigger()

time.sleep(0.001)  # This is done to synchronize the multivibrator thread ...

print (out())

# <codecell>

# Display the oscilloscope
o.display()

# <codecell>

# Kill the multivibrator and the oscilloscope threads
m.kill()
o.kill()

########NEW FILE########
__FILENAME__ = PowerSourceAndGround
# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# Example to show the usage of PowerSupply

# <codecell>

from __future__ import print_function
from BinPy.tools import *

# <codecell>

# Usage of PowerSource and Ground classes:
# Creating Power Source POW and Ground terminal, GND

POW = PowerSource()
GND = Ground()

# <codecell>

# Creating connectors a,b,c

a = Connector()
b = Connector()
c = Connector()

# <codecell>

# Creating AND gate with inputs a and b and setting it output as c
AND1 = AND(a, b)
AND1.setOutput(c)

# <codecell>

# Connecting the connectors a, b to the Power Source
POW.connect(a)
POW.connect(b)

# a and b connected to Power Source, POW

# Printing Status of AND1

print('The inputs to the AND1 are: ' + str(AND1.getInputStates()))

print('The output of AND1 is: ' + str(AND1.output()))

# <codecell>

# Disconnecting b from Power Source and printing inputs of AND1

print('\nAfter disconnecting b from the Power Source, POW')

# <codecell>

POW.disconnect(b)

print('The inputs of the AND1 are: ' + str(AND1.getInputStates()))

# <codecell>

# Conneting b to Ground and printing the status AND1

print('\nAfter connecting b to the Ground, GND')

GND.connect(b)

# <codecell>

print('The inputs of the AND1 are: ' + str(AND1.getInputStates()))

print('The output of AND1 is: ' + str(AND1.output()))

########NEW FILE########
__FILENAME__ = connector
from __future__ import division
from BinPy.config import *


"""
Contains
========

* Connector
* Bus
* make_bus

"""


class Connector:

    """
    This class is the primary medium for data transfer. Objects of this
    class can be connected to any digital object.

    Example
    =======

    >>> from BinPy import *
    >>> conn = Connector(1)  #Initializing connector with initial state = 1
    >>> conn.state
    1
    >>> gate = OR(0, 1)
    >>> conn.tap(gate, 'output')  #Tapping the connector

    Methods
    =======

    * tap
    * untap
    * is_input_of
    * is_output_of
    * trigger
    """

    _index = 0

    def __init__(self, state=None, name=""):
        self.connections = {"output": [], "input": []}
        # To store the all the taps onto this connection
        self.state = state  # To store the state of the connection
        self.oldstate = None
        # voltage for analog components
        self.voltage = 0.0
        self.oldvoltage = 0.0
        self._name = name
        self.name_set = (name != "")
        Connector._index += 1
        self._index = Connector._index

    @property
    def index(self):
        return self._index

    def tap(self, element, mode):
        # Can't serve output for multiple devices
        if mode == "output":
            self.connections["output"] = []

        if element not in self.connections[mode]:
            self.connections[mode].append(
                element)  # Add an element to the connections list

    def untap(self, element, mode):
        if element in self.connections[mode]:
            self.connections[mode].remove(
                element)  # Delete an element from the connections list
        else:
            raise Exception(
                "ERROR:Connector is not the %s of the passed element" %
                mode)

    def set_logic(self, val):
        if type(val) in [int, None, bool]:
            self.state = val if val is not None else None
            self.voltage = constants.LOGIC_HIGH_VOLT if self.state == constants.LOGIC_HIGH_STATE else constants.LOGIC_LOW_VOLT
            self.trigger()

        elif isinstance(val, Connector):
            self.state = val.get_logic()

        else:
            raise Exception("ERROR: Invalid input type")

        self.trigger()
        # All set functions ultimately call this. So one trigger here should
        # suffice.

    def get_logic(self):
        return self.state

    def set_voltage(self, val):
        if type(val) in [float, int]:
            self.voltage = float(val)
        elif isinstance(val, Connector):
            self.voltage = val.get_voltage()

        else:
            raise Exception("ERROR: Voltage must be a float or int")

        state = constants.LOGIC_HIGH_STATE if self.voltage > constants.LOGIC_THRESHOLD_VOLT else constants.LOGIC_LOW_STATE
        self.set_logic(state)

    def get_voltage(self):
        return self.voltage

    def is_input_of(self, element):
        return element in self.connections["input"]

    def is_output_of(self, element):
        return element in self.connections["output"]

    # This function is called when the value of the connection changes
    def trigger(self):
        for i in self.connections["input"]:
            i.trigger()

    def __call__(self):
        return self.state

    def set_name(self, name):
        if (self.name is None) and (not self.name_set):
            for k, v in list(globals().iteritems()):
                if (id(v) == id(self)) and (k != "self"):
                    self.name = k
            self.name_set = True

    @property
    def name(self):
        return self._name

    # This could replace the trigger method all together.
    def __setattr__(self, name, val):
        self.__dict__[name] = val
        # self.trigger()

    # Overloads the bool method
    # For python3
    def __bool__(self):
        return True if self.state == 1 else False

    # To be compatible with Python 2.x
    __nonzero__ = __bool__

    # Overloads the int() method
    def __int__(self):
        return 1 if self.state == 1 else 0

    def __float__(self):
        return float(self.voltage)

    def __repr__(self):
        return str(self.state)

    def __str__(self):
        return "Connector; Name: %s; Index: %d; State: " % (
            self.name, self.index) + str(self.state)

    def __add__(self, other):
        return self.voltage + other.voltage

    def __sub__(self, other):
        return self.voltage - other.voltage

    def __mul__(self, other):
        return self.voltage * other.voltage

    def __truediv__(self, other):
        return self.voltage / other.voltage


class Bus:

    """
    This class provides an array of Connector Objects.
    Objects of this class can be used :
    1. As input and output interfaces for modules and other blocks
    2. When a lot of connectors are needed
    """

    _index = 0

    def __init__(self, *inputs):
        """
        Initialized through a list of connectors or another Bus
        or a integer (width) to create a Bus of new Connectors of the specified width
        """

        self.bus = []
        self.analog = False

        # Each Bus will have an unique index. Good for debugging Connections.
        Bus._index += 1
        self._index = Bus._index

        # width specified
        if (len(inputs) == 1) and (isinstance(inputs[0], int)) and (inputs[0] >= 0):
            self.bus += [Connector() for i in range(inputs[0])]
            self._width = inputs[0]

        # create from Bus; Similar to a = list(b)
        elif (len(inputs) == 1) and isinstance(inputs[0], Bus):
            self.bus = list(inputs[0].bus)
            self.analog = inputs[0].analog
            self._width = len(self.bus)

        # create from a list of connectors
        else:
            # if inputs is a list of connectors
            if (len(inputs) == 1) and (isinstance(inputs[0], list)):
                inputs = inputs[0]

            # if inputs is an unpacked list of connectors
            if (len(inputs) > 0) and (False not in [isinstance(i, Connector) for i in inputs]):
                self.bus += inputs
                self._width = len(self.bus)

            else:
                raise Exception("ERROR: Invalid input")

    def set_width(self, width, *connectors):
        """Used to decrease the width of the bus or increase it and appending new additional connectors."""

        # Use this method sparingly. It would be good practice to keep Bus
        # objects of fixed size.

        if width <= 0:
            raise Exception("ERROR: Enter non-negative width")
        if width == self._width:
            return
        elif width < self._width:
            self.bus = self.bus[:width]
        elif width > self._width:
            if len(connectors) == width - self._width:
                self.bus += [(conn if isinstance(conn, Connector)
                              else Connector()) for conn in connectors]

            self.bus += [Connector() for i in range(width - len(self.bus))]

        self._width = width

    # PLEASE DO NOT ADD A SET INPUT METHOD. WE DO NOT WANT TO CHANGE THE BUS CONNECTORS DYNAMICALLY.
    # IT CAN ONLY BE APPENDED OR DELETED BUT NOT UPDATED.

    def set_type(self, analog):
        self.analog = bool(analog)

    get_type = lambda self: "ANALOG" if self.analog else "DIGITAL"

    def set_logic(self, index, value):
        if index > 0 and index < self._width:
            self.bus[index].set_logic(value)
        else:
            raise Exception("ERROR: Invalid Index value")

    def get_logic(self, index):
        if index > 0 and index < self._width:
            return self.bus[index].get_logic()
        raise Exception("ERROR: Invalid Index value")

    def set_logic_all(self, *values):
        """
        Sets the passed word to the connectors in 4 ways
        1. word as an int representation of the bits of bus ( trucated to digital voltage levels ) : 4 ( 0100 )
        2. word as a binary literal : '0b0001' or '1111'
        3. A packed or unpacked list of  connector objects or
           a packed or unpacked list of integer binary values. : [ a, b, c, d ] or *[ 1, 0, None, 1]
        4. A Bus : bus1
        """

        if isinstance(values[0], int):
            word = values[0]
            if word < 0:
                raise Exception("ERROR: Negative value passed")
            word = bin(word)[2:0].zfill(self._width)

        elif isinstance(values[0], str):
            word = values[0]
            # This will convert '11', '0011' and '0b0011' to '0011'
            word = bin(int(word, 2))[2:].zfill(self._width)

        elif isinstance(values[0], list):
            word = values[0]
            str_int_bool = lambda o: str(int(bool(o)))
            # This is done to convert Connector elements to logic states or to
            # ensure the list passed is binary
            word = "".join(list(map(str_int_bool, word)))

        elif isinstance(values[0], Bus):
            word = values.get_logic_all(as_list=False)

        elif isinstance(values[0], Connector):
            str_int_bool = lambda o: str(int(bool(o)))
            word = list(map(str_int_bool, values))

        else:
            raise Exception("ERROR: Invalid input")

        word = list(map(int, word))

        if len(word) != self._width:
            # If input width is not of same size as the bus raise an exception
            raise Exception(
                "ERROR: Input width is not the same as that of the bus")

        for (bit, conn) in zip(word, self.bus):
            conn.set_logic(bit)

    def get_logic_all(self, as_list=True):
        if as_list:
            return list(map(int, self.bus))

        return "0b" + "".join((list(map(lambda o: str(int(o)), self.bus))))

    def set_voltage_all(self, *values):
        """
        Set the voltage of all the connectors in the bus in 4 ways:
        1. Packed or unpacked List of connectors
        2. Bus
        3. Packed or unpacked List of voltage values
        """

        # If a list is passed as such or the values[0] is a Bus

        if isinstance(values[0], list):
            values = values[0]
            values = list(map(float, values))
            # This serves dual purpose:
            # 1. Converts 5 to 5.0
            # 2. When inputs are connectors it extracts the voltage data from
            # them.

        if isinstance(values[0], Bus):
            values = float(values[0])

        if len(values) != self._width:
            raise Exception(
                "ERROR: Input width is not the same as that of the bus")

        for (volt, conn) in zip(values, self.bus):
            conn.set_voltage(volt)

    def get_voltage_all(self):
        return list(map(float, self.bus))

    def copy(self):
        # Returns a copy of bus
        return Bus(self)

    __copy__ = copy

    def copy_values_to(self, bus):
        """Copy values between two busses"""
        if not isinstance(bus, Bus):
            raise Exception("ERROR: Invalid input""")

        if bus.width != self._width:
            raise Exception("ERROR: Width of both the busses must be same")

        bus.set_voltage_all(self.get_voltage_all())

    def copy_values_from(self, bus):
        """Copy values between two busses"""
        if not isinstance(bus, Bus):
            raise Exception("ERROR: Invalid input""")

        if bus.width != self._width:
            raise Exception("ERROR: Width of both the busses must be same")

        self.set_voltage_all(bus.get_voltage_all())

    def __get__(self, index):
        return self.bus[index]

    def tap(self, index, element, mode):
        if index < 0 or index > self._width:
            raise Exception("ERROR: Invalid Index Value")
        self.bus[index].tap(element, mode)

    def untap(self, index, element, mode):
        if index < 0 or index > self._width:
            raise Exception("ERROR: Invalid Index Value")
        self.bus[index].untap(element, mode)

    def __repr__(self):
        return str(self.bus)

    @property
    def width(self):
        """
        Gives width of the Bus
        """
        return self._width

    @property
    def index(self):
        return self._index

    def trigger(self):
        for conn in self.bus:
            conn.trigger()

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        # self.trigger()

    def __contains__(self, value):

        if isinstance(value, Connector):
            return value in self.bus
        elif isinstance(value, bool):
            return value in list(map(bool, self.bus))
        elif isinstance(value, float):
            return value in list(map(float, self.bus))
        elif isinstance(value, int):
            return value in list(map(int, self.bus))
        else:
            return False

    def __reversed__(self):
        return reversed(self.bus)

    # def __getattr__(self, name):
        # pass

    def __getitem__(self, index):
        return self.bus[index]

    def __len__(self):
        return self._width

    def __int__(self):
        return list(map(int, self.bus))

    def __float__(self):
        return list(map(float, self.bus))

    def __str__(self):
        return str(self.bus)

    def __repr__(self):
        return str(self.bus)

    def __iter__(self):
        return iter(self.bus)
        # Make bus iterable

    def __eq__(self, val):

        bus_values = self.get_voltage_all(
        ) if self.analog else self.get_logic_all()

        if isinstance(val, Bus):
            return bus_values == (
                val.get_voltage_all() if self.analog else val.get_logic_all())

        elif isinstance(val, list):
            return bus_values == val

        elif isinstance(val, str):
            return int(val, 2) == self.get_logic_all(as_list=False)

        raise Exception("ERROR: Invalid Comparison")

    def __rshift__(self):
        """ Clock wise right shift """
        return self.bus[-1] + self.bus[1:-1]

    def __lshift__(self):
        """ Clock wise left shift """
        return self.bus[1:] + self.bus[:1]

    def __add__(self, other):
        """ Returns the concatenated Bus with the passed bus"""
        return Bus(self.bus + other.bus)

    def __bool__(self):
        return list(map(bool, self.bus))

    __nonzero__ = __bool__

########NEW FILE########
__FILENAME__ = gates
"""
Contains
========

* GATES(Base class for all the gates)
* MIGATES(Base class for multiple input gates inherits GATES)
* AND
* OR
* NOT
* XOR
* XNOR
* NAND
* NOR
"""


from BinPy.Gates.connector import *


class GATES:

    '''
    Base Class implementing all common functions used by Logic Gates
    '''

    def __init__(self, inputs):

        # Clean Connections before updating new connections
        self.history_active = 0  # Ignore history for first computation
        self.outputType = 0  # 1->output goes to a connector class
        self.result = None  # To store the result
        self.outputConnector = None  # Valid only if outputType = 1
        self.inputs = inputs[:]  # Set the inputs
        self.history_inputs = []  # Save a copy of the inputs
        self._updateConnections()
        self._updateHistory()
        self.trigger()
        # Any change in the input will trigger change in the
        # output

    def _updateConnections(self):
        for i in self.inputs:
            if isinstance(i, Connector):
                i.tap(self, 'input')

    def setInputs(self, *inputs):
        """
        This method sets multiple inputs of the gate at a time.
        You can also use setInput() multiple times with different index
        to add multiple inputs to the gate.
        """

        # Clean Connections before updating new connections
        if len(inputs) < 2:
            raise Exception("ERROR: Too few inputs given")
        else:
            self.history_active = 1  # Use history before computing
            self.inputs = list(inputs)[:]  # Set the inputs
            self._updateConnections()
        self.trigger()
        # Any change in the input will trigger change in the
        # output

    def setInput(self, index, value):
        """
        This method is used to add input to a gate.
        It requires an index and a value/connector object to add
        an input to the gate.
        """

        if index >= len(self.inputs):
            # If the index is more than the length then append to the list
            self.inputs.append(value)
            # Dont use history after a new input is added
            self.history_active = 0
            self._updateHistory()
        # because history_active is set to 0 trigger
        # will get called irrespective of the history.
        else:
            self.history_active = 1  # Use history before computing
            if isinstance(self.inputs[index], Connector):
                self.history_inputs[index] = self.inputs[index].state
            else:
                self.history_inputs[index] = self.inputs[
                    index]  # Modify the history
            self.inputs[index] = value
        if isinstance(value, Connector):
            value.tap(self, 'input')
        self.trigger()

    def getInputStates(self):
        """
        This method returns the input states of the gate
        """

        input_states = []
        for i in self.inputs:
            if isinstance(i, Connector):
                input_states.append(i.state)
            else:
                input_states.append(i)
        return input_states

    def _updateResult(self, value):
        if value is None:
            self.result = None
        else:
            self.result = int(value)  # Set True or False
        if self.outputType == 1:
            self.outputConnector.state = self.result

    def _updateHistory(self):
        for i in range(len(self.inputs)):
            if isinstance(self.inputs[i], Connector):
                val1 = self.inputs[i].state
            else:
                val1 = self.inputs[i]
            if len(self.history_inputs) <= i:
                self.history_inputs.append(val1)
            else:
                self.history_inputs[i] = val1

    def setOutput(self, connector):
        """
        This method sets the output of the gate. It connects
        the passed connector to its output.
        """

        if not isinstance(connector, Connector):
            raise Exception("ERROR: Expecting a Connector Class Object")
        connector.tap(self, 'output')
        self.outputType = 1
        self.outputConnector = connector
        self.history_active = 0
        self.trigger()

    def resetOutput(self):
        """
        The method resets the output of the gate. The output of the gate is not
        directed to any Connector Object
        """

        self.outputConnector.untap(self, 'output')
        self.outputType = 0
        self.outputConnector = None

    def output(self):
        """
        This methods returns the output of the gate.
        """

        self.trigger()
        return self.result

    def __repr__(self):
        '''
        Simple way to do 'print g', where g would be an instance of any gate
        class. Functions returns the result of self.output() as a string.
        '''

        return str(self.output())

    def buildStr(self, gate_name):
        '''
        Returns a string representation of a gate, where gate_name is the class
        name For example, for an AND gate with two inputs the resulting string
        would be: 'AND Gate; Output: 0; Inputs: [0, 1];'
        '''

        return gate_name + " Gate; Output: " + \
            str(self.output()) + "; Inputs: " + \
            str(self.getInputStates()) + ";"

    def _compareHistory(self):
        if self.history_active == 1:  # Only check history if it is active
            for i in range(len(self.inputs)):
                if isinstance(self.inputs[i], Connector):
                    val1 = self.inputs[i].state
                else:
                    val1 = self.inputs[i]
                if i >= len(self.history_inputs) or self.history_inputs[i]\
                        != val1:
                    return True
            return False
        return True


class MIGATES(GATES):

    """
    This class makes GATES compatible with multiple inputs.
    """

    def __init__(self, *inputs):
        if len(inputs) < 2:
            raise Exception(
                "ERROR: Too few inputs given. Needs at least 2 or\
                 more inputs.")

        GATES.__init__(self, list(inputs))

    def addInput(self, value):
        """
        This method adds an input to an existing gate
        """

        self.history_active = 0  # Don't use history after adding an input
        self.inputs.append(value)
        self._updateConnections()
        self._updateHistory()

    def removeInput(self, index):
        """
        This method removes an input whose index is passed
        """

        if len(self.inputs) - 1 < 2:
            raise Exception("ERROR: Too few inputs left after removing")

        if index > len(self.inputs):
            raise Exception("ERROR: Index value out of range")

        self.history_active = 0
        self.inputs.pop(index)
        self._updateConnections()
        self._updateHistory()


class AND(MIGATES):

    """
    This class implements AND gate

    Examples
    ========

    >>> from BinPy import *
    >>> gate = AND(0, 1)
    >>> gate.output()
    0
    >>> gate.setInputs(1, 1, 1, 1)
    >>> gate.output()
    1
    >>> conn = Connector()
    >>> gate.setOutput(conn)
    >>> gate2 = AND(conn, 1)
    >>> gate2.output()
    1
    """

    def __init__(self, *inputs):
        MIGATES.__init__(self, *inputs)

    def trigger(self):
        if self._compareHistory():
            self.history_active = 1
            self._updateResult(True)
            self._updateHistory()  # Update the inputs after a computation
            val = True
            for i in self.inputs:
                if (isinstance(i, Connector)):
                    val = val and i.state
                elif (isinstance(i, GATES)):
                    val = val and i.output()
                else:
                    val = val and i

            self._updateResult(val)
            if self.outputType:
                self.outputConnector.trigger()

    def __str__(self):
        return self.buildStr("AND")


class OR(MIGATES):

    """
    This class implements OR gate

    Examples
    ========

    >>> from BinPy import *
    >>> gate = OR(0, 1)
    >>> gate.output()
    1
    >>> gate.setInputs(0, 0, 0, 0)
    >>> gate.output()
    0
    >>> conn = Connector()
    >>> gate.setOutput(conn)
    >>> gate2 = AND(conn, 1)
    >>> gate2.output()
    0
    """

    def __init__(self, *inputs):
        MIGATES.__init__(self, *inputs)

    def trigger(self):
        if self._compareHistory():
            self.history_active = 1
            self._updateResult(False)
            self._updateHistory()  # Update the inputs after a computation
            val = False
            for i in self.inputs:
                if (isinstance(i, Connector)):
                    val = val or i.state
                elif (isinstance(i, GATES)):
                    val = val or i.output()
                else:
                    val = val or i

            self._updateResult(val)
            if self.outputType:
                self.outputConnector.trigger()

    def __str__(self):
        return self.buildStr("OR")


class NOT(GATES):

    """
    This class implements NOT gate

    Examples
    ========

    >>> from BinPy import *
    >>> gate = NOT(0)
    >>> gate.output()
    1
    >>> conn = Connector()
    >>> gate.setOutput(conn)
    >>> gate2 = AND(conn, 1)
    >>> gate2.output()
    1
    """

    def __init__(self, *inputs):
        if len(inputs) != 1:
            raise Exception("ERROR: NOT Gates takes only one input")
        else:
            GATES.__init__(self, list(inputs))

    def setInputs(self, *inputs):
        # Clean Connections before updating new connections
        if len(inputs) != 1:
            raise Exception("ERROR: NOT Gates takes only one input")
        else:
            self.history_active = 1  # Use history before computing
            self.inputs = list(inputs)[:]  # Set the inputs
            self._updateConnections()
        self.trigger()
        # Any change in the input will trigger change in the
        # output

    def setInput(self, value):
        self.setInputs(value)

    def trigger(self):
        if self._compareHistory():
            self.history_active = 1
            self._updateHistory()  # Update the inputs after a computation
            if (isinstance(self.inputs[0], Connector)):
                self._updateResult(not self.inputs[0].state)
            elif (isinstance(self.inputs[0], GATES)):
                self._updateResult(not self.inputs[0].output())
            else:
                self._updateResult(not self.inputs[0])
            if self.outputType == 1:
                self.outputConnector.trigger()

    def __str__(self):
        return self.buildStr("NOT")


class XOR(MIGATES):

    """
    This class implements XOR gate

    Examples
    ========

    >>> from BinPy import *
    >>> gate = XOR(0, 1)
    >>> gate.output()
    1
    >>> gate.setInputs(1, 0, 1, 0)
    >>> gate.output()
    0
    >>> conn = Connector()
    >>> gate.setOutput(conn)
    >>> gate2 = AND(conn, 1)
    >>> gate2.output()
    0
    """

    def __init__(self, *inputs):
        MIGATES.__init__(self, *inputs)

    def trigger(self):
        if self._compareHistory():
            self.history_active = 1
            self._updateResult(True)
            self._updateHistory()  # Update the inputs after a computation
            temp = 1
            for i in self.inputs:
                if isinstance(i, Connector):
                    val = i.state
                elif isinstance(i, GATES):
                    val = i.output()
                else:
                    val = i
                temp = (temp and not val) or (not temp and val)
            temp = (temp and not 1) or (not temp and 1)
            self._updateResult(temp)
            if self.outputType:
                self.outputConnector.trigger()

    def __str__(self):
        return self.buildStr("XOR")


class XNOR(MIGATES):

    """
    This class implements XNOR gate

    Examples
    ========

    >>> from BinPy import *
    >>> gate = XNOR(0, 1)
    >>> gate.output()
    0
    >>> gate.setInputs(1, 0, 1, 0)
    >>> gate.output()
    1
    >>> conn = Connector()
    >>> gate.setOutput(conn)
    >>> gate2 = AND(conn, 1)
    >>> gate2.output()
    1
    """

    def __init__(self, *inputs):
        MIGATES.__init__(self, *inputs)

    def trigger(self):
        if self._compareHistory():
            self.history_active = 1
            self._updateResult(True)
            self._updateHistory()  # Update the inputs after a computation
            temp = 1
            for i in self.inputs:
                if (isinstance(i, Connector)):
                    val = i.state
                elif isinstance(i, GATES):
                    val = i.output()
                else:
                    val = i
                temp = (temp and not val) or (not temp and val)
            temp = (temp and not 1) or (not temp and 1)
            self._updateResult(not temp)
            if self.outputType:
                self.outputConnector.trigger()

    def __str__(self):
        return self.buildStr("XNOR")


class NAND(MIGATES):

    """
    This class implements NAND gate

    Examples
    ========

    >>> from BinPy import *
    >>> gate = NAND(0, 1)
    >>> gate.output()
    1
    """

    def __init__(self, *inputs):
        MIGATES.__init__(self, *inputs)

    def trigger(self):
        if self._compareHistory():
            self.history_active = 1
            self._updateResult(False)
            self._updateHistory()  # Update the inputs after a computation
            val = True
            for i in self.inputs:
                if (isinstance(i, Connector)):
                    val = val and i.state

                elif (isinstance(i, GATES)):
                    val = val and i.output()
                else:
                    val = val and i

            self._updateResult(not val)
            if self.outputType:
                self.outputConnector.trigger()

    def __str__(self):
        return self.buildStr("NAND")


class NOR(MIGATES):

    """
    This class implements NOR gate

    Examples
    ========

    >>> from BinPy import *
    >>> gate = NOR(0, 1)
    >>> gate.output()
    0
    """

    def __init__(self, *inputs):
        MIGATES.__init__(self, *inputs)

    def trigger(self):
        if self._compareHistory():
            self.history_active = 1
            self._updateResult(True)
            self._updateHistory()  # Update the inputs after a computation
            val = False
            for i in self.inputs:
                if (isinstance(i, Connector)):
                    val = val or i.state
                elif (isinstance(i, GATES)):
                    val = val or i.output()
                else:
                    val = val or i

            self._updateResult(not val)

            if self.outputType:
                self.outputConnector.trigger()

    def __str__(self):
        return self.buildStr("NOR")

########NEW FILE########
__FILENAME__ = tree
"""
Contains
=======

* Tree
* CycleHist
* CycleHistValue
"""


from __future__ import print_function
from sys import stdout
from BinPy.Gates.gates import *
from BinPy.Gates.connector import *


class Tree:

    '''
    This class is a tree representation of a digital element, such as a
    gate, and its inputs. The class uses the backtrack() function which follows
    the element and tracks the inputs, and inputs of inputs, and so on, thus
    constructing the backtrack tree.

    The tree construction has the possibility to not follow cycles so the final
    output is simpler.

    The printTree() function can be used to print the Tree in a readable way.
    The following examples show two use cases, one of which shows what happens
    if cycles are not being followed.

    Examples
    ========

    >>> g1 = AND(True, False)
    >>> g2 = AND(True, False)
    >>> g3 = AND(g1, g2)
    >>> tree = Tree(g3, 2)
    >>> tree.backtrack()
    >>> tree.printTree()
    |- AND Gate; Output: 0; Inputs: [0, 0];
       |- AND Gate; Output: 0; Inputs: [True, False];
          |- True
          |- False
       |- AND Gate; Output: 0; Inputs: [True, False];
          |- True
          |- False

    If the algorithm was executed to not follow cycles, the output will have
    marks indicating repetitions. In the following example the elements
    marked with [0] are the same and have no sons to avoid repetitive
    output. The same for the elements with [1].

    >>> c1 = Connector(True)
    >>> c2 = Connector(True)
    >>> g1 = AND(True, c1)
    >>> g2 = AND(c2, False)
    >>> g3 = AND(g1, g2)
    >>> g4 = AND(g3, True)
    >>> g3.setOutput(c1)
    >>> g4.setOutput(c2)
    |- [1] AND Gate; Output: 0; Inputs: [0, True];
       |- [0] AND Gate; Output: 0; Inputs: [0, 0];
          |- AND Gate; Output: 0; Inputs: [True, 0];
             |- True
             |- Connector; State: 0
                |- [0] AND Gate; Output: 0; Inputs: [0, 0];
          |- AND Gate; Output: 0; Inputs: [0, False];
             |- Connector; State: 0
                |- [1] AND Gate; Output: 0; Inputs: [0, True];
             |- False
       |- True
    '''

    def __init__(self, element, depth=0, cycles=True):
        '''
        Constructor for the tree class

        Keyword arguments:
        element -- Any digital element, such as a gate. This gate will be
                   the root of the tree. The inputs will be the sons.
        depth   -- Depth until which the inputs are tracked. (default 0)
        cycles  -- If the tree such track cycles in the circuits or not. (default True)
        '''
        self.element = element
        self.depth = depth
        self.cycles = cycles

        self.sons = []

    def setDepth(self, val):
        '''
        Sets depth until which the tree is constructed.

        val -- New depth.
        '''

        self.depth = val
        self.resetTree()

    def resetTree(self):
        self.sons = []
        self.hist = None

    def backtrack(self, hist=None):
        '''
        Constructs the backtrack hierarchy of the tree up to self.depth.

        Keyword arguments:
        hist -- An instance of CycleHist. A class which maintains the passed
                tracked if backtrack is not following cycles. Should only be
                used internally.
        '''

        # Store new history if available, or create new one
        if hist is not None:
            self.hist = hist
        else:
            self.hist = CycleHist()

        # Depth must be bigger than 0
        if self.depth < 0:
            raise Exception(
                "ERROR: Depth of backtrack function must be bigger or\
                    equal to 0")

        # Check if the element is a gate, connector or a final value, bool or
        # int
        if not (isinstance(self.element, GATES) or isinstance(self.element, Connector)
                or type(self.element) in [bool, int]):
            raise Exception(
                "ERROR: Element must be either a Gate or Connector")

        # If the algorithm is not following cycles and this element is not in
        # the history, add it
        if not self.cycles and type(self.element) not in [bool, int]:
            self.hist.regOccurrence(self.element)

            if self.hist.isRepeated(self.element):
                return

        # If the element is a gate
        if isinstance(self.element, GATES):
            if self.depth != 0:
                self.sons = []
                for i in self.element.inputs:
                    son = Tree(i, self.depth - 1, self.cycles)
                    son.backtrack(self.hist)
                    self.sons.append(son)

        # If the element is a connector
        elif isinstance(self.element, Connector):
            if self.depth != 0:
                self.sons = []
                for i in self.element.connections["output"]:
                    son = Tree(i, self.depth - 1, self.cycles)
                    son.backtrack(self.hist)
                    self.sons.append(son)

    def printTree(self, space=0):
        '''
        This function prints the tree in a readable way.
        The way a gate, or a mux or any other digital element gets
        represented depends on it's __str__() implementation.

        Keyword arguments:
        space -- Number of spaces which are going to be printed in each
                 recursive step. Should only be used internally. (default 0)
        '''
        self.printTuple(self.node)

    def printTuple(self, tree_node, space=0):

        # Print a few spaces
        self.printSpaces(space)
        stdout.write("|- ")

        # Print the element
        if not self.cycles:
            if type(self.element) not in [int, bool] and\
                    self.hist.isRepeated(self.element):
                stdout.write(
                    "[" + str(self.hist.getIndex(self.element)) + "] ")

        print(self.element)

        # Print the sons
        for i in self.sons:
            i.printTree(space + 1)

    def printSpaces(self, space):
        for i in range(space):
            stdout.write("   ")

    def __call__(self):
        self.printTree()


class CycleHist:

    '''
    This class helps to keep the cycle history of a circuit by registering
    occurrences of a digital element. The class has a dictionary that stores
    an instance of CycleHistValue for each key element.
    '''

    def __init__(self):
        self.hist = {}
        self.current_index = 0

    def regOccurrence(self, element):
        '''
        Register an occurrence for an element. If the element has been seen
        before, mark that element has a repeating element.

        Keyword arguments:
        element -- Any digital element to be added to the dictionary.
        '''

        # If the element has been seen before
        if element in self.hist.keys():
            val = self.hist[element]

            # If it has been seen before and this is the first repetition, mark
            # it has repeating and give it an index
            if not val.isRepeated():
                val.setRepeated()
                val.setIndex(self.current_index)
                self.current_index += 1

        # If not, create a CycleHistValue object for it
        else:
            self.hist[element] = CycleHistValue()

    def getIndex(self, element):
        '''
        Get the repetition index for the given element

        Keyword arguments:
        element -- A digital element in the dictionary
        '''

        return self.hist[element].getIndex()

    def isRepeated(self, element):
        '''
        Check if the given element is repeating or not

        Keyword arguments:
        element -- The element that is being check if it is repeated or not.
        '''

        return self.hist[element].isRepeated()


class CycleHistValue:

    '''
    This class represents the value in the dictionary of the CycleHist class.
    It has the index of the element and if it has been repeated or not.
    '''

    def __init__(self):
        self.repeated = False
        self.index = 0

    def setIndex(self, index):
        '''
        Set the index of the element for which this instance is associated.

        Keyword arguments:
        index -- The index in question.
        '''

        self.index = index

    def getIndex(self):
        '''
        Get index of the element of this instance.
        '''

        return self.index

    def setRepeated(self):
        '''
        Set is the element of this instance is repeated or not.
        '''

        self.repeated = True

    def isRepeated(self):
        '''
        Check if the element for which this instance is associated is repeated
        or not.
        '''

        return self.repeated

########NEW FILE########
__FILENAME__ = base
"""
This module includes all the base classes for different ICs.
"""
from __future__ import print_function
from BinPy import *
import sys

try:
    _V = chr(9474)
    _H = chr(9472)
    _HVD = chr(9488)
    _HVU = chr(9496)
    _VHU = chr(9484)
    _VHD = chr(9492)
    _N = chr(10)
    _U = chr(9697)
    _LT = chr(9508)
    _RT = chr(9500)
except:
    _V = unichr(9474)
    _H = unichr(9472)
    _HVD = unichr(9488)
    _HVU = unichr(9496)
    _VHU = unichr(9484)
    _VHD = unichr(9492)
    _N = unichr(10)
    _U = unichr(9697)
    _LT = unichr(9508)
    _RT = unichr(9500)


class IC:

    """
    This is a base class for IC
    """
    outputConnector = {}

    def __init__(self):
        pass

    def setOutput(self, index, value):
        if not isinstance(value, Connector):
            raise Exception("ERROR: Expecting a connector class object")
        value.tap(self, 'output')
        self.outputConnector[index] = value
        try:
            output = self.run()
        except:
            print("Invalid Argument")

    def setIC(self, param_dict):
        """
        If pin class is not used this method then it takes a dictionary with the format { PINNO:PINVALUE, ... }
        Else it takes a dictionary of dictionaries with the format ->
        { PINNO:{PARAM1:VAL1, PARAM2:VAL2, ... }, PINNO2:{PARAM1:VAL1, PARAM2:VAL2, ... } , ... }
        """
        for pin in param_dict:
            if not self.uses_pincls:
                self.pins[pin] = param_dict[pin]
            else:
                self.pins[pin].setPinParam(param_dict[pin])

    def drawIC(self):
        try:

            if (self.total_pins in [14, 16]):

                top = "\n\n              " + _VHU + \
                    _H * 9 + _U + _H * 9 + _HVD + _N
                bottom = "              " + _VHD + _H * 19 + _HVU + "  "
                diag = top

                ic_number = str(self.__class__.__name__.split('_')[-1])
                ic_name = ' ' * 2 + ic_number + ' ' * 10

                # IC number is obtained by the __class__.__name__ parameter
                # assuming the naming of the class is such that last 4 digits
                # correspond to the IC Number.

                for i in range(1, (self.total_pins // 2) + 1):

                    j = self.total_pins - i + 1
                    if self.uses_pincls:
                        v1 = 'Z' if self.pins[i].value is None else str(
                            self.pins[i].value)
                        v2 = 'Z' if self.pins[j].value is None else str(
                            self.pins[j].value)

                        f = (
                            self.pins[i].pin_tag,
                            v1,
                            str(i),
                            ic_name[i],
                            str(j),
                            v2,
                            self.pins[j].pin_tag)

                    else:
                        v1 = 'Z' if self.pins[i] is None else str(self.pins[i])
                        v2 = 'Z' if self.pins[j] is None else str(self.pins[j])

                        f = ('   ', v1, str(i), ic_name[i], str(j), v2, '   ')
                    diag += "              |                   |\n"
                    diag += " %3s [%1s]    ---| %2s      %1s     %2s  |---    [%1s] %3s\n" % f
                    diag += "              |                   |\n"

                diag += bottom
                diag = diag.replace(
                    "---|",
                    _H *
                    2 +
                    _LT).replace(
                    "|---",
                    _RT +
                    _H *
                    2).replace(
                    '|',
                    _V)
                print(diag)

            else:
                raise Exception("ERROR: IC not supported")
        except:
            print("ERROR: Draw Failed - " + sys.exc_info()[1].args[0])

    def truthtable(self, pinConfig):

        if isinstance(self, Base_14pin):
            a = {
                1: 0,
                2: 0,
                3: 0,
                4: 0,
                5: 0,
                6: 0,
                7: 0,
                8: 0,
                9: 0,
                10: 0,
                11: 0,
                12: 0,
                13: 0,
                14: 1}
        elif isinstance(self, Base_16pin):
            a = {
                1: 0,
                2: 0,
                3: 0,
                4: 0,
                5: 0,
                6: 0,
                7: 0,
                8: 0,
                9: 0,
                10: 0,
                11: 0,
                12: 0,
                13: 0,
                14: 1,
                15: 0,
                16: 1}
        elif isinstance(self, Base_5pin):
            a = {1: 0, 2: 0, 3: 0, 4: 0, 5: 1}

        i = pinConfig['i']
        o = pinConfig['o']

        print ("   " + "INPUTS" + (" " * (5 * len(i) - 4)) + "|" + "OUTPUTS")
        print ("   " + "-" * (5 * len(i) + 2) + "|" + "-" * (5 * len(o)))
        stdout.write("   ")
        for j in range(len(i)):
            if len(str(i[j])) == 1:
                print ("   " + str(i[j]), end=" ")
            elif len(str(i[j])) == 2:
                print ("  " + str(i[j]), end=" ")
        stdout.write("  |")
        for j in range(len(o)):
            if len(str(o[j])) == 1:
                print ("   " + str(o[j]), end=" ")
            elif len(str(o[j])) == 2:
                print ("  " + str(o[j]), end=" ")
        print ("\n   " + "-" * (5 * len(i) + 2) + "|" + "-" * (5 * len(o)))

        def f(l):

            if len(l) == 1:
                for q in range(2):
                    a[l[0]] = q
                    inputlist = []

                    for u in range(len(i)):
                        inputlist.append(a[i[u]])

                    if hasattr(self, 'invalidlist'):
                        if inputlist in self.invalidlist:
                            break

                    self.setIC(a)
                    outpins = self.run()

                    stdout.write("   ")
                    for u in range(len(i)):
                        print ("   " + str(a[i[u]]), end=" ")
                    stdout.write("  |")
                    for u in range(len(o)):
                        print ("   " + str(outpins[o[u]]), end=" ")
                    print ("")

            else:
                for q in range(2):
                    a[l[0]] = q
                    f(l[1:])
        f(i)


class Base_5pin(IC):

    """
    This method takes base class for IC's having 5 pins
    """
    total_pins = 5
    uses_pincls = False

    def setPin(self, pin_no, pin_value):
        if pin_no < 1 or pin_no > 5:
            raise Exception("ERROR: There are only 5 pins in this IC")
        if not self.uses_pincls:
            self.pins[pin_no] = pin_value
        else:
            self.pins[pin_no].setPinParam(pin_value)


class Base_14pin(IC):

    """
    This method takes base class for IC's having 14 pins
    """
    total_pins = 14
    uses_pincls = False

    def setPin(self, pin_no, pin_value):
        if pin_no < 1 or pin_no > 14:
            raise Exception("ERROR: There are only 14 pins in this IC")
        if not self.uses_pincls:
            self.pins[pin_no] = pin_value
        else:
            self.pins[pin_no].setPinParam(pin_value)

    def setPinParam(self, pin_no, parm_dict):
        if pin_no < 1 or pin_no > 14:
            raise Exception("ERROR: There are only 14 pins in this IC")
        if uses_pincls:
            self.pins[pin_no].setPinParam(parm_dict)
        else:
            raise Exception("ERROR: IC Does not use Pinset class")


class Base_16pin(IC):

    """
    This method takes base class for IC's having 16 pins
    """
    total_pins = 16
    uses_pincls = False

    def setPin(self, pin_no, pin_value):
        if pin_no < 1 or pin_no > 16:
            raise Exception("ERROR: There are only 16 pins in this IC")
        if not self.uses_pincls:
            self.pins[pin_no] = pin_value
        else:
            self.pins[pin_no].setPinParam(pin_value)

    def SetPinParam(self, pin_no, parm_dict):
        if pin_no < 1 or pin_no > 16:
            raise Exception("ERROR: There are only 16 pins in this IC")
        if uses_pincls:
            self.pins[pin_no].setPinParam(parm_dict)
        else:
            raise Exception("ERROR: IC Does not use Pinset class")


class Pin():

    """
    Pin class for defining a particular pin of an IC

    Sample param_dict for a pin :
    { 'value':0, 'desc':'IN1: Input 1 of Mux', 'can_vary':True }

    First 3 characters of desc will be used as pin_tag

    """

    def __init__(self, pin_no, param_dict={}):

        self.pin_no = pin_no
        self.pin_tag = '   '
        self.__doc__ = ''
        self.can_vary = True
        self.setPinParam(param_dict)

    def setPinParam(self, param_dict):
        if isinstance(param_dict, dict):
            # If a dictionary of parameters is passed, store the contents of the dictionary to the
            # respective parameters
            for param in param_dict:
                if param == 'value':
                    self.value = param_dict[param]
                elif param == 'pin_tag':
                    if len(param_dict[param]) >= 3:
                        self.pin_tag = param_dict[param][:3].upper()
                elif param == 'desc':
                    self.__doc__ = param_dict[param]
                    if len(self.__doc__) >= 3:
                        self.pin_tag = self.__doc__[:3]
                elif param == 'can_vary':
                    self.can_vary = bool(param_dict[param])
                else:
                    print("ERROR: Unknown Parameters passed")
        elif (isinstance(param_dict, int)) and (param_dict in [0, 1, None]):
            # If the value is passed , store the value
            val = param_dict
            self.value = val
        else:
            raise Exception('ERROR: Unrecognized parameter passed.')

    def __str__(self):
        return str(self.value)

    def __call__(self):
        """ The call method returns the logic value of the pin """
        # This method can be used in IC implementations
        return logic(self.value)


def pinlist_quick(first_arg):
    """Defines a method to quickly convert a list of logic states to pin instances"""
    if isinstance(first_arg, list):
        # Quickly converts a list of Logic values to a list of Pin instances
        listofpins = list()
        for i in range(len(first_arg)):
            listofpins.append(
                Pin(i + 1, {'value': first_arg[i], 'desc': '   ', 'can_vary': True}))
        return listofpins
    else:
        raise Exception("ERROR: Unknown parameter type passed")


class logic():

    """
    Implements methods of AND OR and EXOR using BinPy library Gate modules
    Remaps all basic python implementation of gates on variable of type bool to BinPy's implementation of the same
    """

    def __init__(self, value=0):
        if value is bool:
            self.value = int(value)
        else:
            self.value = value
        # Tri state logic can be introduced later on ...

    def __add__(self, right):
        '''OR Gate equivalent'''
        return logic(OR(self.value, right.value).output())
        # Returns a logic instance corresponding to the boolean value of the
        # output of BinPy's OR Gate implementation

    def __or__(self, right):
        '''OR Gate equivalent'''
        return logic(OR(self.value, right.value).output())
        # Returns a logic instance corresponding to the boolean value of the
        # output of BinPy's OR Gate implementation

    def __xor__(self, right):
        '''XOR Gate'''
        return logic(XOR(self.value, right.value).output())
        # Returns a logic instance corresponding to the boolean value of the
        # output of BinPy's XOR Gate implementation

    def __mul__(self, right):
        '''AND Gate'''
        return logic(AND(self.value, right.value).output())
        # Returns a logic instance corresponding to the boolean value of the
        # output of BinPy's AND Gate implementation

    def __and__(self, right):
        '''AND Gate'''
        return logic(AND(self.value, right.value).output())
        # Returns a logic instance corresponding to the boolean value of the
        # output of BinPy's AND Gate implementation

    def __invert__(self):
        '''NOT Gate'''
        return logic(NOT(self.value).output())
        # Returns a logic instance corresponding to the boolean value of the
        # output of BinPy's NOT Gate implementation

    def __call__(self):
        '''Returns the binary equivalent of the logic value of self'''
        return int(self.value)

    def __int__(self):
        return int(self.value)

    def __str__(self):
        return str(int(value))

########NEW FILE########
__FILENAME__ = series_4000
"""
This module has all the classes of ICs belonging to 4000 series.

Please note that the length of list self.pins is 1 more than the number of
actual pins. This is so because pin0 is not used as a general term referring
to the first pin of the IC. Zeroth index of the self.pins is not being used.

ICs in this module:
[4000, 4001, 4002, 4008, 4009, 4010, 4011, 4012, 4013, 4015, 4017, 4019, 4020, 4023, 4025, 4068, 4069, 4070, 4071, 4072, 4073
 4075, 4077, 4078, 4081, 4082]
"""

from __future__ import print_function
from BinPy.Gates import *
from BinPy.ic import *
from BinPy.Combinational import *

#################################
# IC's with 14 pins
#################################


class IC_4000(Base_14pin):

    """
    Dual 3 Input NOR gate + one NOT gate IC.
    Pin_6 = NOR(Pin_3, Pin_4, Pin_5)
    Pin_10 = NOR(Pin_11, Pin_12, Pin_13)
    Pin_9 = NOT(Pin_8)
    """

    def __init__(self):
        self.pins = [None, None, None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'NC'},
                    2: {'desc': 'NC'},
                    3: {'desc': 'A1: Input 1 of NOR gate 1'},
                    4: {'desc': 'B1: Input 2 of NOR gate 1'},
                    5: {'desc': 'C1: Input 3 of NOR gate 1'},
                    6: {'desc': 'Q1: Output of NOR gate 1'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'B2: Input of NOT gate'},
                    9: {'desc': 'Q2: Output of NOT gate'},
                    10: {'desc': 'Q3: Output of NOR gate 2'},
                    11: {'desc': 'C3: Input 3 of NOR gate 2'},
                    12: {'desc': 'B3: Input 2 of NOR gate 2'},
                    13: {'desc': 'A3: Input 1 of NOR gate 2'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[6] = NOR(self.pins[3].value, self.pins[4].value,
                        self.pins[5].value).output()
        output[10] = NOR(self.pins[11].value, self.pins[12].value,
                         self.pins[13].value).output()
        output[9] = NOT(self.pins[8].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4001(Base_14pin):

    """
    Quad 2 input NOR gate
    Pin_3 = NOR(Pin_1, Pin_2)
    Pin_4 = NOR(Pin_5, Pin_6)
    Pin_10 = NOR(Pin_8, Pin_9)
    Pin_11 = NOR(Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'A1: Input 1 of NOR gate 1'},
                    2: {'desc': 'B1: Input 2 of NOR gate 1'},
                    3: {'desc': 'Q1: Output of NOR gate 1'},
                    4: {'desc': 'Q2: Output of NOR gate 2'},
                    5: {'desc': 'B2: Input 2 of NOR gate 2'},
                    6: {'desc': 'A2: Input 1 of NOR gate 2'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A3: Input 1 of NOR gate 3'},
                    9: {'desc': 'B3: Input 2 of NOR gate 3'},
                    10: {'desc': 'Q3: Output of NOR gate 3'},
                    11: {'desc': 'Q4: Output of NOR gate 4'},
                    12: {'desc': 'B4: Input 2 of NOR gate 4'},
                    13: {'desc': 'A4: Input 1 of NOR gate 4'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[3] = NOR(self.pins[1].value, self.pins[2].value).output()
        output[4] = NOR(self.pins[5].value, self.pins[6].value).output()
        output[10] = NOR(self.pins[8].value, self.pins[9].value).output()
        output[11] = NOR(self.pins[12].value, self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4002(Base_14pin):

    """
    Dual 4 input NOR gate
    Pin_1 = NOR(Pin_2, Pin_3, Pin_4, Pin_5)
    Pin_13 = NOR(Pin_9, Pin_10, Pin_11, Pin_12)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'Q1: Output of NOR gate 1'},
                    2: {'desc': 'A1: Input 1 of NOR gate 1'},
                    3: {'desc': 'B1: Input 2 of NOR gate 1'},
                    4: {'desc': 'C1: Input 3 of NOR gate 1'},
                    5: {'desc': 'D1: Input 4 of NOR gate 1'},
                    6: {'desc': 'NC'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'NC'},
                    9: {'desc': 'D2: Input 4 of NOR gate 2'},
                    10: {'desc': 'C2: Input 3 of NOR gate 2'},
                    11: {'desc': 'B2: Input 2 of NOR gate 2'},
                    12: {'desc': 'A2: Input 1 of NOR gate 2'},
                    13: {'desc': 'Q2: Output of NOR gate 2'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[1] = NOR(self.pins[2].value, self.pins[3].value,
                        self.pins[4].value, self.pins[5].value).output()
        output[13] = NOR(self.pins[9].value, self.pins[10].value,
                         self.pins[11].value, self.pins[12].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4011(Base_14pin):

    """
    Quad 2 input NAND gate
    Pin_3 = NAND(Pin_1, Pin_2)
    Pin_4 = NAND(Pin_5, Pin_6)
    Pin_10 = NAND(Pin_8, Pin_9)
    Pin_11 = NAND(Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'A1: Input 1 of NAND gate 1'},
                    2: {'desc': 'B1: Input 2 of NAND gate 1'},
                    3: {'desc': 'Q1: Output of NAND gate 1'},
                    4: {'desc': 'Q2: Output of NAND gate 2'},
                    5: {'desc': 'B2: Input 2 of NAND gate 2'},
                    6: {'desc': 'A2: Input 1 of NAND gate 2'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A3: Input 1 of NAND gate 3'},
                    9: {'desc': 'B3: Input 2 of NAND gate 3'},
                    10: {'desc': 'Q3: Output of NAND gate 3'},
                    11: {'desc': 'Q4: Output of NAND gate 4'},
                    12: {'desc': 'B4: Input 2 of NAND gate 4'},
                    13: {'desc': 'A4: Input 1 of NAND gate 4'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[3] = NAND(self.pins[1].value, self.pins[2].value).output()
        output[4] = NAND(self.pins[5].value, self.pins[6].value).output()
        output[10] = NAND(self.pins[8].value, self.pins[9].value).output()
        output[11] = NAND(self.pins[12].value, self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4012(Base_14pin):

    """
    Dual 4 input NAND gate
    Pin_1 = NAND(Pin_2, Pin_3, Pin_4, Pin_5)
    Pin_13 = NAND(Pin_9, Pin_10, Pin_11, Pin_12)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'Q1: Output of NAND gate 1'},
                    2: {'desc': 'A1: Input 1 of NAND gate 1'},
                    3: {'desc': 'B1: Input 2 of NAND gate 1'},
                    4: {'desc': 'C1: Input 3 of NAND gate 1'},
                    5: {'desc': 'D1: Input 4 of NAND gate 1'},
                    6: {'desc': 'NC'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'NC'},
                    9: {'desc': 'D2: Input 4 of NAND gate 2'},
                    10: {'desc': 'C2: Input 3 of NAND gate 2'},
                    11: {'desc': 'B2: Input 2 of NAND gate 2'},
                    12: {'desc': 'A2: Input 1 of NAND gate 2'},
                    13: {'desc': 'Q2: Output of NAND gate 2'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[1] = NAND(self.pins[2].value, self.pins[3].value,
                         self.pins[4].value, self.pins[5].value).output()
        output[13] = NAND(self.pins[9].value, self.pins[10].value,
                          self.pins[11].value, self.pins[12].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4013(Base_14pin):

    """
    CMOS Dual D type Flip Flop
    """

    def __init__(self):
        self.pins = [None, None, None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = False
        self.setIC({1: {'desc': 'Q1'},
                    2: {'desc': '~Q1'},
                    3: {'desc': 'CLK1'},
                    4: {'desc': 'RST1'},
                    5: {'desc': 'D1'},
                    6: {'desc': 'SET1'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'SET2'},
                    9: {'desc': 'D2'},
                    10: {'desc': 'RST2'},
                    11: {'desc': 'CLK2'},
                    12: {'desc': '~Q2'},
                    13: {'desc': 'Q2'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        if not (isinstance(self.pins[3], Clock) and
                isinstance(self.pins[11],
                           Clock)):
            raise Exception("Error: Invalid Clock Input")
        ff1 = DFlipFlop(self.pins[5], Connector(1), self.pins[3].A,
                        clear=self.pins[6], preset=self.pins[4])
        while True:
            if self.pins[3].A.state == 0:
                ff1.trigger()
                break
        while True:
            if self.pins[3].A.state == 1:
                ff1.trigger()
                break
        output[1] = ff1.state()[0]
        output[2] = ff1.state()[1]

        ff2 = DFlipFlop(self.pins[9], Connector(1), self.pins[11].A,
                        clear=self.pins[8], preset=self.pins[10])
        while True:
            if self.pins[11].A.state == 0:
                ff2.trigger()
                break
        while True:
            if self.pins[11].A.state == 1:
                ff2.trigger()
                break
        output[13] = ff2.state()[0]
        output[12] = ff2.state()[1]

        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4023(Base_14pin):

    """
    Triple 3 input NAND gate
    Pin_6 = NAND(Pin_3, Pin_4, Pin_5)
    Pin_9 = NAND(Pin_1, Pin_2, Pin_8)
    Pin_10 = NAND(Pin_11, Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'C2: Input 3 of NAND gate 2'},
                    2: {'desc': 'B2: Input 2 of NAND gate 2'},
                    3: {'desc': 'C1: Input 3 of NAND gate 1'},
                    4: {'desc': 'B1: Input 2 of NAND gate 1'},
                    5: {'desc': 'A1: Input 1 of NAND gate 1'},
                    6: {'desc': 'Q1: Output of NAND gate 1'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A2: Input 1 of NAND gate 2'},
                    9: {'desc': 'Q2: Output of NAND gate 2'},
                    10: {'desc': 'Q3: Output of NAND gate 3'},
                    11: {'desc': 'A3: Input 1 of NAND gate 3'},
                    12: {'desc': 'B3: Input 2 of NAND gate 3'},
                    13: {'desc': 'C3: Input 3 of NAND gate 3'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[6] = NAND(self.pins[3].value, self.pins[4].value,
                         self.pins[5].value).output()
        output[9] = NAND(self.pins[1].value, self.pins[2].value,
                         self.pins[8].value).output()
        output[10] = NAND(self.pins[11].value, self.pins[12].value,
                          self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4025(Base_14pin):

    """
    Triple 3 input NOR gate
    Pin_6 = NOR(Pin_3, Pin_4, Pin_5)
    Pin_9 = NOR(Pin_1, Pin_2, Pin_8)
    Pin_10 = NOR(Pin_11, Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'C2: Input 3 of NOR gate 2'},
                    2: {'desc': 'B2: Input 2 of NOR gate 2'},
                    3: {'desc': 'C1: Input 3 of NOR gate 1'},
                    4: {'desc': 'B1: Input 2 of NOR gate 1'},
                    5: {'desc': 'A1: Input 1 of NOR gate 1'},
                    6: {'desc': 'Q1: Output of NOR gate 1'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A2: Input 1 of NOR gate 2'},
                    9: {'desc': 'Q2: Output of NOR gate 2'},
                    10: {'desc': 'Q3: Output of NOR gate 3'},
                    11: {'desc': 'A3: Input 1 of NOR gate 3'},
                    12: {'desc': 'B3: Input 2 of NOR gate 3'},
                    13: {'desc': 'C3: Input 3 of NOR gate 3'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[6] = NOR(self.pins[3].value, self.pins[4].value,
                        self.pins[5].value).output()
        output[9] = NOR(self.pins[1].value, self.pins[2].value,
                        self.pins[8].value).output()
        output[10] = NOR(self.pins[11].value, self.pins[12].value,
                         self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4030(Base_14pin):

    """
    Quad 2-input XOR gate
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': '1A'},
                    2: {'desc': '1B'},
                    3: {'desc': '1Y'},
                    4: {'desc': '2Y'},
                    5: {'desc': '2A'},
                    6: {'desc': '2B'},
                    7: {'desc': 'GND'},
                    8: {'desc': '3A'},
                    9: {'desc': '3B'},
                    10: {'desc': '3Y'},
                    11: {'desc': '4Y'},
                    12: {'desc': '4A'},
                    13: {'desc': '4B'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[3] = XOR(self.pins[1].value, self.pins[2].value).output()
        output[4] = XOR(self.pins[5].value, self.pins[6].value).output()
        output[10] = XOR(self.pins[8].value, self.pins[9].value).output()
        output[11] = XOR(self.pins[12].value, self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4068(Base_14pin):

    """
    8 input NAND gate
    Pin_13 = NAND(Pin_2, Pin_3, Pin_4, Pin_5, Pin_9, Pin_10, Pin_11, Pin_12)
    """

    def __init__(self):
        self.pins = [None, None, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'NC'},
                    2: {'desc': 'Input 1 of NAND gate'},
                    3: {'desc': 'Input 2 of NAND gate'},
                    4: {'desc': 'Input 3 of NAND gate'},
                    5: {'desc': 'Input 4 of NAND gate'},
                    6: {'desc': 'NC'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'NC'},
                    9: {'desc': 'Input 5 of NAND gate'},
                    10: {'desc': 'Input 6 of NAND gate'},
                    11: {'desc': 'Input 7 of NAND gate'},
                    12: {'desc': 'Input 8 of NAND gate'},
                    13: {'desc': 'Output of NAND gate'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[13] = NAND(self.pins[2].value, self.pins[3].value,
                          self.pins[4].value, self.pins[5].value,
                          self.pins[9].value, self.pins[10].value,
                          self.pins[11].value, self.pins[12].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4069(Base_14pin):

    """
    Hex NOT gate
    Pin_2 = NOT(Pin_1)
    Pin_4 = NOT(Pin_3)
    Pin_6 = NOT(Pin_5)
    Pin_8 = NOT(Pin_9)
    Pin_10 = NOT(Pin_11)
    Pin_12 = NOT(Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'Input of NOT gate 1'},
                    2: {'desc': 'Output of NOT gate 1'},
                    3: {'desc': 'Input of NOT gate 2'},
                    4: {'desc': 'Output of NOT gate 2'},
                    5: {'desc': 'Input of NOT gate 3'},
                    6: {'desc': 'Output of NOT gate 3'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'Output of NOT gate 4'},
                    9: {'desc': 'Input of NOT gate 4'},
                    10: {'desc': 'Output of NOT gate 5'},
                    11: {'desc': 'Input of NOT gate 5'},
                    12: {'desc': 'Output of NOT gate 6'},
                    13: {'desc': 'Input of NOT gate 6'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[2] = NOT(self.pins[1].value).output()
        output[4] = NOT(self.pins[3].value).output()
        output[6] = NOT(self.pins[5].value).output()
        output[8] = NOT(self.pins[9].value).output()
        output[10] = NOT(self.pins[11].value).output()
        output[12] = NOT(self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4070(Base_14pin):

    """
    Quad 2 input XOR gate
    Pin_3 = XOR(Pin_1, Pin_2)
    Pin_4 = XOR(Pin_5, Pin_6)
    Pin_10 = XOR(Pin_8, Pin_9)
    Pin_11 = XOR(Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'A1: Input 1 of XOR gate 1'},
                    2: {'desc': 'B1: Input 2 of XOR gate 1'},
                    3: {'desc': 'Q1: Output of XOR gate 1'},
                    4: {'desc': 'Q2: Output of XOR gate 2'},
                    5: {'desc': 'B2: Input 2 of XOR gate 2'},
                    6: {'desc': 'A2: Input 1 of XOR gate 2'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A3: Input 1 of XOR gate 3'},
                    9: {'desc': 'B3: Input 2 of XOR gate 3'},
                    10: {'desc': 'Q3: Output of XOR gate 3'},
                    11: {'desc': 'Q4: Output of XOR gate 4'},
                    12: {'desc': 'B4: Input 2 of XOR gate 4'},
                    13: {'desc': 'A4: Input 1 of XOR gate 4'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[3] = XOR(self.pins[1].value, self.pins[2].value).output()
        output[4] = XOR(self.pins[5].value, self.pins[6].value).output()
        output[10] = XOR(self.pins[8].value, self.pins[9].value).output()
        output[11] = XOR(self.pins[12].value, self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4071(Base_14pin):

    """
    Quad 2 input OR gate
    Pin_3 = OR(Pin_1, Pin_2)
    Pin_4 = OR(Pin_5, Pin_6)
    Pin_10 = OR(Pin_8, Pin_9)
    Pin_11 = OR(Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'A1: Input 1 of OR gate 1'},
                    2: {'desc': 'B1: Input 2 of OR gate 1'},
                    3: {'desc': 'Q1: Output of OR gate 1'},
                    4: {'desc': 'Q2: Output of OR gate 2'},
                    5: {'desc': 'B2: Input 2 of OR gate 2'},
                    6: {'desc': 'A2: Input 1 of OR gate 2'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A3: Input 1 of OR gate 3'},
                    9: {'desc': 'B3: Input 2 of OR gate 3'},
                    10: {'desc': 'Q3: Output of OR gate 3'},
                    11: {'desc': 'Q4: Output of OR gate 4'},
                    12: {'desc': 'B4: Input 2 of OR gate 4'},
                    13: {'desc': 'A4: Input 1 of OR gate 4'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[3] = OR(self.pins[1].value, self.pins[2].value).output()
        output[4] = OR(self.pins[5].value, self.pins[6].value).output()
        output[10] = OR(self.pins[8].value, self.pins[9].value).output()
        output[11] = OR(self.pins[12].value, self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4072(Base_14pin):

    """
    Dual 4 input OR gate
    Pin_1 = OR(Pin_2, Pin_3, Pin_4, Pin_5)
    Pin_13 = OR(Pin_9, Pin_10, Pin_11, Pin_12)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'Q1: Output of OR gate 1'},
                    2: {'desc': 'A1: Input 1 of OR gate 1'},
                    3: {'desc': 'B1: Input 2 of OR gate 1'},
                    4: {'desc': 'C1: Input 3 of OR gate 1'},
                    5: {'desc': 'D1: Input 4 of OR gate 1'},
                    6: {'desc': 'NC'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'NC'},
                    9: {'desc': 'D2: Input 4 of OR gate 2'},
                    10: {'desc': 'C2: Input 3 of OR gate 2'},
                    11: {'desc': 'B2: Input 2 of OR gate 2'},
                    12: {'desc': 'A2: Input 1 of OR gate 2'},
                    13: {'desc': 'Q2: Output of OR gate 2'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[1] = OR(self.pins[2].value, self.pins[3].value,
                       self.pins[4].value, self.pins[5].value).output()
        output[13] = OR(self.pins[9].value, self.pins[10].value,
                        self.pins[11].value, self.pins[12].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4073(Base_14pin):

    """
    Triple 3 input AND gate
    Pin_6 = AND(Pin_3, Pin_4, Pin_5)
    Pin_9 = AND(Pin_1, Pin_2, Pin_8)
    Pin_10 = AND(Pin_11, Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'C2: Input 3 of AND gate 2'},
                    2: {'desc': 'B2: Input 2 of AND gate 2'},
                    3: {'desc': 'C1: Input 3 of AND gate 1'},
                    4: {'desc': 'B1: Input 2 of AND gate 1'},
                    5: {'desc': 'A1: Input 1 of AND gate 1'},
                    6: {'desc': 'Q1: Output of AND gate 1'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A2: Input 1 of AND gate 2'},
                    9: {'desc': 'Q2: Output of AND gate 2'},
                    10: {'desc': 'Q3: Output of AND gate 3'},
                    11: {'desc': 'A3: Input 1 of AND gate 3'},
                    12: {'desc': 'B3: Input 2 of AND gate 3'},
                    13: {'desc': 'C3: Input 3 of AND gate 3'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[6] = AND(self.pins[3].value, self.pins[4].value,
                        self.pins[5].value).output()
        output[9] = AND(self.pins[1].value, self.pins[2].value,
                        self.pins[8].value).output()
        output[10] = AND(self.pins[11].value, self.pins[12].value,
                         self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4075(Base_14pin):

    """
    Triple 3 input OR gate
    Pin_6 = OR(Pin_3, Pin_4, Pin_5)
    Pin_9 = OR(Pin_1, Pin_2, Pin_8)
    Pin_10 = OR(Pin_11, Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'C2: Input 3 of OR gate 2'},
                    2: {'desc': 'B2: Input 2 of OR gate 2'},
                    3: {'desc': 'C1: Input 3 of OR gate 1'},
                    4: {'desc': 'B1: Input 2 of OR gate 1'},
                    5: {'desc': 'A1: Input 1 of OR gate 1'},
                    6: {'desc': 'Q1: Output of OR gate 1'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A2: Input 1 of OR gate 2'},
                    9: {'desc': 'Q2: Output of OR gate 2'},
                    10: {'desc': 'Q3: Output of OR gate 3'},
                    11: {'desc': 'A3: Input 1 of OR gate 3'},
                    12: {'desc': 'B3: Input 2 of OR gate 3'},
                    13: {'desc': 'C3: Input 3 of OR gate 3'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[6] = OR(self.pins[3].value, self.pins[4].value,
                       self.pins[5].value).output()
        output[9] = OR(self.pins[1].value, self.pins[2].value,
                       self.pins[8].value).output()
        output[10] = OR(self.pins[11].value, self.pins[12].value,
                        self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4077(Base_14pin):

    """
    Quad 2 input XNOR gate
    Pin_3 = XNOR(Pin_1, Pin_2)
    Pin_4 = XNOR(Pin_5, Pin_6)
    Pin_10 = XNOR(Pin_8, Pin_9)
    Pin_11 = XNOR(Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'A1: Input 1 of XNOR gate 1'},
                    2: {'desc': 'B1: Input 2 of XNOR gate 1'},
                    3: {'desc': 'Q1: Output of XNOR gate 1'},
                    4: {'desc': 'Q2: Output of XNOR gate 2'},
                    5: {'desc': 'B2: Input 2 of XNOR gate 2'},
                    6: {'desc': 'A2: Input 1 of XNOR gate 2'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A3: Input 1 of XNOR gate 3'},
                    9: {'desc': 'B3: Input 2 of XNOR gate 3'},
                    10: {'desc': 'Q3: Output of XNOR gate 3'},
                    11: {'desc': 'Q4: Output of XNOR gate 4'},
                    12: {'desc': 'B4: Input 2 of XNOR gate 4'},
                    13: {'desc': 'A4: Input 1 of XNOR gate 4'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[3] = XNOR(self.pins[1].value, self.pins[2].value).output()
        output[4] = XNOR(self.pins[5].value, self.pins[6].value).output()
        output[10] = XNOR(self.pins[8].value, self.pins[9].value).output()
        output[11] = XNOR(self.pins[12].value, self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4078(Base_14pin):

    """
    8 input NOR gate
    Pin_13 = NOR(Pin_2, Pin_3, Pin_4, Pin_5, Pin_9, Pin_10, Pin_11, Pin_12)
    """

    def __init__(self):
        self.pins = [None, None, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'NC'},
                    2: {'desc': 'Input 1 of NOR gate'},
                    3: {'desc': 'Input 2 of NOR gate'},
                    4: {'desc': 'Input 3 of NOR gate'},
                    5: {'desc': 'Input 4 of NOR gate'},
                    6: {'desc': 'NC'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'NC'},
                    9: {'desc': 'Input 5 of NOR gate'},
                    10: {'desc': 'Input 6 of NOR gate'},
                    11: {'desc': 'Input 7 of NOR gate'},
                    12: {'desc': 'Input 8 of NOR gate'},
                    13: {'desc': 'Output of NOR gate'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[13] = NOR(self.pins[2].value, self.pins[3].value,
                         self.pins[4].value, self.pins[5].value,
                         self.pins[9].value, self.pins[10].value,
                         self.pins[11].value, self.pins[12].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4081(Base_14pin):

    """
    Quad 2 input AND gate
    Pin_3 = AND(Pin_1, Pin_2)
    Pin_4 = AND(Pin_5, Pin_6)
    Pin_10 = AND(Pin_8, Pin_9)
    Pin_11 = AND(Pin_12, Pin_13)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'A1: Input 1 of AND gate 1'},
                    2: {'desc': 'B1: Input 2 of AND gate 1'},
                    3: {'desc': 'Q1: Output of AND gate 1'},
                    4: {'desc': 'Q2: Output of AND gate 2'},
                    5: {'desc': 'B2: Input 2 of AND gate 2'},
                    6: {'desc': 'A2: Input 1 of AND gate 2'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'A3: Input 1 of AND gate 3'},
                    9: {'desc': 'B3: Input 2 of AND gate 3'},
                    10: {'desc': 'Q3:Output of AND gate 3'},
                    11: {'desc': 'Q4:Output of AND gate 4'},
                    12: {'desc': 'B4: Input 2 of AND gate 4'},
                    13: {'desc': 'A4: Input 1 of AND gate 4'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[3] = AND(self.pins[1].value, self.pins[2].value).output()
        output[4] = AND(self.pins[5].value, self.pins[6].value).output()
        output[10] = AND(self.pins[8].value, self.pins[9].value).output()
        output[11] = AND(self.pins[12].value, self.pins[13].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4082(Base_14pin):

    """
    Dual 4 input AND gate
    Pin_1 = AND(Pin_2, Pin_3, Pin_4, Pin_5)
    Pin_13 = AND(Pin_9, Pin_10, Pin_11, Pin_12)
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'Q1: Output of AND gate 1'},
                    2: {'desc': 'A1: Input 1 of AND gate 1'},
                    3: {'desc': 'B1: Input 2 of AND gate 1'},
                    4: {'desc': 'C1: Input 3 of AND gate 1'},
                    5: {'desc': 'D1: Input 4 of AND gate 1'},
                    6: {'desc': 'NC'},
                    7: {'desc': 'GND'},
                    8: {'desc': 'NC'},
                    9: {'desc': 'D2: Input 4 of AND gate 2'},
                    10: {'desc': 'C2: Input 3 of AND gate 2'},
                    11: {'desc': 'B2: Input 2 of AND gate 2'},
                    12: {'desc': 'A2: Input 1 of AND gate 2'},
                    13: {'desc': 'Q2: Output of AND gate 2'},
                    14: {'desc': 'VCC'}
                    })

    def run(self):
        output = {}
        output[1] = AND(self.pins[2].value, self.pins[3].value,
                        self.pins[4].value, self.pins[5].value).output()
        output[13] = AND(self.pins[9].value, self.pins[10].value,
                         self.pins[11].value, self.pins[12].value).output()
        if self.pins[7].value == 0 and self.pins[14].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:

            print ("Ground and VCC pins have not been configured correctly.")

#################################
# IC's with 16 pins
#################################


class IC_4008(Base_16pin):

    """
    4 Bit Binary Full Adder
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, None, None, None,
                     None, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'A3'},
                    2: {'desc': 'B2'},
                    3: {'desc': 'A2'},
                    4: {'desc': 'B1'},
                    5: {'desc': 'A1'},
                    6: {'desc': 'B0'},
                    7: {'desc': 'A0'},
                    8: {'desc': 'VSS'},
                    9: {'desc': 'C0'},
                    10: {'desc': 'S0'},
                    11: {'desc': 'S1'},
                    12: {'desc': 'S2'},
                    13: {'desc': 'S3'},
                    14: {'desc': 'C4'},
                    15: {'desc': 'B3'},
                    16: {'desc': 'VDD'},
                    })

    def run(self):
        output = {}
        output[10] = ((self.pins[2]()) ^ (self.pins[3]()) ^ (self.pins[9]()))()
        output[11] = (
            (self.pins[5]()) ^ (
                self.pins[4]()) ^ (
                (self.pins[7]() & self.pins[6]()) | (
                    (self.pins[7]() | self.pins[6]()) & (
                        self.pins[9]()))))()
        output[12] = (
            (self.pins[3]()) ^ (
                self.pins[2]()) ^ (
                (self.pins[5]() & self.pins[4]()) | (
                    (self.pins[5]() | self.pins[4]()) & (
                        self.pins[7]() & self.pins[6]())) | (
                            (self.pins[5]() | self.pins[4]()) & (
                                self.pins[7]() | self.pins[6]()) & (
                                    self.pins[9]()))))()
        output[13] = (
            (self.pins[1]()) ^ (
                self.pins[15]()) ^ (
                (self.pins[3]() & self.pins[2]()) | (
                    (self.pins[3]() | self.pins[2]()) & (
                        self.pins[5]() & self.pins[4]())) | (
                            (self.pins[3]() | self.pins[2]()) & (
                                self.pins[5]() | self.pins[4]()) & (
                                    self.pins[7]() & self.pins[6]())) | (
                                        (self.pins[3]() | self.pins[2]()) & (
                                            self.pins[5]() | self.pins[4]()) & (
                                                self.pins[7]() | self.pins[6]()) & (
                                                    self.pins[9]()))))()
        output[14] = (
            (self.pins[1]() & self.pins[15]()) | (
                (self.pins[1]() | self.pins[15]()) & (
                    self.pins[3]() & self.pins[2]())) | (
                (self.pins[1]() | self.pins[15]()) & (
                    self.pins[3]() | self.pins[2]()) & (
                    self.pins[5]() & self.pins[4]())) | (
                (self.pins[1]() | self.pins[15]()) & (
                    self.pins[3]() | self.pins[2]()) & (
                    self.pins[5]() | self.pins[4]()) & (
                    self.pins[7]() & self.pins[6]())) | (
                (self.pins[1]() | self.pins[15]()) & (
                    self.pins[3]() | self.pins[2]()) & (
                    self.pins[5]() | self.pins[4]()) & (
                    self.pins[7]() | self.pins[6]()) & (
                    self.pins[9]())))()

        if self.pins[8].value == 0 and self.pins[16].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4009(Base_16pin):

    """
    Hex Inverter with Level Shifted output
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'VCC'},
                    2: {'desc': 'Y1'},
                    3: {'desc': 'A1'},
                    4: {'desc': 'Y2'},
                    5: {'desc': 'A2'},
                    6: {'desc': 'Y3'},
                    7: {'desc': 'A3'},
                    8: {'desc': 'VSS'},
                    9: {'desc': 'A4'},
                    10: {'desc': 'Y4'},
                    11: {'desc': 'A5'},
                    12: {'desc': 'Y5'},
                    13: {'desc': ''},
                    14: {'desc': 'A6'},
                    15: {'desc': 'Y6'},
                    16: {'desc': 'VDD'},
                    })

    def run(self):
        output = {}
        output[2] = NOT(self.pins[3].value).output()
        output[4] = NOT(self.pins[5].value).output()
        output[6] = NOT(self.pins[7].value).output()
        output[10] = NOT(self.pins[9].value).output()
        output[12] = NOT(self.pins[11].value).output()
        output[15] = NOT(self.pins[14].value).output()

        if self.pins[8].value == 0 and self.pins[16].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4010(Base_16pin):

    """
    Hex Buffer with Level Shifted output
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = True
        self.setIC({1: {'desc': 'VCC'},
                    2: {'desc': 'Y1'},
                    3: {'desc': 'A1'},
                    4: {'desc': 'Y2'},
                    5: {'desc': 'A2'},
                    6: {'desc': 'Y3'},
                    7: {'desc': 'A3'},
                    8: {'desc': 'VSS'},
                    9: {'desc': 'A4'},
                    10: {'desc': 'Y4'},
                    11: {'desc': 'A5'},
                    12: {'desc': 'Y5'},
                    13: {'desc': ''},
                    14: {'desc': 'A6'},
                    15: {'desc': 'Y6'},
                    16: {'desc': 'VDD'},
                    })

    def run(self):
        output = {}
        output[2] = self.pins[3].value
        output[4] = self.pins[5].value
        output[6] = self.pins[7].value
        output[10] = self.pins[9].value
        output[12] = self.pins[11].value
        output[15] = self.pins[14].value

        if self.pins[8].value == 0 and self.pins[16].value == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4015(Base_16pin):

    """
    Dual 4 Stage static shift Register
    """

    def __init__(self):
        self.pins = [None, 0, None, None, None, None, 0, 0, 0, 0, None, None,
                     None, None, 0, 0, 0]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = False
        self.setIC({1: {'desc': 'CLKB'},
                    2: {'desc': 'Q4'},
                    3: {'desc': 'Q3'},
                    4: {'desc': 'Q2'},
                    5: {'desc': 'Q1'},
                    6: {'desc': 'RST1'},
                    7: {'desc': 'DA'},
                    8: {'desc': 'VSS'},
                    9: {'desc': 'CLKA'},
                    10: {'desc': 'Q4'},
                    11: {'desc': 'Q3'},
                    12: {'desc': 'Q2'},
                    13: {'desc': 'Q1'},
                    14: {'desc': 'RSTB'},
                    15: {'desc': 'DB'},
                    16: {'desc': 'VDD'}

                    })

    def run(self):
        output = {}
        if not (isinstance(self.pins[1], Clock) and
                isinstance(self.pins[9], Clock)):
            raise Exception("Error: Invalid Clock Input")
        sr1 = ShiftRegister([self.pins[7],
                             self.pins[4],
                             self.pins[3],
                             self.pins[2]],
                            self.pins[1],
                            NOT(self.pins[6]).output())
        sr2 = ShiftRegister([self.pins[15],
                             self.pins[12],
                             self.pins[11],
                             self.pins[10]],
                            self.pins[9],
                            NOT(self.pins[14]).output())
        sr1 = sr1.output()
        output[5] = sr1[0]
        output[4] = sr1[1]
        output[3] = sr1[2]
        output[2] = sr1[3]
        sr2 = sr2.output()
        output[13] = sr2[0]
        output[12] = sr2[1]
        output[11] = sr2[2]
        output[10] = sr2[3]

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4017(Base_16pin):

    """
    CMOS Counters
    """

    def __init__(self):
        self.pins = [None, None, None, None, None, None, None, None, 0, None,
                     None, None, None, 0, 0, 0, 1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = False
        self.setIC({1: {'desc': '5'},
                    2: {'desc': '1'},
                    3: {'desc': '0'},
                    4: {'desc': '2'},
                    5: {'desc': '6'},
                    6: {'desc': '7'},
                    7: {'desc': '3'},
                    8: {'desc': 'VSS'},
                    9: {'desc': '8'},
                    10: {'desc': '4'},
                    11: {'desc': '9'},
                    12: {'desc': 'carry'},
                    13: {'desc': 'CLKI'},
                    14: {'desc': 'CLK'},
                    15: {'desc': 'RST'},
                    16: {'desc': 'VDD'}

                    })
        self.step = 0

    def run(self):
        output = {}
        if not (isinstance(self.pins[13], Clock) and
                isinstance(self.pins[14], Clock)):
            raise Exception("Error: Invalid Clock Input")
        counter = DecadeCounter(self.pins[14].A,
                                clear=Connector(NOT(self.pins[15]).output()))
        for i in range(self.step):
            counter.trigger()
        self.step += 1
        out = list(map(str, counter.state()))
        out = ''.join(out)
        out = int(out, 2)
        if out <= 4:
            output[12] = 1
        else:
            output[12] = 0
        for i in range(1, 12):
            output[i] = 0

        if out == 5:
            output[1] = 1
        elif out == 1:
            output[2] = 1
        elif out == 0:
            output[3] = 1
        elif out == 2:
            output[4] = 1
        elif out == 6:
            output[5] = 1
        elif out == 7:
            output[6] = 1
        elif out == 3:
            output[7] = 1
        elif out == 8:
            output[9] = 1
        elif out == 4:
            output[10] = 1
        elif out == 9:
            output[11] = 1

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4019(Base_16pin):

    """
    8-to-4 line non-inverting data selector/multiplexer with OR function
    """

    def __init__(self):
        self.pins = [None, None, None, None, None, None, None, None, 0, None,
                     None, None, None, 0, 0, 0, 1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = False
        self.setIC({1: {'desc': '4A1'},
                    2: {'desc': '3A0'},
                    3: {'desc': '3A1'},
                    4: {'desc': '2A0'},
                    5: {'desc': '2A1'},
                    6: {'desc': '1A0'},
                    7: {'desc': '1A1'},
                    8: {'desc': 'GND'},
                    9: {'desc': 'S0'},
                    10: {'desc': 'Y1'},
                    11: {'desc': 'Y2'},
                    12: {'desc': 'Y3'},
                    13: {'desc': 'Y4'},
                    14: {'desc': 'S1'},
                    15: {'desc': '4A0'},
                    16: {'desc': 'VCC'}

                    })

    def run(self):
        output = {}
        output[10] = OR(AND(self.pins[9], self.pins[6]).output(),
                        AND(self.pins[14], self.pins[7]).output()).output()

        output[11] = OR(AND(self.pins[9], self.pins[4]).output(),
                        AND(self.pins[14], self.pins[5]).output()).output()
        output[12] = OR(AND(self.pins[9], self.pins[2]).output(),
                        AND(self.pins[14], self.pins[3]).output()).output()

        output[13] = OR(AND(self.pins[9], self.pins[1]).output(),
                        AND(self.pins[14], self.pins[15]).output()).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4020(Base_16pin):

    """
    CMOS 14 BIT asynchornous binary counter with reset
    """

    def __init__(self):
        self.pins = [None, None, None, None, None, None, None, None, 0, None,
                     0, 0, None, None, None, None, 1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = False
        self.setIC({1: {'desc': 'Q11'},
                    2: {'desc': 'Q12'},
                    3: {'desc': 'Q13'},
                    4: {'desc': 'Q5'},
                    5: {'desc': 'Q4'},
                    6: {'desc': 'Q6'},
                    7: {'desc': 'Q3'},
                    8: {'desc': 'VSS'},
                    9: {'desc': 'Q0'},
                    10: {'desc': 'CLK'},
                    11: {'desc': 'RST'},
                    12: {'desc': 'Q8'},
                    13: {'desc': 'Q7'},
                    14: {'desc': 'Q9'},
                    15: {'desc': 'Q10'},
                    16: {'desc': 'VCC'}

                    })
        self.step = 0

    def run(self):
        output = {}
        if not (isinstance(self.pins[10], Clock)):
            raise Exception("Error: Invalid Clock Input")
        counter = Stage14Counter(self.pins[10].A,
                                 clear=Connector(NOT(self.pins[11]).output()))
        for i in range(self.step):
            counter.trigger()
        self.step += 1
        out = list(map(str, counter.state()))
        out = ''.join(out)
        out = int(out, 2)
        for i in range(1, 16):
            if i != 10 and i != 11:
                output[i] = 0

        if out == 11:
            output[1] = 1
        elif out == 12:
            output[2] = 1
        elif out == 13:
            output[3] = 1
        elif out == 5:
            output[4] = 1
        elif out == 4:
            output[5] = 1
        elif out == 6:
            output[6] = 1
        elif out == 3:
            output[7] = 1
        elif out == 0:
            output[9] = 1
        elif out == 8:
            output[12] = 1
        elif out == 7:
            output[13] = 1
        elif out == 9:
            output[14] = 1
        elif out == 10:
            output[15] = 1

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4022(Base_16pin):

    """
    CMOS Octal Counter
    """

    def __init__(self):
        self.pins = [None, None, None, None, None, None, None, None, 0, None,
                     None, None, None, 0, 0, 0, 1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = False
        self.setIC({1: {'desc': '1'},
                    2: {'desc': '0'},
                    3: {'desc': '2'},
                    4: {'desc': '5'},
                    5: {'desc': '6'},
                    6: {'desc': ''},
                    7: {'desc': '3'},
                    8: {'desc': 'VSS'},
                    9: {'desc': ''},
                    10: {'desc': '7'},
                    11: {'desc': '4'},
                    12: {'desc': 'carry'},
                    13: {'desc': 'CLKI'},
                    14: {'desc': 'CLK'},
                    15: {'desc': 'RST'},
                    16: {'desc': 'VDD'}

                    })
        self.step = 0

    def run(self):
        output = {}
        if not (isinstance(self.pins[13], Clock) and
                isinstance(self.pins[14], Clock)):
            raise Exception("Error: Invalid Clock Input")
        counter = OctalCounter(self.pins[14].A,
                               clear=Connector(NOT(self.pins[15]).output()))
        for i in range(self.step):
            counter.trigger()
        self.step += 1
        out = list(map(str, counter.state()))
        out = ''.join(out)
        out = int(out, 2)
        if out <= 3:
            output[12] = 1
        else:
            output[12] = 0
        for i in range(1, 12):
            output[i] = 0

        if out == 5:
            output[4] = 1
        elif out == 1:
            output[1] = 1
        elif out == 0:
            output[2] = 1
        elif out == 2:
            output[3] = 1
        elif out == 6:
            output[5] = 1
        elif out == 7:
            output[10] = 1
        elif out == 3:
            output[7] = 1
        elif out == 4:
            output[11] = 1

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4027(Base_16pin):

    """
    Dual JK flip flops with set and reset
    """

    def __init__(self):
        self.pins = [None, None, None, 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 0, 0, None, None, 1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = False
        self.setIC({1: {'desc': 'Q1'},
                    2: {'desc': '~Q1'},
                    3: {'desc': 'CLK1'},
                    4: {'desc': 'RST1'},
                    5: {'desc': 'K1'},
                    6: {'desc': 'J1'},
                    7: {'desc': 'SET1'},
                    8: {'desc': 'GND'},
                    9: {'desc': 'SET2'},
                    10: {'desc': 'J2'},
                    11: {'desc': 'K2'},
                    12: {'desc': 'RST2'},
                    13: {'desc': 'CLK2'},
                    14: {'desc': '~Q2'},
                    15: {'desc': 'Q2'},
                    16: {'desc': 'VCC'}

                    })

    def run(self):
        output = {}
        if not (isinstance(self.pins[13], Clock) and
                isinstance(self.pins[3], Clock)):
            raise Exception("Error: Invalid Clock Input")
        ff1 = JKFlipFlop(self.pins[6], self.pins[5], Connector(1),
                         self.pins[3].A, self.pins[4], self.pins[7])

        ff2 = JKFlipFlop(self.pins[10], self.pins[11], Connector(1),
                         self.pins[13].A, self.pins[12], self.pins[9])
        while True:
            if self.pins[3].A.state == 1:
                ff1.trigger()
                break

        while True:
            if self.pins[3].A.state == 0:
                ff1.trigger()
                break
        output[1], output[2] = ff1.state()
        while True:
            if self.pins[13].A.state == 1:
                ff2.trigger()
                break

        while True:
            if self.pins[13].A.state == 1:
                ff2.trigger()
                break
        output[15], output[14] = ff2.state()

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4028(Base_16pin):

    """
    1-of-10 no-inverting decoder/demultiplexer
    """

    def __init__(self):
        self.pins = [None, None, None, None, None, None, None, None, 0, None,
                     0, 0, 0, 0, None, None, 1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = False
        self.setIC({1: {'desc': 'Y4'},
                    2: {'desc': 'Y2'},
                    3: {'desc': 'Y0'},
                    4: {'desc': 'Y7'},
                    5: {'desc': 'Y9'},
                    6: {'desc': 'Y5'},
                    7: {'desc': 'Y6'},
                    8: {'desc': 'GND'},
                    9: {'desc': 'Y8'},
                    10: {'desc': 'S0'},
                    11: {'desc': 'S3'},
                    12: {'desc': 'S2'},
                    13: {'desc': 'S1'},
                    14: {'desc': 'Y1'},
                    15: {'desc': 'Y3'},
                    16: {'desc': 'VCC'}

                    })

    def run(self):
        output = {}
        d = DEMUX(1)
        d.selectLines(self.pins[10], self.pins[13], self.pins[12],
                      self.pins[11])
        d = d.output()[:10]
        output[1] = d[4]
        output[2] = d[2]
        output[3] = d[0]
        output[4] = d[7]
        output[5] = d[9]
        output[6] = d[5]
        output[7] = d[6]
        output[9] = d[8]
        output[14] = d[1]
        output[15] = d[3]

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")


class IC_4029(Base_16pin):

    """
    4-bit synchronous binary/decade up/down counter
    """

    def __init__(self):
        self.pins = [0, 0, None, 0, 0, 0, None, 0, 0, None,
                     0, None, 0, 0, None, 0, 1]
        self.pins = pinlist_quick(self.pins)
        self.uses_pincls = False
        """
      self.setIC({1: {'desc': 'Y4'},
                    2: {'desc': 'Y2'},
                    3: {'desc': 'Y0'},
                    4: {'desc': 'Y7'},
                    5: {'desc': 'Y9'},
                    6: {'desc': 'Y5'},
                    7: {'desc': 'Y6'},
                    8: {'desc': 'GND'},
                    9: {'desc': 'Y8'},
                    10: {'desc': 'S0'},
                    11: {'desc': 'S3'},
                    12: {'desc': 'S2'},
                    13: {'desc': 'S1'},
                    14: {'desc': 'Y1'},
                    15: {'desc': 'Y3'},
                    16: {'desc': 'VCC'}

                    })
        """
        self.steps = 0
        self.state = [0, 0, 0, 0]

    def run(self):
        output = {}

        if not isinstance(self.pins[15], Clock):
            raise Exception("Error: Invalid Clock Input")
        c = BinaryCounter(4, self.pins[15].A)
        while self.arraytoint(self.state) != self.arraytoint(c.trigger()):
            pass

        if self.pins[1] == 1:
            preset = self.arraytoint(self.pins[4], self.pins[12],
                                     self.pins[13], self.pins[3])
            while preset != self.arraytoint(c.trigger()):
                pass

        if self.pins[10] == 1:
            if self.pins[9] == 1:
                output[6], output[11], output[14], output[2] = c.trigger()
                self.state = c.state()
                if self.arraytoint(self.state) == 15:
                    output[7] = 1
            elif self.pins[9] == 0:
                arr = c.trigger()
                output[6], output[11], output[14], output[2] = arr
                self.state = arr
                if self.arraytoint(arr) == 10:
                    self.state = [0, 0, 0, 0]
                    output[6], output[11], output[14], output[2] = [0, 0, 0, 0]

        elif self.pins[10] == 0:
            if self.pins[9] == 0:
                d = NBitDownCounter(4, self.pins[15].A)
                while self.arraytoint(self.state) != self.arraytoint(d.trigger()):
                    pass
                arr = d.trigger()
                output[6], output[11], output[14], output[2] = arr
                self.state = arr
                if self.arraytoint(arr) > 10:
                    self.state = [1, 0, 0, 1]
                    output[6], output[11], output[14], output[2] = [1, 0, 0, 1]
            elif self.pins[9] == 1:
                d = NBitDownCounter(4, self.pins[15].A)
                while self.arraytoint(self.state) != self.arraytoint(d.trigger()):
                    pass
                arr = d.trigger()
                output[6], output[11], output[14], output[2] = arr
                self.state = arr
                if self.arraytoint(arr) == 0:
                    output[7] = 0

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print ("Ground and VCC pins have not been configured correctly.")

    def arraytoint(self, inputs):
        inputs = list(map(str, inputs))
        inputs = ''.join(inputs)
        inputs = int(inputs, 2)
        return inputs

########NEW FILE########
__FILENAME__ = series_7400
"""
This module has all the classes of ICs belonging to 7400 series.

Please note that the length of list self.pins is 1 more than the number of actual pins. This is so because pin0
is not used as a general term referring to the first pin of the IC. Zeroth index of the self.pins is not being used.
"""
from __future__ import print_function
from BinPy.Gates import *
from BinPy.Sequential import *
from BinPy.ic.base import *
from BinPy.tools import *
from BinPy.Combinational.combinational import *


#################################
# IC's with 5 pins
#################################


class IC_741G00(Base_5pin):

    """
    This is a single 2 input NAND gate IC
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, None, 0]

    def run(self):
        output = {}
        output[4] = NAND(self.pins[1], self.pins[2]).output()
        if self.pins[3] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_741G02(Base_5pin):

    """
    This is a single 2 input NOR gate IC
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, None, 0]

    def run(self):
        output = {}
        output[4] = NOR(self.pins[1], self.pins[2]).output()
        if self.pins[3] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_741G03(Base_5pin):

    """
    This is a single 2 input NAND gate IC
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, None, 0]

    def run(self):
        output = {}
        output[4] = NAND(self.pins[1], self.pins[2]).output()
        if self.pins[3] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_741G04(Base_5pin):

    """
    This is a single inverter IC
    """

    def __init__(self):
        self.pins = [None, None, 0, 0, None, 0]

    def run(self):
        output = {}
        output[4] = NOT(self.pins[2]).output()
        if self.pins[3] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_741G05(Base_5pin):

    """
    This is a single input NOT gate IC
    """

    def __init__(self):
        self.pins = [None, None, 0, 0, None, 0]

    def run(self):
        output = {}
        output[4] = NOT(self.pins[2]).output()
        if self.pins[3] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_741G08(Base_5pin):

    """
    This is a single 2 input AND gate IC
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, None, 0]

    def run(self):
        output = {}
        output[4] = AND(self.pins[1], self.pins[2]).output()
        if self.pins[3] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


#################################
# IC's with 14 pins
#################################


class IC_7400(Base_14pin):

    """
    This is a QUAD 2 INPUT NAND gate IC
    Pin Configuration:

    Pin Number  Description
        1   A Input Gate 1
        2   B Input Gate 1
        3   Y Output Gate 1
        4   A Input Gate 2
        5   B Input Gate 2
        6   Y Output Gate 2
        7   Ground
        8   Y Output Gate 3
        9   B Input Gate 3
        10  A Input Gate 3
        11  Y Output Gate 4
        12  B Input Gate 4
        13  A Input Gate 4
        14  Positive Supply

    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7400:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7400()
        >>> pin_config = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Methods:
        pins = [None,0,0,None,0,0,None,0,None,0,0,None,0,0,0]


    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0]

    def run(self):
        output = {}
        output[3] = NAND(self.pins[1], self.pins[2]).output()
        output[6] = NAND(self.pins[4], self.pins[5]).output()
        output[8] = NAND(self.pins[9], self.pins[10]).output()
        output[11] = NAND(self.pins[12], self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7401(Base_14pin):

    """
    This is a Quad 2-input open-collector NAND gate IC
    """

    def __init__(self):
        self.pins = [
            None,
            None,
            0,
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            0,
            None,
            0]

    def run(self):
        output = {}
        output[1] = NAND(self.pins[2], self.pins[3]).output()
        output[4] = NAND(self.pins[5], self.pins[6]).output()
        output[10] = NAND(self.pins[8], self.pins[9]).output()
        output[13] = NAND(self.pins[11], self.pins[12]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7402(Base_14pin):

    """
    This is a Quad 2-input NOR gate IC

    Pin Configuration:

    Pin Number  Description
        1   Y Output Gate 1
        2   A Input Gate 1
        3   B Input Gate 1
        4   Y Output Gate 2
        5   A Input Gate 2
        6   B Input Gate 2
        7   Ground
        8   A Input Gate 3
        9   B Input Gate 3
        10  Y Output Gate 3
        11  A Input Gate 4
        12  B Input Gate 4
        13  Y Output Gate 4
        14  Positive Supply

    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7402:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7402()
        >>> pin_config = {2: 0, 3: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 1, 11: 1, 12: 1, 14: 1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Default pins:
        pins = [None,None,0,0,None,0,0,0,0,0,None,0,0,None,0]


    """

    def __init__(self):
        self.pins = [
            None,
            None,
            0,
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            0,
            None,
            0]

    def run(self):
        output = {}
        output[1] = NOR(self.pins[2], self.pins[3]).output()
        output[4] = NOR(self.pins[5], self.pins[6]).output()
        output[10] = NOR(self.pins[8], self.pins[9]).output()
        output[13] = NOR(self.pins[11], self.pins[12]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7403(Base_14pin):

    """
    This is a Quad 2-input open-collector NAND gate IC

    Pin Number  Description
        1   A Input Gate 1
        2   B Input Gate 1
        3   Y Output Gate 1
        4   A Input Gate 2
        5   B Input Gate 2
        6   Y Output Gate 2
        7   Ground
        8   Y Output Gate 3
        9   B Input Gate 3
        10  A Input Gate 3
        11  Y Output Gate 4
        12  B Input Gate 4
        13  A Input Gate 4
        14  Positive Supply


    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7403:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7403()
        >>> pin_config = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Default pins:
        pins = [None,0,0,None,0,0,None,0,None,0,0,None,0,0,0]


    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0]

    def run(self):
        output = {}
        output[3] = NAND(self.pins[1], self.pins[2]).output()
        output[6] = NAND(self.pins[4], self.pins[5]).output()
        output[8] = NAND(self.pins[9], self.pins[10]).output()
        output[11] = NAND(self.pins[12], self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7404(Base_14pin):

    """
    This is a hex inverter IC

    Pin Number  Description
        1   A Input Gate 1
        2   Y Output Gate 1
        3   A Input Gate 2
        4   Y Output Gate 2
        5   A Input Gate 3
        6   Y Output Gate 3
        7   Ground
        8   Y Output Gate 4
        9   A Input Gate 4
        10  Y Output Gate 5
        11  A Input Gate 5
        12  Y Output Gate 6
        13  A Input Gate 6
        14  Positive Supply

    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7404:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7404()
        >>> pin_config = {1: 1, 3: 0, 5: 0, 7: 0, 9: 0, 11: 0, 13: 1, 14: 1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Default pins:
        pins = [None,0,0,None,0,0,None,0,None,0,0,None,0,0,0]

    """

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            0]

    def run(self):
        output = {}
        output[2] = NOT(self.pins[1]).output()
        output[4] = NOT(self.pins[3]).output()
        output[6] = NOT(self.pins[5]).output()
        output[8] = NOT(self.pins[9]).output()
        output[10] = NOT(self.pins[11]).output()
        output[12] = NOT(self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7405(Base_14pin):

    """
    This is hex open-collector inverter IC
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            0]

    def run(self):
        output = {}
        output[2] = NOT(self.pins[1]).output()
        output[4] = NOT(self.pins[3]).output()
        output[6] = NOT(self.pins[5]).output()
        output[8] = NOT(self.pins[9]).output()
        output[10] = NOT(self.pins[11]).output()
        output[12] = NOT(self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7408(Base_14pin):

    """
    This is a Quad 2 input AND gate IC

    Pin Number  Description
        1   A Input Gate 1
        2   B Input Gate 1
        3   Y Output Gate 1
        4   A Input Gate 2
        5   B Input Gate 2
        6   Y Output Gate 2
        7   Ground
        8   Y Output Gate 3
        9   B Input Gate 3
        10  A Input Gate 3
        11  Y Output Gate 4
        12  B Input Gate 4
        13  A Input Gate 4
        14  Positive Supply

    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7408:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7408()
        >>> pin_config = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Default pins:
        pins = [None,0,0,None,0,0,None,0,None,0,0,None,0,0,0]


    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0]

    def run(self):
        output = {}
        output[3] = AND(self.pins[1], self.pins[2]).output()
        output[6] = AND(self.pins[4], self.pins[5]).output()
        output[8] = AND(self.pins[9], self.pins[10]).output()
        output[11] = AND(self.pins[12], self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7410(Base_14pin):

    """
    This is a Triple 3 input NAND gate IC

    Pin Number  Description
        1   A Input Gate 1
        2   B Input Gate 1
        3   A Input Gate 2
        4   B Input Gate 2
        5   C Input gate 2
        6   Y Output Gate 2
        7   Ground
        8   Y Output Gate 3
        9   A Input Case 3
        10  B Input Case 3
        11  C Input Case 3
        12  Y Output Gate 1
        13  C Input Gate 1
        14  Positive Supply


    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7410:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7410()
        >>> pin_config = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Default pins:
        pins = [None,0,0,0,0,0,None,0,None,0,0,0,None,0,0]

    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, None, 0, 0]

    def run(self):
        output = {}
        output[12] = NAND(self.pins[1], self.pins[2], self.pins[13]).output()
        output[6] = NAND(self.pins[3], self.pins[4], self.pins[5]).output()
        output[8] = NAND(self.pins[9], self.pins[10], self.pins[11]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7411(Base_14pin):

    """
    This is a Triple 3 input AND gate IC

    Pin Number  Description
        1   A Input Gate 1
        2   B Input Gate 1
        3   A Input Gate 2
        4   B Input Gate 2
        5   C Input gate 2
        6   Y Output Gate 2
        7   Ground
        8   Y Output Gate 3
        9   A Input Case 3
        10  B Input Case 3
        11  C Input Case 3
        12  Y Output Gate 1
        13  C Input Gate 1
        14  Positive Supply


    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7411:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7411()
        >>> pin_config = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Default pins:
        pins = [None,0,0,0,0,0,None,0,None,0,0,0,None,0,0]


    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, None, 0, 0]

    def run(self):
        output = {}
        output[12] = AND(self.pins[1], self.pins[2], self.pins[13]).output()
        output[6] = AND(self.pins[3], self.pins[4], self.pins[5]).output()
        output[8] = AND(self.pins[9], self.pins[10], self.pins[11]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7412(Base_14pin):

    """
    This is a Triple 3 input NAND gate IC with open collector outputs

    Pin Number  Description
        1   A Input Gate 1
        2   B Input Gate 1
        3   A Input Gate 2
        4   B Input Gate 2
        5   C Input gate 2
        6   Y Output Gate 2
        7   Ground
        8   Y Output Gate 3
        9   A Input Case 3
        10  B Input Case 3
        11  C Input Case 3
        12  Y Output Gate 1
        13  C Input Gate 1
        14  Positive Supply


    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7412:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7412()
        >>> pin_config = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 13: 0, 14: 1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Default pins:
        pins = [None,0,0,0,0,0,None,0,None,0,0,0,None,0,0]

    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, None, 0, 0]

    def run(self):
        output = {}
        output[12] = NAND(self.pins[1], self.pins[2], self.pins[13]).output()
        output[6] = NAND(self.pins[3], self.pins[4], self.pins[5]).output()
        output[8] = NAND(self.pins[9], self.pins[10], self.pins[11]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7413(Base_14pin):

    """
    This is a dual 4 input NAND gate IC

    Pin Number  Description
        1   A Input Gate 1
        2   B Input Gate 1
        3   Not Connected
        4   C Input Gate 1
        5   D Input Gate 1
        6   Y Output Gate 1
        7   Ground
        8   Y Output Gate 2
        9   A Input Gate 2
        10  B Input Gate 2
        11  Not Connected
        12  C Input Gate 2
        13  D Input Gate 2
        14  Positive Supply


    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7413:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7413()
        >>> pin_config = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Default pins:
        pins = [None,0,0,0,0,0,None,0,None,0,0,0,0,0,0]

    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[6] = NAND(
            self.pins[1],
            self.pins[2],
            self.pins[4],
            self.pins[5]).output()
        output[8] = NAND(
            self.pins[9],
            self.pins[10],
            self.pins[12],
            self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7415(Base_14pin):

    """
    This is a Triple 3 input AND gate IC with open collector outputs

    Pin Number  Description
        1   A Input Gate 1
        2   B Input Gate 1
        3   A Input Gate 2
        4   B Input Gate 2
        5   C Input Gate 2
        6   Y Output Gate 2
        7   Ground
        8   Y Output Gate 3
        9   A Input Gate 3
        10  B Input Gate 3
        11  C Input Gate 3
        12  Y Output Gate 1
        13  C Input Gate 1
        14  Positive Supply


    This class needs 14 parameters. Each parameter being the pin value. The input has to be defined as a dictionary
    with pin number as the key and its value being either 1 or 0

    To initialise the ic 7415:
        1. set pin 7:0
        2. set pin 14:1

    How to use:

        >>> ic = IC_7415()
        >>> pin_config = {1:1, 2:0, 3:0, 4:0, 5:0, 7:0, 9:1, 10:1, 11:1, 13:0, 14:1}
        >>> ic.setIC(pin_cofig)
        >>> ic.drawIC()
        >>> ic.run()
        >>> ic.setIC(ic.run())
        >>> ic.drawIC()

    Default pins:
        pins = [None,0,0,0,0,0,None,0,None,0,0,0,None,0,0]

    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, None, 0, 0]

    def run(self):
        output = {}
        output[12] = AND(self.pins[1], self.pins[2], self.pins[13]).output()
        output[6] = AND(self.pins[3], self.pins[4], self.pins[5]).output()
        output[8] = AND(self.pins[9], self.pins[10], self.pins[11]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7416(Base_14pin):

    """
    This is a Hex open-collector high-voltage inverter
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            0]

    def run(self):
        output = {}
        output[2] = NOT(self.pins[1]).output()
        output[4] = NOT(self.pins[3]).output()
        output[6] = NOT(self.pins[5]).output()
        output[8] = NOT(self.pins[9]).output()
        output[10] = NOT(self.pins[11]).output()
        output[12] = NOT(self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7417(Base_14pin):

    """
    This is a Hex open-collector high-voltage buffer
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            0]

    def run(self):
        output = {}
        output[2] = self.pins[1]
        output[4] = self.pins[3]
        output[6] = self.pins[5]
        output[8] = self.pins[9]
        output[10] = self.pins[11]
        output[12] = self.pins[13]
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7418(Base_14pin):

    """
    This is a Dual 4-input NAND gates with schmitt-trigger inputs.
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[6] = NAND(
            self.pins[1],
            self.pins[2],
            self.pins[4],
            self.pins[5]).output()
        output[8] = NAND(
            self.pins[9],
            self.pins[10],
            self.pins[12],
            self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7419(Base_14pin):

    """
    This is a Hex inverters with schmitt-trigger line-receiver inputs.
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            None,
            0,
            0]

    def run(self):
        output = {}
        output[2] = NOT(self.pins[1]).output()
        output[4] = NOT(self.pins[3]).output()
        output[6] = NOT(self.pins[5]).output()
        output[8] = NOT(self.pins[9]).output()
        output[10] = NOT(self.pins[11]).output()
        output[12] = NOT(self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7420(Base_14pin):

    """
    This is a dual 4-input NAND gate
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[6] = NAND(
            self.pins[1],
            self.pins[2],
            self.pins[4],
            self.pins[5]).output()
        output[8] = NAND(
            self.pins[9],
            self.pins[10],
            self.pins[12],
            self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7421(Base_14pin):

    """
    This is a dual 4-input AND gate
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[6] = AND(
            self.pins[1],
            self.pins[2],
            self.pins[4],
            self.pins[5]).output()
        output[8] = AND(
            self.pins[9],
            self.pins[10],
            self.pins[12],
            self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7422(Base_14pin):

    """
    This is a dual 4-input NAND gate with open collector outputs
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[6] = NAND(
            self.pins[1],
            self.pins[2],
            self.pins[4],
            self.pins[5]).output()
        output[8] = NAND(
            self.pins[9],
            self.pins[10],
            self.pins[12],
            self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7424(Base_14pin):

    """
    This is a Quad 2-input NAND gates with schmitt-trigger line-receiver inputs
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0]

    def run(self):
        output = {}
        output[3] = NAND(self.pins[1], self.pins[2]).output()
        output[6] = NAND(self.pins[4], self.pins[5]).output()
        output[8] = NAND(self.pins[10], self.pins[9]).output()
        output[11] = NAND(self.pins[12], self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7425(Base_14pin):

    """
    This is a Dual 5-Input NOR Gate with Strobe
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[6] = NOR(
            self.pins[1],
            self.pins[2],
            self.pins[3],
            self.pins[4],
            self.pins[5]).output()
        output[8] = NOR(
            self.pins[9],
            self.pins[10],
            self.pins[11],
            self.pins[12],
            self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7426(Base_14pin):

    """
    This is a Quad 2-input open-collector high-voltage NAND gates.
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0]

    def run(self):
        output = {}
        output[3] = NAND(self.pins[1], self.pins[2]).output()
        output[6] = NAND(self.pins[4], self.pins[5]).output()
        output[8] = NAND(self.pins[9], self.pins[10]).output()
        output[11] = NAND(self.pins[12], self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7427(Base_14pin):

    """
    This is a Triple 3-Input NOR Gate
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, None, 0, 0]

    def run(self):
        output = {}
        output[6] = NOR(self.pins[3], self.pins[4], self.pins[5]).output()
        output[8] = NOR(self.pins[9], self.pins[10], self.pins[11]).output()
        output[12] = NOR(self.pins[1], self.pins[2], self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7428(Base_14pin):

    """
    This is a Quad 2-input NOR gates with buffered outputs.
    """

    def __init__(self):
        self.pins = [
            None,
            None,
            0,
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            0,
            None,
            0]

    def run(self):
        output = {}
        output[1] = NOR(self.pins[2], self.pins[3]).output()
        output[4] = NOR(self.pins[5], self.pins[6]).output()
        output[10] = NOR(self.pins[8], self.pins[9]).output()
        output[13] = NOR(self.pins[11], self.pins[12]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7430(Base_14pin):

    """
    This is a 8-Input NAND Gate
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[8] = NAND(
            self.pins[1],
            self.pins[2],
            self.pins[3],
            self.pins[4],
            self.pins[5],
            self.pins[6],
            self.pins[11],
            self.pins[12]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7432(Base_14pin):

    """
    This is a Quad 2-Input OR Gate
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0]

    def run(self):
        output = {}
        output[3] = OR(self.pins[1], self.pins[2]).output()
        output[6] = OR(self.pins[4], self.pins[5]).output()
        output[8] = OR(self.pins[9], self.pins[10]).output()
        output[11] = OR(self.pins[12], self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7433(Base_14pin):

    """
    This is a Quad 2-input open-collector NOR gate
    """

    def __init__(self):
        self.pins = [
            None,
            None,
            0,
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            0,
            None,
            0]

    def run(self):
        output = {}
        output[1] = NOR(self.pins[2], self.pins[3]).output()
        output[4] = NOR(self.pins[5], self.pins[6]).output()
        output[10] = NOR(self.pins[8], self.pins[9]).output()
        output[13] = NOR(self.pins[11], self.pins[12]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7437(Base_14pin):

    """
    This is a Quad 2-input NAND gates with buffered output
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0]

    def run(self):
        output = {}
        output[3] = NAND(self.pins[1], self.pins[2]).output()
        output[6] = NAND(self.pins[4], self.pins[5]).output()
        output[8] = NAND(self.pins[9], self.pins[10]).output()
        output[11] = NAND(self.pins[12], self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7438(Base_14pin):

    """
    This is a Quad 2-Input NAND Buffer with Open Collector Output
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0]

    def run(self):
        output = {}
        output[3] = NAND(self.pins[1], self.pins[2]).output()
        output[6] = NAND(self.pins[4], self.pins[5]).output()
        output[8] = NAND(self.pins[9], self.pins[10]).output()
        output[11] = NAND(self.pins[12], self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7440(Base_14pin):

    """
    This is a Dual 4-Input NAND Buffer
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[6] = NAND(
            self.pins[1],
            self.pins[2],
            self.pins[4],
            self.pins[5]).output()
        output[8] = NAND(
            self.pins[9],
            self.pins[10],
            self.pins[12],
            self.pins[13]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7451(Base_14pin):

    """
    This is a dual 2-wide 2-input AND-OR Invert gate
    """
    # Datasheet here, http://www.unitechelectronics.com/7451-7497data.htm

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[6] = NOR(AND(self.pins[2], self.pins[3]).output(),
                        AND(self.pins[4], self.pins[5]).output()).output()
        output[8] = NOR(AND(self.pins[1],
                            self.pins[13],
                            self.pins[12]).output(),
                        AND(self.pins[11],
                            self.pins[10],
                            self.pins[9]).output()).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7454(Base_14pin):

    """
    This is a 4-wide 2-input AND-OR Invert gate
    """
    # Datasheet here, http://www.unitechelectronics.com/7451-7497data.htm

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        temp = []
        temp.append(OR(AND(self.pins[1], self.pins[2]).output(), AND(
            self.pins[3], self.pins[4], self.pins[5]).output()).output())
        temp.append(OR(AND(self.pins[9],
                           self.pins[10],
                           self.pins[11]).output(),
                       AND(self.pins[12],
                           self.pins[13]).output()).output())
        output[6] = NOR(temp[0], temp[1]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7455(Base_14pin):

    """
    This is a 4-wide 2-input AND-OR Invert gate
    """
    # Datasheet here, http://www.unitechelectronics.com/7451-7497data.htm

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        temp = []
        temp.append(AND(self.pins[1], self.pins[2],
                        self.pins[3], self.pins[4]).output())
        temp.append(AND(self.pins[10], self.pins[11],
                        self.pins[12], self.pins[13]).output())
        output[8] = NOR(temp[0], temp[1]).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7458(Base_14pin):

    """
    This is a 2-input and 3-input AND-OR gate
    """
    # Datasheet here, http://www.unitechelectronics.com/7451-7497data.htm

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[6] = OR(AND(self.pins[2], self.pins[3]).output(),
                       AND(self.pins[4], self.pins[5]).output()).output()
        output[8] = OR(AND(self.pins[1],
                           self.pins[13],
                           self.pins[12]).output(),
                       AND(self.pins[11],
                           self.pins[10],
                           self.pins[9]).output()).output()
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7464(Base_14pin):

    """
    This is a 4-2-3-2 input AND-OR-invert gate
    """

    # Datasheet here, http://www.skot9000.com/ttl/datasheets/64.pdf

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}
        output[8] = NOR(
            AND(
                self.pins[2], self.pins[3]).output(), AND(
                self.pins[9], self.pins[10]).output(), AND(
                self.pins[1], self.pins[11], self.pins[13], self.pins[12]).output(), AND(
                self.pins[4], self.pins[5], self.pins[6]).output()).output()

        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7470(Base_14pin):

    "AND gated JK Positive Edge triggered Flip Flop with preset and clear"

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            0]

    def run(self):
        output = {}
        J = Connector(AND(self.pins[3], self.pins[4], self.pins[5]).output())
        K = Connector(AND(self.pins[9], self.pins[10], self.pins[11]).output())
        if not isinstance(self.pins[12], Clock):
            raise Exception("Error: Invalid Clock Input")
        ff = JKFlipFlop(J, K, Connector(1), self.pins[12].A,
                        self.pins[13], self.pins[2])
        while True:
            if self.pins[12].A.state == 0:
                ff.trigger()
                break
        while True:
            if self.pins[12].A.state == 1:
                ff.trigger()
                break
        output[8] = ff.state()[0]
        output[10] = ff.state()[1]
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7472(Base_14pin):

    "AND gated JK Master-Slave Flip Flop with preset and clear"

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            0]

    def run(self):
        output = {}
        J = Connector(AND(self.pins[3], self.pins[4], self.pins[5]).output())
        K = Connector(AND(self.pins[9], self.pins[10], self.pins[11]).output())
        if not isinstance(self.pins[12], Clock):
            raise Exception("Error: Invalid Clock Input")
        ff = JKFlipFlop(J, K, Connector(1), self.pins[12].A,
                        self.pins[13], self.pins[2])
        while True:
            if self.pins[12].A.state == 0:
                ff.trigger()
                break
        while True:
            if self.pins[12].A.state == 1:
                ff.trigger()
                break
        output[8] = ff.state()[0]
        output[10] = ff.state()[1]
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7473(Base_14pin):

    "DUAL JK Flip Flops with clear"

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            0,
            0,
            None,
            None,
            0]

    def run(self):
        output = {}
        if not (isinstance(self.pins[1], Clock) and
                isinstance(self.pins[5], Clock)):
            raise Exception("Error: Invalid Clock Input")
        ff1 = JKFlipFlop(
            self.pins[14],
            self.pins[3],
            Connector(1),
            self.pins[1].A,
            Connector(1),
            self.pins[2])
        while True:
            if self.pins[1].A.state == 0:
                ff1.trigger()
                break
        while True:
            if self.pins[1].A.state == 1:
                ff1.trigger()
                break
        output[12] = ff1.state()[0]
        output[13] = ff1.state()[1]

        ff2 = JKFlipFlop(
            self.pins[7],
            self.pins[10],
            Connector(1),
            self.pins[5].A,
            Connector(1),
            self.pins[6])
        while True:
            if self.pins[5].A.state == 0:
                ff2.trigger()
                break
        while True:
            if self.pins[5].A.state == 1:
                ff2.trigger()
                break
        output[9] = ff2.state()[0]
        output[8] = ff2.state()[1]
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7474(Base_14pin):

    "Dual D-Type Positive-Edge-Triggered Flip-Flops with preset and clear"

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            None,
            None,
            0,
            None,
            None,
            0,
            0,
            0,
            0,
            0]

    def run(self):
        output = {}
        if not (isinstance(self.pins[3], Clock) and
                isinstance(self.pins[11], Clock)):
            raise Exception("Error: Invalid Clock Input")
        ff1 = DFlipFlop(self.pins[2], Connector(1), self.pins[3].A,
                        self.pins[4], self.pins[1])
        while True:
            if self.pins[3].A.state == 0:
                ff1.trigger()
                break
        while True:
            if self.pins[3].A.state == 1:
                ff1.trigger()
                break
        output[5] = ff1.state()[0]
        output[6] = ff1.state()[1]

        ff2 = DFlipFlop(self.pins[12], Connector(1), self.pins[11].A,
                        self.pins[10], self.pins[13])
        while True:
            if self.pins[11].A.state == 0:
                ff2.trigger()
                break
        while True:
            if self.pins[11].A.state == 1:
                ff2.trigger()
                break
        output[9] = ff2.state()[0]
        output[8] = ff2.state()[1]
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7486(Base_14pin):

    """
    This is a quad 2-input exclusive OR gate
    """

    # Datasheet here, http://www.skot9000.com/ttl/datasheets/86.pdf

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0]

    def run(self):
        output = {}

        output[3] = XOR(self.pins[1], self.pins[2]).output()

        output[6] = XOR(self.pins[4], self.pins[5]).output()

        output[8] = XOR(self.pins[9], self.pins[10]).output()

        output[11] = XOR(self.pins[12], self.pins[13]).output()

        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_74152(Base_14pin):

    """
    This is 14-pin 8:1 multiplexer with inverted input.

    Pin Number  Description
        1   D4
        2   D3
        3   D2
        4   D1
        5   D0
        6   Output W
        7   Ground
        8   select line C
        9   select line B
        10  select line A
        11  D7
        12  D6
        13     D5
        14  Positive Supply

        Selectlines = CBA and Inputlines = D0 D1 D2 D3 D4 D5 D6 D7
    """

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, 0, 0, 0, 0, 0, 0, 0]

    def run(self):

        output = {}

        mux = MUX(
            self.pins[5],
            self.pins[4],
            self.pins[3],
            self.pins[2],
            self.pins[1],
            self.pins[13],
            self.pins[12],
            self.pins[11])
        mux.selectLines(self.pins[8], self.pins[9], self.pins[10])

        output[6] = NOT(mux.output()).output()

        if self.pins[7] == 0 and self.pins[14] == 1:
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_74260(Base_14pin):

    """
    This is a dual 5-input NOR gate
    """

    # Datasheet here, http://www.skot9000.com/ttl/datasheets/260.pdf

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, None, None, 0, 0, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}

        output[5] = NOR(self.pins[1], self.pins[2], self.pins[3],
                        self.pins[12], self.pins[13]).output()

        output[6] = NOR(self.pins[4], self.pins[8], self.pins[9],
                        self.pins[10], self.pins[11]).output()

        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


#################################
# IC's with 16 pins
#################################

class IC_7431(Base_16pin):

    """
    This is a Hex delay element.
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            None,
            0,
            None,
            0,
            0]

    def run(self):
        output = {}
        output[2] = NOT(self.pins[1]).output()
        output[7] = NAND(self.pins[5], self.pins[6]).output()
        output[14] = NOT(self.pins[15]).output()
        output[9] = NAND(self.pins[10], self.pins[11]).output()
        output[4] = self.pins[3]
        output[12] = self.pins[13]

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7442(Base_16pin):

    """
    This is a BCD to Decimal decoder
    BCD Digits are in order of A B C D where pin 15 = A, pin 12 = D
    """

    def __init__(self):
        self.pins = [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            0,
            None,
            None,
            None,
            0,
            0,
            0,
            0,
            0]
        self.invalidlist = [
            [
                1, 0, 1, 0], [
                1, 0, 1, 1], [
                1, 1, 0, 0], [
                1, 1, 0, 1], [
                1, 1, 1, 0], [
                1, 1, 1, 1]]

    def run(self):
        output = {}
        inputlist = []
        for i in range(12, 16, 1):
            inputlist.append(self.pins[i])

        if inputlist in self.invalidlist:
            raise Exception("ERROR: Invalid BCD number")

        output[1] = NAND(NOT(self.pins[15]).output(),
                         NOT(self.pins[14]).output(),
                         NOT(self.pins[13]).output(),
                         NOT(self.pins[12]).output()).output()

        output[2] = NAND(
            self.pins[15], NOT(
                self.pins[14]).output(), NOT(
                self.pins[13]).output(), NOT(
                self.pins[12]).output()).output()

        output[3] = NAND(NOT(self.pins[15]).output(),
                         self.pins[14],
                         NOT(self.pins[13]).output(),
                         NOT(self.pins[12]).output()).output()

        output[4] = NAND(
            self.pins[15], self.pins[14], NOT(
                self.pins[13]).output(), NOT(
                self.pins[12]).output()).output()

        output[5] = NAND(NOT(self.pins[15]).output(),
                         NOT(self.pins[14]).output(),
                         self.pins[13],
                         NOT(self.pins[12]).output()).output()

        output[6] = NAND(self.pins[15], NOT(self.pins[14]).output(),
                         self.pins[13], NOT(self.pins[12]).output()).output()

        output[7] = NAND(NOT(self.pins[15]).output(), self.pins[14],
                         self.pins[13], NOT(self.pins[12]).output()).output()

        output[9] = NAND(self.pins[15], self.pins[14],
                         self.pins[13], NOT(self.pins[12]).output()).output()

        output[10] = NAND(NOT(self.pins[15]).output(),
                          NOT(self.pins[14]).output(),
                          NOT(self.pins[13]).output(),
                          self.pins[12]).output()

        output[11] = NAND(self.pins[15], NOT(self.pins[14]).output(),
                          NOT(self.pins[13]).output(), self.pins[12]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7443(Base_16pin):

    """
    This is an excess-3 to Decimal decoder
    Excess-3 binary digits are in order of A B C D, where pin 15 = A and pin 12 = D
    """

    def __init__(self):
        self.pins = [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            0,
            None,
            None,
            None,
            0,
            0,
            0,
            0,
            0]
        self.invalidlist = [
            [0, 0, 0, 0],
            [0, 0, 0, 1], [
                0, 0, 1, 0], [
                1, 1, 0, 1], [
                1, 1, 1, 0], [
                1, 1, 1, 1]]

    def run(self):
        output = {}
        inputlist = []
        for i in range(12, 16, 1):
            inputlist.append(self.pins[i])

        if inputlist in self.invalidlist:
            raise Exception("ERROR: Invalid Pin configuration")

        output[1] = NAND(
            self.pins[15], self.pins[14], NOT(
                self.pins[13]).output(), NOT(
                self.pins[12]).output()).output()

        output[2] = NAND(NOT(self.pins[15]).output(),
                         NOT(self.pins[14]).output(),
                         self.pins[13],
                         NOT(self.pins[12]).output()).output()

        output[3] = NAND(self.pins[15], NOT(self.pins[14]).output(),
                         self.pins[13], NOT(self.pins[12]).output()).output()

        output[4] = NAND(NOT(self.pins[15]).output(), self.pins[14],
                         self.pins[13], NOT(self.pins[12]).output()).output()

        output[5] = NAND(self.pins[15], self.pins[14],
                         self.pins[13], NOT(self.pins[12]).output()).output()

        output[6] = NAND(NOT(self.pins[15]).output(),
                         NOT(self.pins[14]).output(),
                         NOT(self.pins[13]).output(),
                         self.pins[12]).output()

        output[7] = NAND(self.pins[15], NOT(self.pins[14]).output(),
                         NOT(self.pins[13]).output(), self.pins[12]).output()

        output[9] = NAND(NOT(self.pins[15]).output(), self.pins[14],
                         NOT(self.pins[13]).output(), self.pins[12]).output()

        output[10] = NAND(self.pins[15], self.pins[14],
                          NOT(self.pins[13]).output(), self.pins[12]).output()

        output[11] = NAND(NOT(self.pins[15]).output(),
                          NOT(self.pins[14]).output(),
                          self.pins[13],
                          self.pins[12]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7444(Base_16pin):

    """
    This is an excess-3 gray code to Decimal decoder
    Excess-3 gray code digits are in order of A B C D, where pin 15 = A and pin 12 = D
    """

    def __init__(self):
        self.pins = [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            0,
            None,
            None,
            None,
            0,
            0,
            0,
            0,
            0]
        self.invalidlist = [[0, 0, 0, 0],
                            [0, 0, 0, 1],
                            [0, 0, 1, 1],
                            [1, 0, 0, 0],
                            [1, 0, 0, 1],
                            [1, 0, 1, 1]]

    def run(self):
        output = {}
        inputlist = []
        for i in range(12, 16, 1):
            inputlist.append(self.pins[i])

        if inputlist in self.invalidlist:
            raise Exception("ERROR: Invalid Pin configuration")

        output[1] = NAND(NOT(self.pins[15]).output(),
                         self.pins[14],
                         NOT(self.pins[13]).output(),
                         NOT(self.pins[12]).output()).output()

        output[2] = NAND(NOT(self.pins[15]).output(), self.pins[14],
                         self.pins[13], NOT(self.pins[12]).output()).output()

        output[3] = NAND((self.pins[15]), self.pins[14],
                         self.pins[13], NOT(self.pins[12]).output()).output()

        output[4] = NAND(self.pins[15], NOT(self.pins[14]).output(),
                         self.pins[13], NOT(self.pins[12]).output()).output()

        output[5] = NAND(NOT(self.pins[15]).output(),
                         NOT(self.pins[14]).output(),
                         self.pins[13],
                         NOT(self.pins[12]).output()).output()

        output[6] = NAND(NOT(self.pins[15]).output(),
                         NOT(self.pins[14]).output(),
                         self.pins[13],
                         self.pins[12]).output()

        output[7] = NAND(self.pins[15], NOT(self.pins[14]).output(),
                         self.pins[13], self.pins[12]).output()

        output[9] = NAND(self.pins[15], self.pins[14],
                         self.pins[13], self.pins[12]).output()

        output[10] = NAND(NOT(self.pins[15]).output(), self.pins[14],
                          self.pins[13], self.pins[12]).output()

        output[11] = NAND(NOT(self.pins[15]).output(), self.pins[14],
                          NOT(self.pins[13]).output(), self.pins[12]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7445(Base_16pin):

    """
    This is a Four-to-Ten (BCD to Decimal) DECODER using the DEMUX functionality from combinational.py
    datasheet at http://www.skot9000.com/ttl/datasheets/45.pdf
    """

    def __init__(self):
        self.pins = [
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            0,
            None,
            None,
            None,
            0,
            0,
            0,
            0,
            0]

        self.invalidlist = [
            [1, 0, 1, 0],
            [1, 0, 1, 1],
            [1, 1, 0, 0],
            [1, 1, 0, 1],
            [1, 1, 1, 0],
            [1, 1, 1, 1]]

    def run(self):
        output = {}
        inputlist = []
        for i in range(12, 16, 1):
            inputlist.append(self.pins[i])

        if inputlist in self.invalidlist:
            raise Exception("ERROR: Invalid Pin configuration")

        dem = DEMUX(1)
        dem.selectLines(
            self.pins[12],
            self.pins[13],
            self.pins[14],
            self.pins[15])
        ou = dem.output()

        output[1] = NOT(ou[0]).output()

        output[2] = NOT(ou[1]).output()

        output[3] = NOT(ou[2]).output()

        output[4] = NOT(ou[3]).output()

        output[5] = NOT(ou[4]).output()

        output[6] = NOT(ou[5]).output()

        output[7] = NOT(ou[6]).output()

        output[9] = NOT(ou[7]).output()

        output[10] = NOT(ou[8]).output()

        output[11] = NOT(ou[9]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7459(Base_14pin):

    """
    This is a 2-input and 3-input AND-OR inverter gate
    """
    # Datasheet here, http://www.unitechelectronics.com/7451-7497data.htm and
    # http://en.wikipedia.org/wiki/List_of_7400_series_integrated_circuits

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, None, 0, None, 0, 0, 0, 0, 0, 0]

    def run(self):
        temp = []
        output = {}
        temp.append(AND(self.pins[2], self.pins[3]).output())
        temp.append(AND(self.pins[4], self.pins[5]).output())
        temp.append(AND(self.pins[1],
                        self.pins[13],
                        self.pins[12]).output())
        temp.append(AND(self.pins[11],
                        self.pins[10],
                        self.pins[9]).output())
        output[6] = NOR(temp[0], temp[1]).output()
        output[8] = NOR(temp[2], temp[3]).output()

        if self.pins[7] == 0 and self.pins[14] == 1:
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7475(Base_16pin):
    # Datasheet here, http://www.skot9000.com/ttl/datasheets/83.pdf

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0,
            0,
            None,
            None,
            0]

    def run(self):
        output = {}

        output[9] = XOR(self.pins[10], self.pins[11], self.pins[13]).output()

        carry = OR(AND(self.pins[13],
                       XOR(self.pins[10],
                           self.pins[11]).output()).output(),
                   AND(self.pins[10],
                       self.pins[11]).output()).output()

        output[6] = XOR(self.pins[8], self.pins[7], carry).output()

        carry = OR(AND(carry, XOR(self.pins[8], self.pins[7]).output()).output(), AND(
            self.pins[8], self.pins[7]).output()).output()

        output[2] = XOR(self.pins[3], self.pins[4], carry).output()

        carry = OR(AND(carry, XOR(self.pins[3], self.pins[4]).output()).output(), AND(
            self.pins[3], self.pins[4]).output()).output()

        output[15] = XOR(self.pins[1], self.pins[16], carry).output()

        output[14] = OR(AND(carry,
                            XOR(self.pins[1],
                                self.pins[16]).output()).output(),
                        AND(self.pins[1],
                            self.pins[16]).output()).output()

        if self.pins[12] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


##############################################
# Sequential Circuits
##############################################

##############################################
# Base_14 Pin
##############################################

class IC_7470(Base_14pin):

    "AND gated JK Positive Edge triggered Flip Flop with preset and clear"

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            0]

    def run(self):
        output = {}
        J = Connector(AND(self.pins[3], self.pins[4], self.pins[5]).output())
        K = Connector(AND(self.pins[9], self.pins[10], self.pins[11]).output())
        if not isinstance(self.pins[12], Clock):
            raise Exception("Error: Invalid Clock Input")
        ff = JKFlipFlop(J, K, Connector(1), self.pins[12].A,
                        self.pins[13], self.pins[2])
        while True:
            if self.pins[12].A.state == 0:
                ff.trigger()
                break
        while True:
            if self.pins[12].A.state == 1:
                ff.trigger()
                break
        output[8] = ff.state()[0]
        output[10] = ff.state()[1]
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7472(Base_14pin):

    "AND gated JK Master-Slave Flip Flop with preset and clear"

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            0]

    def run(self):
        output = {}
        J = Connector(AND(self.pins[3], self.pins[4], self.pins[5]).output())
        K = Connector(AND(self.pins[9], self.pins[10], self.pins[11]).output())
        if not isinstance(self.pins[12], Clock):
            raise Exception("Error: Invalid Clock Input")
        ff = JKFlipFlop(J, K, Connector(1), self.pins[12].A,
                        self.pins[13], self.pins[2])
        while True:
            if self.pins[12].A.state == 0:
                ff.trigger()
                break
        while True:
            if self.pins[12].A.state == 1:
                ff.trigger()
                break
        output[8] = ff.state()[0]
        output[10] = ff.state()[1]
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7473(Base_14pin):

    "DUAL JK Flip Flops with clear"

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            0,
            0,
            None,
            None,
            0]

    def run(self):
        output = {}
        if not (isinstance(self.pins[1], Clock) and
                isinstance(self.pins[5], Clock)):
            raise Exception("Error: Invalid Clock Input")
        ff1 = JKFlipFlop(
            self.pins[14],
            self.pins[3],
            Connector(1),
            self.pins[1].A,
            Connector(1),
            self.pins[2])
        while True:
            if self.pins[1].A.state == 0:
                ff1.trigger()
                break
        while True:
            if self.pins[1].A.state == 1:
                ff1.trigger()
                break
        output[12] = ff1.state()[0]
        output[13] = ff1.state()[1]

        ff2 = JKFlipFlop(
            self.pins[7],
            self.pins[10],
            Connector(1),
            self.pins[5].A,
            Connector(1),
            self.pins[6])
        while True:
            if self.pins[5].A.state == 0:
                ff2.trigger()
                break
        while True:
            if self.pins[5].A.state == 1:
                ff2.trigger()
                break
        output[9] = ff2.state()[0]
        output[8] = ff2.state()[1]
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7474(Base_14pin):

    "Dual D-Type Positive-Edge-Triggered Flip-Flops with preset and clear"

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            None,
            None,
            0,
            None,
            None,
            0,
            0,
            0,
            0,
            0]

    def run(self):
        output = {}
        if not (isinstance(self.pins[3], Clock) and
                isinstance(self.pins[11], Clock)):
            raise Exception("Error: Invalid Clock Input")
        ff1 = DFlipFlop(self.pins[2], Connector(1), self.pins[3].A,
                        self.pins[4], self.pins[1])
        while True:
            if self.pins[3].A.state == 0:
                ff1.trigger()
                break
        while True:
            if self.pins[3].A.state == 1:
                ff1.trigger()
                break
        output[5] = ff1.state()[0]
        output[6] = ff1.state()[1]

        ff2 = DFlipFlop(self.pins[12], Connector(1), self.pins[11].A,
                        self.pins[10], self.pins[13])
        while True:
            if self.pins[11].A.state == 0:
                ff2.trigger()
                break
        while True:
            if self.pins[11].A.state == 1:
                ff2.trigger()
                break
        output[9] = ff2.state()[0]
        output[8] = ff2.state()[1]
        if self.pins[7] == 0 and self.pins[14] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


##########################################
# Base_16 Pins
##########################################

class IC_7475(Base_16pin):

    "4-Bit Bistable Latches"

    def __init__(self):
        self.pins = [
            None,
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            None,
            None,
            None,
            0,
            0,
            None,
            None,
            None]

    def run(self):
        output = {}
        if not (isinstance(self.pins[4], Clock) and
                isinstance(self.pins[13], Clock)):
            raise Exception("Error: Invalid Clock Input")
        ff1 = DFlipFlop(self.pins[2], Connector(1),
                        self.pins[13].A, Connector(1), Connector(1))
        while True:
            if self.pins[13].A.state == 0:
                ff1.trigger()
                break
        while True:
            if self.pins[13].A.state == 1:
                ff1.trigger()
                break
        output[16] = ff1.state()[0]
        output[1] = ff1.state()[1]

        ff2 = DFlipFlop(self.pins[3], Connector(1),
                        self.pins[13].A, Connector(1), Connector(1))
        while True:
            if self.pins[13].A.state == 0:
                ff2.trigger()
                break
        while True:
            if self.pins[13].A.state == 1:
                ff2.trigger()
                break
        output[15] = ff2.state()[0]
        output[14] = ff2.state()[1]

        ff3 = DFlipFlop(self.pins[6], Connector(1),
                        self.pins[4].A, Connector(1), Connector(1))
        while True:
            if self.pins[4].A.state == 0:
                ff3.trigger()
                break
        while True:
            if self.pins[4].A.state == 1:
                ff3.trigger()
                break
        output[10] = ff3.state()[0]
        output[11] = ff3.state()[1]

        ff4 = DFlipFlop(self.pins[7], Connector(1),
                        self.pins[4].A, Connector(1), Connector(1))
        while True:
            if self.pins[4].A.state == 0:
                ff4.trigger()
                break
        while True:
            if self.pins[4].A.state == 1:
                ff4.trigger()
                break
        output[9] = ff4.state()[0]
        output[8] = ff4.state()[1]
        if self.pins[12] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7476(Base_16pin):

    "Dual JK Flip Flop with preset and clear"

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            0,
            0,
            None,
            None,
            0]

    def run(self):
        output = {}
        if not (isinstance(self.pins[1], Clock) and
                isinstance(self.pins[6], Clock)):
            raise Exception("Error: Invalid Clock Input")
        ff1 = JKFlipFlop(
            self.pins[4],
            self.pins[16],
            Connector(1),
            self.pins[1].A,
            self.pins[2],
            self.pins[3])
        while True:
            if self.pins[1].A.state == 0:
                ff1.trigger()
                break
        while True:
            if self.pins[1].A.state == 1:
                ff1.trigger()
                break
        output[15] = ff1.state()[0]
        output[14] = ff1.state()[1]

        ff2 = JKFlipFlop(
            self.pins[9],
            self.pins[12],
            Connector(1),
            self.pins[6].A,
            self.pins[7],
            self.pins[8])
        while True:
            if self.pins[6].A.state == 0:
                ff2.trigger()
                break
        while True:
            if self.pins[6].A.state == 1:
                ff2.trigger()
                break
        output[11] = ff2.state()[0]
        output[10] = ff2.state()[1]
        if self.pins[12] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_7483(Base_16pin):

    """
    This is a 4-bit full adder with fast carry
    """

    # Datasheet here, http://www.skot9000.com/ttl/datasheets/83.pdf

    def __init__(self):
        self.pins = [
            None,
            0,
            None,
            0,
            0,
            0,
            None,
            0,
            0,
            None,
            0,
            0,
            0,
            0,
            None,
            None,
            0]

    def run(self):
        output = {}

        output[9] = XOR(self.pins[10], self.pins[11], self.pins[13]).output()

        carry = OR(AND(self.pins[13],
                       XOR(self.pins[10],
                           self.pins[11]).output()).output(),
                   AND(self.pins[10],
                       self.pins[11]).output()).output()

        output[6] = XOR(self.pins[8], self.pins[7], carry).output()

        carry = OR(AND(carry, XOR(self.pins[8], self.pins[7]).output()).output(), AND(
            self.pins[8], self.pins[7]).output()).output()

        output[2] = XOR(self.pins[3], self.pins[4], carry).output()

        carry = OR(AND(carry, XOR(self.pins[3], self.pins[4]).output()).output(), AND(
            self.pins[3], self.pins[4]).output()).output()

        output[15] = XOR(self.pins[1], self.pins[16], carry).output()

        output[14] = OR(AND(carry,
                            XOR(self.pins[1],
                                self.pins[16]).output()).output(),
                        AND(self.pins[1],
                            self.pins[16]).output()).output()

        if self.pins[12] == 0 and self.pins[5] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_74133(Base_16pin):

    """
    This is a 13-input NAND gate
    """

    # Datasheet here, http://www.skot9000.com/ttl/datasheets/133.pdf

    def __init__(self):
        self.pins = [None, 0, 0, 0, 0, 0, 0, 0, 0, None, 0, 0, 0, 0, 0, 0, 0]

    def run(self):
        output = {}

        output[9] = NAND(
            self.pins[1],
            self.pins[2],
            self.pins[3],
            self.pins[4],
            self.pins[5],
            self.pins[6],
            self.pins[7],
            self.pins[10],
            self.pins[11],
            self.pins[12],
            self.pins[13],
            self.pins[14],
            self.pins[15]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            self.setIC(output)
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_74138(Base_16pin):

    """
    This is a 1:8 demultiplexer(3:8 decoder) with output being inverted input
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            0]

    def run(self):

        output = {}

        demux = DEMUX(1)
        demux.selectLines(self.pins[3], self.pins[2], self.pins[1])

        if (self.pins[6] == 0 or (self.pins[4] == 1 and self.pins[5] == 1)):
            output = {15: 1, 14: 1, 13: 1, 12: 1, 11: 1, 10: 1, 9: 1, 7: 1}

        elif (self.pins[6] == 1 and (self.pins[4] == 0 and self.pins[5] == 0)):

            output[15] = NOT(demux.output()[0]).output()
            output[14] = NOT(demux.output()[1]).output()
            output[13] = NOT(demux.output()[2]).output()
            output[12] = NOT(demux.output()[3]).output()
            output[11] = NOT(demux.output()[4]).output()
            output[10] = NOT(demux.output()[5]).output()
            output[9] = NOT(demux.output()[6]).output()
            output[7] = NOT(demux.output()[7]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_74139(Base_16pin):

    """
    This is a dual 1:4 demultiplexer(2:4 decoder) with output being inverted input
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            None,
            None,
            None,
            None,
            0,
            None,
            None,
            None,
            None,
            0,
            0,
            0,
            0]

    def run(self):

        output = {}

        demux1 = DEMUX(1)
        demux1.selectLines(self.pins[3], self.pins[2])

        demux2 = DEMUX(1)
        demux2.selectLines(self.pins[13], self.pins[14])

        if (self.pins[1] == 1 and self.pins[15] == 1):
            output = {12: 1, 11: 1, 10: 1, 9: 1, 7: 1, 6: 1, 5: 1, 4: 1}

        elif (self.pins[1] == 0 and self.pins[15] == 1):

            output[12] = 1
            output[11] = 1
            output[10] = 1
            output[9] = 1
            output[4] = NOT(demux1.output()[0]).output()
            output[5] = NOT(demux1.output()[1]).output()
            output[6] = NOT(demux1.output()[2]).output()
            output[7] = NOT(demux1.output()[3]).output()

        elif (self.pins[1] == 1 and self.pins[15] == 0):

            output[7] = 1
            output[6] = 1
            output[5] = 1
            output[4] = 1
            output[12] = NOT(demux2.output()[0]).output()
            output[11] = NOT(demux2.output()[1]).output()
            output[10] = NOT(demux2.output()[2]).output()
            output[9] = NOT(demux2.output()[3]).output()

        elif (self.pins[1] == 0 and self.pins[15] == 0):

            output[4] = NOT(demux1.output()[0]).output()
            output[5] = NOT(demux1.output()[1]).output()
            output[6] = NOT(demux1.output()[2]).output()
            output[7] = NOT(demux1.output()[3]).output()
            output[12] = NOT(demux2.output()[0]).output()
            output[11] = NOT(demux2.output()[1]).output()
            output[10] = NOT(demux2.output()[2]).output()
            output[9] = NOT(demux2.output()[3]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_74151A(Base_16pin):

    """
    This is 16-pin 8:1 multiplexer featuring complementary W and Y outputs
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            None,
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0]

    def run(self):

        output = {}

        mux = MUX(
            self.pins[4],
            self.pins[3],
            self.pins[2],
            self.pins[1],
            self.pins[15],
            self.pins[14],
            self.pins[13],
            self.pins[12])
        mux.selectLines(self.pins[9], self.pins[10], self.pins[11])

        if self.pins[7] == 1:
            output = {5: 0, 6: 1}
        else:
            output[5] = mux.output()
            output[6] = NOT(output[5]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_74153(Base_16pin):

    """
    This is 16-pin dual 4:1 multiplexer with output same as the input.

        Pin Number  Description
        1   Strobe1
        2   Select line B
        3   1C3
        4   1C2
        5   1C1
        6   1C0
        7   1Y - OUTPUT1
        8   Ground
        9   2Y - OUTPUT2
        10  2C0
        11  2C1
        12  2C2
        13  2C3
        14     Select line A
        15     Strobe2
        16  Positive Supply

        Selectlines = BA ; Inputlines1 = 1C0 1C1 1C2 1C3 ; Inputlines2 = 2C0 2C1 2C2 2C3
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            None,
            0,
            None,
            0,
            0,
            0,
            0,
            0,
            0,
            0]

    def run(self):

        output = {}

        if (self.pins[1] == 1 and self.pins[15] == 1):
            output = {7: 0, 9: 0}

        elif (self.pins[1] == 0 and self.pins[15] == 1):

            mux = MUX(self.pins[6], self.pins[5], self.pins[4], self.pins[3])
            mux.selectLines(self.pins[2], self.pins[14])

            output[9] = 0
            output[7] = mux.output()

        elif (self.pins[1] == 1 and self.pins[15] == 0):

            mux = MUX(
                self.pins[10],
                self.pins[11],
                self.pins[12],
                self.pins[13])
            mux.selectLines(self.pins[2], self.pins[14])

            output[7] = 0
            output[9] = mux.output()

        elif (self.pins[1] == 0 and self.pins[15] == 0):

            mux1 = MUX(self.pins[6], self.pins[5], self.pins[4], self.pins[3])
            mux1.selectLines(self.pins[2], self.pins[14])

            mux2 = MUX(
                self.pins[10],
                self.pins[11],
                self.pins[12],
                self.pins[13])
            mux2.selectLines(self.pins[2], self.pins[14])

            output[7] = mux1.output()
            output[9] = mux2.output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_74155(Base_16pin):

    """
    This is a dual 1:4 demultiplexer(2:4 decoder) with one output being inverted input
    while the other same as the input
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            None,
            None,
            None,
            None,
            0,
            None,
            None,
            None,
            None,
            0,
            0,
            0,
            0]

    def run(self):

        output = {}

        demux1 = DEMUX(self.pins[1])
        demux1.selectLines(self.pins[3], self.pins[13])

        demux2 = DEMUX(NOT(self.pins[15]).output())
        demux2.selectLines(self.pins[3], self.pins[13])

        if (self.pins[2] == 1 and self.pins[14] == 1):
            output = {12: 1, 11: 1, 10: 1, 9: 1, 7: 1, 6: 1, 5: 1, 4: 1}

        elif (self.pins[2] == 0 and self.pins[14] == 1):

            output[12] = 1
            output[11] = 1
            output[10] = 1
            output[9] = 1
            output[4] = NOT(demux1.output()[3]).output()
            output[5] = NOT(demux1.output()[2]).output()
            output[6] = NOT(demux1.output()[1]).output()
            output[7] = NOT(demux1.output()[0]).output()

        elif (self.pins[2] == 1 and self.pins[14] == 0):

            output[7] = 1
            output[6] = 1
            output[5] = 1
            output[4] = 1
            output[12] = NOT(demux2.output()[3]).output()
            output[11] = NOT(demux2.output()[2]).output()
            output[10] = NOT(demux2.output()[1]).output()
            output[9] = NOT(demux2.output()[0]).output()

        elif (self.pins[2] == 0 and self.pins[14] == 0):

            output[4] = NOT(demux1.output()[3]).output()
            output[5] = NOT(demux1.output()[2]).output()
            output[6] = NOT(demux1.output()[1]).output()
            output[7] = NOT(demux1.output()[0]).output()
            output[12] = NOT(demux2.output()[3]).output()
            output[11] = NOT(demux2.output()[2]).output()
            output[10] = NOT(demux2.output()[1]).output()
            output[9] = NOT(demux2.output()[0]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")


class IC_74156(Base_16pin):

    """
    This is a dual 1:4 demultiplexer(2:4 decoder) with one output being inverted input
    while the other same as the input with open collector
    """

    def __init__(self):
        self.pins = [
            None,
            0,
            0,
            0,
            None,
            None,
            None,
            None,
            0,
            None,
            None,
            None,
            None,
            0,
            0,
            0,
            0]

    def run(self):

        output = {}

        demux1 = DEMUX(self.pins[1])
        demux1.selectLines(self.pins[3], self.pins[13])

        demux2 = DEMUX(NOT(self.pins[15]).output())
        demux2.selectLines(self.pins[3], self.pins[13])

        if (self.pins[2] == 1 and self.pins[14] == 1):
            output = {12: 1, 11: 1, 10: 1, 9: 1, 7: 1, 6: 1, 5: 1, 4: 1}

        elif (self.pins[2] == 0 and self.pins[14] == 1):

            output[12] = 1
            output[11] = 1
            output[10] = 1
            output[9] = 1
            output[4] = NOT(demux1.output()[3]).output()
            output[5] = NOT(demux1.output()[2]).output()
            output[6] = NOT(demux1.output()[1]).output()
            output[7] = NOT(demux1.output()[0]).output()

        elif (self.pins[2] == 1 and self.pins[14] == 0):

            output[7] = 1
            output[6] = 1
            output[5] = 1
            output[4] = 1
            output[12] = NOT(demux2.output()[3]).output()
            output[11] = NOT(demux2.output()[2]).output()
            output[10] = NOT(demux2.output()[1]).output()
            output[9] = NOT(demux2.output()[0]).output()

        elif (self.pins[2] == 0 and self.pins[14] == 0):

            output[4] = NOT(demux1.output()[3]).output()
            output[5] = NOT(demux1.output()[2]).output()
            output[6] = NOT(demux1.output()[1]).output()
            output[7] = NOT(demux1.output()[0]).output()
            output[12] = NOT(demux2.output()[3]).output()
            output[11] = NOT(demux2.output()[2]).output()
            output[10] = NOT(demux2.output()[1]).output()
            output[9] = NOT(demux2.output()[0]).output()

        if self.pins[8] == 0 and self.pins[16] == 1:
            for i in self.outputConnector:
                self.outputConnector[i].state = output[i]
            return output
        else:
            print("Ground and VCC pins have not been configured correctly.")

########NEW FILE########
__FILENAME__ = operations
class Operations:

    """
    This class implements the primary arithmetic binary functions ADD, SUB, MUL, DIV, COMP(complement).
    Inputs are in the form of unsigned integers. Negative numbers will have - sign.
    """

    def __parseInput(self, input1, input2):

        if isinstance(input1, list):
            input1 = ''.join(map(str, input1))
        elif not isinstance(input1, str):
            input1 = str(input1)

        if isinstance(input2, list):
            input2 = ''.join(map(str, input2))
        elif not isinstance(input2, str):
            input2 = str(input2)

        return input1, input2

    def ADD(self, input1, input2):
        """
        This function implements the binary addition
        It takes two binary number and gives their sum
        How to use:
            >>> opr = Operations()
            >>> opr.ADD('1100','0001')
            '1101'
        """

        a, b = self.__parseInput(input1, input2)
        c = bin(int(a, 2) + int(b, 2))
        if c[0] == '-':
            return c[3:]
        else:
            return c[2:]

    def SUB(self, input1, input2):
        """
        This function implements the binary subtraction
        It takes two binary number and gives their difference
        How to use:
            >>> opr = Operations()
            >>> opr.SUB('1100','0100')
            '1000'
        """

        a, b = self.__parseInput(input1, input2)
        c = bin(int(a, 2) - int(b, 2))
        if c[0] == '-':
            return c[3:]
        else:
            return c[2:]

    def MUL(self, input1, input2):
        """
        This function implements the binary multiplication
        It takes two binary number and gives their product
        How to use:
            >>> opr = Operations()
            >>> opr.MUL('1100','0100')
            '110000'
        """

        a, b = self.__parseInput(input1, input2)
        c = bin(int(a, 2) * int(b, 2))
        if c[0] == '-':
            return c[3:]
        else:
            return c[2:]

    def DIV(self, input1, input2):
        """
        This function implements the binary division
        It takes two binary number and gives their quotient
        How to use:
            >>> opr = Operations()
            >>> opr.DIV('1000','0010')
            '100'
        """

        a, b = self.__parseInput(input1, input2)
        c = bin(int(a, 2) // int(b, 2))
        if c[0] == '-':
            return c[3:]
        else:
            return c[2:]

    def COMP(self, input1, option):
        """
        This function gives the complement of the input
        Note: In this case the input is put in the form of signed/unsigned number
        It takes two parameters, number to be complemented and the nth complement you want.
        How to use:
            >>> opr = Operations()
            >>> opr.COMP('1000','1')
            '0111'
        """

        if isinstance(input1, list):
            input1 = ''.join(map(str, input1))
        elif not isinstance(input1, str):
            input1 = str(input1)

        result = bin(int(input1, 2) ^ int(len(input1) * '1', 2))[2:]
        temp = bin(int(result, 2) + int('1', 2))[2:]
        if str(option) == '1':
            return (len(input1) - len(result)) * '0' + result
        else:
            return (len(input1) - len(temp)) * temp[0] + temp

    @staticmethod
    def decToBin(number):
        """
        This function converts positive decimal number into binary number
        How to use:
            >>> Operations.decToBin(12)
            >>> 1100
        """

        exponent = 0
        shifted_num = number
        while shifted_num != int(shifted_num):
            shifted_num *= 2
            exponent += 1
        if exponent == 0:
            return '{0:0b}'.format(int(shifted_num))
        binary = '{0:0{1}b}'.format(int(shifted_num), exponent + 1)
        integer_part = binary[:-exponent]
        fractional_part = binary[-exponent:].rstrip('0')
        return '{0}.{1}'.format(integer_part, fractional_part)

    @staticmethod
    def binToDec(number):
        """
        This function converts binary number into decimal number
        How to use:
            >>> Operations.binToDec('1001')
            >>> 9
        """

        if isinstance(number, list):
            number = ''.join([str(i) for i in number])
        if "." in number:
            [x, y] = number.split(".")
            bin_x = int(x, 2)
            a = -1
            bin_y = 0
            for i in list(y):
                if i != "0" and i != "1":
                    raise Exception("Invalid Input")
                bin_y = bin_y + (int(i) * (2 ** a))
                a = a - 1
            flt = bin_x + bin_y
            return flt
        flt = int(number, 2)
        return flt

########NEW FILE########
__FILENAME__ = counters
from BinPy.Sequential import *
from BinPy.Sequential.registers import *


class Counter(object):

    """
    Base class for all counters
    """

    def __init__(self, bits, clock_connector, data, preset, clear):

        self.bits = bits
        self.out = []
        for i in range(self.bits):
            self.out.append(Connector(data))
        self.outinv = []
        for i in range(self.bits):
            self.outinv.append(Connector(NOT(data).output()))

        self.outold = self.out[:]
        self.outoldinv = self.outinv[:]
        self.ff = [None] * self.bits
        self.enable = Connector(1)
        self.t = Connector(1)
        self.clk = clock_connector
        self.set_once = False
        self.reset_once = False
        self.bits_fixed = False
        self.ripple_type = True
        self.preset = preset
        self.clear = clear

    def setInput(self, t, enable):
        if isinstance(t, Connector):
            self.t = t
        else:
            self.t.state = int(t)
        if isinstance(enable, Connector):
            self.enable = enable
        else:
            self.enable.state = int(enable)

    def trigger(self, ffnumber=None):

        self.outold = self.out[:]
        if ffnumber is None:
            ffnumber = self.bits - 1

        # Sending a negative edge to ff
        while True:
            if self.clk.state == 0:
                # Falling edge will trigger the FF
                if self.ripple_type:
                    self.ff[ffnumber].trigger()
                else:
                    for i in range(self.bits):
                        self.ff[i].trigger()
                break
        # Sending a positive edge to ff
        while True:
            if self.clk.state == 1:
                if self.ripple_type:
                    self.ff[ffnumber].trigger()
                else:
                    for i in range(self.bits):
                        self.ff[i].trigger()
                break
        # This completes one full pulse.

        if self.clear.state == 1 and self.preset.state == 0:
            self.setCounter()
        elif self.preset.state == 1 and self.clear.state == 0:
            self.resetCounter()

        return self.state()

    def __call__(self):
        self.trigger()

    def setCounter(self):
        inset = self.clear.state
        if self.bits_fixed:
            self.__init__(self.clk, 1, self.preset, self.clear)
        else:
            self.__init__(self.bits, self.clk, 1, self.preset, self.clear)
        if not self.set_once:
            self.clear.state = inset

    def resetCounter(self):
        reset = self.preset.state
        if self.bits_fixed:
            self.__init__(self.clk, 0, self.preset, self.clear)
        else:
            self.__init__(self.bits, self.clk, 0, self.preset, self.clear)
        if not self.reset_once:
            self.preset.state = reset

    def enable(self):
        # Enables counting on trigger
        self.enable.state = 1

    def disable(self):
        # Disables counter
        self.enable.state = 0

    def state(self):
        # MSB is at the Right Most position
        # To print with MSB at the Left Most position

        return [self.out[i].state for i in range(self.bits)]


class BinaryCounter(Counter):

    """
    An N-Bit Binary Counter
    Output connectors can be referenced by --> BinaryCounter_instance_name.out

    Examples
    ========

    >>> From BinPy import *
    >>> clock = Clock(0, 100)  #A clock with leading edge = 0 and frequency = 100Hz
    >>> clock.start()
    >>> clk_conn = clock.A
    >>> b = BinaryCounter(2, clk_conn)
    >>> for i in range(0, 5):
    >>>     b.trigger()
    >>>     print(b.state)
    [0, 1]
    [1, 0]
    [1, 1]
    [0, 0]
    [0, 1]
    """

    def __init__(self, bits, clk, data=0,
                 preset=Connector(1), clear=Connector(1)):
        Counter.__init__(self, bits, clk, data, preset, clear)

        # Calling the super class constructor
        self.ff[self.bits - 1] = TFlipFlop(
            self.t,
            self.enable,
            self.clk,
            self.preset,
            self.clear,
            self.out[self.bits - 1],
            self.outinv[self.bits - 1])
        for i in range(self.bits - 2, -1, -1):
            self.ff[i] = TFlipFlop(
                self.t,
                self.enable,
                self.out[i + 1],
                self.preset,
                self.clear,
                self.out[i],
                self.outinv[i])

        # <self.bit> nos of TFlipFlop instances are appended in the ff array
        # output of previous stage becomes the input clock for next flip flop


class NBitRippleCounter(Counter):

    """
    An N-Bit Ripple Counter

    Examples
    ========

    >>> From BinPy import *
    >>> clock = Clock(0, 100)  #A clock with leading edge = 0 and frequency = 100Hz
    >>> clock.start()
    >>> clk_conn = clock.A
    >>> counter = NBitRippleCounter(4, clk_conn)
    >>> for i in range(0, 8):
    >>>     counter.trigger()
    >>>     print(counter.state)
    [0, 0, 0, 1]
    [0, 0, 1, 0]
    [0, 0, 1, 1]
    [0, 1, 0, 0]
    [0, 1, 0, 1]
    [0, 1, 1, 0]
    [0, 1, 1, 1]
    [1, 0, 0, 0]
    [1, 0, 0, 1]
    [1, 0, 1, 0]
    [1, 0, 1, 1]
    [1, 1, 0, 0]
    [1, 1, 0, 1]
    [1, 1, 1, 0]
    [1, 1, 1, 1]
    [0, 0, 0, 0]
    """

    def __init__(
            self,
            bits,
            clock_connector,
            data=0,
            preset=Connector(1),
            clear=Connector(1)):

        # All the output bits are initialized to this data bit

        Counter.__init__(self, bits, clock_connector, data,
                         preset, clear)
        # Calling the super class constructor

        self.ff[
            self.bits -
            1] = TFlipFlop(
            self.t,
            self.enable,
            self.clk,
            self.preset,
            self.clear,
            self.out[
                self.bits -
                1],
            self.outinv[
                self.bits -
                1])

        for i in range(self.bits - 1):
            self.ff[i] = TFlipFlop(
                self.t,
                self.enable,
                self.out[
                    i + 1],
                self.preset,
                self.clear,
                self.out[i],
                self.outinv[i])


class NBitDownCounter(Counter):

    """
    An N-Bit Down Counter

    Examples
    ========

    >>> From BinPy import *
    >>> clock = Clock(0, 100)  #A clock with leading edge = 0 and frequency = 100Hz
    >>> clock.start()
    >>> clk_conn = clock.A
    >>> counter = NBitDownCounter(4, clk_conn)
    >>> for i in range(0, 8):
    >>>     counter.trigger()
    >>>     print(counter.state)
    [1, 1, 1, 1]
    [1, 1, 1, 0]
    [1, 1, 0, 1]
    [1, 1, 0, 0]
    [1, 0, 1, 1]
    [1, 0, 1, 0]
    [1, 0, 0, 1]
    [1, 0, 0, 0]
    [0, 1, 1, 1]
    [0, 1, 1, 0]
    [0, 1, 0, 1]
    [0, 1, 0, 0]
    [0, 0, 1, 1]
    [0, 0, 1, 0]
    [0, 0, 0, 1]
    [0, 0, 0, 0]
    [1, 1, 1, 1]
    """

    def __init__(
            self,
            bits,
            clock_connector,
            data=0,
            preset=Connector(1),
            clear=Connector(1)):

        # All the output bits are initialized to this data bit
        Counter.__init__(self, bits, clock_connector, data,
                         preset, clear)
        # Calling the super class constructor

        self.ff[
            self.bits -
            1] = TFlipFlop(
            self.t,
            self.enable,
            self.clk,
            self.preset,
            self.clear,
            self.out[
                self.bits -
                1],
            self.outinv[
                self.bits -
                1])

        for i in range(self.bits - 1):
            self.ff[i] = TFlipFlop(
                self.t,
                self.enable,
                self.outinv[
                    i + 1],
                self.preset,
                self.clear,
                self.out[i],
                self.outinv[i])


class DecadeCounter(Counter):

    """
    A 4-Bit Decade Counter
    """

    def __init__(
            self,
            clock_connector,
            data=0,
            preset=Connector(1),
            clear=Connector(1)):

        # All the output bits are initialized to this data bit

        Counter.__init__(self, 4, clock_connector, data, preset,
                         clear)
        # Calling the super class constructor

        self.ff = [None] * 4

        self.ff[3] = TFlipFlop(
            self.t,
            self.enable,
            self.clk,
            self.preset,
            self.clear,
            self.out[3],
            self.outinv[3])
        self.ff[2] = TFlipFlop(
            self.t,
            self.enable,
            self.out[3],
            self.preset,
            self.clear,
            self.out[2],
            self.outinv[2])
        self.ff[1] = TFlipFlop(
            self.t,
            self.enable,
            self.out[2],
            self.preset,
            self.clear,
            self.out[1],
            self.outinv[1])
        self.ff[0] = TFlipFlop(
            self.t,
            self.enable,
            self.out[1],
            self.preset,
            self.clear,
            self.out[0],
            self.outinv[0])

        self.g1 = NAND(self.out[0], self.out[2])
        self.g1.setOutput(self.clear)

        self.bits_fixed = True
        self.reset_once = True


class OctalCounter(Counter):

    """
    A 4-Bit Octal Counter
    """

    def __init__(
            self,
            clock_connector,
            data=0,
            preset=Connector(1),
            clear=Connector(1)):

        # All the output bits are initialized to this data bit

        Counter.__init__(self, 4, clock_connector, data, preset,
                         clear)
        # Calling the super class constructor

        self.ff = [None] * 4

        self.ff[3] = TFlipFlop(
            self.t,
            self.enable,
            self.clk,
            self.preset,
            self.clear,
            self.out[3],
            self.outinv[3])
        self.ff[2] = TFlipFlop(
            self.t,
            self.enable,
            self.out[3],
            self.preset,
            self.clear,
            self.out[2],
            self.outinv[2])
        self.ff[1] = TFlipFlop(
            self.t,
            self.enable,
            self.out[2],
            self.preset,
            self.clear,
            self.out[1],
            self.outinv[1])
        self.ff[0] = TFlipFlop(
            self.t,
            self.enable,
            self.out[1],
            self.preset,
            self.clear,
            self.out[0],
            self.outinv[0])

        self.g1 = NOT(self.out[0])
        self.g1.setOutput(self.clear)

        self.bits_fixed = True
        self.reset_once = True


class Stage14Counter(Counter):

    """
    A 14-Bit Counter
    """

    def __init__(
            self,
            clock_connector,
            data=0,
            preset=Connector(1),
            clear=Connector(1)):

        # All the output bits are initialized to this data bit

        Counter.__init__(self, 4, clock_connector, data, preset,
                         clear)
        # Calling the super class constructor

        self.ff = [None] * 4

        self.ff[3] = TFlipFlop(
            self.t,
            self.enable,
            self.clk,
            self.preset,
            self.clear,
            self.out[3],
            self.outinv[3])
        self.ff[2] = TFlipFlop(
            self.t,
            self.enable,
            self.out[3],
            self.preset,
            self.clear,
            self.out[2],
            self.outinv[2])
        self.ff[1] = TFlipFlop(
            self.t,
            self.enable,
            self.out[2],
            self.preset,
            self.clear,
            self.out[1],
            self.outinv[1])
        self.ff[0] = TFlipFlop(
            self.t,
            self.enable,
            self.out[1],
            self.preset,
            self.clear,
            self.out[0],
            self.outinv[0])

        self.g1 = NAND(self.out[0], self.out[1], self.out[2])
        self.g1.setOutput(self.clear)

        self.bits_fixed = True
        self.reset_once = True


class RingCounter(Counter):

    """
    An N-bit Ring Counter
    """

    def __init__(
            self,
            bits,
            clock_connector,
            preset=Connector(1),
            clear=Connector(1)):

        Counter.__init__(self, bits, clock_connector, data=None, preset=preset,
                         clear=clear)
        arr = [0] * bits
        arr[0] = 1
        self.sr = ShiftRegister(arr, clock_connector, circular=1)
        self.out = []

    def trigger(self):
        self.out = self.sr.output()
        return self.out

    def state(self):
        return self.out

    def reset(self):
        self.__init__(self.bits, clock_connector, clear=Connector(0))

    def set(self):
        self.__init__(self.bits, clock_connector, preset=Connector(0))


class JohnsonCounter(Counter):

    """
    An N-bit Johnson Counter
    """

    def __init__(
            self,
            bits,
            clock_connector,
            preset=Connector(1),
            clear=Connector(1)):

        Counter.__init__(self, bits, clock_connector, data=None, preset=preset,
                         clear=clear)
        arr = [0] * bits
        arr[0] = 1
        self.sr = ShiftRegister(arr, clock_connector, circular=1)
        self.out = []
        self.tail = 1

    def trigger(self):
        self.out = self.sr.output()
        self.out[0] = self.tail
        self.tail = NOT(self.out[self.bits - 1]).output()
        return self.out

    def state(self):
        return self.out

    def reset(self):
        self.__init__(self.bits, clock_connector, clear=Connector(0))

    def set(self):
        self.__init__(self.bits, clock_connector, preset=Connector(0))

########NEW FILE########
__FILENAME__ = registers
from BinPy.Sequential.sequential import *
from BinPy.tools import *


class Register(object):

    """
    Base class for all registers
    """

    def __init__(self, inputs, clock, clear):
        self.inputs = inputs
        if not isinstance(clock, Clock):
            raise Exception("Error: Invalid Clock Input")
        self.clock = clock
        self.clear = clear
        self.result = None
        self.outputType = {}
        self.outputConnector = {}
        self._updateConnections(self.inputs)

    def _updateConnections(self, inputs):
        for i in inputs:
            if isinstance(i, Connector):
                i.tap(self, 'input')

    def setInputs(self, *inputs):
        if len(list(inputs)) < len(self.inputs):
            raise Exception("Error: Invalid Arguments")
        else:
            self.inputs = list(inputs)
            self._updateConnections(self.inputs)

    def setInput(self, index, value):
        if index >= len(self.inputs):
            self.inputs.append(value)
        else:
            self.inputs[index] = value
        if isinstance(value, Connector):
            value.tap(self, 'input')

    def setClock(self, clk):
        if not isinstance(clk, Clock):
            raise Exception("Error: Invalid Clock")
        self.clock = clk

    def setClear(self, clr):
        self.clear = clr

    def getInputStates(self):
        input_states = []
        for i in self.inputs:
            if isinstance(i, Connector):
                input_states.append(i.state)
            else:
                input_states.append(i)
        return input_states

    def _updateResult(self, value):
        self.result = value
        for i in self.outputType:
            if self.outputType[i] == 1:
                self.outputConnector[i].state = self.result[i]
                self.outputConnector[i].trigger()

    def setOutput(self, index, value):
        if not isinstance(value, Connector):
            raise Exception("Error: Expecting a Connector Class Object")
        self.outputType[index] = 1
        self.outputConnector[index] = value
        value.tap(self, 'output')
        self._updateResult(self.result)

    def output(self):
        self.trigger()
        return self.result


class FourBitRegister(Register):

    """
    Four Bit Register
    Inputs: A0, A1, A2, A3
    Clock: clock
    Clear: clear

    Example:
        >>> from BinPy import *
        >>> c = Clock(1, 500)
        >>> c.start()
        >>> fr = FourBitRegister(1, 0, 1, 1, c, 1)
        >>> fr.output()
        [1, 0, 1, 1]

    """

    def __init__(self, A0, A1, A2, A3, clock, clear):
        Register.__init__(self, [A0, A1, A2, A3], clock, clear)

    def trigger(self):
        out = []
        for i in range(0, 4):
            ff1 = DFlipFlop(self.inputs[i], Connector(1), self.clock.A,
                            clear=self.clear)

            while True:
                if self.clock.A.state == 1:
                    ff1.trigger()
                    break
            while True:
                if self.clock.A.state == 0:
                    ff1.trigger()
                    break
            out.append(ff1.state()[0])

        self._updateResult(out)


class FourBitLoadRegister(Register):

    """
    Four Bit Register with Load
    Inputs: A0, A1, A2, A3
    Clock: clock
    Clear: clear
    Load: load
    Methods: setLoad()

    Example:
        >>> from BinPy import *
        >>> c = Clock(1, 500)
        >>> c.start()
        >>> fr = FourBitLoadRegister(1, 0, 1, 1, c, 1, 1)
        >>> fr.output()
        [1, 0, 1, 0]

    """

    def __init__(self, A0, A1, A2, A3, clock, clear, load):
        self.old = [0, 0, 0, 0]             # Clear State
        self.load = load
        Register.__init__(self, [A0, A1, A2, A3], clock, clear)

    def setLoad(self, load):
        self.load = load

    def trigger(self):
        out = []
        for i in range(0, 4):
            ff1 = DFlipFlop(self.inputs[i], Connector(1), self.clock.A,
                            clear=self.clear)
            if self.load == 0:
                ff1.setInputs(d=self.old[i])
            while True:
                if self.clock.A.state == 1:
                    ff1.trigger()
                    break
            while True:
                if self.clock.A.state == 0:
                    ff1.trigger()
                    break
            out.append(ff1.state()[0])
        self.old = out
        self._updateResult(out)


class ShiftRegister(Register):

    """
    Shift Register
    Inputs: [A0, A1, A2, A3]
    Clock: clock

    Example:
        >>> from BinPy import *
        >>> c = Clock(1, 500)
        >>> c.start()
        >>> fr = ShiftRegister([1, 0, 0, 0], c)
        >>> fr.output()
        [1, 1, 0, 0]
        >>> fr.output()
        [1, 1, 1, 0]
        >>> fr.output()
        [1, 1, 1, 1]

    """

    def __init__(self, inputs, clock, clear=Connector(1), circular=0):
        self.circular = circular
        Register.__init__(self, inputs, clock, clear)

    def trigger(self):
        a0 = self.inputs[0]
        for i in range(0, len(self.inputs)):
            ff1 = DFlipFlop(self.inputs[i], Connector(1), self.clock.A,
                            clear=self.clear)
            if self.circular and i == 0:
                self.inputs[i] = self.inputs[len(self.inputs) - 1]
            else:
                self.inputs[i] = a0
            while True:
                if self.clock.A.state == 1:
                    ff1.trigger()
                    break
            while True:
                if self.clock.A.state == 0:
                    ff1.trigger()
                    break
            a0 = ff1.state()[0]
        out = self.inputs
        self._updateResult(out)

########NEW FILE########
__FILENAME__ = sequential
from __future__ import print_function
from BinPy import *


class FlipFlop:

    """
    Super Class for all FlipFlops
    """

    def __init__(self, enable, clk, a, b):
        self.a = a
        self.b = b
        self.clk = clk
        self.clkoldval = 1
        self.enable = enable

    def Enable(self):
        self.enable.state = 1

    def Disable(self):
        self.enable.state = 0

    def setff(self):
        # Sets the FlipFlop
        self.a.state = 1
        self.b.state = 0
        return [self.a(), self.b()]

    def resetff(self):
        # Resets the FlipFlop
        self.a.state = 0
        self.b.state = 1
        return [self.a(), self.b()]


class SRLatch(FlipFlop):

    """
    S and R are the two primary inputs.
    They are enabled by the third input enable.
    Clock is used to trigger the Latch.

    Outputs are a ( q ) and b ( ~q )

    To Use :
    Set the inputs of SRLatch and to trigger any change in input use\
    trigger() method.
    """

    def __init__(
            self,
            S,
            R,
            enable,
            clk,
            preset=Connector(1),
            clear=Connector(1),
            a=Connector(0),
            b=Connector(1)):

        FlipFlop.__init__(self, enable, clk, a, b)

        # Initiated to support numerical inputs --> See trigger method's doc
        self.S = Connector(0)
        self.R = Connector(1)

        self.preset = Connector(1)
        self.clear = Connector(1)
        # Initiated to initiate the gates
        self.enabledS = Connector(0)
        self.enabledR = Connector(1)

        # Initiating the gates with inputs - Will be overwritten when the
        # self.setInputs() is called 4 lines hence.

        # This is just to initiate the gates.
        self.en1 = AND(S, enable)
        self.en2 = AND(R, enable)

        self.g1 = NOR(self.enabledS, a)
        self.g2 = NOR(self.enabledR, b)

        self.setInputs(S=S, R=R, enable=enable, preset=preset, clear=clear)
        self.setOutputs(A=a, B=b)

    def setInputs(self, **inputs):
        """
        Sets the input connectors of SRLatch.
        Give input parameters as a dictionary

        Ex.: sr1.setInputs(S = S, R = R)
        Ex.2: sr2.setInputs(enable = en1)

        [ where S, R, foo are all Connector class instances. ]

        This is done to support partial change in input [ only S or R etc ]

        Note:
        1) When inputs are given as type-int - The S and R states alone are
        changed. The connections remain intact.
        2) Setting the inputs does not trigger the Latch.
        Use trigger separately to trigger any change.
        """

        # To support both upper and lower case
        for key in inputs:
            if key.lower() == 's':
                # To support both numerical values or Connector instances
                if isinstance(inputs[key], Connector):
                    self.S = inputs[key]
                else:
                    self.S.state = int(inputs[key])

            elif key.lower() == 'r':
                if isinstance(inputs[key], Connector):
                    self.R = inputs[key]
                else:
                    self.R.state = int(inputs[key])

            elif key.lower() == 'enable':
                if isinstance(inputs[key], Connector):
                    self.enable = inputs[key]
                else:
                    self.enable.state = int(inputs[key])

            elif key.lower() == 'clk':
                if isinstance(inputs[key], Connector):
                    self.clk = inputs[key]
                else:
                    self.clk.state = int(inputs[key])
            elif key.lower() == "preset":
                if isinstance(inputs[key], Connector):
                    self.preset = inputs[key]
                else:
                    self.preset.state = int(inputs[key])
            elif key.lower() == "clear":
                if isinstance(inputs[key], Connector):
                    self.clear = inputs[key]
                else:
                    self.clear.state = int(inputs[key])

            else:
                print("ERROR: Unknow parameter passed" + str(key))

        if not (bool(self.S) ^ bool(self.R)):
            print("ERROR: Invalid State - Resetting the Latch")
            self.S.state = 0
            self.R.state = 1
        if not (self.preset or self.clear):
            print("ERROR: Invalid State - Resetting the Latch")
            self.preset.state = 1
            self.clear.state = 1

        self.en1.setInput(0, self.S)
        self.en1.setInput(1, self.enable)
        self.en1.setOutput(self.enabledS)

        self.en2.setInput(0, self.R)
        self.en2.setInput(1, self.enable)
        self.en2.setOutput(self.enabledR)

        self.g1.setInput(0, self.enabledS)
        self.g1.setInput(1, self.a)

        self.g2.setInput(0, self.enabledR)
        self.g2.setInput(1, self.b)

    def setOutputs(self, **outputs):

        for key in outputs:
            if not isinstance(outputs[key], Connector):
                raise Exception("ERROR: Output not a connector instance")
            if key.lower() == 'a':
                self.a = outputs[key]
            elif key.lower() == 'b':
                self.b = outputs[key]
            else:
                print("ERROR: Unknow parameter passed" + str(key))

        self.g1.setOutput(self.b)
        self.g1.setInput(1, self.a)

        self.g2.setOutput(self.a)
        self.g2.setInput(1, self.b)

    def trigger(self):
        if self.clear.state == 1 and self.preset.state == 0:
            return self.setff()
        elif self.preset.state == 1 and self.clear.state == 0:
            return self.resetff()
        elif not(self.clear.state or self.preset.state):
            print("Error: Invalid State - Resetting the Latch")
            self.clear.state = 1
            self.preset.state = 1
        else:
            if self.clkoldval == 1 and self.clk.state == 0:
                if bool(self.S) and bool(self.R):
                    print("ERROR: Invalid State - Resetting the Latch")
                    self.S.state = 0
                    self.R.state = 1

                self.enable.trigger()
                # This will trigger the gates which will trigger the a and b

        self.clkoldval = self.clk.state
        # stores the current clock state

        return [self.a(), self.b()]

    def __call__(self):
        return self.trigger()

    def state(self):
        """Returns the current state of the SRLatch"""
        return [self.a(), self.b()]


class DFlipFlop(FlipFlop):

    """
    DATA Flip Flop ( Negative edge triggered )

    D is the primary input.
    enable activates the Flip Flop.
    ( Negative edge triggered )
    Clock triggers the output

    Outputs are a ( q ) and b ( ~q )

    """

    def __init__(
            self,
            D,
            enable,
            clk,
            preset=Connector(1),
            clear=Connector(1),
            a=Connector(0),
            b=Connector(0)):

        FlipFlop.__init__(self, enable, clk, a, b)
        # Initiated to support numerical inputs --> See trigger method's doc
        self.D = Connector(0)
        self.g1 = AND(self.D, self.enable)
        self.g2 = NOT(self.a)
        self.preset = Connector(1)
        self.clear = Connector(1)

        self.setInputs(D=D, enable=enable, preset=preset, clear=clear)
        self.setOutputs(A=a, B=b)

    def setInputs(self, **inputs):
        """
        Sets the input connectors of DFlipFlop.
        Give input parameters as a dictionary

        Ex.: dff.setInputs(D = dconnector, enable = enable_connector)
        Ex.2: dff.setInputs(enable = foo)

        Usage of **inputs is to pass parameters as dict to to support \
        partial change in input [ D or enable alone ]

        Note:
        1) When inputs are given as type-int - The D state alone is
        changed. The connections remain intact.
        2) Setting the inputs does not trigger the Latch.
        Use trigger separately to trigger any change.
        """

        # To support both upper and lower case
        for key in inputs:
            if key.lower() == "d":
                # To support both numerical/boolean values or Connector
                # instances
                if isinstance(inputs[key], Connector):
                    self.D = inputs[key]
                else:
                    self.D.state = int(inputs[key])
            elif key.lower() == "enable":
                if isinstance(inputs[key], Connector):
                    self.enable = inputs[key]
                else:
                    self.enable.state = int(inputs[key])
            elif key.lower() == "clk":
                if isinstance(inputs[key], Connector):
                    self.clk = inputs[key]
                else:
                    self.clk.state = int(inputs[key])
            elif key.lower() == "preset":
                if isinstance(inputs[key], Connector):
                    self.preset = inputs[key]
                else:
                    self.preset.state = int(inputs[key])
            elif key.lower() == "clear":
                if isinstance(inputs[key], Connector):
                    self.clear = inputs[key]
                else:
                    self.clear.state = int(inputs[key])
            else:
                print("ERROR: Unknow parameter passed" + str(key))

        if not(self.preset.state or self.clear.state):
            print("ERROR : Invalid State - Resetting the Latch")
            self.preset.state = 1
            self.clear.state = 1

        self.g1.setInput(0, self.D)
        self.g1.setInput(1, self.enable)
        self.g1.setOutput(self.a)

        self.g2.setInput(self.a)
        self.g2.setOutput(self.b)

    def setOutputs(self, **outputs):

        for key in outputs:
            if not isinstance(outputs[key], Connector):
                raise Exception("ERROR: Output not a connector instance")
            if key.lower() == "a":
                self.a = outputs[key]
            elif key.lower() == "b":
                self.b = outputs[key]
            else:
                print("ERROR: Unknow parameter passed" + str(key))

        self.g1.setOutput(self.a)

        self.g2.setInput(self.a)
        self.g2.setOutput(self.b)

    def trigger(self):
        if self.clear.state == 1 and self.preset.state == 0:
            return self.setff()
        elif self.preset.state == 1 and self.clear.state == 0:
            return self.resetff()
        elif not(self.clear.state or self.preset.state):
            print("Error: Invalid State - Resetting the Latch")
            self.clear.state = 1
            self.preset.state = 1
        else:
            if self.clkoldval == 1 and self.clk.state == 0:
                self.D.trigger()
        self.clkoldval = self.clk.state
        return [self.a(), self.b()]

    def __call__(self, **inputs):
        """Call to the FlipFlop instance will invoke the trigger method"""
        return self.trigger(**inputs)

    def state(self):
        """Returns the current state of the DFlipflop"""
        return [self.a(), self.b()]


class JKFlipFlop(FlipFlop):

    """
    J K Flip Flop - Negative edge triggered

    J and K are the two primary inputs.
    They are enabled by the third input enable.
    Clock triggers the Flip flop.

    Outputs are a ( q ) and b ( ~q )

    To Use :
    Set the inputs of JKFlipFlop and to trigger any change in input \
    use trigger() method.
    call to the JKFlipFlop instance also triggers it and returns the \
    current state as a list
    """

    def __init__(
            self,
            J,
            K,
            enable,
            clk,
            preset=Connector(1),
            clear=Connector(1),
            a=Connector(0),
            b=Connector(1)):

        FlipFlop.__init__(self, enable, clk, a, b)

        self.J = Connector(0)
        self.K = Connector(0)
        self.preset = Connector(1)
        self.clear = Connector(1)
        self.setInputs(J=J, K=K, enable=enable, preset=preset, clear=clear)
        self.setOutputs(A=a, B=b)

        self.J.tap(self, "input")
        self.K.tap(self, "input")
        self.enable.tap(self, "input")
        self.clk.tap(self, "input")

        self.a.tap(self, "output")
        self.b.tap(self, "output")

    def setInputs(self, **inputs):
        """
        Sets the input connectors of Jk Flip flop.
        Give input parameters as a dictionary

        Ex.: jk1.setInputs(J = J, K = K)
        Ex.2: jk2.setInputs(enable = foo)

        Where J, K, foo are all Connector class instances.

        This is done to support partial change in input [ only J or K etc ]

        Note:
        1) When inputs are given as type-int - The J and K states alone are
        changed. The connections remain intact.
        2) Setting the inputs does not trigger the Latch.
        Use trigger separately to trigger any change.
        """

        for key in inputs:
            # To support both upper and lower case
            if key.lower() == "j":
                # To support both numerical/boolean values or Connector
                # instances
                if isinstance(inputs[key], Connector):
                    self.J = inputs[key]
                else:
                    self.J.state = int(inputs[key])

            elif key.lower() == "k":
                if isinstance(inputs[key], Connector):
                    self.K = inputs[key]
                else:
                    self.K.state = int(inputs[key])

            elif key.lower() == "enable":
                if isinstance(inputs[key], Connector):
                    self.enable = inputs[key]
                else:
                    self.enable.state = int(inputs[key])
            elif key.lower() == "clk":
                if isinstance(inputs[key], Connector):
                    self.clk = inputs[key]
                else:
                    self.clk.state = int(inputs[key])
            elif key.lower() == "preset":
                if isinstance(inputs[key], Connector):
                    self.preset = inputs[key]
                else:
                    self.preset.state = int(inputs[key])
            elif key.lower() == "clear":
                if isinstance(inputs[key], Connector):
                    self.clear = inputs[key]
                else:
                    self.clear.state = int(inputs[key])
            else:
                print("ERROR: Unknow parameter passed" + str(key))

        if not(self.preset.state or self.clear.state):
            print("ERROR : Invalid State - Resetting the Latch")
            self.preset.state = 1
            self.clear.state = 1

        self.J.tap(self, "input")
        self.K.tap(self, "input")
        self.enable.tap(self, "input")
        self.clk.tap(self, "input")

    def setOutputs(self, **outputs):

        for key in outputs:
            if not isinstance(outputs[key], Connector):
                raise Exception("ERROR: Output not a connector instance")
            if key.lower() == "a":
                self.a = outputs[key]
            elif key.lower() == "b":
                self.b = outputs[key]
            else:
                print("ERROR: Unknow parameter passed" + str(key))

        self.a.tap(self, "output")
        self.b.tap(self, "output")

    def trigger(self):
        """
        Trigger will update the output when any of the inputs change.
        """
        if self.clear.state == 1 and self.preset.state == 0:
            return self.setff()
        elif self.preset.state == 1 and self.clear.state == 0:
            return self.resetff()
        elif not(self.clear.state or self.preset.state):
            print("Error: Invalid State - Resetting the Latch")
            self.clear.state = 1
            self.preset.state = 1
        else:
            # Using behavioural Modelling
            if self.clkoldval == 1 and self.clk.state == 0:

                if bool(self.enable):
                    if bool(self.J) and bool(self.K):
                        self.a.state = 0 if bool(self.a) else 1

                    elif not bool(self.J) and bool(self.K):
                        self.a.state = 0

                    elif bool(self.J) and not bool(self.K):
                        self.a.state = 1

                self.b.state = 0 if self.a.state else 1

                self.a.trigger()
                self.b.trigger()
        self.clkoldval = self.clk.state
        return [self.a(), self.b()]

    def __call__(self):
        return self.trigger()

    def state(self):
        return [self.a(), self.b()]


class TFlipFlop(JKFlipFlop):

    """
    Toggle Flip Flop. Negative edge triggered.

    Inputs are T and enable.
    Clock triggers the circuit

    Outputs are:
    a = ( q )
    b = ( q~ )
    """

    def __init__(
            self,
            T,
            enable,
            clk,
            preset=Connector(1),
            clear=Connector(1),
            a=Connector(),
            b=Connector()):

        JKFlipFlop.__init__(self, T, T, enable, clk, preset, clear, a, b)

    def setOutputs(self, **outputs):
        JKFlipFlop.setOutputs(self, **outputs)

    def trigger(self):
        JKFlipFlop.trigger(self)
        # Triggering of the outputs is done by the JKFlipFlop Module.

    def state(self):
        return [self.a(), self.b()]

    def __call__(self):
        self.trigger()
        return [self.a(), self.b()]

########NEW FILE########
__FILENAME__ = Shell
from __future__ import print_function
import subprocess
import platform
import os

from BinPy.__init__ import *
try:
    from BinPy import __version__ as BINPY_VERSION
except ImportError:
    BINPY_VERSION = ""


def shellclear():
    if platform.system() == "Windows":
        return
    subprocess.call("clear")


def magic_clear(self, arg):
    shellclear()

banner = '+-----------------------------------------------------------+\n\n'
banner += ' BinPy '
banner += BINPY_VERSION
banner += ' [interactive shell]\n\n'
banner += ' Website: www.binpy.org\n\n'
banner += ' Documentation: http://docs.binpy.org/\n\n'
banner += '+-----------------------------------------------------------+\n'
banner += '\n'
banner += 'Commands: \n'
banner += '\t"exit()" or press "Ctrl+ D" to exit the shell\n'
banner += '\t"clear()" to clear the shell screen\n'
banner += '\n'

exit_msg = '\n... [Exiting the BinPy interactive shell] ...\n'


def self_update():
    URL = "https://github.com/binpy/binpy/zipball/master"
    command = "pip install -U %s" % URL

    if os.getuid() == 0:
        command = "sudo " + command

    returncode = subprocess.call(command, shell=True)
    sys.exit()


def setupIpython():

    try:
        import IPython
    except:
        raise("ERROR: IPython Failed to load")

    try:
        from IPython.config.loader import Config
        from IPython.frontend.terminal.embed import InteractiveShellEmbed

        cfg = Config()
        cfg.PromptManager.in_template = "BinPy:\\#> "
        cfg.PromptManager.out_template = "BinPy:\\#: "
        bpyShell = InteractiveShellEmbed(config=cfg, banner1=banner,
                                         exit_msg=exit_msg)
        bpyShell.define_magic("clear", magic_clear)

    except ImportError:
        try:
            from IPython.Shell import IPShellEmbed
            argsv = ['-pi1', 'BinPY:\\#>', '-pi2', '   .\\D.:', '-po',
                     'BinPy:\\#>', '-nosep']
            bpyShell = IPShellEmbed(argsv)
            bpyShell.set_banner(banner)
            bpyShell.set_exit_msg(exit_msg)
        except ImportError:
            raise

    return bpyShell()


def run_notebook(mainArgs):
    """Run the ipython notebook server"""

    try:
        import IPython
    except:
        raise("ERROR: IPython Failed to load")

    try:
        from IPython.html import notebookapp
        from IPython.html.services.kernels import kernelmanager
    except:
        from IPython.frontend.html.notebook import notebookapp
        from IPython.frontend.html.notebook import kernelmanager

    kernelmanager.MappingKernelManager.first_beat = 30.0
    app = notebookapp.NotebookApp.instance()
    with open('BinPyNotebook0.ipynb', 'a') as new_ipynb:
        if (new_ipynb.tell() == 0):
            new_ipynb.write(
                """
                {
                "metadata": {
                "name": "",
                "signature": ""
                },
                "nbformat": 3,
                "nbformat_minor": 0,
                "worksheets": [
                {
                "cells": [
                    {
                    "cell_type": "code",
                    "collapsed": false,
                    "input": [
                    "from BinPy import *"
                    ],
                    "language": "python",
                    "metadata": {},
                    "outputs": [],
                    "prompt_number": 1
                    }
                ],
                "metadata": {}
                }
                ]
                }
            """
            )

    app.initialize(['BinPyNotebook0.ipynb'])
    app.start()
    sys.exit()


def shellMain(*args):
    log_level = logging.WARNING
    interface = None

    if len(sys.argv) > 1 and len(sys.argv[1]) > 1:
        flag = sys.argv[1]
        print (flag)

        if flag == 'update':
            print ("Updating BinPy...")
            self_update()

        elif flag == 'notebook':
            run_notebook(['.'])
            sys.exit()

        if flag in ['--nowarnings', 'nowarnings']:
            log_level = logging.INFO
        elif flag in ['--debug', 'debug']:
            log_level = logging.DEBUG

    init_logging(log_level)
    shellclear()
    bpyShell = setupIpython()

########NEW FILE########
__FILENAME__ = analog_devices_tests
from BinPy.Analog import *
from nose.tools import with_setup, nottest


def test_Resisitor():
    params = {'r': 5}
    r = Resistor(params)
    assert r.getParams()['i'] == 0
    assert r.getParams()['r'] == 5
    assert r.getParams()['+'].state == 0
    assert r.getParams()['-'].state == 0

    r.setVoltage(Connector(5), Connector(0))
    assert r.getParams()['i'] == 1.0
    assert r.getParams()['r'] == 5
    assert r.getParams()['+'].state == 5
    assert r.getParams()['-'].state == 0

    r.setCurrent(10)
    assert r.getParams()['i'] == 10
    assert r.getParams()['r'] == 5
    assert r.getParams()['+'].state == 50
    assert r.getParams()['-'].state == 0

    r.setResistance(10)
    assert r.getParams()['i'] == 5.0
    assert r.getParams()['r'] == 10
    assert r.getParams()['+'].state == 50
    assert r.getParams()['-'].state == 0

########NEW FILE########
__FILENAME__ = analog_source_tests
from BinPy.Analog import *
from nose.tools import with_setup, nottest


def test_SinWaveVoltageSource():
    source = SinWaveVoltageSource()

    assert source.getParams()['e'] == 0
    assert source.getParams()['t'] == 0
    assert source.getParams()['w'] == 0
    assert source.getParams()['V'] == 0
    assert source.getParams()['H'].state == 0.0
    assert source.getParams()['L'].state == 0

    params = {'V': 5, 'w': 10, 't': 10, 'e': 0}
    source.setParams(params)

    assert source.getParams()['e'] == 0
    assert source.getParams()['t'] == 10
    assert source.getParams()['w'] == 10
    assert source.getParams()['V'] == 5
    assert source.getParams()['H'].state == 4.9
    assert source.getParams()['L'].state == 0

    params = {'V': 5, 'w': 0, 't': 0, 'e': 90}
    source.setParams(params)

    assert source.getParams()['e'] == 90
    assert source.getParams()['t'] == 0
    assert source.getParams()['w'] == 0
    assert source.getParams()['V'] == 5
    assert source.getParams()['H'].state == 5.0
    assert source.getParams()['L'].state == 0


def test_CosWaveVoltageSource():
    source = CosWaveVoltageSource()

    assert source.getParams()['e'] == 0
    assert source.getParams()['t'] == 0
    assert source.getParams()['w'] == 0
    assert source.getParams()['V'] == 0
    assert source.getParams()['H'].state == 0.0
    assert source.getParams()['L'].state == 0

    params = {'V': 5, 'w': 10, 't': 10, 'e': 0}
    source.setParams(params)

    assert source.getParams()['e'] == 0
    assert source.getParams()['t'] == 10
    assert source.getParams()['w'] == 10
    assert source.getParams()['V'] == 5
    assert source.getParams()['H'].state == -0.8500000000000001
    assert source.getParams()['L'].state == 0

    params = {'V': 5, 'w': 0, 't': 0, 'e': 90}
    source.setParams(params)

    assert source.getParams()['e'] == 90
    assert source.getParams()['t'] == 0
    assert source.getParams()['w'] == 0
    assert source.getParams()['V'] == 5
    assert source.getParams()['H'].state == 0.0
    assert source.getParams()['L'].state == 0


def test_SinWaveCurrentSource():
    source = SinWaveCurrentSource()

    assert source.getParams()['e'] == 0
    assert source.getParams()['t'] == 0
    assert source.getParams()['w'] == 0
    assert source.getParams()['I'] == 0
    assert source.getParams()['i'] == 0.0
    assert source.getParams()['H'].state == 0
    assert source.getParams()['L'].state == 0

    params = {'I': 5, 'w': 10, 't': 10, 'e': 0}
    source.setParams(params)

    assert source.getParams()['e'] == 0
    assert source.getParams()['t'] == 10
    assert source.getParams()['w'] == 10
    assert source.getParams()['I'] == 5
    assert source.getParams()['i'] == 4.9
    assert source.getParams()['H'].state == 0
    assert source.getParams()['L'].state == 0

    params = {'I': 5, 'w': 0, 't': 0, 'e': 90}
    source.setParams(params)

    assert source.getParams()['e'] == 90
    assert source.getParams()['t'] == 0
    assert source.getParams()['w'] == 0
    assert source.getParams()['I'] == 5
    assert source.getParams()['i'] == 5.0
    assert source.getParams()['H'].state == 0
    assert source.getParams()['L'].state == 0


def test_CosWaveCurrentSource():
    source = CosWaveCurrentSource()

    assert source.getParams()['e'] == 0
    assert source.getParams()['t'] == 0
    assert source.getParams()['w'] == 0
    assert source.getParams()['I'] == 0
    assert source.getParams()['i'] == 0.0
    assert source.getParams()['H'].state == 0
    assert source.getParams()['L'].state == 0

    params = {'I': 5, 'w': 10, 't': 10, 'e': 0}
    source.setParams(params)

    assert source.getParams()['e'] == 0
    assert source.getParams()['t'] == 10
    assert source.getParams()['w'] == 10
    assert source.getParams()['I'] == 5
    assert source.getParams()['i'] == -0.8500000000000001
    assert source.getParams()['H'].state == 0
    assert source.getParams()['L'].state == 0

    params = {'I': 5, 'w': 0, 't': 0, 'e': 90}
    source.setParams(params)

    assert source.getParams()['e'] == 90
    assert source.getParams()['t'] == 0
    assert source.getParams()['w'] == 0
    assert source.getParams()['I'] == 5
    assert source.getParams()['i'] == 0.0
    assert source.getParams()['H'].state == 0
    assert source.getParams()['L'].state == 0

########NEW FILE########
__FILENAME__ = combinational_tests
from BinPy.Combinational.combinational import *
from nose.tools import with_setup, nottest


def HalfAdder_test():
    ha = HalfAdder(0, 1)
    assert ha.output() == [0, 1]

    ha.set_input(0, 1)
    assert ha.output() == [1, 0]

    ha.set_inputs(0, 0)
    assert ha.output() == [0, 0]

    ha.set_inputs(1, 1)
    assert ha.output() == [1, 0]


def FullAdder_test():
    fa = FullAdder(0, 1, 0)
    assert fa.output() == [0, 1]

    fa.set_inputs(1, 1, 1)
    assert fa.output() == [1, 1]

    fa.set_input(1, 0)
    assert fa.output() == [1, 0]

    con1 = Connector()
    con2 = Connector()

    fa.set_output(1, con1)
    fa.set_output(0, con2)

    assert [con2.state, con1.state] == fa.output()

'''
def BCDAdder_test():
    ba = BCDAdder([0, 1, 1, 0], [0, 0, 1, 1], 0)
    assert ba.output() == [0, 1, 0, 0, 1]

    ba = BCDAdder([0, 1, 1, 0], [0, 0, 1, 1], 1)
    assert ba.output() == [0, 0, 1, 1, 1]
'''


def HalfSubtractor_test():
    hs = HalfSubtractor(0, 1)
    assert hs.output() == [1, 1]

    hs = HalfSubtractor(1, 1)
    assert hs.output() == [0, 0]


def FullSubtractor_test():
    fs = FullSubtractor(0, 1, 1)
    assert fs.output() == [1, 0]
    fs = FullSubtractor(1, 1, 0)
    assert fs.output() == [0, 0]
    fs = FullSubtractor(1, 1, 1)
    assert fs.output() == [1, 1]


def MUX_test():
    mux = MUX(0, 1)
    mux.selectLines(0)
    if mux.output() != 0:
        assert False
    mux.selectLines(1)
    if mux.output() != 1:
        assert False

    mux = MUX(0, 1, 0, 1)
    mux.selectLines(0, 0)
    if mux.output() != 0:
        assert False
    mux.selectLines(0, 1)
    if mux.output() != 1:
        assert False
    mux.selectLines(1, 0)
    if mux.output() != 0:
        assert False
    mux.selectLines(1, 1)
    if mux.output() != 1:
        assert False

    a = Connector()
    b = Connector()
    NOT(1).setOutput(a)
    NOT(0).setOutput(b)
    mux = MUX(0, 1, 0, 1)
    mux.selectLines(a, b)
    if mux.output() != 1:
        assert False
    mux.selectLine(1, a)
    if mux.output() != 0:
        assert False
    mux.setInput(0, 1)
    if mux.output() != 1:
        assert False


def DEMUX_test():
    demux = DEMUX(0)
    demux.selectLines(0)
    q = [0, 0]
    if demux.output() != q:
        assert False
    demux.selectLines(1)
    if demux.output() != q:
        assert False
    demux = DEMUX(1)
    demux.selectLines(0)
    q = [1, 0]
    if demux.output() != q:
        assert False
    demux.selectLines(1)
    q = [0, 1]
    if demux.output() != q:
        assert False

    demux = DEMUX(0)
    demux.selectLines(0, 0)
    q = [0, 0, 0, 0]
    if demux.output() != q:
        assert False
    demux.selectLines(0, 1)
    if demux.output() != q:
        assert False
    demux = DEMUX(1)
    demux.selectLines(1, 0)
    q = [0, 0, 1, 0]
    if demux.output() != q:
        assert False
    demux.selectLines(1, 1)
    q = [0, 0, 0, 1]
    if demux.output() != q:
        assert False

    a = Connector()
    b = Connector()
    NOT(1).setOutput(a)
    NOT(0).setOutput(b)
    demux = DEMUX(0)
    demux.selectLines(a, 0)
    q = [0, 0, 0, 0]
    if demux.output() != q:
        assert False
    demux.setInputs(b)
    demux.selectLine(1, b)
    q = [0, 1, 0, 0]
    if demux.output() != q:
        assert False


def Decoder_test():
    try:
        decoder = Decoder()
        assert False
    except Exception:
        pass

    decoder = Decoder(0)
    try:
        decoder.setInputs()
        assert False
    except Exception:
        pass

    decoder = Decoder(0)
    q = [1, 0]
    if decoder.output() != q:
        assert False
    decoder = Decoder(1)
    q = [0, 1]
    if decoder.output() != q:
        assert False

    decoder = Decoder(0, 0)
    q = [1, 0, 0, 0]
    if decoder.output() != q:
        assert False
    decoder = Decoder(0, 1)
    q = [0, 1, 0, 0]
    if decoder.output() != q:
        assert False
    decoder = Decoder(1, 0)
    q = [0, 0, 1, 0]
    if decoder.output() != q:
        assert False
    decoder = Decoder(1, 1)
    q = [0, 0, 0, 1]
    if decoder.output() != q:
        assert False

    a = Connector()
    b = Connector()
    NOT(1).setOutput(a)
    NOT(0).setOutput(b)
    decoder = Decoder(a, a)
    q = [1, 0, 0, 0]
    if decoder.output() != q:
        assert False
    decoder.setInput(1, b)
    q = [0, 1, 0, 0]
    if decoder.output() != q:
        assert False


def Encoder_test():
    encoder = Encoder(0, 1)
    q = [1]
    if encoder.output() != q:
        assert False
    encoder = Encoder(1, 0)
    q = [0]
    if encoder.output() != q:
        assert False

    encoder = Encoder(1, 0, 0, 0)
    q = [0, 0]
    if encoder.output() != q:
        assert False
    encoder = Encoder(0, 1, 0, 0)
    q = [0, 1]
    if encoder.output() != q:
        assert False
    encoder = Encoder(0, 0, 1, 0)
    q = [1, 0]
    if encoder.output() != q:
        assert False
    encoder = Encoder(0, 0, 0, 1)
    q = [1, 1]
    if encoder.output() != q:
        assert False

    a = Connector()
    b = Connector()
    NOT(1).setOutput(a)
    NOT(0).setOutput(b)
    encoder = Encoder(a, 0, 0, 1)
    q = [1, 1]
    if encoder.output() != q:
        assert False
    encoder.setInputs(b, 0, 0, a)
    q = [0, 0]
    if encoder.output() != q:
        assert False

########NEW FILE########
__FILENAME__ = connectors_tests
from BinPy.Gates.gates import *
from nose.tools import with_setup, nottest


class Buffer_Block:

    def __init__(self):

        self.inputs = Bus(4)

        # Tests Bus initiation from another Bus
        self.outputs = Bus(self.inputs)

    def trigger(self):
        # Testing Copy values to
        self.outputs.copy_values_to(self.inputs)


def connectors_test():

    a = Buffer_Block()
    b = Buffer_Block()
    c = Buffer_Block()

    # Basic list test
    assert isinstance(a.outputs.bus, list)

    # Test for Connector initiation of bus
    a.inputs.set_logic_all('1011')
    a.trigger()

    # Test for __reversed__
    [int(i) for i in reversed(a.outputs)] == [1, 1, 0, 1]
    # a.outputs will have '1011'

    # Test __getitem__
    conn3 = a.outputs[3]

    # Test Connector
    assert isinstance(conn3, Connector)
    assert conn3.get_logic() == 1
    assert bool(conn3)
    assert float(conn3) == 5.0

    # Set voltage test
    a.outputs[3].set_voltage(0.0)

    # Test get_voltage_all as binary literal test
    assert int(a.outputs.get_logic_all(as_list=False), 2) == 10

    a.outputs.set_voltage_all(list(reversed(a.outputs)))

    assert float(a.outputs[0]) == 0
    assert int(a.outputs[3]) == 1

    # Testing copy_values_from
    b.inputs.set_logic_all(
        Connector(1),
        Connector(0),
        Connector(1),
        Connector(1))
    b.trigger()

    # Testing comparison operations

    assert b.outputs.get_logic_all() == [1, 0, 1, 1]

    assert b.outputs.get_voltage_all() == [5, 0, 5, 5]

    assert b.outputs == [1, 0, 1, 1]

    b.outputs.set_type(analog=True)

    assert b.outputs == [5, 0, 5, 5]

    assert b.outputs.get_logic_all(as_list=False)

    c = a.outputs + b.outputs
    c.trigger()

    assert c == [0, 1, 0, 1, 1, 0, 1, 1]

########NEW FILE########
__FILENAME__ = counters_tests
from BinPy import *
from nose.tools import with_setup, nottest


def test_BinaryCounter():

    clock = Clock(1, 500)
    clock.start()
    test_BinaryCounter = BinaryCounter(2, clock.A)
    op = []
    for i in range(5):
        test_BinaryCounter.trigger()
        op += test_BinaryCounter.state()

    assert op == [0, 1, 1, 0, 1, 1, 0, 0, 0, 1]

    clock.kill()


def test_NBitRippleCounter():

    clock = Clock(1, 500)
    clock.start()
    test_NBitRippleCounter = NBitRippleCounter(3, clock.A)
    op = []
    for i in range(9):
        test_NBitRippleCounter.trigger()
        op += test_NBitRippleCounter.state()

    assert op == [0, 0, 1, 0, 1, 0, 0, 1, 1, 1, 0,
                  0, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1]

    clock.kill()


def test_NBitDownCounter():

    clock = Clock(1, 500)
    clock.start()
    test_NBitDownCounter = NBitDownCounter(3, clock.A)
    op = []
    for i in range(9):
        test_NBitDownCounter.trigger()
        op += test_NBitDownCounter.state()

    assert op == [1, 1, 1, 1, 1, 0, 1, 0, 1, 1, 0,
                  0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1]

    clock.kill()


def test_DecadeCounter():

    clock = Clock(1, 500)
    clock.start()
    test_DecadeCounter = DecadeCounter(clock.A)
    op = []
    for i in range(14):
        test_DecadeCounter.trigger()
        op += test_DecadeCounter.state()

    assert op == [0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1,
                  1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1,
                  1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1,
                  0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1,
                  0, 0, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0]

    clock.kill()


def test_RingCounter():

    clock = Clock(1, 500)
    clock.start()
    test_RingCounter = RingCounter(8, clock)
    op = []
    for i in range(8):
        test_RingCounter.trigger()
        op += test_RingCounter.state()

    assert op == [0, 1, 0, 0, 0, 0, 0, 0,
                  0, 0, 1, 0, 0, 0, 0, 0,
                  0, 0, 0, 1, 0, 0, 0, 0,
                  0, 0, 0, 0, 1, 0, 0, 0,
                  0, 0, 0, 0, 0, 1, 0, 0,
                  0, 0, 0, 0, 0, 0, 1, 0,
                  0, 0, 0, 0, 0, 0, 0, 1,
                  1, 0, 0, 0, 0, 0, 0, 0]
    clock.kill()


def test_JohnsonCounter():

    clock = Clock(1, 500)
    clock.start()
    test_JohnsonCounter = JohnsonCounter(4, clock)
    op = []
    for i in range(8):
        test_JohnsonCounter.trigger()
        op += test_JohnsonCounter.state()

    assert op == [1, 1, 0, 0, 1, 1, 1, 0,
                  1, 1, 1, 1, 0, 1, 1, 1,
                  0, 0, 1, 1, 0, 0, 0, 1,
                  0, 0, 0, 0, 1, 0, 0, 0]
    clock.kill()

########NEW FILE########
__FILENAME__ = expr_tests
from BinPy import *
from nose.tools import with_setup, nottest


def parse_test():

    assert Expr('A & B').parse() == 'AND(B, A)'

    assert Expr('(A & B)').parse() == 'AND(B, A)'

    assert Expr('(~A) & B').parse() == 'AND(B, NOT(A))'

    assert Expr('~(A & B)').parse() == 'NAND(B, A)'

    assert Expr('A | B').parse() == 'OR(B, A)'

    assert Expr('A ^ B').parse() == 'XOR(B, A)'

    assert Expr('A ^ ~B').parse() == 'XOR(NOT(B), A)'

########NEW FILE########
__FILENAME__ = gates_tests
from BinPy.Gates.gates import *
from nose.tools import with_setup, nottest


def AND_test():
    lgate = AND(1, 0)
    outputLogic = []

    inputLogic = [(0, 0), (1, 0), (1, 1), (0, 1)]

    for logic in inputLogic:
        lgate.setInputs(logic[0], logic[1])
        outputLogic.append(lgate.output())
    if outputLogic != [0, 0, 1, 0]:
        assert False

    lgate = AND(1, 0)
    try:
        lgate.addInput(1)
        if lgate.output() is not 0:
            assert False

        lgate.removeInput(1)
        if lgate.output() is not 1:
            assert False
    except Exception:
        assert False


def OR_test():
    lgate = OR(0, 0)
    outputLogic = []

    inputLogic = [(0, 0), (1, 0), (1, 1), (0, 1)]

    for logic in inputLogic:
        lgate.setInputs(logic[0], logic[1])
        outputLogic.append(lgate.output())
    if outputLogic != [0, 1, 1, 1]:
        assert False

    lgate = OR(1, 0)
    try:
        lgate.addInput(1)
        if lgate.output() is not 1:
            assert False

        lgate.removeInput(1)
        if lgate.output() is not 1:
            assert False
    except Exception:
        assert False


def NAND_test():
    lgate = NAND(0, 0)
    outputLogic = []

    inputLogic = [(0, 0), (1, 0), (1, 1), (0, 1)]

    for logic in inputLogic:
        lgate.setInputs(logic[0], logic[1])
        outputLogic.append(lgate.output())
    if outputLogic != [1, 1, 0, 1]:
        assert False

    lgate = NAND(1, 1)
    try:
        lgate.addInput(1)
        if lgate.output() is not 0:
            assert False

        lgate.removeInput(1)
        if lgate.output() is not 0:
            assert False
    except Exception:
        assert False


def NOR_test():
    lgate = NOR(0, 0)
    outputLogic = []

    inputLogic = [(0, 0), (1, 0), (1, 1), (0, 1)]

    for logic in inputLogic:
        lgate.setInputs(logic[0], logic[1])
        outputLogic.append(lgate.output())
    if outputLogic != [1, 0, 0, 0]:
        assert False

    lgate = NOR(1, 0)
    try:
        lgate.addInput(1)
        if lgate.output() is not 0:
            assert False

        lgate.removeInput(1)
        if lgate.output() is not 0:
            assert False
    except Exception:
        assert False


def XOR_test():
    lgate = XOR(0, 0)
    outputLogic = []

    inputLogic = [(0, 0), (1, 0), (1, 1), (0, 1)]

    for logic in inputLogic:
        lgate.setInputs(logic[0], logic[1])
        outputLogic.append(lgate.output())
    if outputLogic != [0, 1, 0, 1]:
        assert False

    lgate = XOR(1, 0)
    try:
        lgate.addInput(1)
        if lgate.output() is not 0:
            assert False

        lgate.removeInput(1)
        if lgate.output() is not 0:
            assert False
    except Exception:
        assert False


def XNOR_test():
    lgate = XNOR(0, 0)
    outputLogic = []

    inputLogic = [(0, 0), (1, 0), (1, 1), (0, 1)]

    for logic in inputLogic:
        lgate.setInputs(logic[0], logic[1])
        outputLogic.append(lgate.output())
    if outputLogic != [1, 0, 1, 0]:
        assert False

        lgate = XNOR(1, 0)
    try:
        lgate.addInput(1)
        if lgate.output() is not 1:
            assert False

        lgate.removeInput(1)
        if lgate.output() is not 0:
            assert False
    except Exception:
        assert False

########NEW FILE########
__FILENAME__ = operations_tests
from BinPy.Operations import *
from nose.tools import with_setup, nottest, assert_raises

op = Operations()


def ADD_test():
    if op.ADD(0, 1) != '1':
        assert False
    if op.ADD('0', '1') != '1':
        assert False

    if op.ADD('01', '10') != '11':
        assert False
    if op.ADD('110', '111') != '1101':
        assert False


def SUB_test():
    if op.SUB(0, 1) != '1':
        assert False
    if op.SUB('0', '1') != '1':
        assert False

    if op.SUB('10', '01') != '1':
        assert False
    if op.SUB('110', '111') != '1':
        assert False


def MUL_test():
    if op.MUL(0, 1) != '0':
        assert False
    if op.MUL('0', '1') != '0':
        assert False

    if op.MUL('10', '01') != '10':
        assert False
    if op.MUL('110', '111') != '101010':
        assert False


def DIV_test():
    if op.DIV(0, 1) != '0':
        assert False
    if op.DIV('0', '1') != '0':
        assert False

    if op.DIV('10', '01') != '10':
        assert False
    if op.DIV('110', '111') != '0':
        assert False


def COMP_test():
    if op.COMP(0, 1) != '1':
        assert False
    if op.COMP('0', '1') != '1':
        assert False

    if op.COMP('110', '1') != '001':
        assert False
    if op.COMP('100', '1') != '011':
        assert False
    if op.COMP('110', '2') != '110':
        assert False


def decToBin_test():
    if Operations.decToBin(10) != '1010':
        assert False
    if Operations.decToBin(11) != '1011':
        assert False
    if Operations.decToBin(15) != '1111':
        assert False
    if Operations.decToBin(1234) != '10011010010':
        assert False
    if Operations.decToBin(56789) != '1101110111010101':
        assert False
    if Operations.decToBin(13.9876) != '1101.1111110011010011010110101000010110000111100101':
        assert False
    if Operations.decToBin(13.00) != '1101':
        assert False


def binToDec_test():
    if Operations.binToDec('111') != 7:
        assert False
    if Operations.binToDec('0111') != 7:
        assert False
    if Operations.binToDec('10011010010') != 1234:
        assert False
    if Operations.binToDec('0001') != 1:
        assert False
    if Operations.binToDec('1010101') != 85:
        assert False
    if Operations.binToDec('1010101.1010101') != 85.6640625:
        assert False
    if Operations.binToDec([1, 0, 1, 0, 1, 0, 1]) != 85:
        assert False
    assert_raises(Exception, Operations.binToDec, '1010101.10101012')

########NEW FILE########
__FILENAME__ = print_tests
from BinPy.Gates.gates import *
from BinPy.Combinational.combinational import *

from nose.tools import with_setup, nottest
import re


def AND_print_test():
    gate = AND(0, 1)
    if not re.search("AND Gate; Output: 0; Inputs: \[0, 1];", gate.__str__()):
        assert False


def OR_print_test():
    gate = OR(0, 1)
    if not re.search("OR Gate; Output: 1; Inputs: \[0, 1];", gate.__str__()):
        assert False


def NOT_print_test():
    gate = NOT(1)
    if not re.search("NOT Gate; Output: 0; Inputs: \[1];", gate.__str__()):
        assert False


def XOR_print_test():
    gate = XOR(0, 1)
    if not re.search("XOR Gate; Output: 1; Inputs: \[0, 1];", gate.__str__()):
        assert False


def XNOR_print_test():
    gate = XNOR(0, 1)
    if not re.search("XNOR Gate; Output: 0; Inputs: \[0, 1];", gate.__str__()):
        assert False


def NAND_print_test():
    gate = NAND(0, 1)
    if not re.search("NAND Gate; Output: 1; Inputs: \[0, 1];", gate.__str__()):
        assert False


def NOR_print_test():
    gate = NOR(0, 1)
    if not re.search("NOR Gate; Output: 0; Inputs: \[0, 1];", gate.__str__()):
        assert False


def MUX_print_test():
    gate = MUX(1, 1)
    gate.selectLines(0)
    if not re.search("MUX Gate; Output: 1; Inputs: \[1, 1];", gate.__str__()):
        assert False


def DEMUX_print_test():
    gate = DEMUX(1)
    gate.selectLines(1)
    if not re.search("DEMUX Gate; Output: \[0, 1]; Inputs: \[1];", gate.__str__()):
        assert False


def Encoder_print_test():
    gate = Encoder(0, 0, 0, 1)
    if not re.search("Encoder Gate; Output: \[1, 1]; Inputs: \[0, 0, 0, 1];", gate.__str__()):
        assert False


def Decoder_print_test():
    gate = Decoder(0, 0)
    if not re.search("Decoder Gate; Output: \[1, 0, 0, 0]; Inputs: \[0, 0];", gate.__str__()):
        assert False

########NEW FILE########
__FILENAME__ = registers_tests
from BinPy import *
from nose.tools import with_setup, nottest


def test_FourBitRegister():

    clock = Clock(1, 500)
    clock.start()
    test_ffr = FourBitRegister(1, 0, 1, 0, clock, 1)

    assert test_ffr.output() == [1, 0, 1, 0]

    clock.kill()


def test_FourBitLoadRegister():

    clock = Clock(1, 500)
    clock.start()
    test_ffr = FourBitLoadRegister(1, 0, 1, 0, clock, 1, 1)

    assert test_ffr.output() == [1, 0, 1, 0]
    test_ffr.setLoad(0)

    assert test_ffr.output() == [1, 0, 1, 0]

    clock.kill()


def test_ShiftRegister():

    clock = Clock(1, 500)
    clock.start()
    test_ffr = ShiftRegister([1, 0, 0, 0], clock)

    assert test_ffr.output() == [1, 1, 0, 0]
    assert test_ffr.output() == [1, 1, 1, 0]
    assert test_ffr.output() == [1, 1, 1, 1]

    test_ffr = ShiftRegister([1, 0, 0, 0], clock, circular=1)

    assert test_ffr.output() == [0, 1, 0, 0]
    assert test_ffr.output() == [0, 0, 1, 0]
    assert test_ffr.output() == [0, 0, 0, 1]
    clock.kill()

########NEW FILE########
__FILENAME__ = sequential_ic_tests
from BinPy.ic import *
from nose.tools import with_setup, nottest

##########################
# IC's with 14 pins
##########################


def test_IC_7470():
    c = Clock(1, 500)
    c.start()
    testIC = IC_7470()
    p = {1: 1, 2: 1, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: c, 13: 0, 14: 1}
    testIC.setIC(p)
    q = {8: 1, 10: 0}
    if q != testIC.run():
        assert False
    p = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: c, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {8: 0, 10: 1}
    if q != testIC.run():
        assert False

    p = {1: 1, 2: 1, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: c, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {8: 0, 10: 1}
    if q != testIC.run():
        assert False

    c.kill()


def test_IC_7472():
    c = Clock(1, 500)
    c.start()
    testIC = IC_7472()
    p = {1: 1, 2: 1, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: c, 13: 0, 14: 1}
    testIC.setIC(p)
    q = {8: 1, 10: 0}
    if q != testIC.run():
        assert False
    p = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: c, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {8: 0, 10: 1}
    if q != testIC.run():
        assert False

    p = {1: 1, 2: 1, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: c, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {8: 0, 10: 1}
    if q != testIC.run():
        assert False

    c.kill()


def test_IC_7473():
    c1 = Clock(1, 500)
    c1.start()
    c2 = Clock(1, 500)
    c2.start()
    testIC = IC_7473()
    p = {1: c1, 2: 1, 4: 0, 5: c2, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}
    testIC.setIC(p)
    q = {8: 1, 9: 0, 12: 1, 13: 0}
    if q != testIC.run():
        assert False
    p = {1: c1, 2: 0, 4: 0, 5: c2, 7: 0, 9: 1, 10: 1, 12: 0, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {8: 1, 9: 0, 12: 0, 13: 1}
    if q != testIC.run():
        assert False

    p = {
        1: c1,
        2: 1,
        4: 0,
        5: c2,
        6: 1,
        7: 0,
        9: 1,
        10: 1,
        12: 0,
        13: 1,
        14: 1}
    testIC.setIC(p)
    q = {8: 1, 9: 0, 12: 1, 13: 0}
    if q != testIC.run():
        assert False

    c1.kill()
    c2.kill()


def test_IC_7474():
    c1 = Clock(1, 500)
    c1.start()
    c2 = Clock(1, 500)
    c2.start()
    testIC = IC_7474()
    p = {
        1: 1,
        2: 1,
        3: c1,
        4: 0,
        5: 0,
        7: 0,
        9: 1,
        10: 1,
        11: c2,
        13: 0,
        14: 1}
    testIC.setIC(p)
    q = {8: 1, 9: 0, 5: 1, 6: 0}
    if q != testIC.run():
        assert False
    p = {
        1: 1,
        2: 1,
        3: c1,
        4: 0,
        5: 0,
        7: 0,
        9: 1,
        10: 0,
        11: c2,
        13: 1,
        14: 1}
    testIC.setIC(p)
    q = {8: 0, 9: 1, 5: 1, 6: 0}
    if q != testIC.run():
        assert False

    p = {
        1: 1,
        2: 1,
        3: c1,
        4: 0,
        5: 0,
        7: 0,
        9: 1,
        10: 1,
        11: c2,
        13: 1,
        14: 1}
    testIC.setIC(p)
    q = {8: 1, 9: 0, 5: 1, 6: 0}
    if q != testIC.run():
        assert False

    c1.kill()
    c2.kill()


def test_IC_7475():
    c1 = Clock(1, 500)
    c1.start()
    c2 = Clock(1, 500)
    c2.start()
    testIC = IC_7475()
    p = {
        1: 1,
        2: 1,
        3: 0,
        4: c1,
        5: 1,
        7: 0,
        9: 1,
        10: 1,
        11: 0,
        12: 0,
        13: c2,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    q = {1: 0, 8: 1, 9: 0, 10: 0, 11: 1, 14: 1, 15: 0, 16: 1}
    if q != testIC.run():
        assert False

    p = {
        1: 1,
        2: 0,
        3: 0,
        4: c1,
        5: 1,
        7: 0,
        9: 1,
        10: 1,
        11: 0,
        12: 0,
        13: c2,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    q = {1: 1, 8: 1, 9: 0, 10: 0, 11: 1, 14: 1, 15: 0, 16: 0}
    if q != testIC.run():
        assert False

    p = {
        1: 1,
        2: 1,
        3: 0,
        4: c1,
        5: 1,
        7: 1,
        9: 0,
        10: 1,
        11: 0,
        12: 0,
        13: c2,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    q = {1: 0, 8: 0, 9: 1, 10: 0, 11: 1, 14: 1, 15: 0, 16: 1}
    if q != testIC.run():
        assert False

    c1.kill()
    c2.kill()


def test_IC_7476():
    c1 = Clock(1, 500)
    c1.start()
    c2 = Clock(1, 500)
    c2.start()
    testIC = IC_7476()
    p = {
        1: c1,
        2: 1,
        3: 0,
        4: 0,
        5: 1,
        6: c2,
        7: 0,
        8: 1,
        9: 1,
        10: 1,
        11: 0,
        12: 0,
        13: 0,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    q = {10: 0, 11: 1, 14: 1, 15: 0}
    if q != testIC.run():
        assert False

    p = {
        1: c1,
        2: 0,
        3: 1,
        4: 0,
        5: 1,
        6: c2,
        7: 0,
        8: 1,
        9: 1,
        10: 1,
        11: 0,
        12: 0,
        13: 0,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    q = {10: 0, 11: 1, 14: 0, 15: 1}
    if q != testIC.run():
        assert False

    p = {
        1: c1,
        2: 1,
        3: 0,
        4: 0,
        5: 1,
        6: c2,
        7: 1,
        8: 0,
        9: 1,
        10: 1,
        11: 0,
        12: 0,
        13: 0,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    q = {10: 1, 11: 0, 14: 1, 15: 0}
    if q != testIC.run():
        assert False

    c1.kill()
    c2.kill()

########NEW FILE########
__FILENAME__ = sequential_tests
from BinPy import *
from nose.tools import with_setup, nottest


def test_SRLatch():

    s = Connector(1)
    r = Connector(0)
    clock = Clock(1, 500)
    clock.start()
    test_SRLatch = SRLatch(s, r, Connector(1), clock.A)

    s.state, r.state = 1, 0
    while True:
        if clock.A.state == 0:
            test_SRLatch.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_SRLatch.trigger()
            break
    assert test_SRLatch.state() == [1, 0]

    s.state, r.state = 0, 1
    while True:
        if clock.A.state == 0:
            test_SRLatch.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_SRLatch.trigger()
            break
    assert test_SRLatch.state() == [0, 1]

    s.state, r.state = 1, 1
    while True:
        if clock.A.state == 0:
            test_SRLatch.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_SRLatch.trigger()
            break
    assert test_SRLatch.state() == [0, 1]

    s.state, r.state = 0, 0
    while True:
        if clock.A.state == 0:
            test_SRLatch.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_SRLatch.trigger()
            break
    assert test_SRLatch.state() == [0, 1]

    clock.kill()


def test_DFlipFlop():

    d = Connector(1)
    clock = Clock(1, 500)
    clock.start()
    test_DFF = DFlipFlop(d, Connector(1), clock.A)

    d.state = 1
    while True:
        if clock.A.state == 0:
            test_DFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_DFF.trigger()
            break
    assert test_DFF.state() == [1, 0]

    d.state = 0
    while True:
        if clock.A.state == 0:
            test_DFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_DFF.trigger()
            break
    assert test_DFF.state() == [0, 1]
    clock.kill()


def test_JKFlipFlop():

    j, k = Connector(0), Connector(0)

    clock = Clock(1, 500)
    clock.start()
    test_JKFF = JKFlipFlop(j, k, Connector(1), clock.A)

    j.state, k.state = 1, 0
    while True:
        if clock.A.state == 0:
            test_JKFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_JKFF.trigger()
            break
    assert test_JKFF.state() == [1, 0]

    j.state, k.state = 0, 1
    while True:
        if clock.A.state == 0:
            test_JKFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_JKFF.trigger()
            break
    assert test_JKFF.state() == [0, 1]

    j.state, k.state = 1, 1
    while True:
        if clock.A.state == 0:
            test_JKFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_JKFF.trigger()
            break
    assert test_JKFF.state() == [1, 0]

    j.state, k.state = 1, 1
    while True:
        if clock.A.state == 0:
            test_JKFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_JKFF.trigger()
            break
    assert test_JKFF.state() == [0, 1]

    j.state, k.state = 0, 0
    while True:
        if clock.A.state == 0:
            test_JKFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_JKFF.trigger()
            break
    assert test_JKFF.state() == [0, 1]

    clock.kill()


def test_TFlipFlop():

    t = Connector()
    clock = Clock(1, 500)
    clock.start()
    test_TFF = TFlipFlop(t, Connector(1), clock.A)

    t.state = 1
    while True:
        if clock.A.state == 0:
            test_TFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_TFF.trigger()
            break
    assert test_TFF.state() == [1, 0]

    t.state = 1
    while True:
        if clock.A.state == 0:
            test_TFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_TFF.trigger()
            break
    assert test_TFF.state() == [0, 1]

    t.state = 0
    while True:
        if clock.A.state == 0:
            test_TFF.trigger()
            break
    while True:
        if clock.A.state == 1:
            test_TFF.trigger()
            break
    assert test_TFF.state() == [0, 1]

    clock.kill()

########NEW FILE########
__FILENAME__ = series_4000_tests
from BinPy.ic import *
from nose.tools import with_setup, nottest

#################################
# IC's with 14 pins
#################################


def test_IC_4000():
    testIC = IC_4000()
    p = {3: 1, 4: 1, 5: 1, 7: 0, 8: 1, 11: 0, 12: 0, 13: 0, 14: 1}
    testIC.setIC(p)
    q = {6: 0, 9: 0, 10: 1}
    if q != testIC.run():
        assert False


def test_IC_4001():
    testIC = IC_4001()
    p = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {3: 1, 4: 0, 10: 0, 11: 0}
    if q != testIC.run():
        assert False


def test_IC_4002():
    testIC = IC_4002()
    p = {2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}
    testIC.setIC(p)
    q = {1: 1, 13: 0}
    if q != testIC.run():
        assert False


def test_IC_4011():
    testIC = IC_4011()
    p = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {3: 1, 4: 1, 10: 1, 11: 0}
    if q != testIC.run():
        assert False


def test_IC_4012():
    testIC = IC_4012()
    p = {2: 0, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}
    testIC.setIC(p)
    q = {1: 1, 13: 0}
    if q != testIC.run():
        assert False


def test_IC_4013():
    testIC = IC_4013()
    p = {
        1: 1,
        2: 0,
        3: 1,
        4: 0,
        5: 1,
        6: 1,
        7: 0,
        8: 0,
        9: 1,
        10: 1,
        11: 1,
        12: 1,
        13: 0,
        14: 1}
    c1 = Clock(1, 500)
    c1.start()
    c2 = Clock(1, 500)
    c2.start()
    p[3] = c1
    p[11] = c2

    testIC.setIC(p)
    assert testIC.run() == {1: 1, 2: 0, 12: 1, 13: 0}
    p[8] = 1
    testIC.setIC(p)
    assert testIC.run() == {1: 1, 2: 0, 12: 0, 13: 1}

    c1.kill()
    c2.kill()


def test_IC_4023():
    testIC = IC_4023()
    p = {1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 7: 0, 8: 1, 11: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {6: 1, 9: 0, 10: 1}
    if q != testIC.run():
        assert False


def test_IC_4025():
    testIC = IC_4025()
    p = {1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 7: 0, 8: 1, 11: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {6: 1, 9: 0, 10: 0}
    if q != testIC.run():
        assert False


def test_IC_4030():
    testIC = IC_4030()
    p = {1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 7: 0, 8: 1, 11: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {11: 0, 10: 1, 3: 0, 4: 0}
    if q != testIC.run():
        assert False


def test_IC_4068():
    testIC = IC_4068()
    p = {2: 1, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 0, 11: 1, 12: 1, 14: 1}
    testIC.setIC(p)
    q = {13: 1}
    if q != testIC.run():
        assert False


def test_IC_4069():
    testIC = IC_4069()
    p = {1: 0, 3: 1, 5: 1, 7: 0, 9: 0, 11: 0, 13: 0, 14: 1}
    testIC.setIC(p)
    q = {2: 1, 4: 0, 6: 0, 8: 1, 10: 1, 12: 1}
    if q != testIC.run():
        assert False


def test_IC_4070():
    testIC = IC_4070()
    p = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {3: 0, 4: 1, 10: 1, 11: 0}
    if q != testIC.run():
        assert False


def test_IC_4071():
    testIC = IC_4071()
    p = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {3: 0, 4: 1, 10: 1, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_4072():
    testIC = IC_4072()
    p = {2: 0, 3: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}
    testIC.setIC(p)
    q = {1: 0, 13: 1}
    if q != testIC.run():
        assert False


def test_IC_4073():
    testIC = IC_4073()
    p = {1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 7: 0, 8: 1, 11: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {6: 0, 9: 1, 10: 0}
    if q != testIC.run():
        assert False


def test_IC_4075():
    testIC = IC_4075()
    p = {1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 7: 0, 8: 1, 11: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {6: 0, 9: 1, 10: 1}
    if q != testIC.run():
        assert False


def test_IC_4077():
    testIC = IC_4077()
    p = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {3: 1, 4: 0, 10: 0, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_4078():
    testIC = IC_4078()
    p = {2: 1, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 0, 11: 1, 12: 1, 14: 1}
    testIC.setIC(p)
    q = {13: 0}
    if q != testIC.run():
        assert False


def test_IC_4081():
    testIC = IC_4081()
    p = {1: 0, 2: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {3: 0, 4: 0, 10: 0, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_4082():
    testIC = IC_4082()
    p = {2: 0, 3: 1, 4: 0, 5: 1, 7: 0, 9: 1, 10: 1, 11: 1, 12: 1, 14: 1}
    testIC.setIC(p)
    q = {1: 0, 13: 1}
    if q != testIC.run():
        assert False

#################################
# IC's with 16 pins
#################################


def test_IC_4008():
    testIC = IC_4008()
    p = {
        1: 1,
        2: 0,
        3: 1,
        4: 0,
        5: 1,
        6: 1,
        7: 0,
        8: 0,
        9: 1,
        10: 1,
        11: 1,
        12: 1,
        13: 0,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    q = {10: 0, 11: 0, 12: 0, 13: 0, 14: 1}
    if q != testIC.run():
        assert False


def test_IC_4009():
    testIC = IC_4009()
    p = {
        1: 1,
        2: 0,
        3: 1,
        4: 0,
        5: 1,
        6: 1,
        7: 0,
        8: 0,
        9: 1,
        10: 1,
        11: 1,
        12: 1,
        13: 0,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    q = {2: 0, 4: 0, 6: 1, 10: 0, 12: 0, 15: 0}
    if q != testIC.run():
        assert False


def test_IC_4010():
    testIC = IC_4010()
    p = {
        1: 1,
        2: 0,
        3: 1,
        4: 0,
        5: 1,
        6: 1,
        7: 0,
        8: 0,
        9: 1,
        10: 1,
        11: 1,
        12: 1,
        13: 0,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    q = {2: 1, 4: 1, 6: 0, 10: 1, 12: 1, 15: 1}
    if q != testIC.run():
        assert False


def test_IC_4015():
    testIC = IC_4015()
    c = Clock(1, 500)
    c.start()
    p = {
        1: c,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
        7: 1,
        8: 0,
        9: c,
        10: 0,
        11: 0,
        12: 0,
        13: 0,
        14: 0,
        15: 1,
        16: 1}
    testIC.setIC(p)

    assert testIC.run() == {2: 0, 3: 0, 4: 1, 5: 1, 10: 0, 11: 0, 12: 1, 13: 1}
    assert testIC.run() == {2: 0, 3: 1, 4: 1, 5: 1, 10: 0, 11: 1, 12: 1, 13: 1}
    assert testIC.run() == {2: 1, 3: 1, 4: 1, 5: 1, 10: 1, 11: 1, 12: 1, 13: 1}

    c.kill()


def test_IC_4017():
    testIC = IC_4017()
    c = Clock(1, 500)
    c.start()
    p = {8: 0, 16: 1, 13: c, 14: c, 15: 0}
    testIC.setIC(p)

    assert testIC.run() == {1: 0, 2: 0, 3: 1, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    assert testIC.run() == {1: 0, 2: 1, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 1, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 1, 11: 0, 12: 1}
    assert testIC.run() == {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            1, 10: 0, 11: 0, 12: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 1, 12: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 1, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    c.kill()


def test_IC_4019():
    testIC = IC_4019()
    p = {
        1: 1,
        2: 0,
        3: 1,
        4: 0,
        5: 1,
        6: 1,
        7: 0,
        8: 0,
        9: 1,
        10: 1,
        11: 1,
        12: 1,
        13: 0,
        14: 1,
        15: 0,
        16: 1}
    testIC.setIC(p)
    assert testIC.run() == {10: 1, 11: 1, 12: 1, 13: 1}


def test_IC_4020():
    testIC = IC_4020()
    c = Clock(1, 500)
    c.start()
    p = {8: 0, 16: 1, 10: c}
    testIC.setIC(p)

    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            1, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 1, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 1, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 1, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 1, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 1, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 1}
    assert testIC.run() == {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 1, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 1, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 12: 0, 13: 0, 14: 0, 15: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            1, 12: 0, 13: 0, 14: 0, 15: 0}
    c.kill()


def test_IC_4022():
    testIC = IC_4022()
    c = Clock(1, 500)
    c.start()
    p = {8: 0, 16: 1, 13: c, 14: c, 15: 0}
    testIC.setIC(p)

    assert testIC.run() == {1: 0, 2: 1, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    assert testIC.run() == {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    assert testIC.run() == {1: 0, 2: 0, 3: 1, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 1, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 1, 12: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 0}
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 1, 11: 0, 12: 0}
    assert testIC.run() == {1: 0, 2: 1, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9:
                            0, 10: 0, 11: 0, 12: 1}
    c.kill()


def test_IC_4027():
    clk = Clock(1, 500)
    clk.start()
    testIC = IC_4027()
    p = {
        1: 0,
        2: 0,
        3: clk,
        4: 1,
        5: 0,
        6: 0,
        7: 1,
        8: 0,
        9: 1,
        10: 0,
        11: 0,
        12: 1,
        13: clk,
        14: 0,
        15: 0,
        16: 1}
    testIC.setIC(p)
    assert testIC.run() == {1: 0, 2: 1, 14: 1, 15: 0}
    p = {
        1: 0,
        2: 0,
        3: clk,
        4: 0,
        5: 0,
        6: 0,
        7: 1,
        8: 0,
        9: 1,
        10: 0,
        11: 0,
        12: 0,
        13: clk,
        14: 0,
        15: 0,
        16: 1}
    testIC.setIC(p)
    assert testIC.run() == {1: 1, 2: 0, 14: 0, 15: 1}
    p = {
        1: 0,
        2: 0,
        3: clk,
        4: 1,
        5: 0,
        6: 0,
        7: 0,
        8: 0,
        9: 0,
        10: 0,
        11: 0,
        12: 1,
        13: clk,
        14: 0,
        15: 0,
        16: 1}
    testIC.setIC(p)
    assert testIC.run() == {1: 0, 2: 1, 14: 1, 15: 0}
    clk.kill()


def test_IC_2028():
    testIC = IC_4028()
    p = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
        7: 0,
        8: 0,
        9: 1,
        10: 0,
        11: 0,
        12: 0,
        13: 0,
        14: 0,
        15: 0,
        16: 1}
    testIC.setIC(p)
    assert testIC.run() == {1: 0, 2: 0, 3: 1, 4: 0, 5: 0, 6: 0, 7: 0, 9: 0, 14:
                            0, 15: 0}
    p[10] = 1
    testIC.setIC(p)
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 9: 1, 14:
                            0, 15: 0}
    p[11] = 1
    testIC.setIC(p)
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 0, 7: 0, 9: 0,
                            14: 0, 15: 0}

    p[12] = 1
    testIC.setIC(p)
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 9: 0,
                            14: 0, 15: 0}

    p[13] = 1
    testIC.setIC(p)
    assert testIC.run() == {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 9: 0,
                            14: 0, 15: 0}


def test_IC_4029():
    clk = Clock(1, 500)
    clk.start()

    p = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
        7: 0,
        8: 0,
        9: 0,
        10: 0,
        11: 0,
        12: 0,
        13: 0,
        14: 0,
        15: clk,
        16: 1}
    testIC = IC_4029()
    testIC.setIC(p)

    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 1, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 1, 14: 0, 6: 0}
    assert testIC.run() == {2: 0, 11: 1, 14: 0, 6: 0}
    assert testIC.run() == {2: 1, 11: 0, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 0, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 0}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 0}
    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 1, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 1, 14: 0, 6: 0}

    p = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
        7: 0,
        8: 0,
        9: 0,
        10: 1,
        11: 0,
        12: 0,
        13: 0,
        14: 0,
        15: clk,
        16: 1}
    testIC.setIC(p)
    assert testIC.run() == {2: 0, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 0}
    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 0}
    assert testIC.run() == {2: 0, 11: 0, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 0, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 1, 14: 0, 6: 0}
    assert testIC.run() == {2: 1, 11: 1, 14: 0, 6: 0}
    assert testIC.run() == {2: 0, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 0}

    p = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
        7: 0,
        8: 0,
        9: 1,
        10: 1,
        11: 0,
        12: 0,
        13: 0,
        14: 0,
        15: clk,
        16: 1}
    testIC.setIC(p)
    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 0}
    assert testIC.run() == {2: 0, 11: 0, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 0, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 1, 14: 0, 6: 0}
    assert testIC.run() == {2: 1, 11: 1, 14: 0, 6: 0}
    assert testIC.run() == {2: 0, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 0, 11: 0, 14: 1, 6: 1}
    assert testIC.run() == {2: 1, 11: 0, 14: 1, 6: 1}
    assert testIC.run() == {2: 0, 11: 1, 14: 0, 6: 1}
    assert testIC.run() == {2: 1, 11: 1, 14: 0, 6: 1}
    assert testIC.run() == {2: 0, 11: 1, 14: 1, 6: 1}
    assert testIC.run() == {2: 1, 11: 1, 14: 1, 6: 1, 7: 1}

    p = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
        7: 0,
        8: 0,
        9: 1,
        10: 0,
        11: 0,
        12: 0,
        13: 0,
        14: 0,
        15: clk,
        16: 1}
    testIC.setIC(p)
    assert testIC.run() == {2: 0, 11: 1, 14: 1, 6: 1}
    assert testIC.run() == {2: 1, 11: 1, 14: 0, 6: 1}
    assert testIC.run() == {2: 0, 11: 1, 14: 0, 6: 1}
    assert testIC.run() == {2: 1, 11: 0, 14: 1, 6: 1}
    assert testIC.run() == {2: 0, 11: 0, 14: 1, 6: 1}
    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 1}
    assert testIC.run() == {2: 1, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 1, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 1, 14: 0, 6: 0}
    assert testIC.run() == {2: 0, 11: 1, 14: 0, 6: 0}
    assert testIC.run() == {2: 1, 11: 0, 14: 1, 6: 0}
    assert testIC.run() == {2: 0, 11: 0, 14: 1, 6: 0}
    assert testIC.run() == {2: 1, 11: 0, 14: 0, 6: 0}
    assert testIC.run() == {2: 0, 11: 0, 14: 0, 6: 0, 7: 0}

    clk.kill()

########NEW FILE########
__FILENAME__ = series_7400_tests
from BinPy.ic import *
from nose.tools import with_setup, nottest

#################################
# IC's with 14 pins
#################################


def test_IC_7400():
    testIC = IC_7400()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}
    testIC.setIC(p)
    q = {3: 1, 6: 1, 8: 0, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_7401():
    testIC = IC_7401()
    p = {2: 0, 3: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 1, 11: 1, 12: 1, 14: 1}
    testIC.setIC(p)
    q = {1: 1, 4: 1, 10: 0, 13: 0}
    if q != testIC.run():
        assert False


def test_IC_7402():
    testIC = IC_7402()
    p = {2: 0, 3: 0, 5: 0, 6: 1, 7: 0, 8: 1, 9: 1, 11: 1, 12: 1, 14: 1}
    testIC.setIC(p)
    q = {1: 1, 4: 0, 10: 0, 13: 0}
    if q != testIC.run():
        assert False


def test_IC_7403():
    testIC = IC_7403()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}
    testIC.setIC(p)
    q = {3: 1, 6: 1, 8: 0, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_7404():
    testIC = IC_7404()
    p = {1: 1, 3: 0, 5: 0, 7: 0, 9: 0, 11: 0, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {2: 0, 4: 1, 6: 1, 8: 1, 10: 1, 12: 0}
    if q != testIC.run():
        assert False


def test_IC_7405():
    testIC = IC_7405()
    p = {1: 1, 3: 0, 5: 0, 7: 0, 9: 0, 11: 0, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {2: 0, 4: 1, 6: 1, 8: 1, 10: 1, 12: 0}
    if q != testIC.run():
        assert False


def test_IC_7408():
    testIC = IC_7408()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 7: 0, 9: 1, 10: 1, 12: 0, 13: 0, 14: 1}
    testIC.setIC(p)
    q = {3: 0, 6: 0, 8: 1, 11: 0}
    if q != testIC.run():
        assert False


def test_IC_7410():
    testIC = IC_7410()
    p = {1: 1, 2: 0, 13: 0, 3: 0, 4: 0, 5: 0, 9: 1, 10: 1, 11: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {12: 1, 6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7411():
    testIC = IC_7411()
    p = {1: 1, 2: 0, 13: 0, 3: 0, 4: 0, 5: 0, 9: 1, 10: 1, 11: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {12: 0, 6: 0, 8: 1}
    if q != testIC.run():
        assert False


def test_IC_7412():
    testIC = IC_7412()
    p = {1: 1, 2: 0, 13: 0, 3: 0, 4: 0, 5: 0, 9: 1, 10: 1, 11: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {12: 1, 6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7413():
    testIC = IC_7413()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7415():
    testIC = IC_7415()
    p = {1: 1, 2: 0, 13: 0, 3: 0, 4: 0, 5: 0, 9: 1, 10: 1, 11: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {12: 0, 6: 0, 8: 1}
    if q != testIC.run():
        assert False


def test_IC_7416():
    testIC = IC_7416()
    p = {1: 1, 2: 0, 13: 0, 3: 0, 4: 0, 5: 0, 9: 1, 10: 1, 11: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {2: 0, 4: 1, 6: 1, 8: 0, 10: 0, 12: 1}
    if q != testIC.run():
        assert False


def test_IC_7417():
    testIC = IC_7417()
    p = {1: 1, 2: 0, 13: 0, 3: 0, 4: 0, 5: 0, 9: 1, 10: 1, 11: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {2: 1, 4: 0, 6: 0, 8: 1, 10: 1, 12: 0}
    if q != testIC.run():
        assert False


def test_IC_7418():
    testIC = IC_7418()
    p = {
        1: 1,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        9: 1,
        10: 1,
        11: 1,
        12: 1,
        13: 1,
        14: 1,
        7: 0}
    testIC.setIC(p)
    q = {6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7419():
    testIC = IC_7419()
    p = {1: 1, 2: 0, 13: 0, 3: 0, 4: 0, 5: 0, 9: 1, 10: 1, 11: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {2: 0, 4: 1, 6: 1, 8: 0, 10: 0, 12: 1}
    if q != testIC.run():
        assert False


def test_IC_7420():
    testIC = IC_7420()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7421():
    testIC = IC_7421()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {6: 0, 8: 1}
    if q != testIC.run():
        assert False


def test_IC_7422():
    testIC = IC_7422()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7424():
    testIC = IC_7424()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {3: 1, 6: 1, 8: 0, 11: 0}
    if q != testIC.run():
        assert False


def test_IC_7425():
    testIC = IC_7425()
    p = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        9: 1,
        10: 1,
        11: 1,
        12: 1,
        13: 1,
        14: 1,
        7: 0}
    testIC.setIC(p)
    q = {6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7426():
    testIC = IC_7426()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {3: 1, 6: 1, 8: 0, 11: 0}
    if q != testIC.run():
        assert False


def test_IC_7427():
    testIC = IC_7427()
    p = {1: 1, 2: 0, 3: 0, 4: 0, 5: 0, 9: 1, 10: 1, 11: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {6: 1, 8: 0, 12: 0}
    if q != testIC.run():
        assert False


def test_IC_7428():
    testIC = IC_7428()
    p = {2: 0, 3: 0, 5: 0, 6: 1, 8: 1, 9: 1, 11: 1, 12: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {1: 1, 4: 0, 10: 0, 13: 0}
    if q != testIC.run():
        assert False


def test_IC_7430():
    testIC = IC_7430()
    p = {1: 0, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 11: 1, 12: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {8: 1}
    if q != testIC.run():
        assert False


def test_IC_7432():
    testIC = IC_7432()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {3: 1, 6: 0, 8: 1, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_7433():
    testIC = IC_7433()
    p = {2: 0, 3: 0, 5: 0, 6: 0, 8: 1, 9: 1, 11: 1, 12: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {1: 1, 4: 1, 10: 0, 13: 0}
    if q != testIC.run():
        assert False


def test_IC_7437():
    testIC = IC_7437()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {3: 1, 6: 1, 8: 0, 11: 0}
    if q != testIC.run():
        assert False


def test_IC_7438():
    testIC = IC_7438()
    m = {1: 1, 2: 1, 4: 0, 5: 0, 7: 0, 9: 0, 10: 0, 12: 0, 13: 1, 14: 1}
    testIC.setIC(m)
    n = {3: 0, 6: 1, 8: 1, 11: 1}
    if n != testIC.run():
        assert False


def test_IC_7440():
    testIC = IC_7440()
    p = {1: 1, 2: 0, 4: 0, 5: 0, 9: 1, 10: 1, 12: 1, 13: 1, 14: 1, 7: 0}
    testIC.setIC(p)
    q = {6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7451():
    testIC = IC_7451()
    p = {
        2: 1,
        3: 0,
        4: 0,
        5: 0,
        7: 0,
        1: 1,
        13: 1,
        12: 1,
        11: 0,
        10: 0,
        9: 0,
        14: 1}
    testIC.setIC(p)
    q = {6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7454():
    testIC = IC_7454()
    p = {
        1: 1,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        7: 0,
        10: 1,
        9: 1,
        11: 0,
        12: 0,
        13: 0,
        14: 1}
    testIC.setIC(p)
    q = {6: 1}
    if q != testIC.run():
        assert False


def test_IC_7455():
    testIC = IC_7455()
    p = {1: 1, 2: 0, 3: 0, 4: 0, 7: 0, 10: 1, 9: 1, 11: 0, 12: 0, 13: 0, 14: 1}
    testIC.setIC(p)
    q = {8: 1}
    if q != testIC.run():
        assert False


def test_IC_7458():
    testIC = IC_7458()
    p = {
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        7: 0,
        1: 1,
        13: 1,
        12: 1,
        11: 0,
        10: 0,
        9: 0,
        14: 1}
    testIC.setIC(p)
    q = {6: 0, 8: 1}
    if q != testIC.run():
        assert False


def test_IC_7459():
    testIC = IC_7459()
    p = {
        14: 1,
        7: 0,
        2: 1,
        3: 0,
        4: 0,
        5: 1,
        1: 1,
        13: 1,
        12: 1,
        11: 1,
        10: 1,
        9: 1}
    testIC.setIC(p)
    q = {6: 1, 8: 0}
    if q != testIC.run():
        assert False


def test_IC_7464():
    testIC = IC_7464()
    p = {1: 1, 7: 0, 13: 1, 12: 1, 11: 1, 14: 1}
    testIC.setIC(p)
    q = {8: 0}
    if q != testIC.run():
        assert False


def test_IC_7486():
    testIC = IC_7486()
    p = {1: 0, 2: 0, 4: 0, 5: 1, 7: 0, 9: 1, 10: 0, 12: 1, 13: 1, 14: 1}
    testIC.setIC(p)
    q = {3: 0, 6: 1, 8: 1, 11: 0}
    if q != testIC.run():
        assert False


def test_IC_74260():
    testIC = IC_74260()
    p = {
        1: 0,
        2: 0,
        3: 0,
        4: 1,
        7: 0,
        8: 0,
        9: 0,
        10: 0,
        11: 0,
        12: 0,
        13: 0,
        14: 1}
    testIC.setIC(p)
    q = {5: 1, 6: 0}
    if q != testIC.run():
        assert False


def test_IC_74152():
    testIC = IC_74152()
    m = {
        1: 1,
        2: 0,
        3: 1,
        4: 0,
        5: 1,
        7: 0,
        8: 0,
        9: 0,
        10: 1,
        11: 1,
        12: 0,
        13: 0,
        14: 1}
    testIC.setIC(m)
    n = {6: 1}
    if n != testIC.run():
        assert False

#################################
# IC's with 5 pins
#################################


def test_IC_741G00():
    testIC = IC_741G00()
    p = {1: 1, 2: 0, 3: 0, 5: 1}
    testIC.setIC(p)
    q = {4: 1}
    if q != testIC.run():
        assert False


def test_IC_741G02():
    testIC = IC_741G02()
    p = {1: 1, 2: 0, 3: 0, 5: 1}
    testIC.setIC(p)
    q = {4: 0}
    if q != testIC.run():
        assert False


def test_IC_741G03():
    testIC = IC_741G03()
    p = {1: 1, 2: 0, 3: 0, 5: 1}
    testIC.setIC(p)
    q = {4: 1}
    if q != testIC.run():
        assert False


def test_IC_741G04():
    testIC = IC_741G04()
    p = {2: 0, 3: 0, 5: 1}
    testIC.setIC(p)
    q = {4: 1}
    if q != testIC.run():
        assert False


def test_IC_741G05():
    testIC = IC_741G05()
    p = {2: 1, 3: 0, 5: 1}
    testIC.setIC(p)
    q = {4: 0}
    if q != testIC.run():
        assert False


def test_IC_741G08():
    testIC = IC_741G08()
    p = {1: 1, 2: 0, 3: 0, 5: 1}
    testIC.setIC(p)
    q = {4: 0}
    if q != testIC.run():
        assert False

#################################
# IC's with 16 pins
#################################


def test_IC_7431():
    testIC = IC_7431()
    p = {1: 1, 5: 0, 6: 0, 15: 1, 10: 1, 11: 1, 3: 1, 13: 0, 8: 0, 16: 1}
    testIC.setIC(p)
    q = {2: 0, 7: 1, 14: 0, 9: 0, 4: 1, 12: 0}
    if q != testIC.run():
        assert False


def test_IC_7442():
    testIC = IC_7442()
    p = {15: 1, 14: 0, 13: 0, 12: 0, 8: 0, 16: 1}
    testIC.setIC(p)
    q = {1: 1, 2: 0, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 9: 1, 10: 1, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_7443():
    testIC = IC_7443()
    p = {15: 1, 14: 0, 13: 1, 12: 0, 8: 0, 16: 1}
    testIC.setIC(p)
    q = {1: 1, 2: 1, 3: 0, 4: 1, 5: 1, 6: 1, 7: 1, 9: 1, 10: 1, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_7444():
    testIC = IC_7444()
    p = {15: 1, 14: 0, 13: 1, 12: 0, 8: 0, 16: 1}
    testIC.setIC(p)
    q = {1: 1, 2: 1, 3: 1, 4: 0, 5: 1, 6: 1, 7: 1, 9: 1, 10: 1, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_7445():
    testIC = IC_7445()
    p = {15: 0, 14: 1, 13: 0, 12: 0, 8: 0, 16: 1}
    testIC.setIC(p)
    q = {1: 1, 2: 1, 3: 0, 4: 1, 5: 1, 6: 1, 7: 1, 9: 1, 10: 1, 11: 1}
    if q != testIC.run():
        assert False


def test_IC_74133():
    testIC = IC_74133()
    p = {
        1: 0,
        2: 1,
        3: 1,
        4: 1,
        5: 1,
        6: 1,
        7: 1,
        8: 0,
        9: 1,
        10: 1,
        12: 1,
        13: 1,
        14: 1,
        15: 1,
        16: 1}
    testIC.setIC(p)
    q = {9: 1}
    if q != testIC.run():
        assert False


def test_IC_7483():
    testIC = IC_7483()
    p = {1: 1, 3: 0, 4: 0, 5: 1, 7: 1, 8: 0, 10: 1, 11: 1, 12: 0, 13: 1, 16: 1}
    testIC.setIC(p)
    q = {9: 1, 2: 1, 14: 1, 6: 0, 15: 0}
    if q != testIC.run():
        assert False


def test_IC_74151A():
    testIC = IC_74151A()
    m = {
        1: 1,
        2: 0,
        4: 1,
        3: 1,
        7: 0,
        8: 0,
        9: 0,
        10: 0,
        11: 0,
        12: 0,
        13: 0,
        14: 1,
        15: 1,
        16: 1}
    testIC.setIC(m)
    n = {5: 1, 6: 0}
    if n != testIC.run():
        assert False


def test_IC_74153():
    testIC = IC_74153()
    m = {
        1: 1,
        2: 1,
        3: 1,
        4: 0,
        5: 0,
        6: 0,
        8: 0,
        10: 0,
        11: 1,
        12: 0,
        13: 0,
        14: 0,
        15: 0,
        16: 1}
    testIC.setIC(m)
    n = {7: 0, 9: 0}
    if n != testIC.run():
        assert False


def test_IC_74156():
    testIC = IC_74156()
    m = {1: 1, 2: 0, 3: 0, 13: 1, 8: 0, 16: 1, 15: 1, 14: 0}
    testIC.setIC(m)
    n = {12: 1, 11: 1, 10: 1, 9: 1, 7: 1, 6: 0, 5: 1, 4: 1}
    if n != testIC.run():
        assert False


def test_IC_74155():
    testIC = IC_74155()
    m = {1: 1, 2: 0, 3: 1, 13: 0, 8: 0, 16: 1, 15: 1, 14: 0}
    testIC.setIC(m)
    n = {12: 1, 11: 1, 10: 1, 9: 1, 7: 1, 6: 1, 5: 0, 4: 1}
    if n != testIC.run():
        assert False


def test_IC_74139():
    testIC = IC_74139()
    m = {1: 0, 2: 0, 3: 0, 8: 0, 14: 0, 13: 1, 15: 0, 16: 1}
    testIC.setIC(m)
    n = {4: 0, 5: 1, 6: 1, 7: 1, 9: 1, 10: 0, 11: 1, 12: 1}
    if n != testIC.run():
        assert False


def test_IC_74138():
    testIC = IC_74138()
    m = {1: 1, 2: 0, 3: 1, 4: 0, 5: 0, 6: 1, 8: 0, 16: 1}
    testIC.setIC(m)
    n = {15: 1, 14: 1, 13: 1, 12: 1, 11: 1, 10: 0, 9: 1, 7: 1}
    if n != testIC.run():
        assert False

########NEW FILE########
__FILENAME__ = source_tests
from BinPy.Gates import *
from BinPy.tools import *
from nose.tools import with_setup, nottest


def test_PowerSourceTest():
    POW = PowerSource()
    a = Connector()

    POW.connect(a)
    if a.state != 1:
        assert False

    POW.disconnect(a)
    if a.state is not None:
        assert False


def test_GroundTest():
    GND = Ground()
    a = Connector()

    GND.connect(a)
    if a.state != 0:
        assert False

    GND.disconnect(a)
    if a.state is not None:
        assert False

########NEW FILE########
__FILENAME__ = test_makebooleanfunction
import sys
from BinPy import *
from nose.tools import with_setup, nottest


def test_make_booelan():
    a, b = make_boolean(['A', 'B', 'C', 'D'], [1, 5, 7], minterms=True)
    assert a == '((A AND C AND (NOT D)) OR (A AND (NOT B) AND (NOT D)))'
    assert b == 'OR(AND(A, C, NOT(D)), AND(A, NOT(B), NOT(D)))'
    a, b = make_boolean(['A', 'B', 'C', 'D'], [1, 5, 7], maxterms=True)
    if not sys.version_info > (3, 4):
        assert a == '((NOT A) OR D OR (B AND (NOT C)))'
        assert b == 'OR(NOT(A), D, AND(B, NOT(C)))'

########NEW FILE########
__FILENAME__ = tree_tests
from __future__ import print_function
from BinPy.Gates.tree import *
from BinPy.Gates.gates import *
from BinPy.Gates.connector import *
from BinPy.Combinational.combinational import *

from nose.tools import with_setup, nottest

'''
Testing backtrack() function for depths from 0 to 4.
'''


def getTreeForDepthTesting(depth):
    # Gates for depth test
    g1 = AND(True, False)
    g2 = AND(True, False)
    g3 = AND(g1, g2)

    g4 = AND(True, False)
    g5 = AND(True, False)
    g6 = AND(g4, g5)

    g_final = AND(g3, g6)

    # Instance of Tree
    tree_inst = Tree(g_final, depth)
    tree_inst.backtrack()

    # Testing tree
    n1 = (g1, [True, False])
    n2 = (g2, [True, False])
    n4 = (g4, [True, False])
    n5 = (g5, [True, False])

    n3 = (g3, [n1, n2])
    n6 = (g6, [n4, n5])
    tree_testing = (g_final, [n3, n6])

    return tree_inst, tree_testing


def compareTrees(tree_inst, tree_testing, depth):
    if isinstance(tree_testing, tuple):
        if not tree_testing[0] == tree_inst.element:
            assert False

        if depth == 0:
            if len(tree_inst.sons) != 0:
                assert False
        else:
            for i in range(len(tree_testing[1])):
                compareTrees(tree_inst.sons[i], tree_testing[1][i], depth - 1)

    else:
        if not tree_testing == tree_inst.element:
            assert False


def backtrack_depth_test():
    for i in range(6):
        tree_inst, tree_testing = getTreeForDepthTesting(i)
        compareTrees(tree_inst, tree_testing, i)

'''
Test to see if the setDepth method works
'''


def set_depth_test():
    tree_inst, tree_testing = getTreeForDepthTesting(0)

    for i in range(1, 6):
        tree_inst.setDepth(i)
        tree_inst.backtrack()
        compareTrees(tree_inst, tree_testing, i)

'''
Test not following Cycles functionality
'''


def not_following_cycles_test():
    c1 = Connector(True)
    g1 = AND(c1, True)
    g2 = AND(g1, False)
    g2.setOutput(c1)

    t_no_cycle = Tree(g2, 5, False)
    t_cycle = Tree(g2, 5, True)

    t_no_cycle.backtrack()
    t_cycle.backtrack()

    assert t_no_cycle.sons[0].sons[0].sons[0].sons == []
    assert t_cycle.sons[0].sons[0].sons[0].sons[0].element == g1

########NEW FILE########
__FILENAME__ = clock
import sys
import time
import threading
from BinPy import Connector


class Clock(threading.Thread):

    """
    This class uses threading technique to create a clock with a certain time period.
    This is how you can create a clock with this class:
        >>> myClock = Clock(0,time_period=2,name="My First Clock")
        >>> myClock.start()     #Do not call run method
        >>> myClock.getState()
        0

    Note: Once you are done with the clock, use myClock.kill() to kill the clock.
          Running too many clocks will unnecessarily overload the CPU.

    Following are the parameters of the class

        :param frequency:   It will decide time interval of the clock, use SI unit i.e. Hertz
        :param time_period: It will also decide time interval of the clock, use SI unit i.e. second
        :param init_state:  It is the initial state of the clock(1 by default)
        :param name:        It is the name of the clock.(optional)

        If time_period and frequency both have been provided, then time_period
        will override frequency
        If nothing is provided, then it will set time_period = 1s by default
    Methods :   start(), getState(), setState(value), getName(), getTimePeriod(), kill()
    """

    def __init__(
            self,
            init_state=1,
            frequency=None,
            time_period=None,
            name=None):
        threading.Thread.__init__(self)
        if frequency is not None:
            self.time_period = 1.0 / frequency
        if time_period is not None:
            self.time_period = time_period
        if time_period is None and frequency is None:
            self.time_period = 1

        self.init_state = init_state
        self.name = name
        self.curr_state = init_state
        self.exitFlag = 0
        self.daemon = True
        self.A = Connector(0)
        # self.A.trigger()

    def __toggleState(self):
        """
        This is an internal method to toggle the state of the output
        """
        if self.curr_state == 1:
            self.curr_state = 0
            self.A.state = self.curr_state
            # self.A.trigger()
        else:
            self.curr_state = 1
            self.A.state = self.curr_state
            # self.A.trigger()

    def __main_func(self):
        while True:
            if self.exitFlag:
                sys.exit()
            time.sleep(self.time_period)
            try:
                self.__toggleState()
            except:
                pass

    def getState(self):
        """
        Returns the current state of the clock
        """
        return self.curr_state

    def setState(self, value):
        """
        Resets the state of the clock to the passed value
        """
        if self.curr_state == value:
            return
        self.curr_state = value
        self.A.state = self.curr_state
        # self.A.trigger()

    def getTimePeriod(self):
        """
        Returns the time period of the clock
        """
        return self.time_period

    def getName(self):
        """
        Returns the name of the clock
        """
        return self.name

    def kill(self):
        """
        Kills the clock(Thread)
        """
        self.exitFlag = 1

    def run(self):
        self.__main_func()

########NEW FILE########
__FILENAME__ = digital
class DigitDisplay:

    '''
    This class emulates a 7 segmented display(Common Cathode)

    Parameters:
        name:   A name given to an object(Optional)

    Methods:
        evaluate()
        getName()

    How to use:
        >>> myDisplay = DigitDisplay("Display1")
        >>> print myDisplay.evaluate([1,1,1,1,1,1,1])
        8
    Note:
        You can either pass complete list of 10 pins [pin1, pin2, pin3,
        pin4, pin5, pin6, pin7, pin8, pin9, pin10] in standard order or
        you can directly pass the list of values corresponding to a, b,
        c, d, e, f and g in lexicographical order.

    Reference
    =========

    http://tronixstuff.files.wordpress.com/2010/05/7segpinout.jpg
    '''

    def __init__(self, name=None):
        self.name = name

    def evaluate(self, pin_conf):
        '''
        This method evaluates the values passed according to the display and returns
        an integer varying from 0 to 9
        '''
        if len(pin_conf) != 10:
            if len(pin_conf) != 7:
                raise Exception("There must be 10 or 7 values")
        if len(pin_conf) == 10:
            vcc = pin_conf[2] or pin_conf[7]
            a = pin_conf[6]
            b = pin_conf[5]
            c = pin_conf[3]
            d = pin_conf[1]
            e = pin_conf[0]
            f = pin_conf[8]
            g = pin_conf[9]
        if len(pin_conf) == 7:
            a = pin_conf[0]
            b = pin_conf[1]
            c = pin_conf[2]
            d = pin_conf[3]
            e = pin_conf[4]
            f = pin_conf[5]
            g = pin_conf[6]
            vcc = 1
        if vcc:
            test = [a, b, c, d, e, f, g]
            data = {
                '0': [1, 1, 1, 1, 1, 1, 0],
                '1': [0, 1, 1, 0, 0, 0, 0],
                '2': [1, 1, 0, 1, 1, 0, 1],
                '3': [1, 1, 1, 1, 0, 0, 1],
                '4': [0, 1, 1, 0, 0, 1, 1],
                '5': [1, 0, 1, 1, 0, 1, 1],
                '6': [1, 0, 1, 1, 1, 1, 1],
                '7': [1, 1, 1, 0, 0, 0, 0],
                '8': [1, 1, 1, 1, 1, 1, 1],
                '9': [1, 1, 1, 1, 0, 1, 1]}
            for i in data:
                if test == data[i]:
                    return int(i)
            print ('Not a valid combination')
            return None
        else:
            return None

        def getName(self):
            return self.name

########NEW FILE########
__FILENAME__ = ground
from BinPy.Gates import *


class Ground:

    """Models a Ground from which various connectors can tap by connecting to it.
    taps: The list of all connectors connected to this ground.
    connect(): Takes in one or more connectors as input and connects them to the ground.
    disconnect(): Takes in one or more connectors as input and disconnects them from the ground."""

    def __init__(self):
        self.taps = []

    def connect(self, *connectors):
        """Takes in one or more connectors as an input and taps to the ground."""
        for connector in connectors:
            if not isinstance(connector, Connector):
                raise Exception("Error: Input given is not a connector")
            else:
                if len(connector.connections['output']) != 0:
                    raise Exception(
                        "ERROR: The connector is already an output of some other object")
                self.taps.append(connector)
                connector.state = 0
                connector.tap(self, 'output')
                connector.trigger()

    def disconnect(self, *connectors):
        """Takes in one or more connectors as an input and disconnects them from the ground.
        A floating connector has a value of None.
        A message is printed if a specified connector is not already tapping from this ground."""

        for connector in connectors:
            if isinstance(connector, Connector):
                try:
                    self.taps.remove(connector)
                    connector.state = None
                    connector.connections['output'].remove(self)
                    connector.trigger()
                except:
                    print (
                        "The specified connector is not tapped to this ground")
            else:
                raise Exception("Error: Input given is not a connector")

########NEW FILE########
__FILENAME__ = multivibrator
import sys
import time
import threading
from BinPy import Connector


class Multivibrator(threading.Thread):

    """
    This class uses threading technique to create a multivibrator with a certain time period.
    USAGE:
        >>> m1 = Multivibrator()
        >>> m1.start()     # Start this thread
        >>> m1.trigger()   # or m1()
        >>> m1.getState()  # or m1.A.state
        0
        >>> m1.setMode(2)
        >>> m1.trigger()
        >>> m1.getstate()
        >>> conn = Connector()
        >>> m1.setOutput(conn) # To set the output to connector conn
        >>> conn()             # Retrieves the current state

    Note: Once you are done with the multivibrator, use m1.kill() to kill the Multivibrators.
        >>> m1.kill()

    Following are the parameters of the class

        frequency:      It will decide time interval of the Multivibrator, use SI unit i.e. Hertz
        time_period:    It will also decide time interval of the Multivibrator, use SI unit i.e. second

        If time_period and frequency both have been provided, then time_period will override frequency
        If nothing is provided, then it will set time_period = 1s by default

        init_state:     It is the initial state of the multivibrator(1 by default)

        mode:           It is the mode of operation.
                        1 --> Monostable
                        2 --> Astable
                        3 --> Bistable

    Methods :   trigger(),setMode(), getState(), setState(value), getTimePeriod(), kill(), stop(), setOutput()
    """

    def __init__(
            self,
            init_state=1,
            mode=1,
            frequency=None,
            time_period=None,
            on_time=None,
            off_time=None):

        threading.Thread.__init__(self)

        if frequency is not None:
            self.time_period = 1.0 / frequency
        if time_period is not None:
            self.time_period = time_period
        if time_period is None and frequency is None:
            self.time_period = 1
        self.mode = mode

        if on_time is not None and off_time is not None:
            self.on_time = on_time
            self.off_time = off_time
        else:
            self.on_time = self.time_period / 2
            self.off_time = self.time_period / 2

        self.init_state = init_state
        self.curr_state = init_state
        self.exitFlag = False
        self.daemon = True
        self.A = Connector(self.init_state)
        self.update = False

    def _toggleState(self):
        """
        This is an internal method to toggle the state of the output
        """
        self.A.state = 0 if self.A.state else 1
        self.A.trigger()

    def setMode(self, mode):
        """
        Sets the mode of the Multivibrator
        """
        self.mode = mode
        self.update = False

    def getState(self):
        """
        Returns the current state
        """
        return self.A.state

    def setState(self, value):
        """
        Resets the state of the clock to the passed value
        """
        self.A.state = value

    def getTimePeriod(self):
        """
        Returns the time period of the clock
        """
        return self.time_period

    def kill(self):
        """
        Kills the Thread
        """
        self.exitFlag = True

    def _updater(self):
        while True:
            if self.exitFlag:
                sys.exit()
            if self.update is True:
                if self.mode == 1:
                    self.A.state = 1
                    self.A.trigger()
                    time.sleep(self.time_period)
                    self._toggleState()
                    self.update = False

                elif self.mode == 2:
                    while (self.mode == 2) and (self.update) and (not self.exitFlag):
                        self._toggleState()
                        if self.A.state == 1:
                            time.sleep(self.on_time)
                        else:
                            time.sleep(self.off_time)

                elif self.mode == 3:
                    self._toggleState()
                    self.update = False

    def __call__(self):
        self.update = True

    trigger = __call__

    def setOutput(self, conn):
        a = self.A
        self.A = conn if isinstance(conn, Connector) else a

    def stop(self):
        # For stopping the multivibrator in astable mode.
        self.update = False

    def run(self):
        self._updater()

########NEW FILE########
__FILENAME__ = oscilloscope
from __future__ import print_function
import time
from itertools import chain
from BinPy import Connector
import threading
import sys

try:
    _V = chr(9474)
    _H = chr(9472)
    _HVD = chr(9488)
    _HVU = chr(9496)
    _VHU = chr(9484)
    _VHD = chr(9492)
    _N = chr(10)
except:
    range = xrange  # This is to make the sampler more efficient in python2
    _V = unichr(9474)
    _H = unichr(9472)
    _HVD = unichr(9488)
    _HVU = unichr(9496)
    _VHU = unichr(9484)
    _VHD = unichr(9492)
    _N = unichr(10)


class Oscilloscope(threading.Thread):

    """
    Oscilloscope is helpful in visualizing simulations.

    USAGE:
    # A clock of 1 hertz frequency
    clock = Clock(1, 1)
    clock.start()
    clk_conn = clock.A

    bc = BinaryCounter()
    os1 = Oscilloscope( (bc.out[1],'lsb') , (bc.out[0],'msb'))
    os1.start()
    #Triggering the counter:
    for i in range(5):
        b.trigger()
        print (b.state())
    os1.stop()
    os1.display()
    """

    def __init__(self, *inputs):
        threading.Thread.__init__(self)
        self.daemon = True

        self.MAX_INP = 15
        self.WID = 150
        self.LEN = 500

        self.inputs = []
        self.labels = {}
        self.logicArray = [[]]
        self.clearLA
        self.leninputs = 0

        self.active = False
        self.exitFlag = False
        self.C = "\x1b[0m"

        if len(inputs) > 0:
            self.updateInputs(*inputs)

    def clearLA(self):
        self.logicArray = [
            [0 for x in range(self.WID)] for x in range(self.MAX_INP)]

    def setWidth(self, w=150):
        """
        Set the maximum width of the oscilloscope.
        This is dependent on your current monitor configuration.
        """
        if w in range(50, 300):
            self.WID = w
        else:
            print("ERROR:Invalid width. Width reverted to old value")

    def setScale(self, scale=0.05):
        """
        This decides the time per unit xWidth.
        To avoid waveform distortion, follow NYQUIST sampling theorem.
        That is if the least time period of the waveform is T;
        Set the scale to be greater than T/2 [ preferably T/5 - To avoid edge sampling effects ]

        There is a lower bound on the scale value [ use trial and error to identify this for your particular PC ]
        This limitation is set by the processing time taken to set a plot etc.
        """
        self.scale = scale

    def updateInputs(self, *inputs):
        """
        Set inputs using a list of tuples.

        For example:
        osc1.setInputs((conn1,"label") , (conn2,"label") ... )
        """
        self.clear(True)

        if len(inputs) < 1:
            raise Exception("ERROR: Too few inputs given.")

        if len(inputs) > self.MAX_INP - self.leninputs:
            raise Exception("ERROR: Maximum inputs exceeded")

        try:
            for i in inputs:
                if not (isinstance(i, tuple) and isinstance(i[0], Connector) and isinstance(i[1], str)):
                    raise Exception("ERROR: Invalid input format")
        except:
            raise Exception("ERROR: Invalid input format")

        for i in inputs:
            lbl = i[1][:5].rjust(5, ' ')

            if i[0] in self.labels:
                self.labels[i[0]] = lbl
            else:
                self.inputs.append(i[0])
                self.labels[i[0]] = lbl

        self.leninputs = len(self.inputs)

    def disconnect(self, conn):
        """
        Disconnects conn from the inputDict
        """
        self.hold()
        self.clear(True)
        self.labels.pop(conn, None)
        self.inputs.remove(conn)
        self.leninputs = len(self.inputs)

    def sampler(self, trigPoint):
        # DEV-note: This is critical part and needs to be highly efficient.
        # Do not introduce any delay causing element

        for i in range(self.leninputs):
            self.logicArray[i][trigPoint] = self.inputs[i].state

    def unhold(self):
        self.clear(True)
        self.active = True

    def hold(self):
        self.active = False

    def clear(self, keepInputs=False):
        self.active = False

        try:
            print("\x1b[0m")
        except:
            pass

        self.clearLA()
        if not keepInputs:
            self.inputs = []
            self.leninputs = 0

    def _trigger(self):
        while True:
            if self.exitFlag:
                sys.exit()
            while self.active:
                for i in range(self.WID):
                    if not self.active:
                        break
                    time.sleep(self.scale)
                    self.sampler(i)
                self.hold()

    def run(self):
        self._trigger()

    def kill(self):
        self.exitFlag = True

    def setColour(self, foreground=1, background=7):
        """
        Acceptable values are:
        1 --> RED
        2 --> GREEN
        4 --> BLUE
        7 --> WHITE

        To RESET call without parameters.

        Please note that serColor is not supported by all operating systems.
        This will run without problems on most Linux systems.
        """
        if not foreground and not background:
            self.C = "\x1b[0m"

        self.C = "\x1b[3%im\x1b[4%im" % (foreground, background)

    def display(self):
        self.hold()

        try:
            sclstr = "SCALE - X-AXIS : 1 UNIT WIDTH = %s" % str(self.scale)
            llen = (self.WID + 15)
            disp = self.C + "=" * llen + \
                "\nBinPy - Oscilloscope\n" + "=" * llen
            disp += _N + sclstr.rjust(llen, " ") + _N + "=" * llen + _N

            j = 0
            for i in range(self.leninputs):

                conn = self.inputs[i]

                lA2 = [0] + self.logicArray[i] + [0]
                lA = [j if j is not None else 0 for j in lA2]

                disp += " " * 10 + _V + _N
                disp += " " * 10 + _V + _N
                disp += " " * 10 + _V + " "
                for i in range(1, len(lA) - 1):
                    cmpstr = (lA[i - 1], lA[i])
                    if cmpstr == (1, 0):
                        disp += _HVD
                    elif cmpstr == (1, 1):
                        disp += _H
                    elif cmpstr == (0, 0):
                        disp += " "
                    elif cmpstr == (0, 1):
                        disp += _VHU

                disp += _N + " " * 3 + self.labels[conn] + "  " + _V + " "

                for i in range(1, len(lA) - 1):
                    cmpstr = lA[i - 1], lA[i]
                    if cmpstr == (1, 0):
                        disp += _V
                    elif cmpstr == (0, 1):
                        disp += _V
                    else:
                        disp += " "

                disp += _N + " " * 10 + _H + " "

                for i in range(1, len(lA) - 1):
                    cmpstr = lA[i - 1], lA[i]
                    if cmpstr == (1, 0):
                        disp += _VHD
                    elif cmpstr == (1, 1):
                        disp += " "
                    elif cmpstr == (0, 0):
                        disp += _H
                    elif cmpstr == (0, 1):
                        disp += _HVU
                disp += _N + " " * 10 + _V + _N
                disp += " " * 10 + _V + _N
            disp += _V * llen + _N
            disp += _H * llen + _N + "\x1b[0m"
            print(disp)
        except:
            print("\x1b[0mERROR: Display error: " + sys.exc_info()[1].args[0])

########NEW FILE########
__FILENAME__ = powersource
from BinPy.Gates import *


class PowerSource:

    """
    Models a Power Source from which various connectors can tap by connecting to it.

    taps: The list of all connectors connected to this power source.

    connect(): Takes in one or more connectors as input and connects them to the power source.

    disconnect(): Takes in one or more connectors as input and disconnects them from the power source.
    """

    def __init__(self):
        self.taps = []

    def connect(self, *connectors):
        """Takes in one or more connectors as an input and taps to the power source."""
        for connector in connectors:
            if not isinstance(connector, Connector):
                raise Exception("Error: Input given is not a connector")
            else:
                if len(connector.connections['output']) != 0:
                    raise Exception(
                        "ERROR: The connector is already an output of some other object")
                self.taps.append(connector)
                connector.state = 1
                connector.tap(self, 'output')
                connector.trigger()

    def disconnect(self, *connectors):
        """
        Takes in one or more connectors as an input and disconnects them from the power source.
        A floating connector has a value of None.
        A message is printed if a specified connector is not already tapping from this source.
        """

        for connector in connectors:
            if isinstance(connector, Connector):
                try:
                    self.taps.remove(connector)
                    connector.state = None
                    connector.connections['output'].remove(self)
                    connector.trigger()
                except:
                    print (
                        "The specified connector is not tapped to this power source")
            else:
                raise Exception("Error: Input given is not a connector")

########NEW FILE########
__FILENAME__ = steppermotor
from __future__ import print_function

import os
import sys
import time
import BinPy
import threading
from BinPy import *

try:
    from PyQt4 import QtGui, QtCore
except ImportError:
    raise ImportError("You need to install PyQt4 for GUI components")


class StepperMotor(threading.Thread):

    """
    Create a StepperMotor Simulation

    Description:
    ============

    This Class is used to simulate a stepper motor using the adequate inputs.

    Specifications:
    ===============

    Drive Method        : Bipolar ( Predefined )
    No. of Phases       : 2
    No. of rotor poles  : 100 ( Can be modified )
    Winding Per Phase   : 1
    Type                : Permanent magnet
    Maximum RPM         : 1200
    Output Leads        : A   B   A!  B!

    Examples
    ========

    >>> import time
    >>> from BinPy import *
    >>> from BinPy.tools.steppermotor import StepperMotor
    >>> a = Connector(); b = Connector(); c = Connector(); d = Connector()
    >>> sm = StepperMotor("Main Motor",a,b,c,d)
    >>> for i in range(100):
    ...     sm.rotate(0.5,1)
    ...     time.sleep(0.1)
    >>> # To rotate through a certain angle
    >>> sm.move_to(-90, rpm = 60)
    >>> sm.move_to(90, rpm = 60, shortest_path = False)
    >>> # To rotate by a certain angle
    >>> sm.move_by(90)
    >>> sm.move_by(-60)
    >>> # To update the leads externally
    >>> a.state = 0; b.state = 0; c.state = 0; d.state = 1
    >>> sm.trigger()
    >>> a.state = 1; b.state = 0; c.state = 0; d.state = 1
    >>> sm.trigger()

    Methods
    =======

    rotate(steps, direction, rpm, step_type)
    # To rotate steps in the direction with a speed of rpm rotations per minute with mode as step_type

    trigger()
    # To update changes in leads

    stop()
    # To terminate existing operation(s)

    kill()
    # To terminate this thread

    reset()
    # To reset the StepperMotor

    Attributes
    ==========

    ROTOR_POLES ; No of rotor poles.
    PHASES      ; No of phases.
    MAX_RPM     ; Max safe speed.
    SEQ         ; Sequence matrix.
    leads       ; Connector list.
    index       ; Serial Number of Stepper motor instance.
    name        ; Specified name of Stepper motor instance.

    angle       ; Current position in degrees of stepper motor.
    busy        ; Status of operation.
    status      ; Stack of pending operations.

    """

    index = 0

    def __init__(self, name, *inputs):

        self.ROTOR_POLES = 100
        self.PHASES = 2
        self.MAX_RPM = 1200
        self.SEQ = [[1, 0, 0, 0],
                    [1, 1, 0, 0],
                    [0, 1, 0, 0],
                    [0, 1, 1, 0],
                    [0, 0, 1, 0],
                    [0, 0, 1, 1],
                    [0, 0, 0, 1],
                    [1, 0, 0, 1]]

        threading.Thread.__init__(self)
        self.name = str(name)

        self.rpm = self.MAX_RPM

        # No of rotor poles = No of poles per phase
        self.total_poles = self.ROTOR_POLES * self.PHASES
        self.step_angle = float(360) / float(self.total_poles)

        StepperMotor.index += 1
        self.index = StepperMotor.index

        self.leads = [None] * 4
        self._history = [0] * 4
        self.set_inputs(*inputs)

        self.step_type = 0  # Half Stepping mode by default
        self.step_resolution = 0.5

        self.angle = 0

        self.daemon = True

        self._disp = _SMDisplayApp(self, self.name, self.index)

        self.status = []
        self.busy = False

        self.exit_flag = False
        self.start()

    def rotate(self, steps=1, direction=1, rpm=None, step_type=0):
        """
        Rotate the stepper motor by [steps] steps and in the specified direction.

        steps can Either be multiples of 0.5 ( Half Stepping ) .
        Default value is 1 ( Full stepping )

        direction 1 --> rotate right
        direction 0 --> rotate left

        rpm should be less than the MAX_RPM and greater than 0

        stepping = 0 --> Half Stepping
        stepping = 1 --> Full Stepping
        """

        # While there is another process goin on sleep for 0.001s
        # while len(self.status) !=0:
        # time.sleep(0.001)

        if self.busy:
            raise Exception
            return

        self.status.append(1)

        self.busy = True

        # Direction analysis

        self.direction = direction

        self.direction = 0 if steps < 0 else 1

        self.steps = abs(steps)

        # Step type configuration

        self.step_type = step_type

        if self.step_type == 0:
            self.steps = float(round(2 * float(self.steps))) / float(2)
            # This will round off to the nearest 0.5 resolution [ Half Stepping
            # ]
            self.step_resolution = 0.5
        else:
            self.steps = round(self.steps)
            # This  will round off to the nearest integer value [ Full Stepping
            # ]
            self.step_resolution = 1

        if rpm is not None:
            if rpm > 0 and rpm < self.MAX_RPM:
                self.rpm = rpm

    def _rotate(self):
        """
        Internally called to realize rotation.
        """
        if (self.steps > 0):

            self.steps -= self.step_resolution

            self.validate()

            updated_state = self.get_next_state(
            ) if self.direction == 1 else self.get_prev_state()

            self._update_leads(updated_state)

            time.sleep(float(60) / float(self.rpm * 360))

            self.status.append(2)

        else:

            self.status.pop()
            self.busy = False

    def move_to(self, angle, rpm=None, shortest_path=True):
        """
        Rotate the stepper motor in the specified rpm speed to reach the specified angle.
        The shortest_path when set forces rotation in the direction of minor arc.
        If shortest_path is not set the behaviour is in the direction of either the major
        or minor arc.
        """

        angle %= 360

        diff_angle = angle - self.angle

        if shortest_path and diff_angle > 180:
            diff_angle *= -1
        self.rotate(steps=diff_angle / self.step_angle, rpm=rpm)

    def move_by(self, angle, rpm=None):
        """
        Rotate the stepper motor by the specified angle at the specified rpm speed.
        """

        diff_angle = angle - self.angle

        self.rotate(steps=angle / self.step_angle, rpm=rpm)

    def _update_leads(self, data):
        for i in range(4):
            self.leads[i].state = data[i]

    def get_state(self):
        return [int(i) for i in self.leads]

    def get_next_state(self, state=None, step_type=0):

        # Use leads' state as state if no state is specified
        if state is None:
            state = self.get_state()

        if (state in self.SEQ):
            return self.SEQ[((self.SEQ.index(state) + step_type + 1) % 8)]
        else:
            raise Exception

    def get_prev_state(self, state=None, step_type=0):

        # Use leads' state as state if no state is specified
        if state is None:
            state = self.get_state()

        if (state in self.SEQ):
            return self.SEQ[((self.SEQ.index(state) - step_type - 1) % 8)]
        else:
            raise Exception

    def get_seq_no(self, state=None):
        if state is None:
            state = self.get_state()
        return self.SEQ.index(state)

    def _update_angle(self):

        # Assumption is that the leads and _history have already been
        # validated.

        state = self.get_state()

        if (self._history == state):
            return

        seq_no = self.get_seq_no(state)
        old_seq_no = self.get_seq_no(self._history)

        # Half step right rotation
        if ((old_seq_no + 1) % 8) == seq_no:
            self.angle += 0.5 * self.step_angle

        # Full Step right rotation
        elif ((old_seq_no + 2) % 8) == seq_no:
            self.angle += self.step_angle

        # Half Step left rotation
        elif ((old_seq_no - 1) % 8) == seq_no:
            self.angle -= 0.5 * self.step_angle

        # Full step left rotation
        elif ((old_seq_no - 2) % 8) == seq_no:
            self.angle -= self.step_angle

        # Invallid Configuration
        else:
            print(
                "ERROR: Invalid configuration. Only single and half step changes are alowed. Refer to SEQ for table of allowed inputs")
            print("Restoring the current configuration from history")
            self._update_leads(self._history)

        self.angle %= 360

    def stop(self):
        self.busy = False
        self.status = []

    def reset(self, keep_connections=True):

        self.stop()

        for pin in self.leads:
            pin.state = 0

        if not keep_connections:
            self.disconnect()

        self.angle = 0
        self._history = [0] * 4
        self.step_type = 0  # Half stepping
        self.step_resolution = 0.5

    def set_inputs(self, *values):
        """
        Connect all the connectors at once
        """
        for i in range(4):
            if not isinstance(values[i], Connector):
                self.leads = [None] * 4
                self._history = [0] * 4
                raise Exception

            self.set_input(i, values[i])
            self._history[i] = values[i].state

    def set_input(self, index, value):
        """
        Set the input based on the index and value.

        If the value is a Connector, then the respective input is connected to it.
        else the Connector at that index is updated with the value.
        """

        if isinstance(self.leads[index], Connector):
            self.leads[index].untap(self, 'input')

        if index <= 4:
            if isinstance(value, Connector):
                self.leads[index] = value
            else:
                self.leads[index].state = int(value) if isinstance(
                    self.leads[index],
                    Connector) else None

        if self.leads[index] is None:
            raise Exception
        else:
            self.leads[index].tap(self, 'input')

    def disconnect(self):
        # Only the connections are removed. The state and configuration is
        # preserved.
        for pin in self.leads:
            pin.untap(self, 'input')
        self.leads = [None] * 4

    def kill(self):
        """
        Use this method to kill the StepperMotor instance.
        """
        self.exit_flag = True

    def run(self):
        while not self.exit_flag and not self._disp.exit:
            if len(self.status) != 0:
                if self.status[-1] == 2:
                    self._trigger()
                    self.status.pop()
                elif self.status[-1] == 1:
                    self._rotate()
                    # The stack is not popped now.
                    # _rotate() upon completion of operation will pop this
                    # stack.

        self._disp.kill()
        sys.exit()

    def trigger(self):
        """
        Call trigger to notify the stepper motor instance of any changes in the input leads
        """

        # User defined function. Only user will call it.
        # Internal methods should not use this.
        # Use _trigger() instead.

        while len(self.status) != 0:
            # while there are incomplete operations
            time.sleep(0.001)

        self.status.append(2)

    def _trigger(self):
        self.validate()
        self._update_angle()
        self._history = self.get_state()

    def validate(self):
        # This method will check the current configuration for validity and modify the bits accordingly.
        # If the current configuration is invalid. It will automatically change
        # it to a valid entry.

        if False in [isinstance(i, Connector) for i in self.leads]:
            raise Exception

        if self.get_state() not in self.SEQ:
            print(
                "ERROR: Current Configuration is invalid. Restoring valid state from history.")
            if self._history in self.SEQ:
                self._update_leads(self._history)
            else:
                print(
                    "ERROR: Restoration Failed, History invalid. Restoring history to 1000. Preserving the current angle")
                self._history = [1, 0, 0, 0]
                self._update_leads(self._history)
        else:
            if self._history not in self.SEQ:
                self._history = self.get_state()


class _SMDisplayApp(threading.Thread):

    def __init__(self, bound_to, name, index):
        threading.Thread.__init__(self)
        self.daemon = False
        self.app = QtGui.QApplication(sys.argv)

        self.window = _SMDisplay(bound_to, name, index)
        self.window.show()
        self.window.raise_()

        self.bound_to = bound_to
        self.index = index
        self.name = name

        self.exit = False
        self.start()

    def run(self):
        self.app.exec_()
        while not self.exit:
            if not self.window.isVisible():
                print("STEPPERMOTOR: " +
                      str(self.index) +
                      " " +
                      str(self.name) +
                      " : Simulation window has been closed. Terminating simulation.\n")
                self.bound_to.reset()
                self.exit = True
            else:
                time.sleep(0.1)
        self.window.close()
        sys.exit()

    def kill(self):
        self.exit = True


class _SMDisplay(QtGui.QMainWindow):

    """
    Internal GUI module to display the stepper motor simulation
    """

    def __init__(self, bound_to, name, index):
        super(_SMDisplay, self).__init__(None)

        # Setting variables
        self.bound_to = bound_to
        self.name = name
        self.index = index

        # Configuring the window:
        self.setGeometry(0, 0, 600, 600)
        self.setStyleSheet("QWidget{background-color: #FFFFFF;}")
        self.setWindowTitle("BinPy : StepperMotor - " +
                            str(self.index) +
                            " - " +
                            str(self.name))

        # Setting the path - To be compatible with different os
        # self.path = os.path.join(os.getcwd(),
        self.path = os.path.join(
            str(
                BinPy.__file__).replace(
                "__init__.pyc",
                "").replace(
                "__init__.py",
                ""),
            "res",
            "stepper_motor.jpg")

        # The UI
        self.label = QtGui.QLabel(self)
        self.label.setGeometry(150, 150, 300, 300)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.setCentralWidget(self.label)

        # Create the initial scaled pixmap for display
        self.pixmap = QtGui.QPixmap(self.path).scaled(self.label.size(), 1)

        # Create a timer to auto refresh display every 1 ms.
        self.timer = QtCore.QTimer()

        QtCore.QObject.connect(
            self.timer,
            QtCore.SIGNAL("timeout()"),
            self.refresh)

        self.timer.start(1)

    def refresh(self, angle=None):

        # If the GUI has terminated via close() stop the timer.
        if not self.isVisible():
            self.timer.stop()
            return

        if angle is None:
            angle = self.bound_to.angle

        # This rotates the image by the self.bound_to.angle
        rotated = self.pixmap.transformed(QtGui.QTransform().rotate(angle))

        self.label.setPixmap(rotated)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# BinPy documentation build configuration file, created by
# sphinx-quickstart on Tue Apr 15 23:23:23 2014.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
import os


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.pngmath',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'BinPy'
copyright = u'2014, BinPy Development Team'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.3.1'
# The full version, including alpha/beta/rc tags.
release = '0.3.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
# language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
# today = ''
# Else, today_fmt is used as the format for a strftime call.
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
# keep_warnings = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'solar'  # Courtesy https://github.com/vkvn/sphinx-themes

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
# html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = "BinPy Documentation"

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = "BinPy Docs"

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "_static/binpy-logo.png"

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
# html_extra_path = []

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
# html_additional_pages = {}

# If false, no module index is generated.
# html_domain_indices = True

# If false, no index is generated.
html_use_index = True

# If true, the index is split into individual pages for each letter.
# html_split_index = False

# If true, links to the reST sources are added to the pages.
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'BinPydoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    'papersize': 'a4paper',

    # The font size ('10pt', '11pt' or '12pt').
    'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    # 'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('index', 'BinPy.tex', u'BinPy Documentation',
     u'BinPy Development Team', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
latex_logo = "_static/binpy-logo.png"

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
# latex_use_parts = False

# If true, show page references after internal links.
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
# latex_appendices = []

# If false, no module index is generated.
# latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'binpy', u'BinPy Documentation',
     [u'BinPy Development Team'], 1)
]

# If true, show URL addresses after external links.
# man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'BinPy', u'BinPy Documentation',
     u'BinPy Development Team', 'BinPy', 'Virtualizing Electronics.',
     'Electronics'),
]

# Documents to append as an appendix to all manuals.
# texinfo_appendices = []

# If false, no module index is generated.
# texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
# texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
# texinfo_no_detailmenu = False


# Example configuration for intersphinx: refer to the Python standard library.
# intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
