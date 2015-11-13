__FILENAME__ = core
import random

#WORDS = "banane fromage lasagne ravioli carotte".split()
WORDS = [x.strip() for x in open("/home/mariedam/webapps/infinity/htdocs/words")]

def add_link(x):
	if random.randint(0,10) == 1:
		x = '<a href="/{x}">{x}</a>'.format(x=x)
	if random.randint(0,100) == 1:
		x = x+"<br/>"
	elif random.randint(0,60) == 1:
		x = "</p><h{n}>{x}</h{n}><p>".format(x=x,n=random.randint(1,3))
	return x

def generate(x):
	global WORDS
	random.seed(x)
	return ' '.join(map(add_link,[random.choice(WORDS) for x in xrange(random.randint(300,400))]))
	
if __name__ == "__main__":
    print(generate("dadamien"))

########NEW FILE########
__FILENAME__ = main
from flask import Flask,render_template
import core
app = Flask(__name__)

from flask import request

@app.route("/map/")
def siemap_index():
    return sitemap("")

@app.route("/map/<path:x>")
def sitemap(x):
    if 'Wget' in request.user_agent.string:
        return ""
    elrange = range(ord("a"),ord("z")+1)+range(ord("A"),ord("Z")+1)
    return render_template("sitemap.html",title=x,links=[x+chr(c) for c in elrange])

@app.route("/")
def index():
    return generator("Hello ")


@app.route('/robots.txt')
def robots():
    return "User-Agent: *\nDisallow: /"

@app.route("/<path:x>")
def generator(x):
    if 'Wget' in request.user_agent.string:
        return ""
    return render_template("content.html",title=x,content=core.generate(x))

if __name__ == "__main__":
    app.run(debug=True)

########NEW FILE########
__FILENAME__ = wsgi
import sys
sys.path.append('/home/mariedam/webapps/infinity/htdocs')
from main import app as application

########NEW FILE########
