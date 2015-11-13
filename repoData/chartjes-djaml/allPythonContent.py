__FILENAME__ = loaders
import os

from django.template import TemplateDoesNotExist
from django.template.loaders import filesystem, app_directories

from hamlpy import hamlpy

from djaml.utils import get_django_template_loaders


def get_haml_loader(loader):
    if hasattr(loader, 'Loader'):
        baseclass = loader.Loader
    else:
        class baseclass(object):
            def load_template_source(self, *args, **kwargs):
                return loader.load_template_source(*args, **kwargs)

    class Loader(baseclass):
        def load_template_source(self, template_name, *args, **kwargs):
            _name, _extension = os.path.splitext(template_name)

            for extension in ["hamlpy", "haml"]:
                try:
                    haml_source, template_path = super(Loader, self).load_template_source(
                        self._generate_template_name(_name, extension), *args, **kwargs
                    )
                except TemplateDoesNotExist:
                    pass
                else:
                    hamlParser = hamlpy.Compiler()
                    html = hamlParser.process(haml_source)

                    return html, template_path

            raise TemplateDoesNotExist(template_name)

        load_template_source.is_usable = True

        def _generate_template_name(self, name, extension="hamlpy"):
            return "%s.%s" % (name, extension)

    return Loader


haml_loaders = dict((name, get_haml_loader(loader))
        for (name, loader) in get_django_template_loaders())


DjamlFilesystemLoader = get_haml_loader(filesystem)
DjamlAppDirectoriesLoader = get_haml_loader(app_directories)

########NEW FILE########
__FILENAME__ = djaml
"""
Template tags to render HAML strings with HamlPy.
"""

from django.template import Library
from django.utils.safestring import mark_safe
from hamlpy import hamlpy

register = Library()
hamlParser = hamlpy.Compiler()


@register.filter
def render_haml(source):
	"""
	.. function render_haml(source)

	Renders *source* string as HAML with HamlPy.
	"""
	return mark_safe(hamlParser.process(source))

########NEW FILE########
__FILENAME__ = utils
import imp
from os import listdir
from os.path import dirname, splitext

from django.template import loaders

MODULE_EXTENSIONS = tuple([suffix[0] for suffix in imp.get_suffixes()])


def get_django_template_loaders():
    return [(loader.__name__.rsplit('.', 1)[1], loader)
                for loader in get_submodules(loaders)
                if hasattr(loader, 'Loader')]


def get_submodules(package):
    submodules = ("%s.%s" % (package.__name__, module)
                for module in package_contents(package))
    return [__import__(module, {}, {}, [module.rsplit(".", 1)[-1]])
                for module in submodules]


def package_contents(package):
    package_path = dirname(loaders.__file__)
    return set([splitext(module)[0]
            for module in listdir(package_path)
            if module.endswith(MODULE_EXTENSIONS)])

########NEW FILE########
