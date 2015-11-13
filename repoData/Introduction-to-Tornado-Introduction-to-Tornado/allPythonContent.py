__FILENAME__ = tweet_rate
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient

import urllib
import json
import datetime
import time

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class IndexHandler(tornado.web.RequestHandler):
	def get(self):
		query = self.get_argument('q')
		client = tornado.httpclient.HTTPClient()
		response = client.fetch("http://search.twitter.com/search.json?" + \
				urllib.urlencode({"q": query, "result_type": "recent", "rpp": 100}))
		body = json.loads(response.body)
		result_count = len(body['results'])
		now = datetime.datetime.utcnow()
		raw_oldest_tweet_at = body['results'][-1]['created_at']
		oldest_tweet_at = datetime.datetime.strptime(raw_oldest_tweet_at,
				"%a, %d %b %Y %H:%M:%S +0000")
		seconds_diff = time.mktime(now.timetuple()) - \
				time.mktime(oldest_tweet_at.timetuple())
		tweets_per_second = float(result_count) / seconds_diff
		self.write("""
<div style="text-align: center">
	<div style="font-size: 72px">%s</div>
	<div style="font-size: 144px">%.02f</div>
	<div style="font-size: 24px">tweets per second</div>
</div>""" % (query, tweets_per_second))

if __name__ == "__main__":
	tornado.options.parse_command_line()
	app = tornado.web.Application(handlers=[(r"/", IndexHandler)])
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = tweet_rate_async
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient

import urllib
import json
import datetime
import time

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class IndexHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	def get(self):
		query = self.get_argument('q')
		client = tornado.httpclient.AsyncHTTPClient()
		client.fetch("http://search.twitter.com/search.json?" + \
				urllib.urlencode({"q": query, "result_type": "recent", "rpp": 100}),
				callback=self.on_response)

	def on_response(self, response):
		body = json.loads(response.body)
		result_count = len(body['results'])
		now = datetime.datetime.utcnow()
		raw_oldest_tweet_at = body['results'][-1]['created_at']
		oldest_tweet_at = datetime.datetime.strptime(raw_oldest_tweet_at,
				"%a, %d %b %Y %H:%M:%S +0000")
		seconds_diff = time.mktime(now.timetuple()) - \
				time.mktime(oldest_tweet_at.timetuple())
		tweets_per_second = float(result_count) / seconds_diff
		self.write("""
<div style="text-align: center">
	<div style="font-size: 72px">%s</div>
	<div style="font-size: 144px">%.02f</div>
	<div style="font-size: 24px">tweets per second</div>
</div>""" % (self.get_argument('q'), tweets_per_second))
		self.finish()

if __name__ == "__main__":
	tornado.options.parse_command_line()
	app = tornado.web.Application(handlers=[(r"/", IndexHandler)])
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = tweet_rate_gen
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient
import tornado.gen

import urllib
import json
import datetime
import time

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class IndexHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	@tornado.gen.engine
	def get(self):
		query = self.get_argument('q')
		client = tornado.httpclient.AsyncHTTPClient()
		response = yield tornado.gen.Task(client.fetch,
				"http://search.twitter.com/search.json?" + \
				urllib.urlencode({"q": query, "result_type": "recent", "rpp": 100}))
		body = json.loads(response.body)
		result_count = len(body['results'])
		now = datetime.datetime.utcnow()
		raw_oldest_tweet_at = body['results'][-1]['created_at']
		oldest_tweet_at = datetime.datetime.strptime(raw_oldest_tweet_at,
				"%a, %d %b %Y %H:%M:%S +0000")
		seconds_diff = time.mktime(now.timetuple()) - \
				time.mktime(oldest_tweet_at.timetuple())
		tweets_per_second = float(result_count) / seconds_diff
		self.write("""
<div style="text-align: center">
	<div style="font-size: 72px">%s</div>
	<div style="font-size: 144px">%.02f</div>
	<div style="font-size: 24px">tweets per second</div>
</div>""" % (query, tweets_per_second))
		self.finish()

if __name__ == "__main__":
	tornado.options.parse_command_line()
	app = tornado.web.Application(handlers=[(r"/", IndexHandler)])
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = shopping_cart
import tornado.web
import tornado.httpserver
import tornado.ioloop
import tornado.options
from uuid import uuid4

class ShoppingCart(object):
	totalInventory = 10
	callbacks = []
	carts = {}
	
	def register(self, callback):
		self.callbacks.append(callback)
	
	def moveItemToCart(self, session):
		if session in self.carts:
			return
		
		self.carts[session] = True
		self.notifyCallbacks()
	
	def removeItemFromCart(self, session):
		if session not in self.carts:
			return
		
		del(self.carts[session])
		self.notifyCallbacks()
	
	def notifyCallbacks(self):
		self.callbacks[:] = [c for c in self.callbacks if self.callbackHelper(c)]
	
	def callbackHelper(self, callback):
		callback(self.getInventoryCount())
		return False
	
	def getInventoryCount(self):
		return self.totalInventory - len(self.carts)

class DetailHandler(tornado.web.RequestHandler):
	def get(self):
		session = uuid4()
		count = self.application.shoppingCart.getInventoryCount()
		self.render("index.html", session=session, count=count)

class CartHandler(tornado.web.RequestHandler):
	def post(self):
		action = self.get_argument('action')
		session = self.get_argument('session')
		
		if not session:
			self.set_status(400)
			return
		
		if action == 'add':
			self.application.shoppingCart.moveItemToCart(session)
		elif action == 'remove':
			self.application.shoppingCart.removeItemFromCart(session)
		else:
			self.set_status(400)

class StatusHandler(tornado.web.RequestHandler):
	@tornado.web.asynchronous
	def get(self):
		self.application.shoppingCart.register(self.async_callback(self.on_message))
	
	def on_message(self, count):
		self.write('{"inventoryCount":"%d"}' % count)
		self.finish()
		
class Application(tornado.web.Application):
	def __init__(self):
		self.shoppingCart = ShoppingCart()
		
		handlers = [
			(r'/', DetailHandler),
			(r'/cart', CartHandler),
			(r'/cart/status', StatusHandler)
		]
		
		settings = {
			'template_path': 'templates',
			'static_path': 'static'
		}
		
		tornado.web.Application.__init__(self, handlers, **settings)

if __name__ == '__main__':
	tornado.options.parse_command_line()
	
	app = Application()
	server = tornado.httpserver.HTTPServer(app)
	server.listen(8000)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = shopping_cart
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import tornado.options
from uuid import uuid4

class ShoppingCart(object):
	totalInventory = 10
	callbacks = []
	carts = {}
	
	def register(self, callback):
		self.callbacks.append(callback)
	
	def unregister(self, callback):
		self.callbacks.remove(callback)
	
	def moveItemToCart(self, session):
		if session in self.carts:
			return
		
		self.carts[session] = True
		self.notifyCallbacks()
	
	def removeItemFromCart(self, session):
		if session not in self.carts:
			return
		
		del(self.carts[session])
		self.notifyCallbacks()
	
	def notifyCallbacks(self):
		for callback in self.callbacks:
			callback(self.getInventoryCount())
	
	def getInventoryCount(self):
		return self.totalInventory - len(self.carts)

class DetailHandler(tornado.web.RequestHandler):
	def get(self):
		session = uuid4()
		count = self.application.shoppingCart.getInventoryCount()
		self.render("index.html", session=session, count=count)

class CartHandler(tornado.web.RequestHandler):
	def post(self):
		action = self.get_argument('action')
		session = self.get_argument('session')
		
		if not session:
			self.set_status(400)
			return
		
		if action == 'add':
			self.application.shoppingCart.moveItemToCart(session)
		elif action == 'remove':
			self.application.shoppingCart.removeItemFromCart(session)
		else:
			self.set_status(400)

class StatusHandler(tornado.websocket.WebSocketHandler):
	def open(self):
		self.application.shoppingCart.register(self.callback)
	
	def on_close(self):
		self.application.shoppingCart.unregister(self.callback)
	
	def on_message(self, message):
		pass
	
	def callback(self, count):
		self.write_message('{"inventoryCount":"%d"}' % count)
		
class Application(tornado.web.Application):
	def __init__(self):
		self.shoppingCart = ShoppingCart()
		
		handlers = [
			(r'/', DetailHandler),
			(r'/cart', CartHandler),
			(r'/cart/status', StatusHandler)
		]
		
		settings = {
			'template_path': 'templates',
			'static_path': 'static'
		}
		
		tornado.web.Application.__init__(self, handlers, **settings)

if __name__ == '__main__':
	tornado.options.parse_command_line()
	
	app = Application()
	server = tornado.httpserver.HTTPServer(app)
	server.listen(8000)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = burts_books_db
#!/usr/bin/env python
import os.path

import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

import pymongo

define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", MainHandler),
			(r"/recommended/", RecommendedHandler),
		]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			ui_modules={"Book": BookModule},
			debug=True,
			)
		conn = pymongo.Connection("localhost", 27017)
		self.db = conn["bookstore"]
		tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
	def get(self):

		self.render(
			"index.html",
			page_title = "Burt's Books | Home",
			header_text = "Welcome to Burt's Books!",
		)

class RecommendedHandler(tornado.web.RequestHandler):
	def get(self):
		coll = self.application.db.books
		books = coll.find()
		self.render(
			"recommended.html",
			page_title = "Burt's Books | Recommended Reading",
			header_text = "Recommended Reading",
			books = books
		)
		
class BookModule(tornado.web.UIModule):
	def render(self, book):
		return self.render_string(
			"modules/book.html", 
			book=book,
		)
	
	def css_files(self):
		return "/static/css/recommended.css"
	
	def javascript_files(self):
		return "/static/js/recommended.js"


def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = burts_books_rwdb
#!/usr/bin/env python
import os.path

import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

import pymongo

define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", MainHandler),
			(r"/recommended/", RecommendedHandler),
			(r"/edit/([0-9Xx\-]+)", BookEditHandler),
			(r"/add", BookEditHandler)
		]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			ui_modules={"Book": BookModule},
			debug=True,
			)
		conn = pymongo.Connection("localhost", 27017)
		self.db = conn["bookstore"]
		tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
	def get(self):

		self.render(
			"index.html",
			page_title = "Burt's Books | Home",
			header_text = "Welcome to Burt's Books!",
		)

class BookEditHandler(tornado.web.RequestHandler):
	def get(self, isbn=None):
		book = dict()
		if isbn:
			coll = self.application.db.books
			book = coll.find_one({"isbn": isbn})
		self.render("book_edit.html",
			page_title="Burt's Books",
			header_text="Edit book",
			book=book)

	def post(self, isbn=None):
		import time
		book_fields = ['isbn', 'title', 'subtitle', 'image', 'author',
			'date_released', 'description']
		coll = self.application.db.books
		book = dict()
		if isbn:
			book = coll.find_one({"isbn": isbn})
		for key in book_fields:
			book[key] = self.get_argument(key, None)

		if isbn:
			coll.save(book)
		else:
			book['date_added'] = int(time.time())
			coll.insert(book)
		self.redirect("/recommended/")

class RecommendedHandler(tornado.web.RequestHandler):
	def get(self):
		coll = self.application.db.books
		books = coll.find()
		self.render(
			"recommended.html",
			page_title = "Burt's Books | Recommended Reading",
			header_text = "Recommended Reading",
			books = books
		)
		
class BookModule(tornado.web.UIModule):
	def render(self, book):
		return self.render_string(
			"modules/book.html", 
			book=book,
		)
	
	def css_files(self):
		return "/static/css/recommended.css"
	
	def javascript_files(self):
		return "/static/js/recommended.js"


def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = burts_books_rwdb_single
#!/usr/bin/env python
import os.path

import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

import pymongo

define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", MainHandler),
			(r"/recommended/", RecommendedHandler),
			(r"/books/([0-9Xx\-]+)", BookHandler),
			(r"/edit/([0-9Xx\-]+)", BookEditHandler),
			(r"/add", BookEditHandler)
		]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			ui_modules={"Book": BookModule},
			debug=True,
			)
		conn = pymongo.Connection("localhost", 27017)
		self.db = conn["bookstore"]
		tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
	def get(self):

		self.render(
			"index.html",
			page_title = "Burt's Books | Home",
			header_text = "Welcome to Burt's Books!",
		)

class BookHandler(tornado.web.RequestHandler):
	def get(self, isbn=None):
		if isbn:
			coll = self.application.db.books
			book = coll.find_one({"isbn": isbn})
			if book:
				self.render("one_book.html",
					page_title="Burt's Books | " + book['title'],
					header_text=book['title'],
					book=book)
				return
		self.set_header(404)
		return

class BookEditHandler(tornado.web.RequestHandler):
	def get(self, isbn=None):
		book = dict()
		if isbn:
			coll = self.application.db.books
			book = coll.find_one({"isbn": isbn})
		self.render("book_edit.html",
			page_title="Burt's Books",
			header_text="Edit book",
			book=book)

	def post(self, isbn=None):
		import time
		book_fields = ['isbn', 'title', 'subtitle', 'image', 'author',
			'date_released', 'description']
		coll = self.application.db.books
		if isbn:
			book = coll.find_one({"isbn": isbn})
		for key in book_fields:
			book[key] = self.get_argument(key, None)

		if isbn:
			coll.save(book)
		else:
			book['date_added'] = int(time.time())
			coll.insert(book)
		self.redirect("/recommended/")

class RecommendedHandler(tornado.web.RequestHandler):
	def get(self):
		coll = self.application.db.books
		books = coll.find()
		self.render(
			"recommended.html",
			page_title = "Burt's Books | Recommended Reading",
			header_text = "Recommended Reading",
			books = books
		)
		
class BookModule(tornado.web.UIModule):
	def render(self, book):
		return self.render_string(
			"modules/book.html", 
			book=book,
		)
	
	def css_files(self):
		return "/static/css/recommended.css"
	
	def javascript_files(self):
		return "/static/js/recommended.js"


def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = definitions_readonly
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

import pymongo

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [(r"/(\w+)", WordHandler)]
		conn = pymongo.Connection("localhost", 27017)
		self.db = conn["example"]
		tornado.web.Application.__init__(self, handlers, debug=True)

class WordHandler(tornado.web.RequestHandler):
	def get(self, word):
		coll = self.application.db.words
		word_doc = coll.find_one({"word": word})
		if word_doc:
			del word_doc["_id"]
			self.write(word_doc)
		else:
			self.set_status(404)
			self.write({"error": "word not found"})

def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = definitions_readwrite
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

import pymongo

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [(r"/(\w+)", WordHandler)]
		conn = pymongo.Connection("localhost", 27017)
		self.db = conn["definitions"]
		tornado.web.Application.__init__(self, handlers, debug=True)

class WordHandler(tornado.web.RequestHandler):
	def get(self, word):
		coll = self.application.db.words
		word_doc = coll.find_one({"word": word})
		if word_doc:
			del word_doc["_id"]
			self.write(word_doc)
		else:
			self.set_status(404)
	def post(self, word):
		definition = self.get_argument("definition")
		coll = self.application.db.words
		word_doc = coll.find_one({"word": word})
		if word_doc:
			word_doc['definition'] = definition
			coll.save(word_doc)
		else:
			word_doc = {'word': word, 'definition': definition}
			coll.insert(word_doc)
		del word_doc["_id"]
		self.write(word_doc)

def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
import os.path

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", MainHandler),
		]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			ui_modules={"Sample": SampleModule},
			debug=True,
			autoescape=None
			)
		tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.render(
			"index.html",
			samples=[
				{
					"title":"Item 1",
					"description":"Description for item 1"
				},
				{
					"title":"Item 2",
					"description":"Description for item 2"
				},
				{
					"title":"Item 3",
					"description":"Description for item 3"
				}
			]	
		)


class SampleModule(tornado.web.UIModule):
	def render(self, sample):
		return self.render_string(
			"modules/sample.html", 
			sample=sample
		)

	def html_body(self):
		return "<div class=\"addition\"><p>html_body()</p></div>"
	
	def embedded_javascript(self):
		return "document.write(\"<p>embedded_javascript()</p>\")"
	
	def embedded_css(self):
		return ".addition {color: #A1CAF1}"
		
	def css_files(self):
		return "/static/css/sample.css"
	
	def javascript_files(self):
		return "/static/js/sample.js"

def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
import os.path

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", MainHandler),
		]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			debug=True,
			autoescape=None
			)
		tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.render(
			"index.html",
			header_text = "Header goes here",
			footer_text = "Footer goes here"
		)


def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
import os.path

import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", MainHandler),
			(r"/recommended/", RecommendedHandler),
			(r"/discussion/", DiscussionHandler),
		]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			ui_modules={"Book": BookModule},
			debug=True,
			)
		tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
	def get(self):

		self.render(
			"index.html",
			page_title = "Burt's Books | Home",
			header_text = "Welcome to Burt's Books!",
		)

class RecommendedHandler(tornado.web.RequestHandler):
	def get(self):

		self.render(
			"recommended.html",
			page_title = "Burt's Books | Recommended Reading",
			header_text = "Recommended Reading",
			books=[
				{
					"title":"Programming Collective Intelligence",
					"subtitle": "Building Smart Web 2.0 Applications",
					"image":"/static/images/collective_intelligence.gif",
					"author": "Toby Segaran",
					"date_added":1310248056,
					"date_released": "August 2007",
					"isbn":"978-0-596-52932-1",
					"description":"<p>This fascinating book demonstrates how you can build web applications to mine the enormous amount of data created by people on the Internet. With the sophisticated algorithms in this book, you can write smart programs to access interesting datasets from other web sites, collect data from users of your own applications, and analyze and understand the data once you've found it.</p>"
				},
				{
					"title":"RESTful Web Services",
					"subtitle": "Web services for the real world",
					"image":"/static/images/restful_web_services.gif",
					"author": "Leonard Richardson, Sam Ruby",
					"date_added":1311148056,
					"date_released": "May 2007",
					"isbn":"978-0-596-52926-0",
					"description":"<p>You've built web sites that can be used by humans. But can you also build web sites that are usable by machines? That's where the future lies, and that's what this book shows you how to do. Today's web service technologies have lost sight of the simplicity that made the Web successful. This book explains how to put the &quot;Web&quot; back into web services with REST, the architectural style that drives the Web.</p>"
				},
				{
					"title":"Head First Python",
					"subtitle": "",
					"image":"/static/images/head_first_python.gif",
					"author": "Paul Barry",
					"date_added":1311348056,
					"date_released": "November 2010",
					"isbn":"Head First Python",
					"description":"<p>Ever wished you could learn Python from a book? Head First Python is a complete learning experience for Python that helps you learn the language through a unique method that goes beyond syntax and how-to manuals, helping you understand how to be a great Python programmer. You'll quickly learn the language's fundamentals, then move onto persistence, exception handling, web development, SQLite, data wrangling, and Google App Engine. You'll also learn how to write mobile apps for Android, all thanks to the power that Python gives you.</p>"
				}
			]
		)

class DiscussionHandler(tornado.web.RequestHandler):
	def get(self):

		self.render(
			"discussion.html",
			page_title = "Burt's Books | Discussion",
			header_text = "Talkin' About Books With Burt",
			comments=[
				{
					"user":"Alice",
					"text": "I can't wait for the next version of Programming Collective Intelligence!"
				},
				{
					"user":"Burt",
					"text": "We can't either, Alice.  In the meantime, be sure to check out RESTful Web Services too."
				},
				{
					"user":"Melvin",
					"text": "Totally hacked ur site lulz <script src=\"http://melvins-web-sploits.com/evil_sploit.js\"></script><script>alert('RUNNING EVIL H4CKS AND SPL0ITS NOW...');</script>"
				}
			]
		)

		
class BookModule(tornado.web.UIModule):
	def render(self, book):
		return self.render_string(
			"modules/book.html", 
			book=book,
		)
	
	def css_files(self):
		return "/static/css/recommended.css"
	
	def javascript_files(self):
		return "/static/js/recommended.js"


def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = facebook
import tornado.web
import tornado.httpserver
import tornado.auth
import tornado.ioloop
import tornado.options

import modules

class FacebookHandler(tornado.web.RequestHandler, tornado.auth.FacebookGraphMixin):
	@tornado.web.asynchronous
	def get(self):
		accessToken = self.get_secure_cookie('access_token')
		if not accessToken:
			self.redirect('/auth/login')
			return
		
		self.facebook_request(
			"/me/feed",
			access_token=accessToken,
			callback=self.async_callback(self._on_facebook_user_feed))
		
	def _on_facebook_user_feed(self, response):
		name = self.get_secure_cookie('user_name')
		self.render('home.html', feed=response['data'] if response else [], name=name)
	
	@tornado.web.asynchronous
	def post(self):
		accessToken = self.get_secure_cookie('access_token')
		if not accessToken:
			self.redirect('/auth/login')
		
		userInput = self.get_argument('message')
		
		self.facebook_request(
			"/me/feed",
			post_args={'message': userInput},
			access_token=accessToken,
			callback=self.async_callback(self._on_facebook_post_status))
	
	def _on_facebook_post_status(self, response):
		self.redirect('/')

class LoginHandler(tornado.web.RequestHandler, tornado.auth.FacebookGraphMixin):
	@tornado.web.asynchronous
	def get(self):
		userID = self.get_secure_cookie('user_id')
		
		if self.get_argument('code', None):
			self.get_authenticated_user(
				redirect_uri='http://example.com/auth/login',
				client_id=self.settings['facebook_api_key'],
				client_secret=self.settings['facebook_secret'],
				code=self.get_argument('code'),
				callback=self.async_callback(self._on_facebook_login))
			return
		elif self.get_secure_cookie('access_token'):
			self.redirect('/')
		
		self.authorize_redirect(
			redirect_uri='http://example.com/auth/login',
			client_id=self.settings['facebook_api_key'],
			extra_params={'scope': 'read_stream,publish_stream'}
		)
	
	def _on_facebook_login(self, user):
		if not user:
			self.clear_all_cookies()
			raise tornado.web.HTTPError(500, 'Facebook authentication failed')
		
		self.set_secure_cookie('user_id', str(user['id']))
		self.set_secure_cookie('user_name', str(user['name']))
		self.set_secure_cookie('access_token', str(user['access_token']))
		self.redirect('/')

class LogoutHandler(tornado.web.RequestHandler):
	def get(self):
		self.clear_all_cookies()
		self.render('logout.html')

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r'/', FacebookHandler),
			(r'/auth/login', LoginHandler),
			(r'/auth/logout',  LogoutHandler)
		]
		
		settings = {
			'facebook_api_key': '2040 ... 8759',
			'facebook_secret': 'eae0 ... 2f08',
			'cookie_secret': 'NTliOTY5NzJkYTVlMTU0OTAwMTdlNjgzMTA5M2U3OGQ5NDIxZmU3Mg==',
			'template_path': 'templates',
			'ui_modules': modules
		}
		
		tornado.web.Application.__init__(self, handlers, **settings)

if __name__ == '__main__':
	tornado.options.parse_command_line()
	
	app = Application()
	server = tornado.httpserver.HTTPServer(app)
	server.listen(8000)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = modules
import tornado.web
from datetime import datetime

class FeedListItem(tornado.web.UIModule):
	def render(self, statusItem):
		return self.render_string('entry.html', item=statusItem, format=lambda x: datetime.strptime(x,'%Y-%m-%dT%H:%M:%S+0000').strftime('%c'))
########NEW FILE########
__FILENAME__ = twitter
import tornado.web
import tornado.httpserver
import tornado.auth
import tornado.ioloop

class TwitterHandler(tornado.web.RequestHandler, tornado.auth.TwitterMixin):
	@tornado.web.asynchronous
	def get(self):
		oAuthToken = self.get_secure_cookie('access_key')
		oAuthSecret = self.get_secure_cookie('access_secret')
		userID = self.get_secure_cookie('user_id')
		
		if self.get_argument('oauth_token', None):
			self.get_authenticated_user(self.async_callback(self._twitter_on_auth))
			return
		
		elif oAuthToken and oAuthSecret:
			accessToken = {
				'key': oAuthToken,
				'secret': oAuthSecret
			}
			self.twitter_request('/users/show',
				access_token=accessToken,
				user_id=userID,
				callback=self.async_callback(self._twitter_on_user)
			)
			return
		
		self.authorize_redirect()
	
	def _twitter_on_auth(self, user):
		if not user:
			self.clear_all_cookies()
			raise tornado.web.HTTPError(500, 'Twitter authentication failed')
		
		self.set_secure_cookie('user_id', str(user['id']))
		self.set_secure_cookie('access_key', user['access_token']['key'])
		self.set_secure_cookie('access_secret', user['access_token']['secret'])
		
		self.redirect('/')
	
	def _twitter_on_user(self, user):
		if not user:
			self.clear_all_cookies()
			raise tornado.web.HTTPError(500, "Couldn't retrieve user information")
		
		self.render('home.html', user=user)

class LogoutHandler(tornado.web.RequestHandler):
	def get(self):
		self.clear_all_cookies()
		self.render('logout.html')

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r'/', TwitterHandler),
			(r'/logout', LogoutHandler)
		]
		
		settings = {
			'twitter_consumer_key': 'cWc3 ... d3yg',
			'twitter_consumer_secret': 'nEoT ... cCXB4',
			'cookie_secret': 'NTliOTY5NzJkYTVlMTU0OTAwMTdlNjgzMTA5M2U3OGQ5NDIxZmU3Mg==',
			'template_path': 'templates',
		}
		
		tornado.web.Application.__init__(self, handlers, **settings)

if __name__ == '__main__':
	app = Application()
	server = tornado.httpserver.HTTPServer(app)
	server.listen(8000)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = hello-error
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)

class IndexHandler(tornado.web.RequestHandler):
	def get(self):
		greeting = self.get_argument('greeting', 'Hello')
		self.write(greeting + ', friendly user!')
	def write_error(self, status_code, **kwargs):
		self.write("Gosh darnit, user! You caused a %d error." % status_code)

if __name__ == "__main__":
	tornado.options.parse_command_line()
	app = tornado.web.Application(handlers=[(r"/", IndexHandler)])
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = hello
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)

class IndexHandler(tornado.web.RequestHandler):
	def get(self):
		greeting = self.get_argument('greeting', 'Hello')
		self.write(greeting + ', friendly user!')

if __name__ == "__main__":
	tornado.options.parse_command_line()
	app = tornado.web.Application(handlers=[(r"/", IndexHandler)])
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = string_service
import textwrap

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)

class ReverseHandler(tornado.web.RequestHandler):
	def get(self, input):
		self.write(input[::-1])

class WrapHandler(tornado.web.RequestHandler):
	def post(self):
		text = self.get_argument('text')
		width = self.get_argument('width', 40)
		self.write(textwrap.fill(text, int(width)))

if __name__ == "__main__":
	tornado.options.parse_command_line()
	app = tornado.web.Application(handlers=[
		(r"/reverse/(\w+)", ReverseHandler),
		(r"/wrap", WrapHandler)
	])
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
import os.path

import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", MainHandler),
		]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			debug=True,
			autoescape=None
			)
		tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
	def get(self):

		self.render(
			"index.html",
			page_title = "Burt's Books | Home",
			header_text = "Welcome to Burt's Books!",
			footer_text = "For more information, please email us at <a href=\"mailto:contact@burtsbooks.com\">contact@burtsbooks.com</a>.",
		)


def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = simple
#!/usr/bin/env python

import os
import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

# define Tornado defaults
define("port", default=8000, help="run on the given port", type=int)

# application configuration
class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", SimpleHandler),
			(r"/one/", SimpleHandler),
			(r"/two/", SecondHandler),
			(r"/three/", ThirdHandler),
			(r"/four/", FourthHandler),
		]
		settings = dict(
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			debug=True,
			)
		tornado.web.Application.__init__(self, handlers, **settings)

class SimpleHandler(tornado.web.RequestHandler):
	def get(self):
		self.render(
			"simple.html",
			title="Home Page",
			header="Welcome",
			intro="You've landed on my amazing page here."
		)
	
class SecondHandler(tornado.web.RequestHandler):
	def get(self):
		self.render(
			"simple_2.html",
			title="Home Page",
			header="Welcome",
			books=["Learning Python","Programming Collective Intelligence","Restful Web Services"]
		)

class ThirdHandler(tornado.web.RequestHandler):
	def get(self):
		self.render(
			"simple_3.xml",
			title="Home Page",
			header="Welcome",
			books=["Learning Python","Programming Collective Intelligence","Restful Web Services"]
		)
	
	
class FourthHandler(tornado.web.RequestHandler):
	def get(self):
		self.render(
			"simple_4.txt",
			title="Home Page",
			header="Welcome",
			books=["Learning Python","Programming Collective Intelligence","Restful Web Services"]
		)
	

# Start it up
def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = poemmaker
import os.path

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)

class IndexHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('index.html')

class PoemPageHandler(tornado.web.RequestHandler):
	def post(self):
		noun1 = self.get_argument('noun1')
		noun2 = self.get_argument('noun2')
		verb = self.get_argument('verb')
		noun3 = self.get_argument('noun3')
		self.render('poem.html', roads=noun1, wood=noun2, made=verb,
				difference=noun3)

if __name__ == '__main__':
	tornado.options.parse_command_line()
	app = tornado.web.Application(
		handlers=[(r'/', IndexHandler), (r'/poem', PoemPageHandler)],
		template_path=os.path.join(os.path.dirname(__file__), "templates")
	)
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


########NEW FILE########
__FILENAME__ = main
import os.path
import random

import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)

class IndexHandler(tornado.web.RequestHandler):
	def get(self):
		self.render('index.html')

class MungedPageHandler(tornado.web.RequestHandler):
	def map_by_first_letter(self, text):
		mapped = dict()
		for line in text.split('\r\n'):
			for word in [x for x in line.split(' ') if len(x) > 0]:
				if word[0] not in mapped: mapped[word[0]] = []
				mapped[word[0]].append(word)
		return mapped

	def post(self):
		source_text = self.get_argument('source')
		text_to_change = self.get_argument('change')
		source_map = self.map_by_first_letter(source_text)
		change_lines = text_to_change.split('\r\n')
		self.render('munged.html', source_map=source_map, change_lines=change_lines,
				choice=random.choice)

if __name__ == '__main__':
	tornado.options.parse_command_line()
	app = tornado.web.Application(
		handlers=[(r'/', IndexHandler), (r'/poem', MungedPageHandler)],
		template_path=os.path.join(os.path.dirname(__file__), "templates"),
		static_path=os.path.join(os.path.dirname(__file__), "static"),
		debug=True
	)
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()


########NEW FILE########
