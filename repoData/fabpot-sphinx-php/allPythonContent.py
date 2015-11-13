__FILENAME__ = configurationblock
# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2010-2012 Fabien Potencier
    :license: MIT, see LICENSE for more details.
"""

from docutils.parsers.rst import Directive, directives
from docutils import nodes
from string import upper

class configurationblock(nodes.General, nodes.Element):
    pass

class ConfigurationBlock(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}
    formats = {
        'html':            'HTML',
        'xml':             'XML',
        'php':             'PHP',
        'yaml':            'YAML',
        'jinja':           'Twig',
        'html+jinja':      'Twig',
        'jinja+html':      'Twig',
        'php+html':        'PHP',
        'html+php':        'PHP',
        'ini':             'INI',
        'php-annotations': 'Annotations',
        'php-standalone':  'Standalone Use',
        'php-symfony':     'Framework Use',
    }

    def run(self):
        env = self.state.document.settings.env

        node = nodes.Element()
        node.document = self.state.document
        self.state.nested_parse(self.content, self.content_offset, node)

        entries = []
        for i, child in enumerate(node):
            if isinstance(child, nodes.literal_block):
                # add a title (the language name) before each block
                #targetid = "configuration-block-%d" % env.new_serialno('configuration-block')
                #targetnode = nodes.target('', '', ids=[targetid])
                #targetnode.append(child)

                innernode = nodes.emphasis(self.formats[child['language']], self.formats[child['language']])

                para = nodes.paragraph()
                para += [innernode, child]

                entry = nodes.list_item('')
                entry.append(para)
                entries.append(entry)

        resultnode = configurationblock()
        resultnode.append(nodes.bullet_list('', *entries))

        return [resultnode]

def visit_configurationblock_html(self, node):
    self.body.append(self.starttag(node, 'div', CLASS='configuration-block'))

def depart_configurationblock_html(self, node):
    self.body.append('</div>\n')

def visit_configurationblock_latex(self, node):
    pass

def depart_configurationblock_latex(self, node):
    pass

def setup(app):
    app.add_node(configurationblock,
                 html=(visit_configurationblock_html, depart_configurationblock_html),
                 latex=(visit_configurationblock_latex, depart_configurationblock_latex))
    app.add_directive('configuration-block', ConfigurationBlock)

########NEW FILE########
__FILENAME__ = php
# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2010-2012 Fabien Potencier
    :license: MIT, see LICENSE for more details.
"""

from sphinx import addnodes
from sphinx.domains import Domain, ObjType
from sphinx.locale import l_, _
from sphinx.directives import ObjectDescription
from sphinx.domains.python import py_paramlist_re as js_paramlist_re
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode
from sphinx.util.docfields import Field, GroupedField, TypedField

def setup(app):
    app.add_domain(PHPDomain)

class PHPXRefRole(XRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        # basically what sphinx.domains.python.PyXRefRole does
        refnode['php:object'] = env.temp_data.get('php:object')
        if not has_explicit_title:
            title = title.lstrip('\\')
            target = target.lstrip('~')
            if title[0:1] == '~':
                title = title[1:]
                ns = title.rfind('\\')
                if ns != -1:
                    title = title[ns+1:]
        if target[0:1] == '\\':
            target = target[1:]
            refnode['refspecific'] = True
        return title, target

class PHPDomain(Domain):
    """PHP language domain."""
    name = 'php'
    label = 'PHP'
    # if you add a new object type make sure to edit JSObject.get_index_string
    object_types = {
    }
    directives = {
    }
    roles = {
        'func':  PHPXRefRole(fix_parens=True),
        'class': PHPXRefRole(),
        'data':  PHPXRefRole(),
        'attr':  PHPXRefRole(),
    }
    initial_data = {
        'objects': {}, # fullname -> docname, objtype
    }

    def clear_doc(self, docname):
        for fullname, (fn, _) in self.data['objects'].items():
            if fn == docname:
                del self.data['objects'][fullname]

    def find_obj(self, env, obj, name, typ, searchorder=0):
        if name[-2:] == '()':
            name = name[:-2]
        objects = self.data['objects']
        newname = None
        if searchorder == 1:
            if obj and obj + '\\' + name in objects:
                newname = obj + '\\' + name
            else:
                newname = name
        else:
            if name in objects:
                newname = name
            elif obj and obj + '\\' + name in objects:
                newname = obj + '\\' + name
        return newname, objects.get(newname)

    def resolve_xref(self, env, fromdocname, builder, typ, target, node,
                     contnode):
        objectname = node.get('php:object')
        searchorder = node.hasattr('refspecific') and 1 or 0
        name, obj = self.find_obj(env, objectname, target, typ, searchorder)
        if not obj:
            return None
        return make_refnode(builder, fromdocname, obj[0], name, contnode, name)

    def get_objects(self):
        for refname, (docname, type) in self.data['objects'].iteritems():
            yield refname, refname, type, docname, refname, 1

########NEW FILE########
__FILENAME__ = phpcode
# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2010-2012 Fabien Potencier
    :license: MIT, see LICENSE for more details.
"""

from docutils import nodes, utils

from sphinx.util.nodes import split_explicit_title
from string import lower

def php_namespace_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    env = inliner.document.settings.env
    base_url = env.app.config.api_url
    has_explicit_title, title, namespace = split_explicit_title(text)

    try:
        full_url = base_url % namespace.replace('\\', '/') + '.html'
    except (TypeError, ValueError):
        env.warn(env.docname, 'unable to expand %s api_url with base '
                 'URL %r, please make sure the base contains \'%%s\' '
                 'exactly once' % (typ, base_url))
        full_url = base_url + utils.escape(full_class)
    if not has_explicit_title:
        name = namespace.lstrip('\\')
        ns = name.rfind('\\')
        if ns != -1:
            name = name[ns+1:]
        title = name
    list = [nodes.reference(title, title, internal=False, refuri=full_url, reftitle=namespace)]
    pnode = nodes.literal('', '', *list)
    return [pnode], []

def php_class_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    env = inliner.document.settings.env
    base_url = env.app.config.api_url
    has_explicit_title, title, full_class = split_explicit_title(text)

    try:
        full_url = base_url % full_class.replace('\\', '/') + '.html'
    except (TypeError, ValueError):
        env.warn(env.docname, 'unable to expand %s api_url with base '
                 'URL %r, please make sure the base contains \'%%s\' '
                 'exactly once' % (typ, base_url))
        full_url = base_url + utils.escape(full_class)
    if not has_explicit_title:
        class_name = full_class.lstrip('\\')
        ns = class_name.rfind('\\')
        if ns != -1:
            class_name = class_name[ns+1:]
        title = class_name
    list = [nodes.reference(title, title, internal=False, refuri=full_url, reftitle=full_class)]
    pnode = nodes.literal('', '', *list)
    return [pnode], []

def php_method_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    env = inliner.document.settings.env
    base_url = env.app.config.api_url
    has_explicit_title, title, class_and_method = split_explicit_title(text)

    ns = class_and_method.rfind('::')
    full_class = class_and_method[:ns]
    method = class_and_method[ns+2:]

    try:
        full_url = base_url % full_class.replace('\\', '/') + '.html' + '#method_' + method
    except (TypeError, ValueError):
        env.warn(env.docname, 'unable to expand %s api_url with base '
                 'URL %r, please make sure the base contains \'%%s\' '
                 'exactly once' % (typ, base_url))
        full_url = base_url + utils.escape(full_class)
    if not has_explicit_title:
        title = method + '()'
    list = [nodes.reference(title, title, internal=False, refuri=full_url, reftitle=full_class + '::' + method + '()')]
    pnode = nodes.literal('', '', *list)
    return [pnode], []

def php_phpclass_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    has_explicit_title, title, full_class = split_explicit_title(text)

    full_url = 'http://php.net/manual/en/class.%s.php' % lower(full_class)

    if not has_explicit_title:
        title = full_class
    list = [nodes.reference(title, title, internal=False, refuri=full_url, reftitle=full_class)]
    pnode = nodes.literal('', '', *list)
    return [pnode], []

def php_phpmethod_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    has_explicit_title, title, class_and_method = split_explicit_title(text)

    ns = class_and_method.rfind('::')
    full_class = class_and_method[:ns]
    method = class_and_method[ns+2:]

    full_url = 'http://php.net/manual/en/%s.%s.php' % (lower(full_class), lower(method))

    if not has_explicit_title:
        title = full_class + '::' + method + '()'
    list = [nodes.reference(title, title, internal=False, refuri=full_url, reftitle=full_class)]
    pnode = nodes.literal('', '', *list)
    return [pnode], []

def php_phpfunction_role(typ, rawtext, text, lineno, inliner, options={}, content=[]):
    text = utils.unescape(text)
    has_explicit_title, title, full_function = split_explicit_title(text)

    full_url = 'http://php.net/manual/en/function.%s.php' % lower(full_function.replace('_', '-'))

    if not has_explicit_title:
        title = full_function
    list = [nodes.reference(title, title, internal=False, refuri=full_url, reftitle=full_function)]
    pnode = nodes.literal('', '', *list)
    return [pnode], []

def setup(app):
    app.add_config_value('api_url', {}, 'env')
    app.add_role('namespace', php_namespace_role)
    app.add_role('class', php_class_role)
    app.add_role('method', php_method_role)
    app.add_role('phpclass', php_phpclass_role)
    app.add_role('phpmethod', php_phpmethod_role)
    app.add_role('phpfunction', php_phpfunction_role)

########NEW FILE########
__FILENAME__ = refinclude
# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2010-2012 Fabien Potencier
    :license: MIT, see LICENSE for more details.
"""

from docutils.parsers.rst import Directive, directives
from docutils import nodes

class refinclude(nodes.General, nodes.Element):
    pass

class RefInclude(Directive):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}

    def run(self):
        document = self.state.document

        if not document.settings.file_insertion_enabled:
            return [document.reporter.warning('File insertion disabled',
                                              line=self.lineno)]

        env = self.state.document.settings.env
        target = self.arguments[0]

        node = refinclude()
        node['target'] = target

        return [node]

def process_refinclude_nodes(app, doctree, docname):
    env = app.env
    for node in doctree.traverse(refinclude):
        docname, labelid, sectname = env.domaindata['std']['labels'].get(node['target'],
                                                                         ('','',''))

        if not docname:
            return [document.reporter.error('Unknown target name: "%s"' % node['target'],
                                            line=self.lineno)]

        resultnode = None
        dt = env.get_doctree(docname)
        for n in dt.traverse(nodes.section):
            if labelid in n['ids']:
                node.replace_self([n])
                break

def setup(app):
    app.add_node(refinclude)
    app.add_directive('include-ref', RefInclude)
    app.connect('doctree-resolved', process_refinclude_nodes)

########NEW FILE########
