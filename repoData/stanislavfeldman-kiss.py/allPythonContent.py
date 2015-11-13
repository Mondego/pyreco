__FILENAME__ = auth
from kiss.views.templates import TemplateResponse
from kiss.views.core import RedirectResponse
from kiss.controllers.core import Controller
import requests
import json
from werkzeug.urls import url_decode
from putils.types import Dict, Regex
from putils.patterns import Singleton
from urlparse import urljoin
from werkzeug.urls import url_encode
	
	
class AuthBackend(object):
	"""
	Base oauth backend
	"""
	def get_code_url(self, request, options):
		params = {
			"client_id": options["client_id"],
			"redirect_uri": options["redirect_uri"],
			"scope": options["scope"],
			"response_type": "code",
			"approval_prompt": "force",
			"access_type": "offline"
		}
		return "%s?%s" % (options["authorization_uri"], url_encode(params))
		
	def get_access_token(self, request, options):
		params = {
			"client_id": options["client_id"],
			"client_secret": options["client_secret"],
			"grant_type": "authorization_code",
			"code": request.args["code"],
			"redirect_uri": options["redirect_uri"]
		}
		response = requests.post(options["get_token_uri"], params).text
		return self.prepare_access_token_response(response)
		
	def prepare_access_token_response(self, response):
		return json.loads(response)
		
	def get_user_info(self, request, options, access_token_result):
		self.access_token = access_token_result["access_token"]
		params = self.prepare_user_info_request_params(access_token_result)
		user_info_response = json.loads(requests.get("%s?%s" % (options["target_uri"], url_encode(params)), auth=self.auth).text)
		user_info_response = self.process_user_info_response(request, user_info_response)
		user_info_response["provider"] = request.params["backend"]
		user_info_response["access_token"] = params["access_token"]
		return user_info_response
				
	def prepare_user_info_request_params(self, access_token_result):
		return {"access_token": access_token_result["access_token"]}
		
	def process_user_info_response(self, request, user_info_response):
		result = {}
		result["id"] = user_info_response["id"]
		return result
		
	def auth(self, request):
		request.headers["Authorization"] = "Bearer %s" % self.access_token
		return request

		
class GoogleAuthBackend(AuthBackend):
	def process_user_info_response(self, request, user_info_response):
		result = {}
		result["id"] = user_info_response["id"]
		result["email"] = user_info_response["email"]
		result["name"] = user_info_response["name"]
		return result

	
class VkAuthBackend(AuthBackend):
	def prepare_user_info_request_params(self, access_token_result):
		return {"access_token": access_token_result["access_token"], "uids": access_token_result["user_id"], "fields": "uid, first_name, last_name, nickname, screen_name, sex, bdate, city, country, photo, photo_medium, photo_big"}
		
	def process_user_info_response(self, request, user_info_response):
		result = {}
		user_info_response = user_info_response["response"][0]
		result["id"] = user_info_response["uid"]
		result["name"] = "%s %s" % (user_info_response["first_name"], user_info_response["last_name"])
		return result

	
class FacebookAuthBackend(AuthBackend):
	def prepare_access_token_response(self, response):
		return url_decode(response)
		
	def process_user_info_response(self, request, user_info_response):
		result = {}
		result["id"] = user_info_response["id"]
		result["email"] = user_info_response["email"]
		result["name"] = user_info_response["name"]
		return result
		

class YandexAuthBackend(AuthBackend):	
	def process_user_info_response(self, request, user_info_response):
		result = {}
		result["id"] = user_info_response["id"]
		result["email"] = user_info_response["default_email"]
		result["name"] = user_info_response["real_name"]
		return result


class AuthManager(Singleton):
	"""
	Auth manager which calls appropriate backend
	"""	
	def __init__(self, opts):
		self.options = {
			"common": {
				"base_uri": "http://localhost:8080/auth/",
				"success_uri": "success/",
				"error_uri": "error/"
			},
			"google": {
				"authorization_uri": "https://accounts.google.com/o/oauth2/auth",
				"scope": "https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email",
				"get_token_uri": "https://accounts.google.com/o/oauth2/token",
				"redirect_uri": "google/callback",
				"target_uri": "https://www.googleapis.com/oauth2/v1/userinfo",
				"backend": GoogleAuthBackend()
			},
			"vk": {
				"authorization_uri": "http://api.vk.com/oauth/authorize",
				"scope": "",
				"get_token_uri": "https://api.vk.com/oauth/token",
				"redirect_uri": "vk/callback",
				"target_uri": "https://api.vk.com/method/users.get",
				"backend": VkAuthBackend()
			},
			"facebook": {
				"authorization_uri": "https://www.facebook.com/dialog/oauth",
				"scope": "email",
				"get_token_uri": "https://graph.facebook.com/oauth/access_token",
				"redirect_uri": "facebook/callback",
				"target_uri": "https://graph.facebook.com/me",
				"backend": FacebookAuthBackend()
			},
			"yandex": {
				"authorization_uri": "https://oauth.yandex.ru/authorize",
				"scope": "",
				"get_token_uri": "https://oauth.yandex.ru/token",
				"redirect_uri": "yandex/callback",
				"target_uri": "https://login.yandex.ru/info",
				"backend": YandexAuthBackend()
			}
		}
		self.options = Dict.merge(self.options, opts)
		base_uri = self.options["common"]["base_uri"]
		self.options["common"]["success_uri"] = urljoin(base_uri, self.options["common"]["success_uri"])
		self.options["common"]["error_uri"] = urljoin(base_uri, self.options["common"]["error_uri"])
		for backend, params in self.options.items():
			if "redirect_uri" in params:
				params["redirect_uri"] = urljoin(base_uri, params["redirect_uri"])
				
	def get_provider_url(self, request):
		current_options = self.options[request.params["backend"]]
		return current_options["backend"].get_code_url(request, current_options)
			
	def get_result_url(self, request):
		current_options = self.options[request.params["backend"]]
		access_token_result = current_options["backend"].get_access_token(request, current_options)
		if "access_token" not in access_token_result or not access_token_result["access_token"]:
			return self.options["common"]["error_uri"]
		user_info_response = current_options["backend"].get_user_info(request, current_options, access_token_result)
		return "%s?%s" % (self.options["common"]["success_uri"], url_encode(user_info_response))
		
class AuthController(object):
	"""
	Controller for social auth, use it in your url mappings
	"""
	def __new__(cls, opts):
		AuthManager(opts)
		return {
			Regex.string_url_regex("backend"): {
				"": StartAuthController,
				"callback": EndAuthController,
			}
		}

	
class StartAuthController(Controller):
	"""
	Controller which starts oauth flow.
	"""
	def get(self, request):
		if "success_uri" in request.args:
			AuthManager().options["common"]["success_uri"] = request.args["success_uri"]
		if "error_uri" in request.args:
			AuthManager().options["common"]["error_uri"] = request.args["error_uri"]
		return RedirectResponse(AuthManager().get_provider_url(request))
		

class EndAuthController(Controller):
	"""
	Controller which finishes oauth flow.
	"""
	def get(self, request):
		return RedirectResponse(AuthManager().get_result_url(request))


########NEW FILE########
__FILENAME__ = core
from putils.patterns import Singleton
from kiss.views.core import Response


class Controller(object):
	"""
	Base class of all controllers.
	"""
	def get(self, request):
		return Response("Method is not supported", status=405)
		
	def post(self, request):
		return Response("Method is not supported", status=405)
		
	def put(self, request):
		return Response("Method is not supported", status=405)
		
	def delete(self, request):
		return Response("Method is not supported", status=405)



########NEW FILE########
__FILENAME__ = page
from core import Controller
from kiss.views.templates import TemplateResponse

class PageController(Controller):
	"""
	If you need just to show page, create PageController and pass to it your page and optional context.
	Use it like another controllers in urls settings of your app.
	"""
	def __init__(self, page, context={}):
		self.page = page
		self.context = context
		
	def get(self, request):
		self.context["request"] = request
		return TemplateResponse(self.page, self.context)

########NEW FILE########
__FILENAME__ = rest
from core import Controller
from kiss.views.core import JsonResponse

class RestController(object):
	"""
	Controller that creates REST API to your model.
	Pass model class to it and use url property and controller property in your urls settings.
	"""
	def __init__(self, model, id_regex=r"""(?P<id>\d+)"""):
		self.model = model
		self.id_regex = id_regex
		
	@property
	def url(self):
		return self.model.__name__.lower()
		
	@property
	def controller(self):
		return {
			"": RestListController(self.model),
			self.id_regex: RestShowController(self.model)
		}
	
	
def request_params_to_dict(params):
	result = {}
	for k,v in params.items():
		result[k] = v
	return result
	

class RestListController(Controller):
	def __init__(self, model):
		self.model = model
			
	def get(self, request):
		results = self.model.select()
		return JsonResponse(results)
	
	def post(self, request):
		result = self.model.create(**request_params_to_dict(request.form))
		return JsonResponse({"id": result.id}, status=201)

			
class RestShowController(Controller):
	def __init__(self, model):
		self.model = model
		
	def get(self, request):
		result = self.model.get(id=request.params["id"])
		return JsonResponse(result)
		
	def put(self, request):
		id = request.params["id"]
		self.model.update(**request_params_to_dict(request.form)).where(id=id).execute()
		return JsonResponse({"id": id})
	
	def delete(self, request):
		result = self.model.get(id=request.params["id"])
		result.delete_instance(recursive=True)
		return JsonResponse({"result": "ok"}, status=204)

########NEW FILE########
__FILENAME__ = router
from jinja2 import Environment, PackageLoader, ChoiceLoader
import re
from kiss.controllers.core import Controller
from putils.patterns import Singleton
from putils.types import Dict
from kiss.views.core import *
from kiss.core.events import Eventer
import traceback
import inspect
import logging


class Router(Singleton):
	"""
	Router implements unique hierarchical url mapping.
	Pass dictionary with mapping of regex and controller.
	"""
	def __init__(self, options):
		self.options = options
		self.logger = logging.getLogger(__name__)
		self.eventer = Eventer()
		self.add_urls(self.options["urls"], False)
		if "templates_path" in self.options["views"]:
			tps = []
			for tp in self.options["views"]["templates_path"]:
				tps.append(PackageLoader(tp, ""))
			self.options["views"]["templates_environment"] = Environment(loader=ChoiceLoader(tps), extensions=self.options["views"]["templates_extensions"])
			
	def add_urls(self, urls, merge=True):
		urls = Dict.flat_dict(urls)
		new_urls = []
		for k, v in urls.iteritems():
			if k[len(k)-2] == "/":
				k = k[:len(k)-2] + k[len(k)-1]
			k = re.compile(k)
			if inspect.isclass(v):
				new_urls.append((k, v()))
			else:
				new_urls.append((k,v))
		if merge:
			self.options["urls"] = self.options["urls"] + new_urls
		else:
			self.options["urls"] = new_urls
		
	def route(self, request):
		for (re_url, controller) in self.options["urls"]:
			path = request.path.lower()
			if path[len(path)-1] == "/":
				path = path.rstrip('/')
			mtch = re_url.match(path)
			if mtch:
				request.params = mtch.groupdict()
				try:
					self.eventer.publish("BeforeControllerAction", request)
					#check if controller has method for all requests
					if hasattr(controller, "process") and inspect.ismethod(getattr(controller, "process")):
						action = getattr(controller, "process")
					else:
						action = getattr(controller, request.method.lower())
					response = action(request)
					self.eventer.publish("AfterControllerAction", request, response)
					if not response:
						break
					log_code = 0
					if hasattr(response, "status_code"):
						log_code = response.status_code
					else:
						log_code = response.code
					self.logger.info(Router.format_log(request, log_code))
					return response
				except HTTPException, e:
					response = self.get_err_page(e)
					self.logger.warning(Router.format_log(request, response.code, str(e)), exc_info=True)
					return response
				except Exception, e:
					response = self.get_err_page(InternalServerError(description=traceback.format_exc()))
					self.logger.error(Router.format_log(request, response.code, str(e)), exc_info=True)
					return response
		response = self.get_err_page(NotFound(description="Not found %s" % request.url))
		self.logger.warning(Router.format_log(request, response.code))
		return response
		
	def get_err_page(self, err):
		err_page = self.eventer.publish_and_get_result(err.code, err)
		if err_page:
			return err_page
		return err

	@staticmethod
	def format_log(request, status_code, msg=None):
		addr = request.remote_addr
		provided_ips = request.access_route
		if provided_ips and len(provided_ips) > 0:
			addr = provided_ips[0]
		result = '%d %s %s <- %s %s' % (status_code, request.method, request.url, addr, request.headers['User-Agent'])
		if msg:
			result = "%s %s" % (msg, result)
		return result

########NEW FILE########
__FILENAME__ = application
import gevent
import signal
from gevent import monkey; monkey.patch_all()
from gevent.wsgi import WSGIServer
from putils.patterns import Singleton
from putils.dynamics import Importer, Introspector
from putils.types import Dict
from kiss.controllers.router import Router
from kiss.views.core import Request, Response
from beaker.middleware import SessionMiddleware
from werkzeug.wsgi import SharedDataMiddleware
from kiss.views.static import StaticBuilder
from kiss.views.core import Templater
from kiss.models import metadata
import logging
from kiss.core.events import Eventer


class Application(Singleton):
	"""
	Main class of your application.
	Pass options to constructor and all subsystems(eventer, router) will be configured.
	"""
	def __init__(self, options):
		self.init_options(options)
		self.init_eventer()
		self.init_router()
		self.init_templater()
		self.eventer.publish("BeforeDatabaseEngineConfiguration", self)
		self.init_db()
		self.eventer.publish("AfterDatabaseEngineConfiguration", self)
		self.init_session()
		self.eventer.publish("BeforeInitStatic", self)
		self.init_static()
		self.eventer.publish("AfterInitStatic", self)
		self.eventer.publish("BeforeInitServer", self)
		self.init_server()
		self.eventer.publish("AfterInitServer", self)
		self.eventer.publish("BeforeApplicationStarted", self)
	
	def init_options(self, options):
		logging.basicConfig(level=logging.CRITICAL)
		default_options = {
			"application": {
				"address": "127.0.0.1",
				"port": 8080,
			    "system": {
				    "log": None
			    }
			},
			"urls": {},
			"views": {
				"templates_path": [],
				"templates_extensions": ["compressinja.html.HtmlCompressor", "jinja2.ext.i18n"],
				"static_path": [],
				"static_not_compile": [],
				"static_build": True,
				'session_type': "cookie",
				"session_auto": True,
				'session_cookie_expires': True,
				'session_encrypt_key':'sldk24j0jf09w0jfg24',
				'session_validate_key':';l[pfghopkqeq1234,fs'
			},
			"events": {}
		}
		self.options = Dict.merge(default_options, options)
		
	def init_eventer(self):
		self.eventer = Eventer(self.options["events"])
		
	def init_router(self):
		self.router = Router(self.options)
		
	def init_templater(self):
		self.templater = Templater(self)
		
	def init_static(self):
		static_builder = None
		self.add_static(self.options["views"]["static_path"], not_compile=self.options["views"]["static_not_compile"], merge=False, build=self.options["views"]["static_build"])
		
	def add_static(self, sps, not_compile=[], url_path="/", merge=True, build=True):
		static_path = []
		for sp in sps:
			try:
				sp = Importer.module_path(sp)
			except:
				pass
			try:
				static_path.append(sp)
				static_builder = StaticBuilder(sp, not_compile)
				if build:
					static_builder.build()
				if build:
					self.wsgi_app = SharedDataMiddleware(self.wsgi_app, {url_path : sp + "/build"}, cache=False)
				else:
					self.wsgi_app = SharedDataMiddleware(self.wsgi_app, {url_path : sp}, cache=False)
			except:
				pass
		if merge:
			self.options["views"]["static_path"] = self.options["views"]["static_path"] + static_path
		else:
			self.options["views"]["static_path"] = static_path
			
	def init_db(self):
		if "models" in self.options:
			metadata.bind = self.options["models"]["connection"]
			metadata.bind.echo = False
		
	def init_session(self):
		session_options = {
			'session.type': self.options["views"]['session_type'],
			"session.auto": self.options["views"]["session_auto"],
			'session.cookie_expires': self.options["views"]['session_cookie_expires'],
			'session.encrypt_key': self.options["views"]['session_encrypt_key'],
			'session.validate_key': self.options["views"]['session_validate_key']
		}
		self.wsgi_app = SessionMiddleware(self.wsgi_app, session_options, environ_key="session")
			
	def init_server(self):
		#kwargs = dict(filter(lambda item: item[0] not in ["address", "port"], self.options["application"].iteritems()))
		kwargs = {}
		if "system" in self.options["application"]:
			kwargs = self.options["application"]["system"]
		self.server = WSGIServer((self.options["application"]["address"], self.options["application"]["port"]), self.wsgi_app, **kwargs)
			
	def wsgi_app(self, options, start_response):
		request = Request(options)
		response = self.router.route(request)
		return response(options, start_response)
	
	def start(self):
		gevent.signal(signal.SIGTERM, self.stop)
		gevent.signal(signal.SIGINT, self.stop)
		self.eventer.publish("ApplicationStarted", self)
		self.server.serve_forever()
		
	def start_no_wait(self):
		self.eventer.publish("ApplicationStarted", self)
		self.server.start()
		
	def stop(self):
		self.eventer.publish("ApplicationStopped", self)
		self.server.stop()


########NEW FILE########
__FILENAME__ = events
from pev import Eventer
"""
ApplicationStarted = 0

Event when application is started	

ApplicationStopped = 1
Event when application is stopped

BeforeDatabaseEngineConfiguration = 2
AfterDatabaseEngineConfiguration = 3
BeforeInitStatic = 4
AfterInitStatic = 5
BeforeApplicationStarted = 6
BeforeInitServer = 7
AfterInitServer = 8

BeforeControllerAction = 2
Event before controller action will be executed.
You can change Request object before it will pass to controller action.

AfterControllerAction = 3
Event after controller action was executed.
You can change Response object before rendering.
"""

########NEW FILE########
__FILENAME__ = core
import werkzeug.wrappers
from werkzeug.exceptions import *
from werkzeug.utils import cached_property
from werkzeug.utils import redirect
import jsonpickle
from putils.patterns import Singleton
from putils.dynamics import Importer
from jinja2 import Environment, PackageLoader, PrefixLoader, FileSystemLoader, ChoiceLoader
import gettext


class Templater(Singleton):
	def __init__(self, app):
		self.app = app
		self.options = app.options
		if "templates_path" in self.options["views"]:
			self.add_template_paths(self.options["views"]["templates_path"])
			if "translations" in self.options["views"]:
				self.add_translation_paths(self.options["views"]["translations"])
			if "templates_filters" in self.options["views"]:
				for name, func in self.options["views"]["templates_filters"].iteritems():
					self.app.templates_environment.filters[name] = func
			
	def add_template_paths(self, paths, prefix=""):
		tps = []
		for tp in paths:
			loader = None
			try:
				if Importer.module_path(tp): #if it module path
					loader = PackageLoader(tp, "")
			except:
				loader = FileSystemLoader(tp)
			if loader:
				if prefix:
					tps.append(PrefixLoader({prefix: loader}))
				else:
					tps.append(loader)
		if hasattr(self.app, "templates_environment"):
			for tl in tps:
				self.app.templates_environment.loader.loaders.append(tl)
		else:
			self.app.templates_environment = Environment(loader=ChoiceLoader(tps), extensions=self.options["views"]["templates_extensions"])
			
	def add_translation_paths(self, paths):
		if not paths:
			return
		for tr_path in paths:
			try:
				tr_path = Importer.module_path(tr_path)
			except:
				pass
			try:
				self.app.templates_environment.install_gettext_translations(gettext.translation("messages", tr_path, codeset="UTF-8"))
				gettext.install("messages", tr_path, codeset="UTF-8")
			except:
				pass


class Request(werkzeug.wrappers.Request):
	"""
	Base request object inhereted from werkzeug Request.
	Added session object.
	"""
	def __init__(self, options, **argw):
		super(Request, self).__init__(options, **argw)
	
	@cached_property
	def session(self):
		return self.environ["session"]


class Response(werkzeug.wrappers.Response):
	"""
	Base response object inhereted from werkzeug Response.
	Text/html mimetype is default.
	"""
	def __init__(self, text, **argw):
		if "mimetype" not in argw:
			argw["mimetype"] = "text/html"
		super(Response, self).__init__(text, **argw)


class RedirectResponse(werkzeug.wrappers.Response):
	"""
	Response for redirect. Pass path and server will do 302 request.
	"""
	def __new__(cls, path):
		return redirect(path)
		
		
class JsonResponse(Response):
	"""
	Json response. Pass any object you want, JsonResponse converts it to json.
	"""
	def __init__(self, inp, **argw):
		json_str = jsonpickle.encode(inp, unpicklable=False)
		super(JsonResponse, self).__init__(json_str, mimetype="application/json", **argw)

########NEW FILE########
__FILENAME__ = static
from putils.patterns import Singleton
from putils.filesystem import Dir
import mimetypes
import scss
from scss import Scss
from jsmin import jsmin
import os
import shutil


class StaticCompiler(object):
	"""
	Static files minifier.
	"""
	def __init__(self, path):
		self.css_parser = Scss()
		scss.LOAD_PATHS = path
		
	def compile_file(self, filepath, need_compilation=True):
		result = self.get_content(filepath)
		if need_compilation:
			mimetype = mimetypes.guess_type(filepath)[0]
			result = self.compile_text(result, mimetype)
		return result
		
	def compile_text(self, text, mimetype):
		result = ""
		if mimetype == "text/css":
			result = self.css_parser.compile(text)
		elif mimetype == "application/javascript":
			result = jsmin(text)
		else:
			result = text
		return result
		
	def get_content(self, file):
		return open(file).read()


class StaticBuilder(object):
	"""
	Uses StaticCompiler to minify and compile js and css.
	"""
	def __init__(self, path, static_not_compile):
		self.path = path
		self.static_not_compile = static_not_compile
		self.compiler = StaticCompiler(self.path)
		
	def build(self):
		try:
			shutil.rmtree(self.path + "/build")
		except:
			pass
		try:
			Dir.walk(self.path, self.build_file)
		except:
			pass
		
	def build_file(self, file):
		rel_path = file.replace(self.path, "")
		need_compilation = True
		if rel_path in self.static_not_compile:
			need_compilation = False
		new_path = self.path + "/build" + rel_path
		result = self.compiler.compile_file(file, need_compilation=need_compilation)
		if result:
			try:
				os.makedirs(os.path.dirname(new_path))
			except:
				pass
			with open(new_path, "w") as f:
				f.write(result)

########NEW FILE########
__FILENAME__ = templates
from kiss.views.core import Response
from kiss.core.application import Application


class Template(object):
	@staticmethod
	def text_by_path(path, context={}):
		return Application().templates_environment.get_template(path).render(context)
		
	@staticmethod
	def text_by_text(text, context={}):
		return Application().templates_environment.from_string(text).render(context)
		

class TemplateResponse(Response):
	"""
	Template response via Jinja2. Pass template path and context.
	"""
	def __init__(self, path, context={}, **argw):
		super(TemplateResponse, self).__init__(Template.text_by_path(path, context), **argw)
		
				
class TextResponse(Response):
	def __init__(self, text, context={}, **argw):
		super(TextResponse, self).__init__(Template.text_by_text(text, context), **argw)

########NEW FILE########
__FILENAME__ = auth
from kiss.views.templates import TemplateResponse
from kiss.controllers.core import Controller

class AuthPageController(Controller):
	def get(self, request):
		return TemplateResponse("auth_page.html")
		

class AuthSuccessController(Controller):
	def get(self, request):
		return TemplateResponse("auth_result.html", {"result": request.args})


########NEW FILE########
__FILENAME__ = controller1
from kiss.views.core import Response
from kiss.controllers.core import Controller


class Controller1:
	def get(self, request):
		return Response("<h1>hello first response!</h1>")
		

########NEW FILE########
__FILENAME__ = controller2
from kiss.views.templates import TemplateResponse
from kiss.views.core import Response
from kiss.core.events import Eventer
from models.models import Blog, Entry
import datetime
from kiss.controllers.core import Controller
from kiss.models import setup_all, drop_all, create_all, session

	
class Controller2(Controller):
	def get(self, request):
		#publish some event
		eventer = Eventer()
		eventer.publish("some event", self)
		if not "foo" in request.session:
			request.session["foo"] = 0
		request.session["foo"] += 1
		blog = Blog(name="super blog", creator="Stas")
		if not Entry.get_by(title="super post"):
			entry = Entry(title="super post", body="saifjo", blog=blog)
		session.commit()
		print Entry.query.all()
		return TemplateResponse("view.html", {
			"foo": request.session["foo"], 
			"users": [{"url": "google.com", "username": "brin"}],
			"blog": blog
		})
		
	#on load handler via eventer
	def application_after_load(self, application):
		setup_all()
		drop_all()
		create_all()
		print "app loaded"
		
	def internal_server_error(self, request):
		return Response("<h1>error: %s</h1>" % request.description)

########NEW FILE########
__FILENAME__ = models
from kiss.models import Entity, Field, Unicode, UnicodeText, OneToMany, ManyToOne


class Blog(Entity):
	creator = Field(Unicode)
	name = Field(Unicode)
	entries = OneToMany("Entry")


class Entry(Entity):
	title = Field(Unicode)
	body = Field(UnicodeText)
	blog = ManyToOne("Blog")

########NEW FILE########
__FILENAME__ = settings
from os import path
current_dir = path.dirname(path.abspath(__file__))
import sys
sys.path.append(path.join(current_dir, "../../kiss.py"))
sys.path.append(path.join(current_dir, "../../compressinja/"))
sys.path.append(path.join(current_dir, "../../putils/"))
sys.path.append(path.join(current_dir, "../../pev/"))
from kiss.core.application import Application
from controllers.controller1 import Controller1
from controllers.controller2 import Controller2
from kiss.core.exceptions import InternalServerError
from kiss.controllers.page import PageController
from kiss.controllers.rest import RestController
from kiss.controllers.auth import AuthController
from models.models import Blog
from controllers.auth import AuthPageController, AuthSuccessController


options = {
	"application": {
		"address": "127.0.0.1",
		"port": 8080
	},
	"urls": {
		"": Controller1,
		"users": {
			"(?P<user>\w+)": Controller2
		},
		"2": {
			"3": Controller1(),
			"4": Controller2
		},
		"3": PageController("static_view.html", {"foo": "bar"}),
		RestController(Blog).url: RestController(Blog).controller,
		"auth": AuthController({
			"common": {
				"base_uri": "http://test.com:8080/auth/",
				"success_uri": "/authsuccess/"
			},
			"google": {
				"client_id": "691519038986.apps.googleusercontent.com",
				"client_secret": "UsLDDLu-1ry8IgY88zy6qNiU"
			},
			"vk": {
				"client_id": "2378631",
				"client_secret": "oX5geATcgJgWbkfImli9"
			},
			"facebook": {
				"client_id": "485249151491568",
				"client_secret": "66f2503d9806104dd47fca55a6fbbac3"
			},
			"yandex": {
				"client_id": "e1dbe6ca53c14389922d6b77e36e9dee",
				"client_secret": "7f1cb1a0c1534a9f8af98b60d8d187bb"
			}
		}),
		"authsuccess": AuthSuccessController,
		"authpage": AuthPageController
	},
	"views": {
		"templates_path": ["views.templates"],
		"static_path": ["views.static"],
		"translations": ["views.locales"]
	},
	"events": {
		"ApplicationStarted": Controller2.application_after_load,
		InternalServerError.code: Controller2.internal_server_error
	},
	"models": {
		"connection": "sqlite:///kisspy_project.sqldb"
	}
}


########NEW FILE########
__FILENAME__ = start
from settings import options
from kiss.core.application import Application


app = Application(options)
app.start()



########NEW FILE########
