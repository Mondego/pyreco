__FILENAME__ = graph
import os
import json
from subprocess import check_output, CalledProcessError

#Constants
_TREE_PATH="data/graph/"

def renderGraph(query):
	"""
		Returns the path to a svg file that
		contains the graph render of the query.
		Creates the svg file itself if it 
		does not already exist.
	"""
	#Compute the hash of the query string
	qhash = hashFunc(query)

	if (not os.path.exists(_TREE_PATH+str(qhash))):

		#Create bucket if it doesn't already exist.
		os.makedirs(_TREE_PATH+str(qhash))

		#Create the lookup table for the bucket.
		bucketTableFile=open(_TREE_PATH+str(qhash)+"/lookup.json",'w')
		bucketTableFile.write("{}")
		bucketTableFile.close()

	#Load bucketTable
	bucketTableFile=open(_TREE_PATH+str(qhash)+"/lookup.json",'r+')
	bucketTable = json.loads(bucketTableFile.read())

	if query not in bucketTable.keys():

		#File is not cache! Create PNG in bucket.
		filename=str(len(os.listdir(_TREE_PATH+str(qhash))))+".svg"


		fn=query.split(",")[0]
		rest=query.split(",")[1:]
		myParams={i[0]:i[1] for i in map(lambda x:x.split("="),rest)}



		if not TeXToGraph(fn,_TREE_PATH+str(qhash),filename,myParams):
			#An error has occurred while rendering the LaTeX. 
			return open(handleTeXRenderError("An error has occurred while rendering LaTeX."))

		#Update bucketTable
		bucketTable[query]=filename

		#Write back to bucketTableFile
		bucketTableFile.seek(0)
		bucketTableFile.write(json.dumps(bucketTable))
		bucketTableFile.close()

	#Return path to newly created/existing file
	return open(_TREE_PATH+str(qhash)+"/"+bucketTable[query]).read()

def hashFunc(s):
	"""
	Call some hashfunc and return the result.
	Goes "hashy hashy".
	"""
	return abs(hash(s))

def TeXToGraph(fn,targetDir,name,paramsIn):
	"""
		Renders a graph in query to a svg in targetDir named name. Return true if successful, false if not.
	"""
	params={
		'xmin':-10,
		'xmax':10,
		'ymin':-10,
		'ymax':10,
		'xlabel':"x",
		'ylabel':"y",
	}
	for i in paramsIn:
		if i!='xlabel' and i !='ylabel':
			params[i]=int(paramsIn[i])
		else:
			params[i]=paramsIn[i]
	print params
	print fn
	try:
		check_output("./to_graph.sh {0} {1} {2} {3} {4} {5} {6} {7} {8}".format(fn,params['xmin'],params['xmax'],params['ymin'],params['ymax'],params['xlabel'],params['ylabel'],targetDir,name).split())
	except CalledProcessError:
		return False
	return True


def handleTeXRenderError(errorMsg):
	"""
		Handles an error encountered while attempting to render a TeX string
	"""
	print errorMsg
	return "assets/img/error.png"

########NEW FILE########
__FILENAME__ = settings
PRODUCTION=False
MIXPANEL_TOKEN=""

########NEW FILE########
__FILENAME__ = tex
import os
import json
from subprocess import check_output, CalledProcessError

#Constants
_TREE_PATH="data/tex/"


def renderTex(query):
	"""
		Returns the path to a svg file that
		contains the tex render of the query.
		Creates the svg file itself if it 
		does not already exist.
	"""
	#Compute the hash of the query string
	qhash = hashFunc(query)


	if (not os.path.exists(_TREE_PATH+str(qhash))):

		#Create bucket if it doesn't already exist.
		os.makedirs(_TREE_PATH+str(qhash))

		#Create the lookup table for the bucket.
		bucketTableFile=open(_TREE_PATH+str(qhash)+"/lookup.json",'w')
		bucketTableFile.write("{}")
		bucketTableFile.close()



	#Load bucketTable
	bucketTableFile=open(_TREE_PATH+str(qhash)+"/lookup.json",'r+')
	bucketTable = json.loads(bucketTableFile.read())

	if query not in bucketTable.keys():

		#File is not cache! Create PNG in bucket.
		filename=str(len(os.listdir(_TREE_PATH+str(qhash))))+".svg"
		if not TeXToPng(query,_TREE_PATH+str(qhash),filename):
			#An error has occurred while rendering the LaTeX. 
			return open(handleTeXRenderError("An error has occurred while rendering LaTeX."))

		#Update bucketTable
		bucketTable[query]=filename

		#Write back to bucketTableFile
		bucketTableFile.seek(0)
		bucketTableFile.write(json.dumps(bucketTable))
		bucketTableFile.close()

	#Return path to newly created/existing file
	return open(_TREE_PATH+str(qhash)+"/"+bucketTable[query]).read()




#Pointless comment

def hashFunc(s):
	"""
	Call some hashfunc and return the result.
	Goes "hashy hashy".
	"""
	return abs(hash(s))

def TeXToPng(query,targetDir,name):
	"""
		Renders a latex string in query to a svg in targetDir named name. Return true if successful, false if not.
	"""
	print (query,targetDir+"/"+name)
	try:
		check_output(["./to_svg.sh",query])
		check_output("mv equation.svg {0}".format(targetDir+"/"+name).split())
	except CalledProcessError:
		return False
	return True
	

def handleTeXRenderError(errorMsg):
	"""
		Handles an error encountered while attempting to render a TeX string
	"""
	print errorMsg
	return "assets/img/error.png"

########NEW FILE########
__FILENAME__ = texit
from flask import Flask
from flask import Response
from flask import request
from tex import renderTex
from graph import renderGraph
from settings import *
from mixpanel import Mixpanel

from werkzeug.contrib.fixers import ProxyFix

app = Flask(__name__)
app.debug = not PRODUCTION

if MIXPANEL_TOKEN:
  mp = Mixpanel(MIXPANEL_TOKEN)

if (PRODUCTION):
  app.wsgi_app=ProxyFix(app.wsgi_app)

@app.route('/')
def homePage():
  return Response(open("assets/html/index.html"),mimetype='text/html')

@app.route('/docs/<page>')
def docPage(page):
  return Response(open("assets/html/"+page+".html"),mimetype='text/html')

@app.route('/<path:query>')
def tex2(query):
  if MIXPANEL_TOKEN:
    mp.track(request.remote_addr, 'rendered tex')
  return Response(renderTex(query.replace(".png","").replace("$","").replace("/","\\")),mimetype='image/svg+xml')

@app.route('/js/<filename>')
def js(filename):
  return Response(open("assets/js/"+filename),mimetype='text/js')

@app.route('/css/<filename>')
def css(filename):
  return Response(open("assets/css/"+filename),mimetype='text/css')

@app.route('/file/<filename>')
def file(filename):
  return Response(open("assets/file/"+filename),mimetype='application/octet-stream')

@app.route('/img/<filename>')
def img(filename):
  return Response(open("assets/img/"+filename),mimetype='text/css')

@app.route('/tex/<path:query>')
def tex(query):
  if MIXPANEL_TOKEN:
    mp.track(request.remote_addr, 'rendered tex')
  return Response(renderTex(query.replace(".png","").replace("$","").replace("/","\\")),mimetype='image/svg+xml')

@app.route('/graph/<path:query>')
def graph(query):
  if MIXPANEL_TOKEN:
    mp.track(request.remote_addr, 'rendered graph')
  return Response(renderGraph(query.replace(".png","").replace(" ","")),mimetype='image/svg+xml')

#Pointless comment

if __name__=="__main__":
  app.run()

########NEW FILE########
