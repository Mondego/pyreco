__FILENAME__ = blog_urls
"""
This code should be copy and pasted into blog/urls.py
"""


from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url(r'^$', 'blog.views.home'),
    url(r'^posts/$', 'blog.views.post_list'),
    url(r'^posts/(?P<id>\d+)/((?P<showComments>.*)/)?$', 'blog.views.post_detail'),
    ## add your url here
)

########NEW FILE########
__FILENAME__ = blog_views
"""
This code should be copied and pasted into your blog/views.py file before you begin working on it.
"""

from django.template import Context, loader
from django.http import HttpResponse

from models import Post, Comment 


def post_list(request):
    post_list = Post.objects.all()
    
    print type(post_list)
    print post_list
    
    return HttpResponse('This should be a list of posts!')

def post_detail(request, id, showComments=False):
    pass
    
def post_search(request, term):
    pass

def home(request):
    print 'it works'
    return HttpResponse('hello world. Ete zene?') 

########NEW FILE########
__FILENAME__ = reg_view
"""
Code that should be copy and pasted in to
reg/views.py to as a skeleton for creating
the authentication views
"""
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django import forms
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

@csrf_exempt
def do_login(request):
    if request.method == 'POST':
        #YOUR CODE HERE
        pass
    
    form = LoginForm()
    return render_to_response('reg/login.html', {
        'form': form,
        'logged_in': request.user.is_authenticated()
    })

@csrf_exempt
def do_logout(request):
    logout(request)
    return render_to_response('reg/logout.html')

########NEW FILE########
__FILENAME__ = RawResponseMiddleware
"""
A tool for using view functions without templates.
Will render
"""

class RawResponseMiddleware(object):
    
    
    def process_response(self, request, response):
        """
        Wraps the response body in <pre></pre> tags to avoid http rendering
        
        Will NOT do so to admin pages
        Will NOT do so unless status code is 200 
        """
        
        if (not request.path.startswith('/admin')) and response.status_code == 200:
            escaped_content = (response.content
                                .replace('&','&amp;')
                                .replace('<','&lt;')
                                .replace('>','&gt;')
                                .replace('"','&quot;'))
            response.content = "<pre>%s</pre>" % escaped_content
        
        return response
########NEW FILE########
