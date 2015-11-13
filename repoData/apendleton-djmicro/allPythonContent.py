__FILENAME__ = djmicro
import os

_base_module = None

def configure(options={}, module=None):
    if not module:
        # hack to figure out where we were called from
        import sys, inspect
        module = sys.modules[inspect.stack()[1][0].f_locals['__name__']]
    
    # settings
    from django.conf import settings
    if not settings.configured:
        opts = dict(
            DEBUG = True,
            ROOT_URLCONF = module.__name__,
            TEMPLATE_DIRS = [os.path.dirname(module.__file__)],
            INSTALLED_APPS = []
        )
        opts.update(options)
        settings.configure(**opts)
    
    # urls
    from django.conf.urls.defaults import patterns
    module.urlpatterns = patterns('')
        
    global _base_module
    _base_module = module

def route(*args, **kwargs):
    def add_route(view):
        from django.conf.urls.defaults import patterns, url
        _base_module.urlpatterns += patterns('',
            url(args[0], view, *args[1:], **kwargs)
        )
        return view
    return add_route

def run():
    from django.core.management import execute_from_command_line
    execute_from_command_line()
########NEW FILE########
__FILENAME__ = djmicro
../djmicro.py
########NEW FILE########
__FILENAME__ = web
import djmicro
djmicro.configure()

from django.shortcuts import render

@djmicro.route(r'^$')
def hello(request):
    return render(request, 'index.html', {})

@djmicro.route(r'^test/(\d+)/$')
def test(request, id):
    return render(request, 'test.html', {'id': id})

if __name__ == '__main__':
    djmicro.run()
########NEW FILE########
