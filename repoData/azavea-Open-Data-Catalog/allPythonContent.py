__FILENAME__ = fabfile
# USAGE: fab --host=localhost catalog
# When prompted for postgres role passowrd, use 'passw0rd' for default config.
#
# Install the prerequisites:
#     apt-get install python-pip
#     pip install fabric
#
# Get the script, don't check out the entire repo (fabric will get the repo):
#     wget https://raw.github.com/azavea/Open-Data-Catalog/master/fabfile.py


from fabric import api as fab


# NOTE(xtoddx): I'm not well versed in Postgres, but making this be the
#               unix account name makes things simple, it seems.  Using
#               'catalog' for both a unix user and a postgres user is
#               recommended, as the sample config supports it.
DB_USER='catalog'
GIT_REPO='https://github.com/azavea/Open-Data-Catalog.git'
OVERLAY_REPO='https://github.com/openlexington/ODC-overlay.git'


def unix_user():
    fab.sudo('useradd -m -G sudo %s' % (DB_USER,))

def apt_dependencies():
    fab.sudo('apt-get install --yes sendmail postgresql python-pip libpq-dev '
             'python-dev git')


def python_dependencies():
    fab.sudo('pip install virtualenv')


def dependencies():
    apt_dependencies()
    python_dependencies()


def virtualenv():
    fab.run('virtualenv opendatacatalog')


def source():
    with fab.cd('opendatacatalog'):
        fab.run('rm -rf Open-Data-Catalog || true')
        fab.run('git clone %s' % (GIT_REPO,))


def pip_from_app():
    with fab.cd('opendatacatalog/Open-Data-Catalog'):
        fab.run('PIP_DOWNLOAD_CACHE=../pip-cache ../bin/pip install -r '
                'requirements.txt')


def links_and_permissions():
    with fab.cd('opendatacatalog/Open-Data-Catalog/OpenDataCatalog'):
        fab.run('mkdir media')
        fab.run('chmod 755 media')
        fab.run('ln -s ../../lib/python2.7/site-packages/django/contrib/admin'
                '/admin_media')


def create_postgres_user():
    fab.sudo('createuser -S -d -R -P %s' % (DB_USER,), user='postgres')


def create_postgres_table():
    fab.sudo('psql template1 -c '
             '"CREATE DATABASE catalog OWNER \\\\"%s\\\\";"' % (DB_USER,),
             user='postgres')

def create_postgres_pycsw_plpythonu():
    fab.sudo('createlang plpythonu catalog', user='postgres')
    fab.sudo('psql -d catalog -f etc/pycsw_plpythonu.sql', user='postgres')


def postgres():
    create_postgres_user()
    create_postgres_table()
    create_postgres_pycsw_plpythonu()

def local_settings():
    with fab.cd('opendatacatalog/Open-Data-Catalog/OpenDataCatalog'):
        fab.run('cp local_settings.py.example local_settings.py')


def style_overlay():
    with fab.cd('opendatacatalog'):
        fab.run('git clone %s' % (OVERLAY_REPO,))


def syncdb():
    with fab.cd('opendatacatalog/Open-Data-Catalog/OpenDataCatalog'):
        fab.sudo('../../bin/python manage.py syncdb', user=DB_USER)

def migrate():
    with fab.cd('opendatacatalog/Open-Data-Catalog/OpenDataCatalog'):
        fab.sudo('../../bin/python manage.py migrate', user=DB_USER)


def catalog():
    unix_user()
    dependencies()
    virtualenv()
    source()
    pip_from_app()
    links_and_permissions()
    postgres()
    local_settings()
    style_overlay()
    syncdb()
    migrate()


def server_dependencies():
    fab.sudo('apt-get install --yes libapache2-mod-wsgi')


def server_config():
    with fab.cd('opendatacatalog'):
        fab.run('cat Open-Data-Catalog/apache.conf.sample'
	        '| sed -e s!{{PATH}}!`pwd`/Open-Data-Catalog!'
		'> /etc/apache2/sites-enabled/000-default')


def static_assets():
    with fab.cd('opendatacatalog/Open-Data-Catalog/OpenDataCatalog'):
        fab.mkdir('static')
        fab.run('../../bin/python manage.py collectstatic --link --noinput')


def restart_server():
    fab.sudo('apache2ctl restart')


def server():
    server_dependencies()
    server_config()
    static_assets()
    restart_server()

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "OpenDataCatalog.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = encoder
from OpenDataCatalog.opendata.models import Resource, DataType, Tag, CoordSystem, Url, UrlImage, Idea, IdeaImage
from OpenDataCatalog.suggestions.models import Suggestion
import simplejson as j

def tiny_resource_encoder(obj):
        return { "name" : obj.name,
                 "id" : obj.id,
                 "url" : "/api/resources/%s/" %(obj.id)
                 }


def short_resource_encoder(obj):
        return { "name" : obj.name,
                 "short_description" : obj.short_description,
                 "release_date" : obj.release_date,
                 "time_period" : obj.time_period,
                 "organization" : obj.organization,
                 "division" : obj.division,
                 "tags" : list(obj.tags.all()),

                 "area_of_interest" : obj.area_of_interest,
                 "is_published" : obj.is_published,
                 
                 "rating" : obj.rating.score,                 
               
                 "id" : obj.id,
                 "url" : "/api/resources/%s/" %(obj.id)
                 }

def full_resource_encoder(obj):
        return { "name" : obj.name,
                 "short_description" : obj.short_description,
                 "release_date" : obj.release_date,
                 "time_period" : obj.time_period,
                 "organization" : obj.organization,
                 "division" : obj.division,
                 "usage" : obj.usage,
                 "tags" : list(obj.tags.all()),
                 "data_types" : list(obj.data_types.all()),
                 "data_formats" : obj.data_formats,

                 "description" : obj.description,
                 "contact_phone" : obj.contact_phone,
                 "contact_email" : obj.contact_email,
                 "contact_url" : obj.contact_url,

                 "updates" : obj.updates.update_frequency if obj.updates else None,
                 "update_frequency" : obj.update_frequency,
                 "area_of_interest" : obj.area_of_interest,
                 "is_published" : obj.is_published,
                 
                 "created_by" : obj.created_by.username,
                 "last_updated_by" : obj.last_updated_by.username,
                 "last_updated" : obj.last_updated,
                 "metadata_contact" : obj.metadata_contact,
                 "metadata_notes" : obj.metadata_notes,

                 "coord_sys" : list(obj.coord_sys.all()),
                 "proj_coord_sys" : obj.proj_coord_sys,
                 "rating" : obj.rating.score,                 
               
                 "urls" : list(obj.url_set.all()),
                 "id" : obj.id
                 }

def encode_resource(resource_encoder):
    def encode_resource_with_encoder(obj):
        if isinstance(obj, Resource):
            return resource_encoder(obj)
        elif isinstance(obj, Suggestion):
            return { "text" : obj.text,
                     "suggested_by" : obj.suggested_by.username,
                     "suggested_date" : obj.suggested_date,
                     "last_modified_date" : obj.last_modified_date,
                     "rating" : obj.rating.votes,
                     "url" : "/api/suggestions/%s/" %(obj.id),
                     "id" : obj.pk
                     }
        elif isinstance(obj, Idea):
            return { "title" : obj.title,
                     "id" : obj.pk,
                     "description" : obj.description,
                     "author" : obj.author,
                     "created_by" : obj.created_by.username,
                     "created_by_date" : obj.created_by_date,
                     "updated_by" : obj.updated_by.username,
                     "updated_by_date" : obj.updated_by_date,
                     "resources" : list(obj.resources.all()),
                     "images" : list(IdeaImage.objects.filter(idea = obj).all())
                     }
        elif isinstance(obj, Url):
            return { "url" : obj.url,
                     "label" : obj.url_label,
                     "type" : obj.url_type.url_type,
                     "images" : list(obj.urlimage_set.all())
                     }            
        elif isinstance(obj, CoordSystem):
            return { "name": obj.name,
                     "description": obj.description,
                     "EPSG_code" : obj.EPSG_code
                     }
        elif isinstance(obj, UrlImage) or isinstance(obj, IdeaImage):
            return { "title" : obj.title,
                     "source" : obj.source,
                     "source_url" : obj.source_url,
                     "image_thumb_url" : "/media/" + obj.image.thumbnail.relative_url,
                     "image_url" : obj.image.url
                     }
        elif isinstance(obj, DataType):
            return obj.data_type
        elif isinstance(obj, Tag):
            return { "name" : obj.tag_name,
                     "url" : "/api/tags/%s/" % obj.tag_name }
        elif hasattr(obj, "strftime"):
            return obj.strftime("%Y-%m-%d")
        else:
            raise TypeError(repr(obj) + " is not JSON serializable")
    return encode_resource_with_encoder

def json_encode(obj, rsrc = short_resource_encoder):
    return j.dumps(obj, default = encode_resource(rsrc))

def json_load(jsonstr):
    return j.loads(jsonstr)

########NEW FILE########
__FILENAME__ = models
# Keep the test runner happy

########NEW FILE########
__FILENAME__ = rest
from django.http import HttpResponse
from django.contrib.auth import authenticate
import re
import base64

def http_unauth():
    res = HttpResponse("Unauthorized")
    res.status_code = 401
    res['WWW-Authenticate'] = 'Basic realm="Secure Area"'
    return res

def match_first(regx, strg):
    m = re.match(regx, strg)
    if (m == None):
        return None
    else:
        return m.group(1)

def decode_auth(strg):
    if (strg == None):
        return None
    else:
        m = re.match(r'([^:]*)\:(.*)', base64.decodestring(strg))
        if (m != None):
            return (m.group(1), m.group(2))
        else:
            return None

def parse_auth_string(authstr):
    auth = decode_auth(match_first('Basic (.*)', authstr))
    if (auth == None):
        return None
    else:
        return authenticate(username = auth[0], password = auth[1])
        
def login_required(view_f):
    def wrapperf(request, *args, **kwargs):
        if (request.META.has_key('HTTP_AUTHORIZATION')):
            auth = request.META['HTTP_AUTHORIZATION']
            user = parse_auth_string(auth)
            if (user != None):
                request.user = user
                return view_f(request, *args, **kwargs)
        return http_unauth()

    return wrapperf


########NEW FILE########
__FILENAME__ = tests
"""
A few test to verify basic functionality. The encoder should probably be tested directly

This file demonstrates writing tests using the unittest module. These shoud pass
when you run "manage.py test".
"""
from OpenDataCatalog.opendata.models import *
from OpenDataCatalog.suggestions.models import *

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from datetime import datetime

import simplejson as j
import base64

class RestTestCase(TestCase):
    def setUp(self):
        self.c = Client()
        self.password = "password"
        self.u = User.objects.create(username="testuser")
        self.u.set_password(self.password)
        self.u.save()

        self.u2 = User.objects.create(username="testuser2")
        self.u2.set_password(self.password)
        self.u2.save()

    def mkrsrc(self,name,**kwargs):
        return Resource.objects.create(
            name = name,
            created_by = self.u,
            last_updated_by=self.u,
            created = datetime.now(),
            **kwargs)

    def mkidea(self,title,**kwargs):
        return Idea.objects.create(
            title = title,
            created_by = self.u,
            created_by_date = datetime.now(),
            updated_by = self.u,
            **kwargs)

    def mktag(self,tag_name,**kwargs):
        return Tag.objects.create(
            tag_name = tag_name,
            **kwargs)

    def mksug(self,text, **kwargs):
        return Suggestion.objects.create(
            text = text,
            suggested_by = self.u,
            **kwargs)

    def verify_ids(self, objdict, objlist, dict_key="id", list_key = "pk"):
        self.assertEquals(
            set(map(lambda obj: obj[dict_key], objdict)),
            set(map(lambda obj: getattr(obj, list_key), objlist)))

    def get(self, url):
        return j.loads(self.c.get(url).content)

    def assertCode(self, resp, code):
        self.assertEquals(resp.status_code, code)

    def assertEmptyList(self, url):
        self.assertEquals(self.get(url), list())

    def auth_pair(self, user, password = None):
        if not password:
            password = self.password

        base64_auth = base64.encodestring(user.username + ":" + password)
        return {"HTTP_AUTHORIZATION" : "Basic " + base64_auth}

class SuggestionsTest(RestTestCase):
    def test_empty_case(self):
        self.assertEmptyList("/api/suggestions/")

    def test_many(self):
        sug1 = self.mksug("sug1")
        sug2 = self.mksug("sug2")

        self.verify_ids(self.get("/api/suggestions/"), [sug1,sug2])

    def test_one(self):
        sug1 = self.mksug("sug1")
        sug2 = self.mksug("sug2")

        self.assertEquals(self.get("/api/suggestions/%d/" % sug1.pk)["id"], sug1.pk)
        self.assertEquals(self.get("/api/suggestions/%d/" % sug2.pk)["id"], sug2.pk)

    def test_search(self):
        sug1 = self.mksug("sug_a_b")
        sug2 = self.mksug("sug_c_b")
        sug3 = self.mksug("a_sug_c")

        # All results
        self.verify_ids(self.get("/api/suggestions/search?qs="), [sug1,sug2,sug3])

        # Basic searches
        self.verify_ids(self.get("/api/suggestions/search?qs=sug_a"), [sug1])
        self.verify_ids(self.get("/api/suggestions/search?qs=sug_"), [sug1,sug2,sug3])
        self.verify_ids(self.get("/api/suggestions/search?qs=_c"), [sug2,sug3])

        # No results
        self.assertEqual(self.get("/api/suggestions/search?qs=fail"), [])

    def test_invalid_url(self):
        self.assertCode(self.c.get("/api/suggestions/22/"), 404)
        self.assertCode(self.c.get("/api/suggestions/f/"), 404)

    def test_invalid_login(self):
        sug1 = self.mksug("sug1")

        resp = self.c.put("/api/suggestions/%s/vote"%sug1.pk, {}, **self.auth_pair(self.u,"fail"))
        self.assertEquals(resp.status_code, 401)


    def test_vote(self):
        sug1 = self.mksug("sug1")

        self.assertEqual(sug1.rating.votes, 0)

        # Single vote
        self.c.put("/api/suggestions/%s/vote"%sug1.pk, {}, **self.auth_pair(self.u))
        self.assertEqual(Suggestion.objects.all()[0].rating.votes, 1)

        # Only allow 1 vote
        self.c.put("/api/suggestions/%s/vote"%sug1.pk, {}, **self.auth_pair(self.u))
        self.assertEqual(Suggestion.objects.all()[0].rating.votes, 1)

        # Remove vote (does not exist)
        self.c.delete("/api/suggestions/%s/vote"%sug1.pk, {}, **self.auth_pair(self.u2))
        self.assertEqual(Suggestion.objects.all()[0].rating.votes, 1)

        # Second vote
        self.c.put("/api/suggestions/%s/vote"%sug1.pk, {}, **self.auth_pair(self.u2))
        self.assertEqual(Suggestion.objects.all()[0].rating.votes, 2)

        # Only allow 1 vote
        self.c.put("/api/suggestions/%s/vote"%sug1.pk, {}, **self.auth_pair(self.u2))
        self.assertEqual(Suggestion.objects.all()[0].rating.votes, 2)

        # Remove vote
        self.c.delete("/api/suggestions/%s/vote"%sug1.pk, {}, **self.auth_pair(self.u))
        self.assertEqual(Suggestion.objects.all()[0].rating.votes, 1)

        # Only remove once
        self.c.delete("/api/suggestions/%s/vote"%sug1.pk, {}, **self.auth_pair(self.u))
        self.assertEqual(Suggestion.objects.all()[0].rating.votes, 1)

        # Back to zero
        self.c.delete("/api/suggestions/%s/vote"%sug1.pk, {}, **self.auth_pair(self.u2))
        self.assertEqual(Suggestion.objects.all()[0].rating.votes, 0)
        
class TagTest(RestTestCase):
    def test_empty_case(self):
        self.assertEmptyList("/api/tags/")

    def test_many(self):
        tag1 = self.mktag("tag1")
        tag2 = self.mktag("tag2")

        self.verify_ids(self.get("/api/tags/"), [tag1, tag2], "name", "tag_name")

    def test_one_empty(self):
        tag1 = self.mktag("tag1")

        self.assertEmptyList("/api/tags/%s/" % tag1.tag_name)

    def test_one(self):
        tag1 = self.mktag("tag1")
        tag2 = self.mktag("tag2")

        rsrc1 = self.mkrsrc("rsrc1")
        rsrc2 = self.mkrsrc("rsrc2")
        rsrc3 = self.mkrsrc("rsrc3")

        rsrc1.tags.add(tag1)
        rsrc2.tags.add(tag1)
        rsrc2.tags.add(tag2)
        rsrc3.tags.add(tag2)
        
        self.verify_ids(self.get("/api/tags/%s/" % tag1.tag_name),[rsrc1,rsrc2])
        self.verify_ids(self.get("/api/tags/%s/" % tag2.tag_name),[rsrc2,rsrc3])

class IdeaTest(RestTestCase):
    def test_empty_case(self):
        self.assertEmptyList("/api/ideas/")

    def test_many(self):
        idea1 = self.mkidea("idea1")
        idea2 = self.mkidea("idea2")
        
        self.verify_ids(self.get("/api/ideas/"), [idea1,idea2])

    def test_single_case(self):
        idea1 = self.mkidea("idea1")

        self.assertEquals(self.get("/api/ideas/%d/" % idea1.pk)["id"], idea1.pk)

    def test_invalid_url(self):
        self.assertCode(self.c.get("/api/ideas/22/"), 404)
        self.assertCode(self.c.get("/api/ideas/f/"), 404)

        

class ResourceTest(RestTestCase):

    def test_empty_json_case(self):
        self.assertEmptyList("/api/resources/")
        
    def test_search(self):
        # Search fields:
        # name, description, org, div
        
        rsrc1 = self.mkrsrc("rsrc_a")
        rsrc2 = self.mkrsrc("rsrc_a", description = "descr_a")
        rsrc3 = self.mkrsrc("rsrc_b", description = "descr_b")
        rsrc4 = self.mkrsrc("f_rsrc_c", description = "descr_b", organization = "org_a")
        rsrc5 = self.mkrsrc("f_rsrc_d", organization = "org_a", division = "div_a")
        rsrc6 = self.mkrsrc("f_rsrc_e", division = "div_a", organization = "orb_c")

        # Empty search - return everything
        self.verify_ids(self.get("/api/resources/search?qs="), [rsrc1,rsrc2, rsrc3, rsrc4, rsrc5, rsrc6])

        # No search match
        self.assertEquals(self.get("/api/resources/search?qs=fail"), list())

        # Name partial search
        self.verify_ids(self.get("/api/resources/search?qs=f_rsrc_"), [rsrc4,rsrc5,rsrc6])

        # Name exact search
        self.verify_ids(self.get("/api/resources/search?qs=rsrc_c"), [rsrc4])

        # Description search
        self.verify_ids(self.get("/api/resources/search?qs=descr_b"), [rsrc3,rsrc4])

        # Organization search
        self.verify_ids(self.get("/api/resources/search?qs=org_a"), [rsrc4,rsrc5])

        # Division search
        self.verify_ids(self.get("/api/resources/search?qs=div_a"), [rsrc5,rsrc6])

    def test_multi_case(self):

        rsrc1 = self.mkrsrc("rsrc1")
        rsrc2 = self.mkrsrc("rsrc2")
        rsrc3 = self.mkrsrc("rsrc3", is_published=False)

        # Don't show non-published data
        self.verify_ids(self.get("/api/resources/"), [rsrc1, rsrc2])

        rsrc3.is_published = True
        rsrc3.save()

        self.verify_ids(self.get("/api/resources/"), [rsrc1, rsrc2, rsrc3])
    
    def test_single_case(self):
        rsrc1 = self.mkrsrc("rsrc1")

        self.assertEquals(self.get("/api/resources/%d/" % rsrc1.pk)["id"], rsrc1.pk)

    def test_invalid_url(self):
        self.assertCode(self.c.get("/api/resources/22/"), 404)
        self.assertCode(self.c.get("/api/resources/f/"), 404)

        


########NEW FILE########
__FILENAME__ = views
# Create your views here
from django.http import HttpResponse, Http404
from OpenDataCatalog.opendata.models import *
from OpenDataCatalog.opendata.views import send_email
from OpenDataCatalog.suggestions.models import Suggestion
from datetime import datetime
from encoder import *
from rest import login_required
from django.views.decorators.csrf import csrf_exempt

def http_badreq(body = ""):
    res = HttpResponse("Bad Request\n" + body)
    res.status_code = 400
    return res

@login_required
def vote(request, suggestion_id):
    suggestion = Suggestion.objects.get(pk=suggestion_id)
    remote_addr = request.META['REMOTE_ADDR']
    if request.method == 'PUT' and suggestion != None:
        did_vote = suggestion.rating.get_rating_for_user(request.user, remote_addr)
        
        if did_vote == None:
            suggestion.rating.add(score=1, user=request.user, ip_address=remote_addr)

        return HttpResponse(json_encode(suggestion))

    elif request.method == "DELETE" and suggestion != None:
        vote = suggestion.rating.get_ratings().filter(user = request.user)
        if vote:
            vote.delete()
                
        return HttpResponse(json_encode(suggestion))

    raise Http404

def add_suggestion(user, text, remote_addr):
    sug = Suggestion()
    sug.suggested_by = user
    sug.text = text
            
    sug.save()            
    sug.rating.add(score=1, user=user, ip_address=remote_addr)
            
    return sug

@login_required
def add_suggestion_view(request):
    json_string = request.raw_post_data
    json_dict = json_load(json_string)

    if (json_dict.has_key("text") == False):
        return http_badreq()

    text = json_dict["text"]

    return HttpResponse(json_encode(add_suggestion(request.user, text, request.META['REMOTE_ADDR'])))

def suggestion(request, suggestion_id):
    objs = Suggestion.objects.filter(pk = suggestion_id)

    if objs and len(objs) == 1:
        return HttpResponse(json_encode(objs[0]))
    else:
        raise Http404

@csrf_exempt
def suggestions(request):
    if (request.method == 'POST'):
        return add_suggestion_view(request)
    elif (request.method == 'GET'):
        return HttpResponse(json_encode(list(Suggestion.objects.all())))
    else:
        raise Http404

def search_suggestions(request):
    if 'qs' in request.GET:
        qs = request.GET['qs'].replace("+"," ")

        return HttpResponse(json_encode(list(Suggestion.objects.filter(text__icontains=qs))))
    else:
        return http_badreq("Missing required parameter qs")

def ideas(request):
    return HttpResponse(json_encode(list(Idea.objects.all()), tiny_resource_encoder))

def idea(request, idea_id):
    obj = Idea.objects.filter(id = idea_id)
    if obj and len(obj) == 1:
        return HttpResponse(json_encode(obj[0]))
    else:
        raise Http404

def tags(request):
    return HttpResponse(json_encode(list(Tag.objects.all())))

def by_tag(request, tag_name):
    return HttpResponse(json_encode(list(Resource.objects.filter(tags__tag_name = tag_name))))

def resource_search(request):
    if 'qs' in request.GET:
        qs = request.GET['qs'].replace("+", " ")
        search_resources = Resource.search(qs) 

        return HttpResponse(json_encode(list(search_resources), short_resource_encoder))
    else:
        return http_badreq("Must specify qs search param")

def resource(request, resource_id):
    rsrc = Resource.objects.filter(id=resource_id, is_published = True)
    if rsrc and len(rsrc) == 1:
        return HttpResponse(json_encode(rsrc[0], full_resource_encoder))
    else:
        raise Http404

def resources(request):
    return HttpResponse(json_encode(list(Resource.objects.filter(is_published = True)), short_resource_encoder))

def safe_key_getter(dic):
    def annon(key, f = lambda x: x):
        if dic.has_key(key):
            return f(dic[key])
        else:
            return None
    return annon

@csrf_exempt
def submit(request):
    if (request.method == 'POST'):
        json_dict = safe_key_getter(json_load(request.raw_post_data))
    
        coord_list = json_dict("coord_system")
        type_list = json_dict("types")
        format_list = json_dict("formats")
        update_frequency_list = json_dict("update_frequency")

        coords, types, formats, updates ="", "", "", ""

        if (coord_list == None):
            return http_badreq("coord_system should be a list")
        if (type_list == None):
            return http_badreq("types should be a list")
        if (format_list == None):
            return http_badreq("formats should be a list")
        if (update_frequency_list == None):
            return http_badreq("update_frequency should be a list")

            
        for c in coord_list:
            coords = coords + " EPSG:" + CoordSystem.objects.get(pk=c).EPSG_code.__str__()
        
        for t in type_list:
            types = types + " " + UrlType.objects.get(pk=t).url_type        
            
        for f in format_list:
            formats = formats + " " + DataType.objects.get(pk=f).data_type

        for u in update_frequency_list:
            if u:
                updates = updates + " " + UpdateFrequency.objects.get(pk=u).update_frequency
                
        data = {
            "submitter": request.user.username,
            "submit_date": datetime.now(),
            "dataset_name": json_dict("dataset_name"),
            "organization": json_dict("organization"),
            "copyright_holder": json_dict("copyright_holder"),
            "contact_email": json_dict("contact_email"),
            "contact_phone": json_dict("contact_phone"),
            "url": json_dict("url"),
            "time_period": json_dict("time_period"),
            "release_date": json_dict("release_date"),
            "area_of_interest": json_dict("area_of_interest"),
            "update_frequency": updates,
            "coord_system": coords,
            "types": types,
            "formats": formats,
            "usage_limitations": json_dict("usage_limitations"),
            "collection_process": json_dict("collection_process"),
            "data_purpose": json_dict("data_purpose"),
            "intended_audience": json_dict("intended_audience"),
            "why": json_dict("why"),
            }
        
        for key in data:
            if (data[key] == None or (hasattr(data[key], "len") and len(data[key]) == 0)):
                return http_badreq(key + " is empty or not defined")

        send_email(request.user, data)

        return HttpResponse("Created")
    else:
        raise Http404

########NEW FILE########
__FILENAME__ = mappings

MD_CORE_MODEL = {
    'typename': 'pycsw:CoreMetadata',
    'outputschema': 'http://pycsw.org/metadata',
    'mappings': {
        'pycsw:Identifier': 'csw_identifier',
        'pycsw:Typename': 'csw_typename',
        'pycsw:Schema': 'csw_schema',
        'pycsw:MdSource': 'csw_mdsource',
        'pycsw:InsertDate': 'last_updated',
        'pycsw:XML': 'csw_xml',
        'pycsw:AnyText': 'csw_anytext',
        'pycsw:Language': 'language',
        'pycsw:Title': 'name',
        'pycsw:Abstract': 'description',
        'pycsw:Keywords': 'csw_keywords',
        'pycsw:KeywordType': 'keywordstype',
        'pycsw:Format': 'data_formats',
        'pycsw:Source': 'csw_identifier',
        'pycsw:Date': 'created',
        'pycsw:Modified': 'last_updated',
        'pycsw:Type': 'csw_type',
        'pycsw:BoundingBox': 'wkt_geometry',
        'pycsw:CRS': 'csw_crs',
        'pycsw:AlternateTitle': 'title_alternate',
        'pycsw:RevisionDate': 'date_revision',
        'pycsw:CreationDate': 'created',
        'pycsw:PublicationDate': 'date_publication',
        'pycsw:OrganizationName': 'organization',
        'pycsw:SecurityConstraints': 'securityconstraints',
        'pycsw:ParentIdentifier': 'parentidentifier',
        'pycsw:TopicCategory': 'topicategory',
        'pycsw:ResourceLanguage': 'resourcelanguage',
        'pycsw:GeographicDescriptionCode': 'geodescode',
        'pycsw:Denominator': 'denominator',
        'pycsw:DistanceValue': 'distancevalue',
        'pycsw:DistanceUOM': 'distanceuom',
        'pycsw:TempExtent_begin': 'temporal_extent_start',
        'pycsw:TempExtent_end': 'temporal_extent_end',
        'pycsw:ServiceType': 'servicetype',
        'pycsw:ServiceTypeVersion': 'servicetypeversion',
        'pycsw:Operation': 'operation',
        'pycsw:CouplingType': 'couplingtype',
        'pycsw:OperatesOn': 'operateson',
        'pycsw:OperatesOnIdentifier': 'operatesonidentifier',
        'pycsw:OperatesOnName': 'operatesoname',
        'pycsw:Degree': 'degree',
        'pycsw:AccessConstraints': 'accessconstraints',
        'pycsw:OtherConstraints': 'otherconstraints',
        'pycsw:Classification': 'classification',
        'pycsw:ConditionApplyingToAccessAndUse': 'conditionapplyingtoaccessanduse',
        'pycsw:Lineage': 'lineage',
        'pycsw:ResponsiblePartyRole': 'responsiblepartyrole',
        'pycsw:SpecificationTitle': 'specificationtitle',
        'pycsw:SpecificationDate': 'specificationdate',
        'pycsw:SpecificationDateType': 'specificationdatetype',
        'pycsw:Creator': 'csw_creator',
        'pycsw:Publisher': 'csw_creator',
        'pycsw:Contributor': 'csw_creator',
        'pycsw:Relation': 'relation',
        'pycsw:Links': 'csw_links',
    }
}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    '',
    url(r'^csw$','OpenDataCatalog.catalog.views.csw'),
)

########NEW FILE########
__FILENAME__ = views
import json
import os.path

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from OpenDataCatalog.opendata.models import Resource
from pycsw import server

CONFIGURATION = {
    'server': {
        'home': '.',
        'mimetype': 'application/xml; charset=UTF-8',
        'encoding': 'UTF-8',
        'language': 'en-US',
        'maxrecords': '10',
        # 'pretty_print': 'true',
        'profiles': 'apiso,ebrim',
    },
    'repository': {
        'source': 'odc',
        'mappings': os.path.join(os.path.dirname(__file__), 'mappings.py')
    }
}


@csrf_exempt
def data_json(request):
    """Return data.json representation of site catalog"""
    json_data = []
    for resource in Resource.objects.all():
        record = {} 
        record['title'] = resource.name
        record['description'] = resource.description
        record['keyword'] = resource.csw_keywords.split(',')
        record['modified'] = resource.last_updated
        record['publisher'] = resource.organization
        record['contactPoint'] = resource.metadata_contact
        record['mbox'] = resource.contact_email
        record['identifier'] = resource.csw_identifier
        if resource.is_published:
            record['accessLevel'] = 'public'
        else:
            record['accessLevel'] = 'non-public'

        json_data.append(record)

    return HttpResponse(json.dumps(json_data), 'application/json')

@csrf_exempt
def csw(request):
    """CSW WSGI wrapper"""
    # serialize settings.CSW into SafeConfigParser
    # object for interaction with pycsw
    mdict = dict(settings.CSW, **CONFIGURATION)

    # update server.url
    server_url = '%s://%s%s' % \
        (request.META['wsgi.url_scheme'],
         request.META['HTTP_HOST'],
         request.META['PATH_INFO'])

    mdict['server']['url'] = server_url

    env = request.META.copy()

    env.update({ 
            'local.app_root': os.path.dirname(__file__),
            'REQUEST_URI': request.build_absolute_uri(),
            })
            
    csw = server.Csw(mdict, env)

    content = csw.dispatch_wsgi()

    return HttpResponse(content, content_type=csw.contenttype)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.comments.forms import CommentForm
from OpenDataCatalog.comments.models import CommentWithRating
from OpenDataCatalog.comments.widgets import StarsRadioFieldRenderer

RATING_CHOICES = (
    (1,1),
    (2,2),
    (3,3),
    (4,4),
    (5,5),
)

class CommentFormWithRating(CommentForm):
    rating = forms.CharField(widget=forms.RadioSelect(renderer=StarsRadioFieldRenderer, attrs={'class':'star'}, choices=RATING_CHOICES))
    
    def get_comment_model(self):
        # Use our custom comment model instead of the built-in one.
        return CommentWithRating

    def get_comment_create_data(self):
        # Use the data of the superclass, and add in the title field
        data = super(CommentFormWithRating, self).get_comment_create_data()
        data['rating'] = self.cleaned_data['rating']
        return data
        

########NEW FILE########
__FILENAME__ = models
from django import forms
from django.db import models
from django.contrib.comments.models import Comment

class CommentWithRating(Comment):
    rating = models.IntegerField()

    def save(self, *args, **kwargs):
        self.content_object.rating.add(score=self.rating, user=self.user, ip_address=self.ip_address)
        super(CommentWithRating, self).save(*args, **kwargs)

########NEW FILE########
__FILENAME__ = widgets
from django.forms.util import flatatt

from django.utils.encoding import StrAndUnicode, force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

class StarsRadioInput(StrAndUnicode):
    """
    An object used by RadioFieldRenderer that represents a single
    <input type='radio'>.
    """

    def __init__(self, name, value, attrs, choice, index):
        self.name, self.value = name, value
        self.attrs = attrs
        self.choice_value = force_unicode(choice[0])
        self.choice_label = force_unicode(choice[1])
        self.index = index

    def __unicode__(self):
       return mark_safe(u'%s' % self.tag())

    def is_checked(self):
        return self.value == self.choice_value

    def tag(self):
        if 'id' in self.attrs:
            self.attrs['id'] = '%s_%s' % (self.attrs['id'], self.index)
        final_attrs = dict(self.attrs, type='radio', name=self.name, value=self.choice_value)
        if self.is_checked():
            final_attrs['checked'] = 'checked'
        return mark_safe(u'<input%s />' % flatatt(final_attrs))


class StarsRadioFieldRenderer(StrAndUnicode):
    def __init__(self, name, value, attrs, choices):
        self.name, self.value, self.attrs = name, value, attrs
        self.choices = choices

    def __iter__(self):
        for i, choice in enumerate(self.choices):
            yield StarsRadioInput(self.name, self.value, self.attrs.copy(), choice, i)

    def __getitem__(self, idx):
        choice = self.choices[idx] # Let the IndexError propogate
        return StarsRadioInput(self.name, self.value, self.attrs.copy(), choice, idx)

    def __unicode__(self):
        return self.render()

    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(u'\n%s\n' % u'\n'.join([u'%s'
                % force_unicode(w) for w in self]))
    
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

import os
import datetime
from datetime import datetime as dt

# Create your models here.

DATA_STATUS = (
    ('Released', 'Released'), 
    ('Not Released', 'Not Released'), 
    ('Under Discussion', 'Under Discussion'), 
    ('Cannot Be Released', 'Cannot Be Released'),
    ('Rejected', 'Rejected')
)

class Contest(models.Model):
    title = models.CharField(max_length=255)    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    vote_frequency = models.IntegerField()
    rules = models.TextField()
    
    def get_days_left(self):
        today = dt.today()
        left = self.end_date - today 
        if left.days < 0:
            return 0
        return left.days
    
    def get_days_till_start(self):
        till = self.start_date - dt.today()
        return till.days +1

    def has_ended(self):
        return dt.today() >= self.end_date

    def has_started(self):
        return dt.today() >= self.start_date


    def get_next_vote_date(self, user):
        votes = user.vote_set.order_by('-timestamp')
        increment = datetime.timedelta(days=self.vote_frequency)
        if len(votes):
            last_vote_date = votes[0].timestamp
        else:
            last_vote_date = dt.today()
        next_vote_date = last_vote_date + increment 
        return next_vote_date

    def user_can_vote(self, user):
        votes = user.vote_set.order_by('-timestamp')
        if votes.count() > 0:           
            next_date = self.get_next_vote_date(user)
            if dt.today() < next_date and dt.today() < self.end_date:
                return False
        return True

    def __str__(self):
        return self.title

class Entry(models.Model):
    def get_image_path(instance, filename):
        fsplit = filename.split('.')
        extra = 1
        test_path = os.path.join(settings.MEDIA_ROOT, 'contest_images', str(instance.id), fsplit[0] + '_' + str(extra) + '.' + fsplit[1])
        while os.path.exists(test_path):
           extra += 1
           test_path = os.path.join(settings.MEDIA_ROOT, 'contest_images', str(instance.id), fsplit[0] + '_' + str(extra) + '.' +  fsplit[1])
        path = os.path.join('contest_images', str(instance.id), fsplit[0] + '_' + str(extra) + '.' + fsplit[1])
        return path

    title = models.CharField(max_length=255)
    description = models.TextField()
    short_description = models.CharField(max_length=120)
    nominator = models.CharField(max_length=255)
    nominator_link = models.CharField(max_length=255)
    nominator_image = models.ImageField(upload_to=get_image_path, null=True, blank=True, help_text="Save the entries before adding images.")        
    status = models.CharField(max_length=255, choices=DATA_STATUS, default="Not Released")
    links = models.CharField(max_length=400, null=True, blank=True)
    is_visible = models.BooleanField(default=True)
    data_owner = models.CharField(max_length=255)
    rejected_reason = models.CharField(max_length=255, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)

    contest = models.ForeignKey(Contest)
    vote_count = models.IntegerField(default=0)


    def __str__(self):
        return self.title

    def get_place(self):
        entries = Entry.objects.filter(contest=self.contest).order_by('-vote_count')
        for i, entry in enumerate(entries):
            if entry == self: return i+1

class Vote(models.Model):
    user = models.ForeignKey(User)
    timestamp = models.DateTimeField(auto_now=True)

    entry = models.ForeignKey(Entry)


from django import forms

class EntryForm(forms.Form):
    org_name = forms.CharField(max_length=255, label="Organization Name")
    org_url = forms.CharField(max_length=255, label="Organization Url")
    contact_person = forms.CharField(max_length=150, label="Contact Person")
    contact_phone = forms.CharField(max_length=15, label="Contact Phone Number")
    contact_email = forms.EmailField(max_length=150, label="Contact Email")
    data_set = forms.CharField(max_length=255, label="Data Set to Nominate")
    data_use = forms.CharField(max_length=1000, widget=forms.Textarea, label="If this data set were available, how would your organization use it?")
    data_mission = forms.CharField(max_length=1000, widget=forms.Textarea, label="How would this data set contribute to your organization's mission")
    


########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.template.loader import render_to_string
from django.core.mail import send_mail, mail_managers, EmailMessage
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from OpenDataCatalog.contest.models import *
from datetime import datetime

def get_entries(request, contest_id=1):
    contest = Contest.objects.get(pk=contest_id)
    entries = Entry.objects.filter(contest=contest, is_visible=True)
    if not request.GET.__contains__('sort'):
        entries = entries.order_by('-vote_count')
    return render_to_response('contest/entries.html', {'contest': contest, 'entries': entries}, context_instance=RequestContext(request))

def get_entries_table(request, contest_id=1):
    contest = Contest.objects.get(pk=contest_id)
    entries = Entry.objects.filter(contest=contest)
    if not request.GET.__contains__('sort'):
        entries = entries.order_by('-vote_count')
    return render_to_response('contest/entry_table.html', {'contest': contest, 'entries': entries}, context_instance=RequestContext(request))

def get_winners(request, contest_id=1):
    contest = Contest.objects.get(pk=contest_id)
    entries = Entry.objects.filter(contest=contest, is_visible=True).order_by('-vote_count')
    return render_to_response('contest/winners.html', {'contest': contest, 'entries': entries}, context_instance=RequestContext(request))

def get_rules(request, contest_id=1):
    contest = Contest.objects.get(pk=contest_id)
    return render_to_response('contest/rules.html', {'contest': contest}, context_instance=RequestContext(request))

def get_entry(request, entry_id):
    entry = Entry.objects.get(pk=entry_id)
    return render_to_response('contest/entry.html', {'contest': entry.contest, 'entry': entry}, context_instance=RequestContext(request))

#@login_required
def add_entry(request, contest_id=1):
    contest = Contest.objects.get(pk=contest_id)
    if request.method == 'POST':
        form = EntryForm(request.POST)
        form.contest = contest_id

        if form.is_valid():

            data = {
                #"submitter": request.user.username,
                "submit_date": datetime.now(),
                "org_name": form.cleaned_data.get("org_name"),
                "org_url": form.cleaned_data.get("org_url"),
                "contact_person": form.cleaned_data.get("contact_person"),
                "contact_phone": form.cleaned_data.get("contact_phone"),
                "contact_email": form.cleaned_data.get("contact_email"),
                "data_set": form.cleaned_data.get("data_set"),
                "data_use": form.cleaned_data.get("data_use"),
                "data_mission": form.cleaned_data.get("data_mission")
            }

            subject = 'OpenDataPhilly - Contest Submission'
            user_email = form.cleaned_data.get("contact_email")
            text_content = render_to_string('contest/submit_email.txt', data)
            text_content_copy = render_to_string('contest/submit_email_copy.txt', data)
            mail_managers(subject, text_content)

            msg = EmailMessage(subject, text_content_copy, to=[user_email])
            msg.send()

            return render_to_response('contest/thanks.html', {'contest': contest}, context_instance=RequestContext(request))

    else: 
        form = EntryForm()

    return render_to_response('contest/submit_entry.html', {'contest': contest, 'form': form}, context_instance=RequestContext(request))

@login_required
def add_vote(request, entry_id):
    entry = Entry.objects.get(pk=entry_id)
    contest = entry.contest
    user = User.objects.get(username=request.user)

    if contest.user_can_vote(user):
        new_vote = Vote(user=user, entry=entry)
        new_vote.save()
        entry.vote_count = entry.vote_set.count()
        entry.save()
        next_vote_date = contest.get_next_vote_date(user)
        if next_vote_date > contest.end_date:
            messages.success(request, '<div style="font-weight:bold;">Your vote has been recorded.</div>Thank you for your vote! You will not be able to vote again before the end of the contest. <br><br>Please encourage others to visit <a href="/">OpenDataPhilly</a> and to join the race toward more open data!')
        else:
            messages.success(request, '<div style="font-weight:bold;">Your vote has been recorded.</div>You may vote once per week, so come back and visit us again on ' + next_vote_date.strftime('%A, %b %d %Y, %I:%M%p') + '. <br><br>Until then, encourage others to visit <a href="/">OpenDataPhilly</a> and to join the race toward more open data!')
    else:
        next_vote_date = contest.get_next_vote_date(user)
        if next_vote_date > contest.end_date:
            messages.error(request, '<div style="font-weight:bold;">You have already voted.</div>You will not be able to vote again before the end of the contest. <br><br>Please encourage others to visit <a href="/">OpenDataPhilly</a> and to join the race toward more open data!')
        else:
            messages.error(request, '<div style="font-weight:bold;">You have already voted.</div>You may vote once per week, so come back and visit us again on ' + next_vote_date.strftime('%A, %b %d %Y, %I:%M%p') + '. <br><br>Until then, encourage others to visit <a href="/">OpenDataPhilly</a> and to join the race toward more open data!')    
    
    return redirect('/contest/?sort=vote_count')
    

########NEW FILE########
__FILENAME__ = admin
from datetime import datetime
from OpenDataCatalog.opendata.models import *
from OpenDataCatalog.comments.models import *
from OpenDataCatalog.suggestions.models import *
from OpenDataCatalog.contest.models import *
from django.contrib import admin

class UrlImageInline(admin.TabularInline):
    model = UrlImage
    extra = 1
    
class UrlInline(admin.TabularInline):
    model = Url
    extra = 1
    verbose_name = 'Resource Url'
    verbose_name_plural = 'Resource Urls'

class IdeaImageInline(admin.TabularInline):
    model = IdeaImage
    extra = 1

class ResourceAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields':[('name', 'is_published'), 'description', 'short_description', 'usage', 
            ('organization', 'division'), ('contact_phone', 'contact_email', 'contact_url')], 'classes':['wide']}),
        ('Metadata Fields ', {'fields':['release_date', ('time_period', 'update_frequency'), 
            'updates',
            ('data_formats', 'area_of_interest'), 'proj_coord_sys', 
            ('created_by', 'created'), ('last_updated_by', 'last_updated'),
            ('coord_sys', 'wkt_geometry'),
            'metadata_contact','metadata_notes', 'data_types', 'tags', ], 'classes':['wide']})
    ]
    readonly_fields = ['created_by', 'created', 'last_updated_by', 'last_updated']
    inlines = [UrlInline,]
    
    verbose_name = 'Resource Url'
    verbose_name_plural = 'Resource Urls'
    list_display = ('name', 'organization', 'release_date', 'is_published')
    search_fields = ['name', 'description', 'organization']
    list_filter = ['tags', 'url__url_type', 'is_published']
    date_heirarchy = 'release_date'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.created = datetime.datetime.now()
        
        obj.last_updated_by = request.user
        obj.save()

class UrlImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'image')
    search_fields = ['image', 'title', 'description']
    
class UrlAdmin(admin.ModelAdmin):
    list_display = ('url_label', 'url_type', 'url')
    inlines = [UrlImageInline,]
    list_filter = ['url_type',]
    
class CoordSystemAdmin(admin.ModelAdmin):
    list_display = ('EPSG_code', 'name')
    search_fields = ['name', 'EPSG_code', 'description']

    verbose_name = 'Resource Url'
    verbose_name_plural = 'Resource Urls'
class IdeaAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields':[('title', 'author'),  'description', ('created_by', 'created_by_date'), 
                ('updated_by', 'updated_by_date'), 'resources']})
    ]
    readonly_fields = ['created_by', 'created_by_date', 'updated_by', 'updated_by_date']
    inlines = [IdeaImageInline, ]

    list_display = ('title', 'created_by', 'created_by_date', 'updated_by', 'updated_by_date')
    search_fields = ['title',]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
            obj.created_by_date = datetime.datetime.now()
        
        obj.updated_by = request.user
        obj.save()

class SuggestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'suggested_by', 'completed']
    search_fields = ['text', 'suggested_by']

class SubmissionAdmin(admin.ModelAdmin):   
    verbose_name = 'Resource Url'
    verbose_name_plural = 'Resource Urls' 
    list_display = ['user', 'sent_date']
    search_fields = ['email_text', 'user']
    readonly_fields = ['user',]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        
        obj.save()

class ODPUserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'can_notify',]
    fieldsets = [(None, {'fields':['user', 'organization', 'can_notify']}),]
    readonly_fields = ['user',]
    list_filter = ['can_notify',]
    
class EntryAdmin(admin.ModelAdmin):
    list_display = ['title', 'nominator', 'contest']
    search_fields = ['title', 'nominator', 'description']
    list_filter = ['contest__title', ]

class EntryInline(admin.StackedInline):
    model = Entry
    extra = 1
    verbose_name_plural = 'Entries'

class ContestAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'end_date']
    search_fields = ['title', 'rules']
    inlines = [EntryInline, ]

class VoteAdmin(admin.ModelAdmin):
    list_display= ['entry', 'user', 'timestamp']
    search_fields = ['entry']
    list_filter = ['entry',]

admin.site.register(Submission, SubmissionAdmin)
admin.site.register(ODPUserProfile, ODPUserProfileAdmin)
admin.site.register(Suggestion, SuggestionAdmin)
admin.site.register(Idea, IdeaAdmin)
admin.site.register(IdeaImage)
admin.site.register(Tag)
admin.site.register(UpdateFrequency)
admin.site.register(UrlType)
admin.site.register(CoordSystem, CoordSystemAdmin)
admin.site.register(DataType)
admin.site.register(Url, UrlAdmin)
admin.site.register(UrlImage, UrlImageAdmin)
admin.site.register(Resource, ResourceAdmin)

admin.site.register(Contest, ContestAdmin)
admin.site.register(Entry, EntryAdmin)
admin.site.register(Vote, VoteAdmin)

admin.site.register(CommentWithRating)


########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings


def get_current_path(request):
    return {'current_path': request.get_full_path(), 'current_host': request.get_host()}

def get_settings(request):
    return {'SITE_ROOT': settings.SITE_ROOT}


########NEW FILE########
__FILENAME__ = feeds
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Rss201rev2Feed as Rss2
from django.shortcuts import get_object_or_404
from OpenDataCatalog.opendata.models import Resource, Tag, Idea

class BaseResourceFeed(Feed):
    feed_type = Rss2

    def item_title(self, item):
        return item.name
    def item_link(self, item):
        return item.get_absolute_url()
    def item_description(self, item):
        return item.short_description
    def item_author_name(self, item):
        return item.organization
    def item_author_email(self, item):
        return item.contact_email
    def item_author_link(self, item):
        return item.contact_url
    def item_categories(self, item):
        return item.tags.all()
    def item_pubdate(self, item):
        return item.created


class ResourcesFeed(BaseResourceFeed):
    title = "OpenDataPhilly.org: Resources - All"
    link = "/feeds/resources/"
    description = "List of resources on OpenDataPhilly.org listed in the order they were added"
    description_template = "feeds/resource.html"
    feed_type = Rss2

    def items(self):
        return Resource.objects.order_by('-created')
    
class UpdatesFeed(BaseResourceFeed):
    title = "OpenDataPhilly.org: Resources - Last Updated"
    link = "/feeds/updates/"
    description = "List of resources on OpenDataPhilly.org listed in the order they were last updated"
    description_template = "feeds/resource.html"
    feed_type = Rss2

    def items(self):
        return Resource.objects.order_by('-last_updated')
    
class IdeasFeed(Feed):
    title = "OpenDataPhilly.org: Ideas"
    link = "/feeds/ideas/"
    description = "List of ideas on OpenDataPhilly.org listed in the order they were added"
    description_template = "feeds/idea.html"
    feed_type = Rss2

    def items(self):
        return Idea.objects.order_by('-created_by_date')
    def item_title(self, item):
        return item.title
    def item_link(self, item):
        return item.get_absolute_url()
    def item_author_name(self, item):
        return item.author
    def item_description(self, item):
        return item.description

class TagFeed(BaseResourceFeed):
    description_template = "feeds/resource.html"
    
    def get_object(self, request, tag_id):
        return get_object_or_404(Tag, pk=tag_id)
    def title(self, obj):
        return "OpenDataPhilly.org: Resources in %s" % obj.tag_name
    def link(self, obj):
        return "/feeds/tag/%i" % obj.id
    def description(self, obj):
        return "Resources with the tag %s in the order they were added" % obj.tag_name

    def items(self, obj):
        return Resource.objects.filter(tags=obj).order_by('-created')
   

########NEW FILE########
__FILENAME__ = forms
from django import forms
from OpenDataCatalog.opendata.models import UpdateFrequency, CoordSystem, UrlType, DataType

class SubmissionForm(forms.Form):
    dataset_name = forms.CharField(max_length=255, label="Data set, API or App name")
    organization = forms.CharField(max_length=255)
    copyright_holder = forms.CharField(max_length=255)
    contact_email = forms.CharField(max_length=255)
    contact_phone = forms.CharField(max_length=255)
    url = forms.CharField(max_length=255, label="Data/API/App url")
    time_period = forms.CharField(required=False, max_length=255, label="Valid time period")
    release_date = forms.DateField(required=False)
    area_of_interest = forms.CharField(max_length=255, label="Geographic area")
    
    update_frequency = forms.ModelChoiceField(required=False, queryset=UpdateFrequency.objects.all())
    coord_system = forms.ModelMultipleChoiceField(required=False, queryset=CoordSystem.objects.all(), label="Coordinate system")
    wkt_geometry = forms.CharField(widget=forms.Textarea, label="Well known Text (WKT) geometry of the dataset")
    types = forms.ModelMultipleChoiceField(required=False, queryset=UrlType.objects.all(), label="Data types")
    formats = forms.ModelMultipleChoiceField(required=False, queryset=DataType.objects.all(), label="Data formats")
    
    description = forms.CharField(max_length=1000, widget=forms.Textarea, label="Describe this dataset")
    usage_limitations = forms.CharField(max_length=1000, widget=forms.Textarea, label="Are there usage limitations?")
    collection_process = forms.CharField(max_length=1000, widget=forms.Textarea, label="How was the data collected?")
    data_purpose = forms.CharField(max_length=1000, widget=forms.Textarea, label="Why was the data collected?")
    intended_audience = forms.CharField(max_length=1000, widget=forms.Textarea, label="Who is the intended audience?")
    why = forms.CharField(max_length=1000, widget=forms.Textarea, label="Why should the data be included in this site?")
    certified = forms.BooleanField(required=False, label="", help_text="I am the copyright holder or have permission to release this data")
    terms = forms.BooleanField(label="", help_text="I have read and agree with the site's <a href='/terms/' target='_blank'>terms of use</a>")
    

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Tag'
        db.create_table('opendata_tag', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('tag_name', self.gf('django.db.models.fields.CharField')(max_length=150)),
        ))
        db.send_create_signal('opendata', ['Tag'])

        # Adding model 'DataType'
        db.create_table('opendata_datatype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('data_type', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('opendata', ['DataType'])

        # Adding model 'UrlType'
        db.create_table('opendata_urltype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url_type', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('opendata', ['UrlType'])

        # Adding model 'UpdateFrequency'
        db.create_table('opendata_updatefrequency', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('update_frequency', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal('opendata', ['UpdateFrequency'])

        # Adding model 'CoordSystem'
        db.create_table('opendata_coordsystem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('EPSG_code', self.gf('django.db.models.fields.IntegerField')(blank=True)),
        ))
        db.send_create_signal('opendata', ['CoordSystem'])

        # Adding model 'Resource'
        db.create_table('opendata_resource', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('short_description', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('release_date', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('time_period', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('organization', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('division', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('usage', self.gf('django.db.models.fields.TextField')()),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('contact_phone', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('contact_email', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('contact_url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('updates', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['opendata.UpdateFrequency'], null=True, blank=True)),
            ('area_of_interest', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('is_published', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='created_by', to=orm['auth.User'])),
            ('last_updated_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='updated_by', to=orm['auth.User'])),
            ('created', self.gf('django.db.models.fields.DateTimeField')()),
            ('last_updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('metadata_contact', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('metadata_notes', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('update_frequency', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('data_formats', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('proj_coord_sys', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('rating_votes', self.gf('django.db.models.fields.PositiveIntegerField')(default=0, blank=True)),
            ('rating_score', self.gf('django.db.models.fields.IntegerField')(default=0, blank=True)),
        ))
        db.send_create_signal('opendata', ['Resource'])

        # Adding M2M table for field tags on 'Resource'
        db.create_table('opendata_resource_tags', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('resource', models.ForeignKey(orm['opendata.resource'], null=False)),
            ('tag', models.ForeignKey(orm['opendata.tag'], null=False))
        ))
        db.create_unique('opendata_resource_tags', ['resource_id', 'tag_id'])

        # Adding M2M table for field data_types on 'Resource'
        db.create_table('opendata_resource_data_types', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('resource', models.ForeignKey(orm['opendata.resource'], null=False)),
            ('datatype', models.ForeignKey(orm['opendata.datatype'], null=False))
        ))
        db.create_unique('opendata_resource_data_types', ['resource_id', 'datatype_id'])

        # Adding M2M table for field coord_sys on 'Resource'
        db.create_table('opendata_resource_coord_sys', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('resource', models.ForeignKey(orm['opendata.resource'], null=False)),
            ('coordsystem', models.ForeignKey(orm['opendata.coordsystem'], null=False))
        ))
        db.create_unique('opendata_resource_coord_sys', ['resource_id', 'coordsystem_id'])

        # Adding model 'Url'
        db.create_table('opendata_url', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('url_label', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('url_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['opendata.UrlType'])),
            ('resource', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['opendata.Resource'])),
        ))
        db.send_create_signal('opendata', ['Url'])

        # Adding model 'UrlImage'
        db.create_table('opendata_urlimage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['opendata.Url'])),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('source_url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal('opendata', ['UrlImage'])

        # Adding model 'Idea'
        db.create_table('opendata_idea', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('author', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='idea_created_by', to=orm['auth.User'])),
            ('created_by_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('updated_by', self.gf('django.db.models.fields.related.ForeignKey')(related_name='idea_updated_by', to=orm['auth.User'])),
            ('updated_by_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('opendata', ['Idea'])

        # Adding M2M table for field resources on 'Idea'
        db.create_table('opendata_idea_resources', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('idea', models.ForeignKey(orm['opendata.idea'], null=False)),
            ('resource', models.ForeignKey(orm['opendata.resource'], null=False))
        ))
        db.create_unique('opendata_idea_resources', ['idea_id', 'resource_id'])

        # Adding model 'IdeaImage'
        db.create_table('opendata_ideaimage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('idea', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['opendata.Idea'])),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('source', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('source_url', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('home_page', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('opendata', ['IdeaImage'])

        # Adding model 'Submission'
        db.create_table('opendata_submission', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('sent_date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('email_text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('opendata', ['Submission'])

        # Adding model 'TwitterCache'
        db.create_table('opendata_twittercache', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('opendata', ['TwitterCache'])

        # Adding model 'ODPUserProfile'
        db.create_table('opendata_odpuserprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('organization', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('can_notify', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
        ))
        db.send_create_signal('opendata', ['ODPUserProfile'])


    def backwards(self, orm):
        # Deleting model 'Tag'
        db.delete_table('opendata_tag')

        # Deleting model 'DataType'
        db.delete_table('opendata_datatype')

        # Deleting model 'UrlType'
        db.delete_table('opendata_urltype')

        # Deleting model 'UpdateFrequency'
        db.delete_table('opendata_updatefrequency')

        # Deleting model 'CoordSystem'
        db.delete_table('opendata_coordsystem')

        # Deleting model 'Resource'
        db.delete_table('opendata_resource')

        # Removing M2M table for field tags on 'Resource'
        db.delete_table('opendata_resource_tags')

        # Removing M2M table for field data_types on 'Resource'
        db.delete_table('opendata_resource_data_types')

        # Removing M2M table for field coord_sys on 'Resource'
        db.delete_table('opendata_resource_coord_sys')

        # Deleting model 'Url'
        db.delete_table('opendata_url')

        # Deleting model 'UrlImage'
        db.delete_table('opendata_urlimage')

        # Deleting model 'Idea'
        db.delete_table('opendata_idea')

        # Removing M2M table for field resources on 'Idea'
        db.delete_table('opendata_idea_resources')

        # Deleting model 'IdeaImage'
        db.delete_table('opendata_ideaimage')

        # Deleting model 'Submission'
        db.delete_table('opendata_submission')

        # Deleting model 'TwitterCache'
        db.delete_table('opendata_twittercache')

        # Deleting model 'ODPUserProfile'
        db.delete_table('opendata_odpuserprofile')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'opendata.coordsystem': {
            'EPSG_code': ('django.db.models.fields.IntegerField', [], {'blank': 'True'}),
            'Meta': {'ordering': "['EPSG_code']", 'object_name': 'CoordSystem'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'opendata.datatype': {
            'Meta': {'ordering': "['data_type']", 'object_name': 'DataType'},
            'data_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'opendata.idea': {
            'Meta': {'object_name': 'Idea'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'idea_created_by'", 'to': "orm['auth.User']"}),
            'created_by_date': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resources': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['opendata.Resource']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'idea_updated_by'", 'to': "orm['auth.User']"}),
            'updated_by_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'opendata.ideaimage': {
            'Meta': {'object_name': 'IdeaImage'},
            'home_page': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'idea': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.Idea']"}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'opendata.odpuserprofile': {
            'Meta': {'object_name': 'ODPUserProfile'},
            'can_notify': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'opendata.resource': {
            'Meta': {'object_name': 'Resource'},
            'area_of_interest': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'contact_email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'contact_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'coord_sys': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['opendata.CoordSystem']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_by'", 'to': "orm['auth.User']"}),
            'data_formats': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'data_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['opendata.DataType']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'division': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'last_updated_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'updated_by'", 'to': "orm['auth.User']"}),
            'metadata_contact': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'metadata_notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'organization': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'proj_coord_sys': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'rating_score': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'rating_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'blank': 'True'}),
            'release_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['opendata.Tag']", 'null': 'True', 'blank': 'True'}),
            'time_period': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'update_frequency': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'updates': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.UpdateFrequency']", 'null': 'True', 'blank': 'True'}),
            'usage': ('django.db.models.fields.TextField', [], {})
        },
        'opendata.submission': {
            'Meta': {'object_name': 'Submission'},
            'email_text': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'opendata.tag': {
            'Meta': {'ordering': "['tag_name']", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'tag_name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'opendata.twittercache': {
            'Meta': {'object_name': 'TwitterCache'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'opendata.updatefrequency': {
            'Meta': {'ordering': "['update_frequency']", 'object_name': 'UpdateFrequency'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'update_frequency': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'opendata.url': {
            'Meta': {'object_name': 'Url'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.Resource']"}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url_label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.UrlType']"})
        },
        'opendata.urlimage': {
            'Meta': {'object_name': 'UrlImage'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.Url']"})
        },
        'opendata.urltype': {
            'Meta': {'ordering': "['url_type']", 'object_name': 'UrlType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['opendata']
########NEW FILE########
__FILENAME__ = 0002_auto__add_field_resource_wkt_geometry__add_field_resource_csw_typename
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Resource.wkt_geometry'
        db.add_column('opendata_resource', 'wkt_geometry',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Resource.csw_typename'
        db.add_column('opendata_resource', 'csw_typename',
                      self.gf('django.db.models.fields.CharField')(default='csw:Record', max_length=200),
                      keep_default=False)

        # Adding field 'Resource.csw_schema'
        db.add_column('opendata_resource', 'csw_schema',
                      self.gf('django.db.models.fields.CharField')(default='http://www.opengis.net/cat/csw/2.0.2', max_length=200),
                      keep_default=False)

        # Adding field 'Resource.csw_mdsource'
        db.add_column('opendata_resource', 'csw_mdsource',
                      self.gf('django.db.models.fields.CharField')(default='local', max_length=100),
                      keep_default=False)

        # Adding field 'Resource.csw_xml'
        db.add_column('opendata_resource', 'csw_xml',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)

        # Adding field 'Resource.csw_anytext'
        db.add_column('opendata_resource', 'csw_anytext',
                      self.gf('django.db.models.fields.TextField')(default='', blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Resource.wkt_geometry'
        db.delete_column('opendata_resource', 'wkt_geometry')

        # Deleting field 'Resource.csw_typename'
        db.delete_column('opendata_resource', 'csw_typename')

        # Deleting field 'Resource.csw_schema'
        db.delete_column('opendata_resource', 'csw_schema')

        # Deleting field 'Resource.csw_mdsource'
        db.delete_column('opendata_resource', 'csw_mdsource')

        # Deleting field 'Resource.csw_xml'
        db.delete_column('opendata_resource', 'csw_xml')

        # Deleting field 'Resource.csw_anytext'
        db.delete_column('opendata_resource', 'csw_anytext')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'opendata.coordsystem': {
            'EPSG_code': ('django.db.models.fields.IntegerField', [], {'blank': 'True'}),
            'Meta': {'ordering': "['EPSG_code']", 'object_name': 'CoordSystem'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'opendata.datatype': {
            'Meta': {'ordering': "['data_type']", 'object_name': 'DataType'},
            'data_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'opendata.idea': {
            'Meta': {'object_name': 'Idea'},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'idea_created_by'", 'to': "orm['auth.User']"}),
            'created_by_date': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resources': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['opendata.Resource']", 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'idea_updated_by'", 'to': "orm['auth.User']"}),
            'updated_by_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'opendata.ideaimage': {
            'Meta': {'object_name': 'IdeaImage'},
            'home_page': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'idea': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.Idea']"}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'opendata.odpuserprofile': {
            'Meta': {'object_name': 'ODPUserProfile'},
            'can_notify': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'organization': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'opendata.resource': {
            'Meta': {'object_name': 'Resource'},
            'area_of_interest': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'contact_email': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'contact_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'coord_sys': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['opendata.CoordSystem']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'created_by'", 'to': "orm['auth.User']"}),
            'csw_anytext': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'csw_mdsource': ('django.db.models.fields.CharField', [], {'default': "'local'", 'max_length': '100'}),
            'csw_schema': ('django.db.models.fields.CharField', [], {'default': "'http://www.opengis.net/cat/csw/2.0.2'", 'max_length': '200'}),
            'csw_typename': ('django.db.models.fields.CharField', [], {'default': "'csw:Record'", 'max_length': '200'}),
            'csw_xml': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'data_formats': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'data_types': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['opendata.DataType']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'division': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'last_updated_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'updated_by'", 'to': "orm['auth.User']"}),
            'metadata_contact': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'metadata_notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'organization': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'proj_coord_sys': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'rating_score': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'rating_votes': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0', 'blank': 'True'}),
            'release_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'tags': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['opendata.Tag']", 'null': 'True', 'blank': 'True'}),
            'time_period': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'update_frequency': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'updates': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.UpdateFrequency']", 'null': 'True', 'blank': 'True'}),
            'usage': ('django.db.models.fields.TextField', [], {}),
            'wkt_geometry': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        'opendata.submission': {
            'Meta': {'object_name': 'Submission'},
            'email_text': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sent_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'opendata.tag': {
            'Meta': {'ordering': "['tag_name']", 'object_name': 'Tag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'tag_name': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'opendata.twittercache': {
            'Meta': {'object_name': 'TwitterCache'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'opendata.updatefrequency': {
            'Meta': {'ordering': "['update_frequency']", 'object_name': 'UpdateFrequency'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'update_frequency': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'opendata.url': {
            'Meta': {'object_name': 'Url'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.Resource']"}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url_label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.UrlType']"})
        },
        'opendata.urlimage': {
            'Meta': {'object_name': 'UrlImage'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'source': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'source_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['opendata.Url']"})
        },
        'opendata.urltype': {
            'Meta': {'ordering': "['url_type']", 'object_name': 'UrlType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url_type': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['opendata']
########NEW FILE########
__FILENAME__ = models
import os
from lxml import etree
from shapely.wkt import loads

from operator import attrgetter
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.db.models.signals import post_save

from sorl.thumbnail.fields import ImageWithThumbnailsField
from djangoratings.fields import RatingField


class Tag(models.Model):
    tag_name = models.CharField(max_length=150)

    def __unicode__(self):
        return '%s' % self.tag_name

    class Meta:
        ordering = ['tag_name']

class DataType(models.Model):
    data_type = models.CharField(max_length=50)

    def __unicode__(self):
        return '%s' % self.data_type

    class Meta:
        ordering = ['data_type']

class UrlType(models.Model):
    url_type = models.CharField(max_length=50)

    def __unicode__(self):
        return '%s' % self.url_type

    class Meta:
        ordering = ['url_type']

class UpdateFrequency(models.Model):
    update_frequency = models.CharField(max_length=50)

    def __unicode__(self):
        return '%s' % self.update_frequency

    class Meta:
        ordering = ['update_frequency']

class CoordSystem(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    EPSG_code = models.IntegerField(blank=True, help_text="Official EPSG code, numbers only")

    def __unicode__(self):
        return '%s, %s' % (self.EPSG_code, self.name)

    class Meta:
        ordering = ['EPSG_code']
        verbose_name = 'Coordinate system'

class Resource(models.Model):
    @classmethod
    def search(cls, qs = None, objs = None):
        if objs == None:
            objs = cls.objects.filter(is_published = True)

        if qs:
            objs = objs.filter(Q(name__icontains=qs) | Q(description__icontains=qs) | Q(organization__icontains=qs) | Q(division__icontains=qs))

        return objs

    def save(self, *args, **kwargs):
        if not self.pk:
            super(Resource, self).save(*args, **kwargs)

        self.csw_xml = self.gen_csw_xml()
        self.csw_anytext = self.gen_csw_anytext()
        super(Resource, self).save(*args, **kwargs)

    # Basic Info
    name = models.CharField(max_length=255)
    short_description = models.CharField(max_length=255)
    release_date = models.DateField(blank=True, null=True)
    time_period = models.CharField(max_length=50, blank=True)
    organization = models.CharField(max_length=255)
    division = models.CharField(max_length=255, blank=True)
    usage = models.TextField()
    tags = models.ManyToManyField(Tag, blank=True, null=True)
    data_types = models.ManyToManyField(DataType, blank=True, null=True)

    # More Info
    description = models.TextField()
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_email = models.CharField(max_length=255, blank=True)
    contact_url = models.CharField(max_length=255, blank=True)

    updates = models.ForeignKey(UpdateFrequency, null=True, blank=True)
    area_of_interest = models.CharField(max_length=255, blank=True)
    is_published = models.BooleanField(default=True, verbose_name="Public")

    created_by = models.ForeignKey(User, related_name='created_by')
    last_updated_by = models.ForeignKey(User, related_name='updated_by')
    created = models.DateTimeField()
    last_updated = models.DateTimeField(auto_now=True)
    metadata_contact = models.CharField(max_length=255, blank=True)
    metadata_notes = models.TextField(blank=True)
    coord_sys = models.ManyToManyField(CoordSystem, blank=True, null=True,  verbose_name="Coordinate system")

    rating = RatingField(range=5, can_change_vote=True)

    update_frequency = models.CharField(max_length=255, blank=True)
    data_formats = models.CharField(max_length=255, blank=True)
    proj_coord_sys = models.CharField(max_length=255, blank=True, verbose_name="Coordinate system")

    # CSW specific properties
    wkt_geometry = models.TextField(blank=True)
    csw_typename = models.CharField(max_length=200,default="csw:Record")
    csw_schema = models.CharField(max_length=200,default="http://www.opengis.net/cat/csw/2.0.2")
    csw_mdsource = models.CharField(max_length=100,default="local")
    csw_xml = models.TextField(blank=True)
    csw_anytext = models.TextField(blank=True)

    def get_distinct_url_types(self):
        types = []
        for url in self.url_set.all():
            if url.url_type not in types:
                types.append(url.url_type)
        return sorted(types, key=attrgetter('url_type'))

    def get_grouped_urls(self):
        urls = {}
        for utype in UrlType.objects.all():
            urls[utype.url_type] = self.url_set.filter(url_type=utype)
        return urls

    def get_first_image(self):
        images = UrlImage.objects.filter(url__resource=self)
        if images.count() == 0:
            return None
        return images[0]

    def get_images(self):
        images = UrlImage.objects.filter(url__resource=self)
        if images.count() == 0:
            return None
        return images

    def get_absolute_url(self):
        slug = slugify(self.name)
        return "/opendata/resource/%i/%s" % (self.id, slug)

    def __unicode__(self):
        return '%s' % self.name

    # CSW specific properties
    @property
    def csw_identifier(self):
        if not settings.SITEHOST:
            raise RuntimeError('settings.SITEHOST is not set')
        fqrhn = '.'.join((reversed(settings.SITEHOST.split('.'))))
        return 'urn:x-odc:resource:%s::%d' % (fqrhn, self.id)

    @property
    def csw_type(self):
        data_types = self.data_types.values()
        if len(data_types) > 0:
            return data_types[0]['data_type']
        return None

    @property
    def csw_crs(self):
        crs = self.coord_sys.values()
        if len(crs) > 0:
            return crs[0]['name']
        return None

    @property
    def csw_links(self):
        links = []
        for url in self.url_set.all():
            tmp = '%s,%s,%s,%s' % (url.url_label, url.url_type.url_type, 'WWW:DOWNLOAD-1.0-http--download', url.url)
            links.append(tmp)
        abs_url = '%s%s' % (gen_website_url(), self.get_absolute_url())
        link = '%s,%s,%s,%s' % (self.name, self.name, 'WWW:LINK-1.0-http--link', abs_url)
        links.append(link)
        return '^'.join(links)

    @property
    def csw_keywords(self):
        keywords = []
        for keyword in self.tags.values():
            keywords.append(keyword['tag_name'])
        return ','.join(keywords)

    @property
    def csw_creator(self):
        creator = User.objects.filter(username=self.created_by)[0]
        return '%s %s' % (creator.first_name, creator.last_name)

    def gen_csw_xml(self):

        def nspath(ns, element):
            return '{%s}%s' % (ns, element)

        nsmap = {
            'csw': 'http://www.opengis.net/cat/csw/2.0.2',
            'dc' : 'http://purl.org/dc/elements/1.1/',
            'dct': 'http://purl.org/dc/terms/',
            'ows': 'http://www.opengis.net/ows',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }

        record = etree.Element(nspath(nsmap['csw'], 'Record'), nsmap=nsmap)
        etree.SubElement(record, nspath(nsmap['dc'], 'identifier')).text = self.csw_identifier
        etree.SubElement(record, nspath(nsmap['dc'], 'title')).text = self.name

        if self.csw_type is not None:
            etree.SubElement(record, nspath(nsmap['dc'], 'type')).text = self.csw_type

        for tag in self.tags.all():
            etree.SubElement(record, nspath(nsmap['dc'], 'subject')).text = tag.tag_name

        etree.SubElement(record, nspath(nsmap['dc'], 'format')).text = str(self.data_formats)

        abs_url = '%s%s' % (gen_website_url(), self.get_absolute_url())
        etree.SubElement(record, nspath(nsmap['dct'], 'references'), scheme='WWW:LINK-1.0-http--link').text = abs_url

        for link in self.url_set.all():
            etree.SubElement(record, nspath(nsmap['dct'], 'references'),
                             scheme='WWW:DOWNLOAD-1.0-http--download').text = link.url

        etree.SubElement(record, nspath(nsmap['dct'], 'modified')).text = str(self.last_updated)
        etree.SubElement(record, nspath(nsmap['dct'], 'abstract')).text = self.description

        etree.SubElement(record, nspath(nsmap['dc'], 'date')).text = str(self.created)
        etree.SubElement(record, nspath(nsmap['dc'], 'creator')).text = str(self.csw_creator)

        etree.SubElement(record, nspath(nsmap['dc'], 'coverage')).text = self.area_of_interest

        try:
            geom = loads(self.wkt_geometry)
            bounds = geom.envelope.bounds
            dimensions = str(geom.envelope._ndim)

            bbox = etree.SubElement(record, nspath(nsmap['ows'], 'BoundingBox'), dimensions=dimensions)

            if self.csw_crs is not None:
                bbox.attrib['crs'] = self.csw_crs

            etree.SubElement(bbox, nspath(nsmap['ows'], 'LowerCorner')).text = '%s %s' % (bounds[1], bounds[0])
            etree.SubElement(bbox, nspath(nsmap['ows'], 'UpperCorner')).text = '%s %s' % (bounds[3], bounds[2])
        except Exception:
            # We can safely ignore geom issues
            pass

        return etree.tostring(record)

    def gen_csw_anytext(self):
        xml = etree.fromstring(self.csw_xml)
        return ' '.join([value.strip() for value in xml.xpath('//text()')])

class Url(models.Model):
    url = models.CharField(max_length=255)
    url_label = models.CharField(max_length=255)
    url_type = models.ForeignKey(UrlType)
    resource = models.ForeignKey(Resource)

    def __unicode__(self):
        return '%s - %s - %s' % (self.url_label, self.url_type, self.url)

class UrlImage(models.Model):
    def get_image_path(instance, filename):
        fsplit = filename.split('.')
        extra = 1
        test_path = os.path.join(settings.MEDIA_ROOT, 'url_images', str(instance.url_id), fsplit[0] + '_' + str(extra) + '.' + fsplit[1])
        while os.path.exists(test_path):
           extra += 1
           test_path = os.path.join(settings.MEDIA_ROOT, 'url_images', str(instance.url_id), fsplit[0] + '_' + str(extra) + '.' +  fsplit[1])
        path = os.path.join('url_images', str(instance.url_id), fsplit[0] + '_' + str(extra) + '.' + fsplit[-1])
        return path

    url = models.ForeignKey(Url)
    image = ImageWithThumbnailsField(upload_to=get_image_path, thumbnail={'size': (80, 80)}, help_text="The site will resize this master image as necessary for page display")
    title = models.CharField(max_length=255, help_text="For image alt tags")
    source = models.CharField(max_length=255, help_text="Source location or person who created the image")
    source_url = models.CharField(max_length=255, blank=True)

    def __unicode__(self):
        return '%s' % (self.image)

class Idea(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    author = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, related_name="idea_created_by")
    created_by_date = models.DateTimeField(verbose_name="Created on")
    updated_by = models.ForeignKey(User, related_name="idea_updated_by")
    updated_by_date = models.DateTimeField(auto_now=True, verbose_name="Updated on")

    resources = models.ManyToManyField(Resource, blank=True, null=True)

    def get_home_page_image(self):
        images = IdeaImage.objects.filter(idea=self)
        home = images.filter(home_page=True)
        if home.count() == 0:
            return images[0]
        return home[0]

    def get_absolute_url(self):
        slug = slugify(self.title)
        return "/idea/%i/%s" % (self.id, slug)

    def __unicode__(self):
        return '%s' % (self.title)


class IdeaImage(models.Model):
    def get_image_path(instance, filename):
        fsplit = filename.split('.')
        extra = 1
        test_path = os.path.join(settings.MEDIA_ROOT, 'idea_images', str(instance.idea_id), fsplit[0] + '_' + str(extra) + '.' + fsplit[1])
        while os.path.exists(test_path):
           extra += 1
           test_path = os.path.join(settings.MEDIA_ROOT, 'idea_images', str(instance.idea_id), fsplit[0] + '_' + str(extra) + '.' +  fsplit[1])
        path = os.path.join('idea_images', str(instance.idea_id), fsplit[0] + '_' + str(extra) + '.' + fsplit[-1])
        return path

    idea = models.ForeignKey(Idea)
    image = ImageWithThumbnailsField(upload_to=get_image_path, thumbnail={'size': (300, 300)}, help_text="The site will resize this master image as necessary for page display")
    title = models.CharField(max_length=255, help_text="For image alt tags")
    source = models.CharField(max_length=255, help_text="Source location or person who created the image")
    source_url = models.CharField(max_length=255, blank=True)
    home_page = models.BooleanField(default=False, help_text="Select this image for use on the home page.")

    def __unicode__(self):
        return '%s' % (self.image)

class Submission(models.Model):
    user = models.ForeignKey(User)
    sent_date = models.DateTimeField(auto_now=True)
    email_text = models.TextField()

class TwitterCache(models.Model):
    text = models.TextField()

class ODPUserProfile(models.Model):
    organization = models.CharField(max_length=255, blank=True)
    can_notify = models.BooleanField(default=False)

    user = models.ForeignKey(User, unique=True)

def gen_website_url():
    if not settings.SITEHOST:
        raise RuntimeError('settings.SITEHOST is not set')
    if not settings.SITEPORT:
        raise RuntimeError('settings.SITEPORT is not set')

    scheme = 'http'
    port = ':%d' % settings.SITEPORT

    if settings.SITEPORT == 443:
        scheme = 'https'
    if settings.SITEPORT == 80:
        port = ''
    return '%s://%s%s' % (scheme, settings.SITEHOST, port)

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
import random
from datetime import datetime
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core import serializers
from django.core.mail import send_mail, mail_managers, EmailMessage
from django.template import RequestContext
from django.template.loader import render_to_string
from django.db.models import Q
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from datetime import datetime
import pytz
from pytz import timezone
from django.core.cache import cache
from models import TwitterCache
import twitter
import simplejson as json

from OpenDataCatalog.opendata.models import *
from OpenDataCatalog.opendata.forms import *

def home(request):
    tweets = cache.get( 'tweets' )

    utc = pytz.utc
    local = timezone('US/Eastern')

    if not tweets and settings.TWITTER_USER:    
        tweets = twitter.Api().GetUserTimeline( settings.TWITTER_USER )[:4]
        if tweets.count < 4:
            tweet_cache = []
            for t in TwitterCache.objects.all():
                tc = json.JSONDecoder().decode(t.text)
                tc['date'] = datetime.strptime( tc['created_at'], "%a %b %d %H:%M:%S +0000 %Y" ).replace(tzinfo=utc).astimezone(local)
                tweet_cache.append(tc)
            tweets = tweet_cache
        else:
            TwitterCache.objects.all().delete()
            for tweet in tweets:
                tweet.date = datetime.strptime( tweet.created_at, "%a %b %d %H:%M:%S +0000 %Y" ).replace(tzinfo=utc).astimezone(local)
                t = TwitterCache(text=tweet.AsJsonString())
                t.save()
            cache.set( 'tweets', tweets, settings.TWITTER_TIMEOUT )
    
    recent = Resource.objects.order_by("-created")[:3]
    idea = Idea.objects.order_by("-created_by_date")[:4]
    if idea.count() > 0:
        ct = idea.count() - 1     
        ran = random.randint(0, ct)
        return render_to_response('home.html', {'recent': recent, 'idea': idea[ran], 'tweets': tweets},  context_instance=RequestContext(request))
    return render_to_response('home.html', {'recent': recent, 'idea': idea, 'tweets': tweets},  context_instance=RequestContext(request))

def results(request):
    resources = Resource.objects.all()
    if 'filter' in request.GET:
        f = request.GET['filter']
        resources = resources.filter(url__url_type__url_type__iexact=f).distinct()
    return render_to_response('results.html', {'results': resources}, context_instance=RequestContext(request))

def thanks(request):
    return render_to_response('thanks.html', context_instance=RequestContext(request))

def tag_results(request, tag_id):
    tag = Tag.objects.get(pk=tag_id)
    tag_resources = Resource.objects.filter(tags=tag)
    if 'filter' in request.GET:
        f = request.GET['filter']
        tag_resources = tag_resources.filter(url__url_type__url_type__icontains=f).distinct()
    
    return render_to_response('results.html', {'results': tag_resources, 'tag': tag}, context_instance=RequestContext(request))

def search_results(request):
    search_resources = Resource.objects.all()
    if 'qs' in request.GET:
        qs = request.GET['qs'].replace("+", " ")
        search_resources = Resource.search(qs, search_resources)
    if 'filter' in request.GET:
        f = request.GET['filter']
        search_resources = search_resources.filter(url__url_type__url_type__iexact=f).distinct()
    
    return render_to_response('results.html', {'results': search_resources}, context_instance=RequestContext(request))

def resource_details(request, resource_id, slug=""):
    resource = get_object_or_404(Resource, pk=resource_id)
    return render_to_response('details.html', {'resource': resource}, context_instance=RequestContext(request)) 
    

def idea_results(request, idea_id=None, slug=""):
    if idea_id:
        idea = Idea.objects.get(pk=idea_id)
        return render_to_response('idea_details.html', {'idea': idea}, context_instance=RequestContext(request)) 
    
    ideas = Idea.objects.order_by("-created_by_date")
    return render_to_response('ideas.html', {'ideas': ideas}, context_instance=RequestContext(request)) 

def feed_list(request):
    tags = Tag.objects.all()
    return render_to_response('feeds/list.html', {'tags': tags}, context_instance=RequestContext(request)) 

@login_required
def suggest_content(request):
    if request.method == 'POST':
        form = SubmissionForm(request.POST)
        if form.is_valid():
            #do something
            
            coords, types, formats, updates ="", "", "", ""
            for c in request.POST.getlist("coord_system"):
                coords = coords + " EPSG:" + CoordSystem.objects.get(pk=c).EPSG_code.__str__()
            for t in request.POST.getlist("types"):
                types = types + " " + UrlType.objects.get(pk=t).url_type
            for f in request.POST.getlist("formats"):
                formats = formats + " " + DataType.objects.get(pk=f).data_type
            for u in request.POST.getlist("update_frequency"):
                if u:
                    updates = updates + " " + UpdateFrequency.objects.get(pk=u).update_frequency
                
            data = {
                "submitter": request.user.username,
                "submit_date": datetime.now(),
                "dataset_name": request.POST.get("dataset_name"),
                "organization": request.POST.get("organization"),
                "copyright_holder": request.POST.get("copyright_holder"),
                "contact_email": request.POST.get("contact_email"),
                "contact_phone": request.POST.get("contact_phone"),
                "url": request.POST.get("url"),
                "time_period": request.POST.get("time_period"),
                "release_date": request.POST.get("release_date"),
                "area_of_interest": request.POST.get("area_of_interest"),
                "update_frequency": updates,
                "coord_system": coords,
                "wkt_geometry": request.POST.get("wkt_geometry"),
                "types": types,
                "formats": formats,
                "usage_limitations": request.POST.get("usage_limitations"),
                "collection_process": request.POST.get("collection_process"),
                "data_purpose": request.POST.get("data_purpose"),
                "intended_audience": request.POST.get("intended_audience"),
                "why": request.POST.get("why"),
            }
            
            
            send_email(request.user, data)
            return render_to_response('thanks.html', context_instance=RequestContext(request))
    else: 
        form = SubmissionForm()
        
    return render_to_response('submit.html', {'form': form}, context_instance=RequestContext(request))

def send_email(user, data):
    subject, user_email = 'OpenDataPhilly - Data Submission', (user.first_name + " " + user.last_name, user.email)
    text_content = render_to_string('submit_email.txt', data)
    text_content_copy = render_to_string('submit_email_copy.txt', data)

    mail_managers(subject, text_content)
    
    msg = EmailMessage(subject, text_content_copy, to=user_email)
    msg.send()
    
    sug_object = Submission()
    sug_object.user = user
    sug_object.email_text = text_content
    
    sug_object.save()

    return sug_object



## views called by js ajax for object lists
def get_tag_list(request):
    tags = Tag.objects.all()
    return HttpResponse(serializers.serialize("json", tags)) 

########NEW FILE########
__FILENAME__ = fields
from django.conf import settings
from django import forms
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _

from widgets import *
from recaptcha.client import captcha

class ReCaptchaField(forms.CharField):
    default_error_messages = {
        'captcha_invalid': _(u'Invalid captcha')
    }

    def __init__(self, *args, **kwargs):
        self.widget = ReCaptcha
        self.required = True
        super(ReCaptchaField, self).__init__(*args, **kwargs)

    def clean(self, values):
        super(ReCaptchaField, self).clean(values[1])
        recaptcha_challenge_value = smart_unicode(values[0])
        recaptcha_response_value = smart_unicode(values[1])
        check_captcha = captcha.submit(recaptcha_challenge_value, 
            recaptcha_response_value, settings.RECAPTCHA_PRIVATE_KEY, {})
        if not check_captcha.is_valid:
            raise forms.util.ValidationError(self.error_messages['captcha_invalid'])
        return values[0]

########NEW FILE########
__FILENAME__ = widgets
from django import forms
from django.utils.safestring import mark_safe
from django.conf import settings
from recaptcha.client import captcha

class ReCaptcha(forms.widgets.Widget):
    recaptcha_challenge_name = 'recaptcha_challenge_field'
    recaptcha_response_name = 'recaptcha_response_field'

    def render(self, name, value, attrs=None):
        return mark_safe(u'%s' % captcha.displayhtml(settings.RECAPTCHA_PUBLIC_KEY))

    def value_from_datadict(self, data, files, name):
        return [data.get(self.recaptcha_challenge_name, None), 
            data.get(self.recaptcha_response_name, None)]

########NEW FILE########
__FILENAME__ = settings
import os
# Django settings for opendata project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
     ('OpenData Admins', 'admin@example.org'),
)
CONTACT_EMAILS = ['admin@example.org',]
DEFAULT_FROM_EMAIL = 'OpenData Team <info@example.org>'
EMAIL_SUBJECT_PREFIX = '[OpenData.org] '
SERVER_EMAIL = 'OpenData Team <info@example.org>'

MANAGERS = (
     ('OpenData Team', 'info@example.org'),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'catalog',                      # Or path to database file if using sqlite3.
        'USER': 'catalog',                      # Not used with sqlite3.
        'PASSWORD': 'passw0rd',                  # Not used with sqlite3.
        'HOST': '',                      # Set to 'localhost' for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media/')
ADMIN_MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'admin_media/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static/')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

STATIC_DATA = os.path.join(os.path.dirname(__file__), 'static/')

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
#ADMIN_MEDIA_PREFIX = '/hidden/static/admin_media/'
ADMIN_MEDIA_PREFIX = '/static/admin/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

### Package settings
ACCOUNT_ACTIVATION_DAYS = 7
TWITTER_TIMEOUT = 6000
THUMBNAIL_EXTENSION = 'png'
PAGINATION_DEFAULT_WINDOW = 2
###

COMMENTS_APP = 'OpenDataCatalog.comments'

AUTH_PROFILE_MODULE = 'opendata.odpuserprofile'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.request",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",

    "OpenDataCatalog.opendata.context_processors.get_current_path",
    "OpenDataCatalog.opendata.context_processors.get_settings",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django_sorting.middleware.SortingMiddleware',
    'pagination.middleware.PaginationMiddleware',
)

ROOT_URLCONF = 'OpenDataCatalog.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.comments',
    'django.contrib.flatpages',
    'django.contrib.sitemaps',
    'django.contrib.humanize',
    'south',
    'OpenDataCatalog.opendata',
    'registration',
    'sorl.thumbnail',
    'pagination',
    'django_sorting',
    'djangoratings',
    'OpenDataCatalog.comments',
    'OpenDataCatalog.suggestions',
    'OpenDataCatalog.contest',
    'OpenDataCatalog.catalog',

)

# the hostname of the deployment
SITEHOST = None
# the port which the deployment runs on
SITEPORT = None

# pycsw configuration
CSW = {
    'metadata:main': {
        'identification_title': 'Open Data Catalog CSW',
        'identification_abstract': 'Open Data Catalog is an open data catalog based on Django, Python and PostgreSQL. It was originally developed for OpenDataPhilly.org, a portal that provides access to open data sets, applications, and APIs related to the Philadelphia region. The Open Data Catalog is a generalized version of the original source code with a simple skin. It is intended to display information and links to publicly available data in an easily searchable format. The code also includes options for data owners to submit data for consideration and for registered public users to nominate a type of data they would like to see openly available to the public.',
        'identification_keywords': 'odc,Open Data Catalog,catalog,discovery',
        'identification_keywords_type': 'theme',
        'identification_fees': 'None',
        'identification_accessconstraints': 'None',
        'provider_name': ADMINS[0][0],
        'provider_url': 'https://github.com/azavea/Open-Data-Catalog',
        'contact_name': ADMINS[0][0],
        'contact_position': ADMINS[0][0],
        'contact_address': 'TBA',
        'contact_city': 'City',
        'contact_stateorprovince': 'State',
        'contact_postalcode': '12345',
        'contact_country': 'United States of America',
        'contact_phone': '+01-xxx-xxx-xxxx',
        'contact_fax': '+01-xxx-xxx-xxxx',
        'contact_email': ADMINS[0][1],
        'contact_url': 'https://github.com/azavea/Open-Data-Catalog/',
        'contact_hours': '0800h - 1600h EST',
        'contact_instructions': 'During hours of service.  Off on weekends.',
        'contact_role': 'pointOfContact',
    },
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}

try:
    from local_settings import *
except Exception:
    pass

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    LOCAL_STATICFILE_DIR,
    os.path.abspath(os.path.join(os.path.dirname(__file__),
                                 'opendata/static')),
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    LOCAL_TEMPLATE_DIR,
    os.path.join(os.path.dirname(__file__), 'templates')
)

LOGIN_URL = SITE_ROOT + "/accounts/login/"

########NEW FILE########
__FILENAME__ = forms
from django import forms

from OpenDataCatalog.suggestions.models import *

class SuggestionForm(forms.Form):
    text = forms.CharField(widget=forms.Textarea(), max_length=255, label="My Nomination")
    

########NEW FILE########
__FILENAME__ = models
import os
from operator import attrgetter
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

from sorl.thumbnail.fields import ImageWithThumbnailsField
from djangoratings.fields import RatingField
from OpenDataCatalog.opendata.models import Resource

class Suggestion(models.Model):
    text = models.CharField(max_length=255)
    suggested_by = models.ForeignKey(User, related_name="suggested_by")
    suggested_date = models.DateTimeField(auto_now_add=True)
    last_modified_date = models.DateTimeField(auto_now=True)
    completed = models.BooleanField(default=False)
    
    rating = RatingField(range=1, allow_delete=True, can_change_vote=True)

    resources = models.ManyToManyField(Resource, related_name="resources_added", null=True, blank=True)

    def __unicode__(self):
        return '%s' % self.text


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
   (r'^$', 'OpenDataCatalog.suggestions.views.list_all'),
   (r'^post/$', 'OpenDataCatalog.suggestions.views.add_suggestion'),
   (r'^vote/(?P<suggestion_id>.*)/$', 'OpenDataCatalog.suggestions.views.add_vote'),
   (r'^unvote/(?P<suggestion_id>.*)/$', 'OpenDataCatalog.suggestions.views.remove_vote'),
   (r'^close/(?P<suggestion_id>.*)/$', 'OpenDataCatalog.suggestions.views.close'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required

from OpenDataCatalog.suggestions.models import *
from OpenDataCatalog.suggestions.forms import *

def list_all(request):
    suggestions = Suggestion.objects.order_by("-rating_score")
    if 'nqs' in request.GET:
        qs = request.GET['nqs'].replace("+", " ")
        suggestions = suggestions.filter(text__icontains=qs)
    if 'filter' in request.GET:
        try:
            f = request.GET['filter']
            if f == 'mine':
                user = User.objects.get(username=request.user)
                for s in suggestions:
                    voted = s.rating.get_rating_for_user(user=user, ip_address=request.META['REMOTE_ADDR'])
                    if not voted:
                        suggestions = suggestions.exclude(pk=s.id)
            if f == 'done':                  
                suggestions = suggestions.exclude(completed=False)
                
        except:
            pass    

    form = SuggestionForm()
    return render_to_response('suggestions/list.html', {'suggestions': suggestions, 'form': form}, context_instance=RequestContext(request))

@login_required
def add_suggestion(request):
    if request.method == 'POST':
        form = SuggestionForm(request.POST)
        if form.is_valid():

            sug = Suggestion()
            sug.suggested_by = request.user
            sug.text = request.POST.get('text')
            
            sug.save()            
            sug.rating.add(score=1, user=request.user, ip_address=request.META['REMOTE_ADDR'])
            
            return HttpResponseRedirect('../?sort=suggested_date&dir=desc&filter=mine')
    else: 
        form = SuggestionForm()

    suggestions = Suggestion.objects.order_by("rating_score")
    return render_to_response('suggestions/list.html', {'suggestions': suggestions, 'form': form}, context_instance=RequestContext(request))

@login_required
def add_vote(request, suggestion_id):
    suggestion = Suggestion.objects.get(pk=suggestion_id)
    did_vote = suggestion.rating.get_rating_for_user(request.user, request.META['REMOTE_ADDR'])
    if did_vote == None:
        suggestion.rating.add(score=1, user=request.user, ip_address=request.META['REMOTE_ADDR'])
    return HttpResponseRedirect('../../')

@login_required
def remove_vote(request, suggestion_id):    
    suggestion = Suggestion.objects.get(pk=suggestion_id)
    suggestion.rating.delete(request.user, request.META['REMOTE_ADDR'])
    return HttpResponseRedirect('../../')

@login_required
def close(request, suggestion_id):
    suggestion = Suggestion.objects.get(pk=suggestion_id)
    suggestion.completed = True;
    suggestion.save()
    return HttpResponseRedirect('../../')



########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.contrib.sitemaps import FlatPageSitemap, GenericSitemap
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from OpenDataCatalog.opendata.feeds import ResourcesFeed, TagFeed, IdeasFeed, UpdatesFeed
from OpenDataCatalog.opendata.models import Resource, Idea
from OpenDataCatalog.registration_backend import CatalogRegistrationView

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

sitemaps = {
    'flatpages': FlatPageSitemap,
    'resources': GenericSitemap({'queryset': Resource.objects.all(), 'date_field': 'created'}, priority=0.5),
    'ideas': GenericSitemap({'queryset': Idea.objects.all(), 'date_field': 'created_by_date'}, priority=0.5),
}

urlpatterns = patterns('',
    # Examples:
    (r'^$', 'OpenDataCatalog.opendata.views.home'),
    (r'^opendata/$', 'OpenDataCatalog.opendata.views.results'),
    
    (r'^opendata/tag/(?P<tag_id>\d+)/$', 'OpenDataCatalog.opendata.views.tag_results'),
    (r'^opendata/search/$', 'OpenDataCatalog.opendata.views.search_results'),
    (r'^opendata/resource/(?P<resource_id>\d+)/$', 'OpenDataCatalog.opendata.views.resource_details'),
    (r'^opendata/resource/(?P<resource_id>\d+)/(?P<slug>[-\w]+)/$', 'OpenDataCatalog.opendata.views.resource_details'),
    (r'^ideas/$', 'OpenDataCatalog.opendata.views.idea_results'),
    (r'^idea/(?P<idea_id>\d+)/$', 'OpenDataCatalog.opendata.views.idea_results'),
    (r'^idea/(?P<idea_id>\d+)/(?P<slug>[-\w]+)/$', 'OpenDataCatalog.opendata.views.idea_results'),
    (r'^opendata/submit/$', 'OpenDataCatalog.opendata.views.suggest_content'),
    (r'^thanks/$', 'OpenDataCatalog.opendata.views.thanks'),   
    
    (r'^tags/$', 'OpenDataCatalog.opendata.views.get_tag_list'),
    
    (r'^comments/', include('django.contrib.comments.urls')),
    url(r'^accounts/register/$', CatalogRegistrationView.as_view(), name='registration_register'),
    (r'^accounts/password_reset', 'django.contrib.auth.views.password_reset'),
    (r'^accounts/', include('registration.backends.default.urls')),
    (r'^opendata/nominate/', include('OpenDataCatalog.suggestions.urls')),

    (r'^contest/$', 'OpenDataCatalog.contest.views.get_entries'),
    (r'^contest/rules/$', 'OpenDataCatalog.contest.views.get_rules'),
    (r'^contest/add/$', 'OpenDataCatalog.contest.views.add_entry'),
    (r'^contest/entry/(?P<entry_id>\d+)/$', 'OpenDataCatalog.contest.views.get_entry'),
    (r'^contest/entry/(?P<entry_id>\d+)/vote/$', 'OpenDataCatalog.contest.views.add_vote'),
    (r'^contest/entries/$', 'OpenDataCatalog.contest.views.get_entries_table'),
    (r'^contest/winners/$', 'OpenDataCatalog.contest.views.get_winners'),

    (r'^feeds/$', 'OpenDataCatalog.opendata.views.feed_list'),
    (r'^feeds/resources/$', ResourcesFeed()),
    (r'^feeds/updates/$', UpdatesFeed()),
    (r'^feeds/ideas/$', IdeasFeed()),
    (r'^feeds/tag/(?P<tag_id>\d+)/$', TagFeed()),
    (r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    (r'^robots\.txt$', TemplateView.as_view(template_name='robots.txt')),
    
    # API urls (all are GET urls unless stated otherwise)
    (r'^api/resources/$', 'OpenDataCatalog.api.views.resources'),
    (r'^api/resources/(?P<resource_id>\d+)/$', 'OpenDataCatalog.api.views.resource'),                 
    (r'^api/resources/search$', 'OpenDataCatalog.api.views.resource_search'),
    (r'^api/tags/$', 'OpenDataCatalog.api.views.tags'),                       
    (r'^api/tags/(?P<tag_name>.*)/$', 'OpenDataCatalog.api.views.by_tag'),
    (r'^api/ideas/$', 'OpenDataCatalog.api.views.ideas'),
    (r'^api/ideas/(?P<idea_id>\d+)/$', 'OpenDataCatalog.api.views.idea'),
    # GET to list, POST to created
    (r'^api/suggestions/$', 'OpenDataCatalog.api.views.suggestions'),
    (r'^api/suggestions/search$', 'OpenDataCatalog.api.views.search_suggestions'),
    (r'^api/suggestions/(?P<suggestion_id>\d+)/$', 'OpenDataCatalog.api.views.suggestion'),
    # PUT to vote, DELETE to remove
    (r'^api/suggestions/(?P<suggestion_id>\d+)/vote$', 'OpenDataCatalog.api.views.vote'),
    # POST to create
    (r'^api/submit/$', 'OpenDataCatalog.api.views.submit'),

    url(r'^catalog/', include("OpenDataCatalog.catalog.urls")),
    url(r'^data.json$', "OpenDataCatalog.catalog.views.data_json"),

    # Uncomment the next line to enable the admin:
    url(r'^_admin_/', include(admin.site.urls)),

) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
