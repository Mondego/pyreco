__FILENAME__ = decorators
"""Offers decorators to make the use of django_xmlrpc a great deal simpler

Authors::
    Graham Binns,
    Reza Mohammadi

Credit must go to Brendan W. McAdams <brendan.mcadams@thewintergrp.com>, who
posted the original SimpleXMLRPCDispatcher to the Django wiki:
http://code.djangoproject.com/wiki/XML-RPC

New BSD License
===============
Copyright (c) 2007, Graham Binns http://launchpad.net/~codedragon

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.
    * Neither the name of the <ORGANIZATION> nor the names of its contributors
      may be used to endorse or promote products derived from this software
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
try:
    from xmlrpc.client import Fault
except ImportError:  # Python 2
    from xmlrpclib import Fault
from django.contrib.auth import authenticate
from django.utils.translation import gettext as _


# Some constants for your pleasure
#XXX: Any standardization?
AUTHENTICATION_FAILED_CODE = 81
PERMISSION_DENIED_CODE = 82


class AuthenticationFailedException(Fault):
    """An XML-RPC fault to be raised when a permission_required authentication
    check fails

    Author
    """
    def __init__(self):
        Fault.__init__(self, AUTHENTICATION_FAILED_CODE,
                       _('Username and/or password is incorrect'))


class PermissionDeniedException(Fault):
    """An XML-RPC fault to be raised when a permission_required permission
    check fails
    """
    def __init__(self):
        Fault.__init__(self, PERMISSION_DENIED_CODE, _('Permission denied'))


def xmlrpc_method(returns='string', args=None, name=None):
    """Adds a signature to an XML-RPC function and register
    it with the dispatcher.

    returns
        The return type of the function. This can either be a string
        description (e.g. 'string') or a type (e.g. str, bool) etc.

    args
        A list of the types of the arguments that the function accepts. These
        can be strings or types or a mixture of the two e.g.
        [str, bool, 'string']
    """
    # Args should be a list
    if args is None:
        args = []

    def _xmlrpc_func(func):
        """Inner function for XML-RPC method decoration. Adds a signature to
        the method passed to it.

        func
            The function to add the signature to
        """
        # Add a signature to the function
        func._xmlrpc_signature = {
            'returns': returns,
            'args': args
        }
        return func

    return _xmlrpc_func

xmlrpc_func = xmlrpc_method


# Don't use this decorator when your service is going to be
# available in an unencrpted/untrusted network.
# Configure HTTPS transport for your web server.
def permission_required(perm=None):
    """Decorator for authentication. Uses Django's built in authentication
    framework to provide authenticated-only and permission-related access
    to XML-RPC methods

    perm
        The permission (as a string) that the user must hold to be able to
        call the function that is decorated with permission_required.
    """
    def _dec(func):
        """An inner decorator. Adds the lookup code for the permission passed
        in the outer method to the function passed to it.

        func
            The function to add the permission check to
        """
        def __authenticated_call(username, password, *args):
            """Inner inner decorator. Adds username and password parameters to
            a given XML-RPC function for authentication and permission
            checking purposes and modifies the method signature appropriately

            username
                The username used for authentication

            password
                The password used for authentication
            """
            try:
                user = authenticate(username=username, password=password)
                if not user:
                    raise AuthenticationFailedException
                if perm and not user.has_perm(perm):
                    raise PermissionDeniedException
            except AuthenticationFailedException:
                raise
            except PermissionDeniedException:
                raise
            except:
                raise AuthenticationFailedException
            return func(user, *args)

        # Update the function's XML-RPC signature, if the method has one
        if hasattr(func, '_xmlrpc_signature'):
            sig = func._xmlrpc_signature

            # We just stick two string args on the front of sign['args'] to
            # represent username and password
            sig['args'] = (['string'] * 2) + sig['args']
            __authenticated_call._xmlrpc_signature = sig

        # Update the function's docstring
        if func.__doc__:
            __authenticated_call.__doc__ = func.__doc__ + \
                "\nNote: Authentication is required."""
            if perm:
                __authenticated_call.__doc__ += (' this function requires '
                                                 '"%s" permission.' % perm)

        return __authenticated_call

    return _dec

########NEW FILE########
__FILENAME__ = dispatcher
"""Offers a simple XML-RPC dispatcher for django_xmlrpc

Author::
    Graham Binns

Credit must go to Brendan W. McAdams <brendan.mcadams@thewintergrp.com>, who
posted the original SimpleXMLRPCDispatcher to the Django wiki:
http://code.djangoproject.com/wiki/XML-RPC

New BSD License
===============
Copyright (c) 2007, Graham Binns http://launchpad.net/~codedragon

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.
    * Neither the name of the <ORGANIZATION> nor the names of its contributors
      may be used to endorse or promote products derived from this software
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from inspect import getargspec

try:
    from xmlrpc.server import SimpleXMLRPCDispatcher
except ImportError:  # Python 2
    from SimpleXMLRPCServer import SimpleXMLRPCDispatcher


class DjangoXMLRPCDispatcher(SimpleXMLRPCDispatcher):
    """A simple XML-RPC dispatcher for Django.

    Subclassess SimpleXMLRPCServer.SimpleXMLRPCDispatcher for the purpose of
    overriding certain built-in methods (it's nicer than monkey-patching them,
    that's for sure).
    """

    def system_methodSignature(self, method):
        """Returns the signature details for a specified method

        method
            The name of the XML-RPC method to get the details for
        """
        # See if we can find the method in our funcs dict
        # TODO: Handle this better: We really should return something more
        # formal than an AttributeError
        func = self.funcs[method]

        try:
            sig = func._xmlrpc_signature
        except:
            sig = {
                'returns': 'string',
                'args': ['string' for arg in getargspec(func)[0]],
            }

        return [sig['returns']] + sig['args']

########NEW FILE########
__FILENAME__ = views
"""Uses SimpleXMLRPCServer's SimpleXMLRPCDispatcher to serve XML-RPC requests

Authors::
    Graham Binns
    Reza Mohammadi
    Julien Fache

Credit must go to Brendan W. McAdams <brendan.mcadams@thewintergrp.com>, who
posted the original SimpleXMLRPCDispatcher to the Django wiki:
http://code.djangoproject.com/wiki/XML-RPC

New BSD License
===============
Copyright (c) 2007, Graham Binns http://launchpad.net/~codedragon

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice,
      this list of conditions and the following disclaimer in the documentation
      and/or other materials provided with the distribution.
    * Neither the name of the <ORGANIZATION> nor the names of its contributors
      may be used to endorse or promote products derived from this software
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from logging import getLogger
from collections import Callable

from django.conf import settings
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.http import HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt

from django_xmlrpc.decorators import xmlrpc_func
from django_xmlrpc.dispatcher import DjangoXMLRPCDispatcher


logger = getLogger('xmlrpc')
xmlrpcdispatcher = DjangoXMLRPCDispatcher(allow_none=False, encoding=None)


@xmlrpc_func(returns='string', args=['string'])
def test_xmlrpc(text):
    """Simply returns the args passed to it as a string"""
    return "Here's a response! %s" % str(text)


@csrf_exempt
def handle_xmlrpc(request):
    """Handles XML-RPC requests. All XML-RPC calls should be forwarded here

    request
        The HttpRequest object that carries the XML-RPC call. If this is a
        GET request, nothing will happen (we only accept POST requests)
    """
    if request.method == "POST":
        logger.info(request.body)
        try:
            response = HttpResponse(content_type='text/xml')
            response.write(
                xmlrpcdispatcher._marshaled_dispatch(request.body))
            logger.debug(response)
            return response
        except:
            return HttpResponseServerError()
    else:
        methods = xmlrpcdispatcher.system_listMethods()
        method_list = []

        for method in methods:
            sig_ = xmlrpcdispatcher.system_methodSignature(method)
            sig = {
                'returns': sig_[0],
                'args': ", ".join(sig_[1:]),
            }

            # this just reads your docblock, so fill it in!
            method_help = xmlrpcdispatcher.system_methodHelp(method)

            method_list.append((method, sig, method_help))

        return render_to_response('xmlrpc_get.html', {'methods': method_list},
                                  context_instance=RequestContext(request))


# Load up any methods that have been registered with the server in settings
if hasattr(settings, 'XMLRPC_METHODS'):
    for path, name in settings.XMLRPC_METHODS:
        # if "path" is actually a function, just add it without fuss
        if isinstance(path, Callable):
            xmlrpcdispatcher.register_function(path, name)
            continue

        # Otherwise we try and find something that we can call
        i = path.rfind('.')
        module, attr = path[:i], path[i + 1:]

        try:
            mod = __import__(module, globals(), locals(), [attr])
        except ImportError as ex:
            raise ImproperlyConfigured(
                "Error registering XML-RPC method: "
                "module %s can't be imported" % module)

        try:
            func = getattr(mod, attr)
        except AttributeError:
            raise ImproperlyConfigured(
                'Error registering XML-RPC method: '
                'module %s doesn\'t define a method "%s"' % (module, attr))

        if not isinstance(func, Callable):
            raise ImproperlyConfigured(
                'Error registering XML-RPC method: '
                '"%s" is not callable in module %s' % (attr, module))

        xmlrpcdispatcher.register_function(func, name)


# Finally, register the introspection and multicall methods with the XML-RPC
# namespace
xmlrpcdispatcher.register_introspection_functions()
xmlrpcdispatcher.register_multicall_functions()

########NEW FILE########
