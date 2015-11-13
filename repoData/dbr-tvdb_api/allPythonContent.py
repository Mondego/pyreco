__FILENAME__ = gprof2dot
#!/usr/bin/env python
#
# Copyright 2008 Jose Fonseca
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Generate a dot graph from the output of several profilers."""

__author__ = "Jose Fonseca"

__version__ = "1.0"


import sys
import math
import os.path
import re
import textwrap
import optparse


try:
    # Debugging helper module
    import debug
except ImportError:
    pass


def percentage(p):
    return "%.02f%%" % (p*100.0,)

def add(a, b):
    return a + b

def equal(a, b):
    if a == b:
        return a
    else:
        return None

def fail(a, b):
    assert False


def ratio(numerator, denominator):
    numerator = float(numerator)
    denominator = float(denominator)
    assert 0.0 <= numerator
    assert numerator <= denominator
    try:
        return numerator/denominator
    except ZeroDivisionError:
        # 0/0 is undefined, but 1.0 yields more useful results
        return 1.0


class UndefinedEvent(Exception):
    """Raised when attempting to get an event which is undefined."""
    
    def __init__(self, event):
        Exception.__init__(self)
        self.event = event

    def __str__(self):
        return 'unspecified event %s' % self.event.name


class Event(object):
    """Describe a kind of event, and its basic operations."""

    def __init__(self, name, null, aggregator, formatter = str):
        self.name = name
        self._null = null
        self._aggregator = aggregator
        self._formatter = formatter

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    def null(self):
        return self._null

    def aggregate(self, val1, val2):
        """Aggregate two event values."""
        assert val1 is not None
        assert val2 is not None
        return self._aggregator(val1, val2)
    
    def format(self, val):
        """Format an event value."""
        assert val is not None
        return self._formatter(val)


MODULE = Event("Module", None, equal)
PROCESS = Event("Process", None, equal)

CALLS = Event("Calls", 0, add)
SAMPLES = Event("Samples", 0, add)

TIME = Event("Time", 0.0, add, lambda x: '(' + str(x) + ')')
TIME_RATIO = Event("Time ratio", 0.0, add, lambda x: '(' + percentage(x) + ')')
TOTAL_TIME = Event("Total time", 0.0, fail)
TOTAL_TIME_RATIO = Event("Total time ratio", 0.0, fail, percentage)

CALL_RATIO = Event("Call ratio", 0.0, add, percentage)

PRUNE_RATIO = Event("Prune ratio", 0.0, add, percentage)


class Object(object):
    """Base class for all objects in profile which can store events."""

    def __init__(self, events=None):
        if events is None:
            self.events = {}
        else:
            self.events = events

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

    def __contains__(self, event):
        return event in self.events
    
    def __getitem__(self, event):
        try:
            return self.events[event]
        except KeyError:
            raise UndefinedEvent(event)
    
    def __setitem__(self, event, value):
        if value is None:
            if event in self.events:
                del self.events[event]
        else:
            self.events[event] = value


class Call(Object):
    """A call between functions.
    
    There should be at most one call object for every pair of functions.
    """

    def __init__(self, callee_id):
        Object.__init__(self)
        self.callee_id = callee_id    


class Function(Object):
    """A function."""

    def __init__(self, id, name):
        Object.__init__(self)
        self.id = id
        self.name = name
        self.calls = {}
        self.cycle = None
    
    def add_call(self, call):
        if call.callee_id in self.calls:
            sys.stderr.write('warning: overwriting call from function %s to %s\n' % (str(self.id), str(call.callee_id)))
        self.calls[call.callee_id] = call

    # TODO: write utility functions

    def __repr__(self):
        return self.name


class Cycle(Object):
    """A cycle made from recursive function calls."""

    def __init__(self):
        Object.__init__(self)
        # XXX: Do cycles need an id?
        self.functions = set()

    def add_function(self, function):
        assert function not in self.functions
        self.functions.add(function)
        # XXX: Aggregate events?
        if function.cycle is not None:
            for other in function.cycle.functions:
                if function not in self.functions:
                    self.add_function(other)
        function.cycle = self


class Profile(Object):
    """The whole profile."""

    def __init__(self):
        Object.__init__(self)
        self.functions = {}
        self.cycles = []

    def add_function(self, function):
        if function.id in self.functions:
            sys.stderr.write('warning: overwriting function %s (id %s)\n' % (function.name, str(function.id)))
        self.functions[function.id] = function

    def add_cycle(self, cycle):
        self.cycles.append(cycle)

    def validate(self):
        """Validate the edges."""

        for function in self.functions.itervalues():
            for callee_id in function.calls.keys():
                assert function.calls[callee_id].callee_id == callee_id
                if callee_id not in self.functions:
                    sys.stderr.write('warning: call to undefined function %s from function %s\n' % (str(callee_id), function.name))
                    del function.calls[callee_id]

    def find_cycles(self):
        """Find cycles using Tarjan's strongly connected components algorithm."""

        # Apply the Tarjan's algorithm successively until all functions are visited
        visited = set()
        for function in self.functions.itervalues():
            if function not in visited:
                self._tarjan(function, 0, [], {}, {}, visited)
        cycles = []
        for function in self.functions.itervalues():
            if function.cycle is not None and function.cycle not in cycles:
                cycles.append(function.cycle)
        self.cycles = cycles
        if 0:
            for cycle in cycles:
                sys.stderr.write("Cycle:\n")
                for member in cycle.functions:
                    sys.stderr.write("\t%s\n" % member.name)
    
    def _tarjan(self, function, order, stack, orders, lowlinks, visited):
        """Tarjan's strongly connected components algorithm.

        See also:
        - http://en.wikipedia.org/wiki/Tarjan's_strongly_connected_components_algorithm
        """

        visited.add(function)
        orders[function] = order
        lowlinks[function] = order
        order += 1
        pos = len(stack)
        stack.append(function)
        for call in function.calls.itervalues():
            callee = self.functions[call.callee_id]
            # TODO: use a set to optimize lookup
            if callee not in orders:
                order = self._tarjan(callee, order, stack, orders, lowlinks, visited)
                lowlinks[function] = min(lowlinks[function], lowlinks[callee])
            elif callee in stack:
                lowlinks[function] = min(lowlinks[function], orders[callee])
        if lowlinks[function] == orders[function]:
            # Strongly connected component found
            members = stack[pos:]
            del stack[pos:]
            if len(members) > 1:
                cycle = Cycle()
                for member in members:
                    cycle.add_function(member)
        return order

    def call_ratios(self, event):
        # Aggregate for incoming calls
        cycle_totals = {}
        for cycle in self.cycles:
            cycle_totals[cycle] = 0.0
        function_totals = {}
        for function in self.functions.itervalues():
            function_totals[function] = 0.0
        for function in self.functions.itervalues():
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    function_totals[callee] += call[event]
                    if callee.cycle is not None and callee.cycle is not function.cycle:
                        cycle_totals[callee.cycle] += call[event]

        # Compute the ratios
        for function in self.functions.itervalues():
            for call in function.calls.itervalues():
                assert CALL_RATIO not in call
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is not None and callee.cycle is not function.cycle:
                        total = cycle_totals[callee.cycle]
                    else:
                        total = function_totals[callee]
                    call[CALL_RATIO] = ratio(call[event], total)

    def integrate(self, outevent, inevent):
        """Propagate function time ratio allong the function calls.

        Must be called after finding the cycles.

        See also:
        - http://citeseer.ist.psu.edu/graham82gprof.html
        """

        # Sanity checking
        assert outevent not in self
        for function in self.functions.itervalues():
            assert outevent not in function
            assert inevent in function
            for call in function.calls.itervalues():
                assert outevent not in call
                if call.callee_id != function.id:
                    assert CALL_RATIO in call

        # Aggregate the input for each cycle 
        for cycle in self.cycles:
            total = inevent.null()
            for function in self.functions.itervalues():
                total = inevent.aggregate(total, function[inevent])
            self[inevent] = total

        # Integrate along the edges
        total = inevent.null()
        for function in self.functions.itervalues():
            total = inevent.aggregate(total, function[inevent])
            self._integrate_function(function, outevent, inevent)
        self[outevent] = total

    def _integrate_function(self, function, outevent, inevent):
        if function.cycle is not None:
            return self._integrate_cycle(function.cycle, outevent, inevent)
        else:
            if outevent not in function:
                total = function[inevent]
                for call in function.calls.itervalues():
                    if call.callee_id != function.id:
                        total += self._integrate_call(call, outevent, inevent)
                function[outevent] = total
            return function[outevent]
    
    def _integrate_call(self, call, outevent, inevent):
        assert outevent not in call
        assert CALL_RATIO in call
        callee = self.functions[call.callee_id]
        subtotal = call[CALL_RATIO]*self._integrate_function(callee, outevent, inevent)
        call[outevent] = subtotal
        return subtotal

    def _integrate_cycle(self, cycle, outevent, inevent):
        if outevent not in cycle:

            total = inevent.null()
            for member in cycle.functions:
                subtotal = member[inevent]
                for call in member.calls.itervalues():
                    callee = self.functions[call.callee_id]
                    if callee.cycle is not cycle:
                        subtotal += self._integrate_call(call, outevent, inevent)
                total += subtotal
            cycle[outevent] = total
            
            callees = {}
            for function in self.functions.itervalues():
                if function.cycle is not cycle:
                    for call in function.calls.itervalues():
                        callee = self.functions[call.callee_id]
                        if callee.cycle is cycle:
                            try:
                                callees[callee] += call[CALL_RATIO]
                            except KeyError:
                                callees[callee] = call[CALL_RATIO]

            for callee, call_ratio in callees.iteritems():
                ranks = {}
                call_ratios = {}
                partials = {}
                self._rank_cycle_function(cycle, callee, 0, ranks)
                self._call_ratios_cycle(cycle, callee, ranks, call_ratios, set())
                partial = self._integrate_cycle_function(cycle, callee, call_ratio, partials, ranks, call_ratios, outevent, inevent)
                assert partial == max(partials.values())
                assert not total or abs(1.0 - partial/(call_ratio*total)) <= 0.001
            
        return cycle[outevent]

    def _rank_cycle_function(self, cycle, function, rank, ranks):
        if function not in ranks or ranks[function] > rank:
            ranks[function] = rank
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is cycle:
                        self._rank_cycle_function(cycle, callee, rank + 1, ranks)

    def _call_ratios_cycle(self, cycle, function, ranks, call_ratios, visited):
        if function not in visited:
            visited.add(function)
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is cycle:
                        if ranks[callee] > ranks[function]:
                            call_ratios[callee] = call_ratios.get(callee, 0.0) + call[CALL_RATIO]
                            self._call_ratios_cycle(cycle, callee, ranks, call_ratios, visited)

    def _integrate_cycle_function(self, cycle, function, partial_ratio, partials, ranks, call_ratios, outevent, inevent):
        if function not in partials:
            partial = partial_ratio*function[inevent]
            for call in function.calls.itervalues():
                if call.callee_id != function.id:
                    callee = self.functions[call.callee_id]
                    if callee.cycle is not cycle:
                        assert outevent in call
                        partial += partial_ratio*call[outevent]
                    else:
                        if ranks[callee] > ranks[function]:
                            callee_partial = self._integrate_cycle_function(cycle, callee, partial_ratio, partials, ranks, call_ratios, outevent, inevent)
                            call_ratio = ratio(call[CALL_RATIO], call_ratios[callee])
                            call_partial = call_ratio*callee_partial
                            try:
                                call[outevent] += call_partial
                            except UndefinedEvent:
                                call[outevent] = call_partial
                            partial += call_partial
            partials[function] = partial
            try:
                function[outevent] += partial
            except UndefinedEvent:
                function[outevent] = partial
        return partials[function]

    def aggregate(self, event):
        """Aggregate an event for the whole profile."""

        total = event.null()
        for function in self.functions.itervalues():
            try:
                total = event.aggregate(total, function[event])
            except UndefinedEvent:
                return
        self[event] = total

    def ratio(self, outevent, inevent):
        assert outevent not in self
        assert inevent in self
        for function in self.functions.itervalues():
            assert outevent not in function
            assert inevent in function
            function[outevent] = ratio(function[inevent], self[inevent])
            for call in function.calls.itervalues():
                assert outevent not in call
                if inevent in call:
                    call[outevent] = ratio(call[inevent], self[inevent])
        self[outevent] = 1.0

    def prune(self, node_thres, edge_thres):
        """Prune the profile"""

        # compute the prune ratios
        for function in self.functions.itervalues():
            try:
                function[PRUNE_RATIO] = function[TOTAL_TIME_RATIO]
            except UndefinedEvent:
                pass

            for call in function.calls.itervalues():
                callee = self.functions[call.callee_id]

                if TOTAL_TIME_RATIO in call:
                    # handle exact cases first
                    call[PRUNE_RATIO] = call[TOTAL_TIME_RATIO] 
                else:
                    try:
                        # make a safe estimate
                        call[PRUNE_RATIO] = min(function[TOTAL_TIME_RATIO], callee[TOTAL_TIME_RATIO]) 
                    except UndefinedEvent:
                        pass

        # prune the nodes
        for function_id in self.functions.keys():
            function = self.functions[function_id]
            try:
                if function[PRUNE_RATIO] < node_thres:
                    del self.functions[function_id]
            except UndefinedEvent:
                pass

        # prune the egdes
        for function in self.functions.itervalues():
            for callee_id in function.calls.keys():
                call = function.calls[callee_id]
                try:
                    if callee_id not in self.functions or call[PRUNE_RATIO] < edge_thres:
                        del function.calls[callee_id]
                except UndefinedEvent:
                    pass
    
    def dump(self):
        for function in self.functions.itervalues():
            sys.stderr.write('Function %s:\n' % (function.name,))
            self._dump_events(function.events)
            for call in function.calls.itervalues():
                callee = self.functions[call.callee_id]
                sys.stderr.write('  Call %s:\n' % (callee.name,))
                self._dump_events(call.events)

    def _dump_events(self, events):
        for event, value in events.iteritems():
            sys.stderr.write('    %s: %s\n' % (event.name, event.format(value)))


class Struct:
    """Masquerade a dictionary with a structure-like behavior."""

    def __init__(self, attrs = None):
        if attrs is None:
            attrs = {}
        self.__dict__['_attrs'] = attrs
    
    def __getattr__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self._attrs[name] = value

    def __str__(self):
        return str(self._attrs)

    def __repr__(self):
        return repr(self._attrs)
    

class ParseError(Exception):
    """Raised when parsing to signal mismatches."""

    def __init__(self, msg, line):
        self.msg = msg
        # TODO: store more source line information
        self.line = line

    def __str__(self):
        return '%s: %r' % (self.msg, self.line)


class Parser:
    """Parser interface."""

    def __init__(self):
        pass

    def parse(self):
        raise NotImplementedError

    
class LineParser(Parser):
    """Base class for parsers that read line-based formats."""

    def __init__(self, file):
        Parser.__init__(self)
        self._file = file
        self.__line = None
        self.__eof = False

    def readline(self):
        line = self._file.readline()
        if not line:
            self.__line = ''
            self.__eof = True
        self.__line = line.rstrip('\r\n')

    def lookahead(self):
        assert self.__line is not None
        return self.__line

    def consume(self):
        assert self.__line is not None
        line = self.__line
        self.readline()
        return line

    def eof(self):
        assert self.__line is not None
        return self.__eof


class GprofParser(Parser):
    """Parser for GNU gprof output.

    See also:
    - Chapter "Interpreting gprof's Output" from the GNU gprof manual
      http://sourceware.org/binutils/docs-2.18/gprof/Call-Graph.html#Call-Graph
    - File "cg_print.c" from the GNU gprof source code
      http://sourceware.org/cgi-bin/cvsweb.cgi/~checkout~/src/gprof/cg_print.c?rev=1.12&cvsroot=src
    """

    def __init__(self, fp):
        Parser.__init__(self)
        self.fp = fp
        self.functions = {}
        self.cycles = {}

    def readline(self):
        line = self.fp.readline()
        if not line:
            sys.stderr.write('error: unexpected end of file\n')
            sys.exit(1)
        line = line.rstrip('\r\n')
        return line

    _int_re = re.compile(r'^\d+$')
    _float_re = re.compile(r'^\d+\.\d+$')

    def translate(self, mo):
        """Extract a structure from a match object, while translating the types in the process."""
        attrs = {}
        groupdict = mo.groupdict()
        for name, value in groupdict.iteritems():
            if value is None:
                value = None
            elif self._int_re.match(value):
                value = int(value)
            elif self._float_re.match(value):
                value = float(value)
            attrs[name] = (value)
        return Struct(attrs)

    _cg_header_re = re.compile(
        # original gprof header
        r'^\s+called/total\s+parents\s*$|' +
        r'^index\s+%time\s+self\s+descendents\s+called\+self\s+name\s+index\s*$|' +
        r'^\s+called/total\s+children\s*$|' +
        # GNU gprof header
        r'^index\s+%\s+time\s+self\s+children\s+called\s+name\s*$'
    )

    _cg_ignore_re = re.compile(
        # spontaneous
        r'^\s+<spontaneous>\s*$|'
        # internal calls (such as "mcount")
        r'^.*\((\d+)\)$'
    )

    _cg_primary_re = re.compile(
        r'^\[(?P<index>\d+)\]' + 
        r'\s+(?P<percentage_time>\d+\.\d+)' + 
        r'\s+(?P<self>\d+\.\d+)' + 
        r'\s+(?P<descendants>\d+\.\d+)' + 
        r'\s+(?:(?P<called>\d+)(?:\+(?P<called_self>\d+))?)?' + 
        r'\s+(?P<name>\S.*?)' +
        r'(?:\s+<cycle\s(?P<cycle>\d+)>)?' +
        r'\s\[(\d+)\]$'
    )

    _cg_parent_re = re.compile(
        r'^\s+(?P<self>\d+\.\d+)?' + 
        r'\s+(?P<descendants>\d+\.\d+)?' + 
        r'\s+(?P<called>\d+)(?:/(?P<called_total>\d+))?' + 
        r'\s+(?P<name>\S.*?)' +
        r'(?:\s+<cycle\s(?P<cycle>\d+)>)?' +
        r'\s\[(?P<index>\d+)\]$'
    )

    _cg_child_re = _cg_parent_re

    _cg_cycle_header_re = re.compile(
        r'^\[(?P<index>\d+)\]' + 
        r'\s+(?P<percentage_time>\d+\.\d+)' + 
        r'\s+(?P<self>\d+\.\d+)' + 
        r'\s+(?P<descendants>\d+\.\d+)' + 
        r'\s+(?:(?P<called>\d+)(?:\+(?P<called_self>\d+))?)?' + 
        r'\s+<cycle\s(?P<cycle>\d+)\sas\sa\swhole>' +
        r'\s\[(\d+)\]$'
    )

    _cg_cycle_member_re = re.compile(
        r'^\s+(?P<self>\d+\.\d+)?' + 
        r'\s+(?P<descendants>\d+\.\d+)?' + 
        r'\s+(?P<called>\d+)(?:\+(?P<called_self>\d+))?' + 
        r'\s+(?P<name>\S.*?)' +
        r'(?:\s+<cycle\s(?P<cycle>\d+)>)?' +
        r'\s\[(?P<index>\d+)\]$'
    )

    _cg_sep_re = re.compile(r'^--+$')

    def parse_function_entry(self, lines):
        parents = []
        children = []

        while True:
            if not lines:
                sys.stderr.write('warning: unexpected end of entry\n')
            line = lines.pop(0)
            if line.startswith('['):
                break
        
            # read function parent line
            mo = self._cg_parent_re.match(line)
            if not mo:
                if self._cg_ignore_re.match(line):
                    continue
                sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            else:
                parent = self.translate(mo)
                parents.append(parent)

        # read primary line
        mo = self._cg_primary_re.match(line)
        if not mo:
            sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            return
        else:
            function = self.translate(mo)

        while lines:
            line = lines.pop(0)
            
            # read function subroutine line
            mo = self._cg_child_re.match(line)
            if not mo:
                if self._cg_ignore_re.match(line):
                    continue
                sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            else:
                child = self.translate(mo)
                children.append(child)
        
        function.parents = parents
        function.children = children

        self.functions[function.index] = function

    def parse_cycle_entry(self, lines):

        # read cycle header line
        line = lines[0]
        mo = self._cg_cycle_header_re.match(line)
        if not mo:
            sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
            return
        cycle = self.translate(mo)

        # read cycle member lines
        cycle.functions = []
        for line in lines[1:]:
            mo = self._cg_cycle_member_re.match(line)
            if not mo:
                sys.stderr.write('warning: unrecognized call graph entry: %r\n' % line)
                continue
            call = self.translate(mo)
            cycle.functions.append(call)
        
        self.cycles[cycle.cycle] = cycle

    def parse_cg_entry(self, lines):
        if lines[0].startswith("["):
            self.parse_cycle_entry(lines)
        else:
            self.parse_function_entry(lines)

    def parse_cg(self):
        """Parse the call graph."""

        # skip call graph header
        while not self._cg_header_re.match(self.readline()):
            pass
        line = self.readline()
        while self._cg_header_re.match(line):
            line = self.readline()

        # process call graph entries
        entry_lines = []
        while line != '\014': # form feed
            if line and not line.isspace():
                if self._cg_sep_re.match(line):
                    self.parse_cg_entry(entry_lines)
                    entry_lines = []
                else:
                    entry_lines.append(line)            
            line = self.readline()
    
    def parse(self):
        self.parse_cg()
        self.fp.close()

        profile = Profile()
        profile[TIME] = 0.0
        
        cycles = {}
        for index in self.cycles.iterkeys():
            cycles[index] = Cycle()

        for entry in self.functions.itervalues():
            # populate the function
            function = Function(entry.index, entry.name)
            function[TIME] = entry.self
            if entry.called is not None:
                function[CALLS] = entry.called
            if entry.called_self is not None:
                call = Call(entry.index)
                call[CALLS] = entry.called_self
                function[CALLS] += entry.called_self
            
            # populate the function calls
            for child in entry.children:
                call = Call(child.index)
                
                assert child.called is not None
                call[CALLS] = child.called

                if child.index not in self.functions:
                    # NOTE: functions that were never called but were discovered by gprof's 
                    # static call graph analysis dont have a call graph entry so we need
                    # to add them here
                    missing = Function(child.index, child.name)
                    function[TIME] = 0.0
                    function[CALLS] = 0
                    profile.add_function(missing)

                function.add_call(call)

            profile.add_function(function)

            if entry.cycle is not None:
                cycles[entry.cycle].add_function(function)

            profile[TIME] = profile[TIME] + function[TIME]

        for cycle in cycles.itervalues():
            profile.add_cycle(cycle)

        # Compute derived events
        profile.validate()
        profile.ratio(TIME_RATIO, TIME)
        profile.call_ratios(CALLS)
        profile.integrate(TOTAL_TIME, TIME)
        profile.ratio(TOTAL_TIME_RATIO, TOTAL_TIME)

        return profile


class OprofileParser(LineParser):
    """Parser for oprofile callgraph output.
    
    See also:
    - http://oprofile.sourceforge.net/doc/opreport.html#opreport-callgraph
    """

    _fields_re = {
        'samples': r'(?P<samples>\d+)',
        '%': r'(?P<percentage>\S+)',
        'linenr info': r'(?P<source>\(no location information\)|\S+:\d+)',
        'image name': r'(?P<image>\S+(?:\s\(tgid:[^)]*\))?)',
        'app name': r'(?P<application>\S+)',
        'symbol name': r'(?P<symbol>\(no symbols\)|.+?)',
    }

    def __init__(self, infile):
        LineParser.__init__(self, infile)
        self.entries = {}
        self.entry_re = None

    def add_entry(self, callers, function, callees):
        try:
            entry = self.entries[function.id]
        except KeyError:
            self.entries[function.id] = (callers, function, callees)
        else:
            callers_total, function_total, callees_total = entry
            self.update_subentries_dict(callers_total, callers)
            function_total.samples += function.samples
            self.update_subentries_dict(callees_total, callees)
    
    def update_subentries_dict(self, totals, partials):
        for partial in partials.itervalues():
            try:
                total = totals[partial.id]
            except KeyError:
                totals[partial.id] = partial
            else:
                total.samples += partial.samples
        
    def parse(self):
        # read lookahead
        self.readline()

        self.parse_header()
        while self.lookahead():
            self.parse_entry()

        profile = Profile()

        reverse_call_samples = {}
        
        # populate the profile
        profile[SAMPLES] = 0
        for _callers, _function, _callees in self.entries.itervalues():
            function = Function(_function.id, _function.name)
            function[SAMPLES] = _function.samples
            profile.add_function(function)
            profile[SAMPLES] += _function.samples

            if _function.application:
                function[PROCESS] = os.path.basename(_function.application)
            if _function.image:
                function[MODULE] = os.path.basename(_function.image)

            total_callee_samples = 0
            for _callee in _callees.itervalues():
                total_callee_samples += _callee.samples

            for _callee in _callees.itervalues():
                if not _callee.self:
                    call = Call(_callee.id)
                    call[SAMPLES] = _callee.samples
                    function.add_call(call)
                
        # compute derived data
        profile.validate()
        profile.find_cycles()
        profile.ratio(TIME_RATIO, SAMPLES)
        profile.call_ratios(SAMPLES)
        profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return profile

    def parse_header(self):
        while not self.match_header():
            self.consume()
        line = self.lookahead()
        fields = re.split(r'\s\s+', line)
        entry_re = r'^\s*' + r'\s+'.join([self._fields_re[field] for field in fields]) + r'(?P<self>\s+\[self\])?$'
        self.entry_re = re.compile(entry_re)
        self.skip_separator()

    def parse_entry(self):
        callers = self.parse_subentries()
        if self.match_primary():
            function = self.parse_subentry()
            if function is not None:
                callees = self.parse_subentries()
                self.add_entry(callers, function, callees)
        self.skip_separator()

    def parse_subentries(self):
        subentries = {}
        while self.match_secondary():
            subentry = self.parse_subentry()
            subentries[subentry.id] = subentry
        return subentries

    def parse_subentry(self):
        entry = Struct()
        line = self.consume()
        mo = self.entry_re.match(line)
        if not mo:
            raise ParseError('failed to parse', line)
        fields = mo.groupdict()
        entry.samples = int(fields.get('samples', 0))
        entry.percentage = float(fields.get('percentage', 0.0))
        if 'source' in fields and fields['source'] != '(no location information)':
            source = fields['source']
            filename, lineno = source.split(':')
            entry.filename = filename
            entry.lineno = int(lineno)
        else:
            source = ''
            entry.filename = None
            entry.lineno = None
        entry.image = fields.get('image', '')
        entry.application = fields.get('application', '')
        if 'symbol' in fields and fields['symbol'] != '(no symbols)':
            entry.symbol = fields['symbol']
        else:
            entry.symbol = ''
        if entry.symbol.startswith('"') and entry.symbol.endswith('"'):
            entry.symbol = entry.symbol[1:-1]
        entry.id = ':'.join((entry.application, entry.image, source, entry.symbol))
        entry.self = fields.get('self', None) != None
        if entry.self:
            entry.id += ':self'
        if entry.symbol:
            entry.name = entry.symbol
        else:
            entry.name = entry.image
        return entry

    def skip_separator(self):
        while not self.match_separator():
            self.consume()
        self.consume()

    def match_header(self):
        line = self.lookahead()
        return line.startswith('samples')

    def match_separator(self):
        line = self.lookahead()
        return line == '-'*len(line)

    def match_primary(self):
        line = self.lookahead()
        return not line[:1].isspace()
    
    def match_secondary(self):
        line = self.lookahead()
        return line[:1].isspace()


class SharkParser(LineParser):
    """Parser for MacOSX Shark output.

    Author: tom@dbservice.com
    """

    def __init__(self, infile):
        LineParser.__init__(self, infile)
        self.stack = []
        self.entries = {}

    def add_entry(self, function):
        try:
            entry = self.entries[function.id]
        except KeyError:
            self.entries[function.id] = (function, { })
        else:
            function_total, callees_total = entry
            function_total.samples += function.samples
    
    def add_callee(self, function, callee):
        func, callees = self.entries[function.id]
        try:
            entry = callees[callee.id]
        except KeyError:
            callees[callee.id] = callee
        else:
            entry.samples += callee.samples
        
    def parse(self):
        self.readline()
        self.readline()
        self.readline()
        self.readline()

        match = re.compile(r'(?P<prefix>[|+ ]*)(?P<samples>\d+), (?P<symbol>[^,]+), (?P<image>.*)')

        while self.lookahead():
            line = self.consume()
            mo = match.match(line)
            if not mo:
                raise ParseError('failed to parse', line)

            fields = mo.groupdict()
            prefix = len(fields.get('prefix', 0)) / 2 - 1

            symbol = str(fields.get('symbol', 0))
            image = str(fields.get('image', 0))

            entry = Struct()
            entry.id = ':'.join([symbol, image])
            entry.samples = int(fields.get('samples', 0))

            entry.name = symbol
            entry.image = image

            # adjust the callstack
            if prefix < len(self.stack):
                del self.stack[prefix:]

            if prefix == len(self.stack):
                self.stack.append(entry)

            # if the callstack has had an entry, it's this functions caller
            if prefix > 0:
                self.add_callee(self.stack[prefix - 1], entry)
                
            self.add_entry(entry)
                
        profile = Profile()
        profile[SAMPLES] = 0
        for _function, _callees in self.entries.itervalues():
            function = Function(_function.id, _function.name)
            function[SAMPLES] = _function.samples
            profile.add_function(function)
            profile[SAMPLES] += _function.samples

            if _function.image:
                function[MODULE] = os.path.basename(_function.image)

            for _callee in _callees.itervalues():
                call = Call(_callee.id)
                call[SAMPLES] = _callee.samples
                function.add_call(call)
                
        # compute derived data
        profile.validate()
        profile.find_cycles()
        profile.ratio(TIME_RATIO, SAMPLES)
        profile.call_ratios(SAMPLES)
        profile.integrate(TOTAL_TIME_RATIO, TIME_RATIO)

        return profile


class PstatsParser:
    """Parser python profiling statistics saved with te pstats module."""

    def __init__(self, *filename):
        import pstats
        self.stats = pstats.Stats(*filename)
        self.profile = Profile()
        self.function_ids = {}

    def get_function_name(self, (filename, line, name)):
        module = os.path.splitext(filename)[0]
        module = os.path.basename(module)
        return "%s:%d:%s" % (module, line, name)

    def get_function(self, key):
        try:
            id = self.function_ids[key]
        except KeyError:
            id = len(self.function_ids)
            name = self.get_function_name(key)
            function = Function(id, name)
            self.profile.functions[id] = function
            self.function_ids[key] = id
        else:
            function = self.profile.functions[id]
        return function

    def parse(self):
        self.profile[TIME] = 0.0
        self.profile[TOTAL_TIME] = self.stats.total_tt
        for fn, (cc, nc, tt, ct, callers) in self.stats.stats.iteritems():
            callee = self.get_function(fn)
            callee[CALLS] = nc
            callee[TOTAL_TIME] = ct
            callee[TIME] = tt
            self.profile[TIME] += tt
            self.profile[TOTAL_TIME] = max(self.profile[TOTAL_TIME], ct)
            for fn, value in callers.iteritems():
                caller = self.get_function(fn)
                call = Call(callee.id)
                if isinstance(value, tuple):
                    for i in xrange(0, len(value), 4):
                        nc, cc, tt, ct = value[i:i+4]
                        if CALLS in call:
                            call[CALLS] += cc
                        else:
                            call[CALLS] = cc

                        if TOTAL_TIME in call:
                            call[TOTAL_TIME] += ct
                        else:
                            call[TOTAL_TIME] = ct

                else:
                    call[CALLS] = value
                    call[TOTAL_TIME] = ratio(value, nc)*ct

                caller.add_call(call)
        #self.stats.print_stats()
        #self.stats.print_callees()

        # Compute derived events
        self.profile.validate()
        self.profile.ratio(TIME_RATIO, TIME)
        self.profile.ratio(TOTAL_TIME_RATIO, TOTAL_TIME)

        return self.profile


class Theme:

    def __init__(self, 
            bgcolor = (0.0, 0.0, 1.0),
            mincolor = (0.0, 0.0, 0.0),
            maxcolor = (0.0, 0.0, 1.0),
            fontname = "Arial",
            minfontsize = 10.0,
            maxfontsize = 10.0,
            minpenwidth = 0.5,
            maxpenwidth = 4.0,
            gamma = 2.2):
        self.bgcolor = bgcolor
        self.mincolor = mincolor
        self.maxcolor = maxcolor
        self.fontname = fontname
        self.minfontsize = minfontsize
        self.maxfontsize = maxfontsize
        self.minpenwidth = minpenwidth
        self.maxpenwidth = maxpenwidth
        self.gamma = gamma

    def graph_bgcolor(self):
        return self.hsl_to_rgb(*self.bgcolor)

    def graph_fontname(self):
        return self.fontname

    def graph_fontsize(self):
        return self.minfontsize

    def node_bgcolor(self, weight):
        return self.color(weight)

    def node_fgcolor(self, weight):
        return self.graph_bgcolor()

    def node_fontsize(self, weight):
        return self.fontsize(weight)

    def edge_color(self, weight):
        return self.color(weight)

    def edge_fontsize(self, weight):
        return self.fontsize(weight)

    def edge_penwidth(self, weight):
        return max(weight*self.maxpenwidth, self.minpenwidth)

    def edge_arrowsize(self, weight):
        return 0.5 * math.sqrt(self.edge_penwidth(weight))

    def fontsize(self, weight):
        return max(weight**2 * self.maxfontsize, self.minfontsize)

    def color(self, weight):
        weight = min(max(weight, 0.0), 1.0)
    
        hmin, smin, lmin = self.mincolor
        hmax, smax, lmax = self.maxcolor

        h = hmin + weight*(hmax - hmin)
        s = smin + weight*(smax - smin)
        l = lmin + weight*(lmax - lmin)

        return self.hsl_to_rgb(h, s, l)

    def hsl_to_rgb(self, h, s, l):
        """Convert a color from HSL color-model to RGB.

        See also:
        - http://www.w3.org/TR/css3-color/#hsl-color
        """

        h = h % 1.0
        s = min(max(s, 0.0), 1.0)
        l = min(max(l, 0.0), 1.0)

        if l <= 0.5:
            m2 = l*(s + 1.0)
        else:
            m2 = l + s - l*s
        m1 = l*2.0 - m2
        r = self._hue_to_rgb(m1, m2, h + 1.0/3.0)
        g = self._hue_to_rgb(m1, m2, h)
        b = self._hue_to_rgb(m1, m2, h - 1.0/3.0)

        # Apply gamma correction
        r **= self.gamma
        g **= self.gamma
        b **= self.gamma

        return (r, g, b)

    def _hue_to_rgb(self, m1, m2, h):
        if h < 0.0:
            h += 1.0
        elif h > 1.0:
            h -= 1.0
        if h*6 < 1.0:
            return m1 + (m2 - m1)*h*6.0
        elif h*2 < 1.0:
            return m2
        elif h*3 < 2.0:
            return m1 + (m2 - m1)*(2.0/3.0 - h)*6.0
        else:
            return m1


TEMPERATURE_COLORMAP = Theme(
    mincolor = (2.0/3.0, 0.80, 0.25), # dark blue
    maxcolor = (0.0, 1.0, 0.5), # satured red
    gamma = 1.0
)

PINK_COLORMAP = Theme(
    mincolor = (0.0, 1.0, 0.90), # pink
    maxcolor = (0.0, 1.0, 0.5), # satured red
)

GRAY_COLORMAP = Theme(
    mincolor = (0.0, 0.0, 0.85), # light gray
    maxcolor = (0.0, 0.0, 0.0), # black
)

BW_COLORMAP = Theme(
    minfontsize = 8.0,
    maxfontsize = 24.0,
    mincolor = (0.0, 0.0, 0.0), # black
    maxcolor = (0.0, 0.0, 0.0), # black
    minpenwidth = 0.1,
    maxpenwidth = 8.0,
)


class DotWriter:
    """Writer for the DOT language.

    See also:
    - "The DOT Language" specification
      http://www.graphviz.org/doc/info/lang.html
    """

    def __init__(self, fp):
        self.fp = fp

    def graph(self, profile, theme):
        self.begin_graph()

        fontname = theme.graph_fontname()

        self.attr('graph', fontname=fontname, ranksep=0.25, nodesep=0.125)
        self.attr('node', fontname=fontname, shape="box", style="filled,rounded", fontcolor="white", width=0, height=0)
        self.attr('edge', fontname=fontname)

        for function in profile.functions.itervalues():
            labels = []
            for event in PROCESS, MODULE:
                if event in function.events:
                    label = event.format(function[event])
                    labels.append(label)
            labels.append(function.name)
            for event in TOTAL_TIME_RATIO, TIME_RATIO, CALLS:
                if event in function.events:
                    label = event.format(function[event])
                    labels.append(label)

            try:
                weight = function[PRUNE_RATIO]
            except UndefinedEvent:
                weight = 0.0

            label = '\n'.join(labels)
            self.node(function.id, 
                label = label, 
                color = self.color(theme.node_bgcolor(weight)), 
                fontcolor = self.color(theme.node_fgcolor(weight)), 
                fontsize = "%.2f" % theme.node_fontsize(weight),
            )

            for call in function.calls.itervalues():
                callee = profile.functions[call.callee_id]

                labels = []
                for event in TOTAL_TIME_RATIO, CALLS:
                    if event in call.events:
                        label = event.format(call[event])
                        labels.append(label)

                try:
                    weight = call[PRUNE_RATIO]
                except UndefinedEvent:
                    try:
                        weight = callee[PRUNE_RATIO]
                    except UndefinedEvent:
                        weight = 0.0

                label = '\n'.join(labels)

                self.edge(function.id, call.callee_id, 
                    label = label, 
                    color = self.color(theme.edge_color(weight)), 
                    fontcolor = self.color(theme.edge_color(weight)),
                    fontsize = "%.2f" % theme.edge_fontsize(weight), 
                    penwidth = "%.2f" % theme.edge_penwidth(weight), 
                    labeldistance = "%.2f" % theme.edge_penwidth(weight), 
                    arrowsize = "%.2f" % theme.edge_arrowsize(weight),
                )

        self.end_graph()

    def begin_graph(self):
        self.write('digraph {\n')

    def end_graph(self):
        self.write('}\n')

    def attr(self, what, **attrs):
        self.write("\t")
        self.write(what)
        self.attr_list(attrs)
        self.write(";\n")

    def node(self, node, **attrs):
        self.write("\t")
        self.id(node)
        self.attr_list(attrs)
        self.write(";\n")

    def edge(self, src, dst, **attrs):
        self.write("\t")
        self.id(src)
        self.write(" -> ")
        self.id(dst)
        self.attr_list(attrs)
        self.write(";\n")

    def attr_list(self, attrs):
        if not attrs:
            return
        self.write(' [')
        first = True
        for name, value in attrs.iteritems():
            if first:
                first = False
            else:
                self.write(", ")
            self.id(name)
            self.write('=')
            self.id(value)
        self.write(']')

    def id(self, id):
        if isinstance(id, (int, float)):
            s = str(id)
        elif isinstance(id, str):
            if id.isalnum():
                s = id
            else:
                s = self.escape(id)
        else:
            raise TypeError
        self.write(s)

    def color(self, (r, g, b)):

        def float2int(f):
            if f <= 0.0:
                return 0
            if f >= 1.0:
                return 255
            return int(255.0*f + 0.5)

        return "#" + "".join(["%02x" % float2int(c) for c in (r, g, b)])

    def escape(self, s):
        s = s.encode('utf-8')
        s = s.replace('\\', r'\\')
        s = s.replace('\n', r'\n')
        s = s.replace('\t', r'\t')
        s = s.replace('"', r'\"')
        return '"' + s + '"'

    def write(self, s):
        self.fp.write(s)


class Main:
    """Main program."""

    themes = {
            "color": TEMPERATURE_COLORMAP,
            "pink": PINK_COLORMAP,
            "gray": GRAY_COLORMAP,
            "bw": BW_COLORMAP,
    }

    def main(self):
        """Main program."""

        parser = optparse.OptionParser(
            usage="\n\t%prog [options] [file] ...",
            version="%%prog %s" % __version__)
        parser.add_option(
            '-o', '--output', metavar='FILE',
            type="string", dest="output",
            help="output filename [stdout]")
        parser.add_option(
            '-n', '--node-thres', metavar='PERCENTAGE',
            type="float", dest="node_thres", default=0.5,
            help="eliminate nodes below this threshold [default: %default]")
        parser.add_option(
            '-e', '--edge-thres', metavar='PERCENTAGE',
            type="float", dest="edge_thres", default=0.1,
            help="eliminate edges below this threshold [default: %default]")
        parser.add_option(
            '-f', '--format',
            type="choice", choices=('prof', 'oprofile', 'pstats', 'shark'),
            dest="format", default="prof",
            help="profile format: prof, oprofile, or pstats [default: %default]")
        parser.add_option(
            '-c', '--colormap',
            type="choice", choices=('color', 'pink', 'gray', 'bw'),
            dest="theme", default="color",
            help="color map: color, pink, gray, or bw [default: %default]")
        parser.add_option(
            '-s', '--strip',
            action="store_true",
            dest="strip", default=False,
            help="strip function parameters, template parameters, and const modifiers from demangled C++ function names")
        parser.add_option(
            '-w', '--wrap',
            action="store_true",
            dest="wrap", default=False,
            help="wrap function names")
        (self.options, self.args) = parser.parse_args(sys.argv[1:])

        if len(self.args) > 1 and self.options.format != 'pstats':
            parser.error('incorrect number of arguments')

        try:
            self.theme = self.themes[self.options.theme]
        except KeyError:
            parser.error('invalid colormap \'%s\'' % self.options.theme)

        if self.options.format == 'prof':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = GprofParser(fp)
        elif self.options.format == 'oprofile':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = OprofileParser(fp)
        elif self.options.format == 'pstats':
            if not self.args:
                parser.error('at least a file must be specified for pstats input')
            parser = PstatsParser(*self.args)
        elif self.options.format == 'shark':
            if not self.args:
                fp = sys.stdin
            else:
                fp = open(self.args[0], 'rt')
            parser = SharkParser(fp)
        else:
            parser.error('invalid format \'%s\'' % self.options.format)

        self.profile = parser.parse()
        
        if self.options.output is None:
            self.output = sys.stdout
        else:
            self.output = open(self.options.output, 'wt')

        self.write_graph()

    _parenthesis_re = re.compile(r'\([^()]*\)')
    _angles_re = re.compile(r'<[^<>]*>')
    _const_re = re.compile(r'\s+const$')

    def strip_function_name(self, name):
        """Remove extraneous information from C++ demangled function names."""

        # Strip function parameters from name by recursively removing paired parenthesis
        while True:
            name, n = self._parenthesis_re.subn('', name)
            if not n:
                break

        # Strip const qualifier
        name = self._const_re.sub('', name)

        # Strip template parameters from name by recursively removing paired angles
        while True:
            name, n = self._angles_re.subn('', name)
            if not n:
                break

        return name

    def wrap_function_name(self, name):
        """Split the function name on multiple lines."""

        if len(name) > 32:
            ratio = 2.0/3.0
            height = max(int(len(name)/(1.0 - ratio) + 0.5), 1)
            width = max(len(name)/height, 32)
            # TODO: break lines in symbols
            name = textwrap.fill(name, width, break_long_words=False)

        # Take away spaces
        name = name.replace(", ", ",")
        name = name.replace("> >", ">>")
        name = name.replace("> >", ">>") # catch consecutive

        return name

    def compress_function_name(self, name):
        """Compress function name according to the user preferences."""

        if self.options.strip:
            name = self.strip_function_name(name)

        if self.options.wrap:
            name = self.wrap_function_name(name)

        # TODO: merge functions with same resulting name

        return name

    def write_graph(self):
        dot = DotWriter(self.output)
        profile = self.profile
        profile.prune(self.options.node_thres/100.0, self.options.edge_thres/100.0)

        for function in profile.functions.itervalues():
            function.name = self.compress_function_name(function.name)

        dot.graph(profile, self.theme)


if __name__ == '__main__':
    Main().main()

########NEW FILE########
__FILENAME__ = runtests
#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:unlicense (http://unlicense.org/)

import sys
import unittest

import test_tvdb_api

def main():
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromModule(test_tvdb_api)
    ])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(
        int(main())
    )

########NEW FILE########
__FILENAME__ = test_tvdb_api
#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:unlicense (http://unlicense.org/)

"""Unittests for tvdb_api
"""

import os
import sys
import datetime
import unittest

# Force parent directory onto path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tvdb_api
import tvdb_ui
from tvdb_api import (tvdb_shownotfound, tvdb_seasonnotfound,
tvdb_episodenotfound, tvdb_attributenotfound)

class test_tvdb_basic(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None
    
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, banners = False)
     
    def test_different_case(self):
        """Checks the auto-correction of show names is working.
        It should correct the weirdly capitalised 'sCruBs' to 'Scrubs'
        """
        self.assertEquals(self.t['scrubs'][1][4]['episodename'], 'My Old Lady')
        self.assertEquals(self.t['sCruBs']['seriesname'], 'Scrubs')

    def test_spaces(self):
        """Checks shownames with spaces
        """
        self.assertEquals(self.t['My Name Is Earl']['seriesname'], 'My Name Is Earl')
        self.assertEquals(self.t['My Name Is Earl'][1][4]['episodename'], 'Faked His Own Death')

    def test_numeric(self):
        """Checks numeric show names
        """
        self.assertEquals(self.t['24'][2][20]['episodename'], 'Day 2: 3:00 A.M.-4:00 A.M.')
        self.assertEquals(self.t['24']['seriesname'], '24')

    def test_show_iter(self):
        """Iterating over a show returns each seasons
        """
        self.assertEquals(
            len(
                [season for season in self.t['Life on Mars']]
            ),
            2
        )
    
    def test_season_iter(self):
        """Iterating over a show returns episodes
        """
        self.assertEquals(
            len(
                [episode for episode in self.t['Life on Mars'][1]]
            ),
            8
        )

    def test_get_episode_overview(self):
        """Checks episode overview is retrieved correctly.
        """
        self.assertEquals(
            self.t['Battlestar Galactica (2003)'][1][6]['overview'].startswith(
                'When a new copy of Doral, a Cylon who had been previously'),
            True
        )

    def test_get_parent(self):
        """Check accessing series from episode instance
        """
        show = self.t['Battlestar Galactica (2003)']
        season = show[1]
        episode = show[1][1]

        self.assertEquals(
            season.show,
            show
        )

        self.assertEquals(
            episode.season,
            season
        )

        self.assertEquals(
            episode.season.show,
            show
        )

    def test_no_season(self):
        show = self.t['Katekyo Hitman Reborn']
        print tvdb_api
        print show[1][1]

class test_tvdb_errors(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None
    
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, banners = False)

    def test_seasonnotfound(self):
        """Checks exception is thrown when season doesn't exist.
        """
        self.assertRaises(tvdb_seasonnotfound, lambda:self.t['CNNNN'][10][1])

    def test_shownotfound(self):
        """Checks exception is thrown when episode doesn't exist.
        """
        self.assertRaises(tvdb_shownotfound, lambda:self.t['the fake show thingy'])
    
    def test_episodenotfound(self):
        """Checks exception is raised for non-existent episode
        """
        self.assertRaises(tvdb_episodenotfound, lambda:self.t['Scrubs'][1][30])

    def test_attributenamenotfound(self):
        """Checks exception is thrown for if an attribute isn't found.
        """
        self.assertRaises(tvdb_attributenotfound, lambda:self.t['CNNNN'][1][6]['afakeattributething'])
        self.assertRaises(tvdb_attributenotfound, lambda:self.t['CNNNN']['afakeattributething'])

class test_tvdb_search(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None
    
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, banners = False)

    def test_search_len(self):
        """There should be only one result matching
        """
        self.assertEquals(len(self.t['My Name Is Earl'].search('Faked His Own Death')), 1)

    def test_search_checkname(self):
        """Checks you can get the episode name of a search result
        """
        self.assertEquals(self.t['Scrubs'].search('my first')[0]['episodename'], 'My First Day')
        self.assertEquals(self.t['My Name Is Earl'].search('Faked His Own Death')[0]['episodename'], 'Faked His Own Death')
    
    def test_search_multiresults(self):
        """Checks search can return multiple results
        """
        self.assertEquals(len(self.t['Scrubs'].search('my first')) >= 3, True)

    def test_search_no_params_error(self):
        """Checks not supplying search info raises TypeError"""
        self.assertRaises(
            TypeError,
            lambda: self.t['Scrubs'].search()
        )

    def test_search_season(self):
        """Checks the searching of a single season"""
        self.assertEquals(
            len(self.t['Scrubs'][1].search("First")),
            3
        )
    
    def test_search_show(self):
        """Checks the searching of an entire show"""
        self.assertEquals(
            len(self.t['CNNNN'].search('CNNNN', key='episodename')),
            3
        )

    def test_aired_on(self):
        """Tests airedOn show method"""
        sr = self.t['Scrubs'].airedOn(datetime.date(2001, 10, 2))
        self.assertEquals(len(sr), 1)
        self.assertEquals(sr[0]['episodename'], u'My First Day')

class test_tvdb_data(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None
    
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, banners = False)

    def test_episode_data(self):
        """Check the firstaired value is retrieved
        """
        self.assertEquals(
            self.t['lost']['firstaired'],
            '2004-09-22'
        )

class test_tvdb_misc(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None
    
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, banners = False)

    def test_repr_show(self):
        """Check repr() of Season
        """
        self.assertEquals(
            repr(self.t['CNNNN']),
            "<Show Chaser Non-Stop News Network (CNNNN) (containing 3 seasons)>"
        )
    def test_repr_season(self):
        """Check repr() of Season
        """
        self.assertEquals(
            repr(self.t['CNNNN'][1]),
            "<Season instance (containing 9 episodes)>"
        )
    def test_repr_episode(self):
        """Check repr() of Episode
        """
        self.assertEquals(
            repr(self.t['CNNNN'][1][1]),
            "<Episode 01x01 - Terror Alert>"
        )
    def test_have_all_languages(self):
        """Check valid_languages is up-to-date (compared to languages.xml)
        """
        et = self.t._getetsrc(
            "http://thetvdb.com/api/%s/languages.xml" % (
                self.t.config['apikey']
            )
        )
        languages = [x.find("abbreviation").text for x in et.findall("Language")]
        
        self.assertEquals(
            sorted(languages),
            sorted(self.t.config['valid_languages'])
        )
        
class test_tvdb_languages(unittest.TestCase):
    def test_episode_name_french(self):
        """Check episode data is in French (language="fr")
        """
        t = tvdb_api.Tvdb(cache = True, language = "fr")
        self.assertEquals(
            t['scrubs'][1][1]['episodename'],
            "Mon premier jour"
        )
        self.assertTrue(
            t['scrubs']['overview'].startswith(
                u"J.D. est un jeune m\xe9decin qui d\xe9bute"
            )
        )

    def test_episode_name_spanish(self):
        """Check episode data is in Spanish (language="es")
        """
        t = tvdb_api.Tvdb(cache = True, language = "es")
        self.assertEquals(
            t['scrubs'][1][1]['episodename'],
            "Mi Primer Dia"
        )
        self.assertTrue(
            t['scrubs']['overview'].startswith(
                u'Scrubs es una divertida comedia'
            )
        )

    def test_multilanguage_selection(self):
        """Check selected language is used
        """
        class SelectEnglishUI(tvdb_ui.BaseUI):
            def selectSeries(self, allSeries):
                return [x for x in allSeries if x['language'] == "en"][0]

        class SelectItalianUI(tvdb_ui.BaseUI):
            def selectSeries(self, allSeries):
                return [x for x in allSeries if x['language'] == "it"][0]

        t_en = tvdb_api.Tvdb(
            cache=True,
            custom_ui = SelectEnglishUI,
            language = "en")
        t_it = tvdb_api.Tvdb(
            cache=True,
            custom_ui = SelectItalianUI,
            language = "it")

        self.assertEquals(
            t_en['dexter'][1][2]['episodename'], "Crocodile"
        )
        self.assertEquals(
            t_it['dexter'][1][2]['episodename'], "Lacrime di coccodrillo"
        )


class test_tvdb_unicode(unittest.TestCase):
    def test_search_in_chinese(self):
        """Check searching for show with language=zh returns Chinese seriesname
        """
        t = tvdb_api.Tvdb(cache = True, language = "zh")
        show = t[u'T\xecnh Ng\u01b0\u1eddi Hi\u1ec7n \u0110\u1ea1i']
        self.assertEquals(
            type(show),
            tvdb_api.Show
        )
        
        self.assertEquals(
            show['seriesname'],
            u'T\xecnh Ng\u01b0\u1eddi Hi\u1ec7n \u0110\u1ea1i'
        )

    def test_search_in_all_languages(self):
        """Check search_all_languages returns Chinese show, with language=en
        """
        t = tvdb_api.Tvdb(cache = True, search_all_languages = True, language="en")
        show = t[u'T\xecnh Ng\u01b0\u1eddi Hi\u1ec7n \u0110\u1ea1i']
        self.assertEquals(
            type(show),
            tvdb_api.Show
        )
        
        self.assertEquals(
            show['seriesname'],
            u'Virtues Of Harmony II'
        )

class test_tvdb_banners(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None
    
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, banners = True)

    def test_have_banners(self):
        """Check banners at least one banner is found
        """
        self.assertEquals(
            len(self.t['scrubs']['_banners']) > 0,
            True
        )

    def test_banner_url(self):
        """Checks banner URLs start with http://
        """
        for banner_type, banner_data in self.t['scrubs']['_banners'].items():
            for res, res_data in banner_data.items():
                for bid, banner_info in res_data.items():
                    self.assertEquals(
                        banner_info['_bannerpath'].startswith("http://"),
                        True
                    )

    def test_episode_image(self):
        """Checks episode 'filename' image is fully qualified URL
        """
        self.assertEquals(
            self.t['scrubs'][1][1]['filename'].startswith("http://"),
            True
        )
    
    def test_show_artwork(self):
        """Checks various image URLs within season data are fully qualified
        """
        for key in ['banner', 'fanart', 'poster']:
            self.assertEquals(
                self.t['scrubs'][key].startswith("http://"),
                True
            )

class test_tvdb_actors(unittest.TestCase):
    t = None
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, actors = True)

    def test_actors_is_correct_datatype(self):
        """Check show/_actors key exists and is correct type"""
        self.assertTrue(
            isinstance(
                self.t['scrubs']['_actors'],
                tvdb_api.Actors
            )
        )
    
    def test_actors_has_actor(self):
        """Check show has at least one Actor
        """
        self.assertTrue(
            isinstance(
                self.t['scrubs']['_actors'][0],
                tvdb_api.Actor
            )
        )
    
    def test_actor_has_name(self):
        """Check first actor has a name"""
        self.assertEquals(
            self.t['scrubs']['_actors'][0]['name'],
            "Zach Braff"
        )

    def test_actor_image_corrected(self):
        """Check image URL is fully qualified
        """
        for actor in self.t['scrubs']['_actors']:
            if actor['image'] is not None:
                # Actor's image can be None, it displays as the placeholder
                # image on thetvdb.com
                self.assertTrue(
                    actor['image'].startswith("http://")
                )

class test_tvdb_doctest(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None
    
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, banners = False)
    
    def test_doctest(self):
        """Check docstring examples works"""
        import doctest
        doctest.testmod(tvdb_api)


class test_tvdb_custom_caching(unittest.TestCase):
    def test_true_false_string(self):
        """Tests setting cache to True/False/string

        Basic tests, only checking for errors
        """

        tvdb_api.Tvdb(cache = True)
        tvdb_api.Tvdb(cache = False)
        tvdb_api.Tvdb(cache = "/tmp")

    def test_invalid_cache_option(self):
        """Tests setting cache to invalid value
        """

        try:
            tvdb_api.Tvdb(cache = 2.3)
        except ValueError:
            pass
        else:
            self.fail("Expected ValueError from setting cache to float")

    def test_custom_urlopener(self):
        class UsedCustomOpener(Exception):
            pass

        import urllib2
        class TestOpener(urllib2.BaseHandler):
            def default_open(self, request):
                print request.get_method()
                raise UsedCustomOpener("Something")

        custom_opener = urllib2.build_opener(TestOpener())
        t = tvdb_api.Tvdb(cache = custom_opener)
        try:
            t['scrubs']
        except UsedCustomOpener:
            pass
        else:
            self.fail("Did not use custom opener")

class test_tvdb_by_id(unittest.TestCase):
    t = None
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, actors = True)

    def test_actors_is_correct_datatype(self):
        """Check show/_actors key exists and is correct type"""
        self.assertEquals(
            self.t[76156]['seriesname'],
            'Scrubs'
            )


class test_tvdb_zip(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None

    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, useZip = True)

    def test_get_series_from_zip(self):
        """
        """
        self.assertEquals(self.t['scrubs'][1][4]['episodename'], 'My Old Lady')
        self.assertEquals(self.t['sCruBs']['seriesname'], 'Scrubs')

    def test_spaces_from_zip(self):
        """Checks shownames with spaces
        """
        self.assertEquals(self.t['My Name Is Earl']['seriesname'], 'My Name Is Earl')
        self.assertEquals(self.t['My Name Is Earl'][1][4]['episodename'], 'Faked His Own Death')


class test_tvdb_show_ordering(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t_dvd = None
    t_air = None

    def setUp(self):
        if self.t_dvd is None:
            self.t_dvd = tvdb_api.Tvdb(cache = True, useZip = True, dvdorder=True)

        if self.t_air is None:
            self.t_air = tvdb_api.Tvdb(cache = True, useZip = True)

    def test_ordering(self):
        """Test Tvdb.search method
        """
        self.assertEquals(u'The Train Job', self.t_air['Firefly'][1][1]['episodename'])
        self.assertEquals(u'Serenity', self.t_dvd['Firefly'][1][1]['episodename'])

        self.assertEquals(u'The Cat & the Claw (Part 1)', self.t_air['Batman The Animated Series'][1][1]['episodename'])
        self.assertEquals(u'On Leather Wings', self.t_dvd['Batman The Animated Series'][1][1]['episodename'])

class test_tvdb_show_search(unittest.TestCase):
    # Used to store the cached instance of Tvdb()
    t = None

    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, useZip = True)

    def test_search(self):
        """Test Tvdb.search method
        """
        results = self.t.search("my name is earl")
        all_ids = [x['seriesid'] for x in results]
        self.assertTrue('75397' in all_ids)


class test_tvdb_alt_names(unittest.TestCase):
    t = None
    def setUp(self):
        if self.t is None:
            self.__class__.t = tvdb_api.Tvdb(cache = True, actors = True)

    def test_1(self):
        """Tests basic access of series name alias
        """
        results = self.t.search("Don't Trust the B---- in Apartment 23")
        series = results[0]
        self.assertTrue(
            'Apartment 23' in series['aliasnames']
        )


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity = 2)
    unittest.main(testRunner = runner)

########NEW FILE########
__FILENAME__ = tvdb_api
#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:unlicense (http://unlicense.org/)

"""Simple-to-use Python interface to The TVDB's API (thetvdb.com)

Example usage:

>>> from tvdb_api import Tvdb
>>> t = Tvdb()
>>> t['Lost'][4][11]['episodename']
u'Cabin Fever'
"""
__author__ = "dbr/Ben"
__version__ = "1.9"

import os
import time
import urllib
import urllib2
import getpass
import StringIO
import tempfile
import warnings
import logging
import datetime
import zipfile

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree

try:
    import gzip
except ImportError:
    gzip = None


from tvdb_cache import CacheHandler

from tvdb_ui import BaseUI, ConsoleUI
from tvdb_exceptions import (tvdb_error, tvdb_userabort, tvdb_shownotfound,
    tvdb_seasonnotfound, tvdb_episodenotfound, tvdb_attributenotfound)

lastTimeout = None

def log():
    return logging.getLogger("tvdb_api")


class ShowContainer(dict):
    """Simple dict that holds a series of Show instances
    """

    def __init__(self):
        self._stack = []
        self._lastgc = time.time()

    def __setitem__(self, key, value):
        self._stack.append(key)

        #keep only the 100th latest results
        if time.time() - self._lastgc > 20:
            for o in self._stack[:-100]:
                del self[o]
            self._stack = self._stack[-100:]

            self._lastgc = time.time()

        super(ShowContainer, self).__setitem__(key, value)


class Show(dict):
    """Holds a dict of seasons, and show data.
    """
    def __init__(self):
        dict.__init__(self)
        self.data = {}

    def __repr__(self):
        return "<Show %s (containing %s seasons)>" % (
            self.data.get(u'seriesname', 'instance'),
            len(self)
        )

    def __getitem__(self, key):
        if key in self:
            # Key is an episode, return it
            return dict.__getitem__(self, key)

        if key in self.data:
            # Non-numeric request is for show-data
            return dict.__getitem__(self.data, key)

        # Data wasn't found, raise appropriate error
        if isinstance(key, int) or key.isdigit():
            # Episode number x was not found
            raise tvdb_seasonnotfound("Could not find season %s" % (repr(key)))
        else:
            # If it's not numeric, it must be an attribute name, which
            # doesn't exist, so attribute error.
            raise tvdb_attributenotfound("Cannot find attribute %s" % (repr(key)))

    def airedOn(self, date):
        ret = self.search(str(date), 'firstaired')
        if len(ret) == 0:
            raise tvdb_episodenotfound("Could not find any episodes that aired on %s" % date)
        return ret

    def search(self, term = None, key = None):
        """
        Search all episodes in show. Can search all data, or a specific key (for
        example, episodename)

        Always returns an array (can be empty). First index contains the first
        match, and so on.

        Each array index is an Episode() instance, so doing
        search_results[0]['episodename'] will retrieve the episode name of the
        first match.

        Search terms are converted to lower case (unicode) strings.

        # Examples
        
        These examples assume t is an instance of Tvdb():
        
        >>> t = Tvdb()
        >>>

        To search for all episodes of Scrubs with a bit of data
        containing "my first day":

        >>> t['Scrubs'].search("my first day")
        [<Episode 01x01 - My First Day>]
        >>>

        Search for "My Name Is Earl" episode named "Faked His Own Death":

        >>> t['My Name Is Earl'].search('Faked His Own Death', key = 'episodename')
        [<Episode 01x04 - Faked His Own Death>]
        >>>

        To search Scrubs for all episodes with "mentor" in the episode name:

        >>> t['scrubs'].search('mentor', key = 'episodename')
        [<Episode 01x02 - My Mentor>, <Episode 03x15 - My Tormented Mentor>]
        >>>

        # Using search results

        >>> results = t['Scrubs'].search("my first")
        >>> print results[0]['episodename']
        My First Day
        >>> for x in results: print x['episodename']
        My First Day
        My First Step
        My First Kill
        >>>
        """
        results = []
        for cur_season in self.values():
            searchresult = cur_season.search(term = term, key = key)
            if len(searchresult) != 0:
                results.extend(searchresult)

        return results


class Season(dict):
    def __init__(self, show = None):
        """The show attribute points to the parent show
        """
        self.show = show

    def __repr__(self):
        return "<Season instance (containing %s episodes)>" % (
            len(self.keys())
        )

    def __getitem__(self, episode_number):
        if episode_number not in self:
            raise tvdb_episodenotfound("Could not find episode %s" % (repr(episode_number)))
        else:
            return dict.__getitem__(self, episode_number)

    def search(self, term = None, key = None):
        """Search all episodes in season, returns a list of matching Episode
        instances.

        >>> t = Tvdb()
        >>> t['scrubs'][1].search('first day')
        [<Episode 01x01 - My First Day>]
        >>>

        See Show.search documentation for further information on search
        """
        results = []
        for ep in self.values():
            searchresult = ep.search(term = term, key = key)
            if searchresult is not None:
                results.append(
                    searchresult
                )
        return results


class Episode(dict):
    def __init__(self, season = None):
        """The season attribute points to the parent season
        """
        self.season = season

    def __repr__(self):
        seasno = int(self.get(u'seasonnumber', 0))
        epno = int(self.get(u'episodenumber', 0))
        epname = self.get(u'episodename')
        if epname is not None:
            return "<Episode %02dx%02d - %s>" % (seasno, epno, epname)
        else:
            return "<Episode %02dx%02d>" % (seasno, epno)

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            raise tvdb_attributenotfound("Cannot find attribute %s" % (repr(key)))

    def search(self, term = None, key = None):
        """Search episode data for term, if it matches, return the Episode (self).
        The key parameter can be used to limit the search to a specific element,
        for example, episodename.
        
        This primarily for use use by Show.search and Season.search. See
        Show.search for further information on search

        Simple example:

        >>> e = Episode()
        >>> e['episodename'] = "An Example"
        >>> e.search("examp")
        <Episode 00x00 - An Example>
        >>>

        Limiting by key:

        >>> e.search("examp", key = "episodename")
        <Episode 00x00 - An Example>
        >>>
        """
        if term == None:
            raise TypeError("must supply string to search for (contents)")

        term = unicode(term).lower()
        for cur_key, cur_value in self.items():
            cur_key, cur_value = unicode(cur_key).lower(), unicode(cur_value).lower()
            if key is not None and cur_key != key:
                # Do not search this key
                continue
            if cur_value.find( unicode(term).lower() ) > -1:
                return self


class Actors(list):
    """Holds all Actor instances for a show
    """
    pass


class Actor(dict):
    """Represents a single actor. Should contain..

    id,
    image,
    name,
    role,
    sortorder
    """
    def __repr__(self):
        return "<Actor \"%s\">" % (self.get("name"))


class Tvdb:
    """Create easy-to-use interface to name of season/episode name
    >>> t = Tvdb()
    >>> t['Scrubs'][1][24]['episodename']
    u'My Last Day'
    """
    def __init__(self,
                interactive = False,
                select_first = False,
                debug = False,
                cache = True,
                banners = False,
                actors = False,
                custom_ui = None,
                language = None,
                search_all_languages = False,
                apikey = None,
                forceConnect=False,
                useZip=False,
                dvdorder=False):

        """interactive (True/False):
            When True, uses built-in console UI is used to select the correct show.
            When False, the first search result is used.

        select_first (True/False):
            Automatically selects the first series search result (rather
            than showing the user a list of more than one series).
            Is overridden by interactive = False, or specifying a custom_ui

        debug (True/False) DEPRECATED:
             Replaced with proper use of logging module. To show debug messages:

                 >>> import logging
                 >>> logging.basicConfig(level = logging.DEBUG)

        cache (True/False/str/unicode/urllib2 opener):
            Retrieved XML are persisted to to disc. If true, stores in
            tvdb_api folder under your systems TEMP_DIR, if set to
            str/unicode instance it will use this as the cache
            location. If False, disables caching.  Can also be passed
            an arbitrary Python object, which is used as a urllib2
            opener, which should be created by urllib2.build_opener

        banners (True/False):
            Retrieves the banners for a show. These are accessed
            via the _banners key of a Show(), for example:

            >>> Tvdb(banners=True)['scrubs']['_banners'].keys()
            ['fanart', 'poster', 'series', 'season']

        actors (True/False):
            Retrieves a list of the actors for a show. These are accessed
            via the _actors key of a Show(), for example:

            >>> t = Tvdb(actors=True)
            >>> t['scrubs']['_actors'][0]['name']
            u'Zach Braff'

        custom_ui (tvdb_ui.BaseUI subclass):
            A callable subclass of tvdb_ui.BaseUI (overrides interactive option)

        language (2 character language abbreviation):
            The language of the returned data. Is also the language search
            uses. Default is "en" (English). For full list, run..

            >>> Tvdb().config['valid_languages'] #doctest: +ELLIPSIS
            ['da', 'fi', 'nl', ...]

        search_all_languages (True/False):
            By default, Tvdb will only search in the language specified using
            the language option. When this is True, it will search for the
            show in and language
        
        apikey (str/unicode):
            Override the default thetvdb.com API key. By default it will use
            tvdb_api's own key (fine for small scripts), but you can use your
            own key if desired - this is recommended if you are embedding
            tvdb_api in a larger application)
            See http://thetvdb.com/?tab=apiregister to get your own key

        forceConnect (bool):
            If true it will always try to connect to theTVDB.com even if we
            recently timed out. By default it will wait one minute before
            trying again, and any requests within that one minute window will
            return an exception immediately.

        useZip (bool):
            Download the zip archive where possibale, instead of the xml.
            This is only used when all episodes are pulled.
            And only the main language xml is used, the actor and banner xml are lost.
        """
        
        global lastTimeout
        
        # if we're given a lastTimeout that is less than 1 min just give up
        if not forceConnect and lastTimeout != None and datetime.datetime.now() - lastTimeout < datetime.timedelta(minutes=1):
            raise tvdb_error("We recently timed out, so giving up early this time")
        
        self.shows = ShowContainer() # Holds all Show classes
        self.corrections = {} # Holds show-name to show_id mapping

        self.config = {}

        if apikey is not None:
            self.config['apikey'] = apikey
        else:
            self.config['apikey'] = "0629B785CE550C8D" # tvdb_api's API key

        self.config['debug_enabled'] = debug # show debugging messages

        self.config['custom_ui'] = custom_ui

        self.config['interactive'] = interactive # prompt for correct series?

        self.config['select_first'] = select_first

        self.config['search_all_languages'] = search_all_languages

        self.config['useZip'] = useZip

        self.config['dvdorder'] = dvdorder

        if cache is True:
            self.config['cache_enabled'] = True
            self.config['cache_location'] = self._getTempDir()
            self.urlopener = urllib2.build_opener(
                CacheHandler(self.config['cache_location'])
            )

        elif cache is False:
            self.config['cache_enabled'] = False
            self.urlopener = urllib2.build_opener() # default opener with no caching

        elif isinstance(cache, basestring):
            self.config['cache_enabled'] = True
            self.config['cache_location'] = cache
            self.urlopener = urllib2.build_opener(
                CacheHandler(self.config['cache_location'])
            )

        elif isinstance(cache, urllib2.OpenerDirector):
            # If passed something from urllib2.build_opener, use that
            log().debug("Using %r as urlopener" % cache)
            self.config['cache_enabled'] = True
            self.urlopener = cache

        else:
            raise ValueError("Invalid value for Cache %r (type was %s)" % (cache, type(cache)))

        self.config['banners_enabled'] = banners
        self.config['actors_enabled'] = actors

        if self.config['debug_enabled']:
            warnings.warn("The debug argument to tvdb_api.__init__ will be removed in the next version. "
            "To enable debug messages, use the following code before importing: "
            "import logging; logging.basicConfig(level=logging.DEBUG)")
            logging.basicConfig(level=logging.DEBUG)


        # List of language from http://thetvdb.com/api/0629B785CE550C8D/languages.xml
        # Hard-coded here as it is realtively static, and saves another HTTP request, as
        # recommended on http://thetvdb.com/wiki/index.php/API:languages.xml
        self.config['valid_languages'] = [
            "da", "fi", "nl", "de", "it", "es", "fr","pl", "hu","el","tr",
            "ru","he","ja","pt","zh","cs","sl", "hr","ko","en","sv","no"
        ]

        # thetvdb.com should be based around numeric language codes,
        # but to link to a series like http://thetvdb.com/?tab=series&id=79349&lid=16
        # requires the language ID, thus this mapping is required (mainly
        # for usage in tvdb_ui - internally tvdb_api will use the language abbreviations)
        self.config['langabbv_to_id'] = {'el': 20, 'en': 7, 'zh': 27,
        'it': 15, 'cs': 28, 'es': 16, 'ru': 22, 'nl': 13, 'pt': 26, 'no': 9,
        'tr': 21, 'pl': 18, 'fr': 17, 'hr': 31, 'de': 14, 'da': 10, 'fi': 11,
        'hu': 19, 'ja': 25, 'he': 24, 'ko': 32, 'sv': 8, 'sl': 30}

        if language is None:
            self.config['language'] = 'en'
        else:
            if language not in self.config['valid_languages']:
                raise ValueError("Invalid language %s, options are: %s" % (
                    language, self.config['valid_languages']
                ))
            else:
                self.config['language'] = language

        # The following url_ configs are based of the
        # http://thetvdb.com/wiki/index.php/Programmers_API
        self.config['base_url'] = "http://thetvdb.com"

        if self.config['search_all_languages']:
            self.config['url_getSeries'] = u"%(base_url)s/api/GetSeries.php?seriesname=%%s&language=all" % self.config
        else:
            self.config['url_getSeries'] = u"%(base_url)s/api/GetSeries.php?seriesname=%%s&language=%(language)s" % self.config

        self.config['url_epInfo'] = u"%(base_url)s/api/%(apikey)s/series/%%s/all/%%s.xml" % self.config
        self.config['url_epInfo_zip'] = u"%(base_url)s/api/%(apikey)s/series/%%s/all/%%s.zip" % self.config

        self.config['url_seriesInfo'] = u"%(base_url)s/api/%(apikey)s/series/%%s/%%s.xml" % self.config
        self.config['url_actorsInfo'] = u"%(base_url)s/api/%(apikey)s/series/%%s/actors.xml" % self.config

        self.config['url_seriesBanner'] = u"%(base_url)s/api/%(apikey)s/series/%%s/banners.xml" % self.config
        self.config['url_artworkPrefix'] = u"%(base_url)s/banners/%%s" % self.config

    def _getTempDir(self):
        """Returns the [system temp dir]/tvdb_api-u501 (or
        tvdb_api-myuser)
        """
        if hasattr(os, 'getuid'):
            uid = "u%d" % (os.getuid())
        else:
            # For Windows
            try:
                uid = getpass.getuser()
            except ImportError:
                return os.path.join(tempfile.gettempdir(), "tvdb_api")

        return os.path.join(tempfile.gettempdir(), "tvdb_api-%s" % (uid))

    def _loadUrl(self, url, recache = False, language=None):
        global lastTimeout
        try:
            log().debug("Retrieving URL %s" % url)
            resp = self.urlopener.open(url)
            if 'x-local-cache' in resp.headers:
                log().debug("URL %s was cached in %s" % (
                    url,
                    resp.headers['x-local-cache'])
                )
                if recache:
                    log().debug("Attempting to recache %s" % url)
                    resp.recache()
        except (IOError, urllib2.URLError), errormsg:
            if not str(errormsg).startswith('HTTP Error'):
                lastTimeout = datetime.datetime.now()
            raise tvdb_error("Could not connect to server: %s" % (errormsg))

        
        # handle gzipped content,
        # http://dbr.lighthouseapp.com/projects/13342/tickets/72-gzipped-data-patch
        if 'gzip' in resp.headers.get("Content-Encoding", ''):
            if gzip:
                stream = StringIO.StringIO(resp.read())
                gz = gzip.GzipFile(fileobj=stream)
                return gz.read()

            raise tvdb_error("Received gzip data from thetvdb.com, but could not correctly handle it")

        if 'application/zip' in resp.headers.get("Content-Type", ''):
            try:
                # TODO: The zip contains actors.xml and banners.xml, which are currently ignored [GH-20]
                log().debug("We recived a zip file unpacking now ...")
                zipdata = StringIO.StringIO()
                zipdata.write(resp.read())
                myzipfile = zipfile.ZipFile(zipdata)
                return myzipfile.read('%s.xml' % language)
            except zipfile.BadZipfile:
                if 'x-local-cache' in resp.headers:
                    resp.delete_cache()
                raise tvdb_error("Bad zip file received from thetvdb.com, could not read it")

        return resp.read()

    def _getetsrc(self, url, language=None):
        """Loads a URL using caching, returns an ElementTree of the source
        """
        src = self._loadUrl(url, language=language)
        try:
            # TVDB doesn't sanitize \r (CR) from user input in some fields,
            # remove it to avoid errors. Change from SickBeard, from will14m
            return ElementTree.fromstring(src.rstrip("\r"))
        except SyntaxError:
            src = self._loadUrl(url, recache=True, language=language)
            try:
                return ElementTree.fromstring(src.rstrip("\r"))
            except SyntaxError, exceptionmsg:
                errormsg = "There was an error with the XML retrieved from thetvdb.com:\n%s" % (
                    exceptionmsg
                )

                if self.config['cache_enabled']:
                    errormsg += "\nFirst try emptying the cache folder at..\n%s" % (
                        self.config['cache_location']
                    )

                errormsg += "\nIf this does not resolve the issue, please try again later. If the error persists, report a bug on"
                errormsg += "\nhttp://dbr.lighthouseapp.com/projects/13342-tvdb_api/overview\n"
                raise tvdb_error(errormsg)

    def _setItem(self, sid, seas, ep, attrib, value):
        """Creates a new episode, creating Show(), Season() and
        Episode()s as required. Called by _getShowData to populate show

        Since the nice-to-use tvdb[1][24]['name] interface
        makes it impossible to do tvdb[1][24]['name] = "name"
        and still be capable of checking if an episode exists
        so we can raise tvdb_shownotfound, we have a slightly
        less pretty method of setting items.. but since the API
        is supposed to be read-only, this is the best way to
        do it!
        The problem is that calling tvdb[1][24]['episodename'] = "name"
        calls __getitem__ on tvdb[1], there is no way to check if
        tvdb.__dict__ should have a key "1" before we auto-create it
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        if seas not in self.shows[sid]:
            self.shows[sid][seas] = Season(show = self.shows[sid])
        if ep not in self.shows[sid][seas]:
            self.shows[sid][seas][ep] = Episode(season = self.shows[sid][seas])
        self.shows[sid][seas][ep][attrib] = value

    def _setShowData(self, sid, key, value):
        """Sets self.shows[sid] to a new Show instance, or sets the data
        """
        if sid not in self.shows:
            self.shows[sid] = Show()
        self.shows[sid].data[key] = value

    def _cleanData(self, data):
        """Cleans up strings returned by TheTVDB.com

        Issues corrected:
        - Replaces &amp; with &
        - Trailing whitespace
        """
        data = data.replace(u"&amp;", u"&")
        data = data.strip()
        return data

    def search(self, series):
        """This searches TheTVDB.com for the series name
        and returns the result list
        """
        series = urllib.quote(series.encode("utf-8"))
        log().debug("Searching for show %s" % series)
        seriesEt = self._getetsrc(self.config['url_getSeries'] % (series))
        allSeries = []
        for series in seriesEt:
            result = dict((k.tag.lower(), k.text) for k in series.getchildren())
            result['id'] = int(result['id'])
            result['lid'] = self.config['langabbv_to_id'][result['language']]
            if 'aliasnames' in result:
                result['aliasnames'] = result['aliasnames'].split("|")
            log().debug('Found series %(seriesname)s' % result)
            allSeries.append(result)
        
        return allSeries

    def _getSeries(self, series):
        """This searches TheTVDB.com for the series name,
        If a custom_ui UI is configured, it uses this to select the correct
        series. If not, and interactive == True, ConsoleUI is used, if not
        BaseUI is used to select the first result.
        """
        allSeries = self.search(series)

        if len(allSeries) == 0:
            log().debug('Series result returned zero')
            raise tvdb_shownotfound("Show-name search returned zero results (cannot find show on TVDB)")

        if self.config['custom_ui'] is not None:
            log().debug("Using custom UI %s" % (repr(self.config['custom_ui'])))
            ui = self.config['custom_ui'](config = self.config)
        else:
            if not self.config['interactive']:
                log().debug('Auto-selecting first search result using BaseUI')
                ui = BaseUI(config = self.config)
            else:
                log().debug('Interactively selecting show using ConsoleUI')
                ui = ConsoleUI(config = self.config)

        return ui.selectSeries(allSeries)

    def _parseBanners(self, sid):
        """Parses banners XML, from
        http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/banners.xml

        Banners are retrieved using t['show name]['_banners'], for example:

        >>> t = Tvdb(banners = True)
        >>> t['scrubs']['_banners'].keys()
        ['fanart', 'poster', 'series', 'season']
        >>> t['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
        u'http://thetvdb.com/banners/posters/76156-2.jpg'
        >>>

        Any key starting with an underscore has been processed (not the raw
        data from the XML)

        This interface will be improved in future versions.
        """
        log().debug('Getting season banners for %s' % (sid))
        bannersEt = self._getetsrc( self.config['url_seriesBanner'] % (sid) )
        banners = {}
        for cur_banner in bannersEt.findall('Banner'):
            bid = cur_banner.find('id').text
            btype = cur_banner.find('BannerType')
            btype2 = cur_banner.find('BannerType2')
            if btype is None or btype2 is None:
                continue
            btype, btype2 = btype.text, btype2.text
            if not btype in banners:
                banners[btype] = {}
            if not btype2 in banners[btype]:
                banners[btype][btype2] = {}
            if not bid in banners[btype][btype2]:
                banners[btype][btype2][bid] = {}

            for cur_element in cur_banner.getchildren():
                tag = cur_element.tag.lower()
                value = cur_element.text
                if tag is None or value is None:
                    continue
                tag, value = tag.lower(), value.lower()
                banners[btype][btype2][bid][tag] = value

            for k, v in banners[btype][btype2][bid].items():
                if k.endswith("path"):
                    new_key = "_%s" % (k)
                    log().debug("Transforming %s to %s" % (k, new_key))
                    new_url = self.config['url_artworkPrefix'] % (v)
                    banners[btype][btype2][bid][new_key] = new_url

        self._setShowData(sid, "_banners", banners)

    def _parseActors(self, sid):
        """Parsers actors XML, from
        http://thetvdb.com/api/[APIKEY]/series/[SERIES ID]/actors.xml

        Actors are retrieved using t['show name]['_actors'], for example:

        >>> t = Tvdb(actors = True)
        >>> actors = t['scrubs']['_actors']
        >>> type(actors)
        <class 'tvdb_api.Actors'>
        >>> type(actors[0])
        <class 'tvdb_api.Actor'>
        >>> actors[0]
        <Actor "Zach Braff">
        >>> sorted(actors[0].keys())
        ['id', 'image', 'name', 'role', 'sortorder']
        >>> actors[0]['name']
        u'Zach Braff'
        >>> actors[0]['image']
        u'http://thetvdb.com/banners/actors/43640.jpg'

        Any key starting with an underscore has been processed (not the raw
        data from the XML)
        """
        log().debug("Getting actors for %s" % (sid))
        actorsEt = self._getetsrc(self.config['url_actorsInfo'] % (sid))

        cur_actors = Actors()
        for curActorItem in actorsEt.findall("Actor"):
            curActor = Actor()
            for curInfo in curActorItem:
                tag = curInfo.tag.lower()
                value = curInfo.text
                if value is not None:
                    if tag == "image":
                        value = self.config['url_artworkPrefix'] % (value)
                    else:
                        value = self._cleanData(value)
                curActor[tag] = value
            cur_actors.append(curActor)
        self._setShowData(sid, '_actors', cur_actors)

    def _getShowData(self, sid, language):
        """Takes a series ID, gets the epInfo URL and parses the TVDB
        XML file into the shows dict in layout:
        shows[series_id][season_number][episode_number]
        """

        if self.config['language'] is None:
            log().debug('Config language is none, using show language')
            if language is None:
                raise tvdb_error("config['language'] was None, this should not happen")
            getShowInLanguage = language
        else:
            log().debug(
                'Configured language %s override show language of %s' % (
                    self.config['language'],
                    language
                )
            )
            getShowInLanguage = self.config['language']

        # Parse show information
        log().debug('Getting all series data for %s' % (sid))
        seriesInfoEt = self._getetsrc(
            self.config['url_seriesInfo'] % (sid, getShowInLanguage)
        )
        for curInfo in seriesInfoEt.findall("Series")[0]:
            tag = curInfo.tag.lower()
            value = curInfo.text

            if value is not None:
                if tag in ['banner', 'fanart', 'poster']:
                    value = self.config['url_artworkPrefix'] % (value)
                else:
                    value = self._cleanData(value)

            self._setShowData(sid, tag, value)

        # Parse banners
        if self.config['banners_enabled']:
            self._parseBanners(sid)

        # Parse actors
        if self.config['actors_enabled']:
            self._parseActors(sid)

        # Parse episode data
        log().debug('Getting all episodes of %s' % (sid))

        if self.config['useZip']:
            url = self.config['url_epInfo_zip'] % (sid, language)
        else:
            url = self.config['url_epInfo'] % (sid, language)

        epsEt = self._getetsrc( url, language=language)

        for cur_ep in epsEt.findall("Episode"):

            if self.config['dvdorder']:
                log().debug('Using DVD ordering.')
                use_dvd = cur_ep.find('DVD_season').text != None and cur_ep.find('DVD_episodenumber').text != None
            else:
                use_dvd = False

            if use_dvd:
                elem_seasnum, elem_epno = cur_ep.find('DVD_season'), cur_ep.find('DVD_episodenumber')
            else:
                elem_seasnum, elem_epno = cur_ep.find('SeasonNumber'), cur_ep.find('EpisodeNumber')

            if elem_seasnum is None or elem_epno is None:
                log().warning("An episode has incomplete season/episode number (season: %r, episode: %r)" % (
                    elem_seasnum, elem_epno))
                log().debug(
                    " ".join(
                        "%r is %r" % (child.tag, child.text) for child in cur_ep.getchildren()))
                # TODO: Should this happen?
                continue # Skip to next episode

            # float() is because https://github.com/dbr/tvnamer/issues/95 - should probably be fixed in TVDB data
            seas_no = int(float(elem_seasnum.text))
            ep_no = int(float(elem_epno.text))

            for cur_item in cur_ep.getchildren():
                tag = cur_item.tag.lower()
                value = cur_item.text
                if value is not None:
                    if tag == 'filename':
                        value = self.config['url_artworkPrefix'] % (value)
                    else:
                        value = self._cleanData(value)
                self._setItem(sid, seas_no, ep_no, tag, value)

    def _nameToSid(self, name):
        """Takes show name, returns the correct series ID (if the show has
        already been grabbed), or grabs all episodes and returns
        the correct SID.
        """
        if name in self.corrections:
            log().debug('Correcting %s to %s' % (name, self.corrections[name]) )
            sid = self.corrections[name]
        else:
            log().debug('Getting show %s' % (name))
            selected_series = self._getSeries( name )
            sname, sid = selected_series['seriesname'], selected_series['id']
            log().debug('Got %(seriesname)s, id %(id)s' % selected_series)

            self.corrections[name] = sid
            self._getShowData(selected_series['id'], selected_series['language'])

        return sid

    def __getitem__(self, key):
        """Handles tvdb_instance['seriesname'] calls.
        The dict index should be the show id
        """
        if isinstance(key, (int, long)):
            # Item is integer, treat as show id
            if key not in self.shows:
                self._getShowData(key, self.config['language'])
            return self.shows[key]
        
        key = key.lower() # make key lower case
        sid = self._nameToSid(key)
        log().debug('Got series id %s' % (sid))
        return self.shows[sid]

    def __repr__(self):
        return str(self.shows)


def main():
    """Simple example of using tvdb_api - it just
    grabs an episode name interactively.
    """
    import logging
    logging.basicConfig(level=logging.DEBUG)

    tvdb_instance = Tvdb(interactive=True, cache=False)
    print tvdb_instance['Lost']['seriesname']
    print tvdb_instance['Lost'][1][4]['episodename']

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = tvdb_cache
#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:unlicense (http://unlicense.org/)

"""
urllib2 caching handler
Modified from http://code.activestate.com/recipes/491261/
"""
from __future__ import with_statement

__author__ = "dbr/Ben"
__version__ = "1.9"

import os
import time
import errno
import httplib
import urllib2
import StringIO
from hashlib import md5
from threading import RLock

cache_lock = RLock()

def locked_function(origfunc):
    """Decorator to execute function under lock"""
    def wrapped(*args, **kwargs):
        cache_lock.acquire()
        try:
            return origfunc(*args, **kwargs)
        finally:
            cache_lock.release()
    return wrapped

def calculate_cache_path(cache_location, url):
    """Checks if [cache_location]/[hash_of_url].headers and .body exist
    """
    thumb = md5(url).hexdigest()
    header = os.path.join(cache_location, thumb + ".headers")
    body = os.path.join(cache_location, thumb + ".body")
    return header, body

def check_cache_time(path, max_age):
    """Checks if a file has been created/modified in the [last max_age] seconds.
    False means the file is too old (or doesn't exist), True means it is
    up-to-date and valid"""
    if not os.path.isfile(path):
        return False
    cache_modified_time = os.stat(path).st_mtime
    time_now = time.time()
    if cache_modified_time < time_now - max_age:
        # Cache is old
        return False
    else:
        return True

@locked_function
def exists_in_cache(cache_location, url, max_age):
    """Returns if header AND body cache file exist (and are up-to-date)"""
    hpath, bpath = calculate_cache_path(cache_location, url)
    if os.path.exists(hpath) and os.path.exists(bpath):
        return(
            check_cache_time(hpath, max_age)
            and check_cache_time(bpath, max_age)
        )
    else:
        # File does not exist
        return False

@locked_function
def store_in_cache(cache_location, url, response):
    """Tries to store response in cache."""
    hpath, bpath = calculate_cache_path(cache_location, url)
    try:
        outf = open(hpath, "wb")
        headers = str(response.info())
        outf.write(headers)
        outf.close()

        outf = open(bpath, "wb")
        outf.write(response.read())
        outf.close()
    except IOError:
        return True
    else:
        return False
        
@locked_function
def delete_from_cache(cache_location, url):
    """Deletes a response in cache."""
    hpath, bpath = calculate_cache_path(cache_location, url)
    try:
        if os.path.exists(hpath):
            os.remove(hpath)
        if os.path.exists(bpath):
            os.remove(bpath)
    except IOError:
        return True
    else:
        return False

class CacheHandler(urllib2.BaseHandler):
    """Stores responses in a persistant on-disk cache.

    If a subsequent GET request is made for the same URL, the stored
    response is returned, saving time, resources and bandwidth
    """
    @locked_function
    def __init__(self, cache_location, max_age = 21600):
        """The location of the cache directory"""
        self.max_age = max_age
        self.cache_location = cache_location
        if not os.path.exists(self.cache_location):
            try:
                os.mkdir(self.cache_location)
            except OSError, e:
                if e.errno == errno.EEXIST and os.path.isdir(self.cache_location):
                    # File exists, and it's a directory,
                    # another process beat us to creating this dir, that's OK.
                    pass
                else:
                    # Our target dir is already a file, or different error,
                    # relay the error!
                    raise

    def default_open(self, request):
        """Handles GET requests, if the response is cached it returns it
        """
        if request.get_method() is not "GET":
            return None # let the next handler try to handle the request

        if exists_in_cache(
            self.cache_location, request.get_full_url(), self.max_age
        ):
            return CachedResponse(
                self.cache_location,
                request.get_full_url(),
                set_cache_header = True
            )
        else:
            return None

    def http_response(self, request, response):
        """Gets a HTTP response, if it was a GET request and the status code
        starts with 2 (200 OK etc) it caches it and returns a CachedResponse
        """
        if (request.get_method() == "GET"
            and str(response.code).startswith("2")
        ):
            if 'x-local-cache' not in response.info():
                # Response is not cached
                set_cache_header = store_in_cache(
                    self.cache_location,
                    request.get_full_url(),
                    response
                )
            else:
                set_cache_header = True

            return CachedResponse(
                self.cache_location,
                request.get_full_url(),
                set_cache_header = set_cache_header
            )
        else:
            return response

class CachedResponse(StringIO.StringIO):
    """An urllib2.response-like object for cached responses.

    To determine if a response is cached or coming directly from
    the network, check the x-local-cache header rather than the object type.
    """

    @locked_function
    def __init__(self, cache_location, url, set_cache_header=True):
        self.cache_location = cache_location
        hpath, bpath = calculate_cache_path(cache_location, url)

        StringIO.StringIO.__init__(self, file(bpath, "rb").read())

        self.url     = url
        self.code    = 200
        self.msg     = "OK"
        headerbuf = file(hpath, "rb").read()
        if set_cache_header:
            headerbuf += "x-local-cache: %s\r\n" % (bpath)
        self.headers = httplib.HTTPMessage(StringIO.StringIO(headerbuf))

    def info(self):
        """Returns headers
        """
        return self.headers

    def geturl(self):
        """Returns original URL
        """
        return self.url

    @locked_function
    def recache(self):
        new_request = urllib2.urlopen(self.url)
        set_cache_header = store_in_cache(
            self.cache_location,
            new_request.url,
            new_request
        )
        CachedResponse.__init__(self, self.cache_location, self.url, True)

    @locked_function
    def delete_cache(self):
        delete_from_cache(
            self.cache_location,
            self.url
        )
    

if __name__ == "__main__":
    def main():
        """Quick test/example of CacheHandler"""
        opener = urllib2.build_opener(CacheHandler("/tmp/"))
        response = opener.open("http://google.com")
        print response.headers
        print "Response:", response.read()

        response.recache()
        print response.headers
        print "After recache:", response.read()

        # Test usage in threads
        from threading import Thread
        class CacheThreadTest(Thread):
            lastdata = None
            def run(self):
                req = opener.open("http://google.com")
                newdata = req.read()
                if self.lastdata is None:
                    self.lastdata = newdata
                assert self.lastdata == newdata, "Data was not consistent, uhoh"
                req.recache()
        threads = [CacheThreadTest() for x in range(50)]
        print "Starting threads"
        [t.start() for t in threads]
        print "..done"
        print "Joining threads"
        [t.join() for t in threads]
        print "..done"
    main()

########NEW FILE########
__FILENAME__ = tvdb_exceptions
#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:unlicense (http://unlicense.org/)

"""Custom exceptions used or raised by tvdb_api
"""

__author__ = "dbr/Ben"
__version__ = "1.9"

__all__ = ["tvdb_error", "tvdb_userabort", "tvdb_shownotfound",
"tvdb_seasonnotfound", "tvdb_episodenotfound", "tvdb_attributenotfound"]

class tvdb_exception(Exception):
    """Any exception generated by tvdb_api
    """
    pass

class tvdb_error(tvdb_exception):
    """An error with thetvdb.com (Cannot connect, for example)
    """
    pass

class tvdb_userabort(tvdb_exception):
    """User aborted the interactive selection (via
    the q command, ^c etc)
    """
    pass

class tvdb_shownotfound(tvdb_exception):
    """Show cannot be found on thetvdb.com (non-existant show)
    """
    pass

class tvdb_seasonnotfound(tvdb_exception):
    """Season cannot be found on thetvdb.com
    """
    pass

class tvdb_episodenotfound(tvdb_exception):
    """Episode cannot be found on thetvdb.com
    """
    pass

class tvdb_attributenotfound(tvdb_exception):
    """Raised if an episode does not have the requested
    attribute (such as a episode name)
    """
    pass

########NEW FILE########
__FILENAME__ = tvdb_ui
#!/usr/bin/env python
#encoding:utf-8
#author:dbr/Ben
#project:tvdb_api
#repository:http://github.com/dbr/tvdb_api
#license:unlicense (http://unlicense.org/)

"""Contains included user interfaces for Tvdb show selection.

A UI is a callback. A class, it's __init__ function takes two arguments:

- config, which is the Tvdb config dict, setup in tvdb_api.py
- log, which is Tvdb's logger instance (which uses the logging module). You can
call log.info() log.warning() etc

It must have a method "selectSeries", this is passed a list of dicts, each dict
contains the the keys "name" (human readable show name), and "sid" (the shows
ID as on thetvdb.com). For example:

[{'name': u'Lost', 'sid': u'73739'},
 {'name': u'Lost Universe', 'sid': u'73181'}]

The "selectSeries" method must return the appropriate dict, or it can raise
tvdb_userabort (if the selection is aborted), tvdb_shownotfound (if the show
cannot be found).

A simple example callback, which returns a random series:

>>> import random
>>> from tvdb_ui import BaseUI
>>> class RandomUI(BaseUI):
...    def selectSeries(self, allSeries):
...            import random
...            return random.choice(allSeries)

Then to use it..

>>> from tvdb_api import Tvdb
>>> t = Tvdb(custom_ui = RandomUI)
>>> random_matching_series = t['Lost']
>>> type(random_matching_series)
<class 'tvdb_api.Show'>
"""

__author__ = "dbr/Ben"
__version__ = "1.9"

import logging
import warnings

from tvdb_exceptions import tvdb_userabort

def log():
    return logging.getLogger(__name__)

class BaseUI:
    """Default non-interactive UI, which auto-selects first results
    """
    def __init__(self, config, log = None):
        self.config = config
        if log is not None:
            warnings.warn("the UI's log parameter is deprecated, instead use\n"
                "use import logging; logging.getLogger('ui').info('blah')\n"
                "The self.log attribute will be removed in the next version")
            self.log = logging.getLogger(__name__)

    def selectSeries(self, allSeries):
        return allSeries[0]


class ConsoleUI(BaseUI):
    """Interactively allows the user to select a show from a console based UI
    """

    def _displaySeries(self, allSeries, limit = 6):
        """Helper function, lists series with corresponding ID
        """
        if limit is not None:
            toshow = allSeries[:limit]
        else:
            toshow = allSeries

        print "TVDB Search Results:"
        for i, cshow in enumerate(toshow):
            i_show = i + 1 # Start at more human readable number 1 (not 0)
            log().debug('Showing allSeries[%s], series %s)' % (i_show, allSeries[i]['seriesname']))
            if i == 0:
                extra = " (default)"
            else:
                extra = ""

            print "%s -> %s [%s] # http://thetvdb.com/?tab=series&id=%s&lid=%s%s" % (
                i_show,
                cshow['seriesname'].encode("UTF-8", "ignore"),
                cshow['language'].encode("UTF-8", "ignore"),
                str(cshow['id']),
                cshow['lid'],
                extra
            )

    def selectSeries(self, allSeries):
        self._displaySeries(allSeries)

        if len(allSeries) == 1:
            # Single result, return it!
            print "Automatically selecting only result"
            return allSeries[0]

        if self.config['select_first'] is True:
            print "Automatically returning first search result"
            return allSeries[0]

        while True: # return breaks this loop
            try:
                print "Enter choice (first number, return for default, 'all', ? for help):"
                ans = raw_input()
            except KeyboardInterrupt:
                raise tvdb_userabort("User aborted (^c keyboard interupt)")
            except EOFError:
                raise tvdb_userabort("User aborted (EOF received)")

            log().debug('Got choice of: %s' % (ans))
            try:
                selected_id = int(ans) - 1 # The human entered 1 as first result, not zero
            except ValueError: # Input was not number
                if len(ans.strip()) == 0:
                    # Default option
                    log().debug('Default option, returning first series')
                    return allSeries[0]
                if ans == "q":
                    log().debug('Got quit command (q)')
                    raise tvdb_userabort("User aborted ('q' quit command)")
                elif ans == "?":
                    print "## Help"
                    print "# Enter the number that corresponds to the correct show."
                    print "# a - display all results"
                    print "# all - display all results"
                    print "# ? - this help"
                    print "# q - abort tvnamer"
                    print "# Press return with no input to select first result"
                elif ans.lower() in ["a", "all"]:
                    self._displaySeries(allSeries, limit = None)
                else:
                    log().debug('Unknown keypress %s' % (ans))
            else:
                log().debug('Trying to return ID: %d' % (selected_id))
                try:
                    return allSeries[selected_id]
                except IndexError:
                    log().debug('Invalid show number entered!')
                    print "Invalid number (%s) selected!"
                    self._displaySeries(allSeries)


########NEW FILE########
