__FILENAME__ = CertService
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.ioloop
from tornadows import soaphandler, webservices, complextypes
from tornadows.soaphandler import webservice
import datetime

""" This example uses python datetime module. 
	python datetime.date is equivalent to xml type: xsd:date
	python datetime.datetime is equivalent to xml type: xsd:dateTime
	python datetime.time is equivalent to xml type: xsd:time
"""
class InputRequest(complextypes.ComplexType):
	idperson = str

class CertificateResponse(complextypes.ComplexType):
	numcert = int
	idperson = str
	nameperson = str
	birthday = datetime.date
	datetimecert = datetime.datetime
	isvalid = bool

class CertService(soaphandler.SoapHandler):
	@webservice(_params=InputRequest, _returns=CertificateResponse)
	def getCertificate(self, input):
		idperson = input.idperson

		cert = CertificateResponse()
		cert.numcert = 1
		cert.idperson = idperson
		cert.nameperson = 'Steve J'
		cert.birthday = datetime.date(1973,12,11)
		cert.datetimecert = datetime.datetime.now()
		cert.isvalid = True

		return cert

if __name__ == '__main__':
	service = [('CertService',CertService)]
	app = webservices.WebService(service)
	app.listen(8080)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = CurrentTempService
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import xmltypes
from tornadows.soaphandler import webservice

class CurrentTempService(soaphandler.SoapHandler):
     """ Service that return the current temperature, not uses input parameters """
     @webservice(_params=None,_returns=xmltypes.Integer)
     def getCurrentTemperature(self):
          c = 29
          return c

if __name__ == '__main__':
     service = [('CurrentTempService',CurrentTempService)]
     app = webservices.WebService(service)
     ws  = tornado.httpserver.HTTPServer(app)
     ws.listen(8080)
     tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = DemoServices
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import xmltypes
from tornadows.soaphandler import webservice

class EchoService(soaphandler.SoapHandler):
	""" Echo Service """
	@webservice(_params=xmltypes.String,_returns=xmltypes.String)
	def echo(self, message):
		return 'Echo say : %s' % message

class EchoTargetnsService(soaphandler.SoapHandler):
	""" Service to test the use of an overrided target namespace address """
	targetns_address = '192.168.0.103'
	@webservice(_params=xmltypes.String, _returns=xmltypes.String)
	def echo(self, message):
		return 'Echo say : %s' % message

class CountService(soaphandler.SoapHandler):
	""" Service that counts the number of items in a list """
	@webservice(_params=xmltypes.Array(xmltypes.String),_returns=xmltypes.Integer)
	def count(self, list_of_values):
		length = len(list_of_values)
		return length

class DivService(soaphandler.SoapHandler):
	""" Service that provides the division operation of two float numbers """
	@webservice(_params=[xmltypes.Float,xmltypes.Float],_returns=xmltypes.Float)
	def div(self, a, b):
		result = a/b
		return result

class FibonacciService(soaphandler.SoapHandler):
	""" Service that provides Fibonacci numbers """
	@webservice(_params=xmltypes.Integer,_returns=xmltypes.Array(xmltypes.Integer))
	def fib(self,n):
		a, b = 0, 1
		result = []
		while b < n:
			result.append(b)
			a, b = b, a + b
		return result

if __name__ == '__main__':
     service = [('EchoService',EchoService),
                ('EchoTargetnsService', EchoTargetnsService),
                ('CountService',CountService),
                ('DivService',DivService),
                ('FibonacciService',FibonacciService)]
     app = webservices.WebService(service)
     ws  = tornado.httpserver.HTTPServer(app)
     ws.listen(8080)
     tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = DemoServices2
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import xmltypes
from tornadows.soaphandler import webservice

class EchoService(soaphandler.SoapHandler):
	""" Echo Service """
	@webservice(_params=str,_returns=str)
	def echo(self, message):
		return 'Echo say : %s' % message

class EchoTargetnsService(soaphandler.SoapHandler):
	""" Service to test the use of an overrided target namespace address """
	targetns_address = '192.168.0.102' # IP of your machine
	@webservice(_params=str, _returns=str)
	def echo(self, message):
		return 'Echo say : %s' % message

class CountService(soaphandler.SoapHandler):
	""" Service that counts the number of items in a list """
	@webservice(_params=xmltypes.Array(str),_returns=int)
	def count(self, list_of_values):
		length = len(list_of_values)
		return length

class DivService(soaphandler.SoapHandler):
	""" Service that provides the division operation of two float numbers """
	@webservice(_params=[float,float],_returns=float)
	def div(self, a, b):
		result = a/b
		return result

class FibonacciService(soaphandler.SoapHandler):
	""" Service that provides Fibonacci numbers """
	@webservice(_params=int,_returns=xmltypes.Array(int))
	def fib(self,n):
		a, b = 0, 1
		result = []
		while b < n:
			result.append(b)
			a, b = b, a + b
		return result

if __name__ == '__main__':
  	service = [('EchoService',EchoService),
        	   ('EchoTargetnsService', EchoTargetnsService),
        	   ('CountService',CountService),
               ('DivService',DivService),
               ('FibonacciService',FibonacciService)]
  	app = webservices.WebService(service)
  	ws  = tornado.httpserver.HTTPServer(app)
  	ws.listen(8080)
  	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = DemoServicesHostname
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop

from tornado.options import define, options
from tornadows import soaphandler
from tornadows import webservices
from tornadows import xmltypes
from tornadows.soaphandler import webservice

# If you plan server this webservice in many machines, please set up your
# main domain here. Useful to work in a round-robin way or reverse proxy.
define("wsdl_hostname", default="mydomain.com", help="WSDL Hostname")

class EchoService(soaphandler.SoapHandler):
	""" Echo Service """
	@webservice(_params=xmltypes.String,_returns=xmltypes.String)
	def echo(self, message):
		return 'Echo say : %s' % message

class EchoTargetnsService(soaphandler.SoapHandler):
	""" Service to test the use of an overrided target namespace address """
	targetns_address = '192.168.0.103'
	@webservice(_params=xmltypes.String, _returns=xmltypes.String)
	def echo(self, message):
		return 'Echo say : %s' % message

class CountService(soaphandler.SoapHandler):
	""" Service that counts the number of items in a list """
	@webservice(_params=xmltypes.Array(xmltypes.String),_returns=xmltypes.Integer)
	def count(self, list_of_values):
		length = len(list_of_values)
		return length

class DivService(soaphandler.SoapHandler):
	""" Service that provides the division operation of two float numbers """
	@webservice(_params=[xmltypes.Float,xmltypes.Float],_returns=xmltypes.Float)
	def div(self, a, b):
		result = a/b
		return result

class FibonacciService(soaphandler.SoapHandler):
	""" Service that provides Fibonacci numbers """
	@webservice(_params=xmltypes.Integer,_returns=xmltypes.Array(xmltypes.Integer))
	def fib(self,n):
		a, b = 0, 1
		result = []
		while b < n:
			result.append(b)
			a, b = b, a + b
		return result

if __name__ == '__main__':
  	service = [('EchoService',EchoService),
        	   ('EchoTargetnsService', EchoTargetnsService),
        	   ('CountService',CountService),
             	   ('DivService',DivService),
             	   ('FibonacciService',FibonacciService)]
  	app = webservices.WebService(service)
  	ws  = tornado.httpserver.HTTPServer(app)
  	ws.listen(8080)
  	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = HelloWorldService
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import xmltypes
from tornadows.soaphandler import webservice

class HelloWorldService(soaphandler.SoapHandler):
	""" Service that return Hello World!!!, not uses input parameters """
	@webservice(_params=None,_returns=xmltypes.String)
	def sayHello(self):
		return "Hello World!!!"

if __name__ == '__main__':
  	service = [('HelloWorldService',HelloWorldService)]
  	app = webservices.WebService(service)
  	ws  = tornado.httpserver.HTTPServer(app)
  	ws.listen(8080)
  	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = HelloWorldService2
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import xmltypes
from tornadows.soaphandler import webservice

class HelloWorldService2(soaphandler.SoapHandler):
	""" Service that return an list with Hello and World str elements, not uses input parameters """
	@webservice(_params=None,_returns=xmltypes.Array(xmltypes.String))
	def sayHello(self):
		return ["Hello","World"]

if __name__ == '__main__':
  	service = [('HelloWorldService2',HelloWorldService2)]
  	app = webservices.WebService(service)
  	ws  = tornado.httpserver.HTTPServer(app)
  	ws.listen(8080)
  	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = MathService
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import xmltypes
from tornadows.soaphandler import webservice

class MathService(soaphandler.SoapHandler):
	""" Service that provides math operations of two float numbers """
	@webservice(_params=[float,float],_returns=float)
	def add(self, a, b):
		result = a+b
		return result
	@webservice(_params=[float,float],_returns=float)
	def sub(self, a, b):
		result = a-b
		return result
	@webservice(_params=[float,float],_returns=float)
	def mult(self, a, b):
		result = a*b
		return result
	@webservice(_params=[float,float],_returns=float)
	def div(self, a, b):
		result = a/b
		return result

if __name__ == '__main__':
  	service = [('MathService',MathService)]
  	app = webservices.WebService(service)
  	ws  = tornado.httpserver.HTTPServer(app)
  	ws.listen(8080)
  	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = ProductListService
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import complextypes
from tornadows.soaphandler import webservice

""" This web service implements two python classes as two xml complextypes.

    THIS IS AN ALTERNATIVE IMPLEMENTATION TO ProductService.py. THIS USES 
    PYTHON TYPES FOR THE ATTRIBUTES OF THE CLASS.

    Input is a class that represents the input parameter (request) for the
    web service:

	idList : is a int python type.

    Product is a class that represents Product data structure.

	id: Is a int python type. Is the product id
	name: Is a str python type. Is the name of product. 
	price: Is a float python type. Is the price of product.
	stock: Is a int python type. Is the stock of product.

    List is a class that represents  the response of the web services.

	idList: IS a int python type. Is a id for the list.
	product: Is a python list with a set of product (Product class).

"""

class Input(complextypes.ComplexType):
	idList = int 

class Product(complextypes.ComplexType):
	id    = int
	name  = str
	price = float
	stock = int

class List(complextypes.ComplexType):
	idList = int
	product = [Product]

class ProductListService(soaphandler.SoapHandler):
	@webservice(_params=Input,_returns=List)
	def getProductList(self, input):
		id = input.idList

		listOfProduct = List()
		listOfProduct.idList = id
		
		for i in [1,2,3,4,5,6]:
			reg = self.database(i)
			output = Product()
			output.id    = i
			output.name  = reg[0]
			output.price = reg[1]
			output.stock = reg[2]
	
			listOfProduct.product.append(output)

		return listOfProduct

	def database(self,id):
		""" This method simulates a database of products """
		db = {1:('COMPUTER',1000.5,100),
			  2:('MOUSE',10.0,300),
		      3:('PENCIL BLUE',0.50,500),
		      4:('PENCIL RED',0.50,600),
		      5:('PENCIL WHITE',0.50,900),
		      6:('HEADPHONES',15.7,500),
		     }
		row = (None,0.0,0)
		try:
			row = db[id]
		except:
			None
		return row
	
if __name__ == '__main__':
	service = [('ProductListService',ProductListService)]
	app = webservices.WebService(service)
	ws  = tornado.httpserver.HTTPServer(app)
	ws.listen(8080)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = ProductListService2
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import complextypes
from tornadows.soaphandler import webservice

""" This web service implements two python classes as two xml complextypes.

    THIS IS AN ALTERNATIVE IMPLEMENTATION TO ProductService.py. THIS USES 
    PYTHON TYPES FOR THE ATTRIBUTES OF THE CLASS.

    Product is a class that represents Product data structure.

	id: Is a int python type. Is the product id
	name: Is a str python type. Is the name of product. 
	price: Is a float python type. Is the price of product.
	stock: Is a int python type. Is the stock of product.

    List is a class that represents the response of the web services.
    This is a list of Product.

	product: Is a python list with a set of product (Product class).

	The operation have not input parameters.

"""

class Product(complextypes.ComplexType):
	id    = int
	name  = str
	price = float
	stock = int

class List(complextypes.ComplexType):
	product = [Product]

class ProductListService2(soaphandler.SoapHandler):
	@webservice(_params=None,_returns=List)
	def getProductList(self):

		listOfProduct = List()
		
		for i in [1,2,3,4,5,6,7]:
			reg = self.database(i)
			output = Product()
			output.id    = i
			output.name  = reg[0]
			output.price = reg[1]
			output.stock = reg[2]
	
			listOfProduct.product.append(output)

		return listOfProduct

	def database(self,id):
		""" This method simulates a database of products """
		db = {1:('COMPUTER',1000.5,100),
 		      2:('MOUSE',10.0,300),
		      3:('PENCIL BLUE',0.50,500),
		      4:('PENCIL RED',0.50,600),
		      5:('PENCIL WHITE',0.50,900),
		      6:('HEADPHONES',15.7,500),
		      7:('MACBOOK',80.78,300),
		     }
		row = (None,0.0,0)
		try:
			row = db[id]
		except:
			None
		return row
	
if __name__ == '__main__':
	service = [('ProductListService2',ProductListService2)]
	app = webservices.WebService(service)
	ws  = tornado.httpserver.HTTPServer(app)
	ws.listen(8080)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = ProductService
#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import complextypes
from tornadows.soaphandler import webservice

""" This web service implements two python classes as two xml complextypes.

    Input is a class that represents the input parameter (request) for the
    web service:

	idProduct : is a instance of IntegerProperty(). This create a subclass
		    of Property with value attribute (for store the value) and
		    type attribute for store the xmltype.

    Product is a class that represents the response of the web service.

	id: Is a instance of IntegerProperty() that store the id of product
	name: Is a instance of StringProperty() that store the name of product 
	price: Is a instance of FloatProperty() that store the price of product
	stock: Is a instance of IntegerProperty() that store the stock of product

"""

class Input(complextypes.ComplexType):
	idProduct = complextypes.IntegerProperty()

class Product(complextypes.ComplexType):
	id    = complextypes.IntegerProperty()
	name  = complextypes.StringProperty()
	price = complextypes.FloatProperty()
	stock = complextypes.IntegerProperty()

class ProductService(soaphandler.SoapHandler):
	@webservice(_params=Input,_returns=Product)
	def getProduct(self, input):
		id = input.idProduct.value
		
		reg = self.database(id)

		output = Product()

		output.id.value    = id
		output.name.value  = reg[0]
		output.price.value = reg[1]
		output.stock.value = reg[2]

		return output

	def database(self,id):
		""" This method simulates a database of products """
		db = {1:('COMPUTER',1000.5,100),
 		      2:('MOUSE',10.0,300),
		      3:('PENCIL BLUE',0.50,500),
		      4:('PENCIL RED',0.50,600),
		      5:('PENCIL WHITE',0.50,900),
		      6:('HEADPHONES',15.7,500),
		      7:(u'Japanses Noodles (ラーメン)',1.1,500),
		     }
		row = (None,0.0,0)
		try:
			row = db[id]
		except:
			None
		return row
	
if __name__ == '__main__':
	service = [('ProductService',ProductService)]
	app = webservices.WebService(service)
	ws  = tornado.httpserver.HTTPServer(app)
	ws.listen(8080)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = RegisterService
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.ioloop
from tornadows import soaphandler, webservices, complextypes
from tornadows.soaphandler import webservice
import datetime

""" This example uses python datetime module and xml complex datatypes.
	This example simulates a service of register of users in a system
 
	python datetime.date is equivalent to xml type: xsd:date
	python datetime.datetime is equivalent to xml type: xsd:dateTime
	python datetime.time is equivalent to xml type: xsd:time
"""
class RegisterRequest(complextypes.ComplexType):
	iduser = str
	names  = str
	birthdate = datetime.date
	email  = str

class RegisterResponse(complextypes.ComplexType):
	idregister = int
	names = str
	datetimeregister = datetime.datetime
	isvalid = bool
	message = str

class RegisterService(soaphandler.SoapHandler):
	@webservice(_params=RegisterRequest, _returns=RegisterResponse)
	def register(self, register):
		iduser    = register.iduser
		names     = register.names
		birthdate = register.birthdate
		email     = register.email

		# Here you can insert the user in a database
		response = RegisterResponse()
		response.idregister = 1
		response.names      = names
		response.datetimeregister = datetime.datetime.now()
		response.isvalid = True
		response.message = 'Your register for email : %s'%email

		return response

if __name__ == '__main__':
	service = [('RegisterService',RegisterService)]
	app = webservices.WebService(service)
	app.listen(8080)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = RepositoryService
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.ioloop
from tornadows import soaphandler
from tornadows import webservices
from tornadows import xmltypes
from tornadows import complextypes
from tornadows.soaphandler import webservice

import datetime

# This dictionary emulate a documental repository
repo = {}

class Document(complextypes.ComplexType):
	number = int 
	theme = str
	author = str
	text = str
	created = datetime.date

class Message(complextypes.ComplexType):
	doc = Document
	msg = str

class Repository(soaphandler.SoapHandler):
	""" Service of repository, store documents (Document)  """
	@webservice(_params=Message,_returns=str)
	def save(self, msg):
		global repo
		repo[msg.doc.number] = msg.doc
		return 'Save document number : %d'%msg.doc.number 

	@webservice(_params=int,_returns=Message)
	def find(self, num):
		global repo
		response = Message()
		try:
			doc = Document()
			d = repo[num]
			doc.number = d.number
			doc.theme = d.theme
			doc.author = d.author
			doc.text = d.text
			doc.created = d.created
			response.doc = doc
			response.msg = 'OK'
		except:
			response.doc = Document()
			response.msg = 'Document number %d dont exist'%num
		return response

if __name__ == '__main__':
  	service = [('RepositoryService',Repository)]
  	app = webservices.WebService(service).listen(8080)
  	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = UserRolesService
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import tornado.httpserver
import tornado.ioloop
from tornadows import soaphandler
from tornadows import xmltypes
from tornadows import webservices
from tornadows import complextypes
from tornadows.soaphandler import webservice

""" This web services shows how uses complextypes and classes python.

	User is a python class with two attributes:
		username : is a python str type with the username.
		roles    : is a python list of str (roles for the username).

	ListOfUser is another class with two attributes:
		idlist : is a python str type.
		roles  : is a python list of User (python class).

"""
class User(complextypes.ComplexType):
	username = str
	roles = [str]

class ListOfUser(complextypes.ComplexType):
	idlist = int
	list = [User]

class UserRolesService(soaphandler.SoapHandler):
	@webservice(_params=xmltypes.Integer,_returns=ListOfUser)
	def getUsers(self, idlist):
		user1 = User()
		user1.username = 'steve'
		user1.roles = ['ceo','admin']
		
		user2 = User()
		user2.username = 'billy'
		user2.roles = ['developer']

		listusers = ListOfUser()
		listusers.idlist = idlist
		listusers.list = [user1, user2]

		return listusers
	
if __name__ == '__main__':
	service = [('UserRolesService',UserRolesService)]
	app = webservices.WebService(service)
	ws  = tornado.httpserver.HTTPServer(app)
	ws.listen(8080)
	tornado.ioloop.IOLoop.instance().start()

########NEW FILE########
__FILENAME__ = complextypes
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" Implementation of module with classes and functions for transform python 
    classes in xml schema: 

    See the next example:

    	from tornadows.complextypes import ComplexType, StringProperty, IntegerProperty

    	class Person(ComplexType):
		name = StringProperty()
		age  = IntegerProperty()

	or you can use some python types

	class Person(ComplexType):
		name = str
		age  = int

	is equivalent to:

	 <xsd:complexType name="Person">
		<xsd:sequence>
			<xsd:element name="name" type="xsd:string"/>
			<xsd:element name="age" type="xsd:integer"/> 
		</xsd:sequence>
	 </xsd:complexType>

"""

import tornadows.xmltypes
import xml.dom.minidom
import inspect
from datetime import date, datetime, time
	
class Property:
	""" Class base for definition of properties of the attributes of a python class """
	pass

class IntegerProperty(Property):
	""" Class for definitions of Integer Property """
	def __init__(self):
		self.type = tornadows.xmltypes.Integer
		self.value = None

class DecimalProperty(Property):
	""" Class for definitions of Decimal Property """
	def __init__(self):
		self.type = tornadows.xmltypes.Decimal
		self.value = None

class DoubleProperty(Property):
	""" Class for definitions of Double Property """
	def __init__(self):
		self.type = tornadows.xmltypes.Double
		self.value = None

class FloatProperty(Property):
	""" Class for definitions of Float Property """
	def __init__(self):
		self.type = tornadows.xmltypes.Float
		self.value = None

class DurationProperty(Property):
	""" Class for definitions of Duration Property """
	def __init__(self):
		self.type = tornadows.xmltypes.Duration
		self.value = None

class DateProperty(Property):
	""" Class for definitions of Date Property """
	def __init__(self):
		self.type = tornadows.xmltypes.Date
		self.value = None

class TimeProperty(Property):
	""" Class for definitions of Time Property """
	def __init__(self):
		self.type = tornadows.xmltypes.Time
		self.value = None

class DateTimeProperty(Property):
	""" Class for definitions of DateTime Property """
	def __init__(self):
		self.type = tornadows.xmltypes.DateTime
		self.value = None

class StringProperty(Property):
	""" Class for definitions of String Property """
	def __init__(self):
		self.type = tornadows.xmltypes.String
		self.value = None

class BooleanProperty(Property):
	""" Class for definitions of Boolean Property """
	def __init__(self):
		self.type = tornadows.xmltypes.Boolean
		self.value = None

class ArrayProperty(list):
	""" For create a list of classes """
	def __init__(self, object, minOccurs = 1, maxOccurs=None, data=[]):
		list.__init__(self,data)
		self._minOccurs = minOccurs
		self._maxOccurs = maxOccurs
		self._object = object
		self.append(self._object)
		
	def toXSD(self,namespace='xsd',nameelement=None):
		""" Create xml complex type for ArrayProperty """
		xsd = self._object.toXSD()
		if self._maxOccurs == None:
			xsd += '<%s:element name="%s" type="tns:%s" minOccurs="%s"/>'%(namespace,nameelement,self._object.getName(),self._minOccurs)
		elif self._maxOccurs != None:
			xsd += '<%s:element name="%s" type="tns:%s" minOccurs="%s" maxOccurs="%s"/>'%(namespace,nameelement,self._object.getName(),str(self._minOccurs),str(self._maxOccurs))
		return xsd

class ComplexType(object):
	""" Base class for definitions of python class like xml document and schema:

	    from tornadows.complextypes import ComplexType,StringProperty, IntegerProperty

	    class Person(ComplexType):
		name = StringProperty
		age  = IntegerProperty
	
	    if __name__ == '__main__':
		print 'XML Schema : '
		print(Person.toXSD())
		
		p = Person()
		p.name.value = 'Steve J'
		p.age.value  = 38

		print('XML Document : ')
		print(p.toXML())

	    or you if you want to use some python types (int, str, float, bool)

	    from tornadows.complextypes import ComplexType

	    class Person(ComplexType):
		name = str 
		age  = int
	
	    if __name__ == '__main__':
		print('XML Schema : ')
		print(Person.toXSD())
		
		p = Person()
		p.name.value = 'Steve J'
		p.age.value  = 38

		print('XML Document : ')
		print(p.toXML())

	"""
	def __init__(self):
		""" Class constructor for ComplexType """
		default_attr = dir(type('default',(object,),{}))
		for attr in self.__class__.__dict__.keys():
			if default_attr.count(attr) > 0 or callable(attr):
				continue	
			else:
				element = self.__class__.__dict__[attr]
				typeobj = self._createAttributeType(element)
				setattr(self,attr,typeobj)

	def toXML(self,name=None):
		""" Method that creates the XML document for the instance of python class.
		    Return a string with the xml document.
		 """
		nameroot = None

		if name == None:
			nameroot = self.__class__.__name__
		else:
			nameroot = name

		xml = '<%s>'%nameroot
		default_attr = dir(type('default',(object,),{}))
		for key in dir(self):
			if default_attr.count(key) > 0:
				continue
			element = findElementFromDict(self.__dict__,key)
			if element == None:
				continue
			if isinstance(element,list):
				for e in element:
					if isinstance(e,ComplexType):
						xml += e.toXML(name=key)
					else:
						xml += '<%s>%s</%s>'%(key,e,key)
			elif isinstance(element,Property):
				xml += '<%s>%s</%s>'%(key,element.value,key)
			elif isinstance(element,ComplexType):
				xml += element.toXML(name=key)
			else:
				xml += '<%s>%s</%s>'%(key,convert(type(element).__name__,element),key)
		xml += '</%s>'%nameroot
		return str(xml)
					
	@classmethod
	def toXSD(cls,xmlns='http://www.w3.org/2001/XMLSchema',namespace='xsd',method='', ltype=[]):
		""" Class method that creates the XSD document for the python class.
		    Return a string with the xml schema.
		 """
		name = cls.__name__
		xsd  = cls._generateXSD(ltype=ltype)
		return xsd
		
	@classmethod	
	def _generateXSD(cls,xmlns='http://www.w3.org/2001/XMLSchema',namespace='xsd', ltype=[]):
		""" Class method for get the xml schema with the document definition.
		    Return a string with the xsd document.
		 """
		default_attr = dir(type('default',(object,),{}))
		name = cls.__name__
		xsd  = '<%s:complexType name="%s" xmlns:%s="%s">'%(namespace,name,namespace,xmlns)
		xsd += '<%s:sequence>'%namespace
		complextype = []

		for key in dir(cls):
			if default_attr.count(key) > 0:
				continue
			element = findElementFromDict(cls.__dict__,key)
			if element == None:
				continue
			if isinstance(element,Property):
				xsd += element.type.createElement(str(key))
			
			elif isinstance(element,ComplexType): 
				nameinstance = key

				if ltype.count(self._elementInput.getName()) == 0:
					ltype.append(self._elementInput.getName())
					complextype.append(element._generateXSD())
				
				xsd += '<%s:element name="%s" type="tns:%s"/>'%(namespace,nameinstance,element.getName())			
			elif inspect.isclass(element) and issubclass(element,ComplexType): 
				nameinstance = key
				
				if ltype.count(element.getName()) == 0:
					ltype.append(element.getName())
					complextype.append(element._generateXSD())
				
				xsd += '<%s:element name="%s" type="tns:%s"/>'%(namespace,nameinstance,element.getName())			
			elif isinstance(element,ArrayProperty):
				if isinstance(element[0],ComplexType) or issubclass(element[0],ComplexType):
					complextype.append(element[0]._generateXSD())
					xsd += '<%s:element name="%s" type="tns:%s" maxOccurs="unbounded"/>'%(namespace,key,element[0].__name__)	
				else:
					typeelement = createPythonType2XMLType(element[0].__name__)
					xsd += '<%s:element name="%s" type="%s:%s" maxOccurs="unbounded"/>'%(namespace,key,namespace,typeelement)	
			
			elif isinstance(element,list):
				if isinstance(element[0],ComplexType) or issubclass(element[0],ComplexType):

					if ltype.count(element[0].__name__) == 0:
						ltype.append(element[0].__name__)
						complextype.append(element[0]._generateXSD())
					
					xsd += '<%s:element name="%s" type="tns:%s" maxOccurs="unbounded"/>'%(namespace,key,element[0].__name__)	
				else:
					typeelement = createPythonType2XMLType(element[0].__name__)
					xsd += '<%s:element name="%s" type="%s:%s" maxOccurs="unbounded"/>'%(namespace,key,namespace,typeelement)	
			elif hasattr(element,'__name__'):
				typeelement = createPythonType2XMLType(element.__name__)
				xsd += '<%s:element name="%s" type="%s:%s"/>'%(namespace,str(key),namespace,typeelement)

		xsd += '</%s:sequence>'%namespace
		xsd += '</%s:complexType>'%namespace
		
		if len(complextype) > 0:
			for ct in complextype:
				xsd += ct
				
		return xsd
		
	@classmethod
	def getName(cls):
		""" Class method return the name of the class """
		return cls.__name__
		
	@classmethod	
	def _createAttributeType(self,element):
		""" Class method to create the types of the attributes of a ComplexType """
		if isinstance(element,list):
			return list()
		elif isinstance(element,IntegerProperty):
			return IntegerProperty()
		elif isinstance(element,DecimalProperty):
			return DecimalProperty()
		elif isinstance(element,DoubleProperty):
			return DoubleProperty()
		elif isinstance(element,FloatProperty):
			return FloatProperty()
		elif isinstance(element,DurationProperty):
			return DurationProperty()
		elif isinstance(element,DateProperty):
			return DateProperty()
		elif isinstance(element,TimeProperty):
			return TimeProperty()
		elif isinstance(element,DateTimeProperty):
			return DateTimeProperty()
		elif isinstance(element,StringProperty):
			return StringProperty()
		elif isinstance(element,BooleanProperty):
			return BooleanProperty()
		elif issubclass(element,ComplexType):
			return element()
		else:
			if   element.__name__ == 'int':	
				return int
			elif element.__name__ == 'decimal':
				return float
			elif element.__name__ == 'double':
				return float
			elif element.__name__ == 'float':
				return float
			elif element.__name__ == 'duration':
				return str
			elif element.__name__ == 'date':
				return date
			elif element.__name__ == 'time':
				return time
			elif element.__name__ == 'dateTime':
				return datetime
			elif element.__name__ == 'str':
				return str
			elif element.__name__ == 'bool':
				return bool

def xml2object(xml,xsd,complex,method=''):
	""" Function that converts a XML document in a instance of a python class """
	namecls = complex.getName()
	types   = xsd2dict(xsd)
	lst     = xml2list(xml,namecls,types,method=method)
	tps     = cls2dict(complex)
	obj     = generateOBJ(lst,namecls,tps)
	return obj

def cls2dict(complex):
	""" Function that creates a dictionary from a ComplexType class with the attributes and types """
	default_attr = dir(type('default',(object,),{}))
	dct = {}
	for attr in dir(complex):
		if default_attr.count(attr) > 0 or callable(attr):
			continue
		else:
			elem = findElementFromDict(complex.__dict__,attr)
			if elem != None:
				dct[attr] = elem
	return dct

def xsd2dict(xsd,namespace='xsd'):
	""" Function that creates a dictionary from a xml schema with the type of element """
	types = ['xsd:integer','xsd:decimal','xsd:double','xsd:float','xsd:duration','xsd:date','xsd:time','xsd:dateTime','xsd:string','xsd:boolean']
	dct = {}

	element = '%s:element'%namespace
	elems = xsd.getElementsByTagName(element)
	for e in elems:
		val = 'complexType'
		typ = str(e.getAttribute('type'))
		lst = e.hasAttribute('maxOccurs')
		if types.count(typ) > 0:
			val = 'element'
		dct[str(e.getAttribute('name'))] = (val,typ,lst)
	return dct

def xml2list(xmldoc,name,types,method=''):
	""" Function that creates a list from xml documento with a tuple element and value """
	name = name+method
	
	x = xml.dom.minidom.parseString(xmldoc)
	c = None
	if x.documentElement.prefix != None:
		c = x.getElementsByTagName(x.documentElement.prefix+':'+name)
	else:
		c = x.getElementsByTagName(name)
	attrs = genattr(c)
	lst = []
	for a in attrs:
		t = types[a.nodeName]
		typ = t[0]
		typxml = t[1]
		isarray = t[2]
		if typ == 'complexType' or typ == 'list':
			l = xml2list(a.toxml(),str(a.nodeName),types)
			lst.append((str(a.nodeName),l,isarray))
		else:
			val = None
			if len(a.childNodes) > 0:
				val = convert(typxml,str(a.childNodes[0].nodeValue))
				# Convert str to bool.
				if val == 'true':
					val = True
				elif val == 'false':
					val = False
			lst.append((str(a.nodeName),val,isarray))
	return lst

def generateOBJ(d,namecls,types):
	""" Function that creates a object from a xml document """
	dct = {}
	lst = []
	for a in d:
		name  = a[0]
		value = a[1]
		isarray = a[2]
		if isinstance(value,list):
			o = generateOBJ(value,name,types)
			if isarray:
				lst.append(o)
				dct[name] = lst
			else:
				dct[name] = o
		else:
			typ = findElementFromDict(types,name)
			if isinstance(typ,Property):
				dct[name] = createProperty(typ,value)
			else:
				dct[name] = value
	return type(namecls,(ComplexType,),dct)
	
def createProperty(typ,value):
	""" Function that creates a Property class instance, with the value """
	ct = None
	if isinstance(typ,IntegerProperty):
		ct = IntegerProperty()
		ct.value = tornadows.xmltypes.Integer.genType(value)
	elif isinstance(typ,DecimalProperty):
		ct = DecimalProperty()
		ct.value = tornadows.xmltypes.Decimal.genType(value)
	elif isinstance(typ,DoubleProperty):
		ct = DoubleProperty()
		ct.value = tornadows.xmltypes.Double.genType(value)
	elif isinstance(typ,FloatProperty):
		ct = FloatProperty()
		ct.value = tornadows.xmltypes.Float.genType(value)
	elif isinstance(typ,DurationProperty):
		ct = DurationProperty()
		ct.value = tornadows.xmltypes.Duration.genType(value)
	elif isinstance(typ,DateProperty):
		ct = DateProperty()
		ct.value = tornadows.xmltypes.Date.genType(value)
	elif isinstance(typ,TimeProperty):
		ct = TimeProperty()
		ct.value = tornadows.xmltypes.Time.genType(value)
	elif isinstance(typ,DateTimeProperty):
		ct = DateTimeProperty()
		ct.value = tornadows.xmltypes.DateTime.genType(value)
	elif isinstance(typ,StringProperty):
		ct = StringProperty()
		ct.value = tornadows.xmltypes.String.genType(value)
	elif isinstance(typ,BooleanProperty):
		ct = BooleanProperty()
		ct.value = tornadows.xmltypes.Boolean.genType(value)

	return ct

def genattr(elems):
	""" Function that generates a list with the childnodes of a xml element  """
	d = []
	for e in elems[0].childNodes:
		if e.nodeType == e.ELEMENT_NODE:
			d.append(e)
	return d

def findElementFromDict(dictionary,key):
	""" Function to find a element into a dictionary for the key """
	element = None
	try:
		element = dictionary[key]
		return element
	except KeyError:
		return None

def convert(typeelement,value):
	""" Function that converts a value depending his type """
	if typeelement == 'xsd:integer' or typeelement == 'int':	
		return int(value)
	elif typeelement == 'xsd:decimal':
		return float(value)
	elif typeelement == 'xsd:double':
		return float(value)
	elif typeelement == 'xsd:float' or typeelement == 'float':
		return float(value)
	elif typeelement == 'xsd:duration':
		return str(value)
	elif typeelement == 'xsd:date' or typeelement == 'date':
		sdate = str(value).split('-')
		return date(int(sdate[0]),int(sdate[1]),int(sdate[2]))
	elif typeelement == 'xsd:time' or typeelement == 'time':
		stime = str(value).split(':')
		hour = stime[0]
		min  = stime[1]
		seg  = '00'
		if len(stime) >= 3:
			seg = stime[2].split('.')[0]
		return time(int(hour),int(min),int(seg))
	elif typeelement == 'xsd:dateTime' or typeelement == 'datetime':
		sdatetime = str(value).replace('T','-').replace(' ','-').replace('+','-').split('-')
		year  = sdatetime[0]
		mon   = sdatetime[1]
		day   = sdatetime[2]
		stime = sdatetime[3].split(':')
		hour  = stime[0]
		min   = stime[1]
		seg   = '00'
		if len(stime) >= 3:
			seg = stime[2].split('.')[0]
		return datetime(int(year),int(mon),int(day),int(hour),int(min),int(seg)).isoformat('T')
	elif typeelement == 'xsd:string' or typeelement == 'str' or typeelement == 'unicode':
		return str(value)
	elif typeelement == 'xsd:boolean' or typeelement == 'bool':
		return str(value).lower()

def createPythonType2XMLType(pyType):
	""" Function that creates a xml type from a python type """
	xmlType = None
	if pyType == 'int':
		xmlType = 'integer'
	elif pyType == 'decimal':
		xmlType = 'decimal'
	elif pyType == 'double':
		xmlType = 'float'				
	elif pyType == 'float':
		xmlType = 'float'
	elif pyType == 'duration':
		xmlType = 'duration'
	elif pyType == 'date':
		xmlType = 'date'
	elif pyType == 'time':
		xmlType = 'time'
	elif pyType == 'datetime':
		xmlType = 'dateTime'
	elif pyType == 'str':
		xmlType = 'string'
	elif pyType == 'bool':
		xmlType = 'boolean'
		
	return xmlType


########NEW FILE########
__FILENAME__ = soap
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" Implementation of a envelope soap 1.1 """

import xml.dom.minidom

class SoapMessage:
	""" Implementation of a envelope soap 1.1 with minidom API

		import tornadows.soap
		import xml.dom.minidom

		soapenvelope = tornadows.soap.SoapMessage()
		xmlDoc = xml.dom.minidom.parseString('<Doc>Hello, world!!!</Doc>')
		soapenvelope.setBody(xmlDoc)
		for s in soapenvelope.getBody():
			print s.toxml()

	"""
	def __init__(self):
		self._soap = xml.dom.minidom.Document()
		envurl = 'http://schemas.xmlsoap.org/soap/envelope/'
		self._envelope = self._soap.createElementNS(envurl, 'soapenv:Envelope')
		self._envelope.setAttribute('xmlns:soapenv', envurl)
		self._envelope.setAttribute('xmlns:xsi',
				"http://www.w3.org/2001/XMLSchema-instance")
		self._envelope.setAttribute('xsi:schemaLocation',
				' '.join((envurl, envurl)))
		self._soap.appendChild(self._envelope)
		self._header = self._soap.createElement('soapenv:Header')
		self._body   = self._soap.createElement('soapenv:Body')
		self._envelope.appendChild(self._header)
		self._envelope.appendChild(self._body)

	def getSoap(self):
		""" Return the soap envelope as xml.dom.minidom.Document 
		    getSoap() return a xml.dom.minidom.Document object
		"""
		return self._soap

	def getHeader(self):
		""" Return the child elements of Header element 
		    getHeader() return a list with xml.dom.minidom.Element objects
		"""
		return self._header.childNodes

	def getBody(self):
		""" Return the child elements of Body element 
		    getBody() return a list with xml.dom.minidom.Element objects
		"""
		return self._body.childNodes

	def setHeader(self, header):
		""" Set the child content to Header element
		    setHeader(header), header is a xml.dom.minidom.Document object
		 """
		if isinstance(header,xml.dom.minidom.Document):
			self._header.appendChild(header.documentElement)
		elif isinstance(header,xml.dom.minidom.Element):
			self._header.appendChild(header)

	def setBody(self,body):
		""" Set the child content to Body element 
		    setBody(body), body is a xml.dom.minidom.Document object or
		    a xml.dom.minidom.Element
		"""
		if isinstance(body,xml.dom.minidom.Document):
			self._body.appendChild(body.documentElement)
		elif isinstance(body,xml.dom.minidom.Element):
			self._body.appendChild(body)

	def removeHeader(self):
		""" Remove the last child elements from Header element """
		lastElement = self._header.lastChild
		if lastElement != None:
			self._header.removeChild(lastElement)

	def removeBody(self):
		""" Remove last child elements from Body element """
		lastElement = self._body.lastChild
		if lastElement != None:
			self._body.removeChild(lastElement)

########NEW FILE########
__FILENAME__ = soaphandler
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" Implementation of soaphandler for webservices API 0.9.4.2 (Beta) """

import tornado.httpserver
import tornado.web
import xml.dom.minidom
import string
import inspect
from tornado.options import options
from tornadows import soap
from tornadows import xmltypes
from tornadows import complextypes
from tornadows import wsdl

""" Global variable. If you want use your own wsdl file """
wsdl_path = None

def webservice(*params,**kwparams):
	""" Decorator method for web services operators """
	def method(f):
		_input = None
		_output = None
		_inputArray = False
		_outputArray = False
		_args = None
		if len(kwparams):
			_params = kwparams['_params']
			if inspect.isclass(_params) and issubclass(_params,complextypes.ComplexType):
				_args = inspect.getargspec(f).args[1:]
				_input = _params
			elif isinstance(_params,list):
				_args = inspect.getargspec(f).args[1:]
				_input = {}
				i = 0
				for arg in _args:
					_input[arg] = _params[i]
					i+=1
			else:
				_args = inspect.getargspec(f).args[1:]
				_input = {}
				for arg in _args:
					_input[arg] = _params
				if isinstance(_params,xmltypes.Array):
					_inputArray = True

			_returns = kwparams['_returns']
			if isinstance(_returns,xmltypes.Array):
				_output = _returns
				_outputArray = True
			elif isinstance(_returns,list) or issubclass(_returns,xmltypes.PrimitiveType) or issubclass(_returns,complextypes.ComplexType):
				_output = _returns
			else:
				_output = _returns
		def operation(*args,**kwargs):
			return f(*args,**kwargs)

		operation.__name__ = f.__name__
		operation._is_operation = True
		operation._args = _args
		operation._input = _input
		operation._output = _output
		operation._operation = f.__name__
		operation._inputArray = _inputArray
		operation._outputArray = _outputArray
		
		return operation
	return method

def soapfault(faultstring):
	""" Method for generate a soap fault
	    soapfault() return a SoapMessage() object with a message 
	    for Soap Envelope
	 """
	fault = soap.SoapMessage()
	faultmsg  = '<soapenv:Fault xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope">\n'
	faultmsg += '<faultcode></faultcode>\n'
	faultmsg += '<faultstring>%s</faultstring>\n'%faultstring
	faultmsg += '</soapenv:Fault>\n'
	fault.setBody(xml.dom.minidom.parseString(faultmsg))
	return fault

class SoapHandler(tornado.web.RequestHandler):
	""" This subclass extends tornado.web.RequestHandler class, defining the 
	    methods get() and post() for handle a soap message (request and response).
	"""
	def get(self):
		""" Method get() returned the WSDL. If wsdl_path is null, the
		    WSDL is generated dinamically.
		"""
		if hasattr(options,'wsdl_hostname') and type(options.wsdl_hostname) is str:
			address = options.wsdl_hostname
		else:
			address = getattr(self, 'targetns_address',tornado.httpserver.socket.gethostbyname(tornado.httpserver.socket.gethostname()))
		
		port = 80 # if you are using the port 80
		if len(self.request.headers['Host'].split(':')) >= 2:
			port = self.request.headers['Host'].split(':')[1]
		wsdl_nameservice = self.request.uri.replace('/','').replace('?wsdl','').replace('?WSDL','')
		wsdl_input       = None
		wsdl_output      = None
		wsdl_operation   = None
		wsdl_args        = None
		wsdl_methods     = []

		for operations in dir(self):
			operation = getattr(self,operations)
			if callable(operation) and hasattr(operation,'_input') and hasattr(operation,'_output') and hasattr(operation,'_operation') \
			   and hasattr(operation,'_args') and hasattr(operation,'_is_operation'):
				wsdl_input     = getattr(operation,'_input')
				wsdl_output    = getattr(operation,'_output')
				wsdl_operation = getattr(operation,'_operation')
				wsdl_args      = getattr(operation,'_args')
				wsdl_data      = {'args':wsdl_args,'input':('params',wsdl_input),'output':('returns',wsdl_output),'operation':wsdl_operation}
				wsdl_methods.append(wsdl_data)

		wsdl_targetns = 'http://%s:%s/%s'%(address,port,wsdl_nameservice)
		wsdl_location = 'http://%s:%s/%s'%(address,port,wsdl_nameservice)
		query = self.request.query
		self.set_header('Content-Type','application/xml; charset=UTF-8')
		if query.upper() == 'WSDL':
			if wsdl_path == None:
				wsdlfile = wsdl.Wsdl(nameservice=wsdl_nameservice,
						             targetNamespace=wsdl_targetns,
						             methods=wsdl_methods,
						             location=wsdl_location)

				self.finish(wsdlfile.createWsdl().toxml())
			else:
				fd = open(str(wsdl_path),'r')
				xmlWSDL = ''
				for line in fd:
					xmlWSDL += line
				fd.close()
				self.finish(xmlWSDL)

	def post(self):
		""" Method post() to process of requests and responses SOAP messages """
		try:
			self._request = self._parseSoap(self.request.body)
			soapaction = self.request.headers['SOAPAction'].replace('"','')
			self.set_header('Content-Type','text/xml')
			for operations in dir(self):
				operation = getattr(self,operations)
				method = ''
				if callable(operation) and hasattr(operation,'_is_operation'):
					num_methods = self._countOperations()
					if hasattr(operation,'_operation') and soapaction.endswith(getattr(operation,'_operation')) and num_methods > 1:
						method = getattr(operation,'_operation') 
						self._response = self._executeOperation(operation,method=method)
						break
					elif num_methods == 1:
						self._response = self._executeOperation(operation,method='')
						break

			soapmsg = self._response.getSoap().toxml()
			self.write(soapmsg)
		except Exception as detail:
			fault = soapfault('Error in web service : %s'%detail)
			self.write(fault.getSoap().toxml())

	def _countOperations(self):
		""" Private method that counts the operations on the web services """
		c = 0
		for operations in dir(self):
			operation = getattr(self,operations)
			if callable(operation) and hasattr(operation,'_is_operation'):
				c += 1	
		return c

	def _executeOperation(self,operation,method=''):
		""" Private method that executes operations of web service """
		params = []
		response = None
		res = None
		typesinput = getattr(operation,'_input')
		args  = getattr(operation,'_args')

		if inspect.isclass(typesinput) and issubclass(typesinput,complextypes.ComplexType):
			obj = self._parseComplexType(typesinput,self._request.getBody()[0],method=method)
			response = operation(obj)
		elif hasattr(operation,'_inputArray') and getattr(operation,'_inputArray'):
			params = self._parseParams(self._request.getBody()[0],typesinput,args)
			response = operation(params)
		else:
			params = self._parseParams(self._request.getBody()[0],typesinput,args)
			response = operation(*params)
		is_array = None
		if hasattr(operation,'_outputArray') and getattr(operation,'_outputArray'):
			is_array = getattr(operation,'_outputArray')
				
		typesoutput = getattr(operation,'_output')
		if inspect.isclass(typesoutput) and issubclass(typesoutput,complextypes.ComplexType):
			res = self._createReturnsComplexType(response)
		else:
			res = self._createReturns(response,is_array)
	
		return res

	def _parseSoap(self,xmldoc):
		""" Private method parse a message soap from a xmldoc like string
		    _parseSoap() return a soap.SoapMessage().
		"""
		xmldoc = bytes.decode(xmldoc)
		xmldoc = xmldoc.replace('\n',' ').replace('\t',' ').replace('\r',' ')
		document = xml.dom.minidom.parseString(xmldoc)
		prefix = document.documentElement.prefix
		namespace = document.documentElement.namespaceURI
		
		header = self._getElementFromMessage('Header',document)
		body   = self._getElementFromMessage('Body',document)

		header_elements = self._parseXML(header)
		body_elements = self._parseXML(body)
		
		soapMsg = soap.SoapMessage()
		for h in header_elements:
			soapMsg.setHeader(h)
		for b in body_elements:
			soapMsg.setBody(b)
		return soapMsg

	def _getElementFromMessage(self,name,document):
		""" Private method to search and return elements from XML """
		list_of_elements = []
		for e in document.documentElement.childNodes:
			if e.nodeType == e.ELEMENT_NODE and e.nodeName.count(name) >= 1:
				list_of_elements.append(e)
		return list_of_elements

	def _parseXML(self,elements):
		""" Private method parse and digest the xml.dom.minidom.Element 
		    finding the childs of Header and Body from soap message. 
		    Return a list object with all of child Elements.
		"""
		elem_list = []
		if len(elements) <= 0:
			return elem_list
		if elements[0].childNodes.length <= 0:
			return elem_list
		for element in elements[0].childNodes:
			if element.nodeType == element.ELEMENT_NODE:
				prefix = element.prefix
				namespace = element.namespaceURI
				if prefix != None and namespace != None:
					element.setAttribute('xmlns:'+prefix,namespace)
				else:
					element.setAttribute('xmlns:xsd',"http://www.w3.org/2001/XMLSchema")
					element.setAttribute('xmlns:xsi',"http://www.w3.org/2001/XMLSchema-instance")
				elem_list.append(xml.dom.minidom.parseString(element.toxml()))
		return elem_list

	def _parseComplexType(self,complex,xmld,method=''):
		""" Private method for generate an instance of class nameclass. """
		xsdd  = '<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
		xsdd += complex.toXSD(method=method,ltype=[])
		xsdd += '</xsd:schema>'
		xsd = xml.dom.minidom.parseString(xsdd)
		obj = complextypes.xml2object(xmld.toxml(),xsd,complex,method=method)

		return obj
	
	def _parseParams(self,elements,types=None,args=None):
		""" Private method to parse a Body element of SOAP Envelope and extract
		    the values of the request document like parameters for the soapmethod,
		    this method return a list values of parameters.
		 """
		values   = []
		for tagname in args:
			type = types[tagname]
			values += self._findValues(tagname,type,elements)
		return values		

	def _findValues(self,name,type,xml):
		""" Private method to find the values of elements in the XML of input """
		elems = xml.getElementsByTagName(name)
		values = []
		for e in elems:
			if e.hasChildNodes and len(e.childNodes) > 0:
				v = None
				if inspect.isclass(type) and (issubclass(type,xmltypes.PrimitiveType) or isinstance(type,xmltypes.Array)):
					v = type.genType(e.childNodes[0].nodeValue)
				elif hasattr(type,'__name__') and (not issubclass(type,xmltypes.PrimitiveType) or not isinstance(type,xmltypes.Array)):
					v = complextypes.convert(type.__name__,e.childNodes[0].nodeValue)
				values.append(v)
			else:
				values.append(None)
		return values

	def _createReturnsComplexType(self,result):
		""" Private method to generate the xml document with the response. 
		    Return an SoapMessage() with XML document.
		"""
		response = xml.dom.minidom.parseString(result.toXML())
		
		soapResponse = soap.SoapMessage()
		soapResponse.setBody(response)
		return soapResponse
			
	def _createReturns(self,result,is_array):
		""" Private method to generate the xml document with the response. 
		    Return an SoapMessage().
		"""
		xmlresponse = ''
		if isinstance(result,list):
			xmlresponse = '<returns>\n'
			i = 1
			for r in result:
				if is_array == True:
					xmlresponse += '<value>%s</value>\n'%str(r)
				else:
					xmlresponse += '<value%d>%s</value%d>\n'%(i,str(r),i)
				i+=1
			xmlresponse += '</returns>\n'
		else:
			xmlresponse = '<returns>%s</returns>\n'%str(result)
	
		response = xml.dom.minidom.parseString(xmlresponse)

		soapResponse = soap.SoapMessage()
		soapResponse.setBody(response)
		return soapResponse

########NEW FILE########
__FILENAME__ = webservices
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" Implementation of webservices API 0.9 """

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.wsgi

class WebService(tornado.web.Application):
	""" A implementation of web services for tornado web server.

		import tornado.httpserver
		import tornado.ioloop
		from tornadows import webservices
		from tornadows import xmltypes
	   	from tornadows import soaphandler
		from tornadows.soaphandler import webservice
 
		class MyService(soaphandler.SoapHandler):
			@webservice(_params=[xmltypes.Integer, xmltypes.Integer],_returns=xmltypes.Integer)
			def sum(self, value1, value2):
				result = value1 + value2
	
				return result  

		if __name__ == "__main__":
			app = webservices.WebService("MyService",MyService)
			ws_server = tornado.httpserver.HTTPServer(app)
			ws_server.listen(8080)
			tornado.ioloop.IOLoop.instance().start()
		
	"""
	def __init__(self,services,object=None,wsdl=None):
		""" Initializes the application for web services

		    Instances of this class are callable and can be passed to
		    HTTPServer of tornado to serve the web services.

		    The constructor for this class takes the name for the web 
		    service (service), the class with the web service (object) 
		    and wsdl with the wsdl file path (if this exist).
		 """
		if isinstance(services,list) and object == None:
			srvs = []
			for s in services:
				srv = s[0]
				obj = s[1]
				srvs.append((r"/"+str(srv),obj))
				srvs.append((r"/"+str(srv)+"/",obj))
			tornado.web.Application.__init__(self,srvs)
		else:
			self._service = services
			self._object = object
			self._services = [(r"/"+str(self._service),self._object),
					  (r"/"+str(self._service)+"/",self._object),]
			tornado.web.Application.__init__(self,self._services)

class WSGIWebService(tornado.wsgi.WSGIApplication):
	""" A implementation of web services for tornado web server.

		import tornado.httpserver
		import tornado.ioloop
		from tornadows import webservices
		from tornadows import xmltypes
	   	from tornadows import soaphandler
		from tornadows.soaphandler import webservice
		import wsgiref.simple_server
 
		class MyService(soaphandler.SoapHandler):
			@webservice(_params=[xmltypes.Integer, xmltypes.Integer],_returns=xmltypes.Integer)
			def sum(self, value1, value2):
				result = value1 + value2
	
				return result  

		if __name__ == "__main__":
			app = webservices.WSGIWebService("MyService",MyService)
			server = wsgiref.simple_server.make_server('',8888,app)
			server.serve_forever()
	"""
	def __init__(self,services,object=None,wsdl=None, default_host="", **settings):
		""" Initializes the application for web services

		    Instances of this class are callable and can be passed to
		    HTTPServer of tornado to serve the web services.

		    The constructor for this class takes the name for the web 
		    service (service), the class with the web service (object) 
		    and wsdl with the wsdl file path (if this exist).
		 """
		if isinstance(services,list) and object == None:
			srvs = []
			for s in services:
				srv = s[0]
				obj = s[1]
				srvs.append((r"/"+str(srv),obj))
				srvs.append((r"/"+str(srv)+"/",obj))
			tornado.wsgi.WSGIApplication.__init__(self,srvs,default_host, **settings)
		else:
			self._service = services
			self._object = object
			self._services = [(r"/"+str(self._service),self._object),
					  (r"/"+str(self._service)+"/",self._object),]
			tornado.wsgi.WSGIApplication.__init__(self,self._services,default_host, **settings)

########NEW FILE########
__FILENAME__ = wsdl
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" Class Wsdl to generate WSDL Document """
import xml.dom.minidom
import inspect
from tornadows import xmltypes
from tornadows import complextypes

class Wsdl:
	""" ToDO:
		- Incorporate exceptions for parameters inputs.
		- When elementInput and/or elementOutput are empty trigger a exception.
	"""
	def __init__(self,nameservice=None,targetNamespace=None,methods=None,location=None):
		self._nameservice = nameservice
		self._namespace = targetNamespace
		self._methods   = methods
		self._location = location

	def createWsdl(self):
		""" Method that allows create the wsdl file """
		typeInput  = None
		typeOutput = None
		types  = '<wsdl:types>\n'
		types += '<xsd:schema targetNamespace="%s">\n'%self._namespace

		namespace = 'xsd'
		types_list = []
		ltype = []
		for wsdl_data in self._methods:
			self._arguments = wsdl_data['args']
			self._elementNameInput = wsdl_data['input'][0]
			self._elementInput = wsdl_data['input'][1]
			self._elementNameOutput = wsdl_data['output'][0]
			self._elementOutput = wsdl_data['output'][1]
			self._operation = wsdl_data['operation']

			method = self._operation

			if len(self._methods) == 1:
				method = ''

			if inspect.isclass(self._elementInput) and issubclass(self._elementInput,complextypes.ComplexType): 
				typeInput = self._elementInput.getName()+method
				
				if ltype.count(self._elementInput.getName()) == 0:
					ltype.append(self._elementInput.getName())
					types += self._elementInput.toXSD(method=method,ltype=ltype)
					
				types += '<%s:element name="%s" type="tns:%s"/>'%(namespace,typeInput,self._elementInput.getName())

			elif isinstance(self._elementInput,dict):
				typeInput = self._elementNameInput+method
				types += self._createComplexTypes(self._elementNameInput+method, self._arguments, self._elementInput)
			elif isinstance(self._elementInput,xmltypes.Array):
				typeInput  = self._elementNameInput+method
				types += self._elementInput.createArray(typeInput)			
			elif isinstance(self._elementInput,list) or inspect.isclass(self._elementInput) and issubclass(self._elementInput,xmltypes.PrimitiveType):
				typeInput  = self._elementNameInput+method
				types += self._createTypes(typeInput,self._elementInput)			
			else: # In case if _elementNameInput is a datatype of python (str, int, float, datetime, etc.) or None
				typeInput  = self._elementNameInput+method
				types += self._createTypes(typeInput,self._elementInput)

			if inspect.isclass(self._elementOutput) and issubclass(self._elementOutput,complextypes.ComplexType): 
				typeOutput = self._elementOutput.getName()+method

				if ltype.count(self._elementOutput.getName()) == 0:
					ltype.append(self._elementOutput.getName())
					types += self._elementOutput.toXSD(method=method,ltype=ltype)

				types += '<%s:element name="%s" type="tns:%s"/>'%(namespace,typeOutput,self._elementOutput.getName())

			elif isinstance(self._elementOutput,xmltypes.Array):
				typeOutput = self._elementNameOutput+method
				types += self._elementOutput.createArray(typeOutput)
			elif isinstance(self._elementOutput,list) or inspect.isclass(self._elementOutput) and issubclass(self._elementOutput,xmltypes.PrimitiveType):
				typeOutput = self._elementNameOutput+method
				types += self._createTypes(typeOutput,self._elementOutput)
			else: # In case if _elementNameOutput is a datatype of python (str, int, float, datetime, etc.) or None
				typeOutput = self._elementNameOutput+method
				types += self._createTypes(typeOutput,self._elementOutput)

			types_list.append({'typeInput':typeInput,'typeOutput':typeOutput,'method':method})

		types += '</xsd:schema>\n'
		types += '</wsdl:types>\n'
		
		messages = ''
		
		for t in types_list:
			typeInput = t['typeInput']
			typeOutput = t['typeOutput']
			method = t['method']

			if len(types_list) == 1:
				method = ''

			messages += '<wsdl:message name="%sRequest%s">\n'%(self._nameservice,method)
			messages += '<wsdl:part name="parameters%s" element="tns:%s"/>\n'%(method,typeInput)
			messages += '</wsdl:message>\n'

			messages += '<wsdl:message name="%sResponse%s">\n'%(self._nameservice,method)
			messages += '<wsdl:part name="returns%s" element="tns:%s"/>\n'%(method,typeOutput)
			messages += '</wsdl:message>\n'

		portType  = '<wsdl:portType name="%sPortType">\n'%self._nameservice
		
		for wsdl_data in self._methods:
			self._operation = wsdl_data['operation']
			
			method = self._operation
			if len(self._methods) == 1:
				method = ''

			portType += '<wsdl:operation name="%s">\n'%self._operation
			portType += '<wsdl:input message="tns:%sRequest%s"/>\n'%(self._nameservice,method)
			portType += '<wsdl:output message="tns:%sResponse%s"/>\n'%(self._nameservice,method)
			portType += '</wsdl:operation>\n'
		
		portType += '</wsdl:portType>\n'

		binding  = '<wsdl:binding name="%sBinding" type="tns:%sPortType">\n'%(self._nameservice,self._nameservice)
		binding += '<soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>\n'

		for wsdl_data in self._methods:
			self._operation = wsdl_data['operation']

			binding += '<wsdl:operation name="%s">\n'%self._operation		
			binding += '<soap:operation soapAction="%s/%s" style="document"/>\n'%(self._location,self._operation)
			binding += '<wsdl:input><soap:body use="literal"/></wsdl:input>\n'
			binding += '<wsdl:output><soap:body use="literal"/></wsdl:output>\n'
			binding += '</wsdl:operation>\n'

		binding += '</wsdl:binding>\n'
		
		service  = '<wsdl:service name="%s">\n'%self._nameservice
		service += '<wsdl:port name="%sPort" binding="tns:%sBinding">\n'%(self._nameservice,self._nameservice)
		service += '<soap:address location="%s"/>\n'%self._location
		service += '</wsdl:port>\n'
		service += '</wsdl:service>\n'

		definitions  = '<wsdl:definitions name="%s"\n'%self._nameservice
		definitions  += 'xmlns:xsd="http://www.w3.org/2001/XMLSchema"\n'
		definitions  += 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
		definitions  += 'xmlns:tns="%s"\n'%self._namespace
		definitions  += 'xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/"\n'
		definitions  += 'xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"\n'
		definitions  += 'targetNamespace="%s">\n'%self._namespace
		definitions += types
		definitions += messages
		definitions += portType
		definitions += binding
		definitions += service
		definitions += '</wsdl:definitions>\n'
		wsdlXml = xml.dom.minidom.parseString(definitions)

		return wsdlXml

	def _createTypes(self, name, elements):
		""" Private method that creates the types for the elements of wsdl """
		elem = ''
		if isinstance(elements,list):
			elem = '<xsd:complexType name="%sParams">\n'%name
			elem += '<xsd:sequence>\n'
			elems = ''
			idx = 1
			for e in elements:
				if hasattr(e,'__name__'):
					elems += '<xsd:element name="value%d" type="xsd:%s"/>\n'%(idx,complextypes.createPythonType2XMLType(e.__name__))
				else:
					elems += e.createElement('value%s'%idx)+'\n'
				idx += 1
			elem += elems+'</xsd:sequence>\n'
			elem += '</xsd:complexType>\n'
			elem += '<xsd:element name="%s" type="tns:%sParams"/>\n'%(name,name)
		elif inspect.isclass(elements) and issubclass(elements,xmltypes.PrimitiveType):
			elem = elements.createElement(name)+'\n'
		elif hasattr(elements,'__name__'):
			elem += '<xsd:element name="%s" type="xsd:%s"/>\n'%(name,complextypes.createPythonType2XMLType(elements.__name__))

		return elem

	def _createComplexTypes(self, name, arguments, elements):
		""" Private method that creates complex types for wsdl """
		elem = ''
		if isinstance(elements,dict):
			elem = '<xsd:complexType name="%sTypes">\n'%name
			elem += '<xsd:sequence>\n'
			elems = ''
			for e in arguments:
				if  isinstance(elements[e],xmltypes.Array):
					elems += elements[e].createType(e)
				elif issubclass(elements[e],xmltypes.PrimitiveType):
					elems += elements[e].createElement(e)+'\n'
				else:
					elems += '<xsd:element name="%s" type="xsd:%s"/>\n'%(e,complextypes.createPythonType2XMLType(elements[e].__name__))
			elem += elems+'</xsd:sequence>\n'
			elem += '</xsd:complexType>\n'
			elem += '<xsd:element name="%s" type="tns:%sTypes"/>\n'%(name,name)
		elif issubclass(elements,xmltypes.PrimitiveType):
			elem = elements.createElement(name)+'\n'

		return elem

########NEW FILE########
__FILENAME__ = xmltypes
#!/usr/bin/env python
#
# Copyright 2011 Rodrigo Ancavil del Pino
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

""" 
	Are incorporated the primitive datatypes defined by XML.
	Array is defined for the use of array of elements and his respective datatype.
"""

import inspect
from tornadows import complextypes

def createElementXML(name,type,prefix='xsd'):
	""" Function used for the creation of xml elements. """
	return '<%s:element name="%s" type="%s:%s"/>'%(prefix,name,prefix,type)

def createArrayXML(name,type,prefix='xsd',maxoccurs=None):
	""" Function used for the creation of xml complexElements """
	complexType  = '<%s:complexType name="%sParams">\n'%(prefix,name)
	complexType += '<%s:sequence>\n'%prefix
	if maxoccurs == None:
		complexType += '<%s:element name="value" type="%s:%s" maxOccurs="unbounded"/>\n'%(prefix,prefix,type)
	else:
		complexType += '<%s:element name="value" type="%s:%s" maxOccurs="%d"/>\n'%(prefix,prefix,type,maxoccurs)
	complexType += '</%s:sequence>\n'%prefix
	complexType += '</%s:complexType>\n'%prefix
	complexType += '<%s:element name="%s" type="tns:%sParams"/>\n'%(prefix,name,name)
	return complexType

class Array:
	""" Create arrays of xml elements.
	    
	    Here an example:

	    @webservices(_params=xmltypes.Array(xmltypes.Integer),_returns=xmltypes.Integer)
	    def function(sefl, list_of_elements):
		for e in list_of_elements:
		# Do something with the element    
        	return len(list_of_elements)

	    xmltypes.Array(xmltype.Integer) generate an xml element into schema definition:
		<xsd:element name="arrayOfElement" type="xsd:integer" maxOccurs="unbounded"/>

	    this make the parameter of the function list_of_elements is a python list.

	    if you specify xmltypes.Array(xmltypes.Integer,10), is generated:
		<xsd:element name="arrayOfElement" type="xsd:integer" maxOccurs="10"/>
	"""
	def __init__(self,type,maxOccurs=None):
		self._type = type
		self._n    = maxOccurs

	def createArray(self,name):
		type = None
		if inspect.isclass(self._type) and not issubclass(self._type,PrimitiveType):
			type = complextypes.createPythonType2XMLType(self._type.__name__)
		else:
			type = self._type.getType(self._type)
		return createArrayXML(name,type,'xsd',self._n)

	def createType(self,name):
		prefix = 'xsd'
		type = None
		if inspect.isclass(self._type) and not issubclass(self._type,PrimitiveType):
			type = complextypes.createPythonType2XMLType(self._type.__name__)
		else:
			type = self._type.getType(self._type)
		maxoccurs = self._n
		complexType = ''
		if self._n == None:
			complexType += '<%s:element name="%s" type="%s:%s" maxOccurs="unbounded"/>\n'%(prefix,name,prefix,type)
		else:
			complexType += '<%s:element name="%s" type="%s:%s" maxOccurs="%d"/>\n'%(prefix,name,prefix,type,maxoccurs)
		return complexType

	def genType(self,v):
		value = None
		if inspect.isclass(self._type) and issubclass(self._type,PrimitiveType):
			value = self._type.genType(v)
		elif hasattr(self._type,'__name__'):
			value = complextypes.convert(self._type.__name__,v)
			# Convert str to bool
			if value == 'true':
				value = True
			elif value == 'false':
				value = False
		return value

class PrimitiveType:
	""" Class father for all derived types. """
	pass

class Integer(PrimitiveType):
	""" 1. XML primitive type : integer """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'integer')
	@staticmethod
	def getType(self):
		return 'integer'
	@classmethod
	def genType(self,v):
		return int(v)

class Decimal(PrimitiveType):
	""" 2. XML primitive type : decimal """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'decimal')
	@staticmethod
	def getType(self):
		return 'decimal'
	@classmethod
	def genType(self,v):
		return float(v)

class Double(PrimitiveType):
	""" 3. XML primitive type : double """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'double')
	@staticmethod
	def getType(self):
		return 'double'
	@classmethod
	def genType(self,v):
		return float(v)

class Float(PrimitiveType):
	""" 4. XML primitive type : float """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'float')
	@staticmethod
	def getType(self):
		return 'float'
	@classmethod
	def genType(self,v):
		return float(v)

class Duration(PrimitiveType):
	""" 5. XML primitive type : duration """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'duration')
	@staticmethod
	def getType(self):
		return 'duration'
	@classmethod
	def genType(self,v):
		return str(v)

class Date(PrimitiveType):
	""" 6. XML primitive type : date """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'date')
	@staticmethod
	def getType(self):
		return 'date'
	@classmethod
	def genType(self,v):
		return str(v)

class Time(PrimitiveType):
	""" 7. XML primitive type : time """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'time')
	@staticmethod
	def getType(self):
		return 'time'
	@classmethod
	def genType(self,v):
		return str(v)

class DateTime(PrimitiveType):
	""" 8. XML primitive type : dateTime """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'dateTime')
	@staticmethod
	def getType(self):
		return 'dateTime'
	@classmethod
	def genType(self,v):
		return str(v)

class String(PrimitiveType):
	""" 9. XML primitive type : string """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'string')
	@staticmethod
	def getType(self):
		return 'string'
	@classmethod
	def genType(self,v):
		return str(v)

class Boolean(PrimitiveType):
	""" 10. XML primitive type : boolean """
	@staticmethod
	def createElement(name,prefix='xsd'):
		return createElementXML(name,'boolean')
	@staticmethod
	def getType(self):
		return 'boolean'
	@classmethod
	def genType(self,v):
		return str(v).lower()

########NEW FILE########
