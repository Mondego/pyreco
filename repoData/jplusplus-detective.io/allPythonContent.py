__FILENAME__ = admin
from app.detective        import utils
from app.detective.models import QuoteRequest, Topic, SearchTerm, Article
from django.conf          import settings
from django.contrib       import admin
from django.db.models     import CharField

class QuoteRequestAdmin(admin.ModelAdmin):
    save_on_top   = True
    list_filter   = ("employer", "records", "users", "public", )
    search_fields = ("name", "employer", "domain", "email", "comment",)

admin.site.register(QuoteRequest, QuoteRequestAdmin)

# Display relationship admin panel only on debug mode
if settings.DEBUG:
    class SearchTermAdmin(admin.ModelAdmin):
        list_display  = ("name", "label", "subject", "topic", "is_literal",)
    admin.site.register(SearchTerm, SearchTermAdmin)


class SearchTermInline(admin.TabularInline):
    model  = SearchTerm
    extra  = 0

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'name':
            # We add temporary choices for this field so
            # it will be threaded as a selectbox
            choices = ( (None, "Will be replaced"), )
            db_field = CharField(
                name=db_field.name,
                verbose_name=db_field.verbose_name,
                primary_key=db_field.primary_key,
                max_length=db_field.max_length,
                blank=db_field.blank,
                rel=db_field.rel,
                default=db_field.default,
                editable=db_field.editable,
                serialize=db_field.serialize,
                unique_for_date=db_field.unique_for_date,
                unique_for_year=db_field.unique_for_year,
                help_text=db_field.help_text,
                db_column=db_field.db_column,
                db_tablespace=db_field.db_tablespace,
                auto_created=db_field.auto_created,
                db_index=db_field.db_index,
                validators=db_field.validators,
                # The ony field we don't copy
                choices=choices
            )

        return super(SearchTermInline, self).formfield_for_dbfield(db_field, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'name' and hasattr(request, "topic_id"):
            # We add choices for this field using the current topic's models
            kwargs["choices"] = []
            # Get the current topic with the ID set into the parent form
            topic  = Topic.objects.get(id=request.topic_id)
            # Get the topic's models
            models = topic.get_models()
            for model in models:
                model_name    = getattr(model._meta, "verbose_name").title()
                subset        = []
                # Retreive every relationship field for this model
                for field in utils.get_model_fields(model):
                    if field["type"] != 'AutoField':
                        choice   = [ field["name"], field["verbose_name"].title(), ]
                        # Add ... at the end ot the relationship field
                        if field["type"] == 'Relationship': choice[1] += "..."
                        subset.append(choice)
                # Add the choice subset only if it contains elements
                if len(subset): kwargs["choices"].append( (model_name, subset,) )
        return super(SearchTermInline, self).formfield_for_choice_field(db_field, request,**kwargs)

class TopicAdmin(admin.ModelAdmin):
    save_on_top         = True
    prepopulated_fields = {'slug': ('title',)}
    list_display        = ("title", "link", "public",)
    fieldsets = (
        (None, {
            'fields':  ( ('title', 'slug',), 'ontology', 'module', ('public', 'author'))
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ( 'description', 'about', 'background', )
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        if hasattr(obj, "id"):
            # Save the topic id into the request to retreive it into inline form
            setattr(request, 'topic_id', obj.id)
            # Add inlice SearchTerm only for saved object
            self.inlines = (SearchTermInline,)
        else:
            self.inlines = []
        return super(TopicAdmin, self).get_form(request, obj, **kwargs)


admin.site.register(Topic, TopicAdmin)

class ArticleAdmin(admin.ModelAdmin):
    save_on_top         = True
    prepopulated_fields = {'slug': ('title',)}
    list_display        = ("title", "link", "created_at", "public", )

admin.site.register(Article, ArticleAdmin)
########NEW FILE########
__FILENAME__ = compress_filter
from compressor.filters.css_default import CssAbsoluteFilter
from compressor.utils import staticfiles


class CustomCssAbsoluteFilter(CssAbsoluteFilter):
    def find(self, basename):
        # The line below is the original line.  I removed settings.DEBUG.
        # if settings.DEBUG and basename and staticfiles.finders:
        if basename and staticfiles.finders:
            return staticfiles.finders.find(basename)
########NEW FILE########
__FILENAME__ = individual
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app.detective                      import register
from app.detective.neomatch             import Neomatch
from app.detective.utils                import import_class, to_underscores, get_model_topic
from django.conf.urls                   import url
from django.core.exceptions             import ObjectDoesNotExist
from django.core.paginator              import Paginator, InvalidPage
from django.core.urlresolvers           import reverse
from django.db.models.query             import QuerySet
from django.http                        import Http404
from neo4django.db                      import connection
from neo4django.db.models.properties    import DateProperty
from neo4django.db.models.relationships import MultipleNodes
from tastypie                           import fields
from tastypie.authentication            import Authentication, SessionAuthentication, BasicAuthentication, MultiAuthentication
from tastypie.authorization             import Authorization
from tastypie.constants                 import ALL
from tastypie.exceptions                import Unauthorized
from tastypie.resources                 import ModelResource
from tastypie.serializers               import Serializer
from tastypie.utils                     import trailing_slash
from datetime                           import datetime
from collections                        import defaultdict
import json
import re
import copy

# inspired from django.utils.formats.ISO_FORMATS['DATE_INPUT_FORMATS'][1]
RFC_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

class IndividualAuthorization(Authorization):

    def check_contribution_permission(self, object_list, bundle, operation):
        authorized = False
        user = bundle.request.user
        if user:
            perm_name  = "%s.contribute_%s" % (object_list._app_label, operation)
            authorized = user.is_staff or user.has_perm(perm_name)
        return authorized

    def read_detail(self, object_list, bundle):
        return True

    def create_detail(self, object_list, bundle):
        if not self.check_contribution_permission(object_list, bundle, 'add'):
            raise Unauthorized("Sorry, only staff or contributors can create resource.")
        return True

    def update_detail(self, object_list, bundle):
        if not self.check_contribution_permission(object_list, bundle, 'change'):
            raise Unauthorized("Sorry, only staff or contributors can update resource.")
        return True

    def delete_detail(self, object_list, bundle):
        if not self.check_contribution_permission(object_list, bundle, 'delete'):
            raise Unauthorized("Sorry, only staff or contributors can delete resource.")
        return True

    def delete_list(self, object_list, bundle):
        return False
        # if not self.check_contribution_permission(object_list, bundle, 'delete'):
        #     raise Unauthorized("Sorry, only staff or contributors can delete resource.")
        # return True

class IndividualMeta:
    list_allowed_methods   = ['get', 'post', 'put']
    detail_allowed_methods = ['get', 'post', 'delete', 'put', 'patch']
    always_return_data     = True
    authorization          = IndividualAuthorization()
    authentication         = MultiAuthentication(Authentication(), BasicAuthentication(), SessionAuthentication())
    filtering              = {'name': ALL}
    ordering               = {'name': ALL}
    serializer             = Serializer(formats=['json', 'jsonp', 'xml', 'yaml'])

class IndividualResource(ModelResource):

    def __init__(self, api_name=None):
        super(IndividualResource, self).__init__(api_name)
        # Register relationships fields automaticly
        self.generate_to_many_fields(True)

    def apply_sorting(self, obj_list, options=None):
        options_copy = options.copy()
        # No failling sorting,
        if "order_by" in options and not options["order_by"] in self.fields:
            # remove invalid order_by key
            options_copy.pop("order_by", None)
        return super(IndividualResource, self).apply_sorting(obj_list, options_copy)


    def build_schema(self):
        """
        Description and scope for each Resource
        """
        schema = super(IndividualResource, self).build_schema()
        model  = self._meta.queryset.model

        additionals = {
            "description": getattr(model, "_description", None),
            "scope"      : getattr(model, "_scope", None)
        }
        return dict(additionals.items() + schema.items())

    def get_queryset(self):
        # Resource must implement a queryset!
        queryset = getattr(self._meta, "queryset", None)
        if not isinstance(queryset, QuerySet):
            raise Exception("The given resource must define a queryset.")
        return queryset

    def get_model(self):
        return self.get_queryset().model

    def get_model_fields(self):
        # Find fields of the queryset's model
        return self.get_model()._meta.fields

    def get_model_field(self, name):
        target = None
        for field in self.get_model_fields():
            if field.name == name:
                target = field
        return target

    def need_to_many_field(self, field):
        # Limit the definition of the new fields
        # to the relationships
        if isinstance(field, MultipleNodes) and not field.name.endswith("_set"):
            # The resource already define a field for this one
            # resource_field = self.fields[field.name]
            # But it's probably still a charfield !
            # And it's so bad.
            # if isinstance(resource_field, fields.CharField):
            return True
        # Return false if not needed
        return False

    # TODO: Find another way!
    def dummy_class_to_ressource(self, klass):
        module = klass.__module__.split(".")
        # Remove last path part if need
        if module[-1] == 'models': module = module[0:-1]
        # Build the resource path
        module = ".".join(module + ["resources", klass.__name__ + "Resource"])
        try:
            # Try to import the class
            import_class(module)
            return module
        except ImportError:
            return None

    def get_to_many_field(self, field, full=False):
        if type(field.target_model) == str:
            target_model = import_class(field.target_model)
        else:
            target_model = field.target_model
        resource = self.dummy_class_to_ressource(target_model)
        # Do not create a relationship with an empty resource (not resolved)
        if resource: return fields.ToManyField(resource, field.name, full=full, null=True, use_in=self.use_in)
        else: return None

    def generate_to_many_fields(self, full=False):
        # For each model field
        for field in self.get_model_fields():
            # Limit the definition of the new fields
            # to the relationships
            if self.need_to_many_field(field):
                f = self.get_to_many_field(field, full=bool(full))
                # Get the full relationship
                if f: self.fields[field.name] = f

    def _build_reverse_url(self, name, args=None, kwargs=None):
        # This ModelResource respects Django namespaces.
        # @see tastypie.resources.NamespacedModelResource
        # @see tastypie.api.NamespacedApi
        namespaced = "%s:%s" % (self._meta.urlconf_namespace, name)
        return reverse(namespaced, args=args, kwargs=kwargs)

    def use_in(self, bundle=None):
        # Use in post/put
        if bundle.request.method in ['POST', 'PUT']:
            return bundle.request.path == self.get_resource_uri()
        # Use in detail
        else:
            return self.get_resource_uri(bundle) == bundle.request.path

    def get_detail(self, request, **kwargs):
        # Register relationships fields automaticly with full detail
        self.generate_to_many_fields(True)
        return super(IndividualResource, self).get_detail(request, **kwargs)

    def get_list(self, request, **kwargs):
        # Register relationships fields automaticly with full detail
        self.generate_to_many_fields(False)
        return super(IndividualResource, self).get_list(request, **kwargs)

    def alter_detail_data_to_serialize(self, request, bundle):
        # Show additional field following the model's rules
        rules = register.topics_rules().model(self.get_model()).all()
        # All additional relationships
        for key in rules:
            # Filter rules to keep only Neomatch
            if isinstance(rules[key], Neomatch):
                bundle.data[key] = rules[key].query(bundle.obj.id)

        return bundle

    def dehydrate(self, bundle):
        # Show additional field following the model's rules
        rules = register.topics_rules().model( self.get_model() )
        # Get the output transformation for this model
        transform = rules.get("transform")
        # This is just a string
        # For complex formating use http://docs.python.org/2/library/string.html#formatspec
        if type(transform) is str:
            transform = transform.format(**bundle.data)
        # We can also receive a function
        elif callable(transform):
            transform = transform(bundle.data)

        bundle.data["_transform"] = transform or getattr(bundle.data, 'name', None)
        # Control that every relationship fields are list
        # and that we didn't send hidden field
        for field in bundle.data:
            # Find the model's field
            modelField = getattr(bundle.obj, field, False)
            # The current field is a relationship
            if modelField and hasattr(modelField, "_rel"):
                # Wrong type given, relationship field must ouput a list
                if type(bundle.data[field]) is not list:
                    # We remove the field from the ouput
                    bundle.data[field] = []
            # The field is a list of literal values
            elif type(modelField) in (list, tuple):
                # For tuple serialization
                bundle.data[field] = modelField
            # Get the output transformation for this field
            transform = rules.field(field).get("transform")
            # This is just a string
            # For complex formating use http://docs.python.org/2/library/string.html#formatspec
            if type(transform) is str:
                bundle.data[field] = transform.format(**bundle.data)
            # We can also receive a function
            elif callable(transform):
                bundle.data[field] = transform(bundle.data, field)

        return bundle

    def hydrate(self, bundle):
        # Convert author to set to avoid duplicate
        bundle.obj._author = set(bundle.obj._author)
        bundle.obj._author.add(bundle.request.user.id)
        bundle.obj._author = list(bundle.obj._author)
        # Avoid try to insert automatic relationship
        for name in bundle.data:
            if name.endswith("_set"): bundle.data[name] = []
        return bundle

    def hydrate_m2m(self, bundle):
        # By default, every individual from staff are validated
        bundle.data["_status"] = 1*bundle.request.user.is_staff

        for field in bundle.data:
            # Find the model's field
            modelField = getattr(bundle.obj, field, False)
            # The current field is a relationship
            if modelField and hasattr(modelField, "_rel"):
                # Model associated to that field
                model = modelField._rel.relationship.target_model
                # Wrong type given
                if type(bundle.data[field]) is not list:
                    # Empty the field that contain bad
                    bundle.data[field] = []
                # Transform list field to be more flexible
                elif len(bundle.data[field]):
                    rels = []
                    # For each relation...
                    for rel in bundle.data[field]:
                        # Keeps the string
                        if type(rel) is str:
                            rels.append(rel)
                        # Convert object with id to uri
                        elif type(rel) is int:
                            obj = model.objects.get(id=rel)
                        elif "id" in rel:
                            obj = model.objects.get(id=rel["id"])
                        else:
                            obj = False
                        # Associated the existing object
                        if obj: rels.append(obj)

                    bundle.data[field] = rels
        return bundle

    def save_m2m(self, bundle):
        for field in bundle.data:
            # Find the model's field
            modelField = getattr(bundle.obj, field, False)
            # The field doesn't exist
            if not modelField: setattr(bundle.obj, field, None)
            # Transform list field to be more flexible
            elif type(bundle.data[field]) is list:
                rels = bundle.data[field]
                # Avoid working on empty relationships set
                if len(rels) > 0:
                    # Empties the bundle to avoid insert data twice
                    bundle.data[field] = []
                    # Get the field
                    attr = getattr(bundle.obj, field)
                    # Clean the field to avoid duplicates
                    if attr.count() > 0: attr.clear()
                    # For each relation...
                    for rel in rels:
                        # Add the received obj
                        if hasattr(rel, "obj"):
                            attr.add(rel.obj)
                        else:
                            attr.add(rel)

        # Save the object now to avoid duplicated relations
        bundle.obj.save()

        return bundle

    def prepend_urls(self):
        params = (self._meta.resource_name, trailing_slash())
        return [
            url(r"^(?P<resource_name>%s)/search%s$" % params, self.wrap_view('get_search'), name="api_get_search"),
            url(r"^(?P<resource_name>%s)/mine%s$" % params, self.wrap_view('get_mine'), name="api_get_mine"),
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/patch%s$" % params, self.wrap_view('get_patch'), name="api_get_patch"),
            url(r"^(?P<resource_name>%s)/bulk_upload%s$" % params, self.wrap_view('bulk_upload'), name="api_bulk_upload"),
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/graph%s$" % params, self.wrap_view('get_graph'), name="api_get_graph"),
        ]


    def get_search(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.throttle_check(request)

        query     = request.GET.get('q', '').lower()
        query     = re.sub("\"|'|`|;|:|{|}|\|(|\|)|\|", '', query).strip()
        limit     = int(request.GET.get('limit', 20))
        # Do the query.
        results   = self._meta.queryset.filter(name__icontains=query)
        count     = len(results)
        paginator = Paginator(results, limit)

        try:
            p     = int(request.GET.get('page', 1))
            page  = paginator.page(p)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []

        for result in page.object_list:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle, for_list=True)
            objects.append(bundle)

        object_list = {
            'objects': objects,
            'meta': {
                'q': query,
                'page': p,
                'limit': limit,
                'total_count': count
            }
        }

        self.log_throttled_access(request)
        return self.create_response(request, object_list)

    def get_mine(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        # Do the query.
        limit     = int(request.GET.get('limit', 20))
        results   = self._meta.queryset.filter(_author__contains=request.user.id)
        count     = len(results)
        paginator = Paginator(results, limit)

        try:
            p     = int(request.GET.get('page', 1))
            page  = paginator.page(p)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []

        for result in page.object_list:
            bundle = self.build_bundle(obj=result, request=request)
            bundle = self.full_dehydrate(bundle, for_list=True)
            objects.append(bundle)

        object_list = {
            'objects': objects,
            'meta': {
                'author': request.user,
                'page': p,
                'limit': limit,
                'total_count': count
            }
        }

        self.log_throttled_access(request)
        return self.create_response(request, object_list)

    def get_patch(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        #self.is_authenticated(request)
        self.throttle_check(request)
        self.is_authenticated(request)
        bundle = self.build_bundle(request=request)
        self.authorized_update_detail(self.get_object_list(bundle.request), bundle)
        model = self.get_model()
        try:
            node = model.objects.get(id=kwargs["pk"])
        except ObjectDoesNotExist:
            raise Http404("Sorry, unkown node.")
        # Parse only body string
        body = json.loads(request.body) if type(request.body) is str else request.body
        # Copy data to allow dictionary resizing
        data = body.copy()
        for field in body:
            # If the field exists into our model
            if hasattr(node, field) and not field.startswith("_"):
                value = data[field]
                # Get the field
                attr = getattr(node, field)
                # It's a relationship
                if hasattr(attr, "_rel"):
                    related_model = attr._rel.relationship.target_model
                    # Clean the field to avoid duplicates
                    if attr.count() > 0: attr.clear()
                    # Load the json-formated relationships
                    data[field] = rels = value
                    # For each relation...
                    for idx, rel in enumerate(rels):
                        if type(rel) in [str, int]: rel = dict(id=rel)
                        # We receied an object with an id
                        if rel.has_key("id"):
                            # Get the related object
                            try:
                                related = related_model.objects.get(id=rel["id"])
                                # Creates the relationship between the two objects
                                attr.add(related)
                            except ObjectDoesNotExist:
                                del data[field][idx]
                                # Too bad! Go to the next related object
                                continue
                # It's a literal value
                else:
                    field_prop = self.get_model_field(field)._property
                    if isinstance(field_prop, DateProperty):
                        # It's a date and therefor `value` should be converted as it
                        value  = datetime.strptime(value, RFC_DATETIME_FORMAT)
                    # Set the new value
                    setattr(node, field, value)
                # Continue to not deleted the field
                continue
            # Remove the field
            del data[field]

        if len(data) > 0:
            val = (getattr(node, field), field)
            # Convert author to set to avoid duplicate
            node._author = set(node._author)
            node._author.add(request.user.id)
            node._author = list(node._author)
            # Save the node
            node.save()
        return self.create_response(request, data)

    def get_graph(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.throttle_check(request)

        depth = int(request.GET['depth']) if 'depth' in request.GET.keys() else 1
        aggregation_threshold = 10

        def reduce_destination(outgoing_links, keep_id=None):
            # We count the popularity of each entering relationsip by node
            counter = {}
            # Counter will have the following structure
            # {
            #   "<NAME_OF_A_RELATIONSHIP>" : {
            #       "<IDX_OF_A_DESTINATION>": set("<IDX_OF_AN_ORIGIN>", ...)
            #   }
            # }
            for origin in outgoing_links:
                for rel in outgoing_links[origin]:
                    for dest in outgoing_links[origin][rel]:
                        if int(origin) != int(keep_id):
                            counter[rel]       = counter.get(rel, {})
                            counter[rel][dest] = counter[rel].get(dest, set())
                            counter[rel][dest].add(origin)
            # List of entering link (aggregate outside 'outgoing_links')
            entering_links = {}
            # Check now witch link must be move to entering outgoing_links
            for rel in counter:
                for dest in counter[rel]:
                    # Too much entering  outgoing_links!
                    if len(counter[rel][dest]) > aggregation_threshold:
                        entering_links[dest] = entering_links.get(dest, {"_AGGREGATION_": set() })
                        entering_links[dest]["_AGGREGATION_"] = entering_links[dest]["_AGGREGATION_"].union(counter[rel][dest])
            # We remove element within a copy to avoid changing the size of the
            # dict durring an itteration
            outgoing_links_copy = copy.deepcopy(outgoing_links)
            for i in entering_links:
                # Convert aggregation set to list for JSON serialization
                entering_links[i]["_AGGREGATION_"] = list( entering_links[i]["_AGGREGATION_"] )
                # Remove entering_links from
                for j in outgoing_links:
                    if int(j) == int(keep_id): continue
                    for rel in outgoing_links[j]:
                        if i in outgoing_links[j][rel]:
                            # Remove the enterging id
                            outgoing_links_copy[j][rel].remove(i)
                        # Remove the relationship
                        if rel in outgoing_links_copy[j] and len(outgoing_links_copy[j][rel]) == 0:
                            del outgoing_links_copy[j][rel]
                    # Remove the origin
                    if len(outgoing_links_copy[j]) == 0:
                        del outgoing_links_copy[j]

            return outgoing_links_copy, entering_links


        def reduce_origin(rows):
            # No nodes, no links
            if len(rows) == 0: return ([], [],)
            # Initialize structures
            all_nodes = dict()
            # Use defaultdict() to create somewhat of an autovivificating list
            # We want to build a structure of the form:
            # { source_id : { relation_name : [ target_ids ] } }
            # Must use a set() instead of list() to avoid checking duplicates but it screw up json.dumps()
            all_links = defaultdict(lambda: dict(__count=0, __relations=defaultdict(list)))
            IDs = set(sum([row['nodes'] for row in rows], []))

            # Get all entities from their IDs
            query = """
                START root = node({0})
                MATCH (root)-[:`<<INSTANCE>>`]-(type)
                WHERE type.app_label = '{1}'
                AND HAS(root.name)
                RETURN ID(root) as ID, root, type
            """.format(','.join([str(ID) for ID in IDs]), get_model_topic(self.get_model()))
            all_raw_nodes = connection.cypher(query).to_dicts()
            for row in all_raw_nodes:
                # Twist some data in the entity
                for key in row['root']['data'].keys():
                    if key[0] == '_': del row['root']['data'][key]
                row['root']['data']['_type'] = row['type']['data']['model_name']
                row['root']['data']['_id'] = row['ID']

                all_nodes[row['ID']] = row['root']['data']

            for row in rows:
                nodes = row['nodes']
                i = 0
                for relation in row['relations']:
                    try:
                        if all_nodes[nodes[i]] is None or all_nodes[nodes[i + 1]] is None: continue
                        (a, b) = (nodes[i], nodes[i + 1])
                        if re.search('^'+to_underscores(all_nodes[nodes[i]]['_type']), relation) is None:
                            (a, b) = (nodes[i + 1], nodes[i])
                        if not b in all_links[a]['__relations'][relation]:
                            all_links[a]['__count'] += 1
                            all_links[a]['__relations'][relation].append(b)
                    except KeyError: pass
                    i += 1

            # Sort and aggregate nodes when we're over the threshold
            for node in all_links.keys():
                shortcut = all_links[node]['__relations']
                if all_links[node]['__count'] >= aggregation_threshold:
                    sorted_relations = sorted([(len(shortcut[rel]), rel) for rel in shortcut],
                                              key=lambda to_sort: to_sort[0])
                    shortcut = defaultdict(list)
                    i = 0
                    while i < aggregation_threshold:
                        for rel in sorted_relations:
                            try:
                                node_id = all_links[node]['__relations'][rel[1]].pop()
                                shortcut[rel[1]].append(node_id)
                                i += 1
                            except IndexError:
                                # Must except IndexError if we .pop() on an empty list
                                pass
                            if i >= aggregation_threshold: break
                    shortcut['_AGGREGATION_'] = sum(all_links[node]['__relations'].values(), [])
                all_links[node] = shortcut

            return (all_nodes, all_links)

        query = """
            START root=node({0})
            MATCH path = (root)-[*1..{1}]-(leaf)
            WITH extract(r in relationships(path)|type(r)) as relations, extract(n in nodes(path)|ID(n)) as nodes
            WHERE ALL(rel  in relations WHERE rel <> "<<INSTANCE>>")
            RETURN relations, nodes
        """.format(kwargs['pk'], depth)
        rows = connection.cypher(query).to_dicts()

        nodes, links                   = reduce_origin(rows)
        outgoing_links, entering_links = reduce_destination(links, keep_id=kwargs['pk'])

        self.log_throttled_access(request)
        return self.create_response(request, {'nodes':nodes,'outgoing_links': outgoing_links, 'entering_links': entering_links})

########NEW FILE########
__FILENAME__ = importusers
# -*- coding: utf-8 -*-
from django.core.management.base  import BaseCommand
from neo4django.graph_auth.models import User as GraphUser
from django.contrib.auth.models   import User

class Command(BaseCommand):
    help = "Import users from graph into current user's collection."
    args = ''

    def handle(self, *args, **options):
        imported = 0

        newusers = [u.__dict__["_prop_values"] for u in GraphUser.objects.all()]
        for u in newusers:
            try:
                User.objects.get(username=u["username"])
                print "%s already exists!" % u["username"]
            # User doesn't exist
            except User.DoesNotExist:
                # Avoid integrity error
                if u["first_name"] == None: u["first_name"] = u["username"]
                if u["last_name"] == None:  u["last_name"] = ""
                user = User(**u)
                user.save()
                # Count imported user
                imported += 1

        if imported <= 1:
            print "%s user imported!" % imported
        else:
            print "%s users imported!" % imported
########NEW FILE########
__FILENAME__ = loadnodes
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
import json
from django.db.models.loading import get_model

class Command(BaseCommand):
    help = "Parse the given JSON file to insert the data into database."    
    args = 'filename.json'
    root = None


    def handle(self, *args, **options):

        if not args:
            raise CommandError('Please specify path to JSON file.')

        json_data = open(args[0])   
        nodes = json.load(json_data) # deserialises it
        json_data.close()

        saved = 0
        for node in nodes:
            # Get the model of the fixture
            model = get_model( *node["model"].split('.', 1) )   
            # Callable model
            if hasattr(model, '__call__'):
                # Create an object with its fields
                obj = model(**node["fields"])
                # Then save the obj
                obj.save()
                # Increment the saved count
                saved += 1

        if saved <= 1:       
            print "%s object saved from file!" % saved
        else:
            print "%s objects saved from file!" % saved
########NEW FILE########
__FILENAME__ = parseowl
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from lxml import etree
from app.detective.utils import to_class_name, to_camelcase, to_underscores
import re

# Defines the owl and rdf namespaces
namespaces = {
    'owl': 'http://www.w3.org/2002/07/owl#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'
}
# transform property name
pron = lambda name: to_underscores(to_camelcase(name))

# get local tag
def get(sets, el):
    if hasattr(sets, "iterchildren"):
        props = [ e for e in sets.iterchildren() if re.search('#}%s$' % el, e.tag) ]
        return props[0].text if len(props) else ''
    else:
        return ""

# Merge 2 list and remove duplicates using the given field as reference
def merge(first_list, second_list, field):
    refs = [ x[field] for x in second_list ]
    return second_list + [ x for x in first_list if x[field] not in refs ]


class Command(BaseCommand):
    help = "Parse the given OWL file to generate its neo4django models."
    args = 'filename.owl'
    root = None


    def handle(self, *args, **options):
        if not args:
            raise CommandError('Please specify path to ontology file.')

        # Gives the ontology URI. Only needed for documentation purposes
        ontologyURI = "http://www.semanticweb.org/nkb/ontologies/2013/6/impact-investment#"
        # This string will contain the models.py file
        headers = [
            "# -*- coding: utf-8 -*-",
            "# The ontology can be found in its entirety at %s" % ontologyURI,
            "from neo4django.db import models",
            "from neo4django.graph_auth.models import User",
            ""
        ]


        # This array contains the correspondance between data types
        correspondanceTypes = {
            "string" : "StringProperty",
            "anyURI" : "URLProperty",
            "int" : "IntegerProperty",
            "nonNegativeInteger" : "IntegerProperty",
            "nonPositiveInteger" : "IntegerProperty",
            "PositiveInteger" : "IntegerProperty",
            "NegativeInteger" : "IntegerProperty",
            # Looking forward the neo4django float support!
            # See also: https://github.com/scholrly/neo4django/issues/197
            "float" : "StringProperty",
            "integer" : "IntegerProperty",
            "dateTimeStamp" : "DateTimeProperty",
            "dateTime" : "DateTimeProperty",
            "boolean" : "BooleanProperty"
        }

        try :
            # Parses the file with etree
            tree = etree.parse(args[0])
        except:
            raise CommandError('Unable to parse the given file.')

        self.root = tree.getroot()
        models = []

        # Finds all the Classes
        for ontologyClassElement in self.root.findall("owl:Class", namespaces):

            # Finds the URI of the class
            classURI = ontologyClassElement.attrib["{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"]

            #Finds the name of the class
            className = to_class_name(classURI.split("#")[1])

            # By default, the class has no parent
            parentClass = "models.NodeModel"

            # Declares an array to store the relationships and properties from this class
            relations = []
            properties = []


            scope = get(ontologyClassElement, "scope").replace("'", "\\'")
            # Class help text
            help_text = get(ontologyClassElement, "help_text").replace("'", "\\'")
            # Verbose names
            verbose_name = get(ontologyClassElement, "verbose_name").replace("'", "\\'")
            verbose_name_plural = get(ontologyClassElement, "verbose_name_plural").replace("'", "\\'")

            # Finds all the subClasses of the Class
            for subClassElement in ontologyClassElement.findall("rdfs:subClassOf", namespaces):

                # If the Class is actually an extension of another Class
                if "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource" in subClassElement.attrib:

                    parentClassURI = subClassElement.attrib["{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"]
                    parentClass = to_class_name(parentClassURI.split("#")[1])

                else:

                    for restriction in subClassElement.findall("owl:Restriction", namespaces):

                        # If there is a relationship defined in the subclass
                        if restriction.find("owl:onClass", namespaces) is not None:

                            # Finds the relationship and its elements
                            # (destination Class and type)
                            relationClass    = restriction.find("owl:onClass", namespaces)
                            relation         = {}
                            relation["URI"]  = relationClass.attrib["{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"]
                            relation["name"] = to_class_name(relation["URI"].split("#")[1])

                            # Exception when the relation's destination is
                            # an individual from the same class
                            if relation["name"] == className:
                                relation["name"] = '"self"'
                            else:
                                relation["name"] = '"%s"' % relation["name"]


                            relationType     = restriction.find("owl:onProperty", namespaces)
                            relationTypeURI  = relationType.attrib["{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"]
                            relation["type"] = relationTypeURI.split("#")[1]

                            # Guesses the destination of the relation based on the name.
                            # Name should be "has_..."
                            if relation["type"].find('has') == 0:
                                relation["destination"] = pron(relation["type"][3:])

                                # Get the property's options
                                options = self.propOptions(relation["type"])

                                # Help text
                                relation["help_text"]    = get(options, "help_text").replace("'", "\\'")
                                # Verbose name
                                relation["verbose_name"] = get(options, "verbose_name")
                                relation["type"]         = relation["type"]

                                # Adds the relationship to the array containing all relationships for the class only
                                # if the relation has a destination
                                if "destination" in relation:
                                    relations.append(relation)

                        # If there is a property defined in the subclass
                        elif restriction.find("owl:onDataRange", namespaces) is not None or restriction.find("owl:someValuesFrom", namespaces) is not None:
                            propertyTypeElement = restriction.find("owl:onProperty", namespaces)
                            propertyTypeURI     = propertyTypeElement.attrib["{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"]
                            propertyType        = propertyTypeURI.split("#")[1]

                            if restriction.find("owl:onDataRange", namespaces) is not None:
                                dataTypeElement = restriction.find("owl:onDataRange", namespaces)
                            else:
                                dataTypeElement = restriction.find("owl:someValuesFrom", namespaces)

                            dataTypeURI = dataTypeElement.attrib["{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"]

                            t = dataTypeURI.split("#")[1]

                            if t in correspondanceTypes:
                                dataType = correspondanceTypes[t]
                                # Get the property's options
                                options = self.propOptions(propertyType)

                                prop = {
                                    "name" : propertyType,
                                    "type" : dataType,
                                    # Help text
                                    "help_text": get(options, "help_text").replace("'", "\\'"),
                                    # Verbose name
                                    "verbose_name": get(options, "verbose_name")
                                }

                                properties.append(prop)
                            else:
                                raise CommandError("Property '%s' of '%s' using unkown type: %s" % (propertyType, className, t) )

            models.append({
                "className"          : className,
                "scope"              : scope,
                "help_text"          : help_text,
                "verbose_name"       : verbose_name,
                "verbose_name_plural": verbose_name_plural,
                "parentClass"        : parentClass,
                "properties"         : properties,
                "relations"          : relations,
                "dependencies"       : [parentClass]
            })

        # Topological sort of the model to avoid dependance missings
        models = self.topolgical_sort(models)
        # Output the models file
        self.print_models(models, headers)


    # option of the given property
    def propOptions(self, name):

        options = None
        attr    = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"

        for p in self.root.findall("owl:ObjectProperty", namespaces):
            if re.search('#%s$' % name, p.attrib[attr]):
                options = p
        for p in self.root.findall("owl:DatatypeProperty", namespaces):
            if re.search('#%s$' % name, p.attrib[attr]):
                options = p

        return options

    @staticmethod
    def print_models(models=[], headers=[]):

        modelsContents = headers

        for m in models:
            # Writes the class in models.py
            modelsContents.append("\nclass "+ m["className"] +"(models.NodeModel):")

            # Defines properties and relations that every model have
            m["properties"].insert(0,
                {
                    "name" : "_author",
                    "type": "IntArrayProperty",
                    # Verbose name
                    "verbose_name": "author",
                    "help_text": "People that edited this entity."
                }
            )
            m["properties"].insert(1,
                {
                    "name" : "_status",
                    "type": "IntegerProperty",
                    # Verbose name
                    "verbose_name": "status",
                    "help_text": ""
                }
            )
            # Since neo4django doesn't support model inheritance correctly
            # we use models.NodeModel for every model
            # and duplicates parent's attributes into its child
            if m["parentClass"] != "models.NodeModel":
                modelsContents.append("\t_parent = u'%s'" % m["parentClass"])
                # Find the models that could be the parent of the current one
                parents = [model for model in models if model["className"] == m["parentClass"] ]
                # We found at least one parent
                if len(parents):
                    # We take the first one
                    parent = parents[0]
                    # We merge the properties and the relationships
                    m["properties"] = merge(parent["properties"], m["properties"], "name")
                    m["relations"]  = merge(parent["relations"], m["relations"], "destination")


            if m["scope"] != '' and m["scope"] != None:
                modelsContents.append("\t_topic = u'%s'" % m["scope"])

            if m["help_text"] != None:
                modelsContents.append("\t_description = u'%s'" % m["help_text"])

            # Writes the properties
            for prop in m["properties"]:
                opt = [
                    "null=True",
                    "help_text=u'%s'" % prop["help_text"]
                ]

                if prop["verbose_name"] != '':
                    opt.append("verbose_name=u'%s'" % prop["verbose_name"])

                field = "\t%s = models.%s(%s)"
                opt = ( pron(prop["name"]), prop["type"],  ",".join(opt))
                modelsContents.append(field % opt )

            # Writes the relationships
            for rel in m["relations"]:

                opt = [
                    rel["name"],
                    "null=True",
                    # Add class name prefix to relation type
                    "rel_type='%s+'" % pron( m["className"] + "_" + rel["type"] ),
                    "help_text=u'%s'" % rel["help_text"]
                ]

                if prop["verbose_name"] != '':
                    opt.append("verbose_name=u'%s'" % rel["verbose_name"])

                field = "\t%s = models.Relationship(%s)"
                modelsContents.append(field % (rel["destination"], ",".join(opt) ) )

            modelsContents.append("\n\tclass Meta:")

            if m["verbose_name"] != '':
                modelsContents.append("\t\tverbose_name = u'%s'" % m["verbose_name"])
            if m["verbose_name_plural"] != '':
                modelsContents.append("\t\tverbose_name_plural = u'%s'" % m["verbose_name_plural"])

            if m["verbose_name"] == '' and  m["verbose_name_plural"] == '':
                modelsContents.append("\t\tpass")

            if len([p for p in m["properties"] if p["name"] == "name" ]):
                modelsContents.append("\n\tdef __unicode__(self):")
                modelsContents.append("\t\treturn self.name or u\"Unkown\"")


        print "\n".join(modelsContents).encode("UTF-8")

    @staticmethod
    def topolgical_sort(graph_unsorted):
        """
        :src http://blog.jupo.org/2012/04/06/topological-sorting-acyclic-directed-graphs/

        Repeatedly go through all of the nodes in the graph, moving each of
        the nodes that has all its edges resolved, onto a sequence that
        forms our sorted graph. A node has all of its edges resolved and
        can be moved once all the nodes its edges point to, have been moved
        from the unsorted graph onto the sorted one.
        """

        # This is the list we'll return, that stores each node/edges pair
        # in topological order.
        graph_sorted = []

        # Run until the unsorted graph is empty.
        while graph_unsorted:

            # Go through each of the node/edges pairs in the unsorted
            # graph. If a set of edges doesn't contain any nodes that
            # haven't been resolved, that is, that are still in the
            # unsorted graph, remove the pair from the unsorted graph,
            # and append it to the sorted graph. Note here that by using
            # using the items() method for iterating, a copy of the
            # unsorted graph is used, allowing us to modify the unsorted
            # graph as we move through it. We also keep a flag for
            # checking that that graph is acyclic, which is true if any
            # nodes are resolved during each pass through the graph. If
            # not, we need to bail out as the graph therefore can't be
            # sorted.
            acyclic = False
            for index, item in enumerate(graph_unsorted):
                edges = item["dependencies"]

                node_unsorted = [item_unsorted["className"] for item_unsorted in graph_unsorted]

                for edge in edges:
                    if edge in node_unsorted:
                        break
                else:
                    acyclic = True
                    del graph_unsorted[index]
                    graph_sorted.append(item)

            if not acyclic:
                # Uh oh, we've passed through all the unsorted nodes and
                # weren't able to resolve any of them, which means there
                # are nodes with cyclic edges that will never be resolved,
                # so we bail out with an error.
                raise RuntimeError("A cyclic dependency occurred")

        return graph_sorted


########NEW FILE########
__FILENAME__ = reindex
# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.db.models.loading import get_model

class Command(BaseCommand):
    help = "Reindex a given model."    
    args = 'app.Model'    

    def handle(self, *args, **options):
        if not args:
            raise CommandError('Please specify the model to reindex.')        
        # Get the model parts
        parts = args[0].split('.', 1)
        # Model given is malformed
        if len(parts) != 2:
            raise CommandError('Indicate the model to reindex by following the syntax "app.Model".')        
        # Get the model
        model = get_model( *parts )   
        # Callable model
        if model == None:
            raise CommandError('Unable to load the model "%s"' % args[0])  
        saved_ct = 0     
        print "Starting reindex. This can take a while...." 
        # Load every objects to reindex them one by one
        for o in model.objects.all(): 
            # Save the object without changing anything will force a reindex
            o.save()
            # Count saved objects
            saved_ct += 1
        print 'Model "%s" reindexed through %s object(s).' % (model.__name__, saved_ct)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'QuoteRequest'
        db.create_table(u'detective_quoterequest', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('employer', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=100)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('domain', self.gf('django.db.models.fields.TextField')()),
            ('records', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('users', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('public', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'detective', ['QuoteRequest'])

        # Adding model 'Topic'
        db.create_table(u'detective_topic', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('module', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=250)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=250)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('about', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('ontology', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('background', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal(u'detective', ['Topic'])


    def backwards(self, orm):
        # Deleting model 'QuoteRequest'
        db.delete_table(u'detective_quoterequest')

        # Deleting model 'Topic'
        db.delete_table(u'detective_topic')


    models = {
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0002_auto__add_relationshipsearch
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'RelationshipSearch'
        db.create_table(u'detective_relationshipsearch', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('topic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['detective.Topic'])),
        ))
        db.send_create_signal(u'detective', ['RelationshipSearch'])


    def backwards(self, orm):
        # Deleting model 'RelationshipSearch'
        db.delete_table(u'detective_relationshipsearch')


    models = {
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.relationshipsearch': {
            'Meta': {'object_name': 'RelationshipSearch'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0003_auto__del_unique_topic_module
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Topic', fields ['module']
        db.delete_unique(u'detective_topic', ['module'])


    def backwards(self, orm):
        # Adding unique constraint on 'Topic', fields ['module']
        db.create_unique(u'detective_topic', ['module'])


    models = {
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.relationshipsearch': {
            'Meta': {'object_name': 'RelationshipSearch'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0004_load_myfixture
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
import json

class Migration(DataMigration):

    def forwards(self, orm):
        json_data = open("app/detective/fixtures/initial_data.json")        
        items = json.load(json_data)
        for item in items:
            obj = orm[ item["model"] ](**item["fields"])
            obj.save()
        json_data.close()

    def backwards(self, orm):
        "Write your backwards methods here."

    models = {
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.relationshipsearch': {
            'Meta': {'object_name': 'RelationshipSearch'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0005_add_model_Article
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Article'
        db.create_table(u'detective_article', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('topic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['detective.Topic'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=250)),
            ('content', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('public', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'detective', ['Article'])


    def backwards(self, orm):
        # Deleting model 'Article'
        db.delete_table(u'detective_article')


    models = {
        u'detective.article': {
            'Meta': {'object_name': 'Article'},
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.relationshipsearch': {
            'Meta': {'object_name': 'RelationshipSearch'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0006_auto__add_field_article_created_at
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Article.created_at'
        db.add_column(u'detective_article', 'created_at',
                      self.gf('django.db.models.fields.DateTimeField')(default=None, auto_now_add=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Article.created_at'
        db.delete_column(u'detective_article', 'created_at')


    models = {
        u'detective.article': {
            'Meta': {'object_name': 'Article'},
            'content': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.relationshipsearch': {
            'Meta': {'object_name': 'RelationshipSearch'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0007_auto__chg_field_article_content
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Article.content'
        db.alter_column(u'detective_article', 'content', self.gf('tinymce.models.HTMLField')(null=True))

    def backwards(self, orm):

        # Changing field 'Article.content'
        db.alter_column(u'detective_article', 'content', self.gf('django.db.models.fields.TextField')(null=True))

    models = {
        u'detective.article': {
            'Meta': {'object_name': 'Article'},
            'content': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.relationshipsearch': {
            'Meta': {'object_name': 'RelationshipSearch'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0008_auto__chg_field_topic_about__chg_field_topic_description
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Topic.about'
        db.alter_column(u'detective_topic', 'about', self.gf('tinymce.models.HTMLField')(null=True))

        # Changing field 'Topic.description'
        db.alter_column(u'detective_topic', 'description', self.gf('tinymce.models.HTMLField')(null=True))

    def backwards(self, orm):

        # Changing field 'Topic.about'
        db.alter_column(u'detective_topic', 'about', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'Topic.description'
        db.alter_column(u'detective_topic', 'description', self.gf('django.db.models.fields.TextField')(null=True))

    models = {
        u'detective.article': {
            'Meta': {'object_name': 'Article'},
            'content': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.relationshipsearch': {
            'Meta': {'object_name': 'RelationshipSearch'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0009_auto__chg_field_relationshipsearch_subject__chg_field_relationshipsear
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'RelationshipSearch.subject'
        db.alter_column(u'detective_relationshipsearch', 'subject', self.gf('django.db.models.fields.CharField')(max_length=250, null=True))

        # Changing field 'RelationshipSearch.label'
        db.alter_column(u'detective_relationshipsearch', 'label', self.gf('django.db.models.fields.CharField')(max_length=250, null=True))

    def backwards(self, orm):

        # Changing field 'RelationshipSearch.subject'
        db.alter_column(u'detective_relationshipsearch', 'subject', self.gf('django.db.models.fields.CharField')(default='', max_length=250))

        # Changing field 'RelationshipSearch.label'
        db.alter_column(u'detective_relationshipsearch', 'label', self.gf('django.db.models.fields.CharField')(default='', max_length=250))

    models = {
        u'detective.article': {
            'Meta': {'object_name': 'Article'},
            'content': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.relationshipsearch': {
            'Meta': {'object_name': 'RelationshipSearch'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0010_rename_RelationshipSearch_to_SearchTerm
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.rename_table('detective_relationshipsearch', 'detective_searchterm')

    def backwards(self, orm):
        db.rename_table('detective_searchterm', 'detective_relationshipsearch')

    models = {
        u'detective.article': {
            'Meta': {'object_name': 'Article'},
            'content': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.searchterm': {
            'Meta': {'object_name': 'SearchTerm'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0011_load_myfixture
# -*- coding: utf-8 -*-
from south.v2    import DataMigration
import json

class Migration(DataMigration):

    def forwards(self, orm):
        json_data=open("app/detective/fixtures/search_terms.json")
        search_terms = json.load(json_data)
        for st in search_terms:
            st["fields"]["topic"] = orm["detective.topic"].objects.get(id=st["fields"]["topic"])
            obj = orm["detective.searchterm"](**st["fields"])
            obj.save()
        json_data.close()

    def backwards(self, orm):
        "Write your backwards methods here."

    no_dry_run = True
    models = {
        u'detective.article': {
            'Meta': {'object_name': 'Article'},
            'content': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.searchterm': {
            'Meta': {'object_name': 'SearchTerm'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }


    complete_apps = ['detective']
    symmetrical = True

########NEW FILE########
__FILENAME__ = 0012_auto__add_field_searchterm_is_literal
# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'SearchTerm.is_literal'
        db.add_column(u'detective_searchterm', 'is_literal',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'SearchTerm.is_literal'
        db.delete_column(u'detective_searchterm', 'is_literal')

    no_dry_run = True
    models = {
        u'detective.article': {
            'Meta': {'object_name': 'Article'},
            'content': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.searchterm': {
            'Meta': {'object_name': 'SearchTerm'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_literal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'label': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = 0013_auto__add_field_topic_author
# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Topic.author'
        db.add_column(u'detective_topic', 'author',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Topic.author'
        db.delete_column(u'detective_topic', 'author_id')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'detective.article': {
            'Meta': {'object_name': 'Article'},
            'content': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.quoterequest': {
            'Meta': {'object_name': 'QuoteRequest'},
            'comment': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'domain': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '100'}),
            'employer': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'records': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'detective.searchterm': {
            'Meta': {'object_name': 'SearchTerm'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_literal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'label': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'subject': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '250', 'null': 'True', 'blank': 'True'}),
            'topic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['detective.Topic']"})
        },
        u'detective.topic': {
            'Meta': {'object_name': 'Topic'},
            'about': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'background': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'description': ('tinymce.models.HTMLField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.SlugField', [], {'max_length': '250', 'blank': 'True'}),
            'ontology': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '250'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '250'})
        }
    }

    complete_apps = ['detective']
########NEW FILE########
__FILENAME__ = modelrules
import inspect

# Class that manage rules througt a local object name
class HasRules(object):
    def __init__(self):
        # Default rules for this object
        self.registered_rules = {}

    # Add a rule
    def add(self, **kwargs):
        # Treats arguments as a dictionary of rules
        for name, value in kwargs.items():
            # Each rule can only have one value
            self.set(name, value)
        # Allows chaining
        return self

    # Get all registered rules
    def all(self): return self.registered_rules
    # Get one rule
    def get(self, name): return self.all().get(name)
    # Set a rule with key/value pair
    def set(self, name, value):
        self.registered_rules[name] = value
        # Allows chaining
        return self

# Field class to register rules associated to a field
class Field(HasRules):
    def __init__(self, name, model):
        self.name = name
        self.model = model
        # Call parent constructor
        super(Field, self).__init__()
        # Default rules for this models
        self.registered_rules["is_visible"] = True
        self.registered_rules["priority"] = 0

# Model class to register rules associated to a model
class Model(HasRules):
    # Record the associated model
    def __init__(self, model):
        # Check that the model is a class
        if not inspect.isclass(model): print model
        if not inspect.isclass(model) or not hasattr(model, "_meta"):
            raise Exception("You can only registed model's class.")
        self.model = model
        # Get the model fields
        self.field_names = model._meta.get_all_field_names()
        # Field of the model
        self.registered_fields = {}
        # Register all field
        for name in self.field_names: self.register_field(name)
        # Call parent constructor
        super(Model, self).__init__()
        # Default rules for this models
        self.registered_rules["is_editable"]   = True
        self.registered_rules["is_searchable"] = True


    # Register a field rule
    def register_field(self, field):
        # If the field is not registered yet
        if field not in self.registered_fields:
            # Register the field
            self.registered_fields[field] = Field(name=field, model=self.model)

        return self.registered_fields[field]

    # Shortcut to register field
    field = register_field
    # List of registered model ordered by priority
    def fields(self, ordered=True):
        if not ordered:
            return self.registered_fields
        else:
            def sortkey(field):
                return (
                    -field.get("is_visible"),
                    -field.get("priority"),
                    field.name
                )
            # Sor the list
            return sorted(self.registered_fields.values(), key=sortkey)


# This class is a Singleton that register model layout
# @src http://stackoverflow.com/questions/42558/python-and-the-singleton-pattern
class ModelRules(object):

    __instance = None
    # Override __new__ to avoid create new instance (singleton)
    def __new__(self, *args, **kwargs):
        if not self.__instance:
            self.__instance = super(ModelRules, self).__new__(self, *args, **kwargs)
            # List of registered model
            self.registered_models = {}
        return self.__instance

    # This method will add the given model to the register list
    def register_model(self, model):
        # Soft validation:
        # we stop double registering
        # without raise an exception
        if model not in self.registered_models:
            self.registered_models[model] = Model(model)

        return self.registered_models[model]

    # Get model (shortcut to register_model)
    model = register_model
    # List of registered model
    def models(self): return self.registered_models



########NEW FILE########
__FILENAME__ = models
from .utils                     import get_topics
from app.detective              import utils
from app.detective.permissions  import create_permissions, remove_permissions
from django.core.cache          import cache
from django.core.exceptions     import ValidationError
from django.db                  import models
from django.contrib.auth.models import User
from tinymce.models             import HTMLField

import inspect
import os
import random
import string

PUBLIC = (
    (True, "Yes, public"),
    (False, "No, just for a small group of users"),
)

class QuoteRequest(models.Model):
    RECORDS_SIZE = (
        (0, "Less than 200"),
        (200, "Between 200 and 1000"),
        (1000, "Between 1000 & 10k"),
        (10000, "More than 10k"),
        (-1, "I don't know yet"),
    )
    USERS_SIZE = (
        (1, "1"),
        (5, "1-5"),
        (0, "More than 5"),
        (-1, "I don't know yet"),
    )
    name     = models.CharField(max_length=100)
    employer = models.CharField(max_length=100)
    email    = models.EmailField(max_length=100)
    phone    = models.CharField(max_length=100, blank=True, null=True)
    domain   = models.TextField(help_text="Which domain do you want to investigate on?")
    records  = models.IntegerField(choices=RECORDS_SIZE, blank=True, null=True, help_text="How many entities do you plan to store?")
    users    = models.IntegerField(choices=USERS_SIZE, blank=True, null=True, help_text="How many people will work on the investigation?")
    public   = models.NullBooleanField(choices=PUBLIC, null=True, help_text="Will the data be public?")
    comment  = models.TextField(blank=True, null=True, help_text="Anything else you want to tell us?")

    def __unicode__(self):
        return "%s - %s" % (self.name, self.email,)

class Topic(models.Model):
    MODULES     = tuple( (topic, topic,) for topic in get_topics() )
    title       = models.CharField(max_length=250, help_text="Title of your topic.")
    # Value will be set for this field if it's blank
    module      = models.SlugField(choices=MODULES, blank=True, max_length=250, help_text="Module to use to create your topic. Leave blank to create a virtual one.")
    slug        = models.SlugField(max_length=250, unique=True, help_text="Token to use into the url.")
    description = HTMLField(null=True, blank=True, help_text="A short description of what is your topic.")
    about       = HTMLField(null=True, blank=True, help_text="A longer description of what is your topic.")
    public      = models.BooleanField(help_text="Is your topic public?", default=True, choices=PUBLIC)
    ontology    = models.FileField(null=True, blank=True, upload_to="ontologies", help_text="Ontology file that descibes your field of study.")
    background  = models.ImageField(null=True, blank=True, upload_to="topics", help_text="Background image displayed on the topic's landing page.")
    author      = models.ForeignKey(User, help_text="Author of this topic.", null=True)

    def __unicode__(self):
        return self.title

    def app_label(self):
        if self.slug in ["common", "energy"]:
            return self.slug
        elif not self.module:
            # Already saved topic
            if self.id:
                # Restore the previous module value
                self.module = Topic.objects.get(id=self.id).module
                # Call this function again.
                # Continue if module is still empty
                if self.module: return self.app_label()
            while True:
                token = Topic.get_module_token()
                # Break the loop only if the token doesn't exist
                if not Topic.objects.filter(module=token).exists(): break
            # Save the new token
            self.module = token
            # Save a first time if no idea given
            models.Model.save(self)
        return self.module

    @staticmethod
    def get_module_token(size=10, chars=string.ascii_uppercase + string.digits):
        return "topic%s" % ''.join(random.choice(chars) for x in range(size))

    def get_module(self):
        from app.detective import topics
        return getattr(topics, self.app_label())

    def get_models_module(self):
        """ return the module topic_module.models """
        return getattr(self.get_module(), "models")

    def get_models(self):
        """ return a list of Model """
        # We have to load the topic's model
        models_module = self.get_models_module()
        models_list   = []
        for i in dir(models_module):
            klass = getattr(models_module, i)
            # Collect every Django's model subclass
            if inspect.isclass(klass) and issubclass(klass, models.Model):
                models_list.append(klass)
        return models_list

    def clean(self):
        if self.ontology == "" and not self.has_default_ontology():
            raise ValidationError( 'An ontology file is required with this module.',  code='invalid')
        models.Model.clean(self)

    def save(self, *args, **kwargs):
        # Ensure that the module field is populated with app_label()
        self.module = self.app_label()
        # Call the parent save method
        super(Topic, self).save(*args, **kwargs)
        # Refresh the API
        self.reload()

    def reload(self):
        from app.detective.register import topic_models
        # Register the topic's models again
        topic_models(self.get_module().__name__, force=True)

    def has_default_ontology(self):
        try:
            module = self.get_module()
        except ValueError: return False
        # File if it's a virtual module
        if not hasattr(module, "__file__"): return False
        directory = os.path.dirname(os.path.realpath( module.__file__ ))
        # Path to the ontology file
        ontology  = "%s/ontology.owl" % directory
        return os.path.exists(ontology) or hasattr(self.get_module(), "models")


    def get_absolute_path(self):
        if self.author is None:
            return None
        else:
            return "/%s/%s/" % (self.author.username, self.slug,)

    def link(self):
        path = self.get_absolute_path()
        if path is None:
            return ''
        else:
            return '<a href="%s">%s</a>' % (path, path, )

    link.allow_tags = True


class Article(models.Model):
    topic      = models.ForeignKey(Topic, help_text="The topic this article is related to.")
    title      = models.CharField(max_length=250, help_text="Title of your article.")
    slug       = models.SlugField(max_length=250, unique=True, help_text="Token to use into the url.")
    content    = HTMLField(null=True, blank=True)
    public     = models.BooleanField(default=False, help_text="Is your article public?")
    created_at = models.DateTimeField(auto_now_add=True, default=None, null=True)

    def get_absolute_path(self):
        return self.topic.get_absolute_path() + ( "p/%s/" % self.slug )

    def __unicode__(self):
        return self.title

    def link(self):
        path = self.get_absolute_path()
        return '<a href="%s">%s</a>' % (path, path, )
    link.allow_tags = True


# This model aims to describe a research alongside a relationship.
class SearchTerm(models.Model):
    # This field is deduced from the relationship name
    subject    = models.CharField(null=True, blank=True, default='', editable=False, max_length=250, help_text="Kind of entity to look for (Person, Organization, ...).")
    # This field is set automaticly too according the choosen name
    is_literal = models.BooleanField(editable=False, default=False)
    # Every field are required
    label      = models.CharField(null=True, blank=True, default='', max_length=250, help_text="Label of the relationship (typically, an expression such as 'was educated in', 'was financed by', ...).")
    # This field will be re-written by app.detective.admin
    # to be allow dynamic setting of the choices attribute.
    name       = models.CharField(max_length=250, help_text="Name of the relationship inside the subject.")
    topic      = models.ForeignKey(Topic, help_text="The topic this relationship is related to.")

    def find_subject(self):
        subject = None
        # Retreive the subject that match with the instance's name
        field = self.field
        # If any related_model is given, that means its subject is is parent model
        subject = field["model"]
        return subject

    def clean(self):
        self.subject    = self.find_subject()
        self.is_literal = self.type == "literal"
        models.Model.clean(self)

    @property
    def field(self):
        field = None
        if self.name:
            # Build a cache key with the topic token
            cache_key = "%s__%s__field" % ( self.topic.module, self.name )
            # Try to use the cache value
            if cache.get(cache_key) is not None:
                field = cache.get(cache_key)
            else:
                topic_models = self.topic.get_models()
                for model in topic_models:
                    # Retreive every relationship field for this model
                    for f in utils.get_model_fields(model):
                        if f["name"] == self.name:
                            field = f
        # Very small cache to optimize recording
        cache.set(cache_key, field, 10)
        return field

    @property
    def type(self):
        field = self.field
        if field is None:
            return None
        elif field["type"] == "Relationship":
            return "relationship"
        else:
            return "literal"

# -----------------------------------------------------------------------------
#
#    SIGNALS
#
# -----------------------------------------------------------------------------
from django.db.models import signals

def update_permissions(*args, **kwargs):
    """ create the permissions related to the label module """
    assert kwargs.get('instance')
    # @TODO check that the slug changed or not to avoid permissions hijacking
    if kwargs.get('created', False):
        create_permissions(kwargs.get('instance').get_module(), app_label=kwargs.get('instance').module)

signals.post_delete.connect(remove_permissions, sender=Topic)
signals.post_save.connect(update_permissions, sender=Topic)
# EOF
########NEW FILE########
__FILENAME__ = neomatch
from neo4django.db    import connection

class Neomatch(object):

    def __init__(self, match, target_model, title=""):        
        self.select = "end_obj"
        self.model  = "model_obj"        
        # Save the attributes
        self.match        = str(match)
        self.title        = title
        self.target_model = target_model
        # Build the query
        self.query_str = """
            START root=node({root})
            MATCH {match}
            RETURN DISTINCT({select}) as end_obj, ID({select}) as id
        """
    # Process the query to the database
    def query(self, root="*"):
        # Replace the query's tags 
        # by there choosen value
        query = self.query_str.format(
            root=root, 
            match=self.match.format(
                select=self.select,
                model=self.model
            ),
            select=self.select,
        )
        # Execute the query and returnt the result as a dictionnary
        return self.transform(connection.cypher(query).to_dicts())
    # Transform neo4j result to a more understable list 
    def transform(self, items):
        results = []
        # app     = get_app('detective')
        # models  = get_models(app)

        for item in items:
            #  model = next(m for m in models if m.__name__ == item["model_name"])            
            # Keep the result only if we know its model
            results.append(dict( 
                {'id': item["id"]}.items() + item[self.select]["data"].items() )
            )
        return results


########NEW FILE########
__FILENAME__ = owl
# -*- coding: utf-8 -*-
from app.detective.utils           import to_class_name, to_underscores, create_node_model
from django.db.models.fields.files import FieldFile
from lxml                          import etree as ET
from neo4django.db                 import models

NAMESPACES = {
    'owl': 'http://www.w3.org/2002/07/owl#',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'
}

# This object contains the correspondance between data types
OWLTYPES = {
    "string" : "StringProperty",
    "anyURI" : "URLProperty",
    "int" : "IntegerProperty",
    "nonNegativeInteger" : "IntegerProperty",
    "nonPositiveInteger" : "IntegerProperty",
    "PositiveInteger" : "IntegerProperty",
    "NegativeInteger" : "IntegerProperty",
    "integer" : "IntegerProperty",
    "dateTimeStamp" : "DateTimeProperty",
    "dateTime" : "DateTimeProperty",
    "boolean" : "BooleanProperty",
    # Looking forward the neo4django float support!
    # See also: https://github.com/scholrly/neo4django/issues/197
    "float" : "StringProperty"
}


def attr(obj, name, default=None):
    tokens = name.split(":")
    if not len(tokens):
        return obj.get(name, default)
    else:
        return obj.get("{%s}%s" % ( NAMESPACES[tokens[0]], tokens[1]), default)

def get_field_specials(root, field_name):
    specials = ["verbose_name", "help_text"]
    props = {}
    tags  = root.findall("owl:ObjectProperty",   namespaces=NAMESPACES)
    tags += root.findall("owl:DatatypeProperty", namespaces=NAMESPACES)
    # List all special propertie
    for prop in tags:
        if attr(prop, "rdf:about", "") == field_name:
            # Get the first element txt or the default value
            first = lambda a, d=None: a[0].text if len(a) else d
            for s in specials:
                props[s] = first( prop.xpath("./*[local-name() = '%s']" % s) )
    # Return an empty dict by default
    return props

def get_class_specials(element):
    specials = ["verbose_name", "verbose_name_plural", "help_text", "scope"]
    props = {}
    # Get the first element txt or the default value
    first = lambda a, d=None: a[0].text if len(a) else d
    for s in specials:
        props[s] = first( element.xpath("./*[local-name() = '%s']" % s) )
    # Return an empty dict by default
    return props

def parse(ontology, module='', app_label=None):
    app_label = app_label if app_label is not None else module.split(".")[-1]
    # Deduce the path to the ontology
    if type(ontology) is FieldFile:
        raw = ontology.read()
        # Open the ontology file and returns the root
        root = ET.fromstring(raw)
    else:
        tree = ET.parse(str(ontology))
        # Get the root of the xml
        root = tree.getroot()
    # Where record the new classes
    classes = dict()
    # List classes
    for clss in root.findall("owl:Class", namespaces=NAMESPACES):
        # Extract the class name
        class_name = attr(clss, "rdf:about", "").split('#')[-1]
        # Format the class name to be PEP compliant
        class_name = to_class_name(class_name)
        # Get all special attributes for this class
        class_specials = get_class_specials(clss)
        # Every class fields are recorded into an objects
        class_fields = {
            # Additional informations
            "_description": class_specials["help_text"],
            "_topic"      : class_specials["scope"],
            # Default fields
            "_author": models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author'),
            "_status": models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
        }
        # Pick some options (Meta class)
        class_options = {}
        for f in ["verbose_name", "verbose_name_plural"]:
            if class_specials[f] is not None:
                class_options[f] = class_specials[f]
        # List all fields
        for field in clss.findall("rdfs:subClassOf//owl:Restriction", namespaces=NAMESPACES):
            # All field's options
            field_opts = dict(null=True)
            # Get the name tag
            field_name = field.find("owl:onProperty", namespaces=NAMESPACES)
            # We didn't found a name
            if field_name is None: continue
            # Get the complete field name using the rdf:resource attribute
            field_name = attr(field_name, "rdf:resource");
            # Get field's special properties
            field_opts = dict(field_opts.items() + get_field_specials(root, field_name).items() )
            # Convert the name to a python readable format
            field_name = to_underscores(field_name.split("#")[-1])
            # It might be a relationship
            on_class = field.find("owl:onClass", namespaces=NAMESPACES)
            # It's a relationship!
            if on_class is not None:
                field_opts["target"] = to_class_name(attr(on_class, "rdf:resource").split("#")[-1])
                # Remove "has_" from the begining of the name
                if field_name.startswith("has_"): field_name = field_name[4:]
                # Build rel_type using the name and the class name
                field_opts["rel_type"] = "%s_has_%s+"  % ( to_underscores(class_name), field_name)
                field_type = "Relationship"
            else:
                # Get the type tag
                data_range = field.find("owl:onDataRange", namespaces=NAMESPACES)
                # It might be another tag
                values_from = field.find("owl:someValuesFrom", namespaces=NAMESPACES)
                # Picks one of the two tags type
                field_type = data_range if data_range is not None else values_from
                # It might be nothing!
                if field_type is None: continue
                # Convert the type to a python readable format
                field_type = OWLTYPES[attr(field_type, "rdf:resource").split("#")[-1]]
            # Record the field
            class_fields[field_name] = getattr(models, field_type)(**field_opts)
        # Record the class with this fields
        classes[class_name] = create_node_model(class_name, class_fields, app_label=app_label, options=class_options, module=module)
        # Prevent a bug with select_related when using neo4django and virtual models
        if not hasattr(classes[class_name]._meta, '_relationships'):
            classes[class_name]._meta._relationships = {}
    return classes
########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
# Encoding: utf-8
# -----------------------------------------------------------------------------
# Project : Detective.io
# -----------------------------------------------------------------------------
# Creation : 22-Jan-2014
# Last mod : 22-Jan-2014
# -----------------------------------------------------------------------------
# From http://stackoverflow.com/questions/13932774/how-can-i-use-django-permissions-without-defining-a-content-type-or-model/13952198#13952198
from django.db import models
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

class AppPermissionManager(models.Manager):
    def get_query_set(self):
        return super(AppPermissionManager, self).\
            get_query_set().filter(content_type__name='global_permission')

class AppPermission(Permission):
    """A global permission, not attached to a model"""

    objects = AppPermissionManager()

    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        ct, created = ContentType.objects.get_or_create(
            name="global_permission", app_label=self.app_label()
        )
        self.content_type = ct
        super(AppPermission, self).save(*args, **kwargs)

    def app_label(self, label=None):
        if label:
            self._app_label = label
        return self._app_label

# EOF

########NEW FILE########
__FILENAME__ = register
from app.detective                       import owl, utils
from app.detective.modelrules            import ModelRules
from app.detective.models                import Topic
from django.conf.urls                    import url, include, patterns
from django.conf                         import settings
from django.core.urlresolvers            import clear_url_caches
from tastypie.api                        import NamespacedApi

import importlib
import os
import sys
import imp


def topics_rules():
    """
        Auto-discover topic-related rules by looking into
        evry topics' directories for forms.py files.
    """
    # Avoid bi-directional dependancy
    from app.detective.utils import get_topics
    # ModelRules is a singleton that record every model rules
    rules = ModelRules()
    # Each app can defined a forms.py file that describe the model rules
    topics = get_topics(offline=False)
    for topic in topics:
        # Add default rules
        default_rules(topic)
        # Does this app contain a forms.py file?
        path = "app.detective.topics.%s.forms" % topic
        try:
            mod  = importlib.import_module(path)
        except ImportError:
            # Ignore absent forms.py
            continue
        func = getattr(mod, "topics_rules", None)
        # Simply call the function to register app's rules
        if func: rules = func()
    return rules

def default_rules(topic):
    # ModelRules is a singleton that record every model rules
    rules = ModelRules()
    # We cant import this early to avoid bi-directional dependancies
    from app.detective.utils import import_class
    # Get all registered models
    models = Topic.objects.get(module=topic).get_models()
    # Set "is_searchable" to true on every model with a name
    for model in models:
        # If the current model has a name
        if "name" in rules.model(model).field_names:
            field_names = rules.model(model).field_names
            # Count the fields len
            fields_len = len(field_names)
            # Put the highest priority to that name
            rules.model(model).field('name').add(priority=fields_len)
        # This model isn't searchable
        else: rules.model(model).add(is_searchable=False)
    # Check now that each "Relationship"
    # match with a searchable model
    for model in models:
        for field in model._meta.fields:
            # Find related model for relation
            if hasattr(field, "target_model"):
                target_model  = field.target_model
                # Load class path
                if type(target_model) is str: target_model = import_class(target_model)
                # It's a searchable field !
                modelRules = rules.model(target_model).all()
                # Set it into the rules
                rules.model(model).field(field.name).add(is_searchable=modelRules["is_searchable"])
                rules.model(model).field(field.name).add(is_editable=modelRules["is_editable"])
    return rules

def import_or_create(path, register=True, force=False):
    try:
        # For the new module to be written
        if force:
            if path in sys.modules: del( sys.modules[path] )
            raise ImportError
        # Import the models.py file
        module = importlib.import_module(path)
    # File dosen't exist, we create it virtually!
    except ImportError:
        path_parts      = path.split(".")
        module          = imp.new_module(path)
        module.__name__ = path
        name            = path_parts[-1]
        # Register the new module in the global scope
        if register:
            # Get the parent module
            parent = import_or_create( ".".join( path_parts[0:-1]) )
            # Avoid memory leak
            if force and hasattr(parent, name):
                delattr(parent, name)
            # Register this module as attribute of its parent
            setattr(parent, name, module)
            # Register the virtual module
            sys.modules[path] = module
    return module


def reload_urlconf(urlconf=None):
    if urlconf is None:
        urlconf = settings.ROOT_URLCONF
    if urlconf in sys.modules:
        reload(sys.modules[urlconf])

def topic_models(path, force=False):
    """
        Auto-discover topic-related model by looking into
        a topic package for an ontology file. This will also
        create all api resources and endpoints.

        This will create the following modules:
            {path}
            {path}.models
            {path}.resources
            {path}.summary
            {path}.urls
    """
    topic_module = import_or_create(path, force=force)
    topic_name   = path.split(".")[-1]
    # Ensure that the topic's model exist
    topic = Topic.objects.get(module=topic_name)
    app_label = topic.app_label()
    # Add '.models to the path if needed
    models_path = path if path.endswith(".models") else '%s.models' % path
    urls_path   = "%s.urls" % path
    # Import or create virtually the models.py file
    models_module = import_or_create(models_path, force=force)
    if topic.ontology is None:
        directory     = os.path.dirname(os.path.realpath( models_module.__file__ ))
        # Path to the ontology file
        ontology = "%s/ontology.owl" % directory
    else:
        # Use the provided file
        ontology = topic.ontology
    try:
        # Generates all model using the ontology file.
        # Also overides the default app label to allow data persistance
        models = owl.parse(ontology, path, app_label=app_label)
        # Makes every model available through this module
        for m in models:
            # Record the model
            setattr(models_module, m, models[m])
    except TypeError:
        models = []
    except ValueError:
        models = []
    # Generates the API endpoints
    api = NamespacedApi(api_name='v1', urlconf_namespace=app_label)
    # Create resources root if needed
    resources = import_or_create("%s.resources" % path, force=force)
    # Creates a resource for each model
    for name in models:
        Resource = utils.create_model_resource(models[name])
        resource_name = "%sResource" % name
        # Register the virtual resource to by importa
        resource_path = "%s.resources.%s" % (path, resource_name)
        # This resource is now available everywhere:
        #  * as an attribute of `resources`
        #  * as a module
        setattr(resources, resource_name, Resource)
        sys.modules[resource_path] = Resource
        # And register it into the API instance
        api.register(Resource())
    # Every app have to instance a SummaryResource class
    summary_path   = "%s.summary" % path
    summary_module = import_or_create(summary_path, force=force)
    # Take the existing summary resource
    if hasattr(summary_module, 'SummaryResource'):
        SummaryResource = summary_module.SummaryResource
    # We create one if it doesn't exist
    else:
        from app.detective.topics.common.summary import SummaryResource as CommonSummaryResource
        attrs           = dict(meta=CommonSummaryResource.Meta)
        SummaryResource = type('SummaryResource', (CommonSummaryResource,), attrs)
    # Register the summary resource
    api.register(SummaryResource())
    # Create url patterns
    urlpatterns = patterns(path, url('', include(api.urls)), )
    # Import or create virtually the url path
    urls_modules = import_or_create(urls_path, force=force)
    # Merge the two url patterns if needed
    if hasattr(urls_modules, "urlpatterns"): urlpatterns += urls_modules.urlpatterns
    # Update the current url pattern
    urls_modules.urlpatterns = urlpatterns
    # API is now up and running,
    # we need to connect its url patterns to global one
    urls = importlib.import_module("app.detective.urls")
    # Add api url pattern with the highest priority
    new_patterns = patterns(app_label,
        url(r'^%s/' % topic.slug, include(urls_path, namespace=app_label) ),
    )
    if hasattr(urls, "urlpatterns"):
        # Merge with a filtered version of the urlpattern to avoid duplicates
        new_patterns += [u for u in urls.urlpatterns if getattr(u, "namespace", None) != topic.slug ]
    # Then update url pattern
    urls.urlpatterns = new_patterns
    # At last, force the url resolver to reload (because we update it)
    clear_url_caches()
    reload_urlconf()
    return topic_module
########NEW FILE########
__FILENAME__ = api
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app.detective.models                import Topic
from app.detective.topics.common.message import SaltMixin
from app.detective.topics.energy.models  import Organization, EnergyProject, Person, Country
from datetime                            import datetime
from django.conf                         import settings
from django.contrib.auth.models          import User, Group
from django.core                         import signing
from django.core.exceptions              import ObjectDoesNotExist
from django.core.files                   import File
from registration.models                 import RegistrationProfile
from tastypie.test                       import ResourceTestCase, TestApiClient
from tastypie.utils                      import timezone
import json
import urllib

def find(function, iterable):
    for el in iterable:
        if function(el) is True:
            return el
    return None

class ApiTestCase(ResourceTestCase):

    fixtures = ['app/detective/fixtures/search_terms.json',]

    def setUp(self):
        super(ApiTestCase, self).setUp()
        # Use custom api client
        self.api_client = TestApiClient()
        self.salt       = SaltMixin.salt

        self.super_username = 'super_user'
        self.super_password = 'super_user'
        self.super_email    = 'super_user@detective.io'

        self.contrib_username = 'contrib_user'
        self.contrib_password = 'contrib_user'
        self.contrib_email    = 'contrib_user@detective.io'

        self.lambda_username = 'lambda_user'
        self.lambda_password = 'lambda_user'
        self.lambda_email    = 'lambda_user@detective.io'

        contributors = Group.objects.get(name='energy_contributor')

        # Look for the test users
        try:
            # get users (superuser, contributor & lambda user)
            super_user   = User.objects.get(username=self.super_username)
            contrib_user = User.objects.get(username=self.contrib_username)
            lambda_user  = User.objects.get(username=self.lambda_username)

            # fixtures & test data
            self.jpp  = Organization.objects.filter(name=u"Journalism++")[0]
            self.jg   = Organization.objects.filter(name=u"Journalism Grant")[0]
            self.fra  = Country.objects.get(name=u"France")
            self.pr   = Person.objects.get(name=u"Pierre Roméra")
            self.pb   = Person.objects.get(name=u"Pierre Bellon")
            self.common = Topic.objects.get(slug=u"common")
            self.christmas = Topic.objects.get(slug=u"christmas")

        except ObjectDoesNotExist:
            # Create the new user users
            super_user = User.objects.create(
                username=self.super_username,
                email=self.super_email,
            )
            super_user.set_password(self.super_password)
            super_user.save()

            contrib_user = User.objects.create(
                username=self.contrib_username,
                email=self.contrib_email,
            )
            contrib_user.set_password(self.contrib_password)
            contrib_user.save()

            lambda_user = User.objects.create(
                username=self.lambda_username,
                email=self.lambda_email,
            )
            lambda_user.set_password(self.lambda_password)
            lambda_user.save()

            # Create related objects
            self.jpp = Organization(name=u"Journalism++")
            self.jpp.save()
            self.jg  = Organization(name=u"Journalism Grant")
            self.jg.save()
            self.fra = Country(name=u"France", isoa3=u"FRA")
            self.fra.save()
            self.pr = Person(name=u"Pierre Roméra")
            self.pr.save()
            self.pb = Person(name=u"Pierre Bellon")
            self.pb.save()

            ontology = File(open(settings.DATA_ROOT + "/ontology-v5.7.owl"))
            self.christmas = Topic(slug=u"christmas", title="It's christmas!", ontology=ontology, author=super_user)
            self.christmas.save()
            self.thanksgiving = Topic(slug=u"thanksgiving", title="It's thanksgiving!", ontology=ontology, author=super_user)
            self.thanksgiving.save()



        super_user.is_staff = True
        super_user.is_superuser = True
        super_user.save()

        contrib_user.is_active = True
        contrib_user.groups.add(contributors)
        contrib_user.save()

        self.jpp._author = [super_user.pk]
        self.jpp.founded = datetime(2011, 4, 3)
        self.jpp.website_url = 'http://jplusplus.com'
        self.jpp.save()

        self.jg._author = [super_user.pk]
        self.jg.save()

        self.pr.based_in.add(self.fra)
        self.pr.activity_in_organization.add(self.jpp)
        self.pr.save()

        self.pb.based_in.add(self.fra)
        self.pb.activity_in_organization.add(self.jpp)
        self.pb.save()

        self.super_user = super_user
        self.contrib_user = contrib_user
        self.lambda_user = lambda_user

        self.post_data_simple = {
            "name": "Lorem ispum TEST",
            "twitter_handle": "loremipsum"
        }

        self.post_data_related = {
            "name": "Lorem ispum TEST RELATED",
            "owner": [
                { "id": self.jpp.id },
                { "id": self.jg.id }
            ],
            "activity_in_country": [
                { "id": self.fra.id }
            ]
        }
        self.rdf_jpp = {
            "label": u"Person that has activity in Journalism++",
            "object": {
                "id": 283,
                "model": u"Organization",
                "name": u"Journalism++"
            },
            "predicate": {
                "label": u"has activity in",
                "name": u"activity_in_organization",
                "subject": u"Person"
            },
            "subject": {
                "label": u"Person",
                "name": u"Person"
            }
        }

    def cleanModel(self, model_instance):
        if model_instance:
            model_instance.delete()

    def tearDown(self):
        # Clean & delete generated data
        # users
        self.cleanModel(self.super_user)
        self.cleanModel(self.contrib_user)
        self.cleanModel(self.lambda_user)
        # individuals
        self.cleanModel(self.jpp)  # organization
        self.cleanModel(self.jg)   # organization
        self.cleanModel(self.fra)  # country
        self.cleanModel(self.pr)   # people
        self.cleanModel(self.pb)   # people
        # topics
        self.cleanModel(self.christmas)
        self.cleanModel(self.thanksgiving)

    # Utility functions (Auth, operation etc.)
    def login(self, username, password):
        return self.api_client.client.login(username=username, password=password)

    def get_super_credentials(self):
        return self.login(self.super_username, self.super_password)

    def get_contrib_credentials(self):
        return self.login(self.contrib_username, self.contrib_password)

    def get_lambda_credentials(self):
        return self.login(self.lambda_username, self.lambda_password)

    def signup_user(self, user_dict):
        """ Utility method to signup through API """
        return self.api_client.post('/api/common/v1/user/signup/', format='json', data=user_dict)

    def patch_individual(self, scope=None, model_name=None, model_id=None,
                         patch_data=None, auth=None, skipAuth=False):
        if not skipAuth and not auth:
            auth = self.get_super_credentials()
        url = '/api/%s/v1/%s/%d/patch/' % (scope, model_name, model_id)
        return self.api_client.post(url, format='json', data=patch_data, authentication=auth)

    def check_permissions(self, permissions=None, user=None):
        user_permissions = list(user.get_all_permissions())
        self.assertEqual(len(user_permissions), len(permissions))
        for perm in user_permissions:
            self.assertTrue(perm in permissions)

    # All test functions
    def test_user_signup_succeed(self):
        """
        Test with proper data to signup user
        Expected: HTTT 201 (Created)
        """
        user_dict = dict(username=u"newuser", password=u"newuser", email=u"newuser@detective.io")
        resp = self.signup_user(user_dict)
        self.assertHttpCreated(resp)

    def test_user_signup_empty_data(self):
        """
        Test with empty data to signup user
        Expected: HTTP 400 (BadRequest)
        """
        user_dict = dict(username=u"", password=u"", email=u"")
        resp = self.signup_user(user_dict)
        self.assertHttpBadRequest(resp)

    def test_user_signup_no_data(self):
        resp = self.api_client.post('/api/common/v1/user/signup/', format='json')
        self.assertHttpBadRequest(resp)

    def test_user_signup_existing_user(self):
        user_dict = dict(username=self.super_username, password=self.super_password, email=self.super_email)
        resp = self.signup_user(user_dict)
        self.assertHttpForbidden(resp)

    def test_user_activate_succeed(self):
        user_dict = dict(username='myuser', password='mypassword', email='myuser@mywebsite.com')
        self.assertHttpCreated(self.signup_user(user_dict))
        innactive_user = User.objects.get(email=user_dict.get('email'))
        activation_profile = RegistrationProfile.objects.get(user=innactive_user)
        activation_key = activation_profile.activation_key
        resp_activate = self.api_client.get('/api/common/v1/user/activate/?token=%s' % activation_key)
        self.assertHttpOK(resp_activate)
        user = User.objects.get(email=user_dict.get('email'))
        self.assertTrue(user.is_active)

    def test_user_activate_fake_token(self):
        resp = self.api_client.get('/api/common/v1/user/activate/?token=FAKE')
        self.assertHttpForbidden(resp)

    def test_user_activate_no_token(self):
        resp = self.api_client.get('/api/common/v1/user/activate/')
        self.assertHttpBadRequest(resp)

    def test_user_activate_empty_token(self):
        resp = self.api_client.get('/api/common/v1/user/activate/?token')
        self.assertHttpBadRequest(resp)

    def test_user_contrib_login_succeed(self):
        auth = dict(username=self.contrib_username, password=self.contrib_password)
        resp = self.api_client.post('/api/common/v1/user/login/', format='json', data=auth)
        self.assertValidJSON(resp.content)
        data = json.loads(resp.content)
        self.assertTrue(data["success"])
        self.check_permissions(permissions=data.get("permissions"), user=self.contrib_user)

    def test_user_login_succeed(self):
        auth = dict(username=self.super_username, password=self.super_password)
        resp = self.api_client.post('/api/common/v1/user/login/', format='json', data=auth)
        self.assertValidJSON(resp.content)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        self.assertEqual(data["success"], True)

    def test_user_login_failed(self):
        auth = dict(username=self.super_username, password=u"awrongpassword")
        resp = self.api_client.post('/api/common/v1/user/login/', format='json', data=auth)
        self.assertValidJSON(resp.content)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        self.assertEqual(data["success"], False)

    def test_user_logout_succeed(self):
        # First login
        auth = dict(username=self.super_username, password=self.super_password)
        self.api_client.post('/api/common/v1/user/login/', format='json', data=auth)
        # Then logout
        resp = self.api_client.get('/api/common/v1/user/logout/', format='json')
        self.assertValidJSON(resp.content)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        self.assertEqual(data["success"], True)

    def test_user_logout_failed(self):
        resp = self.api_client.get('/api/common/v1/user/logout/', format='json')
        self.assertValidJSON(resp.content)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        self.assertEqual(data["success"], False)

    def test_user_permissions_is_logged(self):
        auth = dict(username=self.contrib_username, password=self.contrib_password)
        self.api_client.post('/api/common/v1/user/login/', format='json', data=auth)
        resp = self.api_client.get('/api/common/v1/user/permissions/', format='json')
        self.assertValidJSON(resp.content)
        data = json.loads(resp.content)
        self.check_permissions(permissions=data.get("permissions"), user=self.contrib_user)

    def test_user_permissions_isnt_logged(self):
        resp = self.api_client.get('/api/common/v1/user/permissions/', format='json')
        self.assertHttpUnauthorized(resp)


    def test_user_status_isnt_logged(self):
        resp = self.api_client.get('/api/common/v1/user/status/', format='json')
        self.assertValidJSON(resp.content)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        self.assertEqual(data["is_logged"], False)

    def test_user_status_is_logged(self):
        # Log in
        auth = dict(username=self.super_username, password=self.super_password)
        resp = self.api_client.post('/api/common/v1/user/login/', format='json', data=auth)
        self.assertValidJSON(resp.content)
        data = json.loads(resp.content)
        self.assertTrue(data['success'])

        resp = self.api_client.get('/api/common/v1/user/status/', format='json')
        self.assertValidJSON(resp.content)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        self.assertEqual(data["is_logged"], True)

    def test_contrib_user_status_is_logged(self):
        # Log in
        auth = dict(username=self.contrib_username, password=self.contrib_password, remember_me=True)
        resp = self.api_client.post('/api/common/v1/user/login/', format='json', data=auth)
        self.assertValidJSON(resp.content)
        data = json.loads(resp.content)
        self.assertTrue(data['success'])

        resp = self.api_client.get('/api/common/v1/user/status/', format='json')
        self.assertValidJSON(resp.content)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        self.assertEqual(data["is_logged"], True)


    def test_reset_password_success(self):
        email = dict(email=self.super_email)
        resp = self.api_client.post('/api/common/v1/user/reset_password/', format='json', data=email)
        self.assertValidJSON(resp.content)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        self.assertTrue(data['success'])

    def test_reset_password_wrong_email(self):
        email = dict(email="wrong_email@detective.io")
        resp = self.api_client.post('/api/common/v1/user/reset_password/', format='json', data=email)
        self.assertEqual(resp.status_code in [302, 404], True)

    def test_reset_password_no_data(self):
        resp = self.api_client.post('/api/common/v1/user/reset_password/', format='json')
        self.assertHttpBadRequest(resp)

    def test_reset_password_empty_email(self):
        resp = self.api_client.post('/api/common/v1/user/reset_password/', format='json', data=dict(email=''))
        self.assertHttpBadRequest(resp)

    def test_reset_password_confirm_succes(self):
        """
        Test to successfuly reset a password with a new one.
        Expected:
            HTTP 200 - OK
        """
        token = signing.dumps(self.super_user.pk, salt=self.salt)
        password = "testtest"
        auth = dict(password=password, token=token)
        resp = self.api_client.post(
                '/api/common/v1/user/reset_password_confirm/',
                format='json',
                data=auth
            )
        self.assertValidJSON(resp.content)
        data = json.loads(resp.content)
        self.assertTrue(data['success'])
        # we query users to get the latest user object (updated with password)
        user = User.objects.get(email=self.super_user.email)
        self.assertTrue(user.check_password(password))

    def test_reset_password_confirm_no_data(self):
        """
        Test on reset_password_confirm API endpoint without any data.
        Expected response:
            HTTP 400 (BadRequest).
        Explanation:
            Every request on /reset_password_confirm/ must have a JSON data payload.
            {
                password: ... // the password to reset"
                token:    ... // the reset password token (received by emai)
            }
        """
        resp = self.api_client.post('/api/common/v1/user/reset_password_confirm/', format='json')
        self.assertHttpBadRequest(resp)
        self.assertIsNotNone(resp.content)

    def test_reset_password_confirm_empty_data(self):
        """
        Test on reset_password_confirm API endpoint with empty data:
        {
            password: ""
            token: ""
        }
        Expected result:
            HTTP 400 (BadRequest)
        Explanation:
            A reset_password_confirm request must have a password and should be
            authenticated with a token.
        """
        auth = dict(password='', token='')
        resp = self.api_client.post('/api/common/v1/user/reset_password_confirm/', format='json', data=auth)
        self.assertHttpBadRequest(resp)

    def test_reset_password_confirm_fake_token(self):
        """
        Test on reset_password_confirm API endpoint with empty data:
        {
            password: ""
            token: ""
        }
        Expected result:
            HTTP 403 (Forbidden)
        Explanation:
            A reset_password_confirm request should be authenticated with a valid
            token.
        """
        fake_token = 'f4k:t0k3N'
        auth = dict(password='newpassword', token=fake_token)
        resp = self.api_client.post(
                '/api/common/v1/user/reset_password_confirm/',
                format='json',
                data=auth
            )
        self.assertHttpForbidden(resp)

    def test_get_list_json(self):
        resp = self.api_client.get('/api/energy/v1/energyproject/?limit=20', format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)
        # Number of element on the first page
        count = min(20, EnergyProject.objects.count())
        self.assertEqual( len(self.deserialize(resp)['objects']), count)

    def test_post_list_unauthenticated(self):
        self.assertHttpUnauthorized(self.api_client.post('/api/energy/v1/energyproject/', format='json', data=self.post_data_simple))

    def test_post_list_staff(self):
        # Check how many are there first.
        count = EnergyProject.objects.count()
        self.assertHttpCreated(
            self.api_client.post('/api/energy/v1/energyproject/',
                format='json',
                data=self.post_data_simple,
                authentication=self.get_super_credentials()
            )
        )
        # Verify a new one has been added.
        self.assertEqual(EnergyProject.objects.count(), count+1)

    def test_post_list_contributor(self):
        # Check how many are there first.
        count = EnergyProject.objects.count()
        self.assertHttpCreated(
            self.api_client.post('/api/energy/v1/energyproject/',
                format='json',
                data=self.post_data_simple,
                authentication=self.get_contrib_credentials()
            )
        )
        # Verify a new one has been added.
        self.assertEqual(EnergyProject.objects.count(), count+1)

    def test_post_list_lambda(self):
        self.assertHttpUnauthorized(
            self.api_client.post('/api/energy/v1/energyproject/',
                format='json',
                data=self.post_data_simple,
                authentication=self.get_lambda_credentials()
            )
        )

    def test_post_list_related(self):
        # Check how many are there first.
        count = EnergyProject.objects.count()
        # Record API response to extract data
        resp  = self.api_client.post('/api/energy/v1/energyproject/',
            format='json',
            data=self.post_data_related,
            authentication=self.get_super_credentials()
        )
        # Vertify the request status
        self.assertHttpCreated(resp)
        # Verify a new one has been added.
        self.assertEqual(EnergyProject.objects.count(), count+1)
        # Are the data readable?
        self.assertValidJSON(resp.content)
        # Parse data to verify relationship
        data = json.loads(resp.content)
        self.assertEqual(len(data["owner"]), len(self.post_data_related["owner"]))
        self.assertEqual(len(data["activity_in_country"]), len(self.post_data_related["activity_in_country"]))

    def test_mine(self):
        resp = self.api_client.get('/api/energy/v1/energyproject/mine/', format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        self.assertEqual(
            min(20, len(data["objects"])),
            EnergyProject.objects.filter(_author__contains=self.super_user.id).count()
        )

    def test_search_organization(self):
        resp = self.api_client.get('/api/energy/v1/organization/search/?q=Journalism', format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        # At least 2 results
        self.assertGreater( len(data.items()), 1 )

    def test_search_organization_wrong_page(self):
        resp = self.api_client.get('/api/energy/v1/organization/search/?q=Roméra&page=10000', format='json', authentication=self.get_super_credentials())
        self.assertEqual(resp.status_code in [302, 404], True)

    def test_cypher_detail(self):
        resp = self.api_client.get('/api/common/v1/cypher/111/', format='json', authentication=self.get_super_credentials())
        self.assertTrue(resp.status_code in [302, 404])

    def test_cypher_unauthenticated(self):
        self.assertHttpUnauthorized(self.api_client.get('/api/common/v1/cypher/?q=START%20n=node%28*%29RETURN%20n;', format='json'))

    def test_cypher_unauthorized(self):
        # Ensure the user isn't authorized to process cypher request
        self.super_user.is_staff = True
        self.super_user.is_superuser = False
        self.super_user.save()

        self.assertHttpUnauthorized(self.api_client.get('/api/common/v1/cypher/?q=START%20n=node%28*%29RETURN%20n;', format='json', authentication=self.get_super_credentials()))

    def test_cypher_authorized(self):
        # Ensure the user IS authorized to process cypher request
        self.super_user.is_superuser = True
        self.super_user.save()

        self.assertValidJSONResponse(self.api_client.get('/api/common/v1/cypher/?q=START%20n=node%28*%29RETURN%20n;', format='json', authentication=self.get_super_credentials()))

    def test_summary_list(self):
        resp = self.api_client.get('/api/common/v1/summary/', format='json')
        self.assertEqual(resp.status_code in [302, 404], True)

    def test_summary_mine_success(self):
        resp = self.api_client.get('/api/energy/v1/summary/mine/', authentication=self.get_super_credentials(), format='json')
        self.assertValidJSONResponse(resp)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        objects = data['objects']
        self.assertIsNotNone(find(lambda x: x['label'] == self.jpp.name, objects))
        self.assertIsNotNone(find(lambda x: x['label'] == self.jg.name,  objects))

    def test_summary_mine_unauthenticated(self):
        self.assertHttpUnauthorized(self.api_client.get('/api/common/v1/summary/mine/', format='json'))

    def test_countries_summary(self):
        resp = self.api_client.get('/api/energy/v1/summary/countries/', format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        # Only France is present
        self.assertGreater(len(data), 0)
        # We added 1 relation to France
        self.assertEqual("count" in data["FRA"], True)

    def test_forms_summary(self):
        resp = self.api_client.get('/api/energy/v1/summary/forms/', format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        # As many descriptors as models
        self.assertEqual( 11, len(data.items()) )

    def test_types_summary(self):
        resp = self.api_client.get('/api/energy/v1/summary/types/', format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)

    def test_search_summary(self):
        resp = self.api_client.get('/api/energy/v1/summary/search/?q=Journalism', format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)
        # Parse data to check the number of result
        data = json.loads(resp.content)
        # At least 2 results
        self.assertGreater( len(data.items()), 1 )

    def test_search_summary_wrong_page(self):
        resp = self.api_client.get('/api/energy/v1/summary/search/?q=Journalism&page=-1', format='json', authentication=self.get_super_credentials())
        self.assertEqual(resp.status_code in [302, 404], True)

    def test_summary_human_search(self):
        query = "Person activity in Journalism"
        resp = self.api_client.get('/api/energy/v1/summary/human/?q=%s' % query, format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)
        data = json.loads(resp.content)
        self.assertGreater(len(data['objects']), 1)

    def test_rdf_search(self):
        # RDF object for persons that have activity in J++, we need to urlencode
        # the JSON string to avoid '+' loss
        rdf_str = urllib.quote(json.dumps(self.rdf_jpp))
        url = '/api/energy/v1/summary/rdf_search/?limit=20&offset=0&q=%s' % rdf_str
        resp = self.api_client.get(url, format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)
        data = json.loads(resp.content)
        objects = data['objects']
        self.assertIsNotNone(find(lambda x: x['name'] == self.pr.name, objects))
        self.assertIsNotNone(find(lambda x: x['name'] == self.pb.name, objects))

    def test_patch_individual_date_staff(self):
        """
        Test a patch request on an invidividual's date attribute.
        Request: /api/energy/v1/organization/
        Expected: HTTP 200 (OK)
        """
        # date are subject to special process with patch method.
        new_date  = datetime(2011, 4, 1, 0, 0, 0, 0)
        data = {
            'founded': new_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        }
        args = {
            'scope'      : 'energy',
            'model_id'   : self.jpp.id,
            'model_name' : 'organization',
            'patch_data' : data
        }
        resp = self.patch_individual(**args)
        self.assertHttpOK(resp)
        self.assertValidJSONResponse(resp)
        updated_jpp = Organization.objects.get(name=self.jpp.name)
        self.assertEqual(timezone.make_naive(updated_jpp.founded), new_date)

    def test_patch_individual_website_staff(self):
        jpp_url  = 'http://jplusplus.org'
        data = {
            'website_url': jpp_url,
        }
        args = {
            'scope'      : 'energy',
            'model_id'   : self.jpp.id,
            'model_name' : 'organization',
            'patch_data' : data
        }
        resp = self.patch_individual(**args)
        self.assertHttpOK(resp)
        self.assertValidJSONResponse(resp)
        updated_jpp = Organization.objects.get(name=self.jpp.name)
        self.assertEqual(updated_jpp.website_url, jpp_url)

    def test_patch_individual_website_unauthenticated(self):
        jpp_url  = 'http://jplusplus.org'
        data = {
            'website_url': jpp_url,
        }
        args = {
            'scope'      : 'energy',
            'model_id'   : self.jpp.id,
            'model_name' : 'organization',
            'patch_data' : data,
            'skipAuth'   : True,
        }
        resp = self.patch_individual(**args)
        self.assertHttpUnauthorized(resp)

    def test_patch_individual_website_contributor(self):
        jpp_url  = 'http://www.jplusplus.org'
        data = {
            'website_url': jpp_url,
        }
        args = {
            'scope'      : 'energy',
            'model_id'   : self.jpp.id,
            'model_name' : 'organization',
            'patch_data' : data,
            'auth'       : self.get_contrib_credentials(),
        }
        resp = self.patch_individual(**args)
        self.assertHttpOK(resp)
        self.assertValidJSONResponse(resp)
        updated_jpp = Organization.objects.filter(name=self.jpp.name)[0]
        self.assertEqual(updated_jpp.website_url, jpp_url)

    def test_patch_individual_website_lambda(self):
        jpp_url  = 'http://bam.jplusplus.org'
        data = {
            'website_url': jpp_url,
        }
        args = {
            'scope'      : 'energy',
            'model_id'   : self.jpp.id,
            'model_name' : 'organization',
            'patch_data' : data,
            'auth'       : self.get_lambda_credentials(),
        }
        resp = self.patch_individual(**args)
        self.assertHttpUnauthorized(resp)


    def test_patch_individual_not_found(self):
        jpp_url  = 'http://jplusplus.org'
        data = {
            'website_url': jpp_url,
        }
        args = {
            'scope'      : 'energy',
            'model_id'   : 1337,
            'model_name' : 'organization',
            'patch_data' : data,
        }
        resp = self.patch_individual(**args)
        self.assertEqual(resp.status_code in [302, 404], True)

    def test_topic_endpoint_exists(self):
        resp = self.api_client.get('/api/common/v1/topic/?slug=christmas', follow=True, format='json')
        # Parse data to check the number of result
        data = json.loads(resp.content)
        # 1 result
        self.assertEqual( len( data["objects"] ), 1 )

    def test_topic_api_exists(self):
        resp = self.api_client.get('/api/christmas/v1/', format='json')
        self.assertValidJSONResponse(resp)

    def test_topic_has_person(self):
        resp = self.api_client.get('/api/christmas/v1/', format='json')
        self.assertValidJSONResponse(resp)

    def test_topic_multiple_api(self):
        # API 1
        resp = self.api_client.get('/api/christmas/v1/', format='json')
        self.assertValidJSONResponse(resp)
        # API 2
        resp = self.api_client.get('/api/thanksgiving/v1/', format='json')
        self.assertValidJSONResponse(resp)

    def test_topic_has_summary_syntax_from_ontology(self):
        resp = self.api_client.get('/api/christmas/v1/summary/syntax/', format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)

    def test_topic_has_summary_syntax_from_file(self):
        resp = self.api_client.get('/api/energy/v1/summary/syntax/', format='json', authentication=self.get_super_credentials())
        self.assertValidJSONResponse(resp)
########NEW FILE########
__FILENAME__ = commands
from app.detective.topics.energy.models import Country
from django.core.management             import call_command
from django.core.management.base        import CommandError
from django.test                        import TestCase
from neo4django.graph_auth.models       import User as GraphUser
from django.contrib.auth.models         import User
from StringIO                           import StringIO
import sys

class CommandsTestCase(TestCase):
    def setUp(self):
        super(CommandsTestCase, self).setUp()
        try:
            self.toto = GraphUser.objects.get(email='toto@detective.io')
        except GraphUser.DoesNotExist:
            self.toto = GraphUser.objects.create(username='toto', email='toto@detective.io')
            self.toto.set_password('tttooo')
            self.toto.save()

    def tearDown(self):
        if self.toto:
            self.toto.delete()

    def test_parseowl_fail(self):
        # Catch output
        output = StringIO()
        sys.stdout = output
        # Must fail without argument
        with self.assertRaises(CommandError):
            call_command('parseowl')

    def test_parseowl(self):
        # Catch output
        output = StringIO()
        sys.stdout = output
        args = "./app/data/ontology-v5.3.owl"
        call_command('parseowl', args)

    def test_loadnodes_fail(self):
        # Catch output
        output = StringIO()
        sys.stdout = output
        # Must fail without argument
        with self.assertRaises(CommandError):
            call_command('loadnodes')

    def test_loadnodes(self):
        # Catch output
        output = StringIO()
        sys.stdout = output
        # Import countries
        args = "./app/detective/topics/energy/fixtures/countries.json"
        call_command('loadnodes', args)
        # Does France exists?
        self.assertGreater(len( Country.objects.filter(isoa3="FRA") ), 0)

    def test_importusers(self):
        # Catch output
        output = StringIO()
        sys.stdout = output
        # Import users
        call_command('importusers')
        users = User.objects
        self.assertEqual(len(users.all()), len(GraphUser.objects.all()))
        self.assertIsNotNone(users.get(email=self.toto.email))

    def test_reindex(self):
        c = Country(name="France", isoa3="FRA")
        c.save()
        # Catch output
        output = StringIO()
        sys.stdout = output
        # Reindex countries
        args = 'energy.Country'
        call_command('reindex', args)

########NEW FILE########
__FILENAME__ = front
import unittest
from django.test import Client

class FrontTestCase(unittest.TestCase):

    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_home(self):
        # Issue a GET request.
        response = self.client.get('/')
        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)

    def test_partial_exists(self):
        # Issue a GET request.
        response = self.client.get('/partial/account.login.html')
        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)

    def test_login(self):
        from django.contrib.auth.models import User
        from django.core.exceptions import ObjectDoesNotExist
        # Look for the test user
        self.username  = 'tester'
        self.password  = 'tester'
        try:
            self.user = User.objects.get(username=self.username)
        except ObjectDoesNotExist:
            # Create the new user
            self.user = User.objects.create_user(self.username, 'tester@detective.io', self.password)
            self.user.is_staff = True
            self.user.save()

        self.client.login(username=self.username, password=self.password)
        # Issue a GET request.
        response = self.client.get('/')
        # Check that the user is loged
        self.assertEqual( eval(response.cookies["user__is_logged"].value), True )
        # Check that the user is staff
        self.assertEqual( eval(response.cookies["user__is_staff"].value), self.user.is_staff )
        # Check that the username is correct
        self.assertEqual( response.cookies["user__username"].value, self.user.username )
        # Logout the user
        self.client.logout()
        # Issue a GET request.
        response = self.client.get('/')
        # Ensure the cookie is deleted
        self.assertEqual( hasattr(response.cookies, "user__is_logged"), False )

#EOF

########NEW FILE########
__FILENAME__ = cypher
from django.http             import Http404, HttpResponse
from tastypie.exceptions     import ImmediateHttpResponse
from tastypie.authentication import SessionAuthentication, BasicAuthentication, MultiAuthentication
from tastypie.authorization  import Authorization
from tastypie.resources      import Resource
from tastypie.serializers    import Serializer
from neo4django.db           import connection

class CypherResource(Resource):
    # Local serializer
    serializer = Serializer(formats=["json"]).serialize

    class Meta:
        authorization   = Authorization()
        authentication  = MultiAuthentication(BasicAuthentication(), SessionAuthentication())
        allowed_methods = ['get']
        resource_name   = 'cypher'
        object_class    = object

    def obj_get_list(self, request=None, **kwargs):
        request = kwargs["bundle"].request if request == None else request
        # Super user only
        if not request.user.is_superuser:
            # We force tastypie to render the response directly
            raise ImmediateHttpResponse(response=HttpResponse('Unauthorized', status=401))
        query = request.GET["q"];
        data  = connection.cypher(query).to_dicts()
        # Serialize content in json
        # @TODO implement a better format support
        content  = self.serializer(data, "application/json")
        # Create an HTTP response
        response = HttpResponse(content=content, content_type="application/json")
        # We force tastypie to render the response directly
        raise ImmediateHttpResponse(response=response)

    def obj_get(self, request=None, **kwargs):
        # Nothing yet here!
        raise Http404("Sorry, no results on that page.")

########NEW FILE########
__FILENAME__ = errors
class MalformedRequestError(KeyError):
    pass

class ForbiddenError(StandardError):
    pass

class UnauthorizedError(StandardError): 
    pass
########NEW FILE########
__FILENAME__ = job
#!/usr/bin/env python
# Encoding: utf-8
# -----------------------------------------------------------------------------
# Project : Detective.io
# -----------------------------------------------------------------------------
# Author : Edouard Richard                                  <edou4rd@gmail.com>
# -----------------------------------------------------------------------------
# License : GNU GENERAL PUBLIC LICENSE v3
# -----------------------------------------------------------------------------
# Creation : 20-Jan-2014
# Last mod : 20-Jan-2014
# -----------------------------------------------------------------------------
from tastypie.resources import Resource
from tastypie           import fields
from rq.job             import Job
import django_rq
import json

class Document(object):
    def __init__(self, *args, **kwargs):
        self._id = None
        for key, value in kwargs.iteritems():
            setattr(self, key, value)
        if hasattr(self,'_result') and self._result:
            result = json.dumps(self._result)
            self._result = result

class JobResource(Resource):
    id         = fields.CharField(attribute="_id")
    result     = fields.CharField(attribute="_result"    , null=True)
    meta       = fields.CharField(attribute="meta"       , null=True)
    status     = fields.CharField(attribute="_status"    , null=True)
    created_at = fields.CharField(attribute="created_at" , null=True)
    timeout    = fields.CharField(attribute="timeout"    , null=True)

    def obj_get(self, bundle, **kwargs):
        """
        Returns redis document from provided id.
        """
        queue = django_rq.get_queue('default')
        job = Job.fetch(kwargs['pk'], connection=queue.connection)
        return Document(**job.__dict__)

    class Meta:
        resource_name          = "jobs"
        include_resource_uri   = False
        list_allowed_methods   = []
        detail_allowed_methods = ["get"]

# EOF

########NEW FILE########
__FILENAME__ = message
from django.core.mail import EmailMultiAlternatives, get_connection, send_mail


from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.core import signing
from django.template import loader
from django.views import generic

from password_reset.forms import PasswordRecoveryForm
from password_reset.views import Reset


# Monkey patching for Recover (took from `password_reset.views`), now it use the
# newest version of send_mail, see below
class SaltMixin(object):
    salt = 'password_recovery'
    url_salt = 'password_recovery_url'

class Recover(SaltMixin, generic.FormView):
    case_sensitive = True
    form_class = PasswordRecoveryForm
    template_name = 'password_reset/recovery_form.html'
    email_template_name = 'password_reset/recovery_email.txt'
    email_subject_template_name = 'password_reset/recovery_email_subject.txt'
    search_fields = ['username', 'email']

    def get_success_url(self):
        return reverse('password_reset_sent', args=[self.mail_signature])

    def expires(self):
        # returns the number of days for token validity
        return Reset().token_expires / (24 * 3600)

    def send_notification(self):
        context = {
            'site':   RequestSite(self.request),
            'user':   self.user,
            'token':  signing.dumps(self.user.pk, salt=self.salt),
            'secure': self.request.is_secure(),
            'expiration_days': self.expires()
        }
        body = loader.render_to_string(self.email_template_name,
                                       context).strip()
        subject = loader.render_to_string(self.email_subject_template_name,
                                          context).strip()
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL,
                  [self.user.email])

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = resources
# -*- coding: utf-8 -*-
from .models                          import *
from app.detective.models             import QuoteRequest, Topic, Article
from app.detective.utils              import get_registered_models
from app.detective.topics.common.user import UserResource
from tastypie                         import fields
from tastypie.authorization           import ReadOnlyAuthorization
from tastypie.constants               import ALL, ALL_WITH_RELATIONS
from tastypie.exceptions              import Unauthorized
from tastypie.resources               import ModelResource

# Only staff can consult QuoteRequests
class QuoteRequestAuthorization(ReadOnlyAuthorization):
    def read_list(self, object_list, bundle):
        user = bundle.request.user
        if user and user.is_staff:
            return object_list
        else:
            raise Unauthorized("Only staff user can access to the quote requests.")
    def read_detail(self, object_list, bundle):
        user = bundle.request.user
        return user and user.is_staff
    # But anyone can create a QuoteRequest
    def create_detail(self, object_list, bundle):
        return True

class QuoteRequestResource(ModelResource):
    class Meta:
        authorization = QuoteRequestAuthorization()
        queryset      = QuoteRequest.objects.all()

class TopicResource(ModelResource):

    author = fields.ToOneField(UserResource, 'author', full=False, null=True)

    class Meta:
        queryset = Topic.objects.all()
        filtering = {'slug': ALL, 'author': ALL_WITH_RELATIONS, 'module': ALL, 'public': ALL, 'title': ALL}

    def dehydrate(self, bundle):
        # Get all registered models
        models = get_registered_models()
        in_topic = lambda m: m.__module__.startswith("app.detective.topics.%s." % bundle.obj.module)
        # Filter model to the one under app.detective.topics
        bundle.data["models"] = [ m.__name__ for m in models if in_topic(m) ]
        # Every topic has a single permalink
        bundle.data['link']   = bundle.obj.get_absolute_path()
        return bundle

    def get_object_list(self, request):
        is_staff    = request.user and request.user.is_staff
        object_list = super(TopicResource, self).get_object_list(request)
        # Return only public topics for non-staff user
        return object_list if is_staff else object_list.filter(public=True)


class ArticleResource(ModelResource):
    topic = fields.ToOneField(TopicResource, 'topic', full=True)
    class Meta:
        authorization = ReadOnlyAuthorization()
        queryset      = Article.objects.filter(public=True)
        filtering     = {'slug': ALL, 'topic': ALL_WITH_RELATIONS, 'public': ALL, 'title': ALL}

########NEW FILE########
__FILENAME__ = summary
# -*- coding: utf-8 -*-
from app.detective.models     import Topic, SearchTerm
from app.detective.neomatch   import Neomatch
from app.detective.register   import topics_rules
from difflib                  import SequenceMatcher
from django.core.paginator    import Paginator, InvalidPage
from django.core.urlresolvers import resolve
from django.http              import Http404, HttpResponse
from neo4django.db            import connection
from tastypie                 import http
from tastypie.exceptions      import ImmediateHttpResponse
from tastypie.resources       import Resource
from tastypie.serializers     import Serializer
from django.utils.timezone    import utc
from psycopg2.extensions      import adapt

import app.detective.utils    as utils
import json
import re
import datetime
import logging
import django_rq
from .errors import *

# Get an instance of a logger
logger = logging.getLogger(__name__)

class SummaryResource(Resource):
    # Local serializer
    serializer = Serializer(formats=["json"]).serialize

    class Meta:
        allowed_methods = ['get', 'post']
        resource_name   = 'summary'
        object_class    = object

    def obj_get_list(self, request=None, **kwargs):
        # Nothing yet here!
        raise Http404("Sorry, not implemented yet!")

    def obj_get(self, request=None, **kwargs):
        content = {}
        # Refresh syntax cache at each request
        if hasattr(self, "syntax"): delattr(self, "syntax")
        # Get the current topic
        self.topic = self.get_topic_or_404(request=request)
        # Check for an optional method to do further dehydration.
        method = getattr(self, "summary_%s" % kwargs["pk"], None)

        if method:
            try:
                self.throttle_check(kwargs["bundle"].request)
                content = method(kwargs["bundle"], kwargs["bundle"].request)
                # Serialize content in json
                # @TODO implement a better format support
                content  = self.serializer(content, "application/json")
                # Create an HTTP response
                response = HttpResponse(content=content, content_type="application/json")
            except ForbiddenError as e:
                response = http.HttpForbidden(e)
            except UnauthorizedError as e:
                response = http.HttpUnauthorized(e)
        else:
            # Stop here, unkown summary type
            raise Http404("Sorry, not implemented yet!")
        # We force tastypie to render the response directly
        raise ImmediateHttpResponse(response=response)

    # TODO : factorize obj_get and post_detail methods
    def post_detail(self, request=None, **kwargs):
        content = {}
        # Get the current topic
        self.topic = self.get_topic_or_404(request=request)
        # Check for an optional method to do further dehydration.
        method = getattr(self, "summary_%s" % kwargs["pk"], None)
        if method:
            try:
                self.throttle_check(request)
                content = method(request, **kwargs)
                # Serialize content in json
                # @TODO implement a better format support
                content  = self.serializer(content, "application/json")
                # Create an HTTP response
                response = HttpResponse(content=content, content_type="application/json")
            except ForbiddenError as e:
                response = http.HttpForbidden(e)
            except UnauthorizedError as e:
                response = http.HttpUnauthorized(e)
        else:
            # Stop here, unkown summary type
            raise Http404("Sorry, not implemented yet!")
        raise ImmediateHttpResponse(response=response)

    def get_topic_or_404(self, request=None):
        try:
            if request is not None:
                return Topic.objects.get(module=resolve(request.path).namespace)
            else:
                return Topic.objects.get(module=self._meta.urlconf_namespace)
        except Topic.DoesNotExist:
            raise Http404()

    def summary_countries(self, bundle, request):
        app_label = self.topic.app_label()
        # Query to aggreagte relationships count by country
        query = """
            START n=node(*)
            MATCH (m)-[:`<<INSTANCE>>`]->(i)<-[*0..1]->(country)<-[r:`<<INSTANCE>>`]-(n)
            WHERE HAS(country.isoa3)
            AND HAS(n.model_name)
            AND n.model_name = 'Country'
            AND n.app_label = '%s'
            AND HAS(country.isoa3)
            RETURN country.isoa3 as isoa3, ID(country) as id, count(i)-1 as count
        """ % app_label
        # Get the data and convert it to dictionnary
        countries = connection.cypher(query).to_dicts()
        obj       = {}
        for country in countries:
            # Use isoa3 as identifier
            obj[ country["isoa3"] ] = country
            # ISOA3 is now useless
            del country["isoa3"]
        return obj

    def summary_types(self, bundle, request):
        app_label = self.topic.app_label()
        # Query to aggreagte relationships count by country
        query = """
            START n=node(*)
            MATCH (c)<-[r:`<<INSTANCE>>`]-(n)
            WHERE HAS(n.model_name)
            AND n.app_label = '%s'
            RETURN ID(n) as id, n.model_name as name, count(c) as count
        """ % app_label
        # Get the data and convert it to dictionnary
        types = connection.cypher(query).to_dicts()
        obj   = {}
        for t in types:
            # Use name as identifier
            obj[ t["name"].lower() ] = t
            # name is now useless
            del t["name"]
        return obj

    def summary_forms(self, bundle, request):
        available_resources = {}
        # Get the model's rules manager
        rulesManager = topics_rules()
        # Fetch every registered model
        # to print out its rules
        for model in self.topic.get_models():
            name                = model.__name__.lower()
            rules               = rulesManager.model(model).all()
            fields              = utils.get_model_fields(model)
            verbose_name        = getattr(model._meta, "verbose_name", name).title()
            verbose_name_plural = getattr(model._meta, "verbose_name_plural", verbose_name + "s").title()

            for key in rules:
                # Filter rules to keep only Neomatch
                if isinstance(rules[key], Neomatch):
                    fields.append({
                        "name"         : key,
                        "type"         : "ExtendedRelationship",
                        "verbose_name" : rules[key].title,
                        "rules"        : {},
                        "related_model": rules[key].target_model.__name__
                    })

            available_resources[name] = {
                'description'         : getattr(model, "_description", None),
                'topic'               : getattr(model, "_topic", self.topic.slug) or self.topic.slug,
                'model'               : getattr(model, "__name_", ""),
                'verbose_name'        : verbose_name,
                'verbose_name_plural' : verbose_name_plural,
                'name'                : name,
                'fields'              : fields,
                'rules'               : rules
            }

        return available_resources

    def summary_mine(self, bundle, request):
        app_label = self.topic.app_label()
        self.method_check(request, allowed=['get'])
        if not request.user.id:
            raise UnauthorizedError('This method require authentication')

        query = """
            START root=node(*)
            MATCH (type)-[`<<INSTANCE>>`]->(root)
            WHERE HAS(root.name)
            AND HAS(root._author)
            AND HAS(type.model_name)
            AND %s IN root._author
            AND type.app_label = '%s'
            RETURN DISTINCT ID(root) as id, root.name as name, type.model_name as model
        """ % ( int(request.user.id), app_label )

        matches      = connection.cypher(query).to_dicts()
        count        = len(matches)
        limit        = int(request.GET.get('limit', 20))
        paginator    = Paginator(matches, limit)

        try:
            p     = int(request.GET.get('page', 1))
            page  = paginator.page(p)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []
        for result in page.object_list:
            label = result.get("name", None)
            objects.append({
                'label': label,
                'subject': {
                    "name": result.get("id", None),
                    "label": label
                },
                'predicate': {
                    "label": "is instance of",
                    "name": "<<INSTANCE>>"
                },
                'object': result.get("model", None)
            })

        object_list = {
            'objects': objects,
            'meta': {
                'page': p,
                'limit': limit,
                'total_count': count
            }
        }

        return object_list


    def summary_search(self, bundle, request):
        self.method_check(request, allowed=['get'])

        if not "q" in request.GET: raise Exception("Missing 'q' parameter")

        limit     = int(request.GET.get('limit', 20))
        query     = bundle.request.GET["q"].lower()
        results   = self.search(query)
        count     = len(results)
        paginator = Paginator(results, limit)

        try:
            p     = int(request.GET.get('page', 1))
            page  = paginator.page(p)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []
        for result in page.object_list:
            objects.append(result)

        object_list = {
            'objects': objects,
            'meta': {
                'q': query,
                'page': p,
                'limit': limit,
                'total_count': count
            }
        }

        self.log_throttled_access(request)
        return object_list

    def summary_rdf_search(self, bundle, request):
        self.method_check(request, allowed=['get'])

        limit     = int(request.GET.get('limit', 20))
        query     = json.loads(request.GET.get('q', 'null'))
        subject   = query.get("subject", None)
        predicate = query.get("predicate", None)
        obj       = query.get("object", None)
        results   = self.rdf_search(subject, predicate, obj)
        # Stop now in case of error
        if "errors" in results: return results
        count     = len(results)
        paginator = Paginator(results, limit)
        try:
            p     = int(request.GET.get('page', 1))
            page  = paginator.page(p)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []
        for result in page.object_list:
            objects.append(result)

        object_list = {
            'objects': objects,
            'meta': {
                'q': query,
                'page': p,
                'limit': limit,
                'total_count': count
            }
        }

        self.log_throttled_access(request)
        return object_list

    def summary_human(self, bundle, request):
        self.method_check(request, allowed=['get'])

        if not "q" in request.GET:
            raise Exception("Missing 'q' parameter")

        query        = request.GET["q"]
        # Find the kown match for the given query
        matches      = self.find_matches(query)
        # Build and returns a list of proposal
        propositions = self.build_propositions(matches, query)
        # Build paginator
        count        = len(propositions)
        limit        = int(request.GET.get('limit', 20))
        paginator    = Paginator(propositions, limit)

        try:
            p     = int(request.GET.get('page', 1))
            page  = paginator.page(p)
        except InvalidPage:
            raise Http404("Sorry, no results on that page.")

        objects = []
        for result in page.object_list:
            objects.append(result)

        object_list = {
            'objects': objects,
            'meta': {
                'q': query,
                'page': p,
                'limit': limit,
                'total_count': count
            }
        }

        self.log_throttled_access(request)
        return object_list

    def summary_bulk_upload(self, request, **kwargs):

        # only allow POST requests
        self.method_check(request, allowed=['post'])

        # check session
        if not request.user.id:
            raise UnauthorizedError('This method require authentication')

        # flattern the list of files
        files = [file for sublist in request.FILES.lists() for file in sublist[1]]
        # reads the files
        files = [(f.name, f.readlines()) for f in files]
        # enqueue the parsing job
        queue = django_rq.get_queue('default', default_timeout=7200)
        job   = queue.enqueue(process_parsing, self.topic, files)
        # return a quick response
        self.log_throttled_access(request)
        return {
            "status" : "enqueued",
            "token"  : job.get_id()
        }

    def summary_syntax(self, bundle, request): return self.get_syntax(bundle, request)

    def search(self, query):
        match = str(query).lower()
        match = re.sub("\"|'|`|;|:|{|}|\|(|\|)|\|", '', match).strip()
        # Query to get every result
        query = """
            START root=node(*)
            MATCH (root)<-[r:`<<INSTANCE>>`]-(type)
            WHERE HAS(root.name)
            AND LOWER(root.name) =~ '.*(%s).*'
            AND type.app_label = '%s'
            RETURN ID(root) as id, root.name as name, type.model_name as model
        """ % (match, self.topic.app_label() )
        return connection.cypher(query).to_dicts()

    def rdf_search(self, subject, predicate, obj):
        obj = obj["name"] if "name" in obj else obj
        # retrieve all models in current topic
        all_models = dict((model.__name__, model) for model in self.topic.get_models())
        # If the received obj describe a literal value
        if self.is_registered_literal(predicate["name"]):
            # Get the field name into the database
            field_name = predicate["name"]
            # Build the request
            query = """
                START root=node(*)
                MATCH (root)<-[:`<<INSTANCE>>`]-(type)
                WHERE HAS(root.name)
                AND HAS(root.{field})
                AND root.{field} = {value}
                AND type.model_name = {model}
                AND type.app_label = {app}
                RETURN DISTINCT ID(root) as id, root.name as name, type.model_name as model
            """.format(
                field=field_name,
                value=adapt(obj),
                model=adapt(subject["name"]),
                app=adapt(self.topic.app_label())
            )
        # If the received obj describe a literal value
        elif self.is_registered_relationship(predicate["name"]):
            fields        = utils.get_model_fields( all_models[predicate["subject"]] )
            # Get the field name into the database
            relationships = [ field for field in fields if field["name"] == predicate["name"] ]
            # We didn't find the predicate
            if not len(relationships): return {'errors': 'Unkown predicate type'}
            relationship  = relationships[0]["rel_type"]
            # Query to get every result
            query = """
                START st=node(*)
                MATCH (st)<-[:`{relationship}`]-(root)<-[:`<<INSTANCE>>`]-(type)
                WHERE HAS(root.name)
                AND HAS(st.name)
                AND st.name = {name}
                AND type.app_label = {app}
                RETURN DISTINCT ID(root) as id, root.name as name, type.model_name as model
            """.format(
                relationship=relationship,
                name=adapt(obj),
                app=adapt(self.topic.app_label())
            )
        else:
            return {'errors': 'Unkown predicate type'}

        return connection.cypher(query).to_dicts()


    def get_models_output(self):
        # Select only some atribute
        output = lambda m: {'name': m.__name__, 'label': m._meta.verbose_name.title()}
        return [ output(m) for m in self.topic.get_models() ]

    def get_relationship_search(self):
        return  SearchTerm.objects.filter(topic=self.topic, is_literal=False)

    def get_relationship_search_output(self):
        output = lambda m: {'name': m.name, 'label': m.label, 'subject': m.subject}
        terms  = self.get_relationship_search()
        return [ output(rs) for rs in terms ]

    def get_literal_search(self):
        return SearchTerm.objects.filter(topic=self.topic, is_literal=True)

    def get_literal_search_output(self):
        output = lambda m: {'name': m.name, 'label': m.label, 'subject': m.subject}
        terms  = self.get_literal_search()
        return [ output(rs) for rs in terms ]

    def ngrams(self, input):
        input = input.split(' ')
        output = []
        end = len(input)
        for n in range(1, end+1):
            for i in range(len(input)-n+1):
                output.append(input[i:i+n])
        return output

    def get_close_labels(self, token, lst, ratio=0.6):
        """
            Look for the given token into the list using labels
        """
        matches = []
        for item in lst:
            cpr = item["label"]
            if SequenceMatcher(None, token, cpr).ratio() >= ratio:
                matches.append(item)
        return matches

    def find_matches(self, query):
        # Group ngram by following string
        ngrams  = [' '.join(x) for x in self.ngrams(query) ]
        matches = []
        models  = self.get_syntax().get("subject").get("model")
        rels    = self.get_syntax().get("predicate").get("relationship")
        lits    = self.get_syntax().get("predicate").get("literal")
        # Known models lookup for each ngram
        for token in ngrams:
            obj = {
                'models'       : self.get_close_labels(token, models),
                'relationships': self.get_close_labels(token, rels),
                'literals'     : self.get_close_labels(token, lits),
                'token'        : token
            }
            matches.append(obj)
        return matches

    def build_propositions(self, matches, query):
        """
            For now, a proposition follow the form
            <subject> <predicat> <object>
            Where a <subject>, is an "Named entity" or a Model
            a <predicat> is a relationship type
            and an <object> is a "Named entity" or a Model.
            Later, as follow RDF standard, an <object> could be any data.
        """
        def remove_duplicates(lst):
            seen = set()
            new_list = []
            for item in lst:
                if type(item) is dict:
                    # Create a hash of the dictionary
                    obj = hash(frozenset(item.items()))
                else:
                    obj = hash(item)
                if obj not in seen:
                    seen.add(obj)
                    new_list.append(item)
            return new_list

        def is_preposition(token=""):
            return str(token).lower() in ["aboard", "about", "above", "across", "after", "against",
            "along", "amid", "among", "anti", "around", "as", "at", "before", "behind", "below",
            "beneath", "beside", "besides", "between", "beyond", "but", "by", "concerning",
            "considering",  "despite", "down", "during", "except", "excepting", "excluding",
            "following", "for", "from", "in", "inside", "into", "like", "minus", "near", "of",
            "off", "on", "onto", "opposite", "outside", "over", "past", "per", "plus", "regarding",
            "round", "save", "since", "than", "through", "to", "toward", "towards", "under",
            "underneath", "unlike", "until", "up", "upon", "versus", "via", "with", "within", "without"]

        def previous_word(sentence="", base=""):
            if base == "" or sentence == "": return ""
            parts = sentence.split(base)
            return parts[0].strip().split(" ")[-1] if len(parts) else None

        def is_object(query, token):
            previous = previous_word(query, token)
            return is_preposition(previous) or previous.isdigit() or token.isnumeric()

        predicates      = []
        subjects        = []
        objects         = []
        propositions    = []
        ending_tokens   = ""
        searched_tokens = set()
        # Picks candidates for subjects and predicates
        for idx, match in enumerate(matches):
            subjects     += match["models"]
            predicates   += match["relationships"] + match["literals"]
            token         = match["token"]
            # True when the current token is the last of the series
            is_last_token = query.endswith(token)
            # Objects are detected when they start and end by double quotes
            if  token.startswith('"') and token.endswith('"'):
                # Remove the quote from the token
                token = token.replace('"', '')
                # Store the token as an object
                objects += self.search(token)[:5]
            # Or if the previous word is a preposition
            elif is_object(query, token) or is_last_token:
                if token not in searched_tokens and len(token) > 1:
                    # Looks for entities into the database
                    entities = self.search(token)[:5]
                    # Do not search this token again
                    searched_tokens.add(token)
                    # We found some result
                    if len(entities): objects += entities
                # Save every tokens until the last one
                if not is_last_token: ending_tokens = token
                # We reach the end
                else: objects.append( ending_tokens )

        # We find some subjects
        if len(subjects) and not len(predicates):
            terms  = self.get_syntax().get("predicate").get("relationship")
            terms += self.get_syntax().get("predicate").get("literal")
            for subject in subjects:
                # Gets all available terms for these subjects
                predicates += [ term for term in terms if term["subject"] == subject["name"] ]

        # Add a default and irrelevant object
        if not len(objects): objects = [""]

        # Generate proposition using RDF's parts
        for subject in remove_duplicates(subjects):
            for predicate in remove_duplicates(predicates):
                for obj in remove_duplicates(objects):
                    pred_sub = predicate.get("subject", None)
                    # If the predicate has a subject
                    # and it matches to the current one
                    if pred_sub != None:
                        if type(obj) is dict:
                            obj_disp = obj["name"] or obj["label"]
                        else:
                            obj_disp = obj
                        # Value to inset into the proposition's label
                        values = (subject["label"], predicate["label"], obj_disp,)
                        # Build the label
                        label = '%s that %s %s' % values
                        propositions.append({
                            'label'    : label,
                            'subject'  : subject,
                            'predicate': predicate,
                            'object'   : obj
                        })

        # It might be a classic search
        for obj in [ obj for obj in objects if 'id' in obj ]:
            # Build the label
            label = obj.get("name", None)
            propositions.append({
                'label': label,
                'subject': {
                    "name": obj.get("id", None),
                    "label": label
                },
                'predicate': {
                    "label": "is instance of",
                    "name": "<<INSTANCE>>"
                },
                'object': obj.get("model", None)
            })
        # Remove duplicates proposition dicts
        return propositions

    def is_registered_literal(self, name):
        literals = self.get_syntax().get("predicate").get("literal")
        matches  = [ literal for literal in literals if name == literal["name"] ]
        return len(matches)

    def is_registered_relationship(self, name):
        literals = self.get_syntax().get("predicate").get("relationship")
        matches  = [ literal for literal in literals if name == literal["name"] ]
        return len(matches)

    def get_syntax(self, bundle=None, request=None):
        if not hasattr(self, "syntax"):
            syntax = {
                'subject': {
                    'model':  self.get_models_output()
                },
                'predicate': {
                    'relationship': self.get_relationship_search_output(),
                    'literal':      self.get_literal_search_output()
                }
            }
            self.syntax = syntax
        return self.syntax

def process_parsing(topic, files):
    """
    Job which reads the uploaded files, validate and saves them as model
    """

    entities   = {}
    relations  = []
    errors     = []
    id_mapping = {}

    assert type(files) in (tuple, list)
    assert len(files) > 0
    assert type(files[0]) in (tuple, list)
    assert len(files[0]) == 2

    # Define Exceptions
    class Error (Exception):
        """
        Generic Custom Exception for this endpoint.
        Include the topic.
        """
        def __init__(self, **kwargs):
            """ set the topic and add all the parameters as attributes """
            self.topic = topic.title
            for key, value in kwargs.items():
                setattr(self, key, value)
        def __str__(self):
            return self.__dict__

    class WarningCastingValueFail     (Error): pass
    class WarningValidationError      (Error): pass
    class WarningKeyUnknown           (Error): pass
    class WarningInformationIsMissing (Error): pass
    class AttributeDoesntExist        (Error): pass
    class WrongCSVSyntax              (Error): pass
    class ColumnUnknow                (Error): pass
    class ModelDoesntExist            (Error): pass
    class RelationDoesntExist         (Error): pass

    try:
        # retrieve all models in current topic
        all_models = dict((model.__name__, model) for model in topic.get_models())
        # iterate over all files and dissociate entities .csv from relations .csv
        for file in files:
            if type(file) is tuple:
                file_name = file[0]
                file      = file[1]
            elif hasattr(file, "read"):
                file_name = file.name
            else:
                raise Exception("ERROR")
            csv_reader = utils.open_csv(file)
            header = csv_reader.next()
            assert len(header) > 1, "header should have at least 2 columns"
            assert header[0].endswith("_id"), "First column should begin with a header like <model_name>_id"
            if len(header) >=3 and header[0].endswith("_id") and header[2].endswith("_id"):
                # this is a relationship file
                relations.append((file_name, file))
            else:
                # this is an entities file
                model_name = utils.to_class_name(header[0].replace("_id", ""))
                if model_name in all_models.keys():
                    entities[model_name] = (file_name, file)
                else:
                    raise ModelDoesntExist(model=model_name, file=file_name, models_availables=all_models.keys())

        # first iterate over entities
        logger.debug("BulkUpload: creating entities")
        for entity, (file_name, file) in entities.items():
            csv_reader = utils.open_csv(file)
            header     = csv_reader.next()
            # must check that all columns map to an existing model field
            fields      = utils.get_model_fields(all_models[entity])
            fields_types = {}
            for field in fields:
                fields_types[field['name']] = field['type']
            field_names = [field['name'] for field in fields]
            columns = []
            for column in header[1:]:
                column = utils.to_underscores(column)
                if column is not '':
                    if not column in field_names:
                        raise ColumnUnknow(file=file_name, column=column, model=entity, attributes_available=field_names)
                        break
                    column_type = fields_types[column]
                    columns.append((column, column_type))
            else:
                # here, we know that all columns are valid
                for row in csv_reader:
                    data = {}
                    id   = row[0]
                    for i, (column, column_type) in enumerate(columns):
                        value = str(row[i+1]).decode('utf-8')
                        # cast value if needed
                        if value:
                            try:
                                if "Integer" in column_type:
                                    value = int(value)
                                # TODO: cast float
                                if "Date" in column_type:
                                    value = datetime.datetime(*map(int, re.split('[^\d]', value)[:-1])).replace(tzinfo=utc)
                            except Exception as e:
                                e = WarningCastingValueFail(
                                    column_name = column,
                                    value       = value,
                                    type        = column_type,
                                    data        = data, model=entity,
                                    file        = file_name,
                                    line        = csv_reader.line_num,
                                    error       = str(e)
                                )
                                errors.append(e)
                                break
                            data[column] = value
                    else:
                        # instanciate a model
                        try:
                            item = all_models[entity].objects.create(**data)
                            # map the object with the ID defined in the .csv
                            id_mapping[(entity, id)] = item
                        except Exception as e:
                            errors.append(
                                WarningValidationError(
                                    data  = data,
                                    model = entity,
                                    file  = file_name,
                                    line  = csv_reader.line_num,
                                    error = str(e)
                                )
                            )

        inserted_relations = 0
        # then iterate over relations
        logger.debug("BulkUpload: creating relations")
        for file_name, file in relations:
            # create a csv reader
            csv_reader    = utils.open_csv(file)
            csv_header    = csv_reader.next()
            relation_name = utils.to_underscores(csv_header[1])
            model_from    = utils.to_class_name(csv_header[0].replace("_id", ""))
            model_to      = utils.to_class_name(csv_header[2].replace("_id", ""))
            # check that the relation actually exists between the two objects
            try:
                getattr(all_models[model_from], relation_name)
            except Exception as e:
                raise RelationDoesntExist(
                    file             = file_name,
                    model_from       = model_from,
                    model_to         = model_to,
                    relation_name    = relation_name,
                    fields_available = [field['name'] for field in utils.get_model_fields(all_models[model_from])],
                    error            = str(e))
            for row in csv_reader:
                id_from = row[0]
                id_to   = row[2]
                if id_to and id_from:
                    try:
                        getattr(id_mapping[(model_from, id_from)], relation_name).add(id_mapping[(model_to, id_to)])
                        inserted_relations += 1
                    except KeyError as e:
                        errors.append(
                            WarningKeyUnknown(
                                file             = file_name,
                                line             = csv_reader.line_num,
                                model_from       = model_from,
                                id_from          = id_from,
                                model_to         = model_to,
                                id_to            = id_to,
                                relation_name    = relation_name,
                                error            = str(e)
                            )
                        )
                    except Exception as e:
                        # Error unknown, we break the process to alert the user
                        raise Error(
                            file             = file_name,
                            line             = csv_reader.line_num,
                            model_from       = model_from,
                            id_from          = id_from,
                            model_to         = model_to,
                            id_to            = id_to,
                            relation_name    = relation_name,
                            error            = str(e))
                else:
                    # A key is missing (id_from or id_to) but we don't want to stop the parsing.
                    # Then we store the wrong line to return it to the user.
                    errors.append(
                        WarningInformationIsMissing(
                            file=file_name, row=row, line=csv_reader.line_num, id_to=id_to, id_from=id_from
                        )
                    )

        # Save everything
        saved = 0
        logger.debug("BulkUpload: saving %d objects" % (len(id_mapping)))
        for item in id_mapping.values():
            item.save()
            saved += 1

        return {
            'inserted' : {
                'objects' : saved,
                'links'   : inserted_relations
            },
            "errors" : sorted([dict([(e.__class__.__name__, str(e.__dict__))]) for e in errors])
        }
    except Exception as e:
        import traceback
        logger.error(traceback.format_exc())
        return {
            "errors" : [{e.__class__.__name__ : str(e.__dict__)}]
        }

########NEW FILE########
__FILENAME__ = urls
from .resources       import QuoteRequestResource, TopicResource, ArticleResource
from .summary         import SummaryResource
from .user            import UserResource
from .cypher          import CypherResource
from django.conf.urls import patterns, include, url
from tastypie.api     import NamespacedApi
from .job             import JobResource

api = NamespacedApi(api_name='v1', urlconf_namespace='common')
api.register(QuoteRequestResource())
api.register(TopicResource())
api.register(SummaryResource())
api.register(CypherResource())
api.register(UserResource())
api.register(ArticleResource())
api.register(JobResource())

urlpatterns = patterns('common',
    url(r'', include(api.urls)),
)


########NEW FILE########
__FILENAME__ = user
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .errors                      import *
from .message                     import Recover
from django.conf.urls             import url
from django.contrib.auth          import authenticate, login, logout
from django.contrib.auth.models   import User
from django.contrib.sites.models  import RequestSite
from django.core                  import signing
from django.db                    import IntegrityError
from django.middleware.csrf       import _get_new_csrf_key as get_new_csrf_key
from password_reset.views         import Reset
from registration.models          import RegistrationProfile, SHA1_RE
from tastypie                     import http
from tastypie.authentication      import Authentication, SessionAuthentication, BasicAuthentication, MultiAuthentication
from tastypie.authorization       import ReadOnlyAuthorization
from tastypie.constants           import ALL
from tastypie.resources           import ModelResource
from tastypie.utils               import trailing_slash
import hashlib
import random


class UserAuthorization(ReadOnlyAuthorization):
    def update_detail(self, object_list, bundle):
        authorized = False
        if bundle.request:
            authorized = ((bundle.obj.user == bundle.request.user) or bundle.request.user.is_staff)
        return authorized

    def delete_detail(self, object_list, bundle):
        authorized = False
        if bundle.request:
            authorized = ((bundle.obj.user == bundle.request.user) or bundle.request.user.is_staff)
        return authorized


class UserResource(ModelResource):
    class Meta:
        authentication     = MultiAuthentication(Authentication(), SessionAuthentication(), BasicAuthentication())
        authorization      = UserAuthorization()
        allowed_methods    = ['get', 'post']
        always_return_data = True
        fields             = ['first_name', 'last_name', 'username', 'email', 'is_staff', 'password']
        filtering          = {'username': ALL, 'email': ALL}
        queryset           = User.objects.all()
        resource_name      = 'user'

    def prepend_urls(self):
        params = (self._meta.resource_name, trailing_slash())
        return [
            url(r"^(?P<resource_name>%s)/login%s$"                  % params, self.wrap_view('login'),                  name="api_login"),
            url(r'^(?P<resource_name>%s)/logout%s$'                 % params, self.wrap_view('logout'),                 name='api_logout'),
            url(r'^(?P<resource_name>%s)/status%s$'                 % params, self.wrap_view('status'),                 name='api_status'),
            url(r'^(?P<resource_name>%s)/permissions%s$'            % params, self.wrap_view('permissions'),            name='api_user_permissions'),
            url(r'^(?P<resource_name>%s)/signup%s$'                 % params, self.wrap_view('signup'),                 name='api_signup'),
            url(r'^(?P<resource_name>%s)/activate%s$'               % params, self.wrap_view('activate'),               name='api_activate'),
            url(r'^(?P<resource_name>%s)/reset_password%s$'         % params, self.wrap_view('reset_password'),         name='api_reset_password'),
            url(r'^(?P<resource_name>%s)/reset_password_confirm%s$' % params, self.wrap_view('reset_password_confirm'), name='api_reset_password_confirm'),
        ]

    def login(self, request, **kwargs):
        self.method_check(request, allowed=['post'])

        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        username    = data.get('username', '')
        password    = data.get('password', '')
        remember_me = data.get('remember_me', False)

        if username == '' or password == '':
            return self.create_response(request, {
                'success': False,
                'error_message': 'Missing username or password',
            })

        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)

                # Remember me opt-in
                if not remember_me: request.session.set_expiry(0)
                response = self.create_response(request, {
                    'success' : True,
                    'is_staff': user.is_staff,
                    'permissions': list(user.get_all_permissions()),
                    'username': user.username
                })
                # Create CSRF token
                response.set_cookie("csrftoken", get_new_csrf_key())

                return response
            elif not user.is_active:
                return self.create_response(request, {
                    'success': False,
                    'error_message': 'Account not activated yet.',
                })
            else:
                return self.create_response(request, {
                    'success': False,
                    'error_message': 'Account activated but not authorized yet.',
                })
        else:
            return self.create_response(request, {
                'success': False,
                'error_message': 'Incorrect password or username.',
            })

    def dehydrate(self, bundle):
        bundle.data["email"]    = u"☘"
        bundle.data["password"] = u"☘"
        return bundle

    def get_activation_key(self, username=""):
        salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
        if isinstance(username, unicode):
            username = username.encode('utf-8')
        return hashlib.sha1(salt+username).hexdigest()

    def signup(self, request, **kwargs):
        self.method_check(request, allowed=['post'])
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))

        try:
            self.validate_request(data, ['username', 'email', 'password'])
            user = User.objects.create_user(
                data.get("username"),
                data.get("email"),
                data.get("password")
            )
            # Create an inactive user
            setattr(user, "is_active", False)
            user.save()
            # Send activation key by email
            activation_key = self.get_activation_key(user.username)
            rp = RegistrationProfile.objects.create(user=user, activation_key=activation_key)
            rp.send_activation_email( RequestSite(request) )
            # Output the answer
            return http.HttpCreated()
        except MalformedRequestError as e:
            return http.HttpBadRequest(e)
        except IntegrityError as e:
            return http.HttpForbidden("%s in request payload (JSON)" % e)

    def activate(self, request, **kwargs):
        try:
            self.validate_request(request.GET, ['token'])
            token = request.GET.get("token", None)
            # Make sure the key we're trying conforms to the pattern of a
            # SHA1 hash; if it doesn't, no point trying to look it up in
            # the database.
            if SHA1_RE.search(token):
                profile = RegistrationProfile.objects.get(activation_key=token)
                if not profile.activation_key_expired():
                    user = profile.user
                    user.is_active = True
                    user.save()
                    profile.activation_key = RegistrationProfile.ACTIVATED
                    profile.save()
                    return self.create_response(request, {
                            "success": True
                        })
                else:
                    return http.HttpForbidden('Your activation token is no longer active or valid')
            else:
                return http.HttpForbidden('Your activation token  is no longer active or valid')

        except RegistrationProfile.DoesNotExist:
            return http.HttpNotFound('Your activation token is no longer active or valid')

        except MalformedRequestError as e:
            return http.HttpBadRequest("%s as request GET parameters" % e)

    def logout(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        if request.user and request.user.is_authenticated():
            logout(request)
            return self.create_response(request, { 'success': True })
        else:
            return self.create_response(request, { 'success': False })

    def status(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        if request.user and request.user.is_authenticated():
            return self.create_response(request, { 'is_logged': True,  'username': request.user.username })
        else:
            return self.create_response(request, { 'is_logged': False, 'username': '' })


    def permissions(self, request, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        if request.user.is_authenticated():
            # Get the list of permission and sorts it alphabeticly
            permissions = list(request.user.get_all_permissions())
            permissions.sort()
            return self.create_response(request, {
                'permissions': permissions
            })
        else:
            return http.HttpUnauthorized('You need to be logged to list your permissions')

    def reset_password(self, request, **kwargs):
        """
        Send the reset password email to user with the proper URL.
        """
        self.method_check(request, allowed=['post'])
        data = self.deserialize(request, request.body, format=request.META.get('CONTENT_TYPE', 'application/json'))
        try:
            self.validate_request(data, ['email'])
            email   = data['email']
            user    = User.objects.get(email=email)
            recover = Recover()
            recover.user = user
            recover.request = request
            recover.email_template_name = 'reset_password_email.txt'
            recover.email_subject_template_name = 'reset_password_email_subject.txt'
            recover.send_notification()
            return self.create_response(request, { 'success': True })
        except User.DoesNotExist:
            message = 'The specified email (%s) doesn\'t match with any user' % email
            return http.HttpNotFound(message)
        except MalformedRequestError as error:
            return http.HttpBadRequest("%s in request payload (JSON)" % error)

    def reset_password_confirm(self, request, **kwargs):
        """
        Reset the password if the POST's token parameter is a valid token
        """
        self.method_check(request, allowed=['post'])
        reset = Reset()
        data  = self.deserialize(
                    request,
                    request.body,
                    format=request.META.get('CONTENT_TYPE', 'application/json')
                )
        try:
            self.validate_request(data, ['token', 'password'])
            tok          = data['token']
            raw_password = data['password']
            pk = signing.loads(tok, max_age=reset.token_expires,salt=reset.salt)
            user = User.objects.get(pk=pk)
            user.set_password(raw_password)
            user.save()
            return self.create_response(request, { 'success': True })
        except signing.BadSignature:
            return http.HttpForbidden('Wrong signature, your token may had expired (valid for 48 hours).')
        except MalformedRequestError as e:
            return http.HttpBadRequest(e)


    def validate_request(self, data, fields):
        """
        Validate passed `data` based on the required `fields`.
        """
        missing_fields = []
        for field in fields:
            if field not in data.keys() or data[field] is None or data[field] == "":
                missing_fields.append(field)

        if len(missing_fields) > 0:
            message = "Malformed request. The following fields are required: %s" % ', '.join(missing_fields)
            raise MalformedRequestError(message)
########NEW FILE########
__FILENAME__ = forms
from app.detective.topics.energy.models import *
from app.detective.modelrules           import ModelRules
from app.detective.neomatch             import Neomatch
from app.detective.models               import *

def topics_rules():
    # ModelRules is a singleton that record every model rules
    rules = ModelRules()
    # Disable editing on some model
    rules.model(Country).add(is_editable=False)
    # Records "invisible" fields
    rules.model(FundraisingRound).field("personal_payer").add(is_visible=False)
    rules.model(Organization).field("adviser").add(is_visible=False)
    rules.model(Organization).field("board_member").add(is_visible=False)
    rules.model(Organization).field("company_register_link").add(is_visible=False)
    rules.model(Organization).field("litigation_against").add(is_visible=False)
    rules.model(Organization).field("monitoring_body").add(is_visible=False)
    rules.model(Organization).field("partner").add(is_visible=False)
    rules.model(Organization).field("website_url").add(is_visible=False)
    rules.model(Person).field("previous_activity_in_organization").add(is_visible=False)
    rules.model(Person).field("website_url").add(is_visible=False)
    rules.model(EnergyProduct).field("operator").add(is_visible=False)
    rules.model(EnergyProject).field("ended").add(is_visible=False)
    rules.model(EnergyProject).field("partner").add(is_visible=False)

    rules.model(Country).add(person_set=Neomatch(
        title="Persons educated or based in this country",
        target_model=Person,
        match="""
            (root)<-[r:`person_has_based_in+`|`person_has_educated_in+`]-({select})
        """
    ))

    rules.model(Person).add(organizationkey_set=Neomatch(
        title="Organizations this person has a key position in",
        target_model=Organization,
        match="""
            (root)-[:`organization_has_key_person+`]-({select})
        """
    ))

    rules.model(Person).add(organizationadviser_set=Neomatch(
        title="Organizations this person is an adviser to",
        target_model=Organization,
        match="""
            (root)-[:`organization_has_adviser+`]-({select})
        """
    ))

    rules.model(Person).add(organizationboard_set=Neomatch(
        title="Organizations this person is a board member of",
        target_model=Organization,
        match="""
            (root)-[:`organization_has_board_member+`]-({select})
        """
    ))


    rules.model(Country).add(product_set= Neomatch(
        title="Energy products distributed in this country",
        target_model=EnergyProduct,
        match="""
            (root)<--()<-[:`energy_product_has_distribution+`]-({select})
        """
    ))

    rules.model(Country).add(project_set=Neomatch(
        title="Energy projects active in this country",
        target_model=EnergyProject,
        match="""
            (root)-[:`energy_project_has_activity_in_country+`]-({select})
        """
    ))

    rules.model(EnergyProduct).add(country_set= Neomatch(
        title="Countries where this product is distributed",
        target_model=Country,
        match="""
            (root)-[:`energy_product_has_distribution+`]-()-[:`distribution_has_activity_in_country+`]-({select})
        """
    ))

    rules.model(Organization).add(energyproject_set=Neomatch(
        title="Energy projects this organization owns",
        target_model=EnergyProject,
        match="""
            (root)-[:`energy_project_has_owner+`]-({select})
        """
    ))

    rules.model(EnergyProduct).add(energyproduct_set=Neomatch(
        title="Energy project this product belongs to",
        target_model=EnergyProject,
        match="""
            (root)-[:`energy_project_has_product+`]-({select})
        """
    ))

    rules.model(Price).add(transform='{currency} {units}')
    rules.model(FundraisingRound).add(transform='{currency} {units}')

    def to_twitter_profile_url(data, field=None):
        th = data["twitter_handle"]
        if not th:
            return th
        elif th.startswith("http://") or th.startswith("https://"):
            return th
        elif th.startswith("@"):
            return "http://twitter.com/%s" % th[1:]
        else:
            return "http://twitter.com/%s" % th

    rules.model(Organization).field("twitter_handle").add(transform=to_twitter_profile_url)
    rules.model(Person).field("twitter_handle").add(transform=to_twitter_profile_url)
    rules.model(EnergyProject).field("twitter_handle").add(transform=to_twitter_profile_url)

    return rules
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
# The ontology can be found in its entirety at http://www.semanticweb.org/nkb/ontologies/2013/6/impact-investment#
from neo4django.db import models

class Country(models.NodeModel):
	_description = u''
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	name = models.StringProperty(null=True,help_text=u'')
	isoa3 = models.StringProperty(null=True,help_text=u'The 3-letter ISO code for the country or territory (e.g. FRA for France, DEU for Germany etc.)',verbose_name=u'ISO alpha-3 code')

	class Meta:
		verbose_name = u'Country'
		verbose_name_plural = u'Countries'

	def __unicode__(self):
		return self.name or u"Unkown"

class Amount(models.NodeModel):
	_topic = u'energy'
	_description = u''
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	year = models.DateTimeProperty(null=True,help_text=u'',verbose_name=u'Year')
	source = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to your source. If the source is a book, enter the URL to the book at Google Books or Amazon.',verbose_name=u'Source')
	units = models.IntegerProperty(null=True,help_text=u'The value of the amount.',verbose_name=u'Value')

	class Meta:
		pass

class FundraisingRound(models.NodeModel):
	_topic = u'energy'
	_parent = u'Amount'
	_description = u''
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	currency = models.StringProperty(null=True,help_text=u'The currency of the amount, using its 3-letter ISO-4217 code, e.g. USD, EUR, GBP etc.',verbose_name=u'Currency')
	raise_type = models.StringProperty(null=True,help_text=u'Type of the transaction, e.g. equity contribution (cash), preproject expenses, loan.',verbose_name=u'Type of transaction')
	year = models.DateTimeProperty(null=True,help_text=u'',verbose_name=u'Year')
	source = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to your source. If the source is a book, enter the URL to the book at Google Books or Amazon.',verbose_name=u'Source')
	units = models.IntegerProperty(null=True,help_text=u'The value of the amount.',verbose_name=u'Value')
	payer = models.Relationship("Organization",null=True,rel_type='fundraising_round_has_payer+',help_text=u'The Organization that actually pays the amount or contributes the asset considered.',verbose_name=u'Payer')
	personal_payer = models.Relationship("Person",null=True,rel_type='fundraising_round_has_personal_payer+',help_text=u'The Person that contributes the amount or the asset considered.',verbose_name=u'Physical payer')

	class Meta:
		pass

class Person(models.NodeModel):
	_topic = u'energy'
	_description = u'A Person represents a physical man or woman that is involved in an Organization, a Project or a Commentary.'
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	position = models.StringProperty(null=True,help_text=u'Current position within the Organization (e.g. CEO, CFO, spokesperson etc.)',verbose_name=u'Position')
	twitter_handle = models.StringProperty(null=True,help_text=u'The Twitter name of the entity (without the @)',verbose_name=u'Twitter handle')
	name = models.StringProperty(null=True,help_text=u'')
	source = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to your source. If the source is a book, enter the URL to the book at Google Books or Amazon.',verbose_name=u'Source')
	website_url = models.StringProperty(null=True,help_text=u'',verbose_name=u'Website URL')
	image = models.URLProperty(null=True,help_text=u'The URL (starting with http://) where the image is hosted.',verbose_name=u'Image URL')
	previous_activity_in_organization = models.Relationship("Organization",null=True,rel_type='person_has_previous_activity_in_organization+',help_text=u'Has the entity been active in a specific Organization previsously?',verbose_name=u'Previous activity in')
	educated_in  = models.Relationship(Country,null=True,rel_type='person_has_educated_in+',help_text=u'',verbose_name=u'Educated in')
	based_in  = models.Relationship(Country,null=True,rel_type='person_has_based_in+',help_text=u'',verbose_name=u'Based in')
	activity_in_organization = models.Relationship("Organization",null=True,rel_type='person_has_activity_in_organization+',help_text=u'The Organization(s) this Person is active in.',verbose_name=u'Activity in Organizations')

	class Meta:
		verbose_name = u'Person'
		verbose_name_plural = u'Persons'

	def __unicode__(self):
		return self.name or u"Unkown"

class Revenue(models.NodeModel):
	_topic = u'energy'
	_parent = u'Amount'
	_description = u''
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	currency = models.StringProperty(null=True,help_text=u'The currency of the amount, using its 3-letter ISO-4217 code, e.g. USD, EUR, GBP etc.',verbose_name=u'Currency')
	year = models.DateTimeProperty(null=True,help_text=u'',verbose_name=u'Year')
	source = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to your source. If the source is a book, enter the URL to the book at Google Books or Amazon.',verbose_name=u'Source')
	units = models.IntegerProperty(null=True,help_text=u'The value of the amount.',verbose_name=u'Value')

	class Meta:
		pass

class Commentary(models.NodeModel):
	_topic = u'energy'
	_description = u''
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	year = models.DateTimeProperty(null=True,help_text=u'',verbose_name=u'Year')
	article_url = models.URLProperty(null=True,help_text=u'The URL (starting with http://) of the link.')
	title = models.StringProperty(null=True,help_text=u'Title of the article or report of this commentary.',verbose_name=u'Title')
	author = models.Relationship("Person",null=True,rel_type='commentary_has_author+',help_text=u'The author or authors of the document.',verbose_name=u'Author')

	class Meta:
		pass

class Organization(models.NodeModel):
	_topic = u'energy'
	_description = u'An Organization represents a social entity that implements, funds, takes part in or helps a Project. It can be an NGO, a university, a governement organization, a for-profit company or an international organization.'
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	founded = models.DateTimeProperty(null=True,help_text=u'The date when the organization was created.',verbose_name=u'Date founded')
	company_type = models.StringProperty(null=True,help_text=u'If the organization is a company, type of company (e.g. limited liability company, public corporation, unlimited company etc.)',verbose_name=u'Company type')
	company_register_link = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to the official company register where the organization is registered.',verbose_name=u'Company register link')
	twitter_handle = models.StringProperty(null=True,help_text=u'The Twitter name of the entity (without the @)',verbose_name=u'Twitter handle')
	website_url = models.URLProperty(null=True,help_text=u'',verbose_name=u'Website URL')
	name = models.StringProperty(null=True,help_text=u'')
	source = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to your source. If the source is a book, enter the URL to the book at Google Books or Amazon.',verbose_name=u'Source')
	address = models.StringProperty(null=True,help_text=u'The official address of the organization.',verbose_name=u'Address')
	organization_type = models.StringProperty(null=True,help_text=u'Type of organization. Can be Company, Government Organization, International Organization, University or NGO',verbose_name=u'Organization type')
	image = models.URLProperty(null=True,help_text=u'The URL (starting with http://) where the image is hosted.',verbose_name=u'Image URL')
	office_address = models.StringProperty(null=True,help_text=u'The address or addresses where this organization does business. Do add the country at the end of the address, e.g. Grimmstraße 10A, 10967 Berlin, Germany.',verbose_name=u'Office address')
	adviser = models.Relationship("Person",null=True,rel_type='organization_has_adviser+',help_text=u'The list of persons that help the entity.',verbose_name=u'Adviser')
	revenue = models.Relationship("Revenue",null=True,rel_type='organization_has_revenue+',help_text=u'A Revenue represents the quantity of cash that the Organization was able to gather in any given year. It doesn\'t have to be equal to the net sales but can take into account subsidies as well.',verbose_name=u'Revenue')
	board_member = models.Relationship("Person",null=True,rel_type='organization_has_board_member+',help_text=u'The list of board members of the Organization, if any.',verbose_name=u'Board member')
	partner = models.Relationship("self",null=True,rel_type='organization_has_partner+',help_text=u'An entity can have Partners, i.e. Organizations that help without making a financial contribution (if financial or substancial help is involved, use Fundraising Round instead).',verbose_name=u'Partner')
	key_person = models.Relationship("Person",null=True,rel_type='organization_has_key_person+',help_text=u'A Key Person is an executive-level individual within an Organization, such as a CEO, CFO, spokesperson etc.',verbose_name=u'Key Person')
	litigation_against = models.Relationship("self",null=True,rel_type='organization_has_litigation_against+',help_text=u'An entity is said to litigate against another when it is involved in a lawsuit or an out-of-court settlement with the other.',verbose_name=u'Litigation against')
	fundraising_round = models.Relationship("FundraisingRound",null=True,rel_type='organization_has_fundraising_round+',help_text=u'A Fundraising Round represents an event when an Organization was able to raise cash or another asset.',verbose_name=u'Fundraising round')
	monitoring_body = models.Relationship("self",null=True,rel_type='organization_has_monitoring_body+',help_text=u'The Monitoring Body is the organization that is responsible for overseeing the project. In the case of electricity projects, it is often the national electricity regulator.',verbose_name=u'Monitoring body')

	class Meta:
		verbose_name = u'Organization'
		verbose_name_plural = u'Organizations'

	def __unicode__(self):
		return self.name or u"Unkown"


class Distribution(models.NodeModel):
	_topic = u'energy'
	_parent = u'Amount'
	_description = u''
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	sold = models.StringProperty(null=True,help_text=u'The type of distribution can be donated, sold, loaned.',verbose_name=u'Type of distribution')
	year = models.DateTimeProperty(null=True,help_text=u'',verbose_name=u'Year')
	source = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to your source. If the source is a book, enter the URL to the book at Google Books or Amazon.',verbose_name=u'Source')
	units = models.IntegerProperty(null=True,help_text=u'The value of the amount.',verbose_name=u'Value')
	activity_in_country = models.Relationship(Country,null=True,rel_type='distribution_has_activity_in_country+',help_text=u'The list of countries or territories the entity is active in. ',verbose_name=u'Active in countries')

	class Meta:
		pass

class Price(models.NodeModel):
	_topic = u'energy'
	_parent = u'Amount'
	_description = u''
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	currency = models.StringProperty(null=True,help_text=u'The currency of the amount, using its 3-letter ISO-4217 code, e.g. USD, EUR, GBP etc.',verbose_name=u'Currency')
	year = models.DateTimeProperty(null=True,help_text=u'',verbose_name=u'Year')
	source = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to your source. If the source is a book, enter the URL to the book at Google Books or Amazon.',verbose_name=u'Source')
	units = models.StringProperty(null=True,help_text=u'The value of the amount.',verbose_name=u'Value')

	class Meta:
		pass


class EnergyProduct(models.NodeModel):
	_topic = u'energy'
	_description = u'An energy Product represents the concrete emanation of an energy Project. It can be a mass-produced device or a power plant.'
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	power_generation_per_unit_in_watt = models.IntegerProperty(null=True,help_text=u'The amount of energy, in watts, that can be generated by each unit of the product.',verbose_name=u'Power generation per unit (in watts)')
	households_served = models.StringProperty(null=True,help_text=u'The number of households that can use the product. E.g. an oven is for 1 household, a lamp is for 0.25 households, a power plant is for (power / average household consumption in the region) households. Leave blank if you\'re unsure.',verbose_name=u'Households served')
	source = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to your source. If the source is a book, enter the URL to the book at Google Books or Amazon.',verbose_name=u'Source')
	name = models.StringProperty(null=True,help_text=u'')
	image = models.URLProperty(null=True,help_text=u'The URL (starting with http://) where the image is hosted.',verbose_name=u'Image URL')
	distribution = models.Relationship("Distribution",null=True,rel_type='energy_product_has_distribution+',help_text=u'A Distribution represents the batch sales or gift of a product. Companies often communicate in terms of "in year X, Y units of Product Z were sold/distributed in Country A".',verbose_name=u'Distribution')
	operator = models.Relationship("Organization",null=True,rel_type='energy_product_has_operator+',help_text=u'Products, especially large ones such as power plants, have an Operator, usually a company.',verbose_name=u'Operator')
	price = models.Relationship("Price",null=True,rel_type='energy_product_has_price+',help_text=u'The price (use only digits, i.e. 8.99) of the Product at the date considered.',verbose_name=u'Price')

	class Meta:
		verbose_name = u'Energy product'
		verbose_name_plural = u'Energy products'

	def __unicode__(self):
		return self.name or u"Unkown"


class EnergyProject(models.NodeModel):
	_topic = u'energy'
	_description = u'An energy Project represents an endeavor to reach a particular aim (e.g. improve access to electricity, produce electricity in a certain way, improve energy efficiency, etc.). A project is the child of an Organization and takes its concrete form most often through Products.'
	_status = models.IntegerProperty(null=True,help_text=u'',verbose_name=u'status')
	_author = models.IntArrayProperty(null=True, help_text=u'People that edited this entity.', verbose_name=u'author')
	source = models.URLProperty(null=True,help_text=u'The URL (starting with http://) to your source. If the source is a book, enter the URL to the book at Google Books or Amazon.',verbose_name=u'Source')
	twitter_handle = models.StringProperty(null=True,help_text=u'The Twitter name of the entity (without the @)',verbose_name=u'Twitter handle')
	ended = models.DateTimeProperty(null=True,help_text=u'The date when the project or organization ended.',verbose_name=u'End date')
	started = models.DateTimeProperty(null=True,help_text=u'Date when the project was started. Can be anterior to the date when the parent organization was created.',verbose_name=u'Start date')
	comment = models.StringProperty(null=True,help_text=u'Enter a short comment to the entity you are reporting on (max. 500 characters).',verbose_name=u'Comment')
	image = models.URLProperty(null=True,help_text=u'The URL (starting with http://) where the image is hosted.',verbose_name=u'Image URL')
	name = models.StringProperty(null=True,help_text=u'')
	product = models.Relationship("EnergyProduct",null=True,rel_type='energy_project_has_product+',help_text=u'A Product represents the concrete emanation of an energy Project. It can be a mass-produced device or a power plant.')
	partner = models.Relationship("Organization",null=True,rel_type='energy_project_has_partner+',help_text=u'An entity can have Partners, i.e. Organizations that help without making a financial contribution (if financial or substancial help is involved, use Fundraising Round instead).')
	commentary = models.Relationship("Commentary",null=True,rel_type='energy_project_has_commentary+',help_text=u'A Commentary is an article, a blog post or a report that assesses the quality of the Project.')
	activity_in_country = models.Relationship(Country,null=True,rel_type='energy_project_has_activity_in_country+',help_text=u'The list of countries or territories the entity is active in. ')
	owner = models.Relationship("Organization",null=True,rel_type='energy_project_has_owner+',help_text=u'The formal Owner of the entity.')

	class Meta:
		verbose_name = u'Energy project'
		verbose_name_plural = u'Energy projects'

	def __unicode__(self):
		return self.name or u"Unkown"


########NEW FILE########
__FILENAME__ = resources
from .models                             import *
from app.detective.individual            import IndividualResource, IndividualMeta
from app.detective.topics.common.summary import SummaryResource

class SummaryResource(SummaryResource):
    class Meta(SummaryResource.Meta):
        pass

class CountryResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = Country.objects.all().select_related(depth=1)

class AmountResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = Amount.objects.all().select_related(depth=1)

class FundraisingRoundResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = FundraisingRound.objects.all().select_related(depth=1)

class PersonResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = Person.objects.all().select_related(depth=1)

class RevenueResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = Revenue.objects.all().select_related(depth=1)

class CommentaryResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = Commentary.objects.all().select_related(depth=1)

class OrganizationResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = Organization.objects.all().select_related(depth=1)

class DistributionResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = Distribution.objects.all().select_related(depth=1)

class PriceResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = Price.objects.all().select_related(depth=1)

class EnergyProductResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = EnergyProduct.objects.all().select_related(depth=1)

class EnergyProjectResource(IndividualResource):
    class Meta(IndividualMeta):
        queryset = EnergyProject.objects.all().select_related(depth=1)


########NEW FILE########
__FILENAME__ = urls
from .resources       import *
from django.conf.urls import patterns, include, url
from tastypie.api     import NamespacedApi

api = NamespacedApi(api_name='v1', urlconf_namespace='energy')
api.register(SummaryResource())
api.register(AmountResource())
api.register(CommentaryResource())
api.register(CountryResource())
api.register(DistributionResource())
api.register(FundraisingRoundResource())
api.register(OrganizationResource())
api.register(PersonResource())
api.register(PriceResource())
api.register(RevenueResource())
api.register(EnergyProductResource())
api.register(EnergyProjectResource())

urlpatterns = patterns('energy',
    url(r'', include(api.urls)),
)
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

urlpatterns = patterns('api',
    # Energy and Common are the 2 first topics and are threat with attentions
    url(r'^common/', include('app.detective.topics.common.urls', namespace='common')),
    url(r'^energy/', include('app.detective.topics.energy.urls', namespace='energy')),
)
########NEW FILE########
__FILENAME__ = utils
from django.forms.forms       import pretty_name
from random                   import randint
from os                       import listdir
from os.path                  import isdir, join
import importlib
import inspect
import re
import tempfile

def create_node_model(name, fields=None, app_label='', module='', options=None):
    """
    Create specified model
    """
    from neo4django.db            import models
    from django.db.models.loading import AppCache
    # Django use a cache by model
    cache = AppCache()
    # If we already create a model for this app
    if app_label in cache.app_models and name.lower() in cache.app_models[app_label]:
        # We just delete it quietly
        del cache.app_models[app_label][name.lower()]

    class Meta:
        # Using type('Meta', ...) gives a dictproxy error during model creation
        pass
    if app_label:
        # app_label must be set using the Meta inner class
        setattr(Meta, 'app_label', app_label)
    # Update Meta with any options that were provided
    if options is not None:
        for key, value in options.iteritems():
            setattr(Meta, key, value)
    # Set up a dictionary to simulate declarations within a class
    attrs = {'__module__': module, 'Meta': Meta}
    # Add in any fields that were provided
    if fields: attrs.update(fields)
    # Create the class, which automatically triggers ModelBase processing
    cls = type(name, (models.NodeModel,), attrs)
    return cls

def create_model_resource(model, path=None, Resource=None, Meta=None):
    """
        Create specified model's api resource
    """
    from app.detective.individual import IndividualResource, IndividualMeta
    if Resource is None: Resource = IndividualResource
    if Meta is None: Meta = IndividualMeta
    class Meta(IndividualMeta):
        queryset = model.objects.all().select_related(depth=1)
     # Set up a dictionary to simulate declarations within a class
    attrs = {'Meta': Meta}
    name  = "%sResource" % model.__name__
    mr = type(name, (IndividualResource,), attrs)
    # Overide the default module
    if path is not None: mr.__module__ = path
    return mr

def import_class(path):
    components = path.split('.')
    klass      = components[-1:]
    mod        = ".".join(components[0:-1])
    return getattr(__import__(mod, fromlist=klass), klass[0], None)

def get_topics(offline=True):
    if offline:
        # Load topics' names
        appsdir = "./app/detective/topics"
        return [ name for name in listdir(appsdir) if isdir(join(appsdir, name)) ]
    else:
        from app.detective.models import Topic
        return [t.module for t in Topic.objects.all()]

def get_topics_modules():
    # Import the whole topics directory automaticly
    CUSTOM_APPS = tuple( "app.detective.topics.%s" % a for a in get_topics() )
    return CUSTOM_APPS

def get_topic_models(topic):
    import warnings
    warnings.warn("deprecated, you should use the get_models() method from the Topic model.", DeprecationWarning)
    from django.db.models import Model
    from app.detective.models import Topic
    # Models to collect
    models        = []
    models_path   = "app.detective.topics.%s.models" % topic
    try:
        if isinstance(topic, Topic):
            models_module = topic.get_models()
        elif hasattr(topic, '__str__'):
            # Models to collect
            models_path   = "app.detective.topics.%s.models" % topic
            models_module = importlib.import_module(models_path)
        else:
            return []
        for i in dir(models_module):
            cls = getattr(models_module, i)
            # Collect every Django's model subclass
            if inspect.isclass(cls) and issubclass(cls, Model): models.append(cls)
    except ImportError:
        # Fail silently if the topic doesn't exist
        pass
    return models

def get_registered_models():
    from django.db import models
    import app.settings as settings
    mdls = []
    for app in settings.INSTALLED_APPS:
        models_name = app + ".models"
        try:
            models_module = __import__(models_name, fromlist=["models"])
            attributes = dir(models_module)
            for attr in attributes:
                try:
                    attrib = models_module.__getattribute__(attr)
                    if issubclass(attrib, models.Model) and attrib.__module__== models_name:
                        mdls.append(attrib)
                except TypeError:
                    pass
        except ImportError:
            pass
    return mdls

def get_model_fields(model):
    from app.detective           import register
    from django.db.models.fields import FieldDoesNotExist
    fields       = []
    models_rules = register.topics_rules().model(model)
    # Create field object
    for f in model._meta.fields:
        # Ignores field terminating by + or begining by _
        if not f.name.endswith("+") and not f.name.endswith("_set") and not f.name.startswith("_"):
            # Find related model for relation
            if f.get_internal_type().lower() == "relationship":
                # We received a model as a string
                if type(f.target_model) is str:
                    # Extract parts of the module path
                    module_path  = f.target_model.split(".")
                    # Import models as a module
                    module       = __import__( ".".join(module_path[0:-1]), fromlist=["class"])
                    # Import the target_model from the models module
                    target_model = getattr(module, module_path[-1], {__name__: None})
                else:
                    target_model  = f.target_model
                related_model = target_model.__name__
            else:
                related_model = None

            try:
                # Get the rules related to this model
                field_rules = models_rules.field(f.name).all()
            except FieldDoesNotExist:
                # No rules
                field_rules = []

            field = {
                'name'         : f.name,
                'type'         : f.get_internal_type(),
                'rel_type'     : getattr(f, "rel_type", ""),
                'help_text'    : getattr(f, "help_text", ""),
                'verbose_name' : getattr(f, "verbose_name", pretty_name(f.name)),
                'related_model': related_model,
                'model'        : model.__name__,
                'rules'        : field_rules
            }
            fields.append(field)

    return fields

def get_model_nodes():
    from neo4django.db import connection
    # Return buffer values
    if hasattr(get_model_nodes, "buffer"):
        results = get_model_nodes.buffer
        # Refresh the buffer ~ 1/10 calls
        if randint(0,10) == 10: del get_model_nodes.buffer
        return results
    query = """
        START n=node(*)
        MATCH n-[r:`<<TYPE>>`]->t
        WHERE HAS(t.name)
        RETURN t.name as name, ID(t) as id
    """
    # Bufferize the result
    get_model_nodes.buffer = connection.cypher(query).to_dicts()
    return get_model_nodes.buffer


def get_model_node_id(model):
    # All node from neo4j that are have ascending <<TYPE>> relationship
    nodes = get_model_nodes()
    try:
        app  = get_model_topic(model)
        name = model.__name__
        # Search for the node with the good name
        model_node  = next(n for n in nodes if n["name"] == "%s:%s" % (app, name) )
        return model_node["id"] or None
    # We didn't found the node id
    except StopIteration:
        return None

def get_model_topic(model):
    return model._meta.app_label or model.__module__.split(".")[-2]

def to_class_name(value=""):
    """
    Class name must:
        - begin by an uppercase
        - use camelcase
    """
    value = to_camelcase(value)
    value = list(value)
    if len(value) > 0:
        value[0] = value[0].capitalize()

    return "".join(value)


def to_camelcase(value=""):

    def camelcase():
        yield str.lower
        while True:
            yield str.capitalize

    value =  re.sub(r'([a-z])([A-Z])', r'\1_\2', value)
    c = camelcase()
    return "".join(c.next()(x) if x else '_' for x in value.split("_"))

def to_underscores(value=""):
    # Lowercase of the first letter
    value = list(value)
    if len(value) > 0:
        value[0] = value[0].lower()
    value = "".join(value)

    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def uploaded_to_tempfile(uploaded_file):
    # reset uploaded file's cusor
    cursor_pos = uploaded_file.tell()
    uploaded_file.seek(0)
    # create a new tempfile
    temporary = tempfile.TemporaryFile()
    # write the uploaded content
    temporary.write(uploaded_file.read())
    # reset cusors
    temporary.seek(0)
    uploaded_file.seek(cursor_pos)

    return temporary

def open_csv(csv_file):
    """
    Return a csv reader for the reading the given file.
    Deduce the format of the csv file.
    """
    import csv
    if hasattr(csv_file, 'read'):
        sample = csv_file.read(1024)
        csv_file.seek(0)
    elif type(csv_file) in (tuple, list):
        sample = "\n".join(csv_file[:5])
    dialect = csv.Sniffer().sniff(sample)
    dialect.doublequote = True
    reader = csv.reader(csv_file, dialect)
    return reader

# EOF

########NEW FILE########
__FILENAME__ = views
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.http      import Http404
from django.shortcuts import render_to_response, redirect
from django.template  import TemplateDoesNotExist


def home(request):
    # Render template without any argument
    response = render_to_response('home.dj.html')

    # Add a cookie containing some user information
    if request.user.is_authenticated():
        permissions = request.user.get_all_permissions()
        # Create the cookie
        response.set_cookie("user__is_logged",   True)
        response.set_cookie("user__is_staff",    request.user.is_staff)
        response.set_cookie("user__username",    unicode(request.user.username))
        response.set_cookie("user__permissions", unicode(u' '.join(permissions)))
    else:
        # Deletre existing cookie
        response.delete_cookie("user__is_logged")
        response.delete_cookie("user__is_staff")
        response.delete_cookie("user__username")
        response.delete_cookie("user__permissions")

    return response

def partial(request, partial_name=None):
    template_name = 'partials/' + partial_name + '.dj.html'
    try:
        return render_to_response(template_name)
    except TemplateDoesNotExist:
        raise Http404

def partial_explore(request, topic=None):
    template_name = 'partials/topic.explore.' + topic + '.dj.html'
    try:
        return render_to_response(template_name)
    except TemplateDoesNotExist:
        return partial(request, partial_name='topic.explore.common')

def not_found(request):
    return redirect("/404/")
########NEW FILE########
__FILENAME__ = activate_language
from django.utils import translation

class LocaleMiddleware(object):
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context. This allows pages to be dynamically
    translated to the language the user desires (if the language
    is available, of course).
    """
    def process_request(self, request):
        if "lang" in request.GET:
            language = request.GET["lang"]
            translation.activate(language)
            request.LANGUAGE_CODE = translation.get_language()
########NEW FILE########
__FILENAME__ = cache
from django.conf import settings
from django.core.cache import get_cache
from django.utils.cache import get_cache_key

class FetchFromCacheMiddleware(object):
    """
    Request-phase cache middleware that fetches a page from the cache.

    Must be used as part of the two-part update/fetch cache middleware.
    FetchFromCacheMiddleware must be the last piece of middleware in
    MIDDLEWARE_CLASSES so that it'll get called last during the request phase.
    """
    def __init__(self):
        self.cache_timeout = settings.CACHE_MIDDLEWARE_SECONDS
        self.key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        self.cache_anonymous_only = getattr(settings, 'CACHE_MIDDLEWARE_ANONYMOUS_ONLY', False)
        self.cache_alias = settings.CACHE_MIDDLEWARE_ALIAS
        self.cache = get_cache(self.cache_alias)


    def _should_update_cache(self, request):
        if self.cache_anonymous_only:
            assert hasattr(request, 'user'), "The Django cache middleware with CACHE_MIDDLEWARE_ANONYMOUS_ONLY=True requires authentication middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.auth.middleware.AuthenticationMiddleware' before the CacheMiddleware."
            if request.user.is_authenticated():
                # Don't cache user-variable requests from authenticated users.
                return False
        return True

    def process_request(self, request):
        """
        Checks whether the page is already cached and returns the cached
        version if available.
        """
        if not request.method in ('GET', 'HEAD') or not self._should_update_cache(request):
            request._cache_update_cache = False
            return None # Don't bother checking the cache.

        # try and get the cached GET response
        cache_key = get_cache_key(request, self.key_prefix, 'GET', cache=self.cache)
        if cache_key is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.
        response = self.cache.get(cache_key, None)
        # if it wasn't found and we are looking for a HEAD, try looking just for that
        if response is None and request.method == 'HEAD':
            cache_key = get_cache_key(request, self.key_prefix, 'HEAD', cache=self.cache)
            response = self.cache.get(cache_key, None)

        if response is None:
            request._cache_update_cache = True
            return None # No cache information available, need to rebuild.

        # hit, return cached response
        request._cache_update_cache = False
        return response
########NEW FILE########
__FILENAME__ = crossdomainxhr
# Middleware that allows cross-origin request
# https://gist.github.com/1369619
#
# More information about cross-origin: http://enable-cors.org/index.html
from django import http

try:
    from django.conf import settings
    XS_SHARING_ALLOWED_ORIGINS = settings.XS_SHARING_ALLOWED_ORIGINS
    XS_SHARING_ALLOWED_METHODS = settings.XS_SHARING_ALLOWED_METHODS
    XS_SHARING_ALLOWED_HEADERS = settings.XS_SHARING_ALLOWED_HEADERS
    XS_SHARING_ALLOWED_CREDENTIALS = settings.XS_SHARING_ALLOWED_CREDENTIALS
except AttributeError:
    XS_SHARING_ALLOWED_ORIGINS = '*'
    XS_SHARING_ALLOWED_METHODS = ['POST', 'GET', 'OPTIONS', 'PUT', 'DELETE']
    XS_SHARING_ALLOWED_HEADERS = ['Content-Type', '*']
    XS_SHARING_ALLOWED_CREDENTIALS = 'true'


class XsSharing(object):
    """
    This middleware allows cross-domain XHR using the html5 postMessage API.

    Access-Control-Allow-Origin: http://foo.example
    Access-Control-Allow-Methods: POST, GET, OPTIONS, PUT, DELETE

    Based off https://gist.github.com/426829
    """
    def process_request(self, request):
        if 'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in request.META:
            response = http.HttpResponse()
            response['Access-Control-Allow-Origin']  = XS_SHARING_ALLOWED_ORIGINS
            response['Access-Control-Allow-Methods'] = ",".join( XS_SHARING_ALLOWED_METHODS )
            response['Access-Control-Allow-Headers'] = ",".join( XS_SHARING_ALLOWED_HEADERS )
            response['Access-Control-Allow-Credentials'] = XS_SHARING_ALLOWED_CREDENTIALS
            return response

        return None

    def process_response(self, request, response):
        response['Access-Control-Allow-Origin']  = XS_SHARING_ALLOWED_ORIGINS
        response['Access-Control-Allow-Methods'] = ",".join( XS_SHARING_ALLOWED_METHODS )
        response['Access-Control-Allow-Headers'] = ",".join( XS_SHARING_ALLOWED_HEADERS )
        response['Access-Control-Allow-Credentials'] = XS_SHARING_ALLOWED_CREDENTIALS

        return response

########NEW FILE########
__FILENAME__ = virtualapi
import re
from django.http          import Http404
from app.detective        import topics
from app.detective.models import Topic

class VirtualApi:
    def process_request(self, request):
        regex = re.compile(r'api/([a-zA-Z0-9_\-]+)/')
        urlparts = regex.findall(request.path)
        if urlparts:
            # Get the topic that match to this url.
            try:
                topic = Topic.objects.get(slug=urlparts[0])
                # This will automaticly create the API if needed
                # or failed if the topic is unknown
                try:
                    getattr(topics, topic.module)
                except AttributeError as e:
                    raise Http404(e)
            except Topic.DoesNotExist:
                raise Http404()

        return None

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
import os
# for relative paths
here = lambda x: os.path.join(os.path.abspath(os.path.dirname(__file__)), x)

DEBUG = True
TEMPLATE_DEBUG = DEBUG
TASTYPIE_FULL_DEBUG = DEBUG

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# Custom data directory
DATA_ROOT = here('data')

ADMINS = (
    ('Pierre Romera', 'hello@pirhoo.com')
)

DEFAULT_FROM_EMAIL = 'Detective.io <contact@detective.io>'

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'dev.db'
    }
}

NEO4J_DATABASES = {
    'default' : {
        'HOST': "127.0.0.1",
        'PORT': 7474,
        'ENDPOINT':'/db/data'
    }
}

DATABASE_ROUTERS        = ['neo4django.utils.Neo4djangoIntegrationRouter']
SESSION_ENGINE          = "django.contrib.sessions.backends.db"
AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = here('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/public/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = here('staticfiles')

LOGIN_URL = "/admin"
# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Bower components
    ('components', here('static/components') ),
    here("detective/static"),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = os.getenv('SECRET_KEY', '#_o0^tt=lv1k8k-h=n%^=e&amp;vnvcxpnl=6+%&amp;+%(2!qiu!vtd9%')

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'app.middleware.cache.FetchFromCacheMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    'app.middleware.crossdomainxhr.XsSharing',
    # add urlmiddleware after all other middleware.
    'urlmiddleware.URLMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)


ROOT_URLCONF = 'app.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'app.wsgi.application'

TEMPLATE_DIRS = (
    here('detective/templates'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# JS/CSS COMPRESSOR SETTINGS
COMPRESS_PRECOMPILERS = (
    ('text/coffeescript', 'coffee --compile --stdio --bare'),
    ('text/less', 'lessc --include-path="%s" {infile} {outfile}' % here('static') ),
)

# Activate CSS minifier
COMPRESS_CSS_FILTERS = (
    "app.detective.compress_filter.CustomCssAbsoluteFilter",
    "compressor.filters.template.TemplateFilter",
)

COMPRESS_JS_FILTERS = (
    "compressor.filters.template.TemplateFilter",
    "compressor.filters.jsmin.JSMinFilter",
)

COMPRESS_TEMPLATE_FILTER_CONTEXT = {
    'STATIC_URL': STATIC_URL
}

# Remove BeautifulSoup requirement
COMPRESS_PARSER = 'compressor.parser.HtmlParser'
COMPRESS_ENABLED = True
#INTERNAL_IPS = ('127.0.0.1',)

TASTYPIE_DEFAULT_FORMATS = ['json']

INSTALLED_APPS = (
    'neo4django.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.auth',
    # Sign up activation
    'registration',
    # Compresses linked and inline JavaScript or CSS into a single cached file.
    'compressor',
    # API generator
    'tastypie',
    # Email backend
    "djrill",
    'password_reset',
    # Manage migrations
    'south',
    # Rich text editor
    'tinymce',
    # Redis queue backend
    "django_rq",
    # Internal
    'app.detective',
    'app.detective.permissions',
)

# Add customs app to INSTALLED_APPS
from app.detective.utils import get_topics_modules
INSTALLED_APPS = INSTALLED_APPS + get_topics_modules()

MANDRILL_API_KEY = os.getenv("MANDRILL_APIKEY")
EMAIL_BACKEND = "djrill.mail.backends.djrill.DjrillBackend"
# One-week activation window
ACCOUNT_ACTIVATION_DAYS = 7

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        #'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache',
    }
}

# Redis Queues
# RQ_SHOW_ADMIN_LINK will override the default admin template so it may interfere
# with other apps that modifies the default admin template.
RQ_SHOW_ADMIN_LINK = True
RQ_CONFIG = {
    'URL'  : os.getenv('REDISTOGO_URL', None) or os.getenv('REDISCLOUD_URL', None) or 'redis://localhost:6379',
    'DB'   : 0,
    'ASYNC': True
}
RQ_QUEUES = {
    'default': RQ_CONFIG,
    'high'   : RQ_CONFIG,
    'low'    : RQ_CONFIG
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(levelname)s] %(asctime)s | %(filename)s:%(lineno)d | %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
         'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'filters' : ['require_debug_true'],
            'formatter': 'simple'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'app.detective': {
            'handlers': ['mail_admins', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

########NEW FILE########
__FILENAME__ = settings_heroku
# -*- coding: utf-8 -*-
"""
Django Heroku settings for Detective.io project.
Packages required:
    * boto
    * django-storages
"""
from settings import *
from urlparse import urlparse
import os
import dj_database_url

ALLOWED_HOSTS = [".detective.io"]

DATABASES = {
    'default' : dj_database_url.config()
}

# Turn on database level autocommit
# Otherwise db can raise a "current transaction is aborted,
# commands ignored until end of transaction block"
DATABASES['default']['OPTIONS'] = {'autocommit': True,}

# Parse url given into environment variable
NEO4J_URL  = urlparse( os.getenv('NEO4J_URL', '') )
NEO4J_OPTIONS = {}

# Determines the hostname
if NEO4J_URL.username and NEO4J_URL.password:
    NEO4J_OPTIONS = {
        'username': NEO4J_URL.username,
        'password': NEO4J_URL.password
    }

NEO4J_DATABASES = {
    'default' : {
        # Concatenates username, password and hostname
        'HOST': NEO4J_URL.hostname,
        'PORT': int(NEO4J_URL.port),
        'ENDPOINT':'/db/data',
        'OPTIONS': NEO4J_OPTIONS
    }
}

# AWS ACCESS
AWS_ACCESS_KEY_ID          = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY      = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME    = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_QUERYSTRING_AUTH       = False
AWS_S3_FILE_OVERWRITE      = os.getenv('AWS_S3_FILE_OVERWRITE') == "True" and True or False

# Enable debug for minfication
DEBUG                      = bool(os.getenv('DEBUG', False))
# Configure static files for S3
STATIC_URL                 = os.getenv('STATIC_URL')
STATIC_ROOT                = here('staticfiles')
STATICFILES_DIRS          += (here('static'),)
INSTALLED_APPS            += ('storages',)
DEFAULT_FILE_STORAGE       = 'storages.backends.s3boto.S3BotoStorage'
# Static storage
STATICFILES_STORAGE        = DEFAULT_FILE_STORAGE
ADMIN_MEDIA_PREFIX         = STATIC_URL + 'admin/'

# JS/CSS compressor settings
COMPRESS_ENABLED           = True
COMPRESS_ROOT              = STATIC_ROOT
COMPRESS_URL               = STATIC_URL
COMPRESS_STORAGE           = STATICFILES_STORAGE
COMPRESS_OFFLINE           = True

# Activate CSS minifier
COMPRESS_CSS_FILTERS       = (
    "app.detective.compress_filter.CustomCssAbsoluteFilter",
    "compressor.filters.cssmin.CSSMinFilter",
    "compressor.filters.template.TemplateFilter",
)

COMPRESS_JS_FILTERS = (
    "compressor.filters.jsmin.JSMinFilter",
    "compressor.filters.template.TemplateFilter",
)

COMPRESS_OFFLINE_CONTEXT = {
    'STATIC_URL': STATIC_URL
}

COMPRESS_TEMPLATE_FILTER_CONTEXT = {
    'STATIC_URL': STATIC_URL
}

# Activate the cache, for true
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}

# EOF

########NEW FILE########
__FILENAME__ = settings_tests
#!/usr/bin/env python
# Encoding: utf-8

import os
from settings import *
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NEO4J_DATABASES['default']['OPTIONS'] = {
    'CLEANDB_URI': '/cleandb/supersecretdebugkey!',
}

NEO4J_TEST_DATABASES = NEO4J_DATABASES

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test.db'
    }
}

DEBUG = False

INSTALLED_APPS = list(INSTALLED_APPS)

# remove south an djrill to speed up the tests
INSTALLED_APPS.remove('south')
INSTALLED_APPS.remove('djrill')

NEO4DJANGO_PROFILE_REQUESTS = False
NEO4DJANGO_DEBUG_GREMLIN = False

# EOF

########NEW FILE########
__FILENAME__ = urls
from app.middleware.virtualapi import VirtualApi
from django.conf               import settings
from django.conf.urls          import patterns, include, url
from django.contrib            import admin
from urlmiddleware.conf        import middleware, mpatterns

admin.autodiscover()

# This will catch the api calls with a virtual api middleware.
# If needed, this middleware will create the API endpoints and resources
# that match to the given slug.
middlewarepatterns = mpatterns('',
    middleware(r'^api/([a-zA-Z0-9_\-]+)/', VirtualApi),
)

urlpatterns = patterns('',
    url(r'^api/',                                                 include('app.detective.urls')),
    url(r'^$',                                                    'app.detective.views.home', name='home'),
    url(r'^404/$',                                                'app.detective.views.home', name='404'),
    url(r'^admin/',                                               include(admin.site.urls)),
    url(r'^account/',                                             include('registration.backends.default.urls')),
    url(r'^account/activate/$',                                   'app.detective.views.home', name='registration_activate'),
    url(r'^account/reset-password/$',                             'app.detective.views.home', name='reset_password'),
    url(r'^account/reset-password-confirm/$',                     'app.detective.views.home', name='reset_password_confirm'),
    url(r'^page/$',                                               'app.detective.views.home', name='page-list'),
    url(r'^page/\w+/$',                                           'app.detective.views.home', name='page-single'),
    url(r'^login/$',                                              'app.detective.views.home', name='login'),
    url(r'^search/$',                                             'app.detective.views.home', name='search'),
    url(r'^signup/$',                                             'app.detective.views.home', name='signup'),
    url(r'^contact-us/$',                                         'app.detective.views.home', name='contact-us'),
    url(r'^job-runner/',                                          include('django_rq.urls')),
    url(r'^[a-zA-Z0-9_\-/]+/$',                                   'app.detective.views.home', name='user'),
    url(r'^[a-zA-Z0-9_\-/]+/[a-zA-Z0-9_\-/]+/$',                  'app.detective.views.home', name='explore'),
    url(r'^[a-zA-Z0-9_\-/]+/[a-zA-Z0-9_\-/]+/\w+/$',              'app.detective.views.home', name='list'),
    url(r'^[a-zA-Z0-9_\-/]+/[a-zA-Z0-9_\-/]+/\w+/\d+/$',          'app.detective.views.home', name='single'),
    url(r'^[a-zA-Z0-9_\-/]+/[a-zA-Z0-9_\-/]+/contribute/$',       'app.detective.views.home', name='contribute'),
    url(r'^partial/topic.explore.(?P<topic>([a-zA-Z0-9_\-/]+))\.html$', 'app.detective.views.partial_explore', name='partial_explore'),
    url(r'^partial/(?P<partial_name>([a-zA-Z0-9_\-/.]+))\.html$',  'app.detective.views.partial', name='partial'),
    url(r'^tinymce/', include('tinymce.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^public/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
    )

# Handle 404 with the homepage
handler404 = "app.detective.views.not_found"

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for app project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

# update python path with lib/
sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
########NEW FILE########
