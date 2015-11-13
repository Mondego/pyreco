__FILENAME__ = context_processors
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


from django.views.debug import get_safe_settings


class SafeSettings(object):
    """
        Map attributes to values in the safe settings dict
    """
    def __init__(self):
        self._settings = get_safe_settings()

    def __getattr__(self, name):
        try:
            return self._settings[name.upper()]
        except KeyError:
            raise AttributeError


settings_obj = SafeSettings()


def settings(request):
    return {'settings': settings_obj}


########NEW FILE########
__FILENAME__ = decorators
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


import json
import types
from functools import wraps, partial

import django
from django.http import HttpResponse
from django.conf.urls import include, url as addurl
from django.shortcuts import render

from utils import HttpResponseException


__all__ = ["view", "routing"]


def render_if(self, render_to=None, condition=lambda: False):
    """
        Render this view instead of the previous

        This function meant to be bound as a method to any fonction decorated
        with func_name.render_if, func_name being a function you just
        defined before, and decorated with @view.

        @view(render_to='template')
        def my_view(request):
            ...
            return context

        @my_view.render_if(condition=lambda r: r. user.is_authenticated())
        def my_conditional_view(request, context):
            ...

        my_view will always be executed, and should return a dictionary. if
        the user is authenticated, my_conditional_view is called, get the
        dictionary as a context, and should return a dictionary. If not,
        the context returned from my_view will be used directly.

        In any case, the context is rendered to the render_to template.

    """
    def decorator(func):
        self.conditional_calls.append((condition, func, render_to))
        return func
    return decorator

# Thers
render_if_ajax = partial(render_if, condition=lambda r, *a, **k: r.is_ajax())
render_if_get = partial(render_if, condition=lambda r, *a, **k: r.method == 'GET')
render_if_post = partial(render_if, condition=lambda r, *a, **k: r.method == 'POST')


def view(render_to=None, *args, **kwargs):
    """
        Decorate a view to allow it to return only a dictionary and be rendered
        to either a template or json.

        @view(render_to="template"):
        def my_view(request):
            ...
            return {....}

        The returned dict will be used as a context, and rendered with
        the given template and RequestContext as an instance.

        @view(render_to="json"):
        def my_view(request):
            ...
            return {....}

        The returned dict will be used as a context, and rendered as json.

        The view will also gain new attributes that you can use as
        decorators to declare alternative function to execute after the view:

        @view(render_to='user.html'):
        def user_view(request, id)
            ...
            return {'users': users}


        @user_view.ajax(render_to='json')
        def ajax_user_view(request, id, context):
            ...
            return context

        ajax_user_view will be called only if it's an ajax request. It will
        be passed the result of user_view as a context, and it should return
        a dictionary which will be rendered as json.
    """

    decorator_args = args
    decorator_kwargs = kwargs

    def decorator(func):

        func.conditional_calls = []

        func.ajax = types.MethodType(render_if_ajax, func)
        func.get = types.MethodType(render_if_get, func)
        func.post = types.MethodType(render_if_post, func)
        func.render_if = types.MethodType(render_if, func)

        @wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                for test, view, rendering in func.conditional_calls:
                    if test(request, *args, **kwargs):
                        response = view(request,
                                         context=func(request, *args, **kwargs),
                                        *args, **kwargs)
                        break

                else:
                    response, rendering = func(request, *args, **kwargs), render_to

                rendering = rendering or render_to

                if rendering and not isinstance(response, HttpResponse):

                    if rendering == 'json':
                        return HttpResponse(json.dumps(response),
                                            mimetype="application/json",
                                            *decorator_args, **decorator_kwargs)
                    if rendering == 'raw':
                        return HttpResponse(response,
                                            *decorator_args, **decorator_kwargs)

                    return render(request, rendering, response,
                                  *decorator_args, **decorator_kwargs)


                return response
            except HttpResponseException as e:
                return e

        return wrapper

    return decorator


def routing(root=""):
    """
        Return a url patterns list that Django can use for routing, and
        a url decorator that adds any view as a route to this list.


        url, urlpatterns = routing()

        @url(r'/home/')
        def view(request):
            ...

        @url(r'/thing/(?P<pk>\d+)/$', name="thingy")
        def other_view(request, pk):
            ...

    """

    urlpatterns = UrlList()

    def url(regex, kwargs=None, name=None, prefix=''):

        def decorator(func):

            urlpatterns.append(
                addurl(regex, func, kwargs, name or func.__name__, prefix),
            )

            return func

        return decorator

    def http403(func):
        django.conf.urls.handler403 = func
        return func
    url.http403 = http403

    def http404(func):
        django.conf.urls.handler404 = func
        return func
    url.http404 = http404

    def http405(func):
        django.conf.urls.handler405 = func
        return func
    url.http405 = http405

    return url, urlpatterns


class UrlList(list):
    """
        Sublass list to allow shortcuts to add urls to this pattern.
    """

    admin_added = False


    def add_url(self, regex, func, kwargs=None, name="", prefix=""):
        self.append(addurl(regex, func, kwargs, name, prefix))


    def include(self, regex, module, name="", prefix=""):
        self.add_url(regex, include(module), name=name, prefix=prefix)


    def add_admin(self, url):

        from django.contrib import admin

        if not UrlList.admin_added:
            admin.autodiscover()

        self.include(url, admin.site.urls, 'admin')

        UrlList.admin_added = True

########NEW FILE########
__FILENAME__ = fields
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


"""
    Part of the code is borrowed from django-annoying.

    https://bitbucket.org/offline/django-annoying/wiki/Home
"""

from django.db import models

from django.db.models import OneToOneField
from django.db.models.fields.related import SingleRelatedObjectDescriptor

try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    add_introspection_rules = lambda x: x


class AutoSingleRelatedObjectDescriptor(SingleRelatedObjectDescriptor):
    def __get__(self, instance, instance_type=None):
        try:
            return super(AutoSingleRelatedObjectDescriptor, self).__get__(instance, instance_type)
        except self.related.model.DoesNotExist:
            obj = self.related.model(**{self.related.field.name: instance})
            obj.save()
            return obj


class AutoOneToOneField(OneToOneField):
    '''
        OneToOneField creates related object on first call if it doesnt exists yet.
        Use it instead of original OneToOne field.

        example:
        class MyProfile(models.Model):
        user = AutoOneToOneField(User, primary_key=True)
        home_page = models.URLField(max_length=255)
        icq = models.CharField(max_length=255)
    '''
    def contribute_to_related_class(self, cls, related):
        setattr(cls, related.get_accessor_name(), AutoSingleRelatedObjectDescriptor(related))



class IntegerRangeField(models.IntegerField):

    """
        Equvalent of the django Integer Field but with min and max value.
    """

    def __init__(self, verbose_name=None, name=None,
                 min_value=None, max_value=None, **kwargs):
        self.min_value, self.max_value = min_value, max_value
        models.IntegerField.__init__(self, verbose_name, name, **kwargs)


    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value':self.max_value}
        defaults.update(kwargs)
        return super(IntegerRangeField, self).formfield(**defaults)



# if South is installed, provide introspection rules for it's migration
# see: http://south.aeracode.org/docs/tutorial/part4.html#tutorial-part-4
add_introspection_rules([
    (
        [IntegerRangeField],
        [],
        {
            "min_value": ["min_value", {"default": None}],
            "max_value": ["max_value", {"default": None}],
        },
    ),
], ["^libs\.models\.IntegerRangeField"])

########NEW FILE########
__FILENAME__ = clear_sessions
#!/usr/bin/env python
# -*- coding= UTF-8 -*-

"""
    Delete all sessions
"""

from optparse import make_option

from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session


class Command(BaseCommand):

    help = 'Delete all sessions from the server'

    option_list = BaseCommand.option_list + (

        make_option('--no-confirm',
            action='store_true',
            dest='no_confirm',
            default=False,
            help=u"Don't ask for confirmation"),

    )

    def handle(self, *args, **options):

        total = Session.objects.all().count()

        if not options['no_confirm']:
            confirm = raw_input('This will delete all %s sessions. Are you sure ? [y/N]\n' % total)
            if confirm.lower() not in ('y', 'yes'):
                return

        Session.objects.all().delete()
        print '%s sessions deleted' % total

########NEW FILE########
__FILENAME__ = middleware
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import re
import random

from django.conf import settings
from django.views.static import serve
from django.contrib.staticfiles.views import serve as serve_static
from django.shortcuts import redirect, render

from django.contrib.auth.models import User

from namegen.namegen import NameGenerator

from utils import setting


class ForceSuperUserMiddleWare(object):
    """
        Developpement middleware forcing login with a super user so you
        don't have to login or worry about access rights.
    """

    def process_request(self, request):

        request.user = User.objects.filter(is_superuser=True)[0]


class StaticServe(object):
    """
        Django middleware for serving static files instead of using urls.py.

        It serves them wether you are set DEBUG or not, so put it into
        a separate settings file to activate it at will.
    """

    # STATIC_URL must be defined at least
    static_url = settings.STATIC_URL.rstrip('/')

    # try to get MEDIA_URL
    media_url = setting('MEDIA_URL', '').rstrip('/')

    # try to get MEDIA_URL
    admin_url = setting('ADMIN_MEDIA_PREFIX', '').rstrip('/')

    media_regex = re.compile(r'^%s/(?P<path>.*)$' % media_url)
    static_regex = re.compile(r'^%s/(?P<path>.*)$' % static_url)
    admin_regex = re.compile(r'^%s/(?P<path>.*)$' % admin_url)

    # IF not MEDIA_ROOT is defined, we supposed it's the same as the
    # STATIC_ROOT
    MEDIA_ROOT = setting('MEDIA_ROOT') or setting('STATIC_ROOT')
    ADMIN_ROOT = setting('ADMIN_MEDIA_PREFIX') or setting('STATIC_ROOT')


    def process_request(self, request):

        protocol = 'http' + ('', 's')[request.is_secure()]
        host = request.META.get('HTTP_HOST', setting(
            'DJANGO_QUICKY_DEFAULT_HOST', 'django_quicky_fake_host'))
        prefix = protocol + '://' + host
        abspath = prefix + request.path

        if self.media_url:
            path = abspath if prefix in self.media_url else request.path
            match = self.media_regex.search(path)
            if match:
                return serve(request, match.group(1), self.MEDIA_ROOT)

        if self.admin_url:
            path = abspath if prefix in self.admin_url else request.path
            match = self.admin_regex.search(path)
            if match:
                return serve(request, match.group(1), self.ADMIN_ROOT)

        path = abspath if prefix in self.static_url else request.path
        match = self.static_regex.search(path)
        if match:
            return serve_static(request, match.group(1), insecure=True)


class AutoLogNewUser(object):


    CALLBACK = setting('AUTOLOGNEWUSER_CALLBAK', None)


    def process_request(self, request):


        if 'django-quicky-test-cookie' in request.path:

            if not request.session.test_cookie_worked():
                return render(request, 'django_quicky/no_cookies.html',
                              {'next': request.GET.get('next', '/')})

            request.session.delete_test_cookie()

            first_name = iter(NameGenerator()).next().title()
            username = "%s%s" % (first_name, random.randint(10, 100))
            user = User.objects.create(username=username,
                                       first_name=first_name)
            request.session['django-quicky:user_id'] = user.pk
            next = request.GET.get('next', '/')
            if self.CALLBACK:
                res = self.CALLBACK(request)
            return redirect(res or next)

        if not request.user.is_authenticated():

            user_id = request.session.get('django-quicky:user_id', None)

            if not user_id:

                request.session.set_test_cookie()
                return redirect('/django-quicky-test-cookie/?next=%s' % request.path)

            request.user = User.objects.get(pk=user_id)



########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

import types

from random import randint


__all__ = ['get_random_objects', 'get_object_or_none', 'patch_model']



def get_random_objects(model=None, queryset=None, count=float('+inf')):
    """
       Get `count` random objects for a model object `model` or from
       a queryset. Returns an iterator that yield one object at a time.

       You model must have an auto increment id for it to work and it should
       be available on the `id` attribute.
    """
    from django.db.models import Max
    if not queryset:
        try:
            queryset = model.objects.all()
        except AttributeError:
            raise ValueError("You must provide a model or a queryset")

    max_ = queryset.aggregate(Max('id'))['id__max']
    i = 0
    while i < count:
        try:
            yield queryset.get(pk=randint(1, max_))
            i += 1
        except queryset.model.DoesNotExist:
            pass


def get_object_or_none(klass, *args, **kwargs):
    """
        Uses get() to return an object or None if the object does not exist.

        klass may be a Model, Manager, or QuerySet object. All other passed
        arguments and keyword arguments are used in the get() query.
    """

    from django.shortcuts import _get_queryset
    queryset = _get_queryset(klass)
    try:
        return queryset.get(*args, **kwargs)
    except queryset.model.DoesNotExist:
        return None



def patch_model(model_to_patch, class_to_patch_with):
    """
        Adapted from https://gist.github.com/1402045

        Monkey patch a django model with additional or
        replacement fields and methods.

            - All fields and methods that didn't exist previously are added.

            - Existing methods with the same names are renamed with
              <methodname>__overridden, so there are still accessible,
              then the new ones are added.

            - Existing fields with the same name are deleted and replaced with
              the new fields.

        The class used to patch the model MUST be an old-style class (so
        this may not work with Python 3).

        Example (in your models.py):

            from django.contrib.auth.models import User
            from django_quicky.models import patch_model

            class UserOverride: # we don't need to inherit from anything
                email = models.EmailField(_('e-mail address'), unique=True)
                new_field = models.CharField(_('new field'), max_length=10)

                def save(self, *args, **kwargs):

                    # Call original save() method
                    self.save__overridden(*args, **kwargs)

                    # More custom save

            patch_model(User, UserOverride)

    """
    from django.db.models.fields import Field

    # The _meta attribute is where the definition of the fields is stored in
    # django model classes.
    patched_meta = getattr(model_to_patch, '_meta')
    field_lists = (patched_meta.local_fields, patched_meta.local_many_to_many)

    for name, obj in class_to_patch_with.__dict__.iteritems():

        # If the attribute is a field, delete any field with the same name.
        if isinstance(obj, Field):

            for field_list in field_lists:

                match = ((i, f) for i, f in enumerate(field_list) if f.name == name)
                try:
                    i, field = match.next()
                    # The creation_counter is used by django to know in
                    # which order the database columns are declared. We
                    # get it to ensure that when we override a field it
                    # will be declared in the same position as before.
                    obj.creation_counter = field.creation_counter
                    field_list.pop(i)
                finally:
                    break

        # Add "__overridden" to method names if they already exist.
        elif isinstance(obj, (types.FunctionType, property,
                               staticmethod, classmethod)):

            # rename the potential old method
            attr = getattr(model_to_patch, name, None)
            if attr:
                setattr(model_to_patch, name + '__overridden', attr)

            # bind the new method to the object
            if isinstance(obj, types.FunctionType):
                obj = types.UnboundMethodType(obj, None, model_to_patch)

        # Add the new field/method name and object to the model.
        model_to_patch.add_to_class(name, obj)

########NEW FILE########
__FILENAME__ = namegen
#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
    Generate random usernames in
"""

import random

from .names import names as default_names


class NameGenerator(object):

    def __init__(self, names=None):
        self.names = names or default_names


    def __call__(self):
        return self.names.pop(random.randrange(len(self.names)))

    def __iter__(self):
        while self.names:
            yield self()

########NEW FILE########
__FILENAME__ = names
names = """\
aaron
abdul
abe
abel
abraham
abram
adalberto
adam
adan
adolfo
adolph
adrian
agustin
ahmad
ahmed
al
alan
albert
alberto
alden
aldo
alec
alejandro
alex
alexander
alexis
alfonso
alfonzo
alfred
alfredo
ali
allan
allen
alonso
alonzo
alphonse
alphonso
alton
alva
alvaro
alvin
amado
ambrose
amos
anderson
andre
andrea
andreas
andres
andrew
andy
angel
angelo
anibal
anthony
antione
antoine
anton
antone
antonia
antonio
antony
antwan
archie
arden
ariel
arlen
arlie
armand
armando
arnold
arnoldo
arnulfo
aron
arron
art
arthur
arturo
asa
ashley
aubrey
august
augustine
augustus
aurelio
austin
avery
barney
barrett
barry
bart
barton
basil
beau
ben
benedict
benito
benjamin
bennett
bennie
benny
benton
bernard
bernardo
bernie
berry
bert
bertram
bill
billie
billy
blaine
blair
blake
bo
bob
bobbie
bobby
booker
boris
boyce
boyd
brad
bradford
bradley
bradly
brady
brain
branden
brandon
brant
brendan
brendon
brent
brenton
bret
brett
brian
brice
britt
brock
broderick
brooks
bruce
bruno
bryan
bryant
bryce
bryon
buck
bud
buddy
buford
burl
burt
burton
buster
byron
caleb
calvin
cameron
carey
carl
carlo
carlos
carlton
carmelo
carmen
carmine
carol
carrol
carroll
carson
carter
cary
casey
cecil
cedric
cedrick
cesar
chad
chadwick
chance
chang
charles
charley
charlie
chas
chase
chauncey
chester
chet
chi
chong
chris
christian
christoper
christopher
chuck
chung
clair
clarence
clark
claud
claude
claudio
clay
clayton
clement
clemente
cleo
cletus
cleveland
cliff
clifford
clifton
clint
clinton
clyde
cody
colby
cole
coleman
colin
collin
colton
columbus
connie
conrad
cordell
corey
cornelius
cornell
cortez
cory
courtney
coy
craig
cristobal
cristopher
cruz
curt
curtis
cyril
cyrus
dale
dallas
dalton
damian
damien
damion
damon
dan
dana
dane
danial
daniel
danilo
dannie
danny
dante
darell
daren
darin
dario
darius
darnell
daron
darrel
darrell
darren
darrick
darrin
darron
darryl
darwin
daryl
dave
david
davis
dean
deandre
deangelo
dee
del
delbert
delmar
delmer
demarcus
demetrius
denis
dennis
denny
denver
deon
derek
derick
derrick
deshawn
desmond
devin
devon
dewayne
dewey
dewitt
dexter
dick
diego
dillon
dino
dion
dirk
domenic
domingo
dominic
dominick
dominique
don
donald
dong
donn
donnell
donnie
donny
donovan
donte
dorian
dorsey
doug
douglas
douglass
doyle
drew
duane
dudley
duncan
dustin
dusty
dwain
dwayne
dwight
dylan
earl
earle
earnest
ed
eddie
eddy
edgar
edgardo
edison
edmond
edmund
edmundo
eduardo
edward
edwardo
edwin
efrain
efren
elbert
elden
eldon
eldridge
eli
elias
elijah
eliseo
elisha
elliot
elliott
ellis
ellsworth
elmer
elmo
eloy
elroy
elton
elvin
elvis
elwood
emanuel
emerson
emery
emil
emile
emilio
emmanuel
emmett
emmitt
emory
enoch
enrique
erasmo
eric
erich
erick
erik
erin
ernest
ernesto
ernie
errol
ervin
erwin
esteban
ethan
eugene
eugenio
eusebio
evan
everett
everette
ezekiel
ezequiel
ezra
fabian
faustino
fausto
federico
felipe
felix
felton
ferdinand
fermin
fernando
fidel
filiberto
fletcher
florencio
florentino
floyd
forest
forrest
foster
frances
francesco
francis
francisco
frank
frankie
franklin
franklyn
fred
freddie
freddy
frederic
frederick
fredric
fredrick
freeman
fritz
gabriel
gail
gale
galen
garfield
garland
garret
garrett
garry
garth
gary
gaston
gavin
gayle
gaylord
genaro
gene
geoffrey
george
gerald
geraldo
gerard
gerardo
german
gerry
gil
gilbert
gilberto
gino
giovanni
giuseppe
glen
glenn
gonzalo
gordon
grady
graham
graig
grant
granville
greg
gregg
gregorio
gregory
grover
guadalupe
guillermo
gus
gustavo
guy
hai
hal
hank
hans
harlan
harland
harley
harold
harris
harrison
harry
harvey
hassan
hayden
haywood
heath
hector
henry
herb
herbert
heriberto
herman
herschel
hershel
hilario
hilton
hipolito
hiram
hobert
hollis
homer
hong
horace
horacio
hosea
houston
howard
hoyt
hubert
huey
hugh
hugo
humberto
hung
hunter
hyman
ian
ignacio
ike
ira
irvin
irving
irwin
isaac
isaiah
isaias
isiah
isidro
ismael
israel
isreal
issac
ivan
ivory
jacinto
jack
jackie
jackson
jacob
jacques
jae
jaime
jake
jamaal
jamal
jamar
jame
jamel
james
jamey
jamie
jamison
jan
jared
jarod
jarred
jarrett
jarrod
jarvis
jason
jasper
javier
jay
jayson
jc
jean
jed
jeff
jefferey
jefferson
jeffery
jeffrey
jeffry
jerald
jeramy
jere
jeremiah
jeremy
jermaine
jerold
jerome
jerrell
jerrod
jerrold
jerry
jess
jesse
jessie
jesus
jewel
jewell
jim
jimmie
jimmy
joan
joaquin
jody
joe
joel
joesph
joey
john
johnathan
johnathon
johnie
johnnie
johnny
johnson
jon
jonah
jonas
jonathan
jonathon
jordan
jordon
jorge
jose
josef
joseph
josh
joshua
josiah
jospeh
josue
juan
jude
judson
jules
julian
julio
julius
junior
justin
kareem
karl
kasey
keenan
keith
kelley
kelly
kelvin
ken
kendall
kendrick
keneth
kenneth
kennith
kenny
kent
kenton
kermit
kerry
keven
kevin
kieth
kim
king
kip
kirby
kirk
korey
kory
kraig
kris
kristofer
kristopher
kurt
kurtis
kyle
lacy
lamar
lamont
lance
landon
lane
lanny
larry
lauren
laurence
lavern
laverne
lawerence
lawrence
lazaro
leandro
lee
leif
leigh
leland
lemuel
len
lenard
lenny
leo
leon
leonard
leonardo
leonel
leopoldo
leroy
les
lesley
leslie
lester
levi
lewis
lincoln
lindsay
lindsey
lino
linwood
lionel
lloyd
logan
lon
long
lonnie
lonny
loren
lorenzo
lou
louie
louis
lowell
loyd
lucas
luciano
lucien
lucio
lucius
luigi
luis
luke
lupe
luther
lyle
lyman
lyndon
lynn
lynwood
mac
mack
major
malcolm
malcom
malik
man
manual
manuel
marc
marcel
marcelino
marcellus
marcelo
marco
marcos
marcus
margarito
maria
mariano
mario
marion
mark
markus
marlin
marlon
marquis
marshall
martin
marty
marvin
mary
mason
mathew
matt
matthew
maurice
mauricio
mauro
max
maximo
maxwell
maynard
mckinley
mel
melvin
merle
merlin
merrill
mervin
micah
michael
michal
michale
micheal
michel
mickey
miguel
mike
mikel
milan
miles
milford
millard
milo
milton
minh
miquel
mitch
mitchel
mitchell
modesto
mohamed
mohammad
mohammed
moises
monroe
monte
monty
morgan
morris
morton
mose
moses
moshe
murray
myles
myron
napoleon
nathan
nathanael
nathanial
nathaniel
neal
ned
neil
nelson
nestor
neville
newton
nicholas
nick
nickolas
nicky
nicolas
nigel
noah
noble
noe
noel
nolan
norbert
norberto
norman
normand
norris
numbers
octavio
odell
odis
olen
olin
oliver
ollie
omar
omer
oren
orlando
orval
orville
oscar
osvaldo
oswaldo
otha
otis
otto
owen
pablo
palmer
paris
parker
pasquale
pat
patricia
patrick
paul
pedro
percy
perry
pete
peter
phil
philip
phillip
pierre
porfirio
porter
preston
prince
quentin
quincy
quinn
quintin
quinton
rafael
raleigh
ralph
ramiro
ramon
randal
randall
randell
randolph
randy
raphael
rashad
raul
ray
rayford
raymon
raymond
raymundo
reed
refugio
reggie
reginald
reid
reinaldo
renaldo
renato
rene
reuben
rex
rey
reyes
reynaldo
rhett
ricardo
rich
richard
richie
rick
rickey
rickie
ricky
rico
rigoberto
riley
rob
robbie
robby
robert
roberto
robin
robt
rocco
rocky
rod
roderick
rodger
rodney
rodolfo
rodrick
rodrigo
rogelio
roger
roland
rolando
rolf
rolland
roman
romeo
ron
ronald
ronnie
ronny
roosevelt
rory
rosario
roscoe
rosendo
ross
roy
royal
royce
ruben
rubin
rudolf
rudolph
rudy
rueben
rufus
rupert
russ
russel
russell
rusty
ryan
sal
salvador
salvatore
sam
sammie
sammy
samual
samuel
sandy
sanford
sang
santiago
santo
santos
saul
scot
scott
scottie
scotty
sean
sebastian
sergio
seth
seymour
shad
shane
shannon
shaun
shawn
shayne
shelby
sheldon
shelton
sherman
sherwood
shirley
shon
sid
sidney
silas
simon
sol
solomon
son
sonny
spencer
stacey
stacy
stan
stanford
stanley
stanton
stefan
stephan
stephen
sterling
steve
steven
stevie
stewart
stuart
sung
sydney
sylvester
tad
tanner
taylor
ted
teddy
teodoro
terence
terrance
terrell
terrence
terry
thad
thaddeus
thanh
theo
theodore
theron
thomas
thurman
tim
timmy
timothy
titus
tobias
toby
tod
todd
tom
tomas
tommie
tommy
toney
tony
tory
tracey
tracy
travis
trent
trenton
trevor
trey
trinidad
tristan
troy
truman
tuan
ty
tyler
tyree
tyrell
tyron
tyrone
tyson
ulysses
val
valentin
valentine
van
vance
vaughn
vern
vernon
vicente
victor
vince
vincent
vincenzo
virgil
virgilio
vito
von
wade
waldo
walker
wallace
wally
walter
walton
ward
warner
warren
waylon
wayne
weldon
wendell
werner
wes
wesley
weston
whitney
wilber
wilbert
wilbur
wilburn
wiley
wilford
wilfred
wilfredo
will
willard
william
williams
willian
willie
willis
willy
wilmer
wilson
wilton
winford
winfred
winston
wm
woodrow
wyatt
xavier
yong
young
zachariah
zachary
zachery
zack
zackary
zane
aaron
abbey
abbie
abby
abigail
ada
adah
adaline
adam
addie
adela
adelaida
adelaide
adele
adelia
adelina
adeline
adell
adella
adelle
adena
adina
adria
adrian
adriana
adriane
adrianna
adrianne
adrien
adriene
adrienne
afton
agatha
agnes
agnus
agripina
agueda
agustina
ai
aida
aide
aiko
aileen
ailene
aimee
aisha
aja
akiko
akilah
alaina
alaine
alana
alane
alanna
alayna
alba
albert
alberta
albertha
albertina
albertine
albina
alda
alease
alecia
aleen
aleida
aleisha
alejandra
alejandrina
alena
alene
alesha
aleshia
alesia
alessandra
aleta
aletha
alethea
alethia
alex
alexa
alexander
alexandra
alexandria
alexia
alexis
alfreda
alfredia
ali
alia
alica
alice
alicia
alida
alina
aline
alisa
alise
alisha
alishia
alisia
alison
alissa
alita
alix
aliza
alla
alleen
allegra
allen
allena
allene
allie
alline
allison
allyn
allyson
alma
almeda
almeta
alona
alpha
alta
altagracia
altha
althea
alva
alvera
alverta
alvina
alyce
alycia
alysa
alyse
alysha
alysia
alyson
alyssa
amada
amal
amalia
amanda
amber
amberly
amee
amelia
america
ami
amie
amiee
amina
amira
ammie
amparo
amy
an
ana
anabel
analisa
anamaria
anastacia
anastasia
andera
andra
andre
andrea
andree
andrew
andria
anette
angel
angela
angele
angelena
angeles
angelia
angelic
angelica
angelika
angelina
angeline
angelique
angelita
angella
angelo
angelyn
angie
angila
angla
angle
anglea
anh
anika
anisa
anisha
anissa
anita
anitra
anja
anjanette
anjelica
ann
anna
annabel
annabell
annabelle
annalee
annalisa
annamae
annamaria
annamarie
anne
anneliese
annelle
annemarie
annett
annetta
annette
annice
annie
annika
annis
annita
annmarie
anthony
antionette
antoinette
antonetta
antonette
antonia
antonietta
antonina
antonio
anya
apolonia
april
apryl
ara
araceli
aracelis
aracely
arcelia
ardath
ardelia
ardell
ardella
ardelle
ardis
ardith
aretha
argelia
argentina
ariana
ariane
arianna
arianne
arica
arie
ariel
arielle
arla
arlean
arleen
arlena
arlene
arletha
arletta
arlette
arlinda
arline
arlyne
armanda
armandina
armida
arminda
arnetta
arnette
arnita
arthur
artie
arvilla
asha
ashanti
ashely
ashlea
ashlee
ashleigh
ashley
ashli
ashlie
ashly
ashlyn
ashton
asia
asley
assunta
astrid
asuncion
athena
aubrey
audie
audra
audrea
audrey
audria
audrie
audry
augusta
augustina
augustine
aundrea
aura
aurea
aurelia
aurora
aurore
austin
autumn
ava
avelina
avery
avis
avril
awilda
ayako
ayana
ayanna
ayesha
azalee
azucena
azzie
babara
babette
bailey
bambi
bao
barabara
barb
barbar
barbara
barbera
barbie
barbra
bari
barrie
basilia
bea
beata
beatrice
beatris
beatriz
beaulah
bebe
becki
beckie
becky
bee
belen
belia
belinda
belkis
bell
bella
belle
belva
benita
bennie
berenice
berna
bernadette
bernadine
bernarda
bernardina
bernardine
berneice
bernetta
bernice
bernie
berniece
bernita
berry
berta
bertha
bertie
beryl
bess
bessie
beth
bethanie
bethann
bethany
bethel
betsey
betsy
bette
bettie
bettina
betty
bettyann
bettye
beula
beulah
bev
beverlee
beverley
beverly
bianca
bibi
billi
billie
billy
billye
birdie
birgit
blair
blake
blanca
blanch
blanche
blondell
blossom
blythe
bobbi
bobbie
bobby
bobbye
bobette
bok
bong
bonita
bonnie
bonny
branda
brande
brandee
brandi
brandie
brandon
brandy
breana
breann
breanna
breanne
bree
brenda
brenna
brett
brian
briana
brianna
brianne
bridget
bridgett
bridgette
brigette
brigid
brigida
brigitte
brinda
britany
britney
britni
britt
britta
brittaney
brittani
brittanie
brittany
britteny
brittney
brittni
brittny
bronwyn
brook
brooke
bruna
brunilda
bryanna
brynn
buena
buffy
bula
bulah
bunny
burma
caitlin
caitlyn
calandra
calista
callie
camelia
camellia
cameron
cami
camie
camila
camilla
camille
cammie
cammy
candace
candance
candelaria
candi
candice
candida
candie
candis
candra
candy
candyce
caprice
cara
caren
carey
cari
caridad
carie
carin
carina
carisa
carissa
carita
carl
carla
carlee
carleen
carlena
carlene
carletta
carley
carli
carlie
carline
carlita
carlos
carlota
carlotta
carly
carlyn
carma
carman
carmel
carmela
carmelia
carmelina
carmelita
carmella
carmen
carmina
carmon
carol
carola
carolann
carole
carolee
carolin
carolina
caroline
caroll
carolyn
carolyne
carolynn
caron
caroyln
carri
carrie
carrol
carroll
carry
cary
caryl
carylon
caryn
casandra
casey
casie
casimira
cassandra
cassaundra
cassey
cassi
cassidy
cassie
cassondra
cassy
catalina
catarina
caterina
catharine
catherin
catherina
catherine
cathern
catheryn
cathey
cathi
cathie
cathleen
cathrine
cathryn
cathy
catina
catrice
catrina
cayla
cecelia
cecil
cecila
cecile
cecilia
cecille
cecily
celena
celesta
celeste
celestina
celestine
celia
celina
celinda
celine
celsa
ceola
chae
chan
chana
chanda
chandra
chanel
chanell
chanelle
chang
chantal
chantay
chante
chantel
chantell
chantelle
chara
charis
charise
charissa
charisse
charita
charity
charla
charleen
charlena
charlene
charles
charlesetta
charlette
charlie
charline
charlott
charlotte
charlsie
charlyn
charmain
charmaine
charolette
chasidy
chasity
chassidy
chastity
chau
chaya
chelsea
chelsey
chelsie
cher
chere
cheree
cherelle
cheri
cherie
cherilyn
cherise
cherish
cherly
cherlyn
cherri
cherrie
cherry
cherryl
chery
cheryl
cheryle
cheryll
cheyenne
chi
chia
chieko
chin
china
ching
chiquita
chloe
chong
chris
chrissy
christa
christal
christeen
christel
christen
christena
christene
christi
christia
christian
christiana
christiane
christie
christin
christina
christine
christinia
christopher
christy
chrystal
chu
chun
chung
ciara
cicely
ciera
cierra
cinda
cinderella
cindi
cindie
cindy
cinthia
cira
clair
claire
clara
clare
clarence
claretha
claretta
claribel
clarice
clarinda
clarine
claris
clarisa
clarissa
clarita
classie
claude
claudette
claudia
claudie
claudine
clelia
clemencia
clementina
clementine
clemmie
cleo
cleopatra
cleora
cleotilde
cleta
clora
clorinda
clotilde
clyde
codi
cody
colby
coleen
colene
coletta
colette
colleen
collen
collene
collette
concepcion
conception
concetta
concha
conchita
connie
constance
consuela
consuelo
contessa
cora
coral
coralee
coralie
corazon
cordelia
cordia
cordie
coreen
corene
coretta
corey
cori
corie
corina
corine
corinna
corinne
corliss
cornelia
corrie
corrin
corrina
corrine
corrinne
cortney
cory
courtney
creola
cris
criselda
crissy
crista
cristal
cristen
cristi
cristie
cristin
cristina
cristine
cristy
cruz
crysta
crystal
crystle
cuc
curtis
cyndi
cyndy
cynthia
cyrstal
cythia
dacia
dagmar
dagny
dahlia
daina
daine
daisey
daisy
dakota
dale
dalene
dalia
dalila
dallas
damaris
dan
dana
danae
danelle
danette
dani
dania
danica
daniel
daniela
daniele
daniell
daniella
danielle
danika
danille
danita
dann
danna
dannette
dannie
dannielle
danuta
danyel
danyell
danyelle
daphine
daphne
dara
darby
darcel
darcey
darci
darcie
darcy
daria
darla
darleen
darlena
darlene
darline
darnell
daryl
david
davida
davina
dawn
dawna
dawne
dayle
dayna
daysi
deadra
dean
deana
deandra
deandrea
deane
deann
deanna
deanne
deb
debbi
debbie
debbra
debby
debera
debi
debora
deborah
debra
debrah
debroah
dede
dedra
dee
deeann
deeanna
deedee
deedra
deena
deetta
deidra
deidre
deirdre
deja
delaine
delana
delcie
delena
delfina
delia
delicia
delila
delilah
delinda
delisa
dell
della
delma
delmy
delois
deloise
delora
deloras
delores
deloris
delorse
delpha
delphia
delphine
delsie
delta
demetra
demetria
demetrice
demetrius
dena
denae
deneen
denese
denice
denise
denisha
denisse
denita
denna
dennis
dennise
denny
denyse
deon
deonna
desirae
desire
desiree
despina
dessie
destiny
detra
devin
devon
devona
devora
devorah
dia
diamond
dian
diana
diane
diann
dianna
dianne
diedra
diedre
dierdre
digna
dimple
dina
dinah
dinorah
dion
dione
dionna
dionne
divina
dixie
dodie
dollie
dolly
dolores
doloris
domenica
dominga
dominica
dominique
dominque
domitila
domonique
dona
donald
donella
donetta
donette
dong
donita
donna
donnetta
donnette
donnie
donya
dora
dorathy
dorcas
doreatha
doreen
dorene
doretha
dorethea
doretta
dori
doria
dorian
dorie
dorinda
dorine
doris
dorla
dorotha
dorothea
dorothy
dorris
dortha
dorthea
dorthey
dorthy
dot
dottie
dotty
dovie
dreama
drema
drew
drucilla
drusilla
dulce
dulcie
dung
dusti
dusty
dwana
dyan
earlean
earleen
earlene
earlie
earline
earnestine
eartha
easter
eboni
ebonie
ebony
echo
eda
edda
eddie
edelmira
eden
edie
edith
edna
edra
edris
edward
edwina
edyth
edythe
effie
ehtel
eileen
eilene
ela
eladia
elaina
elaine
elana
elane
elanor
elayne
elba
elda
eldora
eleanor
eleanora
eleanore
elease
elena
elene
eleni
elenor
elenora
elenore
eleonor
eleonora
eleonore
elfreda
elfrieda
elfriede
elia
eliana
elicia
elida
elidia
elin
elina
elinor
elinore
elisa
elisabeth
elise
elisha
elissa
eliz
eliza
elizabet
elizabeth
elizbeth
elizebeth
elke
ella
ellamae
ellan
ellen
ellena
elli
ellie
ellis
elly
ellyn
elma
elmer
elmira
elna
elnora
elodia
elois
eloisa
eloise
elouise
elsa
else
elsie
elsy
elva
elvera
elvia
elvie
elvina
elvira
elwanda
elyse
elza
ema
emelda
emelia
emelina
emeline
emely
emerald
emerita
emiko
emilee
emilia
emilie
emily
emma
emmaline
emmie
emmy
emogene
ena
enda
enedina
eneida
enid
enola
enriqueta
epifania
era
eric
erica
ericka
erika
erin
erinn
erlene
erlinda
erline
erma
ermelinda
erminia
erna
ernestina
ernestine
eryn
esmeralda
esperanza
essie
esta
estefana
estela
estell
estella
estelle
ester
esther
estrella
etha
ethel
ethelene
ethelyn
ethyl
etsuko
etta
ettie
eufemia
eugena
eugene
eugenia
eugenie
eula
eulah
eulalia
eun
euna
eunice
eura
eusebia
eustolia
eva
evalyn
evan
evangelina
evangeline
eve
evelia
evelin
evelina
eveline
evelyn
evelyne
evelynn
evette
evia
evie
evita
evon
evonne
ewa
exie
fabiola
fae
fairy
faith
fallon
fannie
fanny
farah
farrah
fatima
fatimah
faustina
faviola
fawn
fay
faye
fe
felecia
felica
felice
felicia
felicidad
felicita
felicitas
felipa
felisa
felisha
fermina
fern
fernanda
fernande
ferne
fidela
fidelia
filomena
fiona
flavia
fleta
flo
flor
flora
florance
florence
florencia
florene
florentina
floretta
floria
florida
florinda
florine
florrie
flossie
floy
fonda
fran
france
francene
frances
francesca
franchesca
francie
francina
francine
francis
francisca
francisco
francoise
frank
frankie
fransisca
fred
freda
fredda
freddie
frederica
fredericka
fredia
fredricka
freeda
freida
frida
frieda
fumiko
gabriel
gabriela
gabriele
gabriella
gabrielle
gail
gala
gale
galina
garnet
garnett
gary
gay
gaye
gayla
gayle
gaylene
gaynell
gaynelle
gearldine
gema
gemma
gena
gene
genesis
geneva
genevie
genevieve
genevive
genia
genie
genna
gennie
genny
genoveva
georgann
george
georgeann
georgeanna
georgene
georgetta
georgette
georgia
georgiana
georgiann
georgianna
georgianne
georgie
georgina
georgine
gerald
geraldine
geralyn
gerda
geri
germaine
gerri
gerry
gertha
gertie
gertrud
gertrude
gertrudis
gertude
ghislaine
gia
gianna
gidget
gigi
gilberte
gilda
gillian
gilma
gina
ginette
ginger
ginny
giovanna
gisela
gisele
giselle
gita
giuseppina
gladis
glady
gladys
glayds
glenda
glendora
glenn
glenna
glennie
glennis
glinda
gloria
glory
glynda
glynis
golda
golden
goldie
grace
gracia
gracie
graciela
grayce
grazyna
gregoria
gregory
greta
gretchen
gretta
gricelda
grisel
griselda
guadalupe
gudrun
guillermina
gussie
gwen
gwenda
gwendolyn
gwenn
gwyn
gwyneth
ha
hae
hailey
haley
halina
halley
hallie
han
hana
hang
hanh
hanna
hannah
hannelore
harmony
harold
harriet
harriett
harriette
hassie
hattie
haydee
hayley
hazel
heather
hedwig
hedy
hee
heide
heidi
heidy
heike
helaine
helen
helena
helene
helga
hellen
henrietta
henriette
henry
herlinda
herma
hermelinda
hermila
hermina
hermine
herminia
herta
hertha
hester
hettie
hiedi
hien
hilaria
hilary
hilda
hilde
hildegard
hildegarde
hildred
hillary
hilma
hiroko
hisako
hoa
holley
holli
hollie
hollis
holly
honey
hong
hope
hortencia
hortense
hortensia
hsiu
hue
hui
hulda
huong
hwa
hyacinth
hye
hyo
hyon
hyun
ida
idalia
idell
idella
iesha
ignacia
ila
ilana
ilda
ileana
ileen
ilene
iliana
illa
ilona
ilse
iluminada
ima
imelda
imogene
in
ina
india
indira
inell
ines
inez
inga
inge
ingeborg
inger
ingrid
inocencia
iola
iona
ione
ira
iraida
irena
irene
irina
iris
irish
irma
irmgard
isa
isabel
isabell
isabella
isabelle
isadora
isaura
isela
isidra
isis
isobel
iva
ivana
ivelisse
ivette
ivey
ivonne
ivory
ivy
izetta
izola
ja
jacalyn
jacelyn
jacinda
jacinta
jack
jackeline
jackelyn
jacki
jackie
jacklyn
jackqueline
jaclyn
jacqualine
jacque
jacquelin
jacqueline
jacquelyn
jacquelyne
jacquelynn
jacquetta
jacqui
jacquie
jacquiline
jacquline
jacqulyn
jada
jade
jadwiga
jae
jaime
jaimee
jaimie
jaleesa
jalisa
jama
jame
jamee
james
jamey
jami
jamie
jamika
jamila
jammie
jan
jana
janae
janay
jane
janean
janee
janeen
janel
janell
janella
janelle
janene
janessa
janet
janeth
janett
janetta
janette
janey
jani
janice
janie
janiece
janina
janine
janis
janise
janita
jann
janna
jannet
jannette
jannie
january
janyce
jaqueline
jaquelyn
jasmin
jasmine
jason
jaunita
jay
jaye
jayme
jaymie
jayna
jayne
jazmin
jazmine
jean
jeana
jeane
jeanelle
jeanene
jeanett
jeanetta
jeanette
jeanice
jeanie
jeanine
jeanmarie
jeanna
jeanne
jeannetta
jeannette
jeannie
jeannine
jeffie
jeffrey
jen
jena
jenae
jene
jenee
jenell
jenelle
jenette
jeneva
jeni
jenice
jenifer
jeniffer
jenine
jenise
jenna
jennefer
jennell
jennette
jenni
jennie
jennifer
jenniffer
jennine
jenny
jeraldine
jeremy
jeri
jerica
jerilyn
jerlene
jerri
jerrica
jerrie
jerry
jesenia
jesica
jesse
jessenia
jessi
jessia
jessica
jessie
jessika
jestine
jesus
jesusa
jesusita
jetta
jettie
jewel
jewell
ji
jill
jillian
jimmie
jimmy
jin
jina
jinny
jo
joan
joana
joane
joanie
joann
joanna
joanne
joannie
joaquina
jocelyn
jodee
jodi
jodie
jody
joe
joeann
joel
joella
joelle
joellen
joetta
joette
joey
johana
johanna
johanne
john
johna
johnetta
johnette
johnie
johnna
johnnie
johnny
johnsie
joi
joie
jolanda
joleen
jolene
jolie
joline
jolyn
jolynn
jon
jona
jone
jonell
jonelle
jong
joni
jonie
jonna
jonnie
jordan
jose
josefa
josefina
josefine
joselyn
joseph
josephina
josephine
josette
joshua
josie
joslyn
josphine
jovan
jovita
joy
joya
joyce
joycelyn
joye
juan
juana
juanita
jude
judi
judie
judith
judy
jule
julee
julene
juli
julia
julian
juliana
juliane
juliann
julianna
julianne
julie
julieann
julienne
juliet
julieta
julietta
juliette
julio
julissa
june
jung
junie
junita
junko
justa
justin
justina
justine
jutta
ka
kacey
kaci
kacie
kacy
kai
kaila
kaitlin
kaitlyn
kala
kaleigh
kaley
kali
kallie
kalyn
kam
kamala
kami
kamilah
kandace
kandi
kandice
kandis
kandra
kandy
kanesha
kanisha
kara
karan
kareen
karen
karena
karey
kari
karie
karima
karin
karina
karine
karisa
karissa
karl
karla
karleen
karlene
karly
karlyn
karma
karmen
karol
karole
karoline
karolyn
karon
karren
karri
karrie
karry
kary
karyl
karyn
kasandra
kasey
kasha
kasi
kasie
kassandra
kassie
kate
katelin
katelyn
katelynn
katerine
kathaleen
katharina
katharine
katharyn
kathe
katheleen
katherin
katherina
katherine
kathern
katheryn
kathey
kathi
kathie
kathleen
kathlene
kathline
kathlyn
kathrin
kathrine
kathryn
kathryne
kathy
kathyrn
kati
katia
katie
katina
katlyn
katrice
katrina
kattie
katy
kay
kayce
kaycee
kaye
kayla
kaylee
kayleen
kayleigh
kaylene
kazuko
kecia
keeley
keely
keena
keesha
keiko
keila
keira
keisha
keith
keitha
keli
kelle
kellee
kelley
kelli
kellie
kelly
kellye
kelsey
kelsi
kelsie
kemberly
kena
kenda
kendal
kendall
kendra
kenia
kenisha
kenna
kenneth
kenya
kenyatta
kenyetta
kera
keren
keri
kerri
kerrie
kerry
kerstin
kesha
keshia
keturah
keva
kevin
khadijah
khalilah
kia
kiana
kiara
kiera
kiersten
kiesha
kiley
kim
kimber
kimberely
kimberlee
kimberley
kimberli
kimberlie
kimberly
kimbery
kimbra
kimi
kimiko
kina
kindra
kira
kirby
kirsten
kirstie
kirstin
kisha
kit
kittie
kitty
kiyoko
kizzie
kizzy
klara
kori
kortney
kourtney
kris
krishna
krissy
krista
kristal
kristan
kristeen
kristel
kristen
kristi
kristian
kristie
kristin
kristina
kristine
kristle
kristy
kristyn
krysta
krystal
krysten
krystin
krystina
krystle
krystyna
kum
kyla
kyle
kylee
kylie
kym
kymberly
kyoko
kyong
kyra
kyung
lacey
lachelle
laci
lacie
lacresha
lacy
ladawn
ladonna
lady
lael
lahoma
lai
laila
laine
lajuana
lakeesha
lakeisha
lakendra
lakenya
lakesha
lakeshia
lakia
lakiesha
lakisha
lakita
lala
lamonica
lan
lana
lane
lanell
lanelle
lanette
lang
lani
lanie
lanita
lannie
lanora
laquanda
laquita
lara
larae
laraine
laree
larhonda
larisa
larissa
larita
laronda
larraine
larry
larue
lasandra
lashanda
lashandra
lashaun
lashaunda
lashawn
lashawna
lashawnda
lashay
lashell
lashon
lashonda
lashunda
lasonya
latanya
latarsha
latasha
latashia
latesha
latia
laticia
latina
latisha
latonia
latonya
latoria
latosha
latoya
latoyia
latrice
latricia
latrina
latrisha
launa
laura
lauralee
lauran
laure
laureen
laurel
lauren
laurena
laurence
laurene
lauretta
laurette
lauri
laurice
laurie
laurinda
laurine
lauryn
lavada
lavelle
lavenia
lavera
lavern
laverna
laverne
laveta
lavette
lavina
lavinia
lavon
lavona
lavonda
lavone
lavonia
lavonna
lavonne
lawana
lawanda
lawanna
lawrence
layla
layne
le
lea
leah
lean
leana
leandra
leann
leanna
leanne
leanora
leatha
leatrice
lecia
leda
lee
leeann
leeanna
leeanne
leena
leesa
leia
leida
leigh
leigha
leighann
leila
leilani
leisa
leisha
lekisha
lela
lelah
lelia
lena
lenita
lenna
lennie
lenora
lenore
leo
leola
leoma
leon
leona
leonarda
leone
leonia
leonida
leonie
leonila
leonor
leonora
leonore
leontine
leora
leota
lera
lesa
lesha
lesia
leslee
lesley
lesli
leslie
lessie
lester
leta
letha
leticia
letisha
letitia
lettie
letty
lewis
lexie
lezlie
li
lia
liana
liane
lianne
libbie
libby
liberty
librada
lida
lidia
lien
lieselotte
ligia
lila
lili
lilia
lilian
liliana
lilla
lilli
lillia
lilliam
lillian
lilliana
lillie
lilly
lily
lin
lina
linda
lindsay
lindsey
lindsy
lindy
linette
ling
linh
linn
linnea
linnie
linsey
lisa
lisabeth
lisandra
lisbeth
lise
lisette
lisha
lissa
lissette
lita
livia
liz
liza
lizabeth
lizbeth
lizeth
lizette
lizzette
lizzie
loan
logan
loida
lois
loise
lola
lolita
loma
lona
londa
loni
lonna
lonnie
lora
loraine
loralee
lore
lorean
loree
loreen
lorelei
loren
lorena
lorene
lorenza
loreta
loretta
lorette
lori
loria
loriann
lorie
lorilee
lorina
lorinda
lorine
loris
lorita
lorna
lorraine
lorretta
lorri
lorriane
lorrie
lorrine
lory
lottie
lou
louann
louanne
louella
louetta
louie
louis
louisa
louise
loura
lourdes
lourie
louvenia
love
lovella
lovetta
lovie
loyce
lu
luana
luann
luanna
luanne
luba
luci
lucia
luciana
lucie
lucienne
lucila
lucile
lucilla
lucille
lucina
lucinda
lucrecia
lucretia
lucy
ludie
ludivina
lue
luella
luetta
luis
luisa
luise
lula
lulu
luna
lupe
lupita
lura
lurlene
lurline
luvenia
luz
lyda
lydia
lyla
lyn
lynda
lyndia
lyndsay
lyndsey
lynell
lynelle
lynetta
lynette
lynn
lynna
lynne
lynnette
lynsey
ma
mabel
mabelle
mable
machelle
macie
mackenzie
macy
madalene
madaline
madalyn
maddie
madelaine
madeleine
madelene
madeline
madelyn
madge
madie
madison
madlyn
madonna
mae
maegan
mafalda
magali
magaly
magan
magaret
magda
magdalen
magdalena
magdalene
magen
maggie
magnolia
mahalia
mai
maia
maida
maile
maira
maire
maisha
maisie
majorie
makeda
malena
malia
malika
malinda
malisa
malissa
malka
mallie
mallory
malorie
malvina
mamie
mammie
man
mana
manda
mandi
mandie
mandy
manie
manuela
many
mao
maple
mara
maragaret
maragret
maranda
marcela
marcelene
marcelina
marceline
marcell
marcella
marcelle
marcene
marchelle
marci
marcia
marcie
marcy
mardell
maren
marg
margaret
margareta
margarete
margarett
margaretta
margarette
margarita
margarite
margart
marge
margene
margeret
margert
margery
marget
margherita
margie
margit
margo
margorie
margot
margret
margrett
marguerita
marguerite
margurite
margy
marhta
mari
maria
mariah
mariam
marian
mariana
marianela
mariann
marianna
marianne
maribel
maribeth
marica
maricela
maricruz
marie
mariel
mariela
mariella
marielle
marietta
mariette
mariko
marilee
marilou
marilu
marilyn
marilynn
marin
marina
marinda
marine
mario
marion
maris
marisa
marisela
marisha
marisol
marissa
marita
maritza
marivel
marjorie
marjory
mark
marketta
markita
marla
marlana
marleen
marlen
marlena
marlene
marlin
marline
marlo
marlyn
marlys
marna
marni
marnie
marquerite
marquetta
marquita
marquitta
marry
marsha
marshall
marta
marth
martha
marti
martin
martina
martine
marty
marva
marvel
marvella
marvis
marx
mary
marya
maryalice
maryam
maryann
maryanna
maryanne
marybelle
marybeth
maryellen
maryetta
maryjane
maryjo
maryland
marylee
marylin
maryln
marylou
marylouise
marylyn
marylynn
maryrose
masako
matha
mathilda
mathilde
matilda
matilde
matthew
mattie
maud
maude
maudie
maura
maureen
maurice
maurine
maurita
mavis
maxie
maxima
maximina
maxine
may
maya
maybell
maybelle
maye
mayme
mayola
mayra
mazie
mckenzie
meagan
meaghan
mechelle
meda
mee
meg
megan
meggan
meghan
meghann
mei
melaine
melani
melania
melanie
melany
melba
melda
melia
melida
melina
melinda
melisa
melissa
melissia
melita
mellie
mellisa
mellissa
melodee
melodi
melodie
melody
melonie
melony
melva
melvin
melvina
melynda
mendy
mercedes
mercedez
mercy
meredith
meri
merideth
meridith
merilyn
merissa
merle
merlene
merlyn
merna
merri
merrie
merrilee
merrill
merry
mertie
meryl
meta
mi
mia
mica
micaela
micah
micha
michael
michaela
michaele
michal
micheal
michel
michele
michelina
micheline
michell
michelle
michiko
mickey
micki
mickie
miesha
migdalia
mignon
miguelina
mika
mikaela
mike
miki
mikki
mila
milagro
milagros
milda
mildred
milissa
millicent
millie
milly
mimi
min
mina
minda
mindi
mindy
minerva
ming
minh
minna
minnie
minta
mira
miranda
mireille
mirella
mireya
miriam
mirian
mirna
mirta
mirtha
misha
miss
missy
misti
mistie
misty
mitchell
mitsue
mitsuko
mittie
mitzi
mitzie
miyoko
modesta
moira
mollie
molly
mona
monet
monica
monika
monique
monnie
monserrate
moon
mora
morgan
moriah
mozell
mozella
mozelle
mui
muoi
muriel
my
myesha
myong
myra
myriam
myrl
myrle
myrna
myrta
myrtice
myrtie
myrtis
myrtle
myung
na
nada
nadene
nadia
nadine
naida
nakesha
nakia
nakisha
nakita
nam
nan
nana
nancee
nancey
nanci
nancie
nancy
nanette
nannette
nannie
naoma
naomi
narcisa
natacha
natalia
natalie
natalya
natasha
natashia
nathalie
natisha
natividad
natosha
necole
neda
nedra
neely
neida
nelda
nelia
nelida
nell
nella
nelle
nellie
nelly
nena
nenita
neoma
neomi
nereida
nerissa
nery
neta
nettie
neva
nevada
nga
ngan
ngoc
nguyet
nia
nichelle
nichol
nichole
nicholle
nicki
nickie
nickole
nicky
nicol
nicola
nicolasa
nicole
nicolette
nicolle
nida
nidia
niesha
nieves
niki
nikia
nikita
nikki
nikole
nila
nilda
nilsa
nina
ninfa
nisha
nita
nobuko
noel
noelia
noella
noelle
noemi
nohemi
nola
noma
nona
nora
norah
noreen
norene
noriko
norine
norma
norman
nova
novella
nu
nubia
numbers
nydia
nyla
obdulia
ocie
octavia
oda
odelia
odell
odessa
odette
odilia
ofelia
ok
ola
olene
oleta
olevia
olga
olimpia
olinda
oliva
olive
olivia
ollie
olympia
oma
omega
ona
oneida
onie
onita
opal
ophelia
ora
oralee
oralia
oretha
orpha
oscar
ossie
otelia
otha
otilia
ouida
ozell
ozella
ozie
pa
page
paige
palma
palmira
pam
pamala
pamela
pamelia
pamella
pamila
pamula
pandora
pansy
paola
paris
parthenia
particia
pasty
pat
patience
patria
patrica
patrice
patricia
patrick
patrina
patsy
patti
pattie
patty
paul
paula
paulene
pauletta
paulette
paulina
pauline
paulita
paz
pearl
pearle
pearlene
pearlie
pearline
pearly
peg
peggie
peggy
pei
penelope
penney
penni
pennie
penny
perla
perry
peter
petra
petrina
petronila
phebe
phillis
philomena
phoebe
phung
phuong
phylicia
phylis
phyliss
phyllis
pia
piedad
pilar
ping
pinkie
piper
pok
polly
porsche
porsha
portia
precious
pricilla
princess
priscila
priscilla
providencia
prudence
pura
qiana
queen
queenie
quiana
quinn
quyen
rachael
rachal
racheal
rachel
rachele
rachell
rachelle
racquel
rae
raeann
raelene
rafaela
raguel
raina
raisa
ramona
ramonita
rana
ranae
randa
randee
randi
randy
ranee
raquel
rasheeda
rashida
raven
ray
raye
raylene
raymond
raymonde
rayna
rea
reagan
reanna
reatha
reba
rebbeca
rebbecca
rebeca
rebecca
rebecka
rebekah
reda
reena
refugia
refugio
regan
regena
regenia
regina
regine
reginia
reiko
reina
reita
rema
remedios
remona
rena
renae
renata
renate
renay
renda
rene
renea
renee
renetta
renita
renna
ressie
reta
retha
retta
reva
reyna
reynalda
rhea
rheba
rhiannon
rhoda
rhona
rhonda
ria
ricarda
richard
richelle
ricki
rickie
rikki
rima
rina
risa
rita
riva
rivka
robbi
robbie
robbin
robbyn
robena
robert
roberta
roberto
robin
robyn
rochel
rochell
rochelle
rocio
rolanda
rolande
roma
romaine
romana
romelia
romona
rona
ronald
ronda
roni
ronna
ronni
ronnie
rory
rosa
rosalba
rosalee
rosalia
rosalie
rosalina
rosalind
rosalinda
rosaline
rosalva
rosalyn
rosamaria
rosamond
rosana
rosann
rosanna
rosanne
rosaria
rosario
rosaura
rose
roseann
roseanna
roseanne
roselee
roselia
roseline
rosella
roselle
roselyn
rosemarie
rosemary
rosena
rosenda
rosetta
rosette
rosia
rosie
rosina
rosio
rosita
roslyn
rossana
rossie
rosy
rowena
roxana
roxane
roxann
roxanna
roxanne
roxie
roxy
roy
royce
rozanne
rozella
rubi
rubie
ruby
rubye
rudy
rufina
russell
ruth
rutha
ruthann
ruthanne
ruthe
ruthie
ryan
ryann
sabina
sabine
sabra
sabrina
sacha
sachiko
sade
sadie
sadye
sage
salena
salina
salley
sallie
sally
salome
sam
samantha
samara
samatha
samella
samira
sammie
sammy
samuel
sana
sanda
sandee
sandi
sandie
sandra
sandy
sang
sanjuana
sanjuanita
sanora
santa
santana
santina
santos
sara
sarah
sarai
saran
sari
sarina
sarita
sasha
saturnina
sau
saundra
savanna
savannah
scarlet
scarlett
scott
scottie
sean
season
sebrina
see
seema
selena
selene
selina
selma
sena
senaida
september
serafina
serena
serina
serita
setsuko
sha
shae
shaina
shakia
shakira
shakita
shala
shalanda
shalon
shalonda
shameka
shamika
shan
shana
shanae
shanda
shandi
shandra
shane
shaneka
shanel
shanell
shanelle
shani
shanice
shanika
shaniqua
shanita
shanna
shannan
shannon
shanon
shanta
shantae
shantay
shante
shantel
shantell
shantelle
shanti
shaquana
shaquita
shara
sharan
sharda
sharee
sharell
sharen
shari
sharice
sharie
sharika
sharilyn
sharita
sharla
sharleen
sharlene
sharmaine
sharolyn
sharon
sharonda
sharri
sharron
sharyl
sharyn
shasta
shaun
shauna
shaunda
shaunna
shaunta
shaunte
shavon
shavonda
shavonne
shawana
shawanda
shawanna
shawn
shawna
shawnda
shawnee
shawnna
shawnta
shay
shayla
shayna
shayne
shea
sheba
sheena
sheila
sheilah
shela
shelba
shelby
shelia
shella
shelley
shelli
shellie
shelly
shemeka
shemika
shena
shenika
shenita
shenna
shera
sheree
sherell
sheri
sherice
sheridan
sherie
sherika
sherill
sherilyn
sherise
sherita
sherlene
sherley
sherly
sherlyn
sheron
sherrell
sherri
sherrie
sherril
sherrill
sherron
sherry
sherryl
shery
sheryl
sheryll
shiela
shila
shiloh
shin
shira
shirely
shirl
shirlee
shirleen
shirlene
shirley
shirly
shizue
shizuko
shona
shonda
shondra
shonna
shonta
shoshana
shu
shyla
sibyl
sidney
sierra
signe
sigrid
silva
silvana
silvia
sima
simona
simone
simonne
sina
sindy
siobhan
sirena
siu
sixta
skye
slyvia
so
socorro
sofia
soila
sol
solange
soledad
somer
sommer
son
sona
sondra
song
sonia
sonja
sonya
soo
sook
soon
sophia
sophie
soraya
sparkle
spring
stacee
stacey
staci
stacia
stacie
stacy
star
starla
starr
stasia
stefani
stefania
stefanie
stefany
steffanie
stella
stepanie
stephaine
stephane
stephani
stephania
stephanie
stephany
stephen
stephenie
stephine
stephnie
steven
stevie
stormy
su
suanne
sudie
sue
sueann
suellen
suk
sulema
sumiko
summer
sun
sunday
sung
sunni
sunny
sunshine
susan
susana
susann
susanna
susannah
susanne
susie
susy
suzan
suzann
suzanna
suzanne
suzette
suzi
suzie
suzy
svetlana
sybil
syble
sydney
sylvia
sylvie
synthia
syreeta
ta
tabatha
tabetha
tabitha
tai
taina
taisha
tajuana
takako
takisha
talia
talisha
talitha
tam
tama
tamala
tamar
tamara
tamatha
tambra
tameika
tameka
tamekia
tamela
tamera
tamesha
tami
tamica
tamie
tamika
tamiko
tamisha
tammara
tammera
tammi
tammie
tammy
tamra
tana
tandra
tandy
taneka
tanesha
tangela
tania
tanika
tanisha
tanja
tanna
tanya
tara
tarah
taren
tari
tarra
tarsha
taryn
tasha
tashia
tashina
tasia
tatiana
tatum
tatyana
taunya
tawana
tawanda
tawanna
tawna
tawny
tawnya
taylor
tayna
teena
tegan
teisha
telma
temeka
temika
tempie
temple
tena
tenesha
tenisha
tennie
tennille
teodora
teofila
tequila
tera
tereasa
teresa
terese
teresia
teresita
teressa
teri
terica
terina
terisa
terra
terrell
terresa
terri
terrie
terrilyn
terry
tesha
tess
tessa
tessie
thalia
thanh
thao
thea
theda
thelma
theo
theodora
theola
theresa
therese
theresia
theressa
thersa
thi
thomas
thomasena
thomasina
thomasine
thora
thresa
thu
thuy
tia
tiana
tianna
tiara
tien
tiera
tierra
tiesha
tifany
tiffaney
tiffani
tiffanie
tiffany
tiffiny
tijuana
tilda
tillie
timika
timothy
tina
tinisha
tiny
tisa
tish
tisha
tobi
tobie
toby
toccara
toi
tomasa
tomeka
tomi
tomika
tomiko
tommie
tommy
tommye
tomoko
tona
tonda
tonette
toni
tonia
tonie
tonisha
tonita
tonja
tony
tonya
tora
tori
torie
torri
torrie
tory
tosha
toshia
toshiko
tova
towanda
toya
tracee
tracey
traci
tracie
tracy
tran
trang
travis
treasa
treena
trena
tresa
tressa
tressie
treva
tricia
trina
trinh
trinidad
trinity
trish
trisha
trista
tristan
troy
trudi
trudie
trudy
trula
tu
tula
tuyet
twana
twanda
twanna
twila
twyla
tyesha
tyisha
tyler
tynisha
tyra
ula
ulrike
un
una
ursula
usha
ute
vada
val
valarie
valda
valencia
valene
valentina
valentine
valeri
valeria
valerie
valery
vallie
valorie
valrie
van
vanda
vanesa
vanessa
vanetta
vania
vanita
vanna
vannesa
vannessa
vashti
vasiliki
veda
velda
velia
vella
velma
velva
velvet
vena
venessa
venetta
venice
venita
vennie
venus
veola
vera
verda
verdell
verdie
verena
vergie
verla
verlene
verlie
verline
verna
vernell
vernetta
vernia
vernice
vernie
vernita
vernon
verona
veronica
veronika
veronique
versie
vertie
vesta
veta
vi
vicenta
vickey
vicki
vickie
vicky
victor
victoria
victorina
vida
viki
vikki
vilma
vina
vincenza
vinita
vinnie
viola
violet
violeta
violette
virgen
virgie
virgil
virgina
virginia
vita
viva
vivan
vivian
viviana
vivien
vivienne
voncile
vonda
vonnie
wai
walter
waltraud
wan
wanda
waneta
wanetta
wanita
wava
wei
wen
wendi
wendie
wendolyn
wendy
wenona
wesley
whitley
whitney
wilda
wilhelmina
wilhemina
willa
willena
willene
willetta
willette
willia
william
willie
williemae
willodean
willow
wilma
windy
winifred
winnie
winnifred
winona
winter
wonda
wynell
wynona
xenia
xiao
xiomara
xochitl
xuan
yadira
yaeko
yael
yahaira
yajaira
yan
yang
yanira
yasmin
yasmine
yasuko
yee
yelena
yen
yer
yesenia
yessenia
yetta
yevette
yi
ying
yoko
yolanda
yolande
yolando
yolonda
yon
yong
yoshie
yoshiko
youlanda
young
yu
yuette
yuk
yuki
yukiko
yuko
yulanda
yun
yung
yuonne
yuri
yuriko
yvette
yvone
yvonne
zada
zaida
zana
zandra
zelda
zella
zelma
zena
zenaida
zenia
zenobia
zetta
zina
zita
zoe
zofia
zoila
zola
zona
zonia
zora
zoraida
zula
zulema
zulma""".split()
########NEW FILE########
__FILENAME__ = introspection
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu

"""
    Tag to use python introspection in a Django template
"""

from django import template
register = template.Library()


@register.filter
def getattr(obj, args):
    """ 
        Try to get an attribute from an object.

        Example: {% if block|getattr:"editable,True" %}

        Beware that the default is always a string, if you want this
        to return False, pass an empty second argument:

        {% if block|getattr:"editable," %}

        Source: http://djangosnippets.org/snippets/38/
    """
    try:
        args = args.split(',')
    except AttributeError:
        raise AttributeError(('"%s" is not a proper value the "getattr" '
                              'filter applied to "%s"') % (args, obj))

    if len(args) == 1:
        (attribute, default) = [args[0], ''] 
    else:
        (attribute, default) = args

    try:
        return obj.__getattribute__(attribute)
    except AttributeError:
         return  obj.__dict__.get(attribute, default)
    except:
        return default
########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4 nu


import imp
import os
import sys

from django.http import HttpResponse
try:
    from django.core.management import setup_environ
except  ImportError:
    from django.conf import settings
    setup_environ = lambda module: settings.configure(**module.__dict__)


__all__ = ['HttpResponseException', 'setting', 'get_client_ip', 'load_config']


class HttpResponseException(HttpResponse, Exception):
    pass


def setting(name, default=None):
    """
        Gets settings from django.conf if exists, returns default value otherwise

        Example:

        DEBUG = setting('DEBUG', False)
    """
    from django.conf import settings
    return getattr(settings, name, default)


def get_client_ip(request):
    """
        Return the client IP address as a string.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]

    return request.META.get('REMOTE_ADDR')


def load_config(path, starting_point='.', settings_module='settings'):
    """
        Add the settings directory to the sys.path, import the settings and
        configure django with it.

        You can path an absolute or a relative path to it.

        If you choose to use a relative path, it will be relative to
        `starting_point` by default, which is set to '.'.

        You may want to set it to something like __file__ (the basename will
        be stripped, and the current file's parent directory will be used
        as a starting point, which is probably what you expect in the
        first place).

        :example:

        >>> load_config('../../settings.py', __file__)
    """

    if not os.path.isabs(path):

        if os.path.isfile(starting_point):
            starting_point = os.path.dirname(starting_point)

        path = os.path.join(starting_point, path)

    path = os.path.realpath(os.path.expandvars(os.path.expanduser(path)))

    if os.path.isfile(path):
        module = os.path.splitext(os.path.basename(path))[0]
        path = os.path.dirname(path)
    else:
        module = os.path.environ.get('DJANGO_SETTINGS_MODULE', settings_module)

    sys.path.append(path)

    f, filename, desc = imp.find_module(module, [path])
    project = imp.load_module(module, f, filename, desc)
    setup_environ(project)

########NEW FILE########
