__FILENAME__ = api

import subprocess, os, json


from pyxc.util import usingPython3, parentOf

from pyxc import pyxc_exceptions

#
# Most of pyxc and pj require Python 3,
# but your build script or Django app is probably running under 2.x...
#
# Not to worry, you can use this module as-is from either 2 or 3!
#
# If you're not running 3, this module will invoke
# a <code>pj</code> subprocess to perform the compilation.
#
# The <code>pj</code> script doesn't even have to be on your <code>PATH</code>

#### Code to Code
def codeToCode(pythonCode):
    return _runViaSubprocessIfNeeded(
                    # name, args, kwargs &mdash; if we're running Python 3
                    'codeToCode',
                    [pythonCode],
                    {},
                    # input, args &mdash; for the Python 3 subprocess
                    pythonCode,
                    ['--code-to-code'])

#### Build Bundle
def buildBundle(mainModule, **kwargs):
    '''
    kwargs:
        path=None, createSourceMap=False, includeSource=False, prependJs=None
    '''
    path = kwargs.get('path')
    assert path is not None
    
    args = ['--build-bundle', mainModule]
    if path is not None:
        args.append('--path=%s' % ':'.join(path))
    if kwargs.get('createSourceMap'):
        args.append('--create-source-map')
    
    return _runViaSubprocessIfNeeded(
                    # name, args, kwargs &mdash; if we're running Python 3
                    'buildBundle',
                    [mainModule],
                    kwargs,
                    # input, args &mdash; for the Python 3 subprocess
                    None,
                    args,
                    parseJson=True)


def _runViaSubprocessIfNeeded(name, args, kwargs, input, subprocessArgs, parseJson=False):
    
    if usingPython3():
        import pj.api_internal
        f = getattr(pj.api_internal, name)
        return f(*args, **kwargs)
    else:
        
        if isinstance(input, unicode):
            input = input.encode('utf-8')
        
        pythonPath = parentOf(parentOf(os.path.abspath(__file__)))
        if os.environ.get('PYTHONPATH'):
            pythonPath += ':' + os.environ.get('PYTHONPATH')
        
        subprocessArgs = ['/usr/bin/env',
                                    'PYTHONPATH=%s' % pythonPath,
                                    'python3.1',
                                    parentOf(os.path.abspath(__file__)) + '/pj',
                                    ] + subprocessArgs
        
        if input is None:
            p = subprocess.Popen(subprocessArgs, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
        else:
            p = subprocess.Popen(subprocessArgs, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            out, err = p.communicate(input=input)
        
        if p.returncode == 0:
            result = unicode(out, 'utf-8')
            if parseJson:
                result = json.loads(result)
            return result
        else:
            try:
                errInfo = json.loads(err)
            except ValueError:
                errInfo = {
                    'name': 'Exception',
                    'message': unicode(err, 'utf-8'),
                }
            if hasattr(pyxc_exceptions, errInfo['name']):
                exceptionClass = getattr(pyxc_exceptions, errInfo['name'])
                raise exceptionClass(errInfo['message'])
            else:
                raise Exception('%s\n--------\n%s' % (errInfo['name'], errInfo['message']))


def closureCompile(js, closureMode):
    
    if not closureMode:
        return js
    
    if isinstance(closureMode, list) or isinstance(closureMode, tuple):
        for mode in closureMode:
            js = closureCompile(js, mode)
        return js
    
    modeArgs = {
        'pretty': [
                        '--compilation_level', 'WHITESPACE_ONLY',
                        '--formatting', 'PRETTY_PRINT'],
        'simple': [
                        '--compilation_level', 'SIMPLE_OPTIMIZATIONS'],
        'advanced': [
                        '--compilation_level', 'ADVANCED_OPTIMIZATIONS'],
    }[closureMode]
    
    p = subprocess.Popen([
                            '/usr/bin/env',
                            'java',
                            '-jar', os.environ['CLOSURE_JAR'],
                            ] + modeArgs,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    out, err = p.communicate(input=js.encode('utf-8'))
    if p.returncode != 0:
        raise Exception('Error while Closure-compiling:\n' + err)
    
    return out



########NEW FILE########
__FILENAME__ = api_internal

import ast

from pyxc.importing import SourcePath, orderedModules
from pyxc.transforming import Transformer, SourceMap, exportSourceMap
from pyxc.util import topLevelNamesInBody

import pj.js_ast
import pj.transformations


#### Code to Code
def codeToCode(py):
    
    t = Transformer(pj.transformations, pj.js_ast.JSStatements)
    jsAst = t.transformCode(py)
    js = '%s\n%s' % ('\n'.join(t.snippets), str(jsAst))
    
    names = set(topLevelNamesInBody(ast.parse(py).body))
    if len(names) > 0:
        js = 'var %s;\n\n%s' % (
            ', '.join(names),
            js)
    
    return js


#### Build Bundle
def buildBundle(mainModule, path=None, createSourceMap=False, includeSource=False, prependJs=None):
    
    assert path
    
    t = Transformer(pj.transformations, pj.js_ast.JSStatements)
    sourcePath = SourcePath(path)
    modules = orderedModules(sourcePath, mainModule)
    
    jsArr = []
    topLevelNames = set()
    
    linemaps = []
    mappings = []
    
    sourceDict = {}
    
    i = 0
    for module in modules:
        fileKey = str(i)
        i += 1
        codePath = sourcePath.pathForModule(module)
        with open(codePath, 'rb') as f:
            
            py = str(f.read(), 'utf-8')
            
            sourceDict[fileKey] = {
                'path': codePath,
                'code': py,
                'module': module,
            }
            
            if codePath.endswith('.js'):
                js = py
            
            else:
                
                # Load the top-level names and confirm they're distinct
                for name in topLevelNamesInBody(ast.parse(py).body):
                    assert name not in topLevelNames
                    topLevelNames.add(name)
                
                # py &rarr; js
                jsAst = t.transformCode(py)
                if createSourceMap:
                    
                    sm = SourceMap(fileKey, nextMappingId=len(mappings))
                    sm.handleNode(jsAst)
                    
                    js = sm.getCode() + '\n'
                    
                    assert len(sm.linemaps) == len(js.split('\n')) - 1
                    
                    linemaps += sm.linemaps
                    mappings += sm.mappings
                    
                else:
                    js = str(jsAst)
            
            jsArr.append(js)
    
    if len(topLevelNames) > 0:
        varJs = 'var %s;' % ', '.join(list(topLevelNames))
    else:
        varJs = ''
    
    jsPrefix = ''.join([
                    (prependJs + '\n\n') if prependJs is not None else '',
                    '(function(){\n\n',
                    '\n'.join(t.snippets), '\n\n',
                    varJs, '\n\n'])
    
    jsSuffix = '\n\n})();'
    
    linemaps = (
                    [([-1] * (len(s) + 2)) for s in jsPrefix.split('\n')[:-1]] + 
                    linemaps[:-1] + 
                    [([-1] * (len(s) + 2)) for s in jsPrefix.split('\n')])
    
    js = ''.join([
                    jsPrefix,
                    ''.join(jsArr),
                    jsSuffix])
    
    info = {
        'js': js,
    }
    
    if createSourceMap:
        info['sourceMap'] = exportSourceMap(linemaps, mappings, sourceDict)
    
    if includeSource:
        info['sourceDict'] = dict(
                                    (
                                        sourceDict[k]['module'],
                                        sourceDict[k])
                                    for k in sourceDict)
    
    return info



########NEW FILE########
__FILENAME__ = django
####jsView
#
# This Django view can be very convenient for dev mode. (Though for production you should obviously use static JS files pre-compiled and minified by your build script.)
#
# **Example:**
#
# **<code>urls.py</code>**:
#<pre>if settings.DEBUG:
#    urlpatterns += patterns('pj.django',
#        url(
#               r'/static/js/mywidget\.js',
#               'jsView',
#               {'main': 'mywidget.main'}),
#    )</pre>
#
# **<code>settings.py</code>**:
#<pre>PJ_PATH = ['...', '...', ...]</pre>

from __future__ import absolute_import

import os, subprocess

from django.http import HttpResponse
from django.template import Context, Template
from django.conf import settings

import pj.api


def jsView(request, **kwargs):
    
    main = kwargs['main']
    path = settings.PJ_PATH
    closureMode = getattr(settings, 'PJ_CLOJURE_MODE', None) or request.GET.get('mode')
    
    js = pj.api.buildBundle(main, path=path)['js']
    
    if kwargs.get('jsPrefix', None):
      js = kwargs['jsPrefix'] + '\n\n' + js
    
    if kwargs.get('renderTemplate', True):
      js = Template(js).render(Context({
        'DEBUG': settings.DEBUG,
      }))
    
    if closureMode:
        js = pj.api.closureCompile(js, closureMode)
    
    return HttpResponse(
                    js.encode('utf-8'),
                    mimetype='text/javascript; charset=utf-8')


########NEW FILE########
__FILENAME__ = js_ast

# To learn what pyxc is doing for you behind the scenes,
# read [pyxc.org/transformations/](http://pyxc.org/transformations/)

import ast, json, re
from functools import reduce

from pyxc.transforming import TargetNode
from pyxc.util import delimitedList


JS_KEYWORDS = set([
    'break', 'case', 'catch', 'continue', 'default', 'delete', 'do', 'else',
    'finally', 'for', 'function', 'if', 'in', 'instanceof', 'new', 'return',
    'switch', 'this', 'throw', 'try', 'typeof', 'var', 'void', 'while', 'with',
    
    'abstract', 'boolean', 'byte', 'char', 'class', 'const', 'debugger',
    'double', 'enum', 'export', 'extends', 'final', 'float', 'goto',
    'implements', 'import', 'int', 'interface', 'long', 'native', 'package',
    'private', 'protected', 'public', 'short', 'static', 'super',
    'synchronized', 'throws', 'transient', 'volatile'])

#### Misc

class JSNode(TargetNode):
    pass

class JSStatement(JSNode):
    pass

class JSLeftSideUnaryOp(JSNode):
    pass

class JSStatements(JSNode):
    def emit(self, statements):
        return delimitedList(';\n', statements, delimAtEnd=True)

class JSPass(JSNode):
    def emit(self):
        return ['']

class JSCommentBlock(JSNode):
    def emit(self, text):
        assert text.find('*/') == -1
        return ['/* ', text, ' */']

#### Statements

class JSExpressionStatement(JSStatement):
    def emit(self, value):
        return [value]

class JSVarStatement(JSStatement):
    def emit(self, keys, values):
        for key in keys:
            assert key not in JS_KEYWORDS, key
        assert len(keys) > 0
        assert len(keys) == len(values)
        
        arr = ['var ']
        for i in range(len(keys)):
            if i > 0:
                arr.append(', ')
            arr.append(keys[i])
            if values[i] is not None:
                arr.append(' = ')
                arr.append(values[i])
        return arr

class JSAugAssignStatement(JSStatement):
    def emit(self, target, op, value):
        return [target, ' ', op, '= ', value]

class JSIfStatement(JSStatement):
    def emit(self, test, body, orelse):
        
        arr = ['if (', test, ') {']
        delimitedList(';', body, dest=arr)
        arr.append('}')
        
        if orelse:
            arr.append('else {')
            delimitedList(';', orelse, dest=arr)
            arr.append('}')
        
        return arr

class JSWhileStatement(JSStatement):
    def emit(self, test, body):
        arr = ['while (', test, ') {']
        delimitedList(';', body, dest=arr)
        arr.append('}')
        return arr

class JSForStatement(JSStatement):
    def emit(self, left, test, right, body):
        arr = ['for (', left, '; ', test, '; ', right, ') {']
        delimitedList(';', body, dest=arr)
        arr.append('}')
        return arr

class JSForeachStatement(JSStatement):
    def emit(self, target, source, body):
        arr = ['for (var ', target, ' in ', source, ') {']
        delimitedList(';', body, dest=arr)
        arr.append('}')
        return arr

class JSReturnStatement(JSStatement):
    def emit(self, value):
        if value:
            return ['return ', value]
        else:
            return ['return']

class JSBreakStatement(JSStatement):
    def emit(self):
        return ['break']

class JSContinueStatement(JSStatement):
    def emit(self):
        return ['continue']

class JSDeleteStatement(JSStatement):
    def emit(self, obj, key):
        return ['delete ', obj, '[', key, ']']

class JSTryCatchStatement(JSStatement):
    def emit(self, tryBody, target, catchBody):
        arr = ['try {']
        delimitedList(';', tryBody, dest=arr)
        arr.append('} catch(')
        arr.append(target)
        arr.append(') {')
        delimitedList(';', catchBody, dest=arr)
        arr.append('}')
        return arr

class JSThrowStatement(JSStatement):
    def emit(self, obj):
        return ['throw ', obj]

#### Expressions

class JSList(JSNode):
    def emit(self, elts):
        arr = ['[']
        delimitedList(', ', elts, dest=arr)
        arr.append(']')
        return arr

class JSDict(JSNode):
    def emit(self, keys, values):
        arr = ['{']
        for i in range(len(keys)):
            if i > 0:
                arr.append(', ')
            arr.append(keys[i])
            arr.append(': ')
            arr.append(values[i])
        arr.append('}')
        return arr

class JSFunction(JSNode):
    def emit(self, name, args, body):
        arr = ['(function ']
        if name is not None:
            arr.append(name)
        arr.append('(')
        delimitedList(', ', args, dest=arr)
        arr.append('){')
        delimitedList(';\n', body, dest=arr)
        arr.append('})')
        return arr

class JSAssignmentExpression(JSNode):
    def emit(self, left, right):
        return ['(', left, ' = ', right, ')']

class JSIfExp(JSNode):
    def emit(self, test, body, orelse):
        return ['(', test, ' ? ', body, ' : ', orelse, ')']

class JSCall(JSNode):
    def emit(self, func, args):
        arr = ['(', func, '(']
        delimitedList(', ', args, dest=arr)
        arr.append('))')
        return arr

class JSNewCall(JSNode):
    def emit(self, func, args):
        arr = ['(new ', func, '(']
        delimitedList(', ', args, dest=arr)
        arr.append('))')
        return arr

class JSAttribute(JSNode):
    def emit(self, obj, s):
        assert re.search(r'^[a-zA-Z_][a-zA-Z_0-9]*$', s)
        assert s not in JS_KEYWORDS
        return [obj, '.', s]

class JSSubscript(JSNode):
    def emit(self, obj, key):
        return [obj, '[', key, ']']

class JSBinOp(JSNode):
    def emit(self, left, op, right):
        return ['(', left, ' ', op, ' ', right, ')']

class JSUnaryOp(JSNode):
    def emit(self, op, right):
        assert isinstance(op, JSLeftSideUnaryOp)
        return ['(', op, ' ', right, ')']

#### Atoms

class JSNum(JSNode):
    def emit(self, x):
        return [str(x)]

class JSStr(JSNode):
    def emit(self, s):
        return [json.dumps(s)]

class JSName(JSNode):
    def emit(self, name):
        assert name not in JS_KEYWORDS, name
        return [name]

class JSThis(JSNode):
    def emit(self):
        return ['this']

class JSTrue(JSNode):
    def emit(self):
        return ['true']

class JSFalse(JSNode):
    def emit(self):
        return ['false']

class JSNull(JSNode):
    def emit(self):
        return ['null']

#### Ops

class JSOpIn(JSNode):
    def emit(self):
        return ['in']

class JSOpAnd(JSNode):
    def emit(self):
        return ['&&']

class JSOpOr(JSNode):
    def emit(self):
        return ['||']

class JSOpNot(JSLeftSideUnaryOp):
    def emit(self):
        return ['!']

class JSOpInstanceof(JSNode):
    def emit(self):
        return ['instanceof']

class JSOpTypeof(JSLeftSideUnaryOp):
    def emit(self):
        return ['typeof']

class JSOpAdd(JSNode):
    def emit(self):
        return ['+']

class JSOpSub(JSNode):
    def emit(self):
        return ['-']

class JSOpMult(JSNode):
    def emit(self):
        return ['*']

class JSOpDiv(JSNode):
    def emit(self):
        return ['/']

class JSOpMod(JSNode):
    def emit(self):
        return ['%']

class JSOpRShift(JSNode):
    def emit(self):
        return ['>>']

class JSOpLShift(JSNode):
    def emit(self):
        return ['<<']

class JSOpBitXor(JSNode):
    def emit(self):
        return ['^']

class JSOpBitAnd(JSNode):
    def emit(self):
        return ['&']

class JSOpBitOr(JSNode):
    def emit(self):
        return ['|']

class JSOpInvert(JSLeftSideUnaryOp):
    def emit(self):
        return ['~']

class JSOpStrongEq(JSNode):
    def emit(self):
        return ['===']

class JSOpStrongNotEq(JSNode):
    def emit(self):
        return ['!==']

class JSOpLt(JSNode):
    def emit(self):
        return ['<']

class JSOpLtE(JSNode):
    def emit(self):
        return ['<=']

class JSOpGt(JSNode):
    def emit(self):
        return ['>']

class JSOpGtE(JSNode):
    def emit(self):
        return ['>=']


########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python3.1

import optparse, sys, os, json

# Require Python 3
from pyxc.util import usingPython3, writeExceptionJsonAndDie, TempDir, parentOf
if not usingPython3():
    sys.stderr.write('Python 3 required.')
    sys.exit(1)

import pj.api_internal
from pj.nodejs import runViaNode


#### Main
def main():
    
    parser = optparse.OptionParser()
    
    parser.add_option('-p', '--path', dest='path', default=None)
    parser.add_option('-M', '--create-source-map', dest='createSourceMap', default=False, action='store_true')
    
    parser.add_option('-C', '--code-to-code', dest='codeToCode', default=False, action='store_true')
    parser.add_option('-B', '--build-bundle', dest='buildBundle', default=False, action='store_true')
    parser.add_option('-E', '--run-exception-server',
                                dest='runExceptionServer', default=False, action='store_true')
    parser.add_option('-U', '--use-exception-server',
                                dest='useExceptionServer', default=None)
    
    options, args = parser.parse_args()
    
    codepath = None
    if options.path is not None:
        codepath = options.path.split(':')
    elif os.environ.get('PYXC_PJ_PATH'):
        codepath = os.environ['PYXC_PJ_PATH'].strip(':').split(':')
    
    # Code to code
    if options.codeToCode:
        codeToCode()
    
    # Build bundle
    elif options.buildBundle:
        buildBundle(args[0], codepath, options.createSourceMap)
    
    # Run via node
    elif len(args) == 1:
        esHost, esPort = (None, None)
        if options.runExceptionServer:
            esHost, esPort = 'localhost', 61163
        elif options.useExceptionServer is not None:
            (esHost, esPort) = options.useExceptionServer.split(':')
            if not esHost:
                esHost = 'localhost'
        runViaNode(args[0], codepath, esHost, esPort, options.runExceptionServer)
    
    else:
        sys.stderr.write('Invalid args -- see http://pyxc.org/pj for usage.\n')
        sys.exit(1)


#### Code to Code
# See [pj.api_internal.codeToCode](api_internal.py)
def codeToCode():
    py = sys.stdin.read()
    try:
        js = pj.api_internal.codeToCode(py)
        sys.stdout.write(js)
    except Exception as e:
        writeExceptionJsonAndDie(e)


#### Build Bundle
# See [pj.api_internal.buildBundle](api_internal.py)
def buildBundle(mainModule, codepath, createSourceMap):
    try:
        info = pj.api_internal.buildBundle(
                            mainModule,
                            path=codepath,
                            createSourceMap=createSourceMap)
        sys.stdout.write(json.dumps(info))
    except Exception as e:
        writeExceptionJsonAndDie(e)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = nodejs

import sys, os, json, subprocess, re, hashlib, time
import urllib.request
import urllib.parse

from pyxc.util import TempDir, parentOf, simplePost

import pj.api_internal


def runViaNode(path, codepath, exceptionServerHost, exceptionServerPort, runExceptionServer):
    
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise Exception('File not found: ' + repr(path))
    filename = path.split('/')[-1]
    module = filename.split('.')[-2]
    codepath = (codepath or []) + [parentOf(path)]
    
    if exceptionServerPort:
        #LATER: nice fatal error if exception-server not installed
        prependJs = "require('exception-server').devCombo(%s);\n" % json.dumps({
            'connectTo': [exceptionServerHost, exceptionServerPort],
        })
    else:
        prependJs = None
    
    info = pj.api_internal.buildBundle(
                            module,
                            path=codepath,
                            createSourceMap=True,
                            includeSource=True,
                            prependJs=prependJs)
    js = info['js']
    sourceMap = info['sourceMap']
    sourceDict = info['sourceDict']
    
    with TempDir() as td:
        
        jsPath = '%s/%s.js' % (td.path, filename)
        with open(jsPath, 'wb') as f:
            f.write(js.encode('utf-8'))
        
        exception_server_proc = None
        if runExceptionServer:
            exception_server_proc = startExceptionServer(
                                        exceptionServerPort, js, sourceMap, sourceDict, jsPath)
        try:
            subprocess.check_call(['node', jsPath])
            if exception_server_proc is not None:
                exception_server_proc.kill()
        except Exception:
            sys.stderr.write('[PYXC] Leaving exception server running until you Control-C...\n')
            try:
                while True:
                    time.sleep(1)
            finally:
                if exception_server_proc is not None:
                    exception_server_proc.kill()


def startExceptionServer(exceptionServerPort, js, sourceMap, sourceDict, jsPath):
    path = '%s/nodejs_exception_server.js' % parentOf(__file__)
    p = subprocess.Popen(
                            ['node', path, str(exceptionServerPort)],
                            stdout=subprocess.PIPE)
    
    try:
        line = p.stdout.readline()
        assert line.startswith(b'Server ready, PYXC-PJ. Go, go, go!'), repr(line)
    
        # Send it information
        jsdata = js.encode('utf-8')
        jshash = hashlib.sha1(jsdata).hexdigest()
        tups = [('mapping', jshash, sourceMap.encode('utf-8'))]
        for k, d in sourceDict.items():
            data = d['code'].encode('utf-8')
            tups.append((
                            'code',
                            hashlib.sha1(data).hexdigest(),
                            data))
        url = 'http://localhost:%d/api/log.js' % exceptionServerPort
        for typename, k, v in tups:
            simplePost(url, POST={
                'type': typename,
                'code_sha1': k,
                'v': v,
            })
    
    except Exception:
        p.kill()
        raise
    
    return p


########NEW FILE########
__FILENAME__ = dual_eval
#!/usr/bin/env python3.1

# For each of many Python fragments, check that...
#
#   * it runs as Python
#   * it compiles to js
#   * the js runs
#   * the value of the last line is the same in py and js
#
# Prereqs
# 
#   * have [Rhino](http://www.mozilla.org/rhino/)'s js.jar somewhere
#   * have the environment variable <code>RHINO_JAR</code> point to it

import os, json, re, sys

def up(n):
    path = os.path.abspath(__file__)
    return '/'.join(path.rstrip('/').split('/')[:-n])

sys.path.append(up(3))

from pyxc.util import usingPython3, check_communicate, exceptionRepr
assert usingPython3()
from pj.api_internal import codeToCode


def main():
    
    for py in getFragments():
        
        js = codeToCode(py)
        jsValue = valueOfLastLine_js(js)
        
        m = re.search(r'# Expected value: (.*)', py)
        if m:
            pyValue = json.loads(m.group(1))
        else:
            pyValue = valueOfLastLine_py(py)
        
        
        sys.stderr.write('%s... ' % json.dumps(py))
        if jsValue == pyValue:
            sys.stderr.write('ok.\n')
        else:
            sys.stderr.write('FAIL!')
            for k in ['py', 'js', 'jsValue', 'pyValue']:
                print('--- %s ---' % k)
                print(locals()[k])
            sys.exit(1)


def runJs(js):
    
    rhinoPath = os.environ['RHINO_JAR']
    
    try:
        out, err = check_communicate([
                            '/usr/bin/env',
                            'java',
                            '-jar', rhinoPath,
                            '-e', js.encode('utf-8')])
    except Exception as e:
        raise Exception(e.msg + '\n--- js ---\n' + js)
    return out


def valueOfLastLine_py(py):
    try:
        k = '___result___'
        py = changeLastLine(py, lambda line: '%s = %s' % (k, line))
        l, g = {}, {}
        exec(py, g, l)
        return json.loads(json.dumps(l[k]))
    except Exception:
        raise Exception('Error when running Python code.\n--- py ---\n%s\n--- err ---\n%s' % (py, exceptionRepr()))


def valueOfLastLine_js(js):
    newJs = changeLastLine(
                js.strip(),
                lambda line: 'print(json_dumps(%s));' % line.rstrip(';'))
    jsWithJson = '%s\n%s' % (
                getJsonCode(),
                newJs)
    jsOut = runJs(jsWithJson)
    try:
        return json.loads(str(jsOut, 'utf-8'))
    except Exception:
        raise Exception('Error decoding Rhino output %s for js %s' % (
                                repr(jsOut),
                                repr(newJs)))


def changeLastLine(code, f):
    lines = code.split('\n')
    lines[-1] = f(lines[-1])
    return '\n'.join(lines)


def getJsonCode():
    return '''
        var json_dumps = function(x) {
            var json_dumps = arguments.callee;
            if (
                    (x === true) ||
                    (x === false) ||
                    (x === null)) {
                return x;
            }
            else if ((typeof x) == "number") {
                return '' + x;
            }
            else if ((typeof x) == "string") {
                //ASSUMPTION: x is a very safe string
                return '"' + x + '"';
            }
            else if (x instanceof Array) {
                var bits = [];
                for (var i = 0, bound = x.length; i < bound; i++) {
                    bits.push(arguments.callee(x[i]));
                }
                return '[' + bits.join(', ') + ']';
            }
            else {
                var bits = [];
                for (var k in x) {
                    if (x.hasOwnProperty(k)) {
                        bits.push(json_dumps(k) + ':' + json_dumps(x[k]));
                    }
                }
                return '{' + bits.join(', ') + '}';
            }
        };
    '''

def getFragments():
    s = '''1729

[0 ^ 0, 0 ^ 1, 1 ^ 0, 1 ^ 1]

[0 & 0, 0 & 1, 1 & 0, 1 & 1]

[0 | 0, 0 | 1, 1 | 0, 1 | 1]

[~(-2), ~(-1), ~(0), ~(1), ~(2)]

[64 >> 2, 65 >> 2, -16 >> 3]

x = y = 2
x + y

x = [
    1 in [10, 11],
    2 in [10, 11],
    11 in [10, 11],
]
# Expected value: [true, false, false]
x

y = [x + 1 for x in [1, 2, 3, 100]]
y

if 3 < 3:
    x = 1
elif 2 < 3:
    x = 2
else:
    x = 3
x

x = 0
i = 10
while True:
    pass
    x += i
    i -= 1
    if i < 0:
        break
    else:
        continue
x

d = {'foo': 1, 'bar': 2}
del d['bar']
d

def f(x):
    return x + 1000
f(7)

x = 0
for i in range(5):
    x += i
x

x = 0
for i in range(3, 5):
    x += i
x

x = ''
d = {'foo': 'FOO', 'bar': 'BAR'}
for k in dict(d):
    x += k + d[k]
x

x = 0
for t in [1, 2, 3, 100]:
    x += t
x

def f(x):
    "docstring"
    return x
f(5)

try:
    raise Exception('foo')
except Exception as e:
    pass
5

try:
    raise Exception
except Exception as e:
    pass
5

class Foo:
    def __init__(self):
        self.msg = 'foo'
Foo().msg

class Animal:
    def __init__(self, name):
        self.name = name
class TalkingAnimal(Animal):
    def __init__(self, name, catchphrase):
        super(name)
        self.catchphrase = catchphrase
    def caption(self):
        return self.name + " sez '" + self.catchphrase + "'"
# Expected value: "Pac-Man sez 'waka waka'"
TalkingAnimal('Pac-Man', 'waka waka').caption()

class Animal:
    def __init__(self, name):
        self.name = name
class TalkingAnimal(Animal):
    def __init__(self, name, catchphrase):
        super(name)
        self.catchphrase = catchphrase
    def caption(self):
        return self.name + " sez '" + self.catchphrase + "'"
class Kitteh(TalkingAnimal):
    def __init__(self, name):
        super(name, 'OH HAI')
    def caption(self):
        return 'OMG AWESOMECUTE: ' + super()
# Expected value: "OMG AWESOMECUTE: Maru-san sez 'OH HAI'"
Kitteh('Maru-san').caption()

1

-1

1E3

True

False

None

0.5

x = "foo"
x

[1, 2, "foo"]

(1, 2, "foo")

{'foo': 1, 'bar': 2}

2 + 3

2 - 3

2 * 3

4 / 2

7 % 6

2**5

1 + 2 * 3

2 < 3

3 <= 3

3 >= 3

3 > 3

2 < 3 <= 3

2 < 3 < 3

100 if 2 < 3 else 200

(lambda x, y: x + y)(2, 3)

(True and False) or (True and not False)

x = 5
x

x = 5
x += 2
x'''
    
    return re.split(r'\n\n[\n]*', s)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = classes

import ast
from pj.js_ast import *

from pyxc.util import localNamesInBody


#### ClassDef
#
# The generated code is the same as [what CoffeeScript generates](http://jashkenas.github.com/coffee-script/#classes).


#<pre>class Animal:                                      ---->
#    def __init__(self, name):
#        self.name = name</pre>
'''
var Animal = function(name) {
    this.name = name;
    return this;
}
'''
#<pre>class TalkingAnimal(Animal):                       ---->
#    def __init__(self, name, catchphrase):
#        super(name)
#        self.catchphrase = catchphrase
#    def caption(self):
#        return self.name + ' sez "' + self.catchphrase + '"'</pre>
'''
var TalkingAnimal = function() {
    this.__super__.__init__.call(this, name);
    this.catchphrase = catchphrase;
    return this
}
__extends(TalkingAnimal, Animal);
TalkingAnimal.prototype.caption = function() {
    alert(this.name + ' sez "' + this.catchphrase + '"');
}
'''
#<pre>class Kitteh(TalkingAnimal):                       ---->
#    def __init__(self, name):
#        super(name, 'OH HAI')
#    def caption(self):
#        return super() + '!!!'</pre>
'''
var Kitteh = function() {
    this.__super__.__init__.call(this, name, "OH HAI");
    return this;
};
__extends(Kitteh, TalkingAnimal);
Kitteh.prototype.caption = function() {
    return this.__super__.caption + "!!!";
};
'''

def ClassDef(t, x):
    
    assert not x.keywords, x.keywords
    assert not x.starargs, x.starargs
    assert not x.kwargs, x.kwargs
    assert not x.decorator_list, x.decorator_list
    
    # If the bundle you're building contains any ClassDef,
    # this snippet ([from CoffeeScript](http://jashkenas.github.com/coffee-script/#classes)) will be included once at the top:
    #
    # <pre>var __extends = function(child, parent) {
    #    var ctor = function(){};
    #    ctor.prototype = parent.prototype;
    #    child.prototype = new ctor();
    #    child.prototype.__init__ = child;
    #    if (typeof parent.extended === "function") {
    #        parent.extended(child);
    #    }
    #    child.__super__ = parent.prototype;
    # };</pre>
    
    extends_helper_name = '__extends'
    t.addSnippet('''var %s = function(child, parent) {
    var ctor = function(){};
    ctor.prototype = parent.prototype;
    child.prototype = new ctor();
    child.prototype.__init__ = child;
    if (typeof parent.extended === "function") {
         parent.extended(child);
    }
    child.__super__ = parent.prototype;
};''' % extends_helper_name)
    
    
    NAME_STRING = x.name
    BODY = x.body
    if len(x.bases) > 0:
        assert len(x.bases) == 1
        assert isinstance(x.bases[0], ast.Name)
        SUPERCLASS_STRING = x.bases[0].id
    else:
        SUPERCLASS_STRING = None
    
    # Enforced restrictions:
    
    # * The class body must consist of nothing but FunctionDefs
    for node in BODY:
        assert isinstance(node, ast.FunctionDef)
    
    # * Each FunctionDef must have self as its first arg
    for node in BODY:
        argNames = [arg.arg for arg in node.args.args]
        assert len(argNames) > 0 and argNames[0] == 'self'
    
    # * (You need \_\_init\_\_) and (it must be the first FunctionDef)
    assert len(BODY) > 0
    INIT = BODY[0]
    assert str(INIT.name) == '__init__'
    
    # * \_\_init\_\_ may not contain a return statement
    INIT_ARGS = [arg.arg for arg in INIT.args.args]
    INIT_BODY = INIT.body
    for stmt in ast.walk(INIT):
        assert not isinstance(stmt, ast.Return)
    
    #<pre>var Kitteh = function(...args...) {
    #    ...__init__ body...
    #    return this;
    #};</pre>
    statements = [
        JSExpressionStatement(
            JSAssignmentExpression(
                JSName(NAME_STRING),
                INIT))]
    
    #<pre>__extends(Kitteh, TalkingAnimal);</pre>
    if SUPERCLASS_STRING is not None:
        statements.append(
            JSExpressionStatement(
                JSCall(
                    JSName(extends_helper_name),
                    [
                        JSName(NAME_STRING),
                        JSName(SUPERCLASS_STRING)])))
    
    # Now for the methods:
    for METHOD in BODY:
        if str(METHOD.name) != '__init__':
            
            #<pre>Kitteh.prototype.caption = function(...){...};
            statements.append(
                JSExpressionStatement(
                    JSAssignmentExpression(
                        JSAttribute(# Kitteh.prototype.caption
                            JSAttribute(# Kitteh.prototype
                                JSName(NAME_STRING),
                                'prototype'),
                            str(METHOD.name)),
                        METHOD)))
    
    return JSStatements(statements)


#### Call_super
def Call_super(t, x):
    if (
            isinstance(x.func, ast.Name) and
            x.func.id == 'super'):
        
        # Are we in a FuncDef and is it a method?
        METHOD = t.firstAncestorSubclassing(x, ast.FunctionDef)
        if METHOD and isinstance(t.parentOf(METHOD), ast.ClassDef):
            
            cls = t.parentOf(METHOD)
            assert len(cls.bases) == 1
            assert isinstance(cls.bases[0], ast.Name)
            SUPERCLASS_STRING = cls.bases[0].id
            CLASS_STRING = cls.name
            
            # <code>super(...)</code> &rarr; <code>SUPERCLASS.call(this, ...)</code>
            if METHOD.name == '__init__':
                return JSCall(
                            JSAttribute(
                                JSName(SUPERCLASS_STRING),
                                'call'),
                            [JSThis()] + x.args)
            
            # <code>super(...)</code> &rarr; <code>CLASSNAME.__super__.METHODNAME.call(this, ...)</code>
            else:
                return JSCall(
                            JSAttribute(
                                JSAttribute(
                                    JSAttribute(
                                        JSName(CLASS_STRING),
                                        '__super__'),
                                    METHOD.name),
                                'call'),
                            [JSThis()] + x.args)


#### FunctionDef
def FunctionDef(t, x):
    
    assert not x.decorator_list
    assert not any(getattr(x.args, k) for k in [
            'vararg', 'varargannotation', 'kwonlyargs', 'kwarg',
            'kwargannotation', 'defaults', 'kw_defaults'])
    
    NAME = x.name
    ARGS = [arg.arg for arg in x.args.args]
    BODY = x.body
    
    # <code>var ...local vars...</code>
    localVars = list(set(localNamesInBody(BODY)))
    if len(localVars) > 0:
        BODY = [JSVarStatement(
                            localVars,
                            [None] * len(localVars))] + BODY
    
    # If x is a method
    if isinstance(t.parentOf(x), ast.ClassDef):
        
        # Skip <code>self</code>
        ARGS = ARGS[1:]
        
        # Add <code>return this;</code> if we're <code>__init__</code>
        if NAME == '__init__':
            BODY =  BODY + [JSReturnStatement(
                                JSThis())]
        
        return JSFunction(
                            None,
                            ARGS,
                            BODY)
    
    # x is a function
    else:
        return JSExpressionStatement(
                    JSAssignmentExpression(
                        str(NAME),
                        JSFunction(
                                        None,
                                        ARGS,
                                        BODY)))



########NEW FILE########
__FILENAME__ = comprehensions

import ast
from pj.js_ast import *

#### ListComp
# Transform
# <pre>[EXPR for NAME in LIST]</pre>
# or
# <pre>[EXPR for NAME in LIST if CONDITION]</pre>
def ListComp(t, x):
    
    assert len(x.generators) == 1
    assert len(x.generators[0].ifs) <= 1
    assert isinstance(x.generators[0], ast.comprehension)
    assert isinstance(x.generators[0].target, ast.Name)
    
    EXPR = x.elt
    NAME = x.generators[0].target
    LIST = x.generators[0].iter
    if len(x.generators[0].ifs) == 1:
        CONDITION = x.generators[0].ifs[0]
    else:
        CONDITION = None
    
    __new = t.newName()
    __old = t.newName()
    __i = t.newName()
    __bound = t.newName()
    
    # Let's contruct the result from the inside out:
    #<pre>__new.push(EXPR);</pre>
    push = JSExpressionStatement(
            JSCall(
                JSAttribute(
                    JSName(__new),
                    'push'),
                [EXPR]))
    
    # If needed, we'll wrap that with:
    #<pre>if (CONDITION) {
    #    <i>...push...</i>
    #}</pre>
    if CONDITION:
        pushIfNeeded = JSIfStatement(
                CONDITION,
                push,
                None)
    else:
        pushIfNeeded = push
    
    # Wrap with:
    #<pre>for(
    #        var __i = 0, __bound = __old.length;
    #        __i &lt; __bound;
    #        __i++) {
    #    var NAME = __old[__i];
    #    <i>...pushIfNeeded...</i>
    #}</pre>
    forloop = JSForStatement(
                    JSVarStatement(
                        [__i, __bound],
                        [0, JSAttribute(
                                JSName(__old),
                                'length')]),
                    JSBinOp(JSName(__i), JSOpLt(), JSName(__bound)),
                    JSAugAssignStatement(JSName(__i), JSOpAdd(), JSNum(1)),
                    [
                        JSVarStatement(
                            [NAME.id],
                            [JSSubscript(
                                JSName(__old),
                                JSName(__i))]),
                        pushIfNeeded])
    
    # Wrap with:
    #<pre>function() {
    #    var __new = [], __old = LIST;
    #    <i>...forloop...</i>
    #    return __new;
    #}
    func = JSFunction(
        None,
        [],
        [
            JSVarStatement(
                [__new, __old],
                [JSList([]), LIST]),
            forloop,
            JSReturnStatement(
                JSName(__new))])
    
    # And finally:
    #<pre>((<i>...func...</i>).call(this))</pre>
    invoked = JSCall(
            JSAttribute(
                func,
                'call'),
            [JSThis()])
    
    return invoked


########NEW FILE########
__FILENAME__ = exceptions

import ast
from pj.js_ast import *

#### TryExcept, Raise
# Example:
#<pre>try:
#    raise EpicFail('omg noes!')
#except Exception as NAME:
#    ...</pre>
# becomes
#<pre>try {
#    throw {'name': 'EpicFail', 'message': 'omg noes!'};
#}
#catch(NAME) {
#    ...
#}</pre>
# 
# This is the only form supported so far.
def TryExcept(t, x):
    assert not x.orelse
    assert len(x.handlers) == 1
    assert isinstance(x.handlers[0].type, ast.Name)
    assert x.handlers[0].type.id == 'Exception'
    assert x.handlers[0].name
    
    NAME = x.handlers[0].name
    TRY_BODY = x.body
    CATCH_BODY = x.handlers[0].body
    
    return JSTryCatchStatement(
                TRY_BODY,
                NAME,
                CATCH_BODY)


def Raise(t, x):
    
    if isinstance(x.exc, ast.Name):
        name = x.exc.id
        arg = JSStr('')
    else:
        assert isinstance(x.exc, ast.Call)
        assert isinstance(x.exc.func, ast.Name)
        assert len(x.exc.args) == 1
        assert all((not x) for x in (
            x.exc.keywords, x.exc.starargs, x.exc.kwargs))
        name = x.exc.func.id
        arg = x.exc.args[0]
    
    return JSThrowStatement(
                JSDict(
                    [JSStr('name'), JSStr('message')],
                    [JSStr(name), arg]))


########NEW FILE########
__FILENAME__ = forloops

import ast
from pj.js_ast import *


#### Case: Ranges
# Transform
#<pre>for NAME in rage(BOUND):
#for NAME in rage(START, BOUND):</pre>
# to
#<pre>for (var NAME = 0, __bound = BOUND; NAME < __bound; NAME++)
#for (var NAME = START, __bound = BOUND; NAME < __bound; NAME++)</pre>
def For_range(t, x):
    if (
                isinstance(x.target, ast.Name) and
                isinstance(x.iter, ast.Call) and
                isinstance(x.iter.func, ast.Name) and
                x.iter.func.id == 'range' and
                len(x.iter.args) in [1, 2]) and (not x.orelse):
        
        NAME = x.target
        LDOTS = x.body
        if len(x.iter.args) == 1:
            START = JSNum(0)
            BOUND = x.iter.args[0]
        else:
            START = x.iter.args[0]
            BOUND = x.iter.args[1]
        
        __bound = t.newName()
        
        return JSForStatement(
                    JSVarStatement(
                        [NAME.id, __bound],
                        [START, BOUND]),
                    JSBinOp(JSName(NAME.id), JSOpLt(), __bound),
                    JSAugAssignStatement(
                        JSName(NAME.id), JSOpAdd(), JSNum(1)),
                    LDOTS)

#### Case: Dicts
# Transform
#<pre>for NAME in dict(EXPR): 
#    ...</pre>
# to
#<pre>var __dict = EXPR;
#for (var NAME in __dict) {
#    if (__dict.hasOwnProperty(NAME)) {
#       ...
#    }
#}</pre>
def For_dict(t, x):
    if (
            isinstance(x.iter, ast.Call) and
            isinstance(x.iter.func, ast.Name) and
            x.iter.func.id == 'dict' and
            len(x.iter.args) == 1) and (not x.orelse):
        
        assert isinstance(x.target, ast.Name)
        
        NAME = x.target
        EXPR = x.iter.args[0]
        LDOTS = x.body
        
        __dict = t.newName()
        
        return JSStatements([
                    JSVarStatement(
                        [__dict],
                        [EXPR]),
                    JSForeachStatement(
                        NAME.id,
                        JSName(__dict),
                        [JSIfStatement(
                            JSCall(
                                JSAttribute(
                                    JSName(__dict),
                                    'hasOwnProperty'),
                                [JSName(NAME.id)]),
                            LDOTS,
                            None)])])


#### Default: assume it's an array
# Transform
#<pre>for NAME in EXPR:
#    ...</pre>
# to
#<pre>var NAME, __list = EXPR;
#for (
#        var __i = 0, __bound = __list.length;
#        __i < __bound;
#        __i++) {
#    NAME = __list[__i];
#    ...
#}</pre>
def For_default(t, x):
    
    assert isinstance(x.target, ast.Name)
    
    NAME = x.target
    EXPR = x.iter
    LDOTS = x.body
    
    __list = t.newName()
    __bound = t.newName()
    __i = t.newName()
    
    return JSStatements([
                JSVarStatement(
                    [NAME.id, __list],
                    [None, EXPR]),
                JSForStatement(
                    JSVarStatement(
                        [__i, __bound],
                        [
                            JSNum(0),
                            JSAttribute(
                                JSName(__list),
                                'length')]),
                    JSBinOp(
                        JSName(__i),
                        JSOpLt(),
                        JSName(__bound)),
                    JSExpressionStatement(
                        JSAugAssignStatement(
                            JSName(__i),
                            JSOpAdd(),
                            JSNum(1))),
                    [
                        JSExpressionStatement(
                            JSAssignmentExpression(
                                JSName(NAME.id),
                                JSSubscript(
                                    JSName(__list),
                                    JSName(__i))))
                    ] + LDOTS)])


For = [For_range, For_dict, For_default]


########NEW FILE########
__FILENAME__ = obvious

#### Statements

import ast
from functools import reduce
from pj.js_ast import *

# Assign
def Assign(t, x):
    y = JSAssignmentExpression(x.targets[-1], x.value)
    for i in range(len(x.targets) - 1):
        y = JSAssignmentExpression(x.targets[-(2 + i)], y)
    return JSExpressionStatement(y)

# **AugAssign**
def AugAssign(t, x):
    return JSAugAssignStatement(x.target, x.op, x.value)

# **If**
def If(t, x):
    return JSIfStatement(x.test, x.body, x.orelse)

# **While**
def While(t, x):
    assert not x.orelse
    return JSWhileStatement(x.test, x.body)

# **Break**
def Break(t, x):
    return JSBreakStatement()

# **Continue**
def Continue(t, x):
    return JSContinueStatement()

# **Pass**
def Pass(t, x):
    return JSPass()

# **Return** 
# 
# x.value is None for blank return statements
def Return(t, x):
    return JSReturnStatement(x.value)

# **Delete**
def Delete(t, x):
    for t in x.targets:
        assert isinstance(t, ast.Subscript)
        assert isinstance(t.slice, ast.Index)
    return JSStatements([
                JSDeleteStatement(t.value, t.slice.value)
                for t in x.targets])


#### Expressions

# **Expr**
#
# See [pj.transformations.special](special.py) for special cases
def Expr_default(t, x):
    return JSExpressionStatement(x.value)

# **List**
def List(t, x):
    return JSList(x.elts)

# **Tuple**
def Tuple(t, x):
    return JSList(x.elts)

# **Tuple**
def Dict(t, x):
    return JSDict(x.keys, x.values)

# **Lambda**
def Lambda(t, x):
    assert not any(getattr(x.args, k) for k in [
            'vararg', 'varargannotation', 'kwonlyargs', 'kwarg',
            'kwargannotation', 'defaults', 'kw_defaults'])
    return JSFunction(
                None,
                [arg.arg for arg in x.args.args],
                [JSReturnStatement(x.body)])

# **IfExp**
def IfExp(t, x):
    return JSIfExp(x.test, x.body, x.orelse)

# **Call**
#
# See [pj.transformations.special](special.py) for special cases
def Call_default(t, x):
    assert not any([x.keywords, x.starargs, x.kwargs])
    return JSCall(x.func, x.args)

# **Attribute**
def Attribute(t, x):
    return JSAttribute(x.value, str(x.attr))

# **Subscript**
def Subscript(t, x):
    if isinstance(x.slice, ast.Index):
        return JSSubscript(x.value, x.slice.value)

# **UnaryOp**
def UnaryOp(t, x):
    return JSUnaryOp(x.op, x.operand)

# **BinOp**
#
# See [pj.transformations.special](special.py) for special cases
def BinOp_default(t, x):
    return JSBinOp(x.left, x.op, x.right)

# **BoolOp**
def BoolOp(t, x):
    return reduce(
                lambda left, right: JSBinOp(left, x.op, right),
                x.values)

# **Compare**
def Compare(t, x):
    exps = [x.left] + x.comparators
    bools = []
    for i in range(len(x.ops)):
        bools.append(JSBinOp(exps[i], x.ops[i], exps[i + 1]))
    return reduce(
            lambda x, y: JSBinOp(x, JSOpAnd(), y),
            bools)

#### Atoms

# **Num**
def Num(t, x):
    return JSNum(x.n)

# **Str**
def Str(t, x):
    return JSStr(x.s)

# **Name**
# 
# {True,False,None} are Names
def Name_default(t, x):
    cls = {
        'True': JSTrue,
        'False': JSFalse,
        'None': JSNull,
    }.get(x.id)
    if cls:
        return cls()
    else:
        return JSName(x.id)

#### Ops

# <code>in</code>
def In(t, x):
  return JSOpIn()

# <code>+</code>
def Add(t, x):
    return JSOpAdd()

# <code>-</code>
def Sub(t, x):
    return JSOpSub()

# <code>*</code>
def Mult(t, x):
    return JSOpMult()

# <code>/</code>
def Div(t, x):
    return JSOpDiv()

# <code>%</code>
def Mod(t, x):
    return JSOpMod()

# <code>&gt;&gt;</code>
def RShift(t, x):
    return JSOpRShift()

# <code>&lt;&lt;</code>
def LShift(t, x):
    return JSOpLShift()

def BitXor(t, x):
    return JSOpBitXor()

def BitAnd(t, x):
    return JSOpBitAnd()

def BitOr(t, x):
    return JSOpBitOr()

def Invert(t, x):
    return JSOpInvert()

# <code>and</code>
def And(t, x):
    return JSOpAnd()

# <code>or</code>
def Or(t, x):
    return JSOpOr()

# <code>not</code>
def Not(t, x):
    return JSOpNot()

# <code>==</code> and <code>!=</code> are in [special.py](special.py)
# because they transform to <code>===</code> and <code>!==</code>

# <code>&lt;</code>
def Lt(t, x):
    return JSOpLt()

# <code>&lt;=</code>
def LtE(t, x):
    return JSOpLtE()

# <code>&gt;</code>
def Gt(t, x):
    return JSOpGt()

# <code>&gt;=</code>
def GtE(t, x):
    return JSOpGtE()



########NEW FILE########
__FILENAME__ = special

import ast, re
from pj.js_ast import *


#### Expr

# docstrings &rarr; comment blocks
def Expr_docstring(t, x):
    if isinstance(x.value, ast.Str):
        return JSCommentBlock(x.value.s)

from pj.transformations.obvious import Expr_default
Expr = [Expr_docstring, Expr_default]


#### BinOp
# <code>2**3</code> &rarr; <code>Math.pow(2, 3)</code>
def BinOp_pow(t, x):
    if isinstance(x.op, ast.Pow):
        return JSCall(
                    JSAttribute(
                        JSName('Math'),
                        'pow'),
                    [x.left, x.right])


from pj.transformations.obvious import BinOp_default
BinOp = [BinOp_pow, BinOp_default]


#### Name
# <code>self</code> &rarr; <code>this</code>
def Name_self(t, x):
    if x.id == 'self':
        return JSThis()

from pj.transformations.obvious import Name_default
Name = [Name_self, Name_default]

#### Call

# <code>typeof(x)</code> &rarr; <code>(typeof x)</code>
def Call_typeof(t, x):
    if (
            isinstance(x.func, ast.Name) and
            x.func.id == 'typeof'):
        assert len(x.args) == 1
        return JSUnaryOp(
                    JSOpTypeof(),
                    x.args[0])


# <code>isinstance(x, y)</code> &rarr; <code>(x instanceof y)</code>
def Call_isinstance(t, x):
    if (
            isinstance(x.func, ast.Name) and
            x.func.id == 'isinstance'):
        assert len(x.args) == 2
        return JSBinOp(
                    x.args[0],
                    JSOpInstanceof(),
                    x.args[1])



# <code>print(...)</code> &rarr; <code>console.log(...)</code>
def Call_print(t, x):
    if (
            isinstance(x.func, ast.Name) and
            x.func.id == 'print'):
        return JSCall(
                    JSAttribute(
                        JSName('console'),
                        'log'),
                    x.args)


# <code>len(x)</code> &rarr; <code>x.length</code>
def Call_len(t, x):
    if (
            isinstance(x.func, ast.Name) and
            x.func.id == 'len' and
            len(x.args) == 1):
        return JSAttribute(
                        x.args[0],
                        'length')


#### Call_new
#
# Transform
#<pre>Foo(...)</pre>
# to
#<pre>(new Foo(...))</pre>
# More generally, this transformation applies iff a Name starting with <code>[A-Z]</code> is Called.
def Call_new(t, x):
    
    def getNameString(x):
        if isinstance(x, ast.Name):
            return x.id
        elif isinstance(x, ast.Attribute):
            return str(x.attr)
        elif isinstance(x, ast.Subscript):
            if isinstance(x.slice, ast.Index):
                return str(x.slice.value)
    
    NAME_STRING = getNameString(x.func)
    
    if NAME_STRING and re.search(r'^[A-Z]', NAME_STRING):
        assert not any([x.keywords, x.starargs, x.kwargs])
        return JSNewCall(x.func, x.args)


from pj.transformations.classes import Call_super
from pj.transformations.obvious import Call_default
Call = [Call_typeof, Call_isinstance, Call_print, Call_len, Call_new, Call_super, Call_default]


#### Ops

# <code>==</code>
#
# Transform to <code>===</code>
def Eq(t, x):
    return JSOpStrongEq()

# <code>!=</code>
# 
# Transform to <code>!==</code>
def NotEq(t, x):
    return JSOpStrongNotEq()


#### ImportFrom
# Only accept imports of these forms:
# <code>from foo import ...names...</code>
# <code>from foo import *</code>
def ImportFrom(t, x):
    for name in x.names:
        assert name.asname is None
    assert x.level == 0
    return JSPass()


########NEW FILE########
__FILENAME__ = colorflash

from mylib.color import Color
from mylib.tweening import Tween, easeInOut
from mylib.random import randint
from mylib.misc import bind


CHANGE_EVERY = 1000
TRANSITION_DURATION = 250


class Controller:
    
    def __init__(self):
        self._newColor = self._oldColor = Color(255, 255, 255)
        self._changeColor()
    
    def _changeColor(self):
        
        self._oldColor = self._newColor
        self._newColor = Color(
                randint(0, 255),
                randint(0, 255),
                randint(0, 255))
        
        def callback(t):
            document.body.style.background = (self._oldColor
                                                    ._interpolatedToward(self._newColor, t)
                                                    ._webString())
        
        def onComplete(t):
            document.title = self._newColor._webString()
        
        Tween({
            '_duration': TRANSITION_DURATION,
            '_callback': bind(callback, self),
            '_easing': easeInOut,
            '_onComplete': bind(onComplete, self),
        })
        
        setTimeout(
            bind(arguments.callee, self),
            CHANGE_EVERY)


def main():
    Controller()


window.colorflash = {
    'main': main,
}

########NEW FILE########
__FILENAME__ = make

import os, sys, time
from subprocess import check_call

import pj.api
from pyxc.util import parentOf


EXAMPLES_ROOT = parentOf(parentOf(os.path.abspath(__file__)))
PATH = [
    '%s/colorflash/js' % EXAMPLES_ROOT,
    '%s/mylib/js' % EXAMPLES_ROOT,
]


def main():
    
    check_call(['mkdir', '-p', 'build'])
    
    js = None
    
    for closureMode in ['', 'pretty', 'simple']:
        
        filename = {
            '': 'colorflash.raw.js',
            'pretty': 'colorflash.pretty.js',
            'simple': 'colorflash.min.simple.js',
        }[closureMode]
        
        path = 'build/%s' % filename
        
        sys.stderr.write('%s... ' % path)
        start = time.time()
        
        if not js:
            js = pj.api.buildBundle('colorflash.colorflash', path=PATH)
        
        with open(path, 'wb') as f:
            f.write(pj.api.closureCompile(js, closureMode))
        
        ms = int((time.time() - start) * 1000)
        sys.stderr.write('done. (%d ms)\n' % ms)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings

import os, sys


def up(n):
    path = os.path.abspath(__file__)
    return '/'.join(path.rstrip('/').split('/')[:-n])
repoPath = up(3)
sys.path = [repoPath] + sys.path + [repoPath]


#### PJ Settings:
PJ_PATH = [
    up(2) + '/colorflash/js',
    up(2) + '/mylib/js',
]
# Closure Compiler is slow to launch and run (> 1 sec),
# so you will rarely want have it on when developing
PJ_CLOJURE_MODE = None


#### Django settings:

DEBUG = True
ROOT_URLCONF = 'colorflash.urls'
LANGUAGE_CODE = 'en-us'
USE_I18N = True
ADMINS = []
MIDDLEWARE_CLASSES = []
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)
TEMPLATE_DIRS = [up(1) + '/templates']








########NEW FILE########
__FILENAME__ = urls

from django.conf.urls.defaults import *


urlpatterns = patterns('colorflash.views',
    url(r'^$', 'index', name='index'),
)


urlpatterns += patterns('pj.django',
    url(r'^static/js/colorflash\.js$',
            'jsView',
            {'main': 'colorflash.colorflash'},
            name='colorflash_js'),
)
########NEW FILE########
__FILENAME__ = views


from django.shortcuts import render_to_response


def index(request):
    from django.http import HttpResponseRedirect
    return render_to_response('colorflash/index.html')


########NEW FILE########
__FILENAME__ = color

from mylib.hex import hex_256_encode
from mylib.math import clamp


class Color:
    
    def __init__(self, r, g, b):
        self.r = clamp(Math.round(r), 0, 255)
        self.g = clamp(Math.round(g), 0, 255)
        self.b = clamp(Math.round(b), 0, 255)

    def _interpolatedToward(self, c2, fraction):
        return Color(
                    self.r + (c2.r - self.r) * fraction,
                    self.g + (c2.g - self.g) * fraction,
                    self.b + (c2.b - self.b) * fraction)
    
    def _webString(self):
        return (
                    '#' +
                    hex_encode_256(self.r) +
                    hex_encode_256(self.g) +
                    hex_encode_256(self.b))



########NEW FILE########
__FILENAME__ = hex


def hex_encode_256(n):
    if n == 0:
        result = '00'
    elif 0 <= n <= 15:
        result = '0' + n.toString(16)
    else:
        result = n.toString(16)
    return result



########NEW FILE########
__FILENAME__ = math


def clamp(value, min, max):
    return Math.min(Math.max(value, min), max)



########NEW FILE########
__FILENAME__ = misc


def bind(f, obj):
    return lambda: f.apply(obj, arguments)


########NEW FILE########
__FILENAME__ = random


# 'Random number from [0.0, 1.0)'
def random():
    x = Math.random()
    return 0 if x == 1 else x


# Assumes a, b are integers and
# returns a random integer from [a, b]
def randint(a, b):
    return Math.floor(random() * (b - a + 1)) + a


########NEW FILE########
__FILENAME__ = tweening

from mylib.misc import bind
from mylib.math import bind


def linear(t):
    return t

def easeIn(t):
    return 1 - Math.pow(1 - t, 3)

def easeOut(t):
    return t * t * t

def easeInOut(t):
    return 3 * t * t - 2 * t * t * t


#<pre>Tween({
#   '_duration': 1000,
#   '_callback': lambda t: console.log(t),
#   '_easing': easeIn, # Default: linear
#})</pre>
class Tween:
    
    def __init__(self, info):
        
        self._startedAt = Date().getTime()
        
        self._duration = info._duration
        self._callback = info._callback
        self._easing = info._easing or linear
        
        self._tick()
    
    def _tick(self):
        
        t = clamp((Date().getTime() - self._startedAt) / self._duration, 0, 1)
        
        self._callback(t)
        
        if t < 1:
            setTimeout(bind(self._tick, self), 1)



########NEW FILE########
__FILENAME__ = importing

import os, re

from pyxc.util import DirectedGraph

# Return a list of module names in an order that doesn't violate the
# [dependency graph](http://en.wikipedia.org/wiki/Dependency_graph)
def orderedModules(sourcePath, mainModule):
    digraph = dependencyGraph(sourcePath, mainModule)
    return list(digraph.topologicalOrdering)


def dependencyGraph(sourcePath, firstModule):
    
    digraph = DirectedGraph()
    
    todo = set([firstModule])
    done = set()
    
    while len(todo) > 0:
        
        module = todo.pop()
        done.add(module)
        
        digraph.addNode(module)
        
        # Load the code
        path = sourcePath.pathForModule(module)
        with open(path, 'r') as f:
            py = f.read()
        
        # Handle each prereq
        for prereq in parseImports(py):
            digraph.addArc(module, prereq)
            if prereq not in done:
                todo.add(prereq)
    
    return digraph


# Python code &rarr; list of imported modules
def parseImports(py):
    imports = []
    for line in py.split('\n'):
        for m in re.finditer(r'^\s*from[ \t]+([^ \t]+)[ \t]+import', line):
            imports.append(m.group(1) or m.group(2))
    return imports


class SourcePath:
    
    def __init__(self, folders):
        self.folders = folders
    
    def pathForModule(self, module, exts=['py', 'pj', 'js']):
        
        # Find all matches
        paths = []
        for folder in self.folders:
            for ext in exts:
                path = '%s/%s.%s' % (
                                        folder.rstrip('/'),
                                        '/'.join(module.split('.')),
                                        ext)
                if os.path.isfile(path):
                    paths.append(path)
        
        # Do we have exactly one match?
        if len(paths) == 1:
            return paths[0]
        elif len(paths) == 0:
            raise Exception('Module not found: "%s". Path: %s' % (module, repr(self.folders)))
        elif len(paths) > 1:
            raise Exception('Multiple files found for module "%s": %s' % (module, repr(paths)))


########NEW FILE########
__FILENAME__ = pyxc_exceptions

class PyxcError(Exception): pass

class NoTransformationForNode(PyxcError): pass

########NEW FILE########
__FILENAME__ = transforming

from pyxc.util import usingPython3
assert usingPython3()

import sys, os, ast, json, hashlib
from pyxc.util import rfilter, parentOf, randomToken

from pyxc.pyxc_exceptions import NoTransformationForNode

#### TargetNode

class TargetNode:
    
    def __init__(self, *args):
        self.args = args
    
    def __str__(self):
        return ''.join(
                    str(x) for x in
                        self.emit(*self.transformedArgs))


#### SourceMap

class SourceMap:
    
    def __init__(self, fileString, nextMappingId=0):
        
        self.fileString = fileString
        
        self.nextMappingId = nextMappingId
        self.node_mappingId_map = {}
        self.mappings = []
        
        self.linemaps = [[]]
        self.strings = []
    
    def getCode(self):
        return ''.join(self.strings)
    
    def handleNode(self, node, parentMappingId=0):
        
        mappingId = self.mappingIdForNode(node)
        if mappingId is None:
            mappingId = parentMappingId
        
        arr = node.emit(*node.transformedArgs)
        for x in arr:
            if isinstance(x, str):
                if x:
                    # Store the string
                    self.strings.append(x)
                    
                    # Update self.linemaps
                    linemap = self.linemaps[-1]
                    for c in x:
                        linemap.append(mappingId)
                        if c == '\n':
                            linemap = []
                            self.linemaps.append(linemap)
            else:
                assert isinstance(x, TargetNode)
                self.handleNode(x, parentMappingId=mappingId)
    
    def mappingIdForNode(self, node):
        if node in self.node_mappingId_map:
            return self.node_mappingId_map[node]
        else:
            lineno = getattr(node.pyNode, 'lineno', None)
            col_offset = getattr(node.pyNode, 'col_offset', None)
            if (lineno is None) or (col_offset is None):
                return None
            else:
                mappingId = self.nextMappingId
                self.nextMappingId += 1
                self.node_mappingId_map[node] = mappingId
                self.mappings.append([self.fileString, lineno, col_offset])
                return mappingId


def exportSourceMap(linemaps, mappings, sourceDict):
    
    # Get filekeys from mappings
    filekeys = []
    filekeysSet = set()
    for tup in mappings:
        k = tup[0]
        if k not in filekeysSet:
            filekeysSet.add(k)
            filekeys.append(k)
    
    arr = ['/** Begin line maps. **/{ "file" : "", "count": %d }\n' % len(filekeys)]
    
    for linemap in linemaps:
        arr.append(json.dumps(linemap, separators=(',', ':')) + '\n')
    
    arr.append('/** Begin file information. **/\n')
    for k in filekeys:
        sourceInfo = sourceDict[k]
        arr.append('%s\n' % json.dumps([{
            'module': sourceInfo['module'],
            'sha1': hashlib.sha1(sourceInfo['code'].encode('utf-8')).hexdigest(),
            'path': sourceInfo['path'],
            'name': sourceInfo['path'].split('/')[-1],
            'k': k,
        }]))
    arr.append('/** Begin mapping definitions. **/\n')
    
    for mapping in mappings:
        arr.append(json.dumps(mapping, separators=(',', ':')) + '\n')
    
    return ''.join(arr)


#### Transformer

class Transformer:
    
    def __init__(self, parentModule, statementsClass):
        self.transformationsDict = loadTransformationsDict(parentModule)
        self.statementsClass = statementsClass
        self.snippets = set()
    
    def transformCode(self, py):
        
        top = ast.parse(py)
        body = top.body
        
        self.node_parent_map = buildNodeParentMap(top)
        
        transformedBody = [self._transformNode(x) for x in body]
        result = self.statementsClass(transformedBody)
        self._finalizeTargetNode(result)
        
        self.node_parent_map = None
        
        return result
    
    def parentOf(self, node):
        return self.node_parent_map.get(node)
    
    def firstAncestorSubclassing(self, node, cls):
        parent = self.parentOf(node)
        if parent is not None:
            if isinstance(parent, cls):
                return parent
            else:
                return self.firstAncestorSubclassing(parent, cls)
    
    def newName(self):
        #LATER: generate better names
        return randomToken(20)
    
    def addSnippet(self, targetCode):
        self.snippets.add(targetCode)
    
    def _transformNode(self, x):
        
        if isinstance(x, list) or isinstance(x, tuple):
            return [self._transformNode(child) for child in x]
        
        elif isinstance(x, ast.AST):
            for t in self.transformationsDict.get(x.__class__.__name__, []):
                y = t(self, x)
                if y is not None:
                    self._finalizeTargetNode(y, pyNode=x)
                    return y
            raise NoTransformationForNode(repr(x))
        
        elif isinstance(x, TargetNode):
            self._finalizeTargetNode(x)
            return x
        
        else:
            # e.g. an integer
            return x
    
    def _finalizeTargetNode(self, y, pyNode=None):
        y.pyNode = pyNode
        y.transformedArgs = [self._transformNode(arg) for arg in y.args]
        y.transformer = self


#### Helpers

def getPythonAstNames():
    #LATER: do this properly
    return rfilter(r'[A-Z][a-zA-Z]+', dir(ast))


def loadTransformationsDict(parentModule):
    # transformationsDict = {
    #     'NodeName': [...transformation functions...]
    # }
    d = {}
    astNames = list(getPythonAstNames())
    filenames = rfilter(
                            r'^[^.]+\.py$',
                            os.listdir(parentOf(parentModule.__file__)))
    for filename in filenames:
        if filename != '__init__.py':
            modName = 'pj.transformations.%s' % filename.split('.')[0]
            __import__(modName)
            mod = sys.modules[modName]
            for name in dir(mod):
                if name in astNames:
                    assert name not in d
                    value = getattr(mod, name)
                    if not isinstance(value, list) or isinstance(value, tuple):
                        value = [value]
                    d[name] = value
    return d


def buildNodeParentMap(top):
    
    node_parent_map = {}
    
    def _processNode(node):
        for k in node._fields:
            x = getattr(node, k)
            if not (isinstance(x, list) or isinstance(x, tuple)):
                x = [x]
            for y in x:
                if isinstance(y, ast.AST):
                    node_parent_map[y] = node
                    _processNode(y)
    
    _processNode(top)
    
    return node_parent_map


########NEW FILE########
__FILENAME__ = util

import json, sys, traceback, re, random, copy, ast
import os, subprocess, tempfile
from subprocess import check_call, call


def simplePost(url, POST={}):
    try:
        import urllib.parse, urllib.request
        data = urllib.parse.urlencode(POST)
        return urllib.request.urlopen(url, data).read()
    except ImportError:
        import urllib, urllib2
        data = urllib.urlencode(POST)
        return urllib2.urlopen(urllib2.Request(url, data)).read()


def delimitedList(item, arr, dest=None, delimAtEnd=False):
    if dest is None:
        dest = []
    if arr:
        dest.append(arr[0])
    for i in range(1, len(arr)):
        dest.append(item)
        dest.append(arr[i])
    if delimAtEnd:
        dest.append(item)
    return dest


def usingPython3():
    return sys.version_info[0] == 3


def parentOf(path):
    return '/'.join(path.rstrip('/').split('/')[:-1])



def topLevelNamesInBody(body):
    names = set()
    for x in body:
        names |= namesInNode(x)
    return names


def localNamesInBody(body):
    names = set()
    for node in body:
        names |= namesInNode(node)
        for x in ast.walk(node):
            names |= namesInNode(x)
    return names


def namesInNode(x):
    names = set()
    if isinstance(x, ast.Assign):
        for target in x.targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    elif (
            isinstance(x, ast.FunctionDef) or
            isinstance(x, ast.ClassDef)):
        names.add(x.name)
    return names



def exceptionRepr(exc_info=None):
    
    if usingPython3():
        from io import StringIO
    else:
        from StringIO import StringIO
    
    if not exc_info:
        exc_info = sys.exc_info()
    f = StringIO()
    traceback.print_exception(exc_info[0], exc_info[1], exc_info[2], file=f)
    return f.getvalue()


# Write a JSON representation of the exception to stderr for
# the script that's invoking us (e.g. pj.api under Python 2)
def writeExceptionJsonAndDie(e):
    sys.stderr.write('%s\n' % json.dumps({
        'name': e.__class__.__name__,
        'message': exceptionRepr(),
    }))
    sys.exit(1)


def randomToken(n):
    while True:
        token = ''.join(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') for i in range(n))
        if not token.isdigit():
            return token


class CyclicGraphError(Exception): pass


class DirectedGraph:
    
    def __init__(self):
        self._graph = {}
    
    def addNode(self, x):
        if x not in self._graph:
            self._graph[x] = set()
    
    def addArc(self, x, y):
        self.addNode(x)
        self.addNode(y)
        self._graph[x].add(y)
    
    @property
    def topologicalOrdering(self):
        
        def topologicalOrderingDestructive(d):
            
            if len(d) == 0:
                return []
            
            possibleInitialNodes = set(d.keys())
            for k, v in d.items():
                if len(v) > 0:
                    possibleInitialNodes.discard(k)
            if len(possibleInitialNodes) == 0:
                raise CyclicGraphError(repr(d))
            initialNode = possibleInitialNodes.pop()
            
            for k, v in d.items():
                v.discard(initialNode)
            del d[initialNode]
            
            return [initialNode] + topologicalOrderingDestructive(d)
        
        return topologicalOrderingDestructive(copy.deepcopy(self._graph))


def rfilter(r, it, propFilter={}, invert=False):
    '''
    
    >>> list(rfilter(r'^.o+$', ['foo', 'bar']))
    ['foo']
    
    >>> list(rfilter(r'^.o+$', ['foo', 'bar'], invert=True))
    ['bar']
    
    >>> list(rfilter(r'-(?P<x>[^-]+)-', ['fooo-baar-ooo', 'fooo-fooo-ooo'], propFilter={'x': r'o{3}'}))
    ['fooo-fooo-ooo']
    
    >>> list(rfilter(r'-(?P<x>[^-]+)-', ['fooo-.*-ooo', 'fooo-fooo-ooo', 'fooo-.+-ooo'], propFilter={'x': ['.*', '.+']}))
    ['fooo-.*-ooo', 'fooo-.+-ooo']
    
    '''
    
    # Supports Python 2 and 3
    if isinstance(r, str):
        r = re.compile(r)
    try:
        if isinstance(r, unicode):
            r = re.compile
    except NameError:
        pass
    
    for x in it:
        m = r.search(x)
        ok = False
        if m:
            ok = True
            if propFilter:
                d = m.groupdict()
                for k, v in propFilter.items():
                    if k in d:
                        if isinstance(v, basestring):
                            if not re.search(v, d[k]):
                                ok = False
                                break
                        else:
                            if d[k] not in v:
                                ok = False
                                break
        
        if invert:
            if not ok:
                yield x
        else:
            if ok:
                yield x


class SubprocessError(Exception):
    
    def __init__(self, out, err, returncode):
        self.out = out
        self.err = err
        self.returncode = returncode
        self.msg = repr('--- out ---\n%s\n--- err ---\n%s\n--- code: %d ---' % (self.out, self.err, self.returncode))


def communicateWithReturncode(cmd, input=None, **Popen_kwargs):
    if input is not None:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, **Popen_kwargs)
        (out, err) = p.communicate(input=input)
    else:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **Popen_kwargs)
        (out, err) = p.communicate()
    return out, err, p.returncode


def communicate(cmd, assertZero=False, input='', **Popen_kwargs):
    out, err, returncode = communicateWithReturncode(cmd, input=input, **Popen_kwargs)
    return (out, err)


def check_communicate(cmd, input='', **Popen_kwargs):
    out, err, returncode = communicateWithReturncode(cmd, input=input, **Popen_kwargs)
    if returncode != 0:
        raise SubprocessError(out, err, returncode)
    return (out, err)


class TempDir:
    
    def __init__(self):
        self.path = tempfile.mkdtemp()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        subprocess.check_call(['rm', '-rf', self.path])


########NEW FILE########
