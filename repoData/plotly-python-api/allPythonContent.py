__FILENAME__ = plotly
import requests
import json
import warnings

from .version import __version__

def signup(un, email):
	''' Remote signup to plot.ly and plot.ly API
	Returns:
		:param r with r['tmp_pw']: Temporary password to access your plot.ly acount
		:param r['api_key']: A key to use the API with
		
	Full docs and examples at https://plot.ly/API
	:un: <string> username
	:email: <string> email address
	'''
	payload = {'version': __version__, 'un': un, 'email': email, 'platform':'Python'}
	r = requests.post('https://plot.ly/apimkacct', data=payload)
	r.raise_for_status()
	r = json.loads(r.text)
	if 'error' in r and r['error'] != '':
		print(r['error'])
	if 'warning' in r and r['warning'] != '':
		warnings.warn(r['warning'])
	if 'message' in r and r['message'] != '':
		print(r['message'])

	return r

class plotly:
	def __init__(self, username_or_email=None, key=None,verbose=True):
		''' plotly constructor. Supply username or email and api key.
		'''
		self.un = username_or_email
		self.key = key
		self.__filename = None
		self.__fileopt = None
		self.verbose = verbose
		self.open = True

	def ion(self):
		self.open = True
	def ioff(self):
		self.open = False

	def iplot(self, *args, **kwargs):
		''' for use in ipython notebooks '''
		res = self.__callplot(*args, **kwargs)
		width = kwargs.get('width', 600)
		height = kwargs.get('height', 450)
		s = '<iframe height="%s" id="igraph" scrolling="no" seamless="seamless" src="%s" width="%s"></iframe>' %\
			(height+50, "/".join(map(str, [res['url'], width, height])), width+50)
		try:
			# see, if we are in the SageMath Cloud
			from sage_salvus import html
			return html(s, hide=False)
		except:
			pass
		try:
			from IPython.display import HTML
			return HTML(s)
		except:
			return s

	def plot(self, *args, **kwargs):
		res = self.__callplot(*args, **kwargs)
		if 'error' in res and res['error'] == '' and self.open:
			from webbrowser import open as wbopen
			wbopen(res['url'])
		return res

	def __callplot(self, *args, **kwargs):
		''' Make a plot in plotly.
		Two interfaces:
			1 - ploty.plot(x1, y1[,x2,y2,...],**kwargs)
			where x1, y1, .... are lists, numpy arrays
			2 - plot.plot([data1[, data2, ...], **kwargs)
			where data1 is a dict that is at least
			{'x': x1, 'y': y1} but can contain more styling and sharing options.
			kwargs accepts:
				filename
				fileopt
				style
				layout
			See https://plot.ly/API for details.
		Returns:
			:param r with r['url']: A URL that displays the generated plot
			:param r['filename']: The filename of the plot in your plotly account.
		'''

		un = kwargs['un'] if 'un' in kwargs else self.un
		key = kwargs['key'] if 'key' in kwargs else self.key
		if not un or not key:
			raise Exception('Not Signed in')

		if not 'filename' in kwargs:
			kwargs['filename'] = self.__filename
		if not 'fileopt' in kwargs:
			kwargs['fileopt'] = self.__fileopt
	
		origin = 'plot'
		r = self.__makecall(args, un, key, origin, kwargs)
		return r

	def layout(self, *args, **kwargs):
		''' Style the layout of a Plotly plot.
			ploty.layout(layout,**kwargs)
			:param layout - a dict that customizes the style of the layout,
							the axes, and the legend.
			:param kwargs - accepts:
				filename
			See https://plot.ly/API for details.
		Returns:
			:param r with r['url']: A URL that displays the generated plot
			:param r['filename']: The filename of the plot in your plotly account.
		'''

		un = kwargs['un'] if 'un' in kwargs.keys() else self.un
		key = kwargs['un'] if 'key' in kwargs.keys() else self.key
		if not un or not key:
			raise Exception('Not Signed in')
		if not 'filename' in kwargs.keys():
			kwargs['filename'] = self.__filename
		if not 'fileopt' in kwargs.keys():
			kwargs['fileopt'] = self.__fileopt
	
		origin = 'layout'
		r = self.__makecall(args, un, key, origin, kwargs)
		return r

	def style(self, *args, **kwargs):
		''' Style the data traces of a Plotly plot.
			ploty.style([data1,[,data2,...],**kwargs)
			:param data1 - a dict that customizes the style of the i'th trace
			:param kwargs - accepts:
				filename
			See https://plot.ly/API for details.
		Returns:
			:param r with r['url']: A URL that displays the generated plot
			:param r['filename']: The filename of the plot in your plotly account.
		'''

		un = kwargs['un'] if 'un' in kwargs.keys() else self.un
		key = kwargs['un'] if 'key' in kwargs.keys() else self.key
		if not un or not key:
			raise Exception('Not Signed in')
		if not 'filename' in kwargs.keys():
			kwargs['filename'] = self.__filename
		if not 'fileopt' in kwargs.keys():
			kwargs['fileopt'] = self.__fileopt
	
		origin = 'style'
		r = self.__makecall(args, un, key, origin, kwargs)
		return r

	class __plotlyJSONEncoder(json.JSONEncoder):
		def numpyJSONEncoder(self, obj):
			try:
				import numpy
				if type(obj).__module__.split('.')[0] == numpy.__name__:
					l = obj.tolist()
					d = self.datetimeJSONEncoder(l) 
					return d if d is not None else l
			except:
				pass
			return None
		def datetimeJSONEncoder(self, obj):
			# if datetime or iterable of datetimes, convert to a string that plotly understands
			# format as %Y-%m-%d %H:%M:%S.%f, %Y-%m-%d %H:%M:%S, or %Y-%m-%d depending on what non-zero resolution was provided
			import datetime
			try:
				if isinstance(obj,(datetime.datetime, datetime.date)):
					if obj.microsecond != 0:
						return obj.strftime('%Y-%m-%d %H:%M:%S.%f')
					elif obj.second != 0 or obj.minute != 0 or obj.hour != 0:
						return obj.strftime('%Y-%m-%d %H:%M:%S')
					else:
						return obj.strftime('%Y-%m-%d')
				elif isinstance(obj[0],(datetime.datetime, datetime.date)):
					return [o.strftime('%Y-%m-%d %H:%M:%S.%f') if o.microsecond != 0 else
						o.strftime('%Y-%m-%d %H:%M:%S') if o.second != 0 or o.minute != 0 or o.hour != 0 else
						o.strftime('%Y-%m-%d')
						for o in obj]
			except:
				pass
			return None
		def pandasJSONEncoder(self, obj):
			try:
				import pandas
				if isinstance(obj, pandas.Series):
					return obj.tolist()
			except:
				pass
			return None
		def sageJSONEncoder(self, obj):
			try:
				from sage.all import RR, ZZ
				if obj in RR:
					return float(obj)
				elif obj in ZZ:
					return int(obj)
			except:
				pass
			return None
		def default(self, obj):
			try:
				return json.dumps(obj)
			except TypeError as e:
				encoders = (self.datetimeJSONEncoder, self.numpyJSONEncoder, self.pandasJSONEncoder, self.sageJSONEncoder)
				for encoder in encoders:
					s = encoder(obj)
					if s is not None:
						return s
				raise e
			return json.JSONEncoder.default(self,obj)

	def __makecall(self, args, un, key, origin, kwargs):
		platform = 'Python'

		args = json.dumps(args, cls=self.__plotlyJSONEncoder)
		kwargs = json.dumps(kwargs, cls=self.__plotlyJSONEncoder)
		url = 'https://plot.ly/clientresp'
		payload = {'platform': platform, 'version': __version__, 'args': args, 'un': un, 'key': key, 'origin': origin, 'kwargs': kwargs}
		r = requests.post(url, data=payload)
		r.raise_for_status()
		r = json.loads(r.text)
		if 'error' in r and r['error'] != '':
			print(r['error'])
		if 'warning' in r and r['warning'] != '':
			warnings.warn(r['warning'])
		if 'message' in r and r['message'] != '' and self.verbose:
			print(r['message'])
			
		return r




########NEW FILE########
__FILENAME__ = version
__version__ = '0.5.8'

########NEW FILE########
__FILENAME__ = plotly
import requests
import json
import warnings

from .version import __version__

def signup(un, email):
	''' Remote signup to plot.ly and plot.ly API
	Returns:
		:param r with r['tmp_pw']: Temporary password to access your plot.ly acount
		:param r['api_key']: A key to use the API with
		
	Full docs and examples at https://plot.ly/API
	:un: <string> username
	:email: <string> email address
	'''
	payload = {'version': __version__, 'un': un, 'email': email, 'platform':'Python'}
	r = requests.post('https://plot.ly/apimkacct', data=payload)
	r.raise_for_status()
	r = json.loads(r.text)
	if 'error' in r and r['error'] != '':
		print(r['error'])
	if 'warning' in r and r['warning'] != '':
		warnings.warn(r['warning'])
	if 'message' in r and r['message'] != '':
		print(r['message'])

	return r

class plotly:
	def __init__(self, username_or_email=None, key=None,verbose=True):
		''' plotly constructor. Supply username or email and api key.
		'''
		self.un = username_or_email
		self.key = key
		self.__filename = None
		self.__fileopt = None
		self.verbose = verbose
		self.open = True

	def ion(self):
		self.open = True
	def ioff(self):
		self.open = False

	def iplot(self, *args, **kwargs):
		''' for use in ipython notebooks '''
		res = self.__callplot(*args, **kwargs)
		width = kwargs.get('width', 600)
		height = kwargs.get('height', 450)
		s = '<iframe height="%s" id="igraph" scrolling="no" seamless="seamless" src="%s" width="%s"></iframe>' %\
			(height+50, "/".join(map(str, [res['url'], width, height])), width+50)
		try:
			# see, if we are in the SageMath Cloud
			from sage_salvus import html
			return html(s, hide=False)
		except:
			pass
		try:
			from IPython.display import HTML
			return HTML(s)
		except:
			return s

	def plot(self, *args, **kwargs):
		res = self.__callplot(*args, **kwargs)
		if 'error' in res and res['error'] == '' and self.open:
			from webbrowser import open as wbopen
			wbopen(res['url'])
		return res

	def __callplot(self, *args, **kwargs):
		''' Make a plot in plotly.
		Two interfaces:
			1 - ploty.plot(x1, y1[,x2,y2,...],**kwargs)
			where x1, y1, .... are lists, numpy arrays
			2 - plot.plot([data1[, data2, ...], **kwargs)
			where data1 is a dict that is at least
			{'x': x1, 'y': y1} but can contain more styling and sharing options.
			kwargs accepts:
				filename
				fileopt
				style
				layout
			See https://plot.ly/API for details.
		Returns:
			:param r with r['url']: A URL that displays the generated plot
			:param r['filename']: The filename of the plot in your plotly account.
		'''

		un = kwargs['un'] if 'un' in kwargs else self.un
		key = kwargs['key'] if 'key' in kwargs else self.key
		if not un or not key:
			raise Exception('Not Signed in')

		if not 'filename' in kwargs:
			kwargs['filename'] = self.__filename
		if not 'fileopt' in kwargs:
			kwargs['fileopt'] = self.__fileopt
	
		origin = 'plot'
		r = self.__makecall(args, un, key, origin, kwargs)
		return r

	def layout(self, *args, **kwargs):
		''' Style the layout of a Plotly plot.
			ploty.layout(layout,**kwargs)
			:param layout - a dict that customizes the style of the layout,
							the axes, and the legend.
			:param kwargs - accepts:
				filename
			See https://plot.ly/API for details.
		Returns:
			:param r with r['url']: A URL that displays the generated plot
			:param r['filename']: The filename of the plot in your plotly account.
		'''

		un = kwargs['un'] if 'un' in kwargs.keys() else self.un
		key = kwargs['un'] if 'key' in kwargs.keys() else self.key
		if not un or not key:
			raise Exception('Not Signed in')
		if not 'filename' in kwargs.keys():
			kwargs['filename'] = self.__filename
		if not 'fileopt' in kwargs.keys():
			kwargs['fileopt'] = self.__fileopt
	
		origin = 'layout'
		r = self.__makecall(args, un, key, origin, kwargs)
		return r

	def style(self, *args, **kwargs):
		''' Style the data traces of a Plotly plot.
			ploty.style([data1,[,data2,...],**kwargs)
			:param data1 - a dict that customizes the style of the i'th trace
			:param kwargs - accepts:
				filename
			See https://plot.ly/API for details.
		Returns:
			:param r with r['url']: A URL that displays the generated plot
			:param r['filename']: The filename of the plot in your plotly account.
		'''

		un = kwargs['un'] if 'un' in kwargs.keys() else self.un
		key = kwargs['un'] if 'key' in kwargs.keys() else self.key
		if not un or not key:
			raise Exception('Not Signed in')
		if not 'filename' in kwargs.keys():
			kwargs['filename'] = self.__filename
		if not 'fileopt' in kwargs.keys():
			kwargs['fileopt'] = self.__fileopt
	
		origin = 'style'
		r = self.__makecall(args, un, key, origin, kwargs)
		return r

	class __plotlyJSONEncoder(json.JSONEncoder):
		def numpyJSONEncoder(self, obj):
			try:
				import numpy
				if type(obj).__module__.split('.')[0] == numpy.__name__:
					l = obj.tolist()
					d = self.datetimeJSONEncoder(l) 
					return d if d is not None else l
			except:
				pass
			return None
		def datetimeJSONEncoder(self, obj):
			# if datetime or iterable of datetimes, convert to a string that plotly understands
			# format as %Y-%m-%d %H:%M:%S.%f, %Y-%m-%d %H:%M:%S, or %Y-%m-%d depending on what non-zero resolution was provided
			import datetime
			try:
				if isinstance(obj,(datetime.datetime, datetime.date)):
					if obj.microsecond != 0:
						return obj.strftime('%Y-%m-%d %H:%M:%S.%f')
					elif obj.second != 0 or obj.minute != 0 or obj.hour != 0:
						return obj.strftime('%Y-%m-%d %H:%M:%S')
					else:
						return obj.strftime('%Y-%m-%d')
				elif isinstance(obj[0],(datetime.datetime, datetime.date)):
					return [o.strftime('%Y-%m-%d %H:%M:%S.%f') if o.microsecond != 0 else
						o.strftime('%Y-%m-%d %H:%M:%S') if o.second != 0 or o.minute != 0 or o.hour != 0 else
						o.strftime('%Y-%m-%d')
						for o in obj]
			except:
				pass
			return None
		def pandasJSONEncoder(self, obj):
			try:
				import pandas
				if isinstance(obj, pandas.Series):
					return obj.tolist()
			except:
				pass
			return None
		def sageJSONEncoder(self, obj):
			try:
				from sage.all import RR, ZZ
				if obj in RR:
					return float(obj)
				elif obj in ZZ:
					return int(obj)
			except:
				pass
			return None
		def default(self, obj):
			try:
				return json.dumps(obj)
			except TypeError as e:
				encoders = (self.datetimeJSONEncoder, self.numpyJSONEncoder, self.pandasJSONEncoder, self.sageJSONEncoder)
				for encoder in encoders:
					s = encoder(obj)
					if s is not None:
						return s
				raise e
			return json.JSONEncoder.default(self,obj)

	def __makecall(self, args, un, key, origin, kwargs):
		platform = 'Python'

		args = json.dumps(args, cls=self.__plotlyJSONEncoder)
		kwargs = json.dumps(kwargs, cls=self.__plotlyJSONEncoder)
		url = 'https://plot.ly/clientresp'
		payload = {'platform': platform, 'version': __version__, 'args': args, 'un': un, 'key': key, 'origin': origin, 'kwargs': kwargs}
		r = requests.post(url, data=payload)
		r.raise_for_status()
		r = json.loads(r.text)
		if 'error' in r and r['error'] != '':
			print(r['error'])
		if 'warning' in r and r['warning'] != '':
			warnings.warn(r['warning'])
		if 'message' in r and r['message'] != '' and self.verbose:
			print(r['message'])
			
		return r




########NEW FILE########
__FILENAME__ = version
__version__ = '0.5.8'

########NEW FILE########
__FILENAME__ = plotly
import requests
import json
import warnings

from .version import __version__

def signup(un, email):
	''' Remote signup to plot.ly and plot.ly API
	Returns:
		:param r with r['tmp_pw']: Temporary password to access your plot.ly acount
		:param r['api_key']: A key to use the API with
		
	Full docs and examples at https://plot.ly/API
	:un: <string> username
	:email: <string> email address
	'''
	payload = {'version': __version__, 'un': un, 'email': email, 'platform':'Python'}
	r = requests.post('https://plot.ly/apimkacct', data=payload)
	r.raise_for_status()
	r = json.loads(r.text)
	if 'error' in r and r['error'] != '':
		print(r['error'])
	if 'warning' in r and r['warning'] != '':
		warnings.warn(r['warning'])
	if 'message' in r and r['message'] != '':
		print(r['message'])

	return r

class plotly:
	def __init__(self, username_or_email=None, key=None,verbose=True):
		''' plotly constructor. Supply username or email and api key.
		'''
		self.un = username_or_email
		self.key = key
		self.__filename = None
		self.__fileopt = None
		self.verbose = verbose
		self.open = True

	def ion(self):
		self.open = True
	def ioff(self):
		self.open = False

	def iplot(self, *args, **kwargs):
		''' for use in ipython notebooks '''
		res = self.__callplot(*args, **kwargs)
		width = kwargs.get('width', 600)
		height = kwargs.get('height', 450)
		s = '<iframe height="%s" id="igraph" scrolling="no" seamless="seamless" src="%s" width="%s"></iframe>' %\
			(height+50, "/".join(map(str, [res['url'], width, height])), width+50)
		try:
			# see, if we are in the SageMath Cloud
			from sage_salvus import html
			return html(s, hide=False)
		except:
			pass
		try:
			from IPython.display import HTML
			return HTML(s)
		except:
			return s

	def plot(self, *args, **kwargs):
		res = self.__callplot(*args, **kwargs)
		if 'error' in res and res['error'] == '' and self.open:
			from webbrowser import open as wbopen
			wbopen(res['url'])
		return res

	def __callplot(self, *args, **kwargs):
		''' Make a plot in plotly.
		Two interfaces:
			1 - ploty.plot(x1, y1[,x2,y2,...],**kwargs)
			where x1, y1, .... are lists, numpy arrays
			2 - plot.plot([data1[, data2, ...], **kwargs)
			where data1 is a dict that is at least
			{'x': x1, 'y': y1} but can contain more styling and sharing options.
			kwargs accepts:
				filename
				fileopt
				style
				layout
			See https://plot.ly/API for details.
		Returns:
			:param r with r['url']: A URL that displays the generated plot
			:param r['filename']: The filename of the plot in your plotly account.
		'''

		un = kwargs['un'] if 'un' in kwargs else self.un
		key = kwargs['key'] if 'key' in kwargs else self.key
		if not un or not key:
			raise Exception('Not Signed in')

		if not 'filename' in kwargs:
			kwargs['filename'] = self.__filename
		if not 'fileopt' in kwargs:
			kwargs['fileopt'] = self.__fileopt
	
		origin = 'plot'
		r = self.__makecall(args, un, key, origin, kwargs)
		return r

	def layout(self, *args, **kwargs):
		''' Style the layout of a Plotly plot.
			ploty.layout(layout,**kwargs)
			:param layout - a dict that customizes the style of the layout,
							the axes, and the legend.
			:param kwargs - accepts:
				filename
			See https://plot.ly/API for details.
		Returns:
			:param r with r['url']: A URL that displays the generated plot
			:param r['filename']: The filename of the plot in your plotly account.
		'''

		un = kwargs['un'] if 'un' in kwargs.keys() else self.un
		key = kwargs['un'] if 'key' in kwargs.keys() else self.key
		if not un or not key:
			raise Exception('Not Signed in')
		if not 'filename' in kwargs.keys():
			kwargs['filename'] = self.__filename
		if not 'fileopt' in kwargs.keys():
			kwargs['fileopt'] = self.__fileopt
	
		origin = 'layout'
		r = self.__makecall(args, un, key, origin, kwargs)
		return r

	def style(self, *args, **kwargs):
		''' Style the data traces of a Plotly plot.
			ploty.style([data1,[,data2,...],**kwargs)
			:param data1 - a dict that customizes the style of the i'th trace
			:param kwargs - accepts:
				filename
			See https://plot.ly/API for details.
		Returns:
			:param r with r['url']: A URL that displays the generated plot
			:param r['filename']: The filename of the plot in your plotly account.
		'''

		un = kwargs['un'] if 'un' in kwargs.keys() else self.un
		key = kwargs['un'] if 'key' in kwargs.keys() else self.key
		if not un or not key:
			raise Exception('Not Signed in')
		if not 'filename' in kwargs.keys():
			kwargs['filename'] = self.__filename
		if not 'fileopt' in kwargs.keys():
			kwargs['fileopt'] = self.__fileopt
	
		origin = 'style'
		r = self.__makecall(args, un, key, origin, kwargs)
		return r

	class __plotlyJSONEncoder(json.JSONEncoder):
		def numpyJSONEncoder(self, obj):
			try:
				import numpy
				if type(obj).__module__.split('.')[0] == numpy.__name__:
					l = obj.tolist()
					d = self.datetimeJSONEncoder(l) 
					return d if d is not None else l
			except:
				pass
			return None
		def datetimeJSONEncoder(self, obj):
			# if datetime or iterable of datetimes, convert to a string that plotly understands
			# format as %Y-%m-%d %H:%M:%S.%f, %Y-%m-%d %H:%M:%S, or %Y-%m-%d depending on what non-zero resolution was provided
			import datetime
			try:
				if isinstance(obj,(datetime.datetime, datetime.date)):
					if obj.microsecond != 0:
						return obj.strftime('%Y-%m-%d %H:%M:%S.%f')
					elif obj.second != 0 or obj.minute != 0 or obj.hour != 0:
						return obj.strftime('%Y-%m-%d %H:%M:%S')
					else:
						return obj.strftime('%Y-%m-%d')
				elif isinstance(obj[0],(datetime.datetime, datetime.date)):
					return [o.strftime('%Y-%m-%d %H:%M:%S.%f') if o.microsecond != 0 else
						o.strftime('%Y-%m-%d %H:%M:%S') if o.second != 0 or o.minute != 0 or o.hour != 0 else
						o.strftime('%Y-%m-%d')
						for o in obj]
			except:
				pass
			return None
		def pandasJSONEncoder(self, obj):
			try:
				import pandas
				if isinstance(obj, pandas.Series):
					return obj.tolist()
			except:
				pass
			return None
		def sageJSONEncoder(self, obj):
			try:
				from sage.all import RR, ZZ
				if obj in RR:
					return float(obj)
				elif obj in ZZ:
					return int(obj)
			except:
				pass
			return None
		def default(self, obj):
			try:
				return json.dumps(obj)
			except TypeError as e:
				encoders = (self.datetimeJSONEncoder, self.numpyJSONEncoder, self.pandasJSONEncoder, self.sageJSONEncoder)
				for encoder in encoders:
					s = encoder(obj)
					if s is not None:
						return s
				raise e
			return json.JSONEncoder.default(self,obj)

	def __makecall(self, args, un, key, origin, kwargs):
		platform = 'Python'

		args = json.dumps(args, cls=self.__plotlyJSONEncoder)
		kwargs = json.dumps(kwargs, cls=self.__plotlyJSONEncoder)
		url = 'https://plot.ly/clientresp'
		payload = {'platform': platform, 'version': __version__, 'args': args, 'un': un, 'key': key, 'origin': origin, 'kwargs': kwargs}
		r = requests.post(url, data=payload)
		r.raise_for_status()
		r = json.loads(r.text)
		if 'error' in r and r['error'] != '':
			print(r['error'])
		if 'warning' in r and r['warning'] != '':
			warnings.warn(r['warning'])
		if 'message' in r and r['message'] != '' and self.verbose:
			print(r['message'])
			
		return r




########NEW FILE########
__FILENAME__ = version
__version__ = '0.5.9'

########NEW FILE########
__FILENAME__ = exceptions
"""
exceptions
==========

A module that contains plotly's exception hierarchy.

message (required!) (should be root message + caller message)
info: (required!)
    path_to_error (required!)
    minimal_message (required!)

- minimal_message is set inside this module, should not be set elsewhere

- message is set inside this module, should not be set elsewhere


"""


## Base Plotly Error ##

class PlotlyError(Exception):
    pass


## Graph Objects Errors ##

class PlotlyGraphObjectError(PlotlyError):
    def __init__(self, message='', path=None, notes=None, plain_message=''):
        self.message = message
        self.plain_message=plain_message
        if isinstance(path, list):
            self.path = path
        elif path is None:
            self.path = []
        else:
            self.path = [path]
        if isinstance(notes, list):
            self.notes = notes
        elif notes is None:
            self.notes = []
        else:
            self.notes = [notes]
        super(PlotlyGraphObjectError, self).__init__(message)
        self.prepare()

    def add_note(self, note):
        if isinstance(note, list):
            self.notes += note
        else:
            self.notes += [note]

    def add_to_error_path(self, path):
        if isinstance(path, list):
            self.path = path + self.path
        else:
            self.path = [path] + self.path

    def prepare(self):
        message = self.message
        message += "\n\nPath To Error:\n["
        for iii, key in enumerate(self.path):
            message += repr(key)
            if iii < len(self.path) - 1:
                message += "]["
        message += "]"
        if len(self.notes):
            message += "\n\nAdditional Notes:\n{}".format("\n".join(self.notes))
        if len(self.args) > 1:
            self.args = (message, self.args[1:][0])
        else:
            self.args = message,


class PlotlyDictKeyError(PlotlyGraphObjectError):
    def __init__(self, obj='', key='', **kwargs):
        message = (
            "Invalid key, '{key}', for class, '{obj_name}'.\n\nRun "
            "'help(plotly.graph_objs.{obj_name})' for more information."
            "".format(key=key, obj_name=obj.__class__.__name__)
        )
        plain_message="invalid key, '{}', in dictionary".format(key)
        super(PlotlyDictKeyError, self).__init__(message=message,
                                                 path=[key],
                                                 plain_message=plain_message,
                                                 **kwargs)


class PlotlyDictValueError(PlotlyGraphObjectError):
    def __init__(self, obj='', key='', value='', val_types='', **kwargs):
        message = (
            "Invalid value type, '{value_name}', associated with key, "
            "'{key}', for class, '{obj_name}'.\nValid types for this key "
            "are:\n '{val_types}'.\n\nRun 'help(plotly.graph_objs.{obj_name})' "
            "for more information.".format(key=key,
                                           value_name=value.__class__.__name__,
                                           val_types=val_types,
                                           obj_name=obj.__class__.__name__)
        )
        plain_message = ("invalid value associated with key, '{}', in "
                         "dictionary".format(key))
        super(PlotlyDictValueError, self).__init__(message=message,
                                                   plain_message=plain_message,
                                                   path=[key],
                                                   **kwargs)


class PlotlyListEntryError(PlotlyGraphObjectError):
    def __init__(self, obj='', index='', entry='', **kwargs):
        message = (
            "The entry at index, '{}', is invalid in a '{}' object"
            "".format(index, obj.__class__.__name__)
        )
        plain_message = (
            "The entry at index, '{}', is invalid."
            "".format(index)
        )
        super(PlotlyListEntryError, self).__init__(message=message,
                                                   plain_message=plain_message,
                                                   path=[index],
                                                   **kwargs)


class PlotlyDataTypeError(PlotlyGraphObjectError):
    def __init__(self, obj='', index='', **kwargs):
        message = (
                "The entry at index, '{}', is invalid because it does not "
                "contain a valid 'type' key-value. This is required for valid "
                "'{}' lists.".format(index, obj.__class__.__name__)
        )
        plain_message = (
                "The entry at index, '{}', is invalid because it does not "
                "contain a valid 'type' key-value. This is required for "
                "valid data lists.".format(index))
        super(PlotlyDataTypeError, self).__init__(message=message,
                                                  plain_message=plain_message,
                                                  path=[index],
                                                  **kwargs)


## Local Config Errors ##

class PlotlyLocalError(PlotlyError):
    pass


class PlotlyLocalCredentialsError(PlotlyLocalError):
    def __init__(self):
        message = ("\n"
            "Couldn't find a 'username', 'api-key' pair for you on your local "
            "machine. To sign in temporarily (until you stop running Python), "
            "run:\n"
            ">>> import plotly.plotly as py\n"
            ">>> py.sign_in('username', 'api_key')\n\n"
            "Even better, save your credentials permanently using the 'tools' "
            "module:\n"
            ">>> import plotly.tools as tls\n"
            ">>> tls.set_credentials_file(username='username', api_key='api-key')\n\n"
            "For more help, see https://plot.ly/python.\n")
        super(PlotlyLocalCredentialsError, self).__init__(message)


## Server Errors ##

class PlotlyServerError(PlotlyError):
    pass


class PlotlyConnectionError(PlotlyServerError):
    pass


class PlotlyCredentialError(PlotlyServerError):
    pass


class PlotlyAccountError(PlotlyServerError):
    pass


class PlotlyRateLimitError(PlotlyServerError):
    pass

########NEW FILE########
__FILENAME__ = graph_objs
"""
graph_objs
==========

A module that understands plotly language and can manage the json
structures. This module defines two base classes: PlotlyList and PlotlyDict.
The former inherits from `list` and the latter inherits from `dict`. and is
A third structure, PlotlyTrace, is also considered a base class for all
subclassing 'trace' objects like Scatter, Box, Bar, etc. It is also not meant
to instantiated by users.

Goals of this module:
---------------------

* A dict/list with the same entries as a PlotlyDict/PlotlyList should look
exactly the same once a call is made to plot.

* Only mutate object structure when users ASK for it.

* It should always be possible to get a dict/list JSON representation from a
graph_objs object and it should always be possible to make a graph_objs object
from a dict/list JSON representation.

"""
import warnings
import collections
import json
import textwrap
from .. import exceptions
from .. import utils

__all__ = ["Data",
           "Annotations",
           "Bar",
           "Box",
           "Contour",
           "Heatmap",
           "Histogram",
           "Histogram2d",
           "Histogram2dContour",
           "Scatter",
           "Annotation",
           "AngularAxis",
           "ColorBar",
           "Contours",
           "ErrorX",
           "ErrorY",
           "Figure",
           "Font",
           "Layout",
           "Legend",
           "Line",
           "Margin",
           "Marker",
           "RadialAxis",
           "Stream",
           "Trace",
           "XAxis",
           "XBins",
           "YAxis",
           "YBins"]

# TODO: BIG ONE, how should exceptions bubble up in this inheritance scheme?
    # TODO: related, WHAT exceptions should bubble up?

from pkg_resources import resource_string
s = resource_string('plotly',
                    'graph_reference/graph_objs_meta.json').decode('utf-8')
INFO = json.loads(s, object_pairs_hook=collections.OrderedDict)

INFO = utils.decode_unicode(INFO)

# define how to map from keys in INFO to a class
# mapping: (n->m, m < n)
KEY_TO_NAME = dict(
    plotlylist='PlotlyList',
    data='Data',
    angularaxis='AngularAxis',
    annotations='Annotations',
    area='Area',
    plotlydict='PlotlyDict',
    plotlytrace='PlotlyTrace',
    bar='Bar',
    box='Box',
    contour='Contour',
    heatmap='Heatmap',
    histogram='Histogram',
    histogram2d='Histogram2d',
    histogram2dcontour='Histogram2dContour',
    scatter='Scatter',
    annotation='Annotation',
    colorbar='ColorBar',
    contours='Contours',
    error_x='ErrorX',
    error_y='ErrorY',
    figure='Figure',
    font='Font',
    layout='Layout',
    legend='Legend',
    line='Line',
    margin='Margin',
    marker='Marker',
    radialaxis='RadialAxis',
    stream='Stream',
    trace='Trace',
    textfont='Font',
    tickfont='Font',
    titlefont='Font',
    xaxis='XAxis',
    xbins='XBins',
    yaxis='YAxis',
    ybins='YBins'
)

# define how to map from a class name to a key name in INFO
# mapping: (n->n)
NAME_TO_KEY = dict(
    PlotlyList='plotlylist',
    Data='data',
    AngularAxis='angularaxis',
    Annotations='annotations',
    PlotlyDict='plotlydict',
    PlotlyTrace='plotlytrace',
    Area='area',
    Bar='bar',
    Box='box',
    Contour='contour',
    Heatmap='heatmap',
    Histogram='histogram',
    Histogram2d='histogram2d',
    Histogram2dContour='histogram2dcontour',
    Scatter='scatter',
    Annotation='annotation',
    ColorBar='colorbar',
    Contours='contours',
    ErrorX='error_x',
    ErrorY='error_y',
    Figure='figure',
    Font='font',
    Layout='layout',
    Legend='legend',
    Line='line',
    Margin='margin',
    Marker='marker',
    RadialAxis='radialaxis',
    Stream='stream',
    Trace='trace',
    XAxis='xaxis',
    XBins='xbins',
    YAxis='yaxis',
    YBins='ybins'
)


class ListMeta(type):
    """A meta class for PlotlyList class creation.

    The sole purpose of this meta class is to properly create the __doc__
    attribute so that running help(Obj), where Obj is a subclass of PlotlyList,
    will return useful information for that object.

    """

    def __new__(mcs, name, bases, attrs):
        doc = attrs['__doc__']
        tab_size = 4
        min_indent = min([len(a) - len(b)
                          for a, b in zip(doc.splitlines(),
                                          [l.lstrip()
                                           for l in doc.splitlines()])])
        doc = "".join([line[min_indent:] + '\n' for line in doc.splitlines()])
        # Add section header for method list...
        doc += "Quick method reference:\n\n"
        doc += "\t{}.".format(name) + "\n\t{}.".format(name).join(
            ["update(changes)", "strip_style()", "get_data()",
             "to_graph_objs()", "validate()", "to_string()",
             "force_clean()"]) + "\n\n"
        attrs['__doc__'] = doc.expandtabs(tab_size)
        return super(ListMeta, mcs).__new__(mcs, name, bases, attrs)


class DictMeta(type):
    """A meta class for PlotlyDict class creation.

    The sole purpose of this meta class is to properly create the __doc__
    attribute so that running help(Obj), where Obj is a subclass of PlotlyDict,
    will return information about key-value pairs for that object.

    """
    def __new__(mcs, name, bases, attrs):
        obj_key = NAME_TO_KEY[name]
        # remove min indentation...
        doc = attrs['__doc__']
        obj_info = INFO[obj_key]
        line_size = 76
        tab_size = 4
        min_indent = min([len(a) - len(b)
                          for a, b in zip(doc.splitlines(),
                                          [l.lstrip()
                                           for l in doc.splitlines()])])
        doc = "".join([line[min_indent:] + '\n' for line in doc.splitlines()])
        # Add section header for method list...
        doc += "Quick method reference:\n\n"
        doc += "\t{}.".format(name) + "\n\t{}.".format(name).join(
            ["update(changes)", "strip_style()", "get_data()",
             "to_graph_objs()", "validate()", "to_string()",
             "force_clean()"]) + "\n\n"
        # Add section header
        if len(obj_info):
            doc += "Valid keys:\n\n"
            # Add each key one-by-one and format
            width1 = line_size-tab_size
            width2 = line_size-2*tab_size
            width3 = line_size-3*tab_size
            undocumented = "Aw, snap! Undocumented!"
            for key in obj_info:
                # main portion of documentation
                try:
                    required = str(obj_info[key]['required'])
                except KeyError:
                    required = undocumented

                try:
                    typ = str(obj_info[key]['type'])
                except KeyError:
                    typ = undocumented

                try:
                    val_types = str(obj_info[key]['val_types'])
                    if typ == 'object':
                        val_types = "{} object | ".format(KEY_TO_NAME[key]) + \
                                    val_types
                except KeyError:
                    val_types = undocumented
                try:
                    descr = str(obj_info[key]['description'])
                except KeyError:
                    descr = undocumented
                str_1 = "{} [required={}] (value={}):\n".format(key, required,
                                                                val_types)
                str_1 = "\t" + "\n\t".join(textwrap.wrap(str_1,
                                                         width=width1)) + "\n"
                str_2 = "\t\t" + "\n\t\t".join(textwrap.wrap(descr,
                                               width=width2)) + "\n"
                doc += str_1 + str_2
                # if a user can run help on this value, tell them!
                if typ == "object":
                    doc += "\n\t\tFor more, run `help(plotly.graph_objs.{" \
                           "})`\n".format(KEY_TO_NAME[key])
                # if example usage exists, tell them!
                if 'examples' in obj_info[key]:
                    ex = "\n\t\tExamples:\n" + "\t\t\t"
                    ex += "\n\t\t\t".join(
                        textwrap.wrap(str(obj_info[key]['examples']),
                                      width=width3)) + "\n"
                    doc += ex
                if 'code' in obj_info[key]:
                    code = "\n\t\tCode snippet:"
                    code += "\n\t\t\t>>>".join(
                        str(obj_info[key]['code']).split('>>>')) + "\n"
                    doc += code
                doc += '\n'
        attrs['__doc__'] = doc.expandtabs(tab_size)
        return super(DictMeta, mcs).__new__(mcs, name, bases, attrs)


class PlotlyList(list):
    """A container for PlotlyDicts, inherits from standard list.

    Plotly uses lists and dicts as collections to hold information about a
    figure. This container is simply a list that understands some plotly
    language and apes the methods in a PlotlyDict, passing them on to its
    constituents.

    It can be initialized like any other list so long as the entries are all
    PlotlyDict objects or subclasses thereof.

    Any available methods that hold for a list object hold for a PlotlyList.

    Validation checking is preformed upon instantiation.

    Valid entry types: empty PlotlyDict or dict only.


    """
    __metaclass__ = ListMeta

    def __init__(self, *args):
        super(PlotlyList, self).__init__(*args)
        self.validate()
        if self.__class__.__name__ == 'PlotlyList':
            warnings.warn("\nThe PlotlyList class is a base class of "
                          "list-like graph_objs.\nIt is not meant to be a "
                          "user interface.")

    def to_graph_objs(self, caller=True):
        """Change any nested collections to subclasses of PlotlyDict/List.

        Procedure:
            1. Attempt to convert all entries to a subclass of PlotlyDict.
            2. Call `to_graph_objects` on each of these entries.

        """
        for index, entry in enumerate(self):
            if isinstance(entry, PlotlyDict):
                try:
                    entry.to_graph_objs(caller=False)
                except (exceptions.PlotlyGraphObjectError) as err:
                    err.add_to_error_path(index)
                    err.prepare()
                    raise  # re-raise current exception
            else:
                raise exceptions.PlotlyListEntryError(obj=self,
                                                      index=index,
                                                      entry=entry)


    def update(self, changes):
        """Update current list with changed_list, which must be iterable.
        The 'changes' should be a list of dictionaries, however,
        it is permitted to be a single dict object.

        """
        if isinstance(changes, dict):
            changes = [changes]
        self.to_graph_objs()
        for index in range(len(self)):
            try:
                self[index].update(changes[index % len(changes)])
            except ZeroDivisionError:
                pass

    def strip_style(self):
        """Strip style from the current representation.

        All PlotlyDicts and PlotlyLists are guaranteed to survive the
        stripping process, though they made be left empty. This is allowable.

        Keys that will be stripped in this process are tagged with
        `'type': 'style'` in the INFO dictionary listed in graph_objs_meta.py.

        This process first attempts to convert nested collections from dicts
        or lists to subclasses of PlotlyList/PlotlyDict. This process forces
        a validation, which may throw exceptions.

        Then, each of these objects call `strip_style` on themselves and so
        on, recursively until the entire structure has been validated and
        stripped.

        """
        self.to_graph_objs()
        for plotly_dict in self:
            plotly_dict.strip_style()

    def get_data(self):
        """Returns the JSON for the plot with non-data elements stripped."""
        self.to_graph_objs()
        l = list()
        for _plotlydict in self:
            l += [_plotlydict.get_data()]
        del_indicies = [index for index, item in enumerate(self)
                        if len(item) == 0]
        del_ct = 0
        for index in del_indicies:
            del self[index - del_ct]
            del_ct += 1
        return l

    def validate(self, caller=True):
        """Recursively check the validity of the entries in a PlotlyList.

        PlotlyList may only contain suclasses of PlotlyDict, or dictionary-like
        objects that can be re-instantiated as subclasses of PlotlyDict.

        The validation process first requires that all nested collections be
        converted to the appropriate subclass of PlotlyDict/PlotlyList. Then,
        each of these objects call `validate` and so on, recursively,
        until the entire list has been validated.

        """
        if caller:  # change everything to PlotlyList/Dict objects
            try:
                self.to_graph_objs()
            except exceptions.PlotlyGraphObjectError as err:
                err.prepare()
                raise
        for index, entry in enumerate(self):
            if isinstance(entry, PlotlyDict):
                try:
                    entry.validate(caller=False)
                except exceptions.PlotlyGraphObjectError as err:
                    err.add_to_error_path(index)
                    err.prepare()
                    raise
            else:
                raise exceptions.PlotlyGraphObjectError(  # TODO!!!
                    message="uh-oh, this error shouldn't have happenend.",
                    plain_message="uh-oh, this error shouldn't have happenend.",
                    path=[index],
                )

    def to_string(self, level=0, indent=4, eol='\n', pretty=True, max_chars=80):
        """Returns a formatted string showing graph_obj constructors.

        Example:

            print obj.to_string()

        Keyword arguments:
        level (default = 0) -- set number of indentations to start with
        indent (default = 4) -- set indentation amount
        eol (default = '\n') -- set end of line character(s)
        pretty (default = True) -- curtail long list output with a '...'
        max_chars (default = 80) -- set max characters per line

        """
        self.to_graph_objs()
        if not len(self):
            return "{name}()".format(name=self.__class__.__name__)
        string = "{name}([{eol}{indent}".format(
            name=self.__class__.__name__,
            eol=eol,
            indent=' ' * indent * (level + 1))
        for index, entry in enumerate(self):
            string += entry.to_string(level=level+1,
                                      indent=indent,
                                      eol=eol,
                                      pretty=pretty,
                                      max_chars=max_chars)
            if index < len(self) - 1:
                string += ",{eol}{indent}".format(
                    eol=eol,
                    indent=' ' * indent * (level + 1))
        string += "{eol}{indent}])".format(eol=eol, indent=' ' * indent * level)
        return string

    def force_clean(self, caller=True):
        """Attempts to convert to graph_objs and calls force_clean() on entries.

        Calling force_clean() on a PlotlyList will ensure that the object is
        valid and may be sent to plotly. This process will remove any entries
        that end up with a length == 0. It will also remove itself from
        enclosing trivial structures if it is enclosed by a collection with
        length 1, meaning the data is the ONLY object in the collection.

        Careful! This will delete any invalid entries *silently*.

        """
        if caller:
            self.to_graph_objs()  # TODO add error handling here!
        for entry in self:
            entry.force_clean(caller=False)
        del_indicies = [index for index, item in enumerate(self)
                        if len(item) == 0]
        del_ct = 0
        for index in del_indicies:
            del self[index - del_ct]
            del_ct += 1


class PlotlyDict(dict):
    """A base dict class for all objects that style a figure in plotly.

    A PlotlyDict can be instantiated like any dict object. This class
    offers some useful recursive methods that can be used by higher-level
    subclasses and containers so long as all plot objects are instantiated
    as a subclass of PlotlyDict. Each PlotlyDict should be instantiated
    with a `kind` keyword argument. This defines the special _info
    dictionary for the object.

    Any available methods that hold for a dict hold for a PlotlyDict.

    """
    __metaclass__ = DictMeta

    def __init__(self, *args, **kwargs):
        class_name = self.__class__.__name__
        super(PlotlyDict, self).__init__(*args, **kwargs)
        if issubclass(NAME_TO_CLASS[class_name], PlotlyTrace):
            if (class_name != 'PlotlyTrace') and (class_name != 'Trace'):
                self['type'] = NAME_TO_KEY[class_name]
        self.validate()
        if self.__class__.__name__ == 'PlotlyDict':
            warnings.warn("\nThe PlotlyDict class is a base class of "
                          "dictionary-like graph_objs.\nIt is not meant to be "
                          "a user interface.")

    def update(self, dict1=None, **dict2):
        """Update current dict with dict1 and then dict2.

        This recursively updates the structure of the original dictionary-like
        object with the new entries in the second and third objects. This
        allows users to update with large, nested structures.

        Note, because the dict2 packs up all the keyword arguments, you can
        specify the changes as a list of keyword agruments.

        Examples:
        # update with dict
        obj = Layout(title='my title', xaxis=XAxis(range=[0,1], domain=[0,1]))
        update_dict = dict(title='new title', xaxis=dict(domain=[0,.8]))
        obj.update(update_dict)
        obj
        {'title': 'new title', 'xaxis': {'range': [0,1], 'domain': [0,.8]}}

        # update with list of keyword arguments
        obj = Layout(title='my title', xaxis=XAxis(range=[0,1], domain=[0,1]))
        obj.update(title='new title', xaxis=dict(domain=[0,.8]))
        obj
        {'title': 'new title', 'xaxis': {'range': [0,1], 'domain': [0,.8]}}

        This 'fully' supports duck-typing in that the call signature is
        identical, however this differs slightly from the normal update
        method provided by Python's dictionaries.

        """
        self.to_graph_objs()

        if dict1 is not None:
            for key, val in dict1.items():
                if key in self:
                    if isinstance(self[key], (PlotlyDict, PlotlyList)):
                        self[key].update(val)
                    else:
                        self[key] = val
                else:
                    self[key] = val

        if len(dict2):
            for key, val in dict2.items():
                if key in self:
                    if isinstance(self[key], (PlotlyDict, PlotlyList)):
                        self[key].update(val)
                    else:
                        self[key] = val
                else:
                    self[key] = val
        self.to_graph_objs()

    def strip_style(self):
        """Strip style from the current representation.

        All PlotlyDicts and PlotlyLists are guaranteed to survive the
        stripping process, though they made be left empty. This is allowable.

        Keys that will be stripped in this process are tagged with
        `'type': 'style'` in the INFO dictionary listed in graph_objs_meta.py.

        This process first attempts to convert nested collections from dicts
        or lists to subclasses of PlotlyList/PlotlyDict. This process forces
        a validation, which may throw exceptions.

        Then, each of these objects call `strip_style` on themselves and so
        on, recursively until the entire structure has been validated and
        stripped.

        """
        self.to_graph_objs()
        obj_key = NAME_TO_KEY[self.__class__.__name__]
        keys = self.keys()
        for key in keys:
            if isinstance(self[key], (PlotlyDict, PlotlyList)):
                self[key].strip_style()
            else:
                try:
                    if INFO[obj_key][key]['type'] == 'style':
                        del self[key]
                except KeyError:  # TODO: Update the JSON
                    # print "'type' not in {} for {}".format(obj_key, key)
                    pass

    def get_data(self):
        """Returns the JSON for the plot with non-data elements stripped."""
        self.to_graph_objs()
        class_name = self.__class__.__name__
        obj_key = NAME_TO_KEY[class_name]
        d = dict()
        for key, val in self.items():
            if isinstance(val, (PlotlyDict, PlotlyList)):
                d[key] = val.get_data()
            else:
                try:
                    if INFO[obj_key][key]['type'] == 'data':  # TODO: Update the JSON
                        d[key] = val
                except KeyError:
                    pass
        keys = d.keys()
        for key in keys:
            if isinstance(d[key], (dict, list)):
                if len(d[key]) == 0:
                    del d[key]
        if len(d) == 1:
            d = d.values()[0]
        return d

    def to_graph_objs(self, caller=True):
        """Walk obj, convert dicts and lists to plotly graph objs.

        For each key in the object, if it corresponds to a special key that
        should be associated with a graph object, the ordinary dict or list
        will be reinitialized as a special PlotlyDict or PlotlyList of the
        appropriate `kind`.

        """
        info_key = NAME_TO_KEY[self.__class__.__name__]
        keys = self.keys()
        for key in keys:
            if isinstance(self[key], (PlotlyDict, PlotlyList)):
                try:
                    self[key].to_graph_objs(caller=False)
                except exceptions.PlotlyGraphObjectError as err:
                    err.add_to_error_path(key)
                    err.prepare()
                    raise
            elif key in INFO[info_key] and 'type' in INFO[info_key][key]:
                if INFO[info_key][key]['type'] == 'object':
                    class_name = KEY_TO_NAME[key]
                    obj = NAME_TO_CLASS[class_name]()  # gets constructor
                    if isinstance(obj, PlotlyDict):
                        if not isinstance(self[key], dict):
                            info_key = NAME_TO_KEY[self.__class__.__name__]
                            raise exceptions.PlotlyDictValueError(
                                obj=self,
                                key=key,
                                value=self[key],
                                val_types=INFO[info_key][key]['val_types'],
                                notes="value needs to be dictionary-like"
                            )
                        for k, v in self.pop(key).items():
                            obj[k] = v  # finish up momentarily...
                    else:  # if not PlotlyDict, it MUST be a PlotlyList
                        if not isinstance(self[key], list):
                            info_key = NAME_TO_KEY[self.__class__.__name__]
                            raise exceptions.PlotlyDictValueError(  # TODO!!!
                                obj=self,
                                key=key,
                                value=self[key],
                                val_types=INFO[info_key][key]['val_types'],
                                notes="value needs to be list-like"
                            )
                        obj += self.pop(key)
                    try:
                        obj.to_graph_objs(caller=False)
                    except exceptions.PlotlyGraphObjectError as err:
                        err.add_to_error_path(key)
                        err.prepare()
                        raise
                    self[key] = obj  # whew! made it!

    def validate(self, caller=True):  # TODO: validate values too?
        """Recursively check the validity of the keys in a PlotlyDict.

        The valid keys constitute the entries in each object
        dictionary in INFO stored in graph_objs_meta.py.

        The validation process first requires that all nested collections be
        converted to the appropriate subclass of PlotlyDict/PlotlyList. Then,
        each of these objects call `validate` and so on, recursively,
        until the entire object has been validated.

        """
        if caller:  # change everything to 'checkable' objs
            try:
                self.to_graph_objs(caller=False)
            except exceptions.PlotlyGraphObjectError as err:
                err.prepare()
                raise
        obj_key = NAME_TO_KEY[self.__class__.__name__]
        for key, val in self.items():
            if isinstance(val, (PlotlyDict, PlotlyList)):
                try:
                    val.validate(caller=False)
                except exceptions.PlotlyGraphObjectError as err:
                    err.add_to_error_path(key)
                    err.prepare()
                    raise
            else:
                if key in INFO[obj_key]:
                    if 'type' not in INFO[obj_key][key]:
                        continue  # TODO: 'type' may not be documented yet!
                    if INFO[obj_key][key]['type'] == 'object':
                        raise exceptions.PlotlyDictValueError(
                            obj=self,
                            key=key,
                            value=val,
                            val_types=INFO[obj_key][key]['val_types']
                        )
                else:
                    matching_objects = [obj for obj in INFO if key in INFO[obj]]
                    notes = ''
                    if len(matching_objects):
                        notes += "That key is valid only in these objects:\n\n"
                        for obj in matching_objects:
                            notes += "\t{}".format(KEY_TO_NAME[obj])
                            try:
                                notes += '({}="{}")\n'.format(
                                    repr(key), INFO[obj][key]['val_types'])
                            except KeyError:
                                notes += '({}="..")\n'.format(repr(key))
                        notes.expandtabs()
                    else:
                        notes += ("Couldn't find uses for key: {}\n\n"
                                  "".format(repr(key)))
                    raise exceptions.PlotlyDictKeyError(obj=self,
                                                        key=key,
                                                        notes=notes)

    def to_string(self, level=0, indent=4, eol='\n', pretty=True, max_chars=80):
        """Returns a formatted string showing graph_obj constructors.

        Example:

            print obj.to_string()

        Keyword arguments:
        level (default = 0) -- set number of indentations to start with
        indent (default = 4) -- set indentation amount
        eol (default = '\n') -- set end of line character(s)
        pretty (default = True) -- curtail long list output with a '...'
        max_chars (default = 80) -- set max characters per line

        """
        self.to_graph_objs()  # todo, consider catching and re-raising?
        if not len(self):
            return "{name}()".format(name=self.__class__.__name__)
        string = "{name}(".format(name=self.__class__.__name__)
        index = 0
        obj_key = NAME_TO_KEY[self.__class__.__name__]
        for key in INFO[obj_key]:  # this sets the order of the keys! nice.
            if key in self:
                string += "{eol}{indent}{key}=".format(
                    eol=eol,
                    indent=' ' * indent * (level+1),
                    key=key)
                try:
                    string += self[key].to_string(level=level+1,
                                                  indent=indent,
                                                  eol=eol,
                                                  pretty=pretty,
                                                  max_chars=max_chars)
                except AttributeError:
                    val = repr(self[key])
                    val_chars = max_chars - (indent*(level+1)) - (len(key)+1)
                    if pretty and (len(val) > val_chars):
                        string += val[:val_chars - 5] + '...' + val[-1]
                    else:
                        string += val
                if index < len(self) - 1:
                    string += ","
                index += 1
                if index == len(self):
                    break
        string += "{eol}{indent})".format(eol=eol, indent=' ' * indent * level)
        return string

    def force_clean(self, caller=True):
        """Attempts to convert to graph_objs and call force_clean() on values.

        Calling force_clean() on a PlotlyDict will ensure that the object is
        valid and may be sent to plotly. This process will also remove any
        entries that end up with a length == 0.

        Careful! This will delete any invalid entries *silently*.

        """
        obj_key = NAME_TO_KEY[self.__class__.__name__]
        if caller:
            self.to_graph_objs(caller=False)
        del_keys = [key for key in self if str(key) not in INFO[obj_key]]
        for key in del_keys:
            del self[key]
        keys = self.keys()
        for key in keys:
            try:
                self[key].force_clean(caller=False)  # TODO: add error handling
            except AttributeError:
                pass
            if isinstance(self[key], (dict, list)):
                if len(self[key]) == 0:
                    del self[key]  # clears empty collections!
            elif self[key] is None:
                del self[key]


class Data(PlotlyList):
    """A list of traces to be shown on a plot/graph.

    Any operation that can be done with a standard list may be used with Data.
    Instantiation requires an iterable (just like list does), for example:

    Data([Scatter(), Heatmap(), Box()])

    Valid entry types: (dict or any subclass of Trace, i.e., Scatter, Box, etc.)

    """
    def to_graph_objs(self, caller=True):  # TODO TODO TODO! check logic!
        """Change any nested collections to subclasses of PlotlyDict/List.

        Procedure:
            1. Attempt to convert all entries to a subclass of PlotlyTrace.
            2. Call `to_graph_objects` on each of these entries.

        """
        for index, entry in enumerate(self):
            if isinstance(entry, PlotlyDict):
                self[index] = NAME_TO_CLASS[entry.__class__.__name__](entry)
            elif isinstance(entry, dict):
                if 'type' not in entry:  # assume 'scatter' if not given
                    entry['type'] = 'scatter'
                try:
                    obj_name = KEY_TO_NAME[entry['type']]
                except KeyError:
                    raise exceptions.PlotlyDataTypeError(
                        obj=self,
                        index=index
                    )
                obj = NAME_TO_CLASS[obj_name]()  # don't hide if KeyError!
                for k, v in entry.items():
                    obj[k] = v
                self[index] = obj
            if not isinstance(self[index], PlotlyTrace):  # Trace ONLY!!!
                raise exceptions.PlotlyListEntryError(
                    obj=self,
                    index=index,
                    notes="The entry could not be converted into a PlotlyTrace "
                          "object (e.g., Scatter, Heatmap, Bar, etc).",
                )
        super(Data, self).to_graph_objs(caller=caller)


class Annotations(PlotlyList):
    """A list-like object to contain all figure notes.

    Any operation that can be done with a standard list may be used with
    Annotations. Instantiation requires an iterable (just like list does),
    for example:

    Annotations([Annotation(), Annotation(), Annotation()])

    This Annotations list is validated upon instantiation, meaning exceptions
    will be thrown if any invalid entries are found.

    Valid entry types: (dict or Annotation)

    For help on Annotation, run `help(plotly.graph_objs.Annotation)`

    """
    def to_graph_objs(self, caller=True):
        """Change any nested collections to subclasses of PlotlyDict/List.

        Procedure:
            1. Attempt to convert all entries to a subclass of PlotlyDict.
            2. Call `to_graph_objects` on each of these entries.

        """
        for index, entry in enumerate(self):
            if isinstance(entry, (PlotlyDict, PlotlyList)):
                if not isinstance(entry, Annotation):
                    raise exceptions.PlotlyListEntryError(
                        obj=self,
                        index=index,
                        notes="The entry could not be converted into an "
                              "Annotation object because it was already a "
                              "different kind of graph object.",
                    )
            elif isinstance(entry, dict):
                obj = Annotation()
                for k, v in entry.items():
                    obj[k] = v
                self[index] = obj
            else:
                raise exceptions.PlotlyListEntryError(
                    obj=self,
                    index=index,
                    notes="The entry could not be converted into an Annotation "
                          "object because it was not a dictionary.",
                )
        super(Annotations, self).to_graph_objs(caller=caller)


class PlotlyTrace(PlotlyDict):
    """A general data class for plotly.

    The PlotlyTrace object is not meant for user interaction. It's sole
    purpose is to improve the structure of the object hierarchy established
    in this module.

    Users should work with the subclasses of PlotlyTrace: Scatter, Box, Bar,
    Heatmap, etc.

    For help with these subclasses, run:
    `help(plotly.graph_objs.Obj)` where Obj == Scatter, Box, Bar, Heatmap, etc.

    """
    def __init__(self, *args, **kwargs):
        super(PlotlyTrace, self).__init__(*args, **kwargs)
        if self.__class__.__name__ == 'PlotlyTrace':
            warnings.warn("\nThe PlotlyTrace class is a base class of "
                          "dictionary-like plot types.\nIt is not meant to be "
                          "a user interface.")

    def to_string(self, level=0, indent=4, eol='\n', pretty=True, max_chars=80):
        """Returns a formatted string showing graph_obj constructors.

        Example:

            print obj.to_string()

        Keyword arguments:
        level (default = 0) -- set number of indentations to start with
        indent (default = 4) -- set indentation amount
        eol (default = '\n') -- set end of line character(s)
        pretty (default = True) -- curtail long list output with a '...'
        max_chars (default = 80) -- set max characters per line

        """
        self.to_graph_objs()
        if self.__class__.__name__ != "Trace":
            trace_type = self.pop('type')
            string = super(PlotlyTrace, self).to_string(level=level,
                                                        indent=indent,
                                                        eol=eol,
                                                        pretty=pretty,
                                                        max_chars=max_chars)
            self['type'] = trace_type
        else:
            string = super(PlotlyTrace, self).to_string(level=level,
                                                        indent=indent,
                                                        eol=eol,
                                                        pretty=pretty,
                                                        max_chars=max_chars)
        return string


class Trace(PlotlyTrace):
    """A general data class for plotly. Never validated...

    This class should be used only for the right reason. This class does not
    do much validation because plotly usually accepts more trace specifiers
    and more value type varieties, e.g., 'x', 'y', 'r', 't', marker = [
    array], etc.

    If you are getting errors locally, you might try using this case if
    you're sure that what you're attempting to plot is valid.

    Also, when getting figures from plotly, you may get back `Trace` types if
    the figure was constructed with data objects that don't fall into any of
    the class categorizations that are defined in this api.

    """
    pass


class Area(PlotlyTrace):
    """A dictionary-like object for representing an area chart in plotly.

    """
    pass


class Bar(PlotlyTrace):
    """A dictionary-like object for representing a bar chart in plotly.

    Example:

    py.plot([Bar(x=['yesterday', 'today', 'tomorrow'], y=[5, 4, 10])])

    """
    pass


class Box(PlotlyTrace):
    """A dictionary-like object for representing a box plot in plotly.

    Example:

        py.plot([Box(name='boxy', y=[1,3,9,2,4,2,3,5,2])])

    """
    pass


class Contour(PlotlyTrace):
    """A dictionary-like object for representing a contour plot in plotly.

    Example:

        z = [[0, 1, 0, 1, 0],
             [1, 0, 1, 0, 1],
             [0, 1, 0, 1, 0],]
        y = ['a', 'b', 'c']
        x = [1, 2, 3, 4, 5]
        py.plot([Contour(z=z, x=x, y=y)])

    """
    pass


class Heatmap(PlotlyTrace):
    """A dictionary-like object for representing a heatmap in plotly.

    Example:

        z = [[0, 1, 0, 1, 0],
             [1, 0, 1, 0, 1],
             [0, 1, 0, 1, 0],]
        y = ['a', 'b', 'c']
        x = [1, 2, 3, 4, 5]
        py.plot([Heatmap(z=z, x=x, y=y)])

    """
    pass


class Histogram(PlotlyTrace):
    """A dictionary-like object for representing a histogram plot in plotly.

    Example:
        # make a histogram along xaxis...
        py.plot([Histogram(x=[1,1,2,3,2,3,3])])

        # make a histogram along yaxis...
        py.plot([Histogram(y=[1,1,2,3,2,3,3], orientation='h')])

    """


class Histogram2d(PlotlyTrace):
    """A dictionary-like object for representing a histogram2d plot in plotly.

    Example:

        import numpy as np
        x = np.random.randn(500)
        y = np.random.randn(500)+1
        py.iplot([Histogram2d(x=x, y=y)])

    """
    pass


class Histogram2dContour(PlotlyTrace):
    """A dict-like object for representing a histogram2d-contour plot in plotly.

    Example:

        import numpy as np
        x = np.random.randn(500)
        y = np.random.randn(500)+1
        py.iplot([Histogram2dcountour(x=x, y=y)])

    """
    pass


class Scatter(PlotlyTrace):
    """A dictionary-like object for representing a scatter plot in plotly.

    Example:

        py.plot([Scatter(name='tacters', x=[1,4,2,3], y=[1,6,2,1])])

    """
    pass


class AngularAxis(PlotlyDict):
    """A  dictionary-like object for representing an angular axis in plotly.

    """
    pass


class RadialAxis(PlotlyDict):
    """A  dictionary-like object for representing an angular axis in plotly.

    """
    pass


class Annotation(PlotlyDict):
    """A dictionary-like object for representing an annotation in plotly.

    Annotations appear as notes on the final figure. You can set all the
    features of the annotation text, background color, and location.
    Additionally, these notes can be anchored to actual data or the page for
    help with location after pan-and-zoom actions.

    This object is validated upon instantiation, therefore, you may see
    exceptions getting thrown. These are intended to help users find the
    origin of errors faster. The errors will usually contain information that
    can be used to remedy the problem.

    Example:

        note = Annotation(text='what i want this to say is:<br>THIS!',
                          x=0,
                          y=0,
                          xref='paper',
                          yref='paper,
                          yanchor='bottom',
                          xanchor='left')

    """
    pass


class ColorBar(PlotlyDict):  # TODO: ?
    """A dictionary-like object for representing a color bar in plotly.

    """
    pass


class Contours(PlotlyDict):  # TODO: ?
    """A dictionary-like object for representing a contours object in plotly.

    This object exists inside definitions for a contour plot.

    """

class ErrorX(PlotlyDict):
    """A dictionary-like object for representing a set of errorx bars in plotly.

    """
    pass


class ErrorY(PlotlyDict):
    """A dictionary-like object for representing a set of errory bars in plotly.

    """
    pass


class Figure(PlotlyDict):
    """A dictionary-like object representing a figure to be rendered in plotly.

    This is the container for all things to be rendered in a figure.

    For help with setting up subplots, run:
    `help(plotly.tools.get_subplots)`

    """
    def __init__(self, *args, **kwargs):
        if len(args):
            if ('data' not in kwargs) and ('data' not in args[0]):
                kwargs['data'] = Data()
            if ('layout' not in kwargs) and ('layout' not in args[0]):
                kwargs['layout'] = Layout()
        else:
            if 'data' not in kwargs:
                kwargs['data'] = Data()
            if 'layout' not in kwargs:
                kwargs['layout'] = Layout()
        super(Figure, self).__init__(*args, **kwargs)


class Font(PlotlyDict):
    """A dictionary-like object representing details about font style.

    """
    pass


class Layout(PlotlyDict):
    """A dictionary-like object holding plot settings for plotly figures.

    """
    def __init__(self, *args, **kwargs):
        super(Layout, self).__init__(*args, **kwargs)

    def to_graph_objs(self, caller=True):
        """Walk obj, convert dicts and lists to plotly graph objs.

        For each key in the object, if it corresponds to a special key that
        should be associated with a graph object, the ordinary dict or list
        will be reinitialized as a special PlotlyDict or PlotlyList of the
        appropriate `kind`.

        """
        keys = self.keys()
        for key in keys:
            if key[:5] in ['xaxis', 'yaxis']:  # allows appended integers!
                try:
                    axis_int = int(key[5:])  # may raise ValueError
                    if axis_int == 0:
                        continue  # xaxis0 and yaxis0 are not valid keys...
                except ValueError:
                    continue  # not an XAxis or YAxis object after all
                if isinstance(self[key], dict):
                    if key[:5] == 'xaxis':
                        obj = XAxis()
                    else:
                        obj = YAxis()
                    for k, v in self.pop(key).items():
                        obj[k] = v
                    self[key] = obj  # call to super will call 'to_graph_objs'
        super(Layout, self).to_graph_objs(caller=caller)

    def to_string(self, level=0, indent=4, eol='\n', pretty=True, max_chars=80):
        """Returns a formatted string showing graph_obj constructors.

        Example:

            print obj.to_string()

        Keyword arguments:
        level (default = 0) -- set number of indentations to start with
        indent (default = 4) -- set indentation amount
        eol (default = '\n') -- set end of line character(s)
        pretty (default = True) -- curtail long list output with a '...'
        max_chars (default = 80) -- set max characters per line

        """
        # TODO: can't call super
        self.to_graph_objs()
        if not len(self):
            return "{name}()".format(name=self.__class__.__name__)
        string = "{name}(".format(name=self.__class__.__name__)
        index = 0
        obj_key = NAME_TO_KEY[self.__class__.__name__]
        for key in INFO[obj_key]:
            if key in self:
                string += "{eol}{indent}{key}=".format(
                    eol=eol,
                    indent=' ' * indent * (level+1),
                    key=key)
                try:
                    string += self[key].to_string(level=level+1,
                                                  indent=indent,
                                                  eol=eol,
                                                  pretty=pretty,
                                                  max_chars=max_chars)
                except AttributeError:
                    val = repr(self[key])
                    val_chars = max_chars - (indent*(level+1)) - (len(key)+1)
                    if pretty and (len(val) > val_chars):
                        string += val[:val_chars - 5] + '...' + val[-1]
                    else:
                        string += val
                if index < len(self) - 1:
                    string += ","
                index += 1
                if index == len(self):
                    break
        left_over_keys = [key for key in self if key not in INFO[obj_key]]
        left_over_keys.sort()
        for key in left_over_keys:
            string += "{eol}{indent}{key}=".format(
                eol=eol,
                indent=' ' * indent * (level+1),
                key=key)
            try:
                string += self[key].to_string(level=level + 1,
                                              indent=indent,
                                              eol=eol,
                                              pretty=pretty,
                                              max_chars=max_chars)
            except AttributeError:
                string += str(repr(self[key]))
            if index < len(self) - 1:
                string += ","
            index += 1
        string += "{eol}{indent})".format(eol=eol, indent=' ' * indent * level)
        return string

    def force_clean(self, caller=True):  # TODO: can't make call to super...
        """Attempts to convert to graph_objs and call force_clean() on values.

        Calling force_clean() on a Layout will ensure that the object is
        valid and may be sent to plotly. This process will also remove any
        entries that end up with a length == 0.

        Careful! This will delete any invalid entries *silently*.

        This method differs from the parent (PlotlyDict) method in that it
        must check for an infinite number of possible axis keys, i.e. 'xaxis',
        'xaxis1', 'xaxis2', 'xaxis3', etc. Therefore, it cannot make a call
        to super...

        """
        obj_key = NAME_TO_KEY[self.__class__.__name__]
        if caller:
            self.to_graph_objs(caller=False)
        del_keys = [key for key in self if str(key) not in INFO[obj_key]]
        for key in del_keys:
            if (key[:5] == 'xaxis') or (key[:5] == 'yaxis'):
                try:
                    test_if_int = int(key[5:])
                except ValueError:
                    del self[key]
            else:
                del self[key]
        keys = self.keys()
        for key in keys:
            try:
                self[key].force_clean(caller=False)  # TODO error handling??
            except AttributeError:
                pass
            if isinstance(self[key], (dict, list)):
                if len(self[key]) == 0:
                    del self[key]  # clears empty collections!
            elif self[key] is None:
                del self[key]


class Legend(PlotlyDict):
    """A dictionary-like object representing the legend options for a figure.

    """
    pass


class Line(PlotlyDict):
    """A dictionary-like object representing the style of a line in plotly.

    """
    pass


class Marker(PlotlyDict):
    """A dictionary-like object representing marker(s) style in plotly.

    """
    pass


class Margin(PlotlyDict):
    """A dictionary-like object holding plot margin information.

    """
    pass


class Stream(PlotlyDict):
    """A dictionary-like object representing a data stream.

    """
    pass


class XAxis(PlotlyDict):
    """A dictionary-like object representing an xaxis in plotly.

    """
    pass


class XBins(PlotlyDict):
    """A dictionary-like object representing bin information for a histogram.

    """
    pass


class YAxis(PlotlyDict):
    """A dictionary-like object representing a yaxis in plotly.

    """
    pass


class YBins(PlotlyDict):
    """A dictionary-like object representing bin information for a histogram.

    """
    pass

# finally... define how to map from a class name to an actual class
# mapping: (n->n)
NAME_TO_CLASS = dict(
    PlotlyList=PlotlyList,
    Data=Data,
    Annotations=Annotations,
    PlotlyDict=PlotlyDict,
    PlotlyTrace=PlotlyTrace,
    Area=Area,
    Bar=Bar,
    Box=Box,
    Contour=Contour,
    Heatmap=Heatmap,
    Histogram=Histogram,
    Histogram2d=Histogram2d,
    Histogram2dContour=Histogram2dContour,
    Scatter=Scatter,
    AngularAxis=AngularAxis,
    Annotation=Annotation,
    ColorBar=ColorBar,
    Contours=Contours,
    ErrorX=ErrorX,
    ErrorY=ErrorY,
    Figure=Figure,
    Font=Font,
    Layout=Layout,
    Legend=Legend,
    Line=Line,
    Margin=Margin,
    Marker=Marker,
    RadialAxis=RadialAxis,
    Stream=Stream,
    Trace=Trace,
    XAxis=XAxis,
    XBins=XBins,
    YAxis=YAxis,
    YBins=YBins
)
########NEW FILE########
__FILENAME__ = exporter
"""
Matplotlib Exporter
===================
This submodule contains tools for crawling a matplotlib figure and exporting
relevant pieces to a renderer.
"""
import warnings
import io
from . import utils

import matplotlib
from matplotlib import transforms, collections


class Exporter(object):
    """Matplotlib Exporter

    Parameters
    ----------
    renderer : Renderer object
        The renderer object called by the exporter to create a figure
        visualization.  See mplexporter.Renderer for information on the
        methods which should be defined within the renderer.
    close_mpl : bool
        If True (default), close the matplotlib figure as it is rendered. This
        is useful for when the exporter is used within the notebook, or with
        an interactive matplotlib backend.
    """

    def __init__(self, renderer, close_mpl=True):
        self.close_mpl = close_mpl
        self.renderer = renderer

    def run(self, fig):
        """
        Run the exporter on the given figure

        Parmeters
        ---------
        fig : matplotlib.Figure instance
            The figure to export
        """
        # Calling savefig executes the draw() command, putting elements
        # in the correct place.
        fig.savefig(io.BytesIO(), format='png', dpi=fig.dpi)
        if self.close_mpl:
            import matplotlib.pyplot as plt
            plt.close(fig)
        self.crawl_fig(fig)

    @staticmethod
    def process_transform(transform, ax=None, data=None, return_trans=False,
                          force_trans=None):
        """Process the transform and convert data to figure or data coordinates

        Parameters
        ----------
        transform : matplotlib Transform object
            The transform applied to the data
        ax : matplotlib Axes object (optional)
            The axes the data is associated with
        data : ndarray (optional)
            The array of data to be transformed.
        return_trans : bool (optional)
            If true, return the final transform of the data
        force_trans : matplotlib.transform instance (optional)
            If supplied, first force the data to this transform

        Returns
        -------
        code : string
            Code is either "data", "axes", "figure", or "display", indicating
            the type of coordinates output.
        transform : matplotlib transform
            the transform used to map input data to output data.
            Returned only if return_trans is True
        new_data : ndarray
            Data transformed to match the given coordinate code.
            Returned only if data is specified
        """
        if isinstance(transform, transforms.BlendedGenericTransform):
            warnings.warn("Blended transforms not yet supported. "
                          "Zoom behavior may not work as expected.")

        if force_trans is not None:
            if data is not None:
                data = (transform - force_trans).transform(data)
            transform = force_trans

        code = "display"
        if ax is not None:
            for (c, trans) in [("data", ax.transData),
                               ("axes", ax.transAxes),
                               ("figure", ax.figure.transFigure),
                               ("display", transforms.IdentityTransform())]:
                if transform.contains_branch(trans):
                    code, transform = (c, transform - trans)
                    break

        if data is not None:
            if return_trans:
                return code, transform.transform(data), transform
            else:
                return code, transform.transform(data)
        else:
            if return_trans:
                return code, transform
            else:
                return code

    def crawl_fig(self, fig):
        """Crawl the figure and process all axes"""
        with self.renderer.draw_figure(fig=fig,
                                       props=utils.get_figure_properties(fig)):
            for ax in fig.axes:
                self.crawl_ax(ax)

    def crawl_ax(self, ax):
        """Crawl the axes and process all elements within"""
        with self.renderer.draw_axes(ax=ax,
                                     props=utils.get_axes_properties(ax)):
            for line in ax.lines:
                self.draw_line(ax, line)
            for text in ax.texts:
                self.draw_text(ax, text)
            for (text, ttp) in zip([ax.xaxis.label, ax.yaxis.label, ax.title],
                                   ["xlabel", "ylabel", "title"]):
                if(hasattr(text, 'get_text') and text.get_text()):
                    self.draw_text(ax, text, force_trans=ax.transAxes,
                                   text_type=ttp)
            for artist in ax.artists:
                # TODO: process other artists
                if isinstance(artist, matplotlib.text.Text):
                    self.draw_text(ax, artist)
            for patch in ax.patches:
                self.draw_patch(ax, patch)
            for collection in ax.collections:
                self.draw_collection(ax, collection)
            for image in ax.images:
                self.draw_image(ax, image)

            legend = ax.get_legend()
            if legend is not None:
                props = utils.get_legend_properties(ax, legend)
                with self.renderer.draw_legend(legend=legend, props=props):
                    if props['visible']:
                        self.crawl_legend(ax, legend)

    def crawl_legend(self, ax, legend):
        """
        Recursively look through objects in legend children
        """
        legendElements = list(utils.iter_all_children(legend._legend_box,
                                                      skipContainers=True))
        legendElements.append(legend.legendPatch)
        for child in legendElements:
            # force a large zorder so it appears on top
            child.set_zorder(1E6 + child.get_zorder())

            try:
                # What kind of object...
                if isinstance(child, matplotlib.patches.Patch):
                    self.draw_patch(ax, child, force_trans=ax.transAxes)
                elif isinstance(child, matplotlib.text.Text):
                    if not (child is legend.get_children()[-1]
                            and child.get_text() == 'None'):
                        self.draw_text(ax, child, force_trans=ax.transAxes)
                elif isinstance(child, matplotlib.lines.Line2D):
                    self.draw_line(ax, child, force_trans=ax.transAxes)
                elif isinstance(child, matplotlib.collections.Collection):
                    self.draw_collection(ax, child,
                                         force_pathtrans=ax.transAxes)
                else:
                    warnings.warn("Legend element %s not impemented" % child)
            except NotImplementedError:
                warnings.warn("Legend element %s not impemented" % child)

    def draw_line(self, ax, line, force_trans=None):
        """Process a matplotlib line and call renderer.draw_line"""
        coordinates, data = self.process_transform(line.get_transform(),
                                                   ax, line.get_xydata(),
                                                   force_trans=force_trans)
        linestyle = utils.get_line_style(line)
        if linestyle['dasharray'] in ['None', 'none', None]:
            linestyle = None
        markerstyle = utils.get_marker_style(line)
        if (markerstyle['marker'] in ['None', 'none', None]
                or markerstyle['markerpath'][0].size == 0):
            markerstyle = None
        label = line.get_label()
        if markerstyle or linestyle:
            self.renderer.draw_marked_line(data=data, coordinates=coordinates,
                                           linestyle=linestyle,
                                           markerstyle=markerstyle,
                                           label=label,
                                           mplobj=line)

    def draw_text(self, ax, text, force_trans=None, text_type=None):
        """Process a matplotlib text object and call renderer.draw_text"""
        content = text.get_text()
        if content:
            transform = text.get_transform()
            position = text.get_position()
            coords, position = self.process_transform(transform, ax,
                                                      position,
                                                      force_trans=force_trans)
            style = utils.get_text_style(text)
            self.renderer.draw_text(text=content, position=position,
                                    coordinates=coords,
                                    text_type=text_type,
                                    style=style, mplobj=text)

    def draw_patch(self, ax, patch, force_trans=None):
        """Process a matplotlib patch object and call renderer.draw_path"""
        vertices, pathcodes = utils.SVG_path(patch.get_path())
        transform = patch.get_transform()
        coordinates, vertices = self.process_transform(transform,
                                                       ax, vertices,
                                                       force_trans=force_trans)
        linestyle = utils.get_path_style(patch, fill=patch.get_fill())
        self.renderer.draw_path(data=vertices,
                                coordinates=coordinates,
                                pathcodes=pathcodes,
                                style=linestyle,
                                mplobj=patch)

    def draw_collection(self, ax, collection,
                        force_pathtrans=None,
                        force_offsettrans=None):
        """Process a matplotlib collection and call renderer.draw_collection"""
        (transform, transOffset,
         offsets, paths) = collection._prepare_points()

        offset_coords, offsets = self.process_transform(
            transOffset, ax, offsets, force_trans=force_offsettrans)
        path_coords = self.process_transform(
            transform, ax, force_trans=force_pathtrans)

        processed_paths = [utils.SVG_path(path) for path in paths]
        processed_paths = [(self.process_transform(
            transform, ax, path[0], force_trans=force_pathtrans)[1], path[1])
                           for path in processed_paths]

        path_transforms = collection.get_transforms()
        try:
            # matplotlib 1.3: path_transforms are transform objects.
            # Convert them to numpy arrays.
            path_transforms = [t.get_matrix() for t in path_transforms]
        except AttributeError:
            # matplotlib 1.4: path transforms are already numpy arrays.
            pass

        styles = {'linewidth': collection.get_linewidths(),
                  'facecolor': collection.get_facecolors(),
                  'edgecolor': collection.get_edgecolors(),
                  'alpha': collection._alpha,
                  'zorder': collection.get_zorder()}

        offset_dict = {"data": "before",
                       "screen": "after"}
        offset_order = offset_dict[collection.get_offset_position()]

        self.renderer.draw_path_collection(paths=processed_paths,
                                           path_coordinates=path_coords,
                                           path_transforms=path_transforms,
                                           offsets=offsets,
                                           offset_coordinates=offset_coords,
                                           offset_order=offset_order,
                                           styles=styles,
                                           mplobj=collection)

    def draw_image(self, ax, image):
        """Process a matplotlib image object and call renderer.draw_image"""
        self.renderer.draw_image(imdata=utils.image_to_base64(image),
                                 extent=image.get_extent(),
                                 coordinates="data",
                                 style={"alpha": image.get_alpha(),
                                        "zorder": image.get_zorder()},
                                 mplobj=image)

########NEW FILE########
__FILENAME__ = base
import warnings
import itertools
from contextlib import contextmanager

import numpy as np
from matplotlib import transforms

from .. import utils
from .. import _py3k_compat as py3k


class Renderer(object):
    @staticmethod
    def ax_zoomable(ax):
        return bool(ax and ax.get_navigate())

    @staticmethod
    def ax_has_xgrid(ax):
        return bool(ax and ax.xaxis._gridOnMajor and ax.yaxis.get_gridlines())

    @staticmethod
    def ax_has_ygrid(ax):
        return bool(ax and ax.yaxis._gridOnMajor and ax.yaxis.get_gridlines())

    @property
    def current_ax_zoomable(self):
        return self.ax_zoomable(self._current_ax)

    @property
    def current_ax_has_xgrid(self):
        return self.ax_has_xgrid(self._current_ax)

    @property
    def current_ax_has_ygrid(self):
        return self.ax_has_ygrid(self._current_ax)

    @contextmanager
    def draw_figure(self, fig, props):
        if hasattr(self, "_current_fig") and self._current_fig is not None:
            warnings.warn("figure embedded in figure: something is wrong")
        self._current_fig = fig
        self._fig_props = props
        self.open_figure(fig=fig, props=props)
        yield
        self.close_figure(fig=fig)
        self._current_fig = None
        self._fig_props = {}

    @contextmanager
    def draw_axes(self, ax, props):
        if hasattr(self, "_current_ax") and self._current_ax is not None:
            warnings.warn("axes embedded in axes: something is wrong")
        self._current_ax = ax
        self._ax_props = props
        self.open_axes(ax=ax, props=props)
        yield
        self.close_axes(ax=ax)
        self._current_ax = None
        self._ax_props = {}

    @contextmanager
    def draw_legend(self, legend, props):
        self._current_legend = legend
        self._legend_props = props
        self.open_legend(legend=legend, props=props)
        yield
        self.close_legend(legend=legend)
        self._current_legend = None
        self._legend_props = {}

    # Following are the functions which should be overloaded in subclasses

    def open_figure(self, fig, props):
        """
        Begin commands for a particular figure.

        Parameters
        ----------
        fig : matplotlib.Figure
            The Figure which will contain the ensuing axes and elements
        props : dictionary
            The dictionary of figure properties
        """
        pass

    def close_figure(self, fig):
        """
        Finish commands for a particular figure.

        Parameters
        ----------
        fig : matplotlib.Figure
            The figure which is finished being drawn.
        """
        pass

    def open_axes(self, ax, props):
        """
        Begin commands for a particular axes.

        Parameters
        ----------
        ax : matplotlib.Axes
            The Axes which will contain the ensuing axes and elements
        props : dictionary
            The dictionary of axes properties
        """
        pass

    def close_axes(self, ax):
        """
        Finish commands for a particular axes.

        Parameters
        ----------
        ax : matplotlib.Axes
            The Axes which is finished being drawn.
        """
        pass

    def open_legend(self, legend, props):
        """
        Beging commands for a particular legend.

        Parameters
        ----------
        legend : matplotlib.legend.Legend
                The Legend that will contain the ensuing elements
        props : dictionary
                The dictionary of legend properties
        """
        pass

    def close_legend(self, legend):
        """
        Finish commands for a particular legend.

        Parameters
        ----------
        legend : matplotlib.legend.Legend
                The Legend which is finished being drawn
        """
        pass

    def draw_marked_line(self, data, coordinates, linestyle, markerstyle,
                         label, mplobj=None):
        """Draw a line that also has markers.

        If this isn't reimplemented by a renderer object, by default, it will
        make a call to BOTH draw_line and draw_markers when both markerstyle
        and linestyle are not None in the same Line2D object.

        """
        if linestyle is not None:
            self.draw_line(data, coordinates, linestyle, label, mplobj)
        if markerstyle is not None:
            self.draw_markers(data, coordinates, markerstyle, label, mplobj)

    def draw_line(self, data, coordinates, style, label, mplobj=None):
        """
        Draw a line. By default, draw the line via the draw_path() command.
        Some renderers might wish to override this and provide more
        fine-grained behavior.

        In matplotlib, lines are generally created via the plt.plot() command,
        though this command also can create marker collections.

        Parameters
        ----------
        data : array_like
            A shape (N, 2) array of datapoints.
        coordinates : string
            A string code, which should be either 'data' for data coordinates,
            or 'figure' for figure (pixel) coordinates.
        style : dictionary
            a dictionary specifying the appearance of the line.
        mplobj : matplotlib object
            the matplotlib plot element which generated this line
        """
        pathcodes = ['M'] + (data.shape[0] - 1) * ['L']
        pathstyle = dict(facecolor='none', **style)
        pathstyle['edgecolor'] = pathstyle.pop('color')
        pathstyle['edgewidth'] = pathstyle.pop('linewidth')
        self.draw_path(data=data, coordinates=coordinates,
                       pathcodes=pathcodes, style=pathstyle, mplobj=mplobj)

    @staticmethod
    def _iter_path_collection(paths, path_transforms, offsets, styles):
        """Build an iterator over the elements of the path collection"""
        N = max(len(paths), len(offsets))

        if not path_transforms:
            path_transforms = [np.eye(3)]

        edgecolor = styles['edgecolor']
        if np.size(edgecolor) == 0:
            edgecolor = ['none']
        facecolor = styles['facecolor']
        if np.size(facecolor) == 0:
            facecolor = ['none']

        elements = [paths, path_transforms, offsets,
                    edgecolor, styles['linewidth'], facecolor]

        it = itertools
        return it.islice(py3k.zip(*py3k.map(it.cycle, elements)), N)

    def draw_path_collection(self, paths, path_coordinates, path_transforms,
                             offsets, offset_coordinates, offset_order,
                             styles, mplobj=None):
        """
        Draw a collection of paths. The paths, offsets, and styles are all
        iterables, and the number of paths is max(len(paths), len(offsets)).

        By default, this is implemented via multiple calls to the draw_path()
        function. For efficiency, Renderers may choose to customize this
        implementation.

        Examples of path collections created by matplotlib are scatter plots,
        histograms, contour plots, and many others.

        Parameters
        ----------
        paths : list
            list of tuples, where each tuple has two elements:
            (data, pathcodes).  See draw_path() for a description of these.
        path_coordinates: string
            the coordinates code for the paths, which should be either
            'data' for data coordinates, or 'figure' for figure (pixel)
            coordinates.
        path_transforms: array_like
            an array of shape (*, 3, 3), giving a series of 2D Affine
            transforms for the paths. These encode translations, rotations,
            and scalings in the standard way.
        offsets: array_like
            An array of offsets of shape (N, 2)
        offset_coordinates : string
            the coordinates code for the offsets, which should be either
            'data' for data coordinates, or 'figure' for figure (pixel)
            coordinates.
        offset_order : string
            either "before" or "after". This specifies whether the offset
            is applied before the path transform, or after.  The matplotlib
            backend equivalent is "before"->"data", "after"->"screen".
        styles: dictionary
            A dictionary in which each value is a list of length N, containing
            the style(s) for the paths.
        mplobj : matplotlib object
            the matplotlib plot element which generated this collection
        """
        if offset_order == "before":
            raise NotImplementedError("offset before transform")

        for tup in self._iter_path_collection(paths, path_transforms,
                                              offsets, styles):
            (path, path_transform, offset, ec, lw, fc) = tup
            vertices, pathcodes = path
            path_transform = transforms.Affine2D(path_transform)
            vertices = path_transform.transform(vertices)
            # This is a hack:
            if path_coordinates == "figure":
                path_coordinates = "points"
            style = {"edgecolor": utils.color_to_hex(ec),
                     "facecolor": utils.color_to_hex(fc),
                     "edgewidth": lw,
                     "dasharray": "10,0",
                     "alpha": styles['alpha'],
                     "zorder": styles['zorder']}
            self.draw_path(data=vertices, coordinates=path_coordinates,
                           pathcodes=pathcodes, style=style, offset=offset,
                           offset_coordinates=offset_coordinates,
                           mplobj=mplobj)

    def draw_markers(self, data, coordinates, style, label, mplobj=None):
        """
        Draw a set of markers. By default, this is done by repeatedly
        calling draw_path(), but renderers should generally overload
        this method to provide a more efficient implementation.

        In matplotlib, markers are created using the plt.plot() command.

        Parameters
        ----------
        data : array_like
            A shape (N, 2) array of datapoints.
        coordinates : string
            A string code, which should be either 'data' for data coordinates,
            or 'figure' for figure (pixel) coordinates.
        style : dictionary
            a dictionary specifying the appearance of the markers.
        mplobj : matplotlib object
            the matplotlib plot element which generated this marker collection
        """
        vertices, pathcodes = style['markerpath']
        pathstyle = dict((key, style[key]) for key in ['alpha', 'edgecolor',
                                                       'facecolor', 'zorder',
                                                       'edgewidth'])
        pathstyle['dasharray'] = "10,0"
        for vertex in data:
            self.draw_path(data=vertices, coordinates="points",
                           pathcodes=pathcodes, style=pathstyle,
                           offset=vertex, offset_coordinates=coordinates,
                           mplobj=mplobj)

    def draw_text(self, text, position, coordinates, style,
                  text_type=None, mplobj=None):
        """
        Draw text on the image.

        Parameters
        ----------
        text : string
            The text to draw
        position : tuple
            The (x, y) position of the text
        coordinates : string
            A string code, which should be either 'data' for data coordinates,
            or 'figure' for figure (pixel) coordinates.
        style : dictionary
            a dictionary specifying the appearance of the text.
        text_type : string or None
            if specified, a type of text such as "xlabel", "ylabel", "title"
        mplobj : matplotlib object
            the matplotlib plot element which generated this text
        """
        raise NotImplementedError()

    def draw_path(self, data, coordinates, pathcodes, style,
                  offset=None, offset_coordinates="data", mplobj=None):
        """
        Draw a path.

        In matplotlib, paths are created by filled regions, histograms,
        contour plots, patches, etc.

        Parameters
        ----------
        data : array_like
            A shape (N, 2) array of datapoints.
        coordinates : string
            A string code, which should be either 'data' for data coordinates,
            'figure' for figure (pixel) coordinates, or "points" for raw
            point coordinates (useful in conjunction with offsets, below).
        pathcodes : list
            A list of single-character SVG pathcodes associated with the data.
            Path codes are one of ['M', 'm', 'L', 'l', 'Q', 'q', 'T', 't',
                                   'S', 's', 'C', 'c', 'Z', 'z']
            See the SVG specification for details.  Note that some path codes
            consume more than one datapoint (while 'Z' consumes none), so
            in general, the length of the pathcodes list will not be the same
            as that of the data array.
        style : dictionary
            a dictionary specifying the appearance of the line.
        offset : list (optional)
            the (x, y) offset of the path. If not given, no offset will
            be used.
        offset_coordinates : string (optional)
            A string code, which should be either 'data' for data coordinates,
            or 'figure' for figure (pixel) coordinates.
        mplobj : matplotlib object
            the matplotlib plot element which generated this path
        """
        raise NotImplementedError()

    def draw_image(self, imdata, extent, coordinates, style, mplobj=None):
        """
        Draw an image.

        Parameters
        ----------
        imdata : string
            base64 encoded png representation of the image
        extent : list
            the axes extent of the image: [xmin, xmax, ymin, ymax]
        coordinates: string
            A string code, which should be either 'data' for data coordinates,
            or 'figure' for figure (pixel) coordinates.
        style : dictionary
            a dictionary specifying the appearance of the image
        mplobj : matplotlib object
            the matplotlib plot object which generated this image
        """
        raise NotImplementedError()

########NEW FILE########
__FILENAME__ = fake_renderer
from .base import Renderer


class FakeRenderer(Renderer):
    """
    Fake Renderer

    This is a fake renderer which simply outputs a text tree representing the
    elements found in the plot(s).  This is used in the unit tests for the
    package.

    Below are the methods your renderer must implement. You are free to do
    anything you wish within the renderer (i.e. build an XML or JSON
    representation, call an external API, etc.)  Here the renderer just
    builds a simple string representation for testing purposes.
    """
    def __init__(self):
        self.output = ""

    def open_figure(self, fig, props):
        self.output += "opening figure\n"

    def close_figure(self, fig):
        self.output += "closing figure\n"

    def open_axes(self, ax, props):
        self.output += "  opening axes\n"

    def close_axes(self, ax):
        self.output += "  closing axes\n"

    def open_legend(self, legend, props):
        self.output += "    opening legend\n"

    def close_legend(self, legend):
        self.output += "    closing legend\n"

    def draw_text(self, text, position, coordinates, style,
                  text_type=None, mplobj=None):
        self.output += "    draw text '{0}' {1}\n".format(text, text_type)

    def draw_path(self, data, coordinates, pathcodes, style,
                  offset=None, offset_coordinates="data", mplobj=None):
        self.output += "    draw path with {0} vertices\n".format(data.shape[0])

    def draw_image(self, imdata, extent, coordinates, style, mplobj=None):
        self.output += "    draw image of size {0}\n".format(len(imdata))


class FullFakeRenderer(FakeRenderer):
    """
    Renderer with the full complement of methods.

    When the following are left undefined, they will be implemented via
    other methods in the class.  They can be defined explicitly for
    more efficient or specialized use within the renderer implementation.
    """
    def draw_line(self, data, coordinates, style, label, mplobj=None):
        self.output += "    draw line with {0} points\n".format(data.shape[0])

    def draw_markers(self, data, coordinates, style, label, mplobj=None):
        self.output += "    draw {0} markers\n".format(data.shape[0])

    def draw_path_collection(self, paths, path_coordinates, path_transforms,
                             offsets, offset_coordinates, offset_order,
                             styles, mplobj=None):
        self.output += ("    draw path collection "
                        "with {0} offsets\n".format(offsets.shape[0]))

########NEW FILE########
__FILENAME__ = vega_renderer
import warnings
import json
import random
from .base import Renderer
from ..exporter import Exporter


class VegaRenderer(Renderer):
    def open_figure(self, fig, props):
        self.props = props
        self.figwidth = int(props['figwidth'] * props['dpi'])
        self.figheight = int(props['figheight'] * props['dpi'])
        self.data = []
        self.scales = []
        self.axes = []
        self.marks = []
            
    def open_axes(self, ax, props):
        if len(self.axes) > 0:
            warnings.warn("multiple axes not yet supported")
        self.axes = [dict(type="x", scale="x", ticks=10),
                     dict(type="y", scale="y", ticks=10)]
        self.scales = [dict(name="x",
                            domain=props['xlim'],
                            type="linear",
                            range="width",
                        ),
                       dict(name="y",
                            domain=props['ylim'],
                            type="linear",
                            range="height",
                        ),]

    def draw_line(self, data, coordinates, style, label, mplobj=None):
        if coordinates != 'data':
            warnings.warn("Only data coordinates supported. Skipping this")
        dataname = "table{0:03d}".format(len(self.data) + 1)

        # TODO: respect the other style settings
        self.data.append({'name': dataname,
                          'values': [dict(x=d[0], y=d[1]) for d in data]})
        self.marks.append({'type': 'line',
                           'from': {'data': dataname},
                           'properties': {
                               "enter": {
                                   "interpolate": {"value": "monotone"},
                                   "x": {"scale": "x", "field": "data.x"},
                                   "y": {"scale": "y", "field": "data.y"},
                                   "stroke": {"value": style['color']},
                                   "strokeOpacity": {"value": style['alpha']},
                                   "strokeWidth": {"value": style['linewidth']},
                               }
                           }
                       })

    def draw_markers(self, data, coordinates, style, label, mplobj=None):
        if coordinates != 'data':
            warnings.warn("Only data coordinates supported. Skipping this")
        dataname = "table{0:03d}".format(len(self.data) + 1)

        # TODO: respect the other style settings
        self.data.append({'name': dataname,
                          'values': [dict(x=d[0], y=d[1]) for d in data]})
        self.marks.append({'type': 'symbol',
                           'from': {'data': dataname},
                           'properties': {
                               "enter": {
                                   "interpolate": {"value": "monotone"},
                                   "x": {"scale": "x", "field": "data.x"},
                                   "y": {"scale": "y", "field": "data.y"},
                                   "fill": {"value": style['facecolor']},
                                   "fillOpacity": {"value": style['alpha']},
                                   "stroke": {"value": style['edgecolor']},
                                   "strokeOpacity": {"value": style['alpha']},
                                   "strokeWidth": {"value": style['edgewidth']},
                               }
                           }
                       })

    def draw_text(self, text, position, coordinates, style,
                  text_type=None, mplobj=None):
        if text_type == 'xlabel':
            self.axes[0]['title'] = text
        elif text_type == 'ylabel':
            self.axes[1]['title'] = text


class VegaHTML(object):
    def __init__(self, renderer):
        self.specification = dict(width=renderer.figwidth,
                                  height=renderer.figheight,
                                  data=renderer.data,
                                  scales=renderer.scales,
                                  axes=renderer.axes,
                                  marks=renderer.marks)

    def html(self):
        """Build the HTML representation for IPython."""
        id = random.randint(0, 2 ** 16)
        html = '<div id="vis%d"></div>' % id
        html += '<script>\n'
        html += VEGA_TEMPLATE % (json.dumps(self.specification), id)
        html += '</script>\n'
        return html

    def _repr_html_(self):
        return self.html()


def fig_to_vega(fig, notebook=False):
    """Convert a matplotlib figure to vega dictionary

    if notebook=True, then return an object which will display in a notebook
    otherwise, return an HTML string.
    """
    renderer = VegaRenderer()
    Exporter(renderer).run(fig)
    vega_html = VegaHTML(renderer)
    if notebook:
        return vega_html
    else:
        return vega_html.html()


VEGA_TEMPLATE = """
( function() {
  var _do_plot = function() {
    if ( (typeof vg == 'undefined') && (typeof IPython != 'undefined')) {
      $([IPython.events]).on("vega_loaded.vincent", _do_plot);
      return;
    }
    vg.parse.spec(%s, function(chart) {
      chart({el: "#vis%d"}).update();
    });
  };
  _do_plot();
})();
"""

########NEW FILE########
__FILENAME__ = vincent_renderer
import warnings
from .base import Renderer
from ..exporter import Exporter


class VincentRenderer(Renderer):
    def open_figure(self, fig, props):
        self.chart = None
        self.figwidth = int(props['figwidth'] * props['dpi'])
        self.figheight = int(props['figheight'] * props['dpi'])

    def draw_line(self, data, coordinates, style, label, mplobj=None):
        import vincent  # only import if VincentRenderer is used
        if coordinates != 'data':
            warnings.warn("Only data coordinates supported. Skipping this")
        linedata = {'x': data[:, 0],
                    'y': data[:, 1]}
        line = vincent.Line(linedata, iter_idx='x',
                            width=self.figwidth, height=self.figheight)

        # TODO: respect the other style settings
        line.scales['color'].range = [style['color']]

        if self.chart is None:
            self.chart = line
        else:
            warnings.warn("Multiple plot elements not yet supported")

    def draw_markers(self, data, coordinates, style, label, mplobj=None):
        import vincent  # only import if VincentRenderer is used
        if coordinates != 'data':
            warnings.warn("Only data coordinates supported. Skipping this")
        markerdata = {'x': data[:, 0],
                      'y': data[:, 1]}
        markers = vincent.Scatter(markerdata, iter_idx='x',
                                  width=self.figwidth, height=self.figheight)

        # TODO: respect the other style settings
        markers.scales['color'].range = [style['facecolor']]

        if self.chart is None:
            self.chart = markers
        else:
            warnings.warn("Multiple plot elements not yet supported")


def fig_to_vincent(fig):
    """Convert a matplotlib figure to a vincent object"""
    renderer = VincentRenderer()
    exporter = Exporter(renderer)
    exporter.run(fig)
    return renderer.chart

########NEW FILE########
__FILENAME__ = test_basic
from ..exporter import Exporter
from ..renderers import FakeRenderer, FullFakeRenderer

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
from numpy.testing import assert_warns


def fake_renderer_output(fig, Renderer):
    renderer = Renderer()
    exporter = Exporter(renderer)
    exporter.run(fig)
    return renderer.output


def _assert_output_equal(text1, text2):
    for line1, line2 in zip(text1.strip().split(), text2.strip().split()):
        assert line1 == line2


def test_lines():
    fig, ax = plt.subplots()
    ax.plot(range(20), '-k')

    _assert_output_equal(fake_renderer_output(fig, FakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw path with 20 vertices
                         closing axes
                         closing figure
                         """)

    _assert_output_equal(fake_renderer_output(fig, FullFakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw line with 20 points
                         closing axes
                         closing figure
                         """)


def test_markers():
    fig, ax = plt.subplots()
    ax.plot(range(2), 'ok')

    _assert_output_equal(fake_renderer_output(fig, FakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw path with 25 vertices
                         draw path with 25 vertices
                         closing axes
                         closing figure
                         """)

    _assert_output_equal(fake_renderer_output(fig, FullFakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw 2 markers
                         closing axes
                         closing figure
                         """)


def test_path_collection():
    fig, ax = plt.subplots()
    ax.scatter(range(3), range(3))

    _assert_output_equal(fake_renderer_output(fig, FakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw path with 25 vertices
                         draw path with 25 vertices
                         draw path with 25 vertices
                         closing axes
                         closing figure
                         """)

    _assert_output_equal(fake_renderer_output(fig, FullFakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw path collection with 3 offsets
                         closing axes
                         closing figure
                         """)


def test_text():
    fig, ax = plt.subplots()
    ax.set_xlabel("my x label")
    ax.set_ylabel("my y label")
    ax.set_title("my title")
    ax.text(0.5, 0.5, "my text")

    _assert_output_equal(fake_renderer_output(fig, FakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw text 'my text' None
                         draw text 'my x label' xlabel
                         draw text 'my y label' ylabel
                         draw text 'my title' title
                         closing axes
                         closing figure
                         """)


def test_path():
    fig, ax = plt.subplots()
    ax.add_patch(plt.Circle((0, 0), 1))
    ax.add_patch(plt.Rectangle((0, 0), 1, 2))

    _assert_output_equal(fake_renderer_output(fig, FakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw path with 25 vertices
                         draw path with 4 vertices
                         closing axes
                         closing figure
                         """)


def test_multiaxes():
    fig, ax = plt.subplots(2)
    ax[0].plot(range(4))
    ax[1].plot(range(10))

    _assert_output_equal(fake_renderer_output(fig, FakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw path with 4 vertices
                         closing axes
                         opening axes
                         draw path with 10 vertices
                         closing axes
                         closing figure
                         """)


def test_image():
    np.random.seed(0)  # image size depends on the seed
    fig, ax = plt.subplots()
    ax.imshow(np.random.random((10, 10)),
              cmap=plt.cm.jet, interpolation='nearest')

    _assert_output_equal(fake_renderer_output(fig, FakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw image of size 2848
                         closing axes
                         closing figure
                         """)


def test_legend():
    fig, ax = plt.subplots()
    ax.plot([1,2,3], label='label')
    ax.legend().set_visible(False)
    _assert_output_equal(fake_renderer_output(fig, FakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw path with 3 vertices
                         opening legend
                         closing legend
                         closing axes
                         closing figure
                         """)

def test_legend_dots():
    fig, ax = plt.subplots()
    ax.plot([1,2,3], label='label')
    ax.plot([2,2,2], 'o', label='dots')
    ax.legend().set_visible(True)
    _assert_output_equal(fake_renderer_output(fig, FullFakeRenderer),
                         """
                         opening figure
                         opening axes
                         draw line with 3 points
                         draw 3 markers
                         opening legend
                         draw line with 2 points
                         draw text 'label' None
                         draw 2 markers
                         draw text 'dots' None
                         draw path with 5 vertices
                         closing legend
                         closing axes
                         closing figure
                         """)

def test_blended():
    fig, ax = plt.subplots()
    ax.axvline(0)
    assert_warns(UserWarning, fake_renderer_output, fig, FakeRenderer)
    

########NEW FILE########
__FILENAME__ = test_utils
from numpy.testing import assert_allclose, assert_equal
import matplotlib.pyplot as plt
from .. import utils


def test_path_data():
    circle = plt.Circle((0, 0), 1)
    vertices, codes = utils.SVG_path(circle.get_path())

    assert_allclose(vertices.shape, (25, 2))
    assert_equal(codes, ['M', 'C', 'C', 'C', 'C', 'C', 'C', 'C', 'C', 'Z'])

########NEW FILE########
__FILENAME__ = tools
"""
Tools for matplotlib plot exporting
"""


def ipynb_vega_init():
    """Initialize the IPython notebook display elements

    This function borrows heavily from the excellent vincent package:
    http://github.com/wrobstory/vincent
    """
    try:
        from IPython.core.display import display, HTML
    except ImportError:
        print('IPython Notebook could not be loaded.')

    require_js = '''
    if (window['d3'] === undefined) {{
        require.config({{ paths: {{d3: "http://d3js.org/d3.v3.min"}} }});
        require(["d3"], function(d3) {{
          window.d3 = d3;
          {0}
        }});
    }};
    if (window['topojson'] === undefined) {{
        require.config(
            {{ paths: {{topojson: "http://d3js.org/topojson.v1.min"}} }}
            );
        require(["topojson"], function(topojson) {{
          window.topojson = topojson;
        }});
    }};
    '''
    d3_geo_projection_js_url = "http://d3js.org/d3.geo.projection.v0.min.js"
    d3_layout_cloud_js_url = ("http://wrobstory.github.io/d3-cloud/"
                              "d3.layout.cloud.js")
    topojson_js_url = "http://d3js.org/topojson.v1.min.js"
    vega_js_url = 'http://trifacta.github.com/vega/vega.js'

    dep_libs = '''$.getScript("%s", function() {
        $.getScript("%s", function() {
            $.getScript("%s", function() {
                $.getScript("%s", function() {
                        $([IPython.events]).trigger("vega_loaded.vincent");
                })
            })
        })
    });''' % (d3_geo_projection_js_url, d3_layout_cloud_js_url,
              topojson_js_url, vega_js_url)
    load_js = require_js.format(dep_libs)
    html = '<script>'+load_js+'</script>'
    display(HTML(html))

########NEW FILE########
__FILENAME__ = utils
"""
Utility Routines for Working with Matplotlib Objects
====================================================
"""
import itertools
import io
import base64

import numpy as np

import warnings

import matplotlib
from matplotlib.colors import colorConverter
from matplotlib.path import Path
from matplotlib.markers import MarkerStyle
from matplotlib.transforms import Affine2D
from matplotlib import ticker


def color_to_hex(color):
    """Convert matplotlib color code to hex color code"""
    if color is None or colorConverter.to_rgba(color)[3] == 0:
        return 'none'
    else:
        rgb = colorConverter.to_rgb(color)
        return '#{0:02X}{1:02X}{2:02X}'.format(*(int(255 * c) for c in rgb))


def many_to_one(input_dict):
    """Convert a many-to-one mapping to a one-to-one mapping"""
    return dict((key, val)
                for keys, val in input_dict.items()
                for key in keys)

LINESTYLES = many_to_one({('solid', '-', (None, None)): "10,0",
                          ('dashed', '--'): "6,6",
                          ('dotted', ':'): "2,2",
                          ('dashdot', '-.'): "4,4,2,4",
                          ('', ' ', 'None', 'none'): "none"})


def get_dasharray(obj, i=None):
    """Get an SVG dash array for the given matplotlib linestyle

    Parameters
    ----------
    obj : matplotlib object
        The matplotlib line or path object, which must have a get_linestyle()
        method which returns a valid matplotlib line code
    i : integer (optional)

    Returns
    -------
    dasharray : string
        The HTML/SVG dasharray code associated with the object.
    """
    if obj.__dict__.get('_dashSeq', None) is not None:
        return ','.join(map(str, obj._dashSeq))
    else:
        ls = obj.get_linestyle()
        if i is not None:
            ls = ls[i]

        dasharray = LINESTYLES.get(ls, None)
        if dasharray is None:
            warnings.warn("dash style '{0}' not understood: "
                          "defaulting to solid.".format(ls))
            dasharray = LINESTYLES['-']
        return dasharray


PATH_DICT = {Path.LINETO: 'L',
             Path.MOVETO: 'M',
             Path.CURVE3: 'S',
             Path.CURVE4: 'C',
             Path.CLOSEPOLY: 'Z'}


def SVG_path(path, transform=None, simplify=False):
    """Construct the vertices and SVG codes for the path

    Parameters
    ----------
    path : matplotlib.Path object

    transform : matplotlib transform (optional)
        if specified, the path will be transformed before computing the output.

    Returns
    -------
    vertices : array
        The shape (M, 2) array of vertices of the Path. Note that some Path
        codes require multiple vertices, so the length of these vertices may
        be longer than the list of path codes.
    path_codes : list
        A length N list of single-character path codes, N <= M. Each code is
        a single character, in ['L','M','S','C','Z']. See the standard SVG
        path specification for a description of these.
    """
    if transform is not None:
        path = path.transformed(transform)

    vc_tuples = [(vertices if path_code != Path.CLOSEPOLY else [],
                  PATH_DICT[path_code])
                 for (vertices, path_code)
                 in path.iter_segments(simplify=simplify)]

    if not vc_tuples:
        # empty path is a special case
        return np.zeros((0, 2)), []
    else:
        vertices, codes = zip(*vc_tuples)
        vertices = np.array(list(itertools.chain(*vertices))).reshape(-1, 2)
        return vertices, list(codes)


def get_path_style(path, fill=True):
    """Get the style dictionary for matplotlib path objects"""
    style = {}
    style['alpha'] = path.get_alpha()
    if style['alpha'] is None:
        style['alpha'] = 1
    style['edgecolor'] = color_to_hex(path.get_edgecolor())
    if fill:
        style['facecolor'] = color_to_hex(path.get_facecolor())
    else:
        style['facecolor'] = 'none'
    style['edgewidth'] = path.get_linewidth()
    style['dasharray'] = get_dasharray(path)
    style['zorder'] = path.get_zorder()
    return style


def get_line_style(line):
    """Get the style dictionary for matplotlib line objects"""
    style = {}
    style['alpha'] = line.get_alpha()
    if style['alpha'] is None:
        style['alpha'] = 1
    style['color'] = color_to_hex(line.get_color())
    style['linewidth'] = line.get_linewidth()
    style['dasharray'] = get_dasharray(line)
    style['zorder'] = line.get_zorder()
    return style


def get_marker_style(line):
    """Get the style dictionary for matplotlib marker objects"""
    style = {}
    style['alpha'] = line.get_alpha()
    if style['alpha'] is None:
        style['alpha'] = 1

    style['facecolor'] = color_to_hex(line.get_markerfacecolor())
    style['edgecolor'] = color_to_hex(line.get_markeredgecolor())
    style['edgewidth'] = line.get_markeredgewidth()

    style['marker'] = line.get_marker()
    markerstyle = MarkerStyle(line.get_marker())
    markersize = line.get_markersize()
    markertransform = (markerstyle.get_transform()
                       + Affine2D().scale(markersize, -markersize))
    style['markerpath'] = SVG_path(markerstyle.get_path(),
                                   markertransform)
    style['markersize'] = markersize
    style['zorder'] = line.get_zorder()
    return style


def get_text_style(text):
    """Return the text style dict for a text instance"""
    style = {}
    style['alpha'] = text.get_alpha()
    if style['alpha'] is None:
        style['alpha'] = 1
    style['fontsize'] = text.get_size()
    style['color'] = color_to_hex(text.get_color())
    style['halign'] = text.get_horizontalalignment()  # left, center, right
    style['valign'] = text.get_verticalalignment()  # baseline, center, top
    style['rotation'] = text.get_rotation()
    style['zorder'] = text.get_zorder()
    return style


def get_axis_properties(axis):
    """Return the property dictionary for a matplotlib.Axis instance"""
    props = {}
    label1On = axis._major_tick_kw.get('label1On', True)

    if isinstance(axis, matplotlib.axis.XAxis):
        if label1On:
            props['position'] = "bottom"
        else:
            props['position'] = "top"
    elif isinstance(axis, matplotlib.axis.YAxis):
        if label1On:
            props['position'] = "left"
        else:
            props['position'] = "right"
    else:
        raise ValueError("{0} should be an Axis instance".format(axis))

    # Use tick values if appropriate
    locator = axis.get_major_locator()
    props['nticks'] = len(locator())
    if isinstance(locator, ticker.FixedLocator):
        props['tickvalues'] = list(locator())
    else:
        props['tickvalues'] = None

    # Find tick formats
    formatter = axis.get_major_formatter()
    if isinstance(formatter, ticker.NullFormatter):
        props['tickformat'] = ""
    elif not any(label.get_visible() for label in axis.get_ticklabels()):
        props['tickformat'] = ""
    else:
        props['tickformat'] = None

    # Get axis scale
    props['scale'] = axis.get_scale()

    # Get major tick label size (assumes that's all we really care about!)
    labels = axis.get_ticklabels()
    if labels:
        props['fontsize'] = labels[0].get_fontsize()
    else:
        props['fontsize'] = None

    # Get associated grid
    props['grid'] = get_grid_style(axis)

    return props


def get_grid_style(axis):
    gridlines = axis.get_gridlines()
    if axis._gridOnMajor and len(gridlines) > 0:
        color = color_to_hex(gridlines[0].get_color())
        alpha = gridlines[0].get_alpha()
        dasharray = get_dasharray(gridlines[0])
        return dict(gridOn=True,
                    color=color,
                    dasharray=dasharray,
                    alpha=alpha)
    else:
        return {"gridOn":False}


def get_figure_properties(fig):
    return {'figwidth': fig.get_figwidth(),
            'figheight': fig.get_figheight(),
            'dpi': fig.dpi}


def get_axes_properties(ax):
    props = {'axesbg': color_to_hex(ax.patch.get_facecolor()),
             'axesbgalpha': ax.patch.get_alpha(),
             'bounds': ax.get_position().bounds,
             'dynamic': ax.get_navigate(),
             'axes': [get_axis_properties(ax.xaxis),
                      get_axis_properties(ax.yaxis)]}

    for axname in ['x', 'y']:
        axis = getattr(ax, axname + 'axis')
        domain = getattr(ax, 'get_{0}lim'.format(axname))()
        lim = domain
        if isinstance(axis.converter, matplotlib.dates.DateConverter):
            scale = 'date'
            try:
                import pandas as pd
                from pandas.tseries.converter import PeriodConverter
            except ImportError:
                pd = None

            if (pd is not None and isinstance(axis.converter,
                                              PeriodConverter)):
                _dates = [pd.Period(ordinal=int(d), freq=axis.freq)
                          for d in domain]
                domain = [(d.year, d.month - 1, d.day,
                           d.hour, d.minute, d.second, 0)
                          for d in _dates]
            else:
                domain = [(d.year, d.month - 1, d.day,
                           d.hour, d.minute, d.second,
                           d.microsecond * 1E-3)
                          for d in matplotlib.dates.num2date(domain)]
        else:
            scale = axis.get_scale()

        if scale not in ['date', 'linear', 'log']:
            raise ValueError("Unknown axis scale: "
                             "{0}".format(axis[axname].get_scale()))

        props[axname + 'scale'] = scale
        props[axname + 'lim'] = lim
        props[axname + 'domain'] = domain

    return props


def iter_all_children(obj, skipContainers=False):
    """
    Returns an iterator over all childen and nested children using
    obj's get_children() method

    if skipContainers is true, only childless objects are returned.
    """
    if hasattr(obj, 'get_children') and len(obj.get_children()) > 0:
        for child in obj.get_children():
            if not skipContainers:
                yield child
            # could use `yield from` in python 3...
            for grandchild in iter_all_children(child, skipContainers):
                yield grandchild
    else:
        yield obj


def get_legend_properties(ax, legend):
    handles, labels = ax.get_legend_handles_labels()
    visible = legend.get_visible()
    return {'handles': handles, 'labels': labels, 'visible': visible}
    

def image_to_base64(image):
    """
    Convert a matplotlib image to a base64 png representation

    Parameters
    ----------
    image : matplotlib image object
        The image to be converted.

    Returns
    -------
    image_base64 : string
        The UTF8-encoded base64 string representation of the png image.
    """
    ax = image.axes
    binary_buffer = io.BytesIO()

    # image is saved in axes coordinates: we need to temporarily
    # set the correct limits to get the correct image
    lim = ax.axis()
    ax.axis(image.get_extent())
    image.write_png(binary_buffer)
    ax.axis(lim)

    binary_buffer.seek(0)
    return base64.b64encode(binary_buffer.read()).decode('utf-8')

########NEW FILE########
__FILENAME__ = _py3k_compat
"""
Simple fixes for Python 2/3 compatibility
"""
import sys
PY3K = sys.version_info[0] >= 3


if PY3K:
    import builtins
    import functools
    reduce = functools.reduce
    zip = builtins.zip
    xrange = builtins.range
    map = builtins.map
else:
    import __builtin__
    import itertools
    builtins = __builtin__
    reduce = __builtin__.reduce
    zip = itertools.izip
    xrange = __builtin__.xrange
    map = itertools.imap

########NEW FILE########
__FILENAME__ = mpltools
"""
Tools

A module for converting from mpl language to plotly language.

"""

import math
import warnings

def check_bar_match(old_bar, new_bar):
    """Check if two bars belong in the same collection (bar chart).

    Positional arguments:
    old_bar -- a previously sorted bar dictionary.
    new_bar -- a new bar dictionary that needs to be sorted.

    """
    tests = []
    tests += new_bar['orientation'] == old_bar['orientation'],
    tests += new_bar['facecolor'] == old_bar['facecolor'],
    if new_bar['orientation'] == 'v':
        new_width = new_bar['x1'] - new_bar['x0']
        old_width = old_bar['x1'] - old_bar['x0']
        tests += new_width - old_width < 0.000001,
        tests += new_bar['y0'] == old_bar['y0'],
    elif new_bar['orientation'] == 'h':
        new_height = new_bar['y1'] - new_bar['y0']
        old_height = old_bar['y1'] - old_bar['y0']
        tests += new_height - old_height < 0.000001,
        tests += new_bar['x0'] == old_bar['x0'],
    if all(tests):
        return True
    else:
        return False


def convert_affine_trans(dpi=None, aff=None):
    if aff is not None and dpi is not None:
        try:
            return aff.to_values()[0]*72/dpi
        except AttributeError:
            return aff[0][0]*72/dpi
    else:
        return None


def convert_dash(mpl_dash):
    """Convert mpl line symbol to plotly line symbol and return symbol."""
    if mpl_dash in DASH_MAP:
        return DASH_MAP[mpl_dash]
    else:
        return 'solid'  # default


def convert_path(path):
    verts = path[0]  # may use this later
    code = tuple(path[1])
    if code in PATH_MAP:
        return PATH_MAP[code]
    else:
        return None


def convert_symbol(mpl_symbol):
    """Convert mpl marker symbol to plotly symbol and return symbol."""
    if mpl_symbol in SYMBOL_MAP:
        return SYMBOL_MAP[mpl_symbol]
    else:
        return 'dot'  # default


def convert_va(mpl_va):
    """Convert mpl vertical alignment word to equivalent HTML word.

    Text alignment specifiers from mpl differ very slightly from those used
    in HTML. See the VA_MAP for more details.

    Positional arguments:
    mpl_va -- vertical mpl text alignment spec.

    """
    if mpl_va in VA_MAP:
        return VA_MAP[mpl_va]
    else:
        return None  # let plotly figure it out!


def convert_x_domain(mpl_plot_bounds, mpl_max_x_bounds):
    """Map x dimension of current plot to plotly's domain space.

    The bbox used to locate an axes object in mpl differs from the
    method used to locate axes in plotly. The mpl version locates each
    axes in the figure so that axes in a single-plot figure might have
    the bounds, [0.125, 0.125, 0.775, 0.775] (x0, y0, width, height),
    in mpl's figure coordinates. However, the axes all share one space in
    plotly such that the domain will always be [0, 0, 1, 1]
    (x0, y0, x1, y1). To convert between the two, the mpl figure bounds
    need to be mapped to a [0, 1] domain for x and y. The margins set
    upon opening a new figure will appropriately match the mpl margins.

    Optionally, setting margins=0 and simply copying the domains from
    mpl to plotly would place axes appropriately. However,
    this would throw off axis and title labeling.

    Positional arguments:
    mpl_plot_bounds -- the (x0, y0, width, height) params for current ax **
    mpl_max_x_bounds -- overall (x0, x1) bounds for all axes **

    ** these are all specified in mpl figure coordinates

    """
    mpl_x_dom = [mpl_plot_bounds[0], mpl_plot_bounds[0]+mpl_plot_bounds[2]]
    plotting_width = (mpl_max_x_bounds[1]-mpl_max_x_bounds[0])
    x0 = (mpl_x_dom[0]-mpl_max_x_bounds[0])/plotting_width
    x1 = (mpl_x_dom[1]-mpl_max_x_bounds[0])/plotting_width
    return [x0, x1]


def convert_y_domain(mpl_plot_bounds, mpl_max_y_bounds):
    """Map y dimension of current plot to plotly's domain space.

    The bbox used to locate an axes object in mpl differs from the
    method used to locate axes in plotly. The mpl version locates each
    axes in the figure so that axes in a single-plot figure might have
    the bounds, [0.125, 0.125, 0.775, 0.775] (x0, y0, width, height),
    in mpl's figure coordinates. However, the axes all share one space in
    plotly such that the domain will always be [0, 0, 1, 1]
    (x0, y0, x1, y1). To convert between the two, the mpl figure bounds
    need to be mapped to a [0, 1] domain for x and y. The margins set
    upon opening a new figure will appropriately match the mpl margins.

    Optionally, setting margins=0 and simply copying the domains from
    mpl to plotly would place axes appropriately. However,
    this would throw off axis and title labeling.

    Positional arguments:
    mpl_plot_bounds -- the (x0, y0, width, height) params for current ax **
    mpl_max_y_bounds -- overall (y0, y1) bounds for all axes **

    ** these are all specified in mpl figure coordinates

    """
    mpl_y_dom = [mpl_plot_bounds[1], mpl_plot_bounds[1]+mpl_plot_bounds[3]]
    plotting_height = (mpl_max_y_bounds[1]-mpl_max_y_bounds[0])
    y0 = (mpl_y_dom[0]-mpl_max_y_bounds[0])/plotting_height
    y1 = (mpl_y_dom[1]-mpl_max_y_bounds[0])/plotting_height
    return [y0, y1]


def display_to_paper(x, y, layout):
    """Convert mpl display coordinates to plotly paper coordinates.

    Plotly references object positions with an (x, y) coordinate pair in either
    'data' or 'paper' coordinates which reference actual data in a plot or
    the entire plotly axes space where the bottom-left of the bottom-left
    plot has the location (x, y) = (0, 0) and the top-right of the top-right
    plot has the location (x, y) = (1, 1). Display coordinates in mpl reference
    objects with an (x, y) pair in pixel coordinates, where the bottom-left
    corner is at the location (x, y) = (0, 0) and the top-right corner is at
    the location (x, y) = (figwidth*dpi, figheight*dpi). Here, figwidth and
    figheight are in inches and dpi are the dots per inch resolution.

    """
    num_x = x - layout['margin']['l']
    den_x = layout['width'] - (layout['margin']['l'] + layout['margin']['r'])
    num_y = y - layout['margin']['b']
    den_y = layout['height'] - (layout['margin']['b'] + layout['margin']['t'])
    return num_x/den_x, num_y/den_y


def get_axes_bounds(fig):
    """Return the entire axes space for figure.

    An axes object in mpl is specified by its relation to the figure where
    (0,0) corresponds to the bottom-left part of the figure and (1,1)
    corresponds to the top-right. Margins exist in matplotlib because axes
    objects normally don't go to the edges of the figure.

    In plotly, the axes area (where all subplots go) is always specified with
    the domain [0,1] for both x and y. This function finds the smallest box,
    specified by two points, that all of the mpl axes objects fit into. This
    box is then used to map mpl axes domains to plotly axes domains.

    """
    x_min, x_max, y_min, y_max = [], [], [], []
    for axes_obj in fig.get_axes():
        bounds = axes_obj.get_position().bounds
        x_min.append(bounds[0])
        x_max.append(bounds[0]+bounds[2])
        y_min.append(bounds[1])
        y_max.append(bounds[1]+bounds[3])
    x_min, y_min, x_max, y_max = min(x_min), min(y_min), max(x_max), max(y_max)
    return (x_min, x_max), (y_min, y_max)


def get_rect_xmin(data):
    """Find minimum x value from four (x,y) vertices."""
    return min(data[0][0], data[1][0], data[2][0], data[3][0])


def get_rect_xmax(data):
    """Find maximum x value from four (x,y) vertices."""
    return max(data[0][0], data[1][0], data[2][0], data[3][0])


def get_rect_ymin(data):
    """Find minimum y value from four (x,y) vertices."""
    return min(data[0][1], data[1][1], data[2][1], data[3][1])


def get_rect_ymax(data):
    """Find maximum y value from four (x,y) vertices."""
    return max(data[0][1], data[1][1], data[2][1], data[3][1])


def is_bar(**props):
    """A test to decide whether a path is a bar from a vertical bar chart."""
    tests = []
    tests += get_rect_ymin(props['data']) == 0,
    if all(tests):
        return True
    else:
        return False


def is_barh(**props):
    """A test to decide whether a path is a bar from a horizontal bar chart."""
    tests = []
    tests += get_rect_xmin(props['data']) == 0,
    if all(tests):
        return True
    else:
        return False


def make_bar(**props):
    """Make an intermediate bar dictionary.

    This creates a bar dictionary which aids in the comparison of new bars to
    old bars from other bar chart (patch) collections. This is not the
    dictionary that needs to get passed to plotly as a data dictionary. That
    happens in PlotlyRenderer in that class's draw_bar method. In other
    words, this dictionary describes a SINGLE bar, whereas, plotly will
    require a set of bars to be passed in a data dictionary.

    """
    return {
        'bar': props['mplobj'],
        'orientation': props['orientation'],
        'x0': get_rect_xmin(props['data']),
        'y0': get_rect_ymin(props['data']),
        'x1': get_rect_xmax(props['data']),
        'y1': get_rect_ymax(props['data']),
        'alpha': props['style']['alpha'],
        'edgecolor': props['style']['edgecolor'],
        'facecolor': props['style']['facecolor'],
        'edgewidth': props['style']['edgewidth'],
        'dasharray': props['style']['dasharray'],
        'zorder': props['style']['zorder']
    }


def prep_x_ticks(ax, props):
    axis = dict()
    scale = props['axes'][0]['scale']
    if scale == 'linear':
        try:
            tickvalues = props['axes'][0]['tickvalues']
            axis['tick0'] = tickvalues[0]
            dticks = [round(tickvalues[i]-tickvalues[i-1], 12)
                      for i in range(1, len(tickvalues) - 1)]
            if all([dticks[i] == dticks[i-1]
                    for i in range(1, len(dticks) - 1)]):
                axis['dtick'] = tickvalues[1] - tickvalues[0]
            else:
                warnings.warn("'linear' x-axis tick spacing not even, "
                              "ignoring mpl tick formatting.")
                raise TypeError
            axis['autotick'] = False
        except (IndexError, TypeError):
            axis = dict(nticks=props['axes'][0]['nticks'])
        return axis
    elif scale == 'log':
        try:
            axis['tick0'] = props['axes'][0]['tickvalues'][0]
            axis['dtick'] = props['axes'][0]['tickvalues'][1] - \
                            props['axes'][0]['tickvalues'][0]
            axis['autotick'] = False
        except (IndexError, TypeError):
            axis = dict(nticks=props['axes'][0]['nticks'])
        base = ax.get_xaxis().get_transform().base
        if base == 10:
            axis['range'] = [math.log10(props['xlim'][0]),
                             math.log10(props['xlim'][1])]
        else:
            axis = dict(range=None, type='linear')
            warnings.warn("Converted non-base10 x-axis log scale to 'linear'")
        return axis
    else:
        return dict()


def prep_y_ticks(ax, props):
    axis = dict()
    scale = props['axes'][1]['scale']
    if scale == 'linear':
        try:
            tickvalues = props['axes'][1]['tickvalues']
            axis['tick0'] = tickvalues[0]
            dticks = [round(tickvalues[i]-tickvalues[i-1], 12)
                      for i in range(1, len(tickvalues) - 1)]
            if all([dticks[i] == dticks[i-1]
                    for i in range(1, len(dticks) - 1)]):
                axis['dtick'] = tickvalues[1] - tickvalues[0]
            else:
                warnings.warn("'linear' y-axis tick spacing not even, "
                              "ignoring mpl tick formatting.")
                raise TypeError
            axis['autotick'] = False
        except (IndexError, TypeError):
            axis = dict(nticks=props['axes'][1]['nticks'])
        return axis
    elif scale == 'log':
        try:
            axis['tick0'] = props['axes'][1]['tickvalues'][0]
            axis['dtick'] = props['axes'][1]['tickvalues'][1] - \
                            props['axes'][1]['tickvalues'][0]
            axis['autotick'] = False
        except (IndexError, TypeError):
            axis = dict(nticks=props['axes'][1]['nticks'])
        base = ax.get_yaxis().get_transform().base
        if base == 10:
            axis['range'] = [math.log10(props['ylim'][0]),
                             math.log10(props['ylim'][1])]
        else:
            axis = dict(range=None, type='linear')
            warnings.warn("Converted non-base10 y-axis log scale to 'linear'")
        return axis
    else:
        return dict()


def prep_xy_axis(ax, props, x_bounds, y_bounds):
    xaxis = dict(
        type=props['axes'][0]['scale'],
        range=list(props['xlim']),
        showgrid=props['axes'][0]['grid']['gridOn'],
        domain=convert_x_domain(props['bounds'], x_bounds),
        side=props['axes'][0]['position'],
        tickfont=dict(size=props['axes'][0]['fontsize'])
    )
    xaxis.update(prep_x_ticks(ax, props))
    yaxis = dict(
        type=props['axes'][1]['scale'],
        range=list(props['ylim']),
        showgrid=props['axes'][1]['grid']['gridOn'],
        domain=convert_y_domain(props['bounds'], y_bounds),
        side=props['axes'][1]['position'],
        tickfont=dict(size=props['axes'][1]['fontsize'])
    )
    yaxis.update(prep_y_ticks(ax, props))
    return xaxis, yaxis


DASH_MAP = {
    '10,0': 'solid',
    '6,6': 'dash',
    '2,2': 'dot',
    '4,4,2,4': 'dashdot',
    'none': 'solid'
}

PATH_MAP = {
    ('M', 'C', 'C', 'C', 'C', 'C', 'C', 'C', 'C', 'Z'): 'o',
    ('M', 'L', 'L', 'L', 'L', 'L', 'L', 'L', 'L', 'L', 'Z'): '*',
    ('M', 'L', 'L', 'L', 'L', 'L', 'L', 'L', 'Z'): '8',
    ('M', 'L', 'L', 'L', 'L', 'L', 'Z'): 'h',
    ('M', 'L', 'L', 'L', 'L', 'Z'): 'p',
    ('M', 'L', 'M', 'L', 'M', 'L'): '1',
    ('M', 'L', 'L', 'L', 'Z'): 's',
    ('M', 'L', 'M', 'L'): '+',
    ('M', 'L', 'L', 'Z'): '^',
    ('M', 'L'): '|'
}

SYMBOL_MAP = {
    'o': 'dot',
    'v': 'triangle-down',
    '^': 'triangle-up',
    '<': 'triangle-left',
    '>': 'triangle-right',
    's': 'square',
    '+': 'cross',
    'x': 'x',
    '*': 'x',  # no star yet in plotly!!
    'D': 'diamond',
    'd': 'diamond',
}

VA_MAP = {
    'center': 'middle',
    'baseline': 'bottom',
    'top': 'top'
}

########NEW FILE########
__FILENAME__ = renderer
"""
Renderer Module

This module defines the PlotlyRenderer class and a single function,
fig_to_plotly, which is intended to be the main way that user's will interact
with the matplotlylib package.

"""
import warnings
from . mplexporter import Exporter, Renderer
from . import mpltools
from .. graph_objs import *


class PlotlyRenderer(Renderer):
    """A renderer class inheriting from base for rendering mpl plots in plotly.

    A renderer class to be used with an exporter for rendering matplotlib
    plots in Plotly. This module defines the PlotlyRenderer class which handles
    the creation of the JSON structures that get sent to plotly.

    All class attributes available are defined in __init__().

    Basic Usage:

    # (mpl code) #
    fig = gcf()
    renderer = PlotlyRenderer(fig)
    exporter = Exporter(renderer)
    exporter.run(fig)  # ... et voila

    """
    def __init__(self):
        """Initialize PlotlyRenderer obj.

        PlotlyRenderer obj is called on by an Exporter object to draw
        matplotlib objects like figures, axes, text, etc.

        All class attributes are listed here in the __init__ method.

        """
        self.plotly_fig = Figure(data=Data(), layout=Layout())
        self.mpl_fig = None
        self.current_ax_patches = []
        self.axis_ct = 0
        self.mpl_x_bounds = (0, 1)
        self.mpl_y_bounds = (0, 1)
        self.msg = "Initialized PlotlyRenderer\n"

    def open_figure(self, fig, props):
        """Creates a new figure by beginning to fill out layout dict.

        The 'autosize' key is set to false so that the figure will mirror
        sizes set by mpl. The 'hovermode' key controls what shows up when you
        mouse around a figure in plotly, it's set to show the 'closest' point.

        Positional agurments:
        fig -- a matplotlib.figure.Figure object.
        props.keys(): [
            'figwidth',
            'figheight',
            'dpi'
            ]

        """
        self.msg += "Opening figure\n"
        self.mpl_fig = fig
        self.plotly_fig['layout'] = Layout(
            width=int(props['figwidth']*props['dpi']),
            height=int(props['figheight']*props['dpi']),
            autosize=False,
            hovermode='closest')
        self.mpl_x_bounds, self.mpl_y_bounds = mpltools.get_axes_bounds(fig)
        margin = Margin(
            l=int(self.mpl_x_bounds[0]*self.plotly_fig['layout']['width']),
            r=int((1-self.mpl_x_bounds[1])*self.plotly_fig['layout']['width']),
            t=int((1-self.mpl_y_bounds[1])*self.plotly_fig['layout']['height']),
            b=int(self.mpl_y_bounds[0]*self.plotly_fig['layout']['height']),
            pad=0)
        self.plotly_fig['layout']['margin'] = margin

    def close_figure(self, fig):
        """Closes figure by cleaning up data and layout dictionaries.

        The PlotlyRenderer's job is to create an appropriate set of data and
        layout dictionaries. When the figure is closed, some cleanup and
        repair is necessary. This method removes inappropriate dictionary
        entries, freeing up Plotly to use defaults and best judgements to
        complete the entries. This method is called by an Exporter object.

        Positional arguments:
        fig -- a matplotlib.figure.Figure object.

        """
        self.plotly_fig.force_clean()
        self.plotly_fig['layout']['showlegend'] = False
        self.msg += "Closing figure\n"

    def open_axes(self, ax, props):
        """Setup a new axes object (subplot in plotly).

        Plotly stores information about subplots in different 'xaxis' and
        'yaxis' objects which are numbered. These are just dictionaries
        included in the layout dictionary. This function takes information
        from the Exporter, fills in appropriate dictionary entries,
        and updates the layout dictionary. PlotlyRenderer keeps track of the
        number of plots by incrementing the axis_ct attribute.

        Setting the proper plot domain in plotly is a bit tricky. Refer to
        the documentation for mpltools.convert_x_domain and
        mpltools.convert_y_domain.

        Positional arguments:
        ax -- an mpl axes object. This will become a subplot in plotly.
        props.keys() -- [
            'axesbg',           (background color for axes obj)
            'axesbgalpha',      (alpha, or opacity for background)
            'bounds',           ((x0, y0, width, height) for axes)
            'dynamic',          (zoom/pan-able?)
            'axes',             (list: [xaxis, yaxis])
            'xscale',           (log, linear, or date)
            'yscale',
            'xlim',             (range limits for x)
            'ylim',
            'xdomain'           (xdomain=xlim, unless it's a date)
            'ydomain'
            ]

        """
        self.msg += "  Opening axes\n"
        self.axis_ct += 1
        # set defaults in axes
        xaxis = XAxis(
            anchor='y{}'.format(self.axis_ct),
            zeroline=False,
            showline=True,
            mirror='ticks',
            ticks='inside')
        yaxis = YAxis(
            anchor='x{}'.format(self.axis_ct),
            zeroline=False,
            showline=True,
            mirror='ticks',
            ticks='inside')
        # update defaults with things set in mpl
        mpl_xaxis, mpl_yaxis = mpltools.prep_xy_axis(ax=ax,
                                                     props=props,
                                                     x_bounds=self.mpl_x_bounds,
                                                     y_bounds=self.mpl_y_bounds)
        xaxis.update(mpl_xaxis)
        yaxis.update(mpl_yaxis)
        # put axes in our figure
        self.plotly_fig['layout']['xaxis{}'.format(self.axis_ct)] = xaxis
        self.plotly_fig['layout']['yaxis{}'.format(self.axis_ct)] = yaxis

    def close_axes(self, ax):
        """Close the axes object and clean up.

        Bars from bar charts are given to PlotlyRenderer one-by-one,
        thus they need to be taken care of at the close of each axes object.
        The self.current_ax_patches variable should be empty unless a bar
        chart has been created or a rectangle object has been drawn that has
        an edge exactly on the lines x=0 or y=0.

        Positional arguments:
        ax -- an mpl axes object, not required at this time.

        """
        for patch_coll in self.current_ax_patches:
            self.draw_bar(patch_coll)
        self.current_ax_patches = []  # clear this for next axes obj
        self.msg += "  Closing axes\n"

    def draw_bar(self, patch_coll):
        """Draw a collection of similar patches as a bar chart.

        After bars are sorted, an appropriate data dictionary must be created
        to tell plotly about this data. Just like draw_line or draw_markers,
        draw_bar translates patch/path information into something plotly
        understands.

        Positional arguments:
        patch_coll -- a collection of patches to be drawn as a bar chart.

        """
        orientation = patch_coll[0]['orientation']
        if orientation == 'v':
            self.msg += "    Attempting to draw a vertical bar chart\n"
            patch_coll.sort(key=lambda b: b['x0'])
            x = [bar['x0']+(bar['x1']-bar['x0'])/2 for bar in patch_coll]
            y = [bar['y1'] for bar in patch_coll]
        else:
            self.msg += "    Attempting to draw a horizontal bar chart\n"
            patch_coll.sort(key=lambda b: b['y0'])
            x = [bar['x1'] for bar in patch_coll]
            y = [bar['y0']+(bar['y1']-bar['y0'])/2 for bar in patch_coll]
        bar = Bar(orientation=orientation,
                  x=x,
                  y=y,
                  xaxis='x{}'.format(self.axis_ct),
                  yaxis='y{}'.format(self.axis_ct),
                  opacity=patch_coll[0]['alpha'],
                  marker=Marker(
                      color=patch_coll[0]['facecolor'],
                      line=Line(width=patch_coll[0]['edgewidth'])))
        if len(bar['x']) > 1:
            self.msg += "    Heck yeah, I drew that bar chart\n"
            self.plotly_fig['data'] += bar,
        else:
            self.msg += "    Bar chart not drawn\n"
            warnings.warn('found box chart data with length <= 1, '
                          'assuming data redundancy, not plotting.')

    def draw_marked_line(self, **props):
        """Create a data dict for a line obj.

        This will draw 'lines', 'markers', or 'lines+markers'.

        props.keys() -- [
        'coordinates',  ('data', 'axes', 'figure', or 'display')
        'data',         (a list of xy pairs)
        'mplobj',       (the matplotlib.lines.Line2D obj being rendered)
        'label',        (the name of the Line2D obj being rendered)
        'linestyle',    (linestyle dict, can be None, see below)
        'markerstyle',  (markerstyle dict, can be None, see below)
        ]

        props['linestyle'].keys() -- [
        'alpha',        (opacity of Line2D obj)
        'color',        (color of the line if it exists, not the marker)
        'linewidth',
        'dasharray',    (code for linestyle, see DASH_MAP in mpltools.py)
        'zorder',       (viewing precedence when stacked with other objects)
        ]

        props['markerstyle'].keys() -- [
        'alpha',        (opacity of Line2D obj)
        'marker',       (the mpl marker symbol, see SYMBOL_MAP in mpltools.py)
        'facecolor',    (color of the marker face)
        'edgecolor',    (color of the marker edge)
        'edgewidth',    (width of marker edge)
        'markerpath',   (an SVG path for drawing the specified marker)
        'zorder',       (viewing precedence when stacked with other objects)
        ]

        """
        self.msg += "    Attempting to draw a line "
        line, marker = {}, {}
        if props['linestyle'] and props['markerstyle']:
            self.msg += "... with both lines+markers\n"
            mode = "lines+markers"
        elif props['linestyle']:
            self.msg += "... with just lines\n"
            mode = "lines"
        elif props['markerstyle']:
            self.msg += "... with just markers\n"
            mode = "markers"
        if props['linestyle']:
            line = Line(
                opacity=props['linestyle']['alpha'],
                color=props['linestyle']['color'],
                width=props['linestyle']['linewidth'],
                dash=mpltools.convert_dash(props['linestyle']['dasharray'])
            )
        if props['markerstyle']:
            marker = Marker(
                opacity=props['markerstyle']['alpha'],
                color=props['markerstyle']['facecolor'],
                symbol=mpltools.convert_symbol(props['markerstyle']['marker']),
                size=props['markerstyle']['markersize'],
                line=Line(
                    color=props['markerstyle']['edgecolor'],
                    width=props['markerstyle']['edgewidth']
                )
            )
        if props['coordinates'] == 'data':
            marked_line = Scatter(mode=mode,
                                  name=props['label'],
                                  x=[xy_pair[0] for xy_pair in props['data']],
                                  y=[xy_pair[1] for xy_pair in props['data']],
                                  xaxis='x{}'.format(self.axis_ct),
                                  yaxis='y{}'.format(self.axis_ct),
                                  line=line,
                                  marker=marker)
            self.plotly_fig['data'] += marked_line,
            self.msg += "    Heck yeah, I drew that line\n"
        else:
            self.msg += "    Line didn't have 'data' coordinates, " \
                        "not drawing\n"
            warnings.warn("Bummer! Plotly can currently only draw Line2D "
                          "objects from matplotlib that are in 'data' "
                          "coordinates!")

    def draw_image(self, **props):
        """Draw image.

        Not implemented yet!

        """
        self.msg += "    Attempting to draw image\n"
        self.msg += "    Not drawing image\n"
        warnings.warn("Aw. Snap! You're gonna have to hold off on "
                      "the selfies for now. Plotly can't import "
                      "images from matplotlib yet!")

    def draw_path_collection(self, **props):
        """Add a path collection to data list as a scatter plot.

        Current implementation defaults such collections as scatter plots.
        Matplotlib supports collections that have many of the same parameters
        in common like color, size, path, etc. However, they needn't all be
        the same. Plotly does not currently support such functionality and
        therefore, the style for the first object is taken and used to define
        the remaining paths in the collection.

        props.keys() -- [
        'paths',                (structure: [vertices, path_code])
        'path_coordinates',     ('data', 'axes', 'figure', or 'display')
        'path_transforms',      (mpl transform, including Affine2D matrix)
        'offsets',              (offset from axes, helpful if in 'data')
        'offset_coordinates',   ('data', 'axes', 'figure', or 'display')
        'offset_order',
        'styles',               (style dict, see below)
        'mplobj'                (the collection obj being drawn)
        ]

        props['styles'].keys() -- [
        'linewidth',            (one or more linewidths)
        'facecolor',            (one or more facecolors for path)
        'edgecolor',            (one or more edgecolors for path)
        'alpha',                (one or more opacites for path)
        'zorder',               (precedence when stacked)
        ]

        """
        self.msg += "    Attempting to draw a path collection\n"
        if props['offset_coordinates'] is 'data':
            alpha_face = props['styles']['facecolor'][0][3]
            rgb_face = [int(c*255)
                        for c in props['styles']['facecolor'][0][:3]]
            alpha_edge = props['styles']['edgecolor'][0][3]
            rgb_edge = [int(c*255)
                        for c in props['styles']['edgecolor'][0][:3]]
            data = props['offsets']
            marker = mpltools.convert_path(props['paths'][0])
            style = {
                'alpha': alpha_face,
                'facecolor': 'rgb({},{},{})'.format(*rgb_face),
                'marker': marker,
                'edgecolor': 'rgb({},{},{})'.format(*rgb_edge),
                'edgewidth': props['styles']['linewidth'][0],
                'markersize': mpltools.convert_affine_trans(
                    dpi=self.mpl_fig.get_dpi(),
                    aff=props['path_transforms'][0])
            }
            scatter_props = {
                'coordinates': 'data',
                'data': data,
                'label': None,
                'markerstyle': style,
                'linestyle': None
            }
            self.msg += "    Drawing path collection as markers\n"
            self.draw_marked_line(**scatter_props)
        else:
            self.msg += "    Path collection not linked to 'data', " \
                        "not drawing\n"
            warnings.warn("Dang! That path collection is out of this "
                          "world. I totally don't know what to do with "
                          "it yet! Plotly can only import path "
                          "collections linked to 'data' coordinates")

    def draw_path(self, **props):
        """Draw path, currently only attempts to draw bar charts.

        This function attempts to sort a given path into a collection of
        horizontal or vertical bar charts. Most of the actual code takes
        place in functions from mpltools.py.

        props.keys() -- [
        'data',         (a list of verticies for the path)
        'coordinates',  ('data', 'axes', 'figure', or 'display')
        'pathcodes',    (code for the path, structure: ['M', 'L', 'Z', etc.])
        'style',        (style dict, see below)
        'mplobj'        (the mpl path object)
        ]

        props['style'].keys() -- [
        'alpha',        (opacity of path obj)
        'edgecolor',
        'facecolor',
        'edgewidth',
        'dasharray',    (style for path's enclosing line)
        'zorder'        (precedence of obj when stacked)
        ]

        """
        self.msg += "    Attempting to draw a path\n"
        is_bar = mpltools.is_bar(**props)
        is_barh = mpltools.is_barh(**props)
        if is_bar:  # if we think it's a bar, add it!
            self.msg += "      Assuming path is a vertical bar\n"
            bar = mpltools.make_bar(orientation='v', **props)
            self.file_bar(bar)
        if is_barh:  # perhaps a horizontal bar?
            self.msg += "      Assuming path is a horizontal bar\n"
            bar = mpltools.make_bar(orientation='h', **props)
            self.file_bar(bar)
        if not (is_bar or is_barh):
            self.msg += "    This path isn't a bar, not drawing\n"
            warnings.warn("I found a path object that I don't think is part "
                          "of a bar chart. Ignoring.")

    def file_bar(self, bar):
        """Puts a given bar into an appropriate bar or barh collection.

        Bars come from the mplexporter one-by-one. To try to put them into
        appropriate data sets, we must compare them to existing data.

        Positional arguments:
        bar -- a bar dictionary created in mpltools.make_bar.py.

        bar.keys() -- [
        'bar',          (mpl path object)
        'orientation',  (bar direction, 'v' or 'h' for horizontal or vertical)
        'x0',           ([x0, y0] = bottom-left corner of rectangle)
        'y0',
        'x1',           ([x1, y1] = top-right corner of rectangle):
        'y1',
        'alpha',        (opacity of rectangle)
        'edgecolor',    (boundary line color)
        'facecolor',    (rectangle color)
        'edgewidth',    (boundary line width)
        'dasharray',    (linestyle for boundary line)
        'zorder',       (precedence when stacked)
        ]

        """
        self.msg += "        Putting a bar into the proper bar collection\n"
        if len(self.current_ax_patches) == 0:
            self.msg += "          Started a new bar collection with this " \
                        "bar\n"
            self.current_ax_patches.append([])
            self.current_ax_patches[-1] += bar,
        else:
            match = False
            for patch_collection in self.current_ax_patches:
                if mpltools.check_bar_match(patch_collection[0], bar):
                    match = True
                    patch_collection += bar,
                    self.msg += "          Filed bar into existing bar " \
                                "collection\n"
            if not match:
                self.msg += "          Started a new bar collection with " \
                            "this bar\n"
                self.current_ax_patches.append([])
                self.current_ax_patches[-1] += bar,

    def draw_text(self, **props):
        """Create an annotation dict for a text obj.

        Currently, plotly uses either 'page' or 'data' to reference
        annotation locations. These refer to 'display' and 'data',
        respectively for the 'coordinates' key used in the Exporter.
        Appropriate measures are taken to transform text locations to
        reference one of these two options.

        props.keys() -- [
        'text',         (actual content string, not the text obj)
        'position',     (an x, y pair, not an mpl Bbox)
        'coordinates',  ('data', 'axes', 'figure', 'display')
        'text_type',    ('title', 'xlabel', or 'ylabel')
        'style',        (style dict, see below)
        'mplobj'        (actual mpl text object)
        ]

        props['style'].keys() -- [
        'alpha',        (opacity of text)
        'fontsize',     (size in points of text)
        'color',        (hex color)
        'halign',       (horizontal alignment, 'left', 'center', or 'right')
        'valign',       (vertical alignment, 'baseline', 'center', or 'top')
        'rotation',
        'zorder',       (precedence of text when stacked with other objs)
        ]

        """
        self.msg += "    Attempting to draw an mpl text object\n"
        if 'annotations' not in self.plotly_fig['layout']:
            self.plotly_fig['layout']['annotations'] = Annotations()
        if props['text_type'] == 'xlabel':
            self.msg += "      Text object is an xlabel\n"
            self.draw_xlabel(**props)
        elif props['text_type'] == 'ylabel':
            self.msg += "      Text object is a ylabel\n"
            self.draw_ylabel(**props)
        elif props['text_type'] == 'title':
            self.msg += "      Text object is a title\n"
            self.draw_title(**props)
        else:  # just a regular text annotation...
            self.msg += "      Text object is a normal annotation\n"
            if props['coordinates'] is not 'data':
                self.msg += "        Text object isn't linked to 'data' " \
                            "coordinates\n"
                x_px, y_px = props['mplobj'].get_transform().transform(
                    props['position'])
                x, y = mpltools.display_to_paper(x_px, y_px,
                                              self.plotly_fig['layout'])
                xref = 'paper'
                yref = 'paper'
                xanchor = props['style']['halign']  # no difference here!
                yanchor = mpltools.convert_va(props['style']['valign'])
            else:
                self.msg += "        Text object is linked to 'data' " \
                            "coordinates\n"
                x, y = props['position']
                xref = 'x{}'.format(self.axis_ct)
                yref = 'y{}'.format(self.axis_ct)
                xanchor = 'center'
                yanchor = 'middle'
            annotation = Annotation(
                text=props['text'],
                opacity=props['style']['alpha'],
                x=x,
                y=y,
                xref=xref,
                yref=yref,
                xanchor=xanchor,
                yanchor=yanchor,
                showarrow=False,  # change this later?
                font=Font(
                    color=props['style']['color'],
                    size=props['style']['fontsize']
                )
            )
            self.plotly_fig['layout']['annotations'] += annotation,
            self.msg += "    Heck, yeah I drew that annotation\n"

    def draw_title(self, **props):
        """Add a title to the current subplot in layout dictionary.

        If there exists more than a single plot in the figure, titles revert
        to 'page'-referenced annotations.

        props.keys() -- [
        'text',         (actual content string, not the text obj)
        'position',     (an x, y pair, not an mpl Bbox)
        'coordinates',  ('data', 'axes', 'figure', 'display')
        'text_type',    ('title', 'xlabel', or 'ylabel')
        'style',        (style dict, see below)
        'mplobj'        (actual mpl text object)
        ]

        props['style'].keys() -- [
        'alpha',        (opacity of text)
        'fontsize',     (size in points of text)
        'color',        (hex color)
        'halign',       (horizontal alignment, 'left', 'center', or 'right')
        'valign',       (vertical alignment, 'baseline', 'center', or 'top')
        'rotation',
        'zorder',       (precedence of text when stacked with other objs)
        ]

        """
        self.msg += "        Attempting to draw a title\n"
        if len(self.mpl_fig.axes) > 1:
            self.msg += "          More than one subplot, adding title as " \
                        "annotation\n"
            x_px, y_px = props['mplobj'].get_transform().transform(props[
                'position'])
            x, y = mpltools.display_to_paper(x_px, y_px,
                                             self.plotly_fig['layout'])
            annotation = Annotation(
                text=props['text'],
                font=Font(color=props['style']['color'],
                         size=props['style']['fontsize']
                ),
                xref='paper',
                yref='paper',
                x=x,
                y=y,
                xanchor='center',
                yanchor='bottom',
                showarrow=False  # no arrow for a title!
            )
            self.plotly_fig['layout']['annotations'] += annotation,
        else:
            self.msg += "          Only one subplot found, adding as a " \
                        "plotly title\n"
            self.plotly_fig['layout']['title'] = props['text']
            titlefont = Font(size=props['style']['fontsize'],
                             color=props['style']['color']
            )
            self.plotly_fig['layout']['titlefont'] = titlefont

    def draw_xlabel(self, **props):
        """Add an xaxis label to the current subplot in layout dictionary.

        props.keys() -- [
        'text',         (actual content string, not the text obj)
        'position',     (an x, y pair, not an mpl Bbox)
        'coordinates',  ('data', 'axes', 'figure', 'display')
        'text_type',    ('title', 'xlabel', or 'ylabel')
        'style',        (style dict, see below)
        'mplobj'        (actual mpl text object)
        ]

        props['style'].keys() -- [
        'alpha',        (opacity of text)
        'fontsize',     (size in points of text)
        'color',        (hex color)
        'halign',       (horizontal alignment, 'left', 'center', or 'right')
        'valign',       (vertical alignment, 'baseline', 'center', or 'top')
        'rotation',
        'zorder',       (precedence of text when stacked with other objs)
        ]

        """
        self.msg += "        Adding xlabel\n"
        axis_key = 'xaxis{}'.format(self.axis_ct)
        self.plotly_fig['layout'][axis_key]['title'] = props['text']
        titlefont = Font(size=props['style']['fontsize'],
                         color=props['style']['color'])
        self.plotly_fig['layout'][axis_key]['titlefont'] = titlefont

    def draw_ylabel(self, **props):
        """Add a yaxis label to the current subplot in layout dictionary.

        props.keys() -- [
        'text',         (actual content string, not the text obj)
        'position',     (an x, y pair, not an mpl Bbox)
        'coordinates',  ('data', 'axes', 'figure', 'display')
        'text_type',    ('title', 'xlabel', or 'ylabel')
        'style',        (style dict, see below)
        'mplobj'        (actual mpl text object)
        ]

        props['style'].keys() -- [
        'alpha',        (opacity of text)
        'fontsize',     (size in points of text)
        'color',        (hex color)
        'halign',       (horizontal alignment, 'left', 'center', or 'right')
        'valign',       (vertical alignment, 'baseline', 'center', or 'top')
        'rotation',
        'zorder',       (precedence of text when stacked with other objs)
        ]

        """
        self.msg += "        Adding ylabel\n"
        axis_key = 'yaxis{}'.format(self.axis_ct)
        self.plotly_fig['layout'][axis_key]['title'] = props['text']
        titlefont = Font(size=props['style']['fontsize'],
                         color=props['style']['color'])
        self.plotly_fig['layout'][axis_key]['titlefont'] = titlefont

    def resize(self):
        """Revert figure layout to allow plotly to resize.

        By default, PlotlyRenderer tries its hardest to precisely mimic an
        mpl figure. However, plotly is pretty good with aesthetics. By
        running PlotlyRenderer.resize(), layout parameters are deleted. This
        lets plotly choose them instead of mpl.

        """
        self.msg += "Resizing figure, deleting keys from layout\n"
        for key in ['width', 'height', 'autosize', 'margin']:
            try:
                del self.plotly_fig['layout'][key]
            except KeyError:
                pass

    def strip_style(self):
        self.msg += "Stripping mpl style, deleting keys from data and layout\n"
        self.plotly_fig.strip_style()

########NEW FILE########
__FILENAME__ = chunked_request
import time
import httplib
import StringIO


class Stream:
    def __init__(self, server, port=80, headers={}):
        ''' Initialize a stream object and an HTTP Connection
        with chunked Transfer-Encoding to server:port with optional headers.
        '''
        self.maxtries = 5
        self._tries = 0
        self._delay = 1
        self._closed = False
        self._server = server
        self._port = port
        self._headers = headers
        self._connect()

    def write(self, data, reconnect_on=('', 200, )):
        ''' Send `data` to the server in chunk-encoded form.
        Check the connection before writing and reconnect
        if disconnected and if the response status code is in `reconnect_on`.

        The response may either be an HTTPResponse object or an empty string.
        '''

        if not self._isconnected():

            # Attempt to get the response.
            response = self._getresponse()

            # Reconnect depending on the status code.
            if ((response == '' and '' in reconnect_on) or
                (response and isinstance(response, httplib.HTTPResponse) and
                 response.status in reconnect_on)):
                self._reconnect()

            elif response and isinstance(response, httplib.HTTPResponse):
                # If an HTTPResponse was recieved then
                # make the users aware instead of
                # auto-reconnecting in case the
                # server is responding with an important
                # message that might prevent
                # future requests from going through,
                # like Invalid Credentials.
                # This allows the user to determine when
                # to reconnect.
                raise Exception("Server responded with "
                                "status code: {status_code}\n"
                                "and message: {msg}."
                                .format(status_code=response.status,
                                        msg=response.read()))

            elif response == '':
                raise Exception("Attempted to write but socket "
                                "was not connected.")

        try:
            msg = data
            msglen = format(len(msg), 'x')  # msg length in hex
            # Send the message in chunk-encoded form
            self._conn.send('{msglen}\r\n{msg}\r\n'
                            .format(msglen=msglen, msg=msg))
        except httplib.socket.error:
            self._reconnect()
            self.write(data)

    def _connect(self):
        ''' Initialize an HTTP connection with chunked Transfer-Encoding
        to server:port with optional headers.
        '''
        server = self._server
        port = self._port
        headers = self._headers
        self._conn = httplib.HTTPConnection(server, port)

        self._conn.putrequest('POST', '/')
        self._conn.putheader('Transfer-Encoding', 'chunked')
        for header in headers:
            self._conn.putheader(header, headers[header])
        self._conn.endheaders()

        # Set blocking to False prevents recv
        # from blocking while waiting for a response.
        self._conn.sock.setblocking(False)
        self._bytes = ''
        self._reset_retries()
        time.sleep(0.5)

    def close(self):
        ''' Close the connection to server.

        If available, return a httplib.HTTPResponse object.

        Closing the connection involves sending the
        Transfer-Encoding terminating bytes.
        '''
        self._reset_retries()
        self._closed = True

        # Chunked-encoded posts are terminated with '0\r\n\r\n'
        # For some reason, either Python or node.js seems to
        # require an extra \r\n.
        try:
            self._conn.send('\r\n0\r\n\r\n')
        except httplib.socket.error:
            # In case the socket has already been closed
            return ''

        return self._getresponse()

    def _getresponse(self):
        ''' Read from recv and return a HTTPResponse object if possible.
        Either
        1 - The client has succesfully closed the connection: Return ''
        2 - The server has already closed the connection: Return the response
            if possible.
        '''
        # Wait for a response
        self._conn.sock.setblocking(True)
        # Parse the response
        response = self._bytes
        while True:
            try:
                bytes = self._conn.sock.recv(1)
            except httplib.socket.error:
                # For error 54: Connection reset by peer
                # (and perhaps others)
                return ''
            if bytes == '':
                break
            else:
                response += bytes
        # Set recv to be non-blocking again
        self._conn.sock.setblocking(False)

        # Convert the response string to a httplib.HTTPResponse
        # object with a bit of a hack
        if response != '':
            # Taken from
            # http://pythonwise.blogspot.ca/2010/02/parse-http-response.html
            try:
                response = httplib.HTTPResponse(_FakeSocket(response))
                response.begin()
            except:
                # Bad headers ... etc.
                response = ''
        return response

    def _isconnected(self):
        ''' Return True if the socket is still connected
        to the server, False otherwise.

        This check is done in 3 steps:
        1 - Check if we have closed the connection
        2 - Check if the original socket connection failed
        3 - Check if the server has returned any data. If they have,
            assume that the server closed the response after they sent
            the data, i.e. that the data was the HTTP response.
        '''

        # 1 - check if we've closed the connection.
        if self._closed:
            return False

        # 2 - Check if the original socket connection failed
        # If this failed, then no socket was initialized
        if self._conn.sock is None:
            return False

        try:
            # 3 - Check if the server has returned any data.
            # If they have, then start to store the response
            # in _bytes.
            self._bytes = ''
            self._bytes = self._conn.sock.recv(1)
            return False
        except httplib.socket.error as e:
            # Check why recv failed
            # Windows machines are the error codes
            # that start with 1
            # (http://msdn.microsoft.com/en-ca/library/windows/desktop/ms740668(v=vs.85).aspx)
            if e.errno == 35 or e.errno == 10035:
                # This is the "Resource temporarily unavailable" error
                # which is thrown cuz there was nothing to receive, i.e.
                # the server hasn't returned a response yet.
                # This is a non-fatal error and the operation
                # should be tried again.
                # So, assume that the connection is still open.
                return True
            elif e.errno == 54 or e.errno == 10054:
                # This is the "Connection reset by peer" error
                # which is thrown cuz the server reset the
                # socket, so the connection is closed.
                return False
            elif e.errno == 11:
                # This is the "Resource temporarily unavailable" error
                # which happens because the "operation would have blocked
                # but nonblocking operation was requested".
                # We require non-blocking reading of this socket because
                # we don't want to wait around for a response, we just
                # want to see if a response is currently available. So
                # let's just assume that we're still connected and
                # hopefully recieve some data on the next try.
                return True
            else:
                # Unknown scenario
                raise e

    def _reconnect(self):
        ''' Connect if disconnected.
        Retry self.maxtries times with delays
        '''
        if not self._isconnected():
            try:
                self._connect()
            except httplib.socket.error as e:
                # Attempt to reconnect if the connection was refused
                if e.errno == 61 or e.errno == 10061:
                    # errno 61 is the "Connection Refused" error
                    time.sleep(self._delay)
                    self._delay += self._delay  # fibonacii delays
                    self._tries += 1
                    if self._tries < self.maxtries:
                        self._reconnect()
                    else:
                        self._reset_retries()
                        raise e
                else:
                    # Unknown scenario
                    raise e

        # Reconnect worked - reset _closed
        self._closed = False

    def _reset_retries(self):
        ''' Reset the connect counters and delays
        '''
        self._tries = 0
        self._delay = 1


class _FakeSocket(StringIO.StringIO):
    # Used to construct a httplib.HTTPResponse object
    # from a string.
    # Thx to: http://pythonwise.blogspot.ca/2010/02/parse-http-response.html
    def makefile(self, *args, **kwargs):
        return self

########NEW FILE########
__FILENAME__ = plotly
"""
plotly
======

A module that contains the plotly class, a liaison between the user
and ploty's servers.

1. get DEFAULT_PLOT_OPTIONS for options

2. update plot_options with .plotly/ dir

3. update plot_options with _plot_options

4. update plot_options with kwargs!

"""
import requests
import chunked_requests
import json
import warnings
import httplib
import copy
import base64
import os
from .. import utils
from .. import tools
from .. import exceptions
from .. import version

__all__ = ["sign_in", "update_plot_options", "get_plot_options",
           "get_credentials", "iplot", "plot", "iplot_mpl", "plot_mpl",
           "get_figure", "Stream", "image"]

_DEFAULT_PLOT_OPTIONS = dict(
    filename="plot from API",
    fileopt="new",
    world_readable=True,
    auto_open=True,
    validate=True)

_credentials = dict()

_plot_options = dict()

_plotly_url = "https://plot.ly"  #  do not append final '/' here for url!

### _credentials stuff ###

def sign_in(username, api_key):
    """Set module-scoped _credentials for session. Verify with plotly."""
    global _credentials
    _credentials['username'], _credentials['api_key'] = username, api_key
    # TODO: verify these _credentials with plotly


### _plot_options stuff ###

# def load_plot_options():
#     """ Import the plot_options from file into the module-level _plot_options.
#     """
#     global _plot_options
#     _plot_options = _plot_options.update(tools.get_plot_options_file())
#
#
# def save_plot_options(**kwargs):
#     """ Save the module-level _plot_options to file for later access
#     """
#     global _plot_options
#     update_plot_options(**kwargs)
#     tools.save_plot_options_file(**_plot_options)


def update_plot_options(**kwargs):
    """ Update the module-level _plot_options
    """
    global _plot_options
    _plot_options.update(kwargs)


def get_plot_options():
    """ Returns a copy of the user supplied plot options.
    Use `update_plot_options()` to change.
    """
    global _plot_options
    return copy.copy(_plot_options)


def get_credentials():
    """ Returns a copy of the user supplied credentials.
    """
    global _credentials
    if ('username' in _credentials) and ('api_key' in _credentials):
        return copy.copy(_credentials)
    else:
        return tools.get_credentials_file()


### plot stuff ###

def iplot(figure_or_data, **plot_options):
    """Create a unique url for this plot in Plotly and open in IPython.

    plot_options keyword agruments:
    filename (string) -- the name that will be associated with this figure
    fileopt ('new' | 'overwrite' | 'extend' | 'append') -- 'new' creates a
        'new': create a new, unique url for this plot
        'overwrite': overwrite the file associated with `filename` with this
        'extend': add additional numbers (data) to existing traces
        'append': add additional traces to existing data lists
    world_readable (default=True) -- make this figure private/public

    """
    if 'auto_open' not in plot_options:
        plot_options['auto_open'] = False
    res = plot(figure_or_data, **plot_options)
    urlsplit = res.split('/')
    username, plot_id = urlsplit[-2][1:], urlsplit[-1]  # TODO: HACKY!

    embed_options = dict()
    if 'width' in plot_options:
        embed_options['width'] = plot_options['width']
    if 'height' in plot_options:
        embed_options['height'] = plot_options['height']

    return tools.embed(username, plot_id, **embed_options)


def _plot_option_logic(plot_options):
    """Sets plot_options via a precedence hierarchy."""
    options = dict()
    options.update(_DEFAULT_PLOT_OPTIONS)
    options.update(_plot_options)
    options.update(plot_options)
    if ('filename' in plot_options
       and 'fileopt' not in _plot_options
       and 'fileopt' not in plot_options):
        options['fileopt'] = 'overwrite'
    return options


def plot(figure_or_data, validate=True, **plot_options):
    """Create a unique url for this plot in Plotly and optionally open url.

    plot_options keyword agruments:
    filename (string) -- the name that will be associated with this figure
    fileopt ('new' | 'overwrite' | 'extend' | 'append') -- 'new' creates a
        'new': create a new, unique url for this plot
        'overwrite': overwrite the file associated with `filename` with this
        'extend': add additional numbers (data) to existing traces
        'append': add additional traces to existing data lists
    world_readable (default=True) -- make this figure private/public
    auto_open (default=True) -- Toggle browser options
        True: open this plot in a new browser tab
        False: do not open plot in the browser, but do return the unique url

    """
    if isinstance(figure_or_data, dict):
        figure = figure_or_data
    elif isinstance(figure_or_data, list):
        figure = {'data': figure_or_data}
    else:
        raise exceptions.PlotlyError("The `figure_or_data` positional argument "
                                     "must be either `dict`-like or "
                                     "`list`-like.")
    if validate:
        try:
            tools.validate(figure, obj_type='Figure')
        except exceptions.PlotlyError as err:
            raise exceptions.PlotlyError("Invalid 'figure_or_data' argument. "
                                         "Plotly will not be able to properly "
                                         "parse the resulting JSON. If you "
                                         "want to send this 'figure_or_data' "
                                         "to Plotly anyway (not recommended), "
                                         "you can set 'validate=False' as a "
                                         "plot option.\nHere's why you're "
                                         "seeing this error:\n\n{}".format(err))
    for entry in figure['data']:
        for key, val in entry.items():
            try:
                if len(val) > 40000:
                    msg = ("Woah there! Look at all those points! Due to "
                           "browser limitations, Plotly has a hard time "
                           "graphing more than 500k data points for line "
                           "charts, or 40k points for other types of charts. "
                           "Here are some suggestions:\n"
                           "(1) Trying using the image API to return an image "
                           "instead of a graph URL\n"
                           "(2) Use matplotlib\n"
                           "(3) See if you can create your visualization with "
                           "fewer data points\n\n"
                           "If the visualization you're using aggregates "
                           "points (e.g., box plot, histogram, etc.) you can "
                           "disregard this warning.")
                    warnings.warn(msg)
            except TypeError:
                pass
    plot_options = _plot_option_logic(plot_options)
    res = _send_to_plotly(figure, **plot_options)
    if res['error'] == '':
        if plot_options['auto_open']:
            try:
                from webbrowser import open as wbopen
                wbopen(res['url'])
            except:  # TODO: what should we except here? this is dangerous
                pass
        return res['url']
    else:
        raise exceptions.PlotlyAccountError(res['error'])


def iplot_mpl(fig, resize=True, strip_style=False, **plot_options):
    """Replot a matplotlib figure with plotly in IPython.

    This function:
    1. converts the mpl figure into JSON (run help(plolty.tools.mpl_to_plotly))
    2. makes a request to Plotly to save this figure in your account
    3. displays the image in your IPython output cell

    Positional agruments:
    fig -- a figure object from matplotlib

    Keyword arguments:
    resize (default=True) -- allow plotly to choose the figure size
    strip_style (default=False) -- allow plotly to choose style options

    Additional keyword arguments:
    plot_options -- run help(plotly.plotly.iplot)

    """
    fig = tools.mpl_to_plotly(fig, resize=resize, strip_style=strip_style)
    return iplot(fig, **plot_options)


def plot_mpl(fig, resize=True, strip_style=False, **plot_options):
    """Replot a matplotlib figure with plotly.

    This function:
    1. converts the mpl figure into JSON (run help(plolty.tools.mpl_to_plotly))
    2. makes a request to Plotly to save this figure in your account
    3. opens your figure in a browser tab OR returns the unique figure url

    Positional agruments:
    fig -- a figure object from matplotlib

    Keyword arguments:
    resize (default=True) -- allow plotly to choose the figure size
    strip_style (default=False) -- allow plotly to choose style options

    Additional keyword arguments:
    plot_options -- run help(plotly.plotly.plot)

    """
    fig = tools.mpl_to_plotly(fig, resize=resize, strip_style=strip_style)
    return plot(fig, **plot_options)


def get_figure(file_owner, file_id, raw=False):
    """Returns a JSON figure representation for the specified file_owner/_id

    Plotly uniquely identifies figures with a 'file_owner'/'file_id' pair.

    Positional arguments:
    file_owner (string) -- a valid plotly username
    file_id ("int") -- an int or string that can be converted to int

    Keyword arguments:
    raw (default=False) -- if true, return unicode JSON string verbatim**

    **by default, plotly will return a Figure object (run help(plotly
    .graph_objs.Figure)). This representation decodes the keys and values from
    unicode (if possible), removes information irrelevant to the figure
    representation, and converts the JSON dictionary objects to plotly
    `graph objects`.

    """
    server = _plotly_url
    resource = "/apigetfile/{username}/{file_id}".format(username=file_owner,
                                                         file_id=file_id)
    (username, api_key) = _validation_key_logic()

    headers = {'plotly-username': username,
               'plotly-apikey': api_key,
               'plotly-version': '2.0',
               'plotly-platform': 'python'}

    try:
        test_if_int = int(file_id)
    except ValueError:
        raise exceptions.PlotlyError(
            "The 'file_id' argument was not able to be converted into an "
            "integer number. Make sure that the positional 'file_id' argument "
            "is a number that can be converted into an integer or a string "
            "that can be converted into an integer."
        )

    if int(file_id) < 0:
        raise exceptions.PlotlyError(
            "The 'file_id' argument must be a non-negative number."
        )

    response = requests.get(server + resource, headers=headers)
    if response.status_code == 200:
        content = json.loads(response.content)
        response_payload = content['payload']
        figure = response_payload['figure']
        utils.decode_unicode(figure)
        if raw:
            return figure
        else:
            return tools.get_valid_graph_obj(figure, obj_type='Figure')
    else:
        try:
            content = json.loads(response.content)
            raise exceptions.PlotlyError(content)
        except:
            raise exceptions.PlotlyError(
                "There was an error retrieving this file")


class Stream:
    """ Interface to Plotly's real-time graphing API.

    Initialize a Stream object with a stream_id
    found in https://plot.ly/settings.
    Real-time graphs are initialized with a call to `plot` that embeds
    your unique `stream_id`s in each of the graph's traces. The `Stream`
    interface plots data to these traces, as identified with the unique
    stream_id, in real-time.
    Every viewer of the graph sees the same data at the same time.

    View examples and tutorials here:
    http://nbviewer.ipython.org/github/plotly/python-user-guide/blob/master/s7_streaming/s7_streaming.ipynb

    Stream example:
    # Initialize a streaming graph
    # by embedding stream_id's in the graph's traces
    >>> stream_id = "your_stream_id" # See https://plot.ly/settings
    >>> py.plot(Data([Scatter(x=[],
                              y=[],
                              stream=dict(token=stream_id, maxpoints=100))])
    # Stream data to the import trace
    >>> stream = Stream(stream_id) # Initialize a stream object
    >>> stream.open() # Open the stream
    >>> stream.write(dict(x=1, y=1)) # Plot (1, 1) in your graph
    """

    def __init__(self, stream_id):
        """ Initialize a Stream object with your unique stream_id.
        Find your stream_id at https://plot.ly/settings.

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples and tutorials here:
        http://nbviewer.ipython.org/github/plotly/python-user-guide/blob/master/s7_streaming/s7_streaming.ipynb
        """
        self.stream_id = stream_id
        self.connected = False

    def open(self):
        """Open streaming connection to plotly.

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples and tutorials here:
        http://nbviewer.ipython.org/github/plotly/python-user-guide/blob/master/s7_streaming/s7_streaming.ipynb
        """
        self._stream = chunked_requests.Stream('stream.plot.ly',
                                               80,
                                               {'Host': 'stream.plot.ly',
                                                'plotly-streamtoken': self.stream_id})


    def write(self, data, layout=None, validate=True,
              reconnect_on=(200, '', 408)):
        """ Write `data` to your stream. This will plot the
        `data` in your graph in real-time.

        `data` is a plotly formatted dict.
        Valid keys:
            'x', 'y', 'text', 'z', 'marker', 'line'

        Examples:
        >>> write(dict(x = 1, y = 2))
        >>> write(dict(x = [1, 2, 3], y = [10, 20, 30]))
        >>> write(dict(x = 1, y = 2, text = 'scatter text'))
        >>> write(dict(x = 1, y = 3, marker = dict(color = 'blue')))
        >>> write(dict(z = [[1,2,3], [4,5,6]]))

        The connection to plotly's servers is checked before writing
        and reconnected if disconnected and if the response status code
        is in `reconnect_on`.

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples and tutorials here:
        http://nbviewer.ipython.org/github/plotly/python-user-guide/blob/master/s7_streaming/s7_streaming.ipynb
        """
        stream_object = dict()
        stream_object.update(data)
        if 'type' not in stream_object:
            stream_object['type'] = 'scatter'
        if validate:
            try:
                tools.validate(stream_object, stream_object['type'])
            except exceptions.PlotlyError as err:
                raise exceptions.PlotlyError(
                    "Part of the data object with type, '{}', is invalid. This "
                    "will default to 'scatter' if you do not supply a 'type'. "
                    "If you do not want to validate your data objects when "
                    "streaming, you can set 'validate=False' in the call to "
                    "'your_stream.write()'. Here's why the object is "
                    "invalid:\n\n{}".format(stream_object['type'], err)
                )
            try:
                tools.validate_stream(stream_object, stream_object['type'])
            except exceptions.PlotlyError as err:
                raise exceptions.PlotlyError(
                    "Part of the data object with type, '{}', cannot yet be "
                    "streamed into Plotly. If you do not want to validate your "
                    "data objects when streaming, you can set 'validate=False' "
                    "in the call to 'your_stream.write()'. Here's why the "
                    "object cannot be streamed:\n\n{}"
                    "".format(stream_object['type'], err)
                )
            if layout is not None:
                try:
                    tools.validate(layout, 'Layout')
                except exceptions.PlotlyError as err:
                    raise exceptions.PlotlyError(
                        "Your layout kwarg was invalid. "
                        "Here's why:\n\n{}".format(err)
                    )
        del stream_object['type']

        if layout is not None:
            stream_object.update(dict(layout=layout))

        # TODO: allow string version of this?
        jdata = json.dumps(stream_object, cls=utils._plotlyJSONEncoder)
        jdata += "\n"

        try:
            self._stream.write(jdata, reconnect_on=reconnect_on)
        except AttributeError:
            raise exceptions.PlotlyError("Stream has not been opened yet, "
                                         "cannot write to a closed connection. "
                                         "Call `open()` on the stream to open the stream.")

    def close(self):
        """ Close the stream connection to plotly's streaming servers.

        For more help, see: `help(plotly.plotly.Stream)`
        or see examples and tutorials here:
        http://nbviewer.ipython.org/github/plotly/python-user-guide/blob/master/s7_streaming/s7_streaming.ipynb
        """
        try:
            self._stream.close()
        except AttributeError:
            raise exceptions.PlotlyError("Stream has not been opened yet.")


class image:
    ''' Helper functions wrapped around plotly's static image generation api.
    '''

    @staticmethod
    def get(figure):
        """ Return a static image of the plot described by `figure`.
        """
        (username, api_key) = _validation_key_logic()
        headers = {'plotly-username': username,
                   'plotly-apikey': api_key,
                   'plotly-version': '2.0',
                   'plotly-platform': 'python'}

        server = "https://plot.ly/apigenimage/"
        res = requests.post(server,
                            data=json.dumps(figure,
                                            cls=utils._plotlyJSONEncoder),
                            headers=headers)

        if res.status_code == 200:
            return_data = json.loads(res.content)
            return return_data['payload']
        else:
            try:
                return_data = json.loads(res.content)
            except:
                raise exceptions.PlotlyError("The response "
                                             "from plotly could "
                                             "not be translated.")
            raise exceptions.PlotlyError(return_data['error'])

    @classmethod
    def ishow(cls, figure):
        """ Display a static image of the plot described by `figure`
        in an IPython Notebook.
        """
        img = cls.get(figure)
        from IPython.display import display, Image
        display(Image(img))

    @classmethod
    def save_as(cls, figure, filename):
        """ Save a static image of the plot described by `figure`
        locally as `filename`.
        """
        img = cls.get(figure)
        (base, ext) = os.path.splitext(filename)
        if not ext:
            filename += '.png'
        f = open(filename, 'w')
        img = base64.b64decode(img)
        f.write(img)
        f.close()


def _send_to_plotly(figure, **plot_options):
    """
    """

    data = json.dumps(figure['data'] if 'data' in figure else [],
                      cls=utils._plotlyJSONEncoder)
    file_credentials = tools.get_credentials_file()
    if ('username' in _credentials) and ('api_key' in _credentials):
        username, api_key = _credentials['username'], _credentials['api_key']
    elif ('username' in file_credentials) and ('api_key' in file_credentials):
        (username, api_key) = (file_credentials['username'],
                               file_credentials['api_key'])
    else:
        raise exceptions.PlotlyLocalCredentialsError()

    kwargs = json.dumps(dict(filename=plot_options['filename'],
                             fileopt=plot_options['fileopt'],
                             world_readable=plot_options['world_readable'],
                             layout=figure['layout'] if 'layout' in figure
                             else {}),
                        cls=utils._plotlyJSONEncoder)


    payload = dict(platform='python', # TODO: It'd be cool to expose the platform for RaspPi and others
                   version=version.__version__,
                   args=data,
                   un=username,
                   key=api_key,
                   origin='plot',
                   kwargs=kwargs)

    # TODO: this doesn't work yet for ppl's individual servers for testing...
    # url = _plotly_url + "/clientresp"
    url = "https://plot.ly/clientresp"

    r = requests.post(url, data=payload)
    r.raise_for_status()
    r = json.loads(r.text)
    if 'error' in r and r['error'] != '':
        print(r['error'])
    if 'warning' in r and r['warning'] != '':
        warnings.warn(r['warning'])
    if 'message' in r and r['message'] != '':
        print(r['message'])

    return r


def _validation_key_logic():
    creds_on_file = tools.get_credentials_file()
    if 'username' in _credentials:
        username = _credentials['username']
    elif 'username' in creds_on_file:
        username = creds_on_file['username']
    else:
        username = None
    if 'api_key' in _credentials:
        api_key = _credentials['api_key']
    elif 'api_key' in creds_on_file:
        api_key = creds_on_file['api_key']
    else:
        api_key = None
    if username is None or api_key is None:
        raise exceptions.PlotlyLocalCredentialsError()
    return (username, api_key)


########NEW FILE########
__FILENAME__ = test_get_figure
"""
test_get_figure:
=================

A module intended for use with Nose.

"""
from ... graph_objs import graph_objs
from ... plotly import plotly as py
from ... import exceptions


# username for tests: 'plotlyimagetest'
# api_key for account: '786r5mecv0'


def compare_with_raw(obj, raw_obj, parents=None):
    if isinstance(obj, dict):
        for key in raw_obj:
            if key not in obj:
                if not is_trivial(raw_obj[key]):
                    msg = ""
                    if parents is not None:
                        msg += "->".join(parents) + "->"
                    msg += key + " not in obj\n"
                    print msg
            elif isinstance(raw_obj[key], (dict, list)) and len(raw_obj[key]):
                if parents is None:
                    compare_with_raw(obj[key],
                                     raw_obj[key],
                                     parents=[key])
                else:
                    compare_with_raw(obj[key],
                                     raw_obj[key],
                                     parents=parents + [key])

            else:
                if raw_obj[key] != obj[key]:
                    msg = ""
                    if parents is not None:
                        msg += "->".join(parents) + "->"
                    msg += key + " not equal!\n"
                    msg += "    raw: {} != obj: {}\n".format(raw_obj[key],
                                                             obj[key])
                    print msg
    elif isinstance(obj, list):
        for entry, entry_raw in zip(obj, raw_obj):
            if isinstance(entry, (dict, list)):
                try:
                    coll_name = graph_objs.NAME_TO_KEY[entry.__class__
                        .__name__]
                except KeyError:
                    coll_name = entry.__class__.__name__
                if parents is None:
                    compare_with_raw(entry,
                                     entry_raw,
                                     parents=[coll_name])
                else:
                    compare_with_raw(entry,
                                     entry_raw,
                                     parents=parents + [coll_name])
            else:
                if entry != entry_raw:
                    msg = ""
                    if parents is not None:
                        msg += "->".join(parents) + "->"
                    msg += "->[]->\n"
                    msg += "    obj: {} != raw_obj: {}\n".format(entry,
                                                                 entry_raw)
                    print msg


def is_trivial(obj):
    if isinstance(obj, (dict, list)):
        if len(obj):
            if isinstance(obj, dict):
                tests = (is_trivial(obj[key]) for key in obj)
                return all(tests)
            elif isinstance(obj, list):
                tests = (is_trivial(entry) for entry in obj)
                return all(tests)
            else:
                return False
        else:
            return True
    elif obj is None:
        return True
    else:
        return False


def test_all():
    un = 'plotlyimagetest'
    ak = '786r5mecv0'
    run_test = False
    end_file = 2
    polar_plots = [], #[6, 7, 8]
    skip = range(0)
    if run_test:
        py.sign_in(un, ak)
        file_id = 0
        while True:
            fig, fig_raw = None, None
            while (file_id in polar_plots) or (file_id in skip):
                print "    skipping: https://plot.ly/{}/{}".format(un, file_id)
                file_id += 1
            print "\n"
            try:
                print "testing: https://plot.ly/{}/{}".format(un, file_id)
                print "###########################################\n\n"
                fig = py.get_figure('plotlyimagetest', str(file_id))
                fig_raw = py.get_figure('plotlyimagetest',
                                        str(file_id),
                                        raw=True)
            except exceptions.PlotlyError:
                pass
            if (fig is None) and (fig_raw is None):
                print "    couldn't find: https://plot.ly/{}/{}".format(un,
                                                                        file_id)
            else:
                compare_with_raw(fig, fig_raw, parents=['figure'])
            file_id += 1
            if file_id > end_file:
                break
        raise exceptions.PlotlyError("This error was generated so that the "
                                     "following output is produced...")




########NEW FILE########
__FILENAME__ = test_get_requests
"""
test_get_requests:
==================

A module intended for use with Nose.

"""

import requests
import copy
import json

default_headers = {'plotly-username': '',
                   'plotly-apikey': '',
                   'plotly-version': '2.0',
                   'plotly-platform': 'pythonz'}

server = "https://plot.ly"

# username = "get_test_user"
# password = "password"
# api_key = "vgs6e0cnoi" (currently...)


def test_user_does_not_exist():
    username = 'user_does_not_exist'
    api_key = 'invalid-apikey'
    file_owner = 'get_test_user'
    file_id = 0
    hd = copy.copy(default_headers)
    hd['plotly-username'] = username
    hd['plotly-apikey'] = api_key
    resource = "/apigetfile/{}/{}/".format(file_owner, file_id)
    response = requests.get(server + resource, headers=hd)
    content = json.loads(response.content)
    print response.status_code
    print content
    assert response.status_code == 404
    assert (content['error'] == "Aw, snap! We don't have an account for {}. "
                                "Want to try again? Sign in is not case "
                                "sensitive.".format(username))


def test_file_does_not_exist():
    username = 'plotlyimagetest'
    api_key = '786r5mecv0'
    file_owner = 'get_test_user'
    file_id = 1000
    hd = copy.copy(default_headers)
    hd['plotly-username'] = username
    hd['plotly-apikey'] = api_key
    resource = "/apigetfile/{}/{}/".format(file_owner, file_id)
    response = requests.get(server + resource, headers=hd)
    content = json.loads(response.content)
    print response.status_code
    print content
    assert response.status_code == 404
    assert (content['error'] == "Aw, snap! It looks like this file does not "
                                "exist. Want to try again?")


def test_wrong_api_key():  # TODO: does this test the right thing?
    username = 'plotlyimagetest'
    api_key = 'invalid-apikey'
    file_owner = 'get_test_user'
    file_id = 0
    hd = copy.copy(default_headers)
    hd['plotly-username'] = username
    hd['plotly-apikey'] = api_key
    resource = "/apigetfile/{}/{}/".format(file_owner, file_id)
    response = requests.get(server + resource, headers=hd)
    content = json.loads(response.content)
    print response.status_code
    print content
    assert response.status_code == 401
    # TODO: check error message?


# Locked File
# TODO

def test_private_permission_defined():
    username = 'plotlyimagetest'
    api_key = '786r5mecv0'
    file_owner = 'get_test_user'
    file_id = 1  # 1 is a private file
    hd = copy.copy(default_headers)
    hd['plotly-username'] = username
    hd['plotly-apikey'] = api_key
    resource = "/apigetfile/{}/{}/".format(file_owner, file_id)
    response = requests.get(server + resource, headers=hd)
    content = json.loads(response.content)
    print response.status_code
    print content
    assert response.status_code == 403

# Private File that is shared
# TODO


def test_missing_headers():
    file_owner = 'get_test_user'
    file_id = 0
    resource = "/apigetfile/{}/{}/".format(file_owner, file_id)
    headers = default_headers.keys()
    for header in headers:
        hd = copy.copy(default_headers)
        del hd[header]
        response = requests.get(server + resource, headers=hd)
        content = json.loads(response.content)
        print response.status_code
        print content
        assert response.status_code == 422


def test_valid_request():
    username = 'plotlyimagetest'
    api_key = '786r5mecv0'
    file_owner = 'get_test_user'
    file_id = 0
    hd = copy.copy(default_headers)
    hd['plotly-username'] = username
    hd['plotly-apikey'] = api_key
    resource = "/apigetfile/{}/{}/".format(file_owner, file_id)
    response = requests.get(server + resource, headers=hd)
    content = json.loads(response.content)
    print response.status_code
    print content
    assert response.status_code == 200
    # content = json.loads(res.content)
    # response_payload = content['payload']
    # figure = response_payload['figure']
    # if figure['data'][0]['x'] != [u'1', u'2', u'3']:
    #     print 'ERROR'
    # return res


########NEW FILE########
__FILENAME__ = test_annotations
"""
test_annotations:
==========

A module intended for use with Nose.

"""
from nose.tools import raises
from ...graph_objs.graph_objs import *
from ...exceptions import (PlotlyDictKeyError, PlotlyDictValueError,
                           PlotlyDataTypeError, PlotlyListEntryError)


def setup():
    import warnings
    warnings.filterwarnings('ignore')


def test_trivial():
    assert Annotations() == list()


def test_weird_instantiation():  # Python allows this...
    assert Annotations({}) == list({})


def test_dict_instantiation():
    Annotations([{'text': 'annotation text'}])


@raises(PlotlyDictKeyError)
def test_dict_instantiation_key_error():
    print Annotations([{'not-a-key': 'anything'}])


@raises(PlotlyDictValueError)
def test_dict_instantiation_key_error():
    print Annotations([{'font': 'not-a-dict'}])


@raises(PlotlyListEntryError)
def test_dict_instantiation_graph_obj_error_0():
    Annotations([Data()])


@raises(PlotlyListEntryError)
def test_dict_instantiation_graph_obj_error_1():
    Annotations([Figure()])


@raises(PlotlyListEntryError)
def test_dict_instantiation_graph_obj_error_2():
    Annotations([Annotations()])


@raises(PlotlyListEntryError)
def test_dict_instantiation_graph_obj_error_3():
    Annotations([Layout()])


def test_validate():
    annotations = Annotations()
    annotations.validate()
    annotations += [{'text': 'some text'}]
    annotations.validate()
    annotations += [{},{},{}]
    annotations.validate()


@raises(PlotlyDictKeyError)
def test_validate_error():
    annotations = Annotations()
    annotations.append({'not-a-key': 'anything'})
    annotations.validate()


########NEW FILE########
__FILENAME__ = test_consistency
"""
test_consistency:
================

A module intended for use with Nose. Check that items in graph_objs_meta.json
are properly defined in both graph_objs.py and included in the mapping dicts.

"""
from ... graph_objs import graph_objs


def test_info_keys_in_key_to_name():
    for key in graph_objs.INFO:
        class_name = graph_objs.KEY_TO_NAME[key]


def test_names_in_name_to_key():
    for key in graph_objs.INFO:
        class_name = graph_objs.KEY_TO_NAME[key]
        key_name = graph_objs.NAME_TO_KEY[class_name]


def test_names_in_name_to_class():
    for key in graph_objs.INFO:
        class_name = graph_objs.KEY_TO_NAME[key]
        _class = graph_objs.NAME_TO_CLASS[class_name]

########NEW FILE########
__FILENAME__ = test_data
"""
test_data:
==========

A module intended for use with Nose.

"""
from nose.tools import raises
from ...graph_objs.graph_objs import *
from ...exceptions import (PlotlyDictKeyError, PlotlyDictValueError,
                           PlotlyDataTypeError, PlotlyListEntryError)


def setup():
    import warnings
    warnings.filterwarnings('ignore')


def test_trivial():
    assert Data() == list()


def test_weird_instantiation():  # Python allows this...
    assert Data({}) == list({})


def test_default_scatter():
    assert Data([{}]) == list([{'type': 'scatter'}])


def test_dict_instantiation():
    Data([{'type': 'scatter'}])


@raises(PlotlyDictKeyError)
def test_dict_instantiation_key_error():
    print Data([{'not-a-key': 'anything'}])


@raises(PlotlyDictValueError)
def test_dict_instantiation_key_error():
    print Data([{'marker': 'not-a-dict'}])


@raises(PlotlyDataTypeError)
def test_dict_instantiation_type_error():
    Data([{'type': 'invalid_type'}])


@raises(PlotlyListEntryError)
def test_dict_instantiation_graph_obj_error_0():
    Data([Data()])


@raises(PlotlyListEntryError)
def test_dict_instantiation_graph_obj_error_1():
    Data([Figure()])


@raises(PlotlyListEntryError)
def test_dict_instantiation_graph_obj_error_2():
    Data([Annotations()])


@raises(PlotlyListEntryError)
def test_dict_instantiation_graph_obj_error_3():
    Data([Layout()])


def test_validate():
    data = Data()
    data.validate()
    data += [{'type': 'scatter'}]
    data.validate()
    data += [{},{},{}]
    data.validate()


@raises(PlotlyDictKeyError)
def test_validate_error():
    data = Data()
    data.append({'not-a-key': 'anything'})
    data.validate()


########NEW FILE########
__FILENAME__ = test_error_bars
"""
test_error_bars:
================

A module intended for use with Nose.

"""
from nose.tools import raises
from ...graph_objs.graph_objs import *
from ...exceptions import (PlotlyDictKeyError, PlotlyDictValueError,
                           PlotlyDataTypeError, PlotlyListEntryError)


def test_instantiate_error_x():
    ErrorX()
    ErrorX(array=[1, 2, 3],
           arrayminus=[2, 1, 2],
           color='red',
           copy_ystyle=False,
           opacity=.4,
           symmetric=False,
           thickness=2,
           traceref=0,  # TODO, what's this do again?
           type='percent',
           value=1,
           valueminus=4,
           visible=True,
           width=5)


def test_instantiate_error_y():
    ErrorY()
    ErrorY(array=[1, 2, 3],
           arrayminus=[2, 1, 2],
           color='red',
           opacity=.4,
           symmetric=False,
           thickness=2,
           traceref=0,  # TODO, what's this do again?
           type='percent',
           value=1,
           valueminus=4,
           visible=True,
           width=5)


@raises(PlotlyDictKeyError)
def test_key_error():
    ErrorX(value=0.1, typ='percent', color='red')
########NEW FILE########
__FILENAME__ = test_plotly_dict
"""
test_plotly_dict:
=================

A module intended for use with Nose.

"""
from nose.tools import raises
from ... graph_objs.graph_objs import PlotlyDict
from ... exceptions import PlotlyError


def test_trivial():
    assert PlotlyDict() == dict()


# @raises(PlotlyError)  # TODO: decide if this SHOULD raise error...
# def test_instantiation_error():
#     print PlotlyDict(anything='something')


def test_validate():
    PlotlyDict().validate()


@raises(PlotlyError)
def test_validate_error():
    pd = PlotlyDict()
    pd['invalid']='something'
    pd.validate()
########NEW FILE########
__FILENAME__ = test_plotly_list
"""
test_plotly_list:
=================

A module intended for use with Nose.

"""
from nose.tools import raises
from ... graph_objs.graph_objs import PlotlyList, PlotlyDict
from ... exceptions import PlotlyError


def test_trivial():
    assert PlotlyList() == list()


def test_weird_instantiation():
    assert PlotlyList({}) == list({})


@raises(PlotlyError)
def test_instantiation_error():
    print PlotlyList([{}])


def test_blank_trace_instantiation():
    assert PlotlyList([PlotlyDict(), PlotlyDict()]) == list([dict(), dict()])


def test_validate():
    PlotlyList().validate()


@raises(PlotlyError)
def test_validate_error():
    pl = PlotlyList()
    pl.append({})
    pl.validate()
########NEW FILE########
__FILENAME__ = test_plotly_trace
"""
test_trace:
===========

A module intended for use with Nose.

"""
from nose.tools import raises
from ... graph_objs.graph_objs import PlotlyTrace
from ... exceptions import PlotlyError


def test_trivial():
    assert PlotlyTrace() == dict()


# @raises(PlotlyError)  # TODO: decide if this SHOULD raise error...
# def test_instantiation_error():
#     print Trace(anything='something')


def test_validate():
    PlotlyTrace().validate()


@raises(PlotlyError)
def test_validate_error():
    trace = PlotlyTrace()
    trace['invalid'] = 'something'
    trace.validate()

########NEW FILE########
__FILENAME__ = test_scatter
"""
test_scatter:
=================

A module intended for use with Nose.

"""
from nose.tools import raises
from ... graph_objs import Scatter
from ... exceptions import PlotlyError


def test_trivial():
    print Scatter()
    assert Scatter() == dict(type='scatter')


# @raises(PlotlyError)  # TODO: decide if this SHOULD raise error...
# def test_instantiation_error():
#     print PlotlyDict(anything='something')


def test_validate():
    Scatter().validate()


@raises(PlotlyError)
def test_validate_error():
    scatter = Scatter()
    scatter['invalid']='something'
    scatter.validate()
########NEW FILE########
__FILENAME__ = annotations
from plotly.graph_objs import *

ANNOTATIONS = Figure(
    data=Data([
        Scatter(
            x=[0.0, 1.0, 2.0],
            y=[1.0, 2.0, 3.0],
            name='_line0',
            mode='lines',
            line=Line(
                dash='solid',
                color='#0000FF',
                width=1.0,
                opacity=1
            ),
            xaxis='x1',
            yaxis='y1'
        ),
        Scatter(
            x=[0.0, 1.0, 2.0],
            y=[3.0, 2.0, 1.0],
            name='_line1',
            mode='lines',
            line=Line(
                dash='solid',
                color='#0000FF',
                width=1.0,
                opacity=1
            ),
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=80,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        annotations=Annotations([
            Annotation(
                x=0.000997987927565,
                y=0.996414507772,
                text='top-left',
                xref='paper',
                yref='paper',
                showarrow=False,
                font=Font(
                    size=12.0,
                    color='#000000'
                ),
                opacity=1,
                xanchor='left',
                yanchor='top'
            ),
            Annotation(
                x=0.000997987927565,
                y=0.00358549222798,
                text='bottom-left',
                xref='paper',
                yref='paper',
                showarrow=False,
                font=Font(
                    size=12.0,
                    color='#000000'
                ),
                opacity=1,
                xanchor='left',
                yanchor='bottom'
            ),
            Annotation(
                x=0.996989939638,
                y=0.996414507772,
                text='top-right',
                xref='paper',
                yref='paper',
                showarrow=False,
                font=Font(
                    size=12.0,
                    color='#000000'
                ),
                opacity=1,
                xanchor='right',
                yanchor='top'
            ),
            Annotation(
                x=0.996989939638,
                y=0.00358549222798,
                text='bottom-right',
                xref='paper',
                yref='paper',
                showarrow=False,
                font=Font(
                    size=12.0,
                    color='#000000'
                ),
                opacity=1,
                xanchor='right',
                yanchor='bottom'
            )
        ]),
        xaxis1=XAxis(
            domain=[0.0, 1.0],
            range=(0.0, 2.0),
            showline=True,
            ticks='inside',
            showgrid=False,
            zeroline=False,
            anchor='y1',
            mirror=True
        ),
        yaxis1=YAxis(
            domain=[0.0, 1.0],
            range=(1.0, 3.0),
            showline=True,
            ticks='inside',
            showgrid=False,
            zeroline=False,
            anchor='x1',
            mirror=True
        )
    )
)

########NEW FILE########
__FILENAME__ = axis_scales
from plotly.graph_objs import *

D = dict(
    x=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    y=[10, 3, 100, 6, 45, 4, 80, 45, 3, 59])

EVEN_LINEAR_SCALE = Figure(
    data=Data([
        Scatter(
            x=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            y=[10.0, 3.0, 100.0, 6.0, 45.0, 4.0, 80.0, 45.0, 3.0, 59.0],
            name='_line0',
            mode='lines',
            line=Line(
                dash='solid',
                color='#0000FF',
                width=1.0,
                opacity=1
            ),
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=80,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        xaxis1=XAxis(
            domain=[0.0, 1.0],
            range=[0.0, 18.0],
            type='linear',
            showline=True,
            tick0=0,
            dtick=3,
            ticks='inside',
            showgrid=False,
            autotick=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y1',
            side='bottom',
            mirror='ticks'
        ),
        yaxis1=YAxis(
            domain=[0.0, 1.0],
            range=[0.0, 195.0],
            type='linear',
            showline=True,
            tick0=0,
            dtick=13,
            ticks='inside',
            showgrid=False,
            autotick=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x1',
            side='left',
            mirror='ticks'
        )
    )
)

########NEW FILE########
__FILENAME__ = bars
from plotly.graph_objs import *

D = dict(
    left=[0, 1, 2, 3, 4, 5],
    height=[10, 20, 50, 80, 100, 200],
    bottom=[0, 1, 2, 3, 4, 5, 6],
    width=[1, 4, 8, 16, 32, 64, 128],
    multi_left=[0, 10, 20, 30, 40, 50],
    multi_height=[1, 4, 8, 16, 32, 64],
    multi_bottom=[15, 30, 45, 60, 75, 90],
    multi_width=[30, 60, 20, 50, 60, 30]
)

VERTICAL_BAR = Figure(
    data=Data([
        Bar(
            x=[0.40000000000000002, 1.3999999999999999, 2.3999999999999999, 3.3999999999999999, 4.4000000000000004, 5.4000000000000004],
            y=[10.0, 20.0, 50.0, 80.0, 100.0, 200.0],
            orientation='v',
            marker=Marker(
                line=Line(
                    width=1.0
                ),
                color='#0000FF'
            ),
            opacity=1,
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=80,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        xaxis1=XAxis(
            domain=[0.0, 1.0],
            range=[0.0, 6.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=7,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y1',
            side='bottom',
            mirror='ticks'
        ),
        yaxis1=YAxis(
            domain=[0.0, 1.0],
            range=[0.0, 200.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=5,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x1',
            side='left',
            mirror='ticks'
        )
    )
)

HORIZONTAL_BAR = Figure(
    data=Data([
        Bar(
            x=[1.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0],
            y=[0.40000000000000002, 1.3999999999999999, 2.3999999999999999, 3.3999999999999999, 4.4000000000000004, 5.4000000000000004, 6.4000000000000004],
            orientation='h',
            marker=Marker(
                line=Line(
                    width=1.0
                ),
                color='#0000FF'
            ),
            opacity=1,
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=80,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        xaxis1=XAxis(
            domain=[0.0, 1.0],
            range=[0.0, 140.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=8,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y1',
            side='bottom',
            mirror='ticks'
        ),
        yaxis1=YAxis(
            domain=[0.0, 1.0],
            range=[0.0, 7.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=8,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x1',
            side='left',
            mirror='ticks'
        )
    )
)

H_AND_V_BARS = Figure(
    data=Data([
        Bar(
            x=[5.0, 15.0, 25.0, 35.0, 45.0, 55.0],
            y=[1.0, 4.0, 8.0, 16.0, 32.0, 64.0],
            orientation='v',
            marker=Marker(
                line=Line(
                    width=1.0
                ),
                color='#008000'
            ),
            opacity=0.5,
            xaxis='x1',
            yaxis='y1'
        ),
        Bar(
            x=[30.0, 60.0, 20.0, 50.0, 60.0, 30.0],
            y=[20.0, 35.0, 50.0, 65.0, 80.0, 95.0],
            orientation='h',
            marker=Marker(
                line=Line(
                    width=1.0
                ),
                color='#FF0000'
            ),
            opacity=0.5,
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=80,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        xaxis1=XAxis(
            domain=[0.0, 1.0],
            range=[0.0, 60.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=7,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y1',
            side='bottom',
            mirror='ticks'
        ),
        yaxis1=YAxis(
            domain=[0.0, 1.0],
            range=[0.0, 100.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x1',
            side='left',
            mirror='ticks'
        )
    )
)



########NEW FILE########
__FILENAME__ = data
D = dict(
    x1=[0, 1, 2, 3, 4, 5],
    y1=[10, 20, 50, 80, 100, 200],
    x2=[0, 1, 2, 3, 4, 5, 6],
    y2=[1, 4, 8, 16, 32, 64, 128]
)

########NEW FILE########
__FILENAME__ = lines
from plotly.graph_objs import *

D = dict(
    x1=[0, 1, 2, 3, 4, 5],
    y1=[10, 20, 50, 80, 100, 200],
    x2=[0, 1, 2, 3, 4, 5, 6],
    y2=[1, 4, 8, 16, 32, 64, 128]
)

SIMPLE_LINE = Figure(
    data=Data([
        Scatter(
            x=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            y=[10.0, 20.0, 50.0, 80.0, 100.0, 200.0],
            name='simple',
            mode='lines',
            line=Line(
                dash='solid',
                color='#0000FF',
                width=1.0,
                opacity=1
            ),
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=80,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        xaxis1=XAxis(
            domain=[0.0, 1.0],
            range=[0.0, 5.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y1',
            side='bottom',
            mirror='ticks'
        ),
        yaxis1=YAxis(
            domain=[0.0, 1.0],
            range=[0.0, 200.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=5,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x1',
            side='left',
            mirror='ticks'
        )
    )
)

COMPLICATED_LINE = Figure(
    data=Data([
        Scatter(
            x=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            y=[10.0, 20.0, 50.0, 80.0, 100.0, 200.0],
            name='one',
            mode='markers',
            marker=Marker(
                symbol='dot',
                line=Line(
                    color='#000000',
                    width=0.5
                ),
                size=10,
                color='#FF0000',
                opacity=0.5
            ),
            xaxis='x1',
            yaxis='y1'
        ),
        Scatter(
            x=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0],
            y=[10.0, 20.0, 50.0, 80.0, 100.0, 200.0],
            name='two',
            mode='lines',
            line=Line(
                dash='solid',
                color='#0000FF',
                width=2,
                opacity=0.7
            ),
            xaxis='x1',
            yaxis='y1'
        ),
        Scatter(
            x=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            y=[1.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0],
            name='three',
            mode='markers',
            marker=Marker(
                symbol='cross',
                line=Line(
                    color='#0000FF',
                    width=2
                ),
                size=10,
                color='#0000FF',
                opacity=0.6
            ),
            xaxis='x1',
            yaxis='y1'
        ),
        Scatter(
            x=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            y=[1.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0],
            name='four',
            mode='lines',
            line=Line(
                dash='dash',
                color='#FF0000',
                width=2,
                opacity=0.8
            ),
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=80,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        xaxis1=XAxis(
            domain=[0.0, 1.0],
            range=[0.0, 6.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=7,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y1',
            side='bottom',
            mirror='ticks'
        ),
        yaxis1=YAxis(
            domain=[0.0, 1.0],
            range=[0.0, 200.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=5,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x1',
            side='left',
            mirror='ticks'
        )
    )
)
########NEW FILE########
__FILENAME__ = scatter
from plotly.graph_objs import *

D = dict(
    x1=[1, 2, 2, 4, 5, 6, 1, 7, 8, 5 ,3],
    y1=[5, 3, 7, 2, 9, 7, 8, 4, 5, 9, 2],
    x2=[-1, 1, -0.3, -0.6, 0.4, 0.8, -0.1, 0.7],
    y2=[-0.5, 0.4, 0.7, -0.6, 0.3, -1, 0, 0.3]
)

SIMPLE_SCATTER = Figure(
    data=Data([
        Scatter(
            x=[1.0, 2.0, 2.0, 4.0, 5.0, 6.0, 1.0, 7.0, 8.0, 5.0, 3.0],
            y=[5.0, 3.0, 7.0, 2.0, 9.0, 7.0, 8.0, 4.0, 5.0, 9.0, 2.0],
            mode='markers',
            marker=Marker(
                symbol='dot',
                line=Line(
                    color='rgb(0,0,0)',
                    width=1.0
                ),
                size=4.4721359549995796,
                color='rgb(0,0,255)',
                opacity=1.0
            ),
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=80,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        xaxis1=XAxis(
            domain=[0.0, 1.0],
            range=[0.0, 9.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=10,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y1',
            side='bottom',
            mirror='ticks'
        ),
        yaxis1=YAxis(
            domain=[0.0, 1.0],
            range=[1.0, 10.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=10,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x1',
            side='left',
            mirror='ticks'
        )
    )
)

DOUBLE_SCATTER = Figure(
    data=Data([
        Scatter(
            x=[1.0, 2.0, 2.0, 4.0, 5.0, 6.0, 1.0, 7.0, 8.0, 5.0, 3.0],
            y=[5.0, 3.0, 7.0, 2.0, 9.0, 7.0, 8.0, 4.0, 5.0, 9.0, 2.0],
            mode='markers',
            marker=Marker(
                symbol='triangle-up',
                line=Line(
                    color='rgb(255,0,0)',
                    width=1.0
                ),
                size=11.0,
                color='rgb(255,0,0)',
                opacity=0.5
            ),
            xaxis='x1',
            yaxis='y1'
        ),
        Scatter(
            x=[-1.0, 1.0, -0.29999999999999999, -0.59999999999999998, 0.40000000000000002, 0.80000000000000004, -0.10000000000000001, 0.69999999999999996],
            y=[-0.5, 0.40000000000000002, 0.69999999999999996, -0.59999999999999998, 0.29999999999999999, -1.0, 0.0, 0.29999999999999999],
            mode='markers',
            marker=Marker(
                symbol='square',
                line=Line(
                    color='rgb(128,0,128)',
                    width=1.0
                ),
                size=8.0,
                color='rgb(128,0,128)',
                opacity=0.5
            ),
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=80,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        xaxis1=XAxis(
            domain=[0.0, 1.0],
            range=[-2.0, 10.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=7,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y1',
            side='bottom',
            mirror='ticks'
        ),
        yaxis1=YAxis(
            domain=[0.0, 1.0],
            range=[-2.0, 10.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=7,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x1',
            side='left',
            mirror='ticks'
        )
    )
)

########NEW FILE########
__FILENAME__ = subplots
from plotly.graph_objs import *

D = dict(
    x1=[0, 1],
    y1=[1, 2]
)

BLANK_SUBPLOTS = Figure(
    data=Data([
        Scatter(
            x=[0.0, 1.0],
            y=[1.0, 2.0],
            name='_line0',
            mode='lines',
            line=Line(
                dash='solid',
                color='#0000FF',
                width=1.0,
                opacity=1
            ),
            xaxis='x1',
            yaxis='y1'
        )
    ]),
    layout=Layout(
        width=640,
        height=480,
        autosize=False,
        margin=Margin(
            l=168,
            r=63,
            b=47,
            t=47,
            pad=0
        ),
        hovermode='closest',
        showlegend=False,
        xaxis1=XAxis(
            domain=[0.0, 0.13513513513513517],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y1',
            side='bottom',
            mirror='ticks'
        ),
        xaxis2=XAxis(
            domain=[0.0, 0.13513513513513517],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y2',
            side='bottom',
            mirror='ticks'
        ),
        xaxis3=XAxis(
            domain=[0.0, 0.13513513513513517],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y3',
            side='bottom',
            mirror='ticks'
        ),
        xaxis4=XAxis(
            domain=[0.2162162162162162, 1.0],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y4',
            side='bottom',
            mirror='ticks'
        ),
        xaxis5=XAxis(
            domain=[0.2162162162162162, 0.56756756756756754],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y5',
            side='bottom',
            mirror='ticks'
        ),
        xaxis6=XAxis(
            domain=[0.2162162162162162, 0.78378378378378377],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y6',
            side='bottom',
            mirror='ticks'
        ),
        xaxis7=XAxis(
            domain=[0.64864864864864857, 1.0],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y7',
            side='bottom',
            mirror='ticks'
        ),
        xaxis8=XAxis(
            domain=[0.8648648648648648, 1.0],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='y8',
            side='bottom',
            mirror='ticks'
        ),
        yaxis1=YAxis(
            domain=[0.82758620689655182, 1.0],
            range=[1.0, 2.2000000000000002],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=8,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x1',
            side='left',
            mirror='ticks'
        ),
        yaxis2=YAxis(
            domain=[0.55172413793103459, 0.72413793103448276],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x2',
            side='left',
            mirror='ticks'
        ),
        yaxis3=YAxis(
            domain=[0.0, 0.44827586206896558],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x3',
            side='left',
            mirror='ticks'
        ),
        yaxis4=YAxis(
            domain=[0.82758620689655182, 1.0],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x4',
            side='left',
            mirror='ticks'
        ),
        yaxis5=YAxis(
            domain=[0.27586206896551724, 0.72413793103448276],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x5',
            side='left',
            mirror='ticks'
        ),
        yaxis6=YAxis(
            domain=[0.0, 0.17241379310344834],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x6',
            side='left',
            mirror='ticks'
        ),
        yaxis7=YAxis(
            domain=[0.27586206896551724, 0.72413793103448276],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x7',
            side='left',
            mirror='ticks'
        ),
        yaxis8=YAxis(
            domain=[0.0, 0.17241379310344834],
            range=[0.0, 1.0],
            type='linear',
            showline=True,
            ticks='inside',
            nticks=6,
            showgrid=False,
            zeroline=False,
            tickfont=Font(
                size=12.0
            ),
            anchor='x8',
            side='left',
            mirror='ticks'
        )
    )
)
########NEW FILE########
__FILENAME__ = nose_tools
from ... matplotlylib import Exporter, PlotlyRenderer
from numbers import Number as Num


def compare_dict(dict1, dict2, equivalent=True, msg='', tol=10e-8):
    for key in dict1:
        if key not in dict2:
            return False, "{} should be {}".format(dict1.keys(), dict2.keys())
    for key in dict1:
        if isinstance(dict1[key], dict):
            equivalent, msg = compare_dict(dict1[key],
                                           dict2[key],
                                           tol=tol)
        elif isinstance(dict1[key], Num) and isinstance(dict2[key], Num):
            if not comp_nums(dict1[key], dict2[key], tol):
                return False, "['{}'] = {} should be {}".format(key,
                                                                dict1[key],
                                                                dict2[key])
        elif is_num_list(dict1[key]) and is_num_list(dict2[key]):
            if not comp_num_list(dict1[key], dict2[key], tol):
                return False, "['{}'] = {} should be {}".format(key,
                                                                dict1[key],
                                                                dict2[key])
        elif not (dict1[key] == dict2[key]):
                return False, "['{}'] = {} should be {}".format(key,
                                                                dict1[key],
                                                                dict2[key])
        if not equivalent:
            return False, "['{}']".format(key) + msg
    return equivalent, msg


def comp_nums(num1, num2, tol=10e-8):
    return abs(num1-num2) < tol


def comp_num_list(list1, list2, tol=10e-8):
    for item1, item2 in zip(list1, list2):
        if not comp_nums(item1, item2, tol):
            return False
    return True


def is_num_list(item):
    try:
        for thing in item:
            if not isinstance(thing, Num):
                raise TypeError
    except TypeError:
        return False
    return True


def run_fig(fig):
    renderer = PlotlyRenderer()
    exporter = Exporter(renderer)
    exporter.run(fig)
    return renderer

########NEW FILE########
__FILENAME__ = test_annotations
import matplotlib.pyplot as plt

from . nose_tools import compare_dict, run_fig
from . data.annotations import *


def test_annotations():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], 'b-')
    ax.plot([3, 2, 1], 'b-')
    ax.text(0.001, 0.999,
            'top-left', transform=ax.transAxes, va='top', ha='left')
    ax.text(0.001, 0.001,
            'bottom-left', transform=ax.transAxes, va='baseline', ha='left')
    ax.text(0.999, 0.999,
            'top-right', transform=ax.transAxes, va='top', ha='right')
    ax.text(0.999, 0.001,
            'bottom-right', transform=ax.transAxes, va='baseline', ha='right')
    renderer = run_fig(fig)
    for data_no, data_dict in enumerate(renderer.plotly_fig['data']):
        equivalent, msg = compare_dict(data_dict,
                                       ANNOTATIONS['data'][data_no])
        assert equivalent, msg
    for no, note in enumerate(renderer.plotly_fig['layout']['annotations']):
        equivalent, msg = compare_dict(note,
                                       ANNOTATIONS['layout']['annotations'][no])
        assert equivalent, msg

########NEW FILE########
__FILENAME__ = test_axis_scales
import matplotlib.pyplot as plt

from .nose_tools import compare_dict, run_fig
from .data.axis_scales import *


def test_even_linear_scale():
    fig, ax = plt.subplots()
    x = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    y = [10, 3, 100, 6, 45, 4, 80, 45, 3, 59]
    ax.plot(x, y)
    _ = ax.set_xticks(range(0, 20, 3))
    _ = ax.set_yticks(range(0, 200, 13))
    renderer = run_fig(fig)
    for data_no, data_dict in enumerate(renderer.plotly_fig['data']):
        equivalent, msg = compare_dict(data_dict,
                                       EVEN_LINEAR_SCALE['data'][data_no])
        assert equivalent, msg
    equivalent, msg = compare_dict(renderer.plotly_fig['layout'],
                                   EVEN_LINEAR_SCALE['layout'])
    assert equivalent, msg

########NEW FILE########
__FILENAME__ = test_bars
import matplotlib.pyplot as plt

from . nose_tools import compare_dict, run_fig
from . data.bars import *


def test_vertical_bar():
    fig, ax = plt.subplots()
    ax.bar(left=D['left'], height=D['height'])
    renderer = run_fig(fig)
    for data_no, data_dict in enumerate(renderer.plotly_fig['data']):
        equivalent, msg = compare_dict(data_dict,
                                       VERTICAL_BAR['data'][data_no])
        assert equivalent, msg
    equivalent, msg = compare_dict(renderer.plotly_fig['layout'],
                                   VERTICAL_BAR['layout'])
    assert equivalent, msg


def test_horizontal_bar():
    fig, ax = plt.subplots()
    ax.barh(bottom=D['bottom'], width=D['width'])
    renderer = run_fig(fig)
    for data_no, data_dict in enumerate(renderer.plotly_fig['data']):
        equivalent, msg = compare_dict(data_dict,
                                       HORIZONTAL_BAR['data'][data_no])
        assert equivalent, msg
    equivalent, msg = compare_dict(renderer.plotly_fig['layout'],
                                   HORIZONTAL_BAR['layout'])
    assert equivalent, msg


def test_h_and_v_bars():
    fig, ax = plt.subplots()
    ax.bar(left=D['multi_left'], height=D['multi_height'],
           width=10, color='green', alpha=.5)
    ax.barh(bottom=D['multi_bottom'], width=D['multi_width'],
            height=10, color='red', alpha=.5)
    renderer = run_fig(fig)
    for data_no, data_dict in enumerate(renderer.plotly_fig['data']):
        equivalent, msg = compare_dict(data_dict,
                                       H_AND_V_BARS['data'][data_no])
        assert equivalent, msg
    equivalent, msg = compare_dict(renderer.plotly_fig['layout'],
                                   H_AND_V_BARS['layout'])
    assert equivalent, msg
########NEW FILE########
__FILENAME__ = test_data
import matplotlib.pyplot as plt

from .nose_tools import run_fig
from .data.data import *


def test_line_data():
    fig, ax = plt.subplots()
    ax.plot(D['x1'], D['y1'])
    renderer = run_fig(fig)
    for xi, xf, yi, yf in zip(renderer.plotly_fig['data'][0]['x'], D['x1'],
                              renderer.plotly_fig['data'][0]['y'], D['y1']):
        assert xi == xf, str(
            renderer.plotly_fig['data'][0]['x']) + ' is not ' + str(D['x1'])
        assert yi == yf, str(
            renderer.plotly_fig['data'][0]['y']) + ' is not ' + str(D['y1'])


def test_lines_data():
    fig, ax = plt.subplots()
    ax.plot(D['x1'], D['y1'])
    ax.plot(D['x2'], D['y2'])
    renderer = run_fig(fig)
    for xi, xf, yi, yf in zip(renderer.plotly_fig['data'][0]['x'], D['x1'],
                              renderer.plotly_fig['data'][0]['y'], D['y1']):
        assert xi == xf, str(
            renderer.plotly_fig['data'][0]['x']) + ' is not ' + str(D['x1'])
        assert yi == yf, str(
            renderer.plotly_fig['data'][0]['y']) + ' is not ' + str(D['y1'])
    for xi, xf, yi, yf in zip(renderer.plotly_fig['data'][1]['x'], D['x2'],
                              renderer.plotly_fig['data'][1]['y'], D['y2']):
        assert xi == xf, str(
            renderer.plotly_fig['data'][1]['x']) + ' is not ' + str(D['x2'])
        assert yi == yf, str(
            renderer.plotly_fig['data'][0]['y']) + ' is not ' + str(D['y2'])


def test_bar_data():
    fig, ax = plt.subplots()
    ax.bar(D['x1'], D['y1'])
    renderer = run_fig(fig)
    for yi, yf in zip(renderer.plotly_fig['data'][0]['y'], D['y1']):
        assert yi == yf, str(
            renderer.plotly_fig['data'][0]['y']) + ' is not ' + str(D['y1'])


def test_bars_data():
    fig, ax = plt.subplots()
    ax.bar(D['x1'], D['y1'], color='r')
    ax.barh(D['x2'], D['y2'], color='b')
    renderer = run_fig(fig)
    for yi, yf in zip(renderer.plotly_fig['data'][0]['y'], D['y1']):
        assert yi == yf, str(
            renderer.plotly_fig['data'][0]['y']) + ' is not ' + str(D['y1'])
    for xi, yf in zip(renderer.plotly_fig['data'][1]['x'], D['y2']):
        assert xi == yf, str(
            renderer.plotly_fig['data'][1]['x']) + ' is not ' + str(D['y2'])
########NEW FILE########
__FILENAME__ = test_lines
import matplotlib.pyplot as plt

from .nose_tools import compare_dict, run_fig
from .data.lines import *


def test_simple_line():
    fig, ax = plt.subplots()
    ax.plot(D['x1'], D['y1'], label='simple')
    renderer = run_fig(fig)
    for data_no, data_dict in enumerate(renderer.plotly_fig['data']):
        equivalent, msg = compare_dict(data_dict, SIMPLE_LINE['data'][data_no])
        assert equivalent, msg
    equivalent, msg = compare_dict(renderer.plotly_fig['layout'],
                                   SIMPLE_LINE['layout'])
    assert equivalent, msg


def test_complicated_line():
    fig, ax = plt.subplots()
    ax.plot(D['x1'], D['y1'], 'ro', markersize=10, alpha=.5, label='one')
    ax.plot(D['x1'], D['y1'], '-b', linewidth=2, alpha=.7, label='two')
    ax.plot(D['x2'], D['y2'], 'b+', markeredgewidth=2,
            markersize=10, alpha=.6, label='three')
    ax.plot(D['x2'], D['y2'], '--r', linewidth=2, alpha=.8, label='four')
    renderer = run_fig(fig)
    for data_no, data_dict in enumerate(renderer.plotly_fig['data']):
        equivalent, msg = compare_dict(data_dict,
                                       COMPLICATED_LINE['data'][data_no])
        assert equivalent, msg
    equivalent, msg = compare_dict(renderer.plotly_fig['layout'],
                                   COMPLICATED_LINE['layout'])
    assert equivalent, msg
########NEW FILE########
__FILENAME__ = test_scatter
import matplotlib.pyplot as plt

from .nose_tools import compare_dict, run_fig
from .data.scatter import *


def test_simple_scatter():
    fig, ax = plt.subplots()
    ax.scatter(D['x1'], D['y1'])
    renderer = run_fig(fig)
    for data_no, data_dict in enumerate(renderer.plotly_fig['data']):
        equivalent, msg = compare_dict(data_dict,
                                       SIMPLE_SCATTER['data'][data_no])
        assert equivalent, msg
    equivalent, msg = compare_dict(renderer.plotly_fig['layout'],
                                   SIMPLE_SCATTER['layout'])
    assert equivalent, msg


def test_double_scatter():
    fig, ax = plt.subplots()
    ax.scatter(D['x1'], D['y1'], color='red', s=121, marker='^', alpha=0.5)
    ax.scatter(D['x2'], D['y2'], color='purple', s=64, marker='s', alpha=0.5)
    renderer = run_fig(fig)
    for data_no, data_dict in enumerate(renderer.plotly_fig['data']):
        equivalent, msg = compare_dict(data_dict,
                                       DOUBLE_SCATTER['data'][data_no])
        assert equivalent, msg
    equivalent, msg = compare_dict(renderer.plotly_fig['layout'],
                                   DOUBLE_SCATTER['layout'])
    assert equivalent, msg
########NEW FILE########
__FILENAME__ = test_subplots
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from . nose_tools import compare_dict, run_fig
from . data.subplots import *


def test_blank_subplots():
    fig = plt.figure()
    gs = GridSpec(4, 6)
    ax1 = fig.add_subplot(gs[0, 1])
    ax1.plot(D['x1'], D['y1'])
    fig.add_subplot(gs[1, 1])
    fig.add_subplot(gs[2:, 1])
    fig.add_subplot(gs[0, 2:])
    fig.add_subplot(gs[1:3, 2:4])
    fig.add_subplot(gs[3, 2:5])
    fig.add_subplot(gs[1:3, 4:])
    fig.add_subplot(gs[3, 5])
    gs.update(hspace=.6, wspace=.6)
    renderer = run_fig(fig)
    equivalent, msg = compare_dict(renderer.plotly_fig['layout'],
                                   BLANK_SUBPLOTS['layout'])
    assert equivalent, msg



########NEW FILE########
__FILENAME__ = bar


########NEW FILE########
__FILENAME__ = test_plot
"""
test_plot:
==========

A module intended for use with Nose.

"""
from ... graph_objs import graph_objs
from ... plotly import plotly as py
from ... import exceptions


# username for tests: 'plotlyimagetest'
# api_key for account: '786r5mecv0'

__all__ = ["Bar", "Box", "Contour", "Heatmap",
           "Histogram", "Histogram2d", "Histogram2dContour", "Scatter"]

def test_bar():
    pass


def test_box():
    pass


def test_contour():
    pass


def test_heatmap():
    pass


def test_histogram():
    pass


def test_histogram2d():
    pass


def test_histogram2dcontour():
    pass


def test_plot_scatter():
    pass
########NEW FILE########
__FILENAME__ = test_stream
"""
test_get_figure:
=================

A module intended for use with Nose.

"""
import time
from nose.tools import raises
from ... graph_objs import *
from ... plotly import plotly as py
from ... import exceptions

un = 'pythonapi'
ak = 'ubpiol2cve'
tk = 'vaia8trjjb'
fi = 461
py.sign_in(un, ak)

run_tests = False


def test_initialize_stream_plot():
    if run_tests:
        stream = Stream(token=tk, maxpoints=50)
        res = py.plot([Scatter(x=[], y=[], mode='markers', stream=stream)],
                      auto_open=False,
                      filename='stream-test')
        assert res == u'https://plot.ly/~PythonAPI/461'
        time.sleep(5)


def test_stream_single_points():
    if run_tests:
        stream = Stream(token=tk, maxpoints=50)
        res = py.plot([Scatter(x=[], y=[], mode='markers', stream=stream)],
                      auto_open=False,
                      filename='stream-test')
        time.sleep(5)
        my_stream = py.Stream(tk)
        my_stream.open()
        my_stream.write(Scatter(x=1, y=10))
        time.sleep(1)
        my_stream.close()
        fig = py.get_figure(un, fi)
        print fig.to_string()
        assert fig['data'][0]['x'] == 1
        assert fig['data'][0]['y'] == 10


def test_stream_multiple_points():
    if run_tests:
        stream = Stream(token=tk, maxpoints=50)
        res = py.plot([Scatter(x=[], y=[], mode='markers', stream=stream)],
                      auto_open=False,
                      filename='stream-test')
        time.sleep(5)
        my_stream = py.Stream(tk)
        my_stream.open()
        my_stream.write(Scatter(x=[1, 2, 3, 4], y=[2, 1, 2, 5]))
        time.sleep(1)
        my_stream.close()
        fig = py.get_figure(un, fi)
        print fig.to_string()
        assert fig['data'][0]['x'] == [1, 2, 3, 4]
        assert fig['data'][0]['y'] == [2, 1, 2, 5]


def test_stream_layout():
    if run_tests:
        stream = Stream(token=tk, maxpoints=50)
        res = py.plot([Scatter(x=[], y=[], mode='markers', stream=stream)],
                      auto_open=False,
                      filename='stream-test')
        time.sleep(5)
        title_0 = "some title i picked first"
        title_1 = "this other title i picked second"
        my_stream = py.Stream(tk)
        my_stream.open()
        my_stream.write(Scatter(x=1, y=10), layout=Layout(title=title_0))
        time.sleep(1)
        my_stream.close()
        fig = py.get_figure(un, fi)
        print fig.to_string()
        assert fig['layout']['title'] == title_0
        my_stream.open()
        my_stream.write(Scatter(x=1, y=10), layout=Layout(title=title_1))
        time.sleep(1)
        my_stream.close()
        fig = py.get_figure(un, fi)
        print fig.to_string()
        assert fig['layout']['title'] == title_1


@raises(exceptions.PlotlyError)
def test_stream_validate_data():
    if run_tests:
        my_stream = py.Stream(tk)
        my_stream.open()
        my_stream.write(dict(x=1, y=10, z=[1]))  # assumes scatter...
        time.sleep(1)
        my_stream.close()
    else:
        raise exceptions.PlotlyError()


@raises(exceptions.PlotlyError)
def test_stream_validate_layout():
    if run_tests:
        my_stream = py.Stream(tk)
        my_stream.open()
        my_stream.write(Scatter(x=1, y=10), layout=Layout(legend=True))
        time.sleep(1)
        my_stream.close()
    else:
        raise exceptions.PlotlyError()
########NEW FILE########
__FILENAME__ = test_validate
from ... import graph_objs




########NEW FILE########
__FILENAME__ = tools
# -*- coding: utf-8 -*-

"""
tools
=====

Functions that USERS will possibly want access to.

"""
import os.path
import warnings
from . graph_objs import graph_objs
from . import utils
from . import exceptions

try:
    from . import matplotlylib
    _matplotlylib_imported = True
except ImportError:
    _matplotlylib_imported = False

PLOTLY_DIR = os.path.join(os.path.expanduser("~"), ".plotly")
CREDENTIALS_FILE = os.path.join(PLOTLY_DIR, ".credentials")
# PLOT_OPTIONS_FILE = os.path.join(PLOTLY_DIR, ".plot_options")
# THEMES_FILE = os.path.join(PLOTLY_DIR, ".themes")


def ensure_local_plotly_files_exist():
    if not os.path.isdir(PLOTLY_DIR):
        os.mkdir(PLOTLY_DIR)
    for filename in [CREDENTIALS_FILE]:  # , PLOT_OPTIONS_FILE, THEMES_FILE]:
        if not os.path.exists(filename):
            f = open(filename, "w")
            f.close()


### config tools ###

# def save_plot_options_file(filename="", fileopt="",
#                       world_readable=None, auto_open=None):
#     """Set the keyword-value pairs in `~/.plotly_plot_options`.
#         TODO: the kwarg defaults are confusing - maybe should be left as a kwargs
#         TODO: should this be hiddenz?
#     """
#     ensure_local_plotly_files_exist()
#     plot_options = get_plot_options_file()
#     if (not plot_options and
#         (filename or fileopt or world_readable is not None or
#          auto_open is not None)):
#         plot_options = {}
#     if filename:
#         plot_options['filename'] = filename
#     if fileopt:
#         plot_options['fileopt'] = fileopt
#     if world_readable is not None:
#         plot_options['world_readable'] = world_readable
#     if auto_open is not None:
#         plot_options['auto_open'] = auto_open
#     utils.save_json(PLOT_OPTIONS_FILE, plot_options)
#
#
# def get_plot_options_file(*args):
#     """Return specified args from `~/.plotly_plot_options`. as dict.
#
#     Returns all if no arguments are specified.
#
#     Example:
#         get_plot_options_file('username', 'api_key')
#
#     """
#     ensure_local_plotly_files_exist()
#     options = utils.load_json(PLOT_OPTIONS_FILE, *args)
#     if len(options):
#         return {str(key): val for key, val in options.items()}
#     else:
#         return {}
#
#
# def show_plot_options_file(*args):
#     """Print specified kwargs from `~/.plotly_plot_options`.
#
#     Prints all if no keyword arguments are specified.
#
#     """
#     ensure_local_plotly_files_exist()
#     plot_options = get_plot_options_file(*args)
#     if len(args):
#         print "The specified keys from your plot options file:\n"
#     else:
#         print "Your plot options file:\n"
#     for key, val in plot_options.items():
#         print "\t{}: {}".format(key, val).expandtabs()


### credentials tools ###

def set_credentials_file(username="", api_key="", stream_ids=()):
    """Set the keyword-value pairs in `~/.plotly_credentials`.

    """
    ensure_local_plotly_files_exist()
    credentials = get_credentials_file()
    if not credentials and (username or api_key or stream_ids):
        credentials = {}
    if username:
        credentials['username'] = username
    if api_key:
        credentials['api_key'] = api_key
    if stream_ids:
        credentials['stream_ids'] = stream_ids
    utils.save_json(CREDENTIALS_FILE, credentials)


def get_credentials_file(*args):
    """Return specified args from `~/.plotly_credentials`. as dict.

    Returns all if no arguments are specified.

    Example:
        get_credentials_file('username')

    """
    ensure_local_plotly_files_exist()
    return utils.load_json(CREDENTIALS_FILE, *args)


def show_credentials_file(*args):
    """Print specified kwargs from `~/.plotly_credentials`.

    Prints all if no keyword arguments are specified.

    """
    ensure_local_plotly_files_exist()
    credentials = get_credentials_file(*args)
    if len(args):
        print "The specified keys from your credentials file:\n"
    else:
        print "Your credentials file:\n"
    for key, val in credentials.items():
        print "\t{}: {}".format(key, val).expandtabs()


### embed tools ###

def get_embed(username, plot_id, width="100%", height=525):
    padding = 25
    if isinstance(width, (int, long)):
        s = ("<iframe id=\"igraph\" scrolling=\"no\" style=\"border:none;\""
             "seamless=\"seamless\" "
             "src=\"https://plot.ly/"
             "~{username}/{plot_id}/{plot_width}/{plot_height}\" "
             "height=\"{iframe_height}\" width=\"{iframe_width}\">"
             "</iframe>").format(
            username=username, plot_id=plot_id,
            plot_width=width-padding, plot_height=height-padding,
            iframe_height=height, iframe_width=width)
    else:
        s = ("<iframe id=\"igraph\" scrolling=\"no\" style=\"border:none;\""
             "seamless=\"seamless\" "
             "src=\"https://plot.ly/"
             "~{username}/{plot_id}\" "
             "height=\"{iframe_height}\" width=\"{iframe_width}\">"
             "</iframe>").format(
            username=username, plot_id=plot_id,
            iframe_height=height, iframe_width=width)

    return s


def embed(username, plot_id, width="100%", height=525):
    s = get_embed(username, plot_id, width, height)
    try:
        # see if we are in the SageMath Cloud
        from sage_salvus import html
        return html(s, hide=False)
    except:
        pass
    try:
        from IPython.display import HTML, display
        display(HTML(s))
    except:
        pass


### mpl-related tools ###

def mpl_to_plotly(fig, resize=False, strip_style=False, verbose=False):
    """Convert a matplotlib figure to plotly dictionary and send.

    All available information about matplotlib visualizations are stored
    within a matplotlib.figure.Figure object. You can create a plot in python
    using matplotlib, store the figure object, and then pass this object to
    the fig_to_plotly function. In the background, mplexporter is used to
    crawl through the mpl figure object for appropriate information. This
    information is then systematically sent to the PlotlyRenderer which
    creates the JSON structure used to make plotly visualizations. Finally,
    these dictionaries are sent to plotly and your browser should open up a
    new tab for viewing! Optionally, if you're working in IPython, you can
    set notebook=True and the PlotlyRenderer will call plotly.iplot instead
    of plotly.plot to have the graph appear directly in the IPython notebook.

    Note, this function gives the user access to a simple, one-line way to
    render an mpl figure in plotly. If you need to trouble shoot, you can do
    this step manually by NOT running this fuction and entereing the following:

    ============================================================================
    from mplexporter import Exporter
    from mplexporter.renderers import PlotlyRenderer

    # create an mpl figure and store it under a varialble 'fig'

    renderer = PlotlyRenderer()
    exporter = Exporter(renderer)
    exporter.run(fig)
    ============================================================================

    You can then inspect the JSON structures by accessing these:

    renderer.layout -- a plotly layout dictionary
    renderer.data -- a list of plotly data dictionaries

    Positional arguments:
    fig -- a matplotlib figure object
    username -- a valid plotly username **
    api_key -- a valid api_key for the above username **
    notebook -- an option for use with an IPython notebook

    ** Don't have a username/api_key? Try looking here:
    https://plot.ly/plot

    ** Forgot your api_key? Try signing in and looking here:
    https://plot.ly/api/python/getting-started

    """
    if _matplotlylib_imported:
        renderer = matplotlylib.PlotlyRenderer()
        matplotlylib.Exporter(renderer).run(fig)
        if resize:
            renderer.resize()
        if strip_style:
            renderer.strip_style()
        if verbose:
            print renderer.msg
        return renderer.plotly_fig
    else:
        warnings.warn(
            "To use Plotly's matplotlylib functionality, you'll need to have "
            "matplotlib successfully installed with all of its dependencies. "
            "You're getting this error because matplotlib or one of its "
            "dependencies doesn't seem to be installed correctly.")


### graph_objs related tools ###

# TODO: Scale spacing based on number of plots and figure size
def get_subplots(rows=1, columns=1, horizontal_spacing=0.1,
                 vertical_spacing=0.15, print_grid=False):
    """Return a dictionary instance with the subplots set in 'layout'.

    Example 1:
        # stack two subplots vertically
        fig = tools.get_subplots(rows=2)
        fig['data'] += [Scatter(x=[1,2,3], y=[2,1,2], xaxis='x1', yaxis='y1')]
        fig['data'] += [Scatter(x=[1,2,3], y=[2,1,2], xaxis='x2', yaxis='y2')]

    Example 2:
        # print out string showing the subplot grid you've put in the layout
        fig = tools.get_subplots(rows=3, columns=2, print_grid=True)

    key (types, default=default):
        description.

    rows (int, default=1):
        Number of rows, evenly spaced vertically on the figure.

    columns (int, default=1):
        Number of columns, evenly spaced horizontally on the figure.

    horizontal_spacing (float in [0,1], default=0.1):
        Space between subplot columns. Applied to all columns.

    vertical_spacing (float in [0,1], default=0.05):
        Space between subplot rows. Applied to all rows.

    print_grid (True | False, default=False):
        If True, prints a tab-delimited string representation of your plot grid.

    """
    fig = dict(layout=graph_objs.Layout())  # will return this at the end
    plot_width = (1 - horizontal_spacing * (columns - 1)) / columns
    plot_height = (1 - vertical_spacing * (rows - 1)) / rows
    plot_num = 0
    for rrr in range(rows):
        for ccc in range(columns):
            xaxis_name = 'xaxis{}'.format(plot_num + 1)
            x_anchor = 'y{}'.format(plot_num + 1)
            x_start = (plot_width + horizontal_spacing) * ccc
            x_end = x_start + plot_width

            yaxis_name = 'yaxis{}'.format(plot_num + 1)
            y_anchor = 'x{}'.format(plot_num + 1)
            y_start = (plot_height + vertical_spacing) * rrr
            y_end = y_start + plot_height

            xaxis = graph_objs.XAxis(domain=[x_start, x_end], anchor=x_anchor)
            fig['layout'][xaxis_name] = xaxis
            yaxis = graph_objs.YAxis(domain=[y_start, y_end], anchor=y_anchor)
            fig['layout'][yaxis_name] = yaxis
            plot_num += 1
    if print_grid:
        print "This is the format of your plot grid!"
        grid_string = ""
        plot = 1
        for rrr in range(rows):
            grid_line = ""
            for ccc in range(columns):
                grid_line += "[{}]\t".format(plot)
                plot += 1
            grid_string = grid_line + '\n' + grid_string
        print grid_string
    return graph_objs.Figure(fig)  # forces us to validate what we just did...


def get_valid_graph_obj(obj, obj_type=None):
    """Returns a new graph object that is guaranteed to pass validate().

    CAREFUL: this will *silently* strip out invalid pieces of the object.

    """
    try:
        new_obj = graph_objs.NAME_TO_CLASS[obj.__class__.__name__]()
    except KeyError:
        try:
            new_obj = graph_objs.NAME_TO_CLASS[obj_type]()
        except KeyError:
            raise exceptions.PlotlyError(
                "'{}' nor '{}' are recognizable graph_objs.".
                format(obj.__class__.__name__, obj_type))
    if isinstance(new_obj, list):
        new_obj += obj
    else:
        for key, val in obj.items():
            new_obj[key] = val
    new_obj.force_clean()
    return new_obj


def validate(obj, obj_type):
    """Validate a dictionary, list, or graph object as 'obj_type'.

    This will not alter the 'obj' referenced in the call signature. It will
    raise an error if the 'obj' reference could not be instantiated as a
    valid 'obj_type' graph object.

    """
    try:
        obj_type = graph_objs.KEY_TO_NAME[obj_type]
    except KeyError:
        pass
    try:
        test_obj = graph_objs.NAME_TO_CLASS[obj_type](obj)
    except KeyError:
        raise exceptions.PlotlyError(
            "'{}' is not a recognizable graph_obj.".
            format(obj_type))


def validate_stream(obj, obj_type):
    """Validate a data dictionary (only) for use with streaming.

    An error is raised if a key within (or nested within) is not streamable.
    
    """
    try:
        obj_type = graph_objs.KEY_TO_NAME[obj_type]
    except KeyError:
        pass
    info = graph_objs.INFO[graph_objs.NAME_TO_KEY[obj_type]]
    for key, val in obj.items():
        if key == 'type':
            continue
        if 'streamable' in info[key]:
            if not info[key]['streamable']:
                raise exceptions.PlotlyError(
                    "The '{}' key is not streamable in the '{}' object".format(
                        key, obj_type
                    )
                )
        else:
            raise exceptions.PlotlyError(
                "The '{}' key is not streamable in the '{}' object".format(
                    key, obj_type
                )
            )
        try:
            sub_obj_type = graph_objs.KEY_TO_NAME[key]
            validate_stream(val, sub_obj_type)
        except KeyError:
            pass
########NEW FILE########
__FILENAME__ = utils
"""
utils
=====

Low-level functionality NOT intended for users to EVER use.

"""

import json
import os.path


### general file setup tools ###

def load_json(filename, *args):
    if os.path.getsize(filename) > 0:
        with open(filename, "r") as f:
            try:
                data = json.load(f)
            except:
                # TODO: issue a warning and bubble it up
                data = ""
    else:
        data = ""
    if len(args) and data:
        return {key: data[key] for key in args}
    else:
        return data


def save_json(filename, json_obj):
    with open(filename, "w") as f:
        f.write(json.dumps(json_obj, indent=4))


### Custom JSON encoders ###
class _plotlyJSONEncoder(json.JSONEncoder):
    def numpyJSONEncoder(self, obj):
        try:
            import numpy
            if type(obj).__module__.split('.')[0] == numpy.__name__:
                l = obj.tolist()
                d = self.datetimeJSONEncoder(l)
                return d if d is not None else l
        except:
            pass
        return None

    def datetimeJSONEncoder(self, obj):
        # if datetime or iterable of datetimes, convert to a string that plotly understands
        # format as %Y-%m-%d %H:%M:%S.%f, %Y-%m-%d %H:%M:%S, or %Y-%m-%d depending on what non-zero resolution was provided
        import datetime
        try:
            if isinstance(obj, (datetime.datetime, datetime.date)):
                if obj.microsecond != 0:
                    return obj.strftime('%Y-%m-%d %H:%M:%S.%f')
                elif obj.second != 0 or obj.minute != 0 or obj.hour != 0:
                    return obj.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    return obj.strftime('%Y-%m-%d')
            elif isinstance(obj[0], (datetime.datetime, datetime.date)):
                return [o.strftime(
                        '%Y-%m-%d %H:%M:%S.%f') if o.microsecond != 0 else
                        o.strftime('%Y-%m-%d %H:%M:%S') if o.second != 0 or o.minute != 0 or o.hour != 0 else
                        o.strftime('%Y-%m-%d')
                        for o in obj]
        except:
            pass
        return None

    def pandasJSONEncoder(self, obj):
        try:
            import pandas
            if isinstance(obj, pandas.Series):
                return obj.tolist()
        except:
            pass
        return None

    def sageJSONEncoder(self, obj):
        try:
            from sage.all import RR, ZZ
            if obj in RR:
                return float(obj)
            elif obj in ZZ:
                return int(obj)
        except:
            pass
        return None

    def default(self, obj):
        try:
            return json.dumps(obj)
        except TypeError as e:
            encoders = (self.datetimeJSONEncoder, self.numpyJSONEncoder,
                        self.pandasJSONEncoder, self.sageJSONEncoder)
            for encoder in encoders:
                s = encoder(obj)
                if s is not None:
                    return s
            raise e
        return json.JSONEncoder.default(self, obj)


### unicode stuff ###

def decode_unicode(coll):
    if isinstance(coll, list):
        for no, entry in enumerate(coll):
            if isinstance(entry, (dict, list)):
                coll[no] = decode_unicode(entry)
            else:
                if isinstance(entry, unicode):
                    try:
                        coll[no] = str(entry)
                    except UnicodeEncodeError:
                        pass
    elif isinstance(coll, dict):
        keys, vals = coll.keys(), coll.values()
        for key, val in zip(keys, vals):
            if isinstance(val, (dict, list)):
                coll[key] = decode_unicode(val)
            elif isinstance(val, unicode):
                try:
                    coll[key] = str(val)
                except UnicodeEncodeError:
                    pass
            coll[str(key)] = coll.pop(key)
    return coll
########NEW FILE########
__FILENAME__ = version
__version__ = '1.0.20'

########NEW FILE########
