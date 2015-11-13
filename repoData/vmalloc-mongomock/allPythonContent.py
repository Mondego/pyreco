__FILENAME__ = collection
import collections
import copy
import functools
import itertools
import json
import time
import warnings
from sentinels import NOTHING
from .filtering import filter_applies, iter_key_candidates
from . import ObjectId, OperationFailure, DuplicateKeyError
from .helpers import basestring, xrange

try:
    # Optional requirements for providing Map-Reduce functionality
    import execjs
except ImportError:     
    execjs = None

try:
    from bson import (json_util, SON)
except ImportError:
    json_utils = SON = None

from six import (
    string_types,
    text_type,
    iteritems,
    itervalues,
    iterkeys)
from mongomock import helpers


class Collection(object):
    def __init__(self, db, name):
        super(Collection, self).__init__()
        self.name = name
        self.full_name = "{0}.{1}".format(db.name, name)
        self._Collection__database = db
        self._documents = {}

    def __repr__(self):
        return "Collection({0}, '{1}')".format(self._Collection__database, self.name)

    def __getitem__(self, name):
        return self._Collection__database[self.name + '.' + name]

    def __getattr__(self, name):
        return self.__getitem__(name)

    def insert(self, data, manipulate=True,
               safe=None, check_keys=True, continue_on_error=False, **kwargs):
        if isinstance(data, list):
            return [self._insert(element) for element in data]
        return self._insert(data)

    def _insert(self, data):

        if not all(isinstance(k, string_types) for k in data):
            raise ValueError("Document keys must be strings")

        if '_id' not in data:
            data['_id'] = ObjectId()
        object_id = data['_id']
        if object_id in self._documents:
            raise DuplicateKeyError("Duplicate Key Error", 11000)
        self._documents[object_id] = self._internalize_dict(data)
        return object_id

    def _internalize_dict(self, d):
        return dict((k, copy.deepcopy(v)) for k, v in iteritems(d))

    def _has_key(self, doc, key):
        return key in doc

    def update(self, spec, document, upsert = False, manipulate = False,
               safe = False, multi = False, _check_keys = False, **kwargs):
        """Updates document(s) in the collection."""
        found = False
        updated_existing = False
        num_updated = 0
        for existing_document in itertools.chain(self._iter_documents(spec), [None]):
            # the sentinel document means we should do an upsert
            if existing_document is None:
                if not upsert:
                    continue
                existing_document = self._documents[self._insert(self._discard_operators(spec))]
            else:
                updated_existing = True
            num_updated += 1
            first = True
            found = True
            subdocument = None
            for k, v in iteritems(document):
                if k == '$set':
                    self._update_document_fields(existing_document, v, _set_updater)
                elif k == '$unset':
                    for field, value in iteritems(v):
                        if self._has_key(existing_document, field):
                            del existing_document[field]
                elif k == '$inc':
                    positional = False
                    for key in iterkeys(v):
                        if '$' in key:
                            positional = True
                            break

                    if positional:
                        subdocument = self._update_document_fields_positional(existing_document, v, spec, _inc_updater, subdocument)
                        continue
                    self._update_document_fields(existing_document, v, _inc_updater)
                elif k == '$addToSet':
                    for field, value in iteritems(v):
                        container = existing_document.setdefault(field, [])
                        if value not in container:
                            container.append(value)
                elif k == '$pull':
                    for field, value in iteritems(v):
                        nested_field_list = field.rsplit('.')
                        if len(nested_field_list) == 1:
                            arr = existing_document[field]
                            existing_document[field] = [obj for obj in arr if not obj == value]
                            continue

                        # nested fields includes a positional element
                        # need to find that element
                        if '$' in nested_field_list:
                            if not subdocument:
                                subdocument = self._get_subdocument(existing_document, spec, nested_field_list)

                            # value should be a dictionary since we're pulling
                            pull_results = []
                            # and the last subdoc should be an array
                            for obj in subdocument[nested_field_list[-1]]:
                                if isinstance(obj, dict):
                                    for pull_key, pull_value in iteritems(value):
                                        if obj[pull_key] != pull_value:
                                            pull_results.append(obj)
                                    continue
                                if obj != value:
                                    pull_results.append(obj)

                            # cannot write to doc directly as it doesn't save to existing_document
                            subdocument[nested_field_list[-1]] = pull_results
                elif k == '$push':
                    for field, value in iteritems(v):
                        nested_field_list = field.rsplit('.')
                        if len(nested_field_list) == 1:
                            if field not in existing_document:
                                existing_document[field] = []
                            # document should be a list
                            # append to it
                            if isinstance(value, dict):
                                if '$each' in value:
                                    # append the list to the field
                                    existing_document[field] += list(value['$each'])
                                    continue
                            existing_document[field].append(value)
                            continue

                        # nested fields includes a positional element
                        # need to find that element
                        if '$' in nested_field_list:
                            if not subdocument:
                                subdocument = self._get_subdocument(existing_document, spec, nested_field_list)

                            # we're pushing a list
                            push_results = []
                            if nested_field_list[-1] in subdocument:
                                # if the list exists, then use that list
                                push_results = subdocument[nested_field_list[-1]]

                            if isinstance(value, dict):
                                # check to see if we have the format
                                # { '$each': [] }
                                if '$each' in value:
                                    push_results += list(value['$each'])
                                else:
                                    push_results.append(value)
                            else:
                                push_results.append(value)

                            # cannot write to doc directly as it doesn't save to existing_document
                            subdocument[nested_field_list[-1]] = push_results
                else:
                    if first:
                        # replace entire document
                        for key in document.keys():
                            if key.startswith('$'):
                                # can't mix modifiers with non-modifiers in update
                                raise ValueError('field names cannot start with $ [{}]'.format(k))
                        _id = spec.get('_id', existing_document.get('_id', None))
                        existing_document.clear()
                        if _id:
                            existing_document['_id'] = _id
                        existing_document.update(self._internalize_dict(document))
                        if existing_document['_id'] != _id:
                            # id changed, fix index
                            del self._documents[_id]
                            self.insert(existing_document)
                        break
                    else:
                        # can't mix modifiers with non-modifiers in update
                        raise ValueError('Invalid modifier specified: {}'.format(k))
                first = False
            if not multi:
                break

        return {
            text_type("connectionId"): self._Collection__database.connection._id,
            text_type("err"): None,
            text_type("ok"): 1.0,
            text_type("n"): num_updated,
            text_type("updatedExisting"): updated_existing,
        }

    def _get_subdocument(self, existing_document, spec, nested_field_list):
        """
        This method retrieves the subdocument of the existing_document.nested_field_list. It uses the spec to filter
        through the items. It will continue to grab nested documents until it can go no further. It will then return the
        subdocument that was last saved. '$' is the positional operator, so we use the $elemMatch in the spec to find
        the right subdocument in the array.
        """
        # current document in view
        doc = existing_document
        # previous document in view
        subdocument = existing_document
        # current spec in view
        subspec = spec
        # walk down the dictionary
        for subfield in nested_field_list:
            if subfield == '$':
                # positional element should have the equivalent elemMatch in the query
                subspec = subspec['$elemMatch']
                for item in doc:
                    # iterate through
                    if filter_applies(subspec, item):
                        # found the matching item
                        # save the parent
                        subdocument = doc
                        # save the item
                        doc = item
                        break
                continue

            subdocument = doc
            doc = doc[subfield]
            if not subfield in subspec:
                break
            subspec = subspec[subfield]

        return subdocument

    def _discard_operators(self, doc):
        # TODO: this looks a little too naive...
        return dict((k, v) for k, v in iteritems(doc) if not k.startswith("$"))

    def find(self, spec = None, fields = None, filter = None, sort = None, timeout = True, limit = 0, snapshot = False, as_class = None, skip = 0, slave_okay=False):
        if filter is not None:
            _print_deprecation_warning('filter', 'spec')
            if spec is None:
                spec = filter
        if as_class is None:
            as_class = dict
        return Cursor(self, functools.partial(self._get_dataset, spec, sort, fields, as_class, skip), limit=limit)

    def _get_dataset(self, spec, sort, fields, as_class, skip):
        dataset = (self._copy_only_fields(document, fields, as_class) for document in self._iter_documents(spec))
        if sort:
            for sortKey, sortDirection in reversed(sort):
                dataset = iter(sorted(dataset, key = lambda x: _resolve_key(sortKey, x), reverse = sortDirection < 0))
        for i in xrange(skip):
            try:
                unused = next(dataset)
            except StopIteration:
                pass

        return dataset

    def _copy_field(self, obj, container):
        if isinstance(obj, list):
            new = []
            for item in obj:
                new.append(self._copy_field(item, container))
            return new
        if isinstance(obj, dict):
            new = container()
            for key, value in obj.items():
                new[key] = self._copy_field(value, container)
            return new
        else:
            return copy.copy(obj)

    def _copy_only_fields(self, doc, fields, container):
        """Copy only the specified fields."""

        if fields is None:
            return self._copy_field(doc, container)
        else:
            if not fields:
                fields = {"_id": 1}
            if not isinstance(fields, dict):
                fields = helpers._fields_list_to_dict(fields)

            #we can pass in something like {"_id":0, "field":1}, so pull the id value out and hang on to it until later
            id_value = fields.pop('_id', 1)

            #other than the _id field, all fields must be either includes or excludes, this can evaluate to 0
            if len(set(list(fields.values()))) > 1:
                raise ValueError('You cannot currently mix including and excluding fields.')

            #if we have novalues passed in, make a doc_copy based on the id_value
            if len(list(fields.values())) == 0:
                if id_value == 1:
                    doc_copy = container()
                else:
                    doc_copy = self._copy_field(doc, container)
            #if 1 was passed in as the field values, include those fields
            elif  list(fields.values())[0] == 1:
                doc_copy = container()
                for key in fields:
                    if key in doc:
                        doc_copy[key] = doc[key]
            #otherwise, exclude the fields passed in
            else:
                doc_copy = self._copy_field(doc, container)
                for key in fields:
                    if key in doc_copy:
                        del doc_copy[key]

            #set the _id value if we requested it, otherwise remove it
            if id_value == 0:
                if '_id' in doc_copy:
                    del doc_copy['_id']
            else:
                if '_id' in doc:
                    doc_copy['_id'] = doc['_id']

            fields['_id'] = id_value #put _id back in fields
            return doc_copy

    def _update_document_fields(self, doc, fields, updater):
        """Implements the $set behavior on an existing document"""
        for k, v in iteritems(fields):
            self._update_document_single_field(doc, k, v, updater)

    def _update_document_fields_positional(self, doc, fields, spec, updater, subdocument=None):
        """Implements the $set behavior on an existing document"""
        for k, v in iteritems(fields):
            if '$' in k:
                field_name_parts = k.split('.')
                if not subdocument:
                    current_doc = doc
                    subspec = spec
                    for part in field_name_parts[:-1]:
                        if part == '$':
                            subspec = subspec['$elemMatch']
                            for item in current_doc:
                                if filter_applies(subspec, item):
                                    current_doc = item
                                    break
                            continue

                        subspec = subspec[part]
                        current_doc = current_doc[part]
                    subdocument = current_doc
                updater(subdocument, field_name_parts[-1], v)
                continue
            # otherwise, we handle it the standard way
            self._update_document_single_field(doc, k, v, updater)

        return subdocument

    def _update_document_single_field(self, doc, field_name, field_value, updater):
        field_name_parts = field_name.split(".")
        for part in field_name_parts[:-1]:
            if not isinstance(doc, dict) and not isinstance(doc, list):
                return # mongodb skips such cases
            if isinstance(doc, list):
                try:
                    doc = doc[int(part)]
                    continue
                except ValueError:
                    pass
            doc = doc.setdefault(part, {})
        updater(doc, field_name_parts[-1], field_value)

    def _iter_documents(self, filter = None):
        return (document for document in itervalues(self._documents) if filter_applies(filter, document))

    def find_one(self, spec_or_id=None, *args, **kwargs):
        # Allow calling find_one with a non-dict argument that gets used as
        # the id for the query.
        if spec_or_id is None:
            spec_or_id = {}
        if not isinstance(spec_or_id, collections.Mapping):
            spec_or_id = {'_id':spec_or_id}

        try:
            return next(self.find(spec_or_id, *args, **kwargs))
        except StopIteration:
            return None

    def find_and_modify(self, query = {}, update = None, upsert = False, **kwargs):
        remove = kwargs.get("remove", False)
        if kwargs.get("new", False) and remove:
            raise OperationFailure("remove and returnNew can't co-exist") # message from mongodb

        if remove and update is not None:
            raise ValueError("Can't do both update and remove")

        old = self.find_one(query)
        if not old:
            if upsert:
                old = {'_id':self.insert(query)}
            else:
                return None

        if remove:
            self.remove({"_id": old["_id"]})
        else:
            self.update({'_id':old['_id']}, update)

        if kwargs.get('new', False):
            return self.find_one({'_id':old['_id']})
        return old

    def save(self, to_save, manipulate = True, safe = False, **kwargs):
        if not isinstance(to_save, dict):
            raise TypeError("cannot save object of type %s" % type(to_save))

        if "_id" not in to_save:
            return self.insert(to_save)
        else:
            self.update({"_id": to_save["_id"]}, to_save, True,
                        manipulate, safe, _check_keys = True, **kwargs)
            return to_save.get("_id", None)

    def remove(self, spec_or_id = None, search_filter = None):
        """Remove objects matching spec_or_id from the collection."""
        if search_filter is not None:
            _print_deprecation_warning('search_filter', 'spec_or_id')
        if spec_or_id is None:
            spec_or_id = search_filter if search_filter else {}
        if not isinstance(spec_or_id, dict):
            spec_or_id = {'_id': spec_or_id}
        to_delete = list(self.find(spec = spec_or_id))
        for doc in to_delete:
            doc_id = doc['_id']
            del self._documents[doc_id]

        return {
            "connectionId": self._Collection__database.connection._id,
            "n": len(to_delete),
            "ok": 1.0,
            "err": None,
        }

    def count(self):
        return len(self._documents)

    def drop(self):
        del self._documents
        self._documents = {}

    def ensure_index(self, key_or_list, cache_for = 300, **kwargs):
        pass

    def map_reduce(self, map_func, reduce_func, out, full_response=False, query=None, limit=0):
        if execjs is None:
            raise NotImplementedError(
                "PyExecJS is required in order to run Map-Reduce. "
                "Use 'pip install pyexecjs pymongo' to support Map-Reduce mock."
            )
        if limit == 0:
            limit = None
        start_time = time.clock()
        out_collection = None
        reduced_rows = None
        full_dict = {'counts': {'input': 0,
                                'reduce':0,
                                'emit':0,
                                'output':0},
                     'timeMillis': 0,
                     'ok': 1.0,
                     'result': None}
        map_ctx = execjs.compile("""
            function doMap(fnc, docList) {
                var mappedDict = {};
                function emit(key, val) {
                    if (key['$oid']) {
                        mapped_key = '$oid' + key['$oid'];
                    }
                    else {
                        mapped_key = key; 
                    }
                    if(!mappedDict[mapped_key]) {
                        mappedDict[mapped_key] = [];
                    }
                    mappedDict[mapped_key].push(val);
                }
                mapper = eval('('+fnc+')');
                var mappedList = new Array();
                for(var i=0; i<docList.length; i++) {
                    var thisDoc = eval('('+docList[i]+')');
                    var mappedVal = (mapper).call(thisDoc);
                }
                return mappedDict;
            }
        """)
        reduce_ctx = execjs.compile("""
            function doReduce(fnc, docList) {
                var reducedList = new Array();
                reducer = eval('('+fnc+')');
                for(var key in docList) {
                    var reducedVal = {'_id': key,
                            'value': reducer(key, docList[key])};
                    reducedList.push(reducedVal);
                }
                return reducedList;
            }
        """)
        doc_list = [json.dumps(doc, default=json_util.default) for doc in self.find(query)]
        mapped_rows = map_ctx.call('doMap', map_func, doc_list)
        reduced_rows = reduce_ctx.call('doReduce', reduce_func, mapped_rows)[:limit]
        for reduced_row in reduced_rows:
            if reduced_row['_id'].startswith('$oid'):
                reduced_row['_id'] = ObjectId(reduced_row['_id'][4:])
        reduced_rows = sorted(reduced_rows, key=lambda x: x['_id'])
        if full_response:
            full_dict['counts']['input'] = len(doc_list)
            for key in mapped_rows.keys():
                emit_count = len(mapped_rows[key])
                full_dict['counts']['emit'] += emit_count
                if emit_count > 1:
                    full_dict['counts']['reduce'] += 1
            full_dict['counts']['output'] = len(reduced_rows)
        if isinstance(out, (str, bytes)):
            out_collection = getattr(self._Collection__database, out)
            out_collection.drop()
            out_collection.insert(reduced_rows)
            ret_val = out_collection
            full_dict['result'] = out
        elif isinstance(out, SON) and out.get('replace') and out.get('db'):
            # Must be of the format SON([('replace','results'),('db','outdb')])
            out_db = getattr(self._Collection__database._Database__connection, out['db'])
            out_collection = getattr(out_db, out['replace'])
            out_collection.insert(reduced_rows)
            ret_val = out_collection
            full_dict['result'] = {'db': out['db'], 'collection': out['replace']}
        elif isinstance(out, dict) and out.get('inline'):
            ret_val = reduced_rows
            full_dict['result'] = reduced_rows
        else:
            raise TypeError("'out' must be an instance of string, dict or bson.SON")
        full_dict['timeMillis'] = int(round((time.clock() - start_time) * 1000))
        if full_response:
            ret_val = full_dict
        return ret_val

    def inline_map_reduce(self, map_func, reduce_func, full_response=False, query=None, limit=0):
        return self.map_reduce(map_func, reduce_func, {'inline':1}, full_response, query, limit)

    def distinct(self, key):
        return self.find().distinct(key)

    def group(self, key, condition, initial, reduce, finalize=None):
        reduce_ctx = execjs.compile("""
            function doReduce(fnc, docList) {
                reducer = eval('('+fnc+')');
                for(var i=0, l=docList.length; i<l; i++) {
                    try {
                        reducedVal = reducer(docList[i-1], docList[i]); 
                    }
                    catch (err) {
                        continue;
                    }
                }
            return docList[docList.length - 1];
            }
        """)

        ret_array = []
        doc_list_copy = []
        ret_array_copy = []
        reduced_val = {}
        doc_list = [doc for doc in self.find(condition)]
        for doc in doc_list:
            doc_copy = copy.deepcopy(doc)
            for k in doc:
                if isinstance(doc[k], ObjectId):
                    doc_copy[k] = str(doc[k])
                if k not in key and k not in reduce:
                    del doc_copy[k]
            for initial_key in initial:
                if initial_key in doc.keys():
                    pass
                else:
                    doc_copy[initial_key] = initial[initial_key]
            doc_list_copy.append(doc_copy)
        doc_list = doc_list_copy
        for k in key:
            doc_list = sorted(doc_list, key=lambda x: _resolve_key(k, x))
        for k in key:
            if not isinstance(k, basestring):
                raise TypeError("Keys must be a list of key names, "
                                "each an instance of %s" % (basestring.__name__,))
            for k2, group in itertools.groupby(doc_list, lambda item: item[k]):
                group_list = ([x for x in group])
                reduced_val = reduce_ctx.call('doReduce', reduce, group_list)
                ret_array.append(reduced_val)
        for doc in ret_array:
            doc_copy = copy.deepcopy(doc)
            for k in doc:
                if k not in key and k not in initial.keys():
                    del doc_copy[k]
            ret_array_copy.append(doc_copy)
        ret_array = ret_array_copy
        return ret_array

    def aggregate(self, pipeline, **kwargs):
        pipeline_operators =       ['$project','$match','$redact','$limit','$skip','$unwind','$group','$sort','$geoNear','$out']
        group_operators =          ['$addToSet', '$first','$last','$max','$min','$avg','$push','$sum']
        boolean_operators =        ['$and','$or', '$not']
        set_operators =            ['$setEquals', '$setIntersection', '$setDifference', '$setUnion', '$setIsSubset', '$anyElementTrue', '$allElementsTrue']
        compairison_operators =    ['$cmp','$eq','$gt','$gte','$lt','$lte','$ne']
        aritmetic_operators =      ['$add','$divide','$mod','$multiply','$subtract']
        string_operators =         ['$concat','$strcasecmp','$substr','$toLower','$toUpper']
        text_search_operators =    ['$meta']
        array_operators =          ['$size']
        projection_operators =     ['$map', '$let', '$literal']
        date_operators =           ['$dayOfYear','$dayOfMonth','$dayOfWeek','$year','$month','$week','$hour','$minute','$second','$millisecond']
        conditional_operators =    ['$cond', '$ifNull']

        out_collection = [doc for doc in self.find()]
        grouped_collection = []
        for expression in pipeline:
            for k, v in iteritems(expression):
                if k == '$match':
                    out_collection = [doc for doc in out_collection if filter_applies(v, doc)]
                elif k == '$group':
                    group_func_keys = expression['$group']['_id'][1:]
                    for group_key in reversed(group_func_keys):
                        out_collection = sorted(out_collection, key=lambda x: _resolve_key(group_key, x))
                    for field, value in iteritems(v):
                        if field != '_id':
                            for func, key in iteritems(value):
                                if func == "$sum" or "$avg":
                                    for group_key in group_func_keys:
                                        for ret_value, group in itertools.groupby(out_collection, lambda item: item[group_key]):
                                            doc_dict = {}
                                            group_list = ([x for x in group])
                                            doc_dict['_id'] = ret_value
                                            current_val = 0
                                            if func == "$sum":
                                                for doc in group_list:
                                                    current_val = sum([current_val, doc[field]])
                                                doc_dict[field] = current_val
                                            else:
                                                for doc in group_list:
                                                    current_val = sum([current_val, doc[field]])
                                                    avg = current_val / len(group_list)
                                                doc_dict[field] = current_val
                                            grouped_collection.append(doc_dict)
                                else:
                                    if func in group_operators:
                                        raise NotImplementedError(
                                            "Although %s is a valid group operator for the aggregation pipeline, "
                                            "%s is currently not implemented in Mongomock."
                                        )
                                    else:
                                        raise NotImplementedError(
                                            "%s is not a valid group operator for the aggregation pipeline. "
                                            "See http://docs.mongodb.org/manual/meta/aggregation-quick-reference/ "
                                            "for a complete list of valid operators."
                                        )
                    out_collection = grouped_collection
                elif k == '$sort':
                    sort_array = []
                    for x, y in v.items():
                        sort_array.append({x:y})
                    for sort_pair in reversed(sort_array):
                        for sortKey, sortDirection in sort_pair.items():
                            out_collection = sorted(out_collection, key = lambda x: _resolve_key(sortKey, x), reverse = sortDirection < 0)
                elif k == '$skip':
                    out_collection = out_collection[v:]
                elif k == '$limit':
                    out_collection = out_collection[:v]
                else:
                    if k in pipeline_operators:
                        raise NotImplementedError(
                            "Although %s is a valid operator for the aggregation pipeline, "
                            "%s is currently not implemented in Mongomock."
                        )
                    else:
                        raise NotImplementedError(
                            "%s is not a valid operator for the aggregation pipeline. "
                            "See http://docs.mongodb.org/manual/meta/aggregation-quick-reference/ "
                            "for a complete list of valid operators."
                        )
        return {'ok':1.0, 'result':out_collection}

def _resolve_key(key, doc):
    return next(iter(iter_key_candidates(key, doc)), NOTHING)

class Cursor(object):
    def __init__(self, collection, dataset_factory, limit=0):
        super(Cursor, self).__init__()
        self.collection = collection
        self._factory = dataset_factory
        self._dataset = self._factory()
        self._limit = limit if limit != 0 else None #pymongo limit defaults to 0, returning everything
        self._skip = None

    def __iter__(self):
        return self

    def clone(self):
        return Cursor(self.collection, self._factory, self._limit)

    def __next__(self):
        if self._skip:
            for i in range(self._skip):
                next(self._dataset)
            self._skip = None
        if self._limit is not None and self._limit <= 0:
            raise StopIteration()
        if self._limit is not None:
            self._limit -= 1
        return next(self._dataset)
    next = __next__
    def sort(self, key_or_list, direction = None):
        if direction is None:
            direction = 1
        if isinstance(key_or_list, (tuple, list)):
            for sortKey, sortDirection in reversed(key_or_list):
                self._dataset = iter(sorted(self._dataset, key = lambda x: _resolve_key(sortKey, x), reverse = sortDirection < 0))
        else:
            self._dataset = iter(sorted(self._dataset, key = lambda x: _resolve_key(key_or_list, x), reverse = direction < 0))
        return self

    def count(self, with_limit_and_skip=False):
        arr = [x for x in self._dataset]
        count = len(arr)
        if with_limit_and_skip:
            if self._skip:
                count -= self._skip
            if self._limit and count > self._limit:
                count = self._limit
        self._dataset = iter(arr)
        return count

    def skip(self, count):
        self._skip = count
        return self
    def limit(self, count):
        self._limit = count
        return self
    def batch_size(self, count):
        return self

    def close(self):
        pass

    def distinct(self, key):
        if not isinstance(key, basestring):
            raise TypeError('cursor.distinct key must be a string')
        unique = set()
        for x in iter(self._dataset):
            value = _resolve_key(key, x)
            if value == NOTHING: continue
            unique.add(value)
        return list(unique)

    def __getitem__(self, index):
        arr = [x for x in self._dataset]
        count = len(arr)
        self._dataset = iter(arr)
        return arr[index]

def _set_updater(doc, field_name, value):
    if isinstance(doc, dict):
        doc[field_name] = value

def _inc_updater(doc, field_name, value):
    if isinstance(doc, dict):
        doc[field_name] = doc.get(field_name, 0) + value

def _sum_updater(doc, field_name, current, result):
    if isinstance(doc, dict):
        result = current + doc.get[field_name, 0]
        return result

########NEW FILE########
__FILENAME__ = connection
import itertools
from .database import Database

class Connection(object):

    _CONNECTION_ID = itertools.count()

    def __init__(self, host = None, port = None, max_pool_size = 10,
                 network_timeout = None, document_class = dict,
                 tz_aware = False, _connect = True, **kwargs):
        super(Connection, self).__init__()
        self.host = host
        self.port = port
        self._databases = {}
        self._id = next(self._CONNECTION_ID)
        self.document_class = document_class

    def __getitem__(self, db_name):
        db = self._databases.get(db_name, None)
        if db is None:
            db = self._databases[db_name] = Database(self, db_name)
        return db
    def __getattr__(self, attr):
        return self[attr]

    def __repr__(self):
        identifier = []
        host = getattr(self,'host','')
        port = getattr(self,'port',None)
        if host is not None:
            identifier = ["'{0}'".format(host)]
            if port is not None:
                identifier.append(str(port))
        return "mongomock.Connection({0})".format(', '.join(identifier))

    def server_info(self):
        return {
            "version" : "2.0.6",
            "sysInfo" : "Mock",
            "versionArray" : [
                              2,
                              0,
                              6,
                              0
                              ],
            "bits" : 64,
            "debug" : False,
            "maxBsonObjectSize" : 16777216,
            "ok" : 1
    }

#Connection is now depricated, it's called MongoClient instead
class MongoClient(Connection):
    def stub(self):
        pass

########NEW FILE########
__FILENAME__ = database
from .collection import Collection

class Database(object):
    def __init__(self, conn, name):
        super(Database, self).__init__()
        self.name = name
        self._Database__connection = conn
        self._collections = {'system.indexes' : Collection(self, 'system.indexes')}

    def __getitem__(self, coll_name):
        coll = self._collections.get(coll_name, None)
        if coll is None:
            coll = self._collections[coll_name] = Collection(self, coll_name)
        return coll

    def __getattr__(self, attr):
        return self[attr]

    def __repr__(self):
        return "Database({0}, '{1}')".format(self._Database__connection, self.name)

    @property
    def connection(self):
        return self._Database__connection

    def collection_names(self, include_system_collections=True):
        if include_system_collections:
            return list(self._collections.keys())

        result = []
        for name in self._collections.keys():
            if name.startswith("system."): continue
            result.append(name)

        return result

    def drop_collection(self, name_or_collection):
        try:
            # FIXME a better way to remove an entry by value ?
            if isinstance(name_or_collection, Collection):
                for collection in self._collections.items():
                    if collection[1] is name_or_collection:
                        del self._collections[collection[0]]
            else:
                del self._collections[name_or_collection]
        except:  # EAFP paradigm (http://en.m.wikipedia.org/wiki/Python_syntax_and_semantics)
            pass

########NEW FILE########
__FILENAME__ = filtering
import operator
import re
import warnings
from six import iteritems, string_types
from sentinels import NOTHING
from .helpers import ObjectId, RE_TYPE

def filter_applies(search_filter, document):
    """
    This function implements MongoDB's matching strategy over documents in the find() method and other
    related scenarios (like $elemMatch)
    """
    if search_filter is None:
        return True
    elif isinstance(search_filter, ObjectId):
        search_filter = {'_id': search_filter}

    for key, search in iteritems(search_filter):

        is_match = False

        for doc_val in iter_key_candidates(key, document):
            if isinstance(search, dict):
                is_match = all(
                    operator_string in OPERATOR_MAP and OPERATOR_MAP[operator_string] (doc_val, search_val) or
                    operator_string == '$not' and _not_op(document, key, search_val)
                    for operator_string, search_val in iteritems(search)
                )
            elif isinstance(search, RE_TYPE) and isinstance(doc_val, (string_types, list)):
                is_match = _regex(doc_val, search)
            elif key in LOGICAL_OPERATOR_MAP:
                is_match = LOGICAL_OPERATOR_MAP[key] (document, search)
            elif isinstance(doc_val, (list, tuple)):
                is_match = (search in doc_val or search == doc_val)
                if isinstance(search, ObjectId):
                    is_match |= (str(search) in doc_val)
            else:
                is_match = (doc_val == search) or (search is None and doc_val is NOTHING)

            if is_match:
                break

        if not is_match:
            return False

    return True

def iter_key_candidates(key, doc):
    """
    Get possible subdocuments or lists that are referred to by the key in question
    Returns the appropriate nested value if the key includes dot notation.
    """
    if doc is None:
        return ()

    if not key:
        return [doc]

    if isinstance(doc, list):
        return _iter_key_candidates_sublist(key, doc)

    if not isinstance(doc, dict):
        return ()

    key_parts = key.split('.')
    if len(key_parts) == 1:
        return [doc.get(key, NOTHING)]

    sub_key = '.'.join(key_parts[1:])
    sub_doc = doc.get(key_parts[0], {})
    return iter_key_candidates(sub_key, sub_doc)

def _iter_key_candidates_sublist(key, doc):
    """
    :param doc: a list to be searched for candidates for our key
    :param key: the string key to be matched
    """
    key_parts = key.split(".")
    sub_key = key_parts.pop(0)
    key_remainder = ".".join(key_parts)
    try:
        sub_key_int = int(sub_key)
    except ValueError:
        sub_key_int = None

    if sub_key_int is None:
        # subkey is not an integer...

        return [x
                for sub_doc in doc
                if isinstance(sub_doc, dict) and sub_key in sub_doc
                for x in iter_key_candidates(key_remainder, sub_doc[sub_key])]

    else:

        # subkey is an index
        if sub_key_int >= len(doc):
            return () # dead end

        sub_doc = doc[sub_key_int]

        if key_parts:
            return iter_key_candidates(".".join(key_parts), sub_doc)

        return [sub_doc]

def _force_list(v):
    return v if isinstance(v, (list, tuple)) else [v]

def _all_op(doc_val, search_val):
    dv = _force_list(doc_val)
    return all(x in dv for x in search_val)

def _not_op(d, k, s):
    return not filter_applies({k: s}, d)

def _not_nothing_and(f):
    "wrap an operator to return False if the first arg is NOTHING"
    return lambda v, l: v is not NOTHING and f(v, l)

def _elem_match_op(doc_val, query):
    if not isinstance(doc_val, list):
        return False
    return any(filter_applies(query, item) for item in doc_val)

def _regex(doc_val, regex):
    return any(regex.search(item) for item in _force_list(doc_val))

def _print_deprecation_warning(old_param_name, new_param_name):
    warnings.warn("'%s' has been deprecated to be in line with pymongo implementation, "
                  "a new parameter '%s' should be used instead. the old parameter will be kept for backward "
                  "compatibility purposes." % old_param_name, new_param_name, DeprecationWarning)

OPERATOR_MAP = {'$ne': operator.ne,
                '$gt': _not_nothing_and(operator.gt),
                '$gte': _not_nothing_and(operator.ge),
                '$lt': _not_nothing_and(operator.lt),
                '$lte': _not_nothing_and(operator.le),
                '$all':_all_op,
                '$in':lambda dv, sv: any(x in sv for x in _force_list(dv)),
                '$nin':lambda dv, sv: all(x not in sv for x in _force_list(dv)),
                '$exists':lambda dv, sv: bool(sv) == (dv is not NOTHING),
                '$regex': _not_nothing_and(lambda dv, sv: _regex(dv, re.compile(sv))),
                '$elemMatch': _elem_match_op,
                }

LOGICAL_OPERATOR_MAP = {'$or':lambda d, subq: any(filter_applies(q, d) for q in subq),
                        '$and':lambda d, subq: all(filter_applies(q, d) for q in subq),
                        }

########NEW FILE########
__FILENAME__ = helpers
import sys
import re

_PY2 = sys.version_info < (3, 0)

try:
    from bson import (ObjectId, RE_TYPE)
except ImportError:
    from mongomock.object_id import ObjectId
    RE_TYPE = type(re.compile(''))

if _PY2:
    from __builtin__ import xrange
else:
    xrange = range

#for Python 3 compatibility
try:
  unicode = unicode
  from __builtin__ import basestring
except NameError:
  unicode = str
  basestring = (str, bytes)


  
def _fields_list_to_dict(fields):
    """Takes a list of field names and returns a matching dictionary.

    ["a", "b"] becomes {"a": 1, "b": 1}

    and

    ["a.b.c", "d", "a.c"] becomes {"a.b.c": 1, "d": 1, "a.c": 1}
    """
    as_dict = {}
    for field in fields:
        if not isinstance(field, basestring):
            raise TypeError("fields must be a list of key names, "
                            "each an instance of %s" % (basestring.__name__,))
        as_dict[field] = 1
    return as_dict

########NEW FILE########
__FILENAME__ = object_id
import uuid

class ObjectId(object):
    def __init__(self, id=None):
        super(ObjectId, self).__init__()
        if id is None:
            self._id = uuid.uuid1()
        else:
            self._id = uuid.UUID(id)
    def __eq__(self, other):
        return isinstance(other, ObjectId) and other._id == self._id
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):
        return hash(self._id)
    def __repr__(self):
        return 'ObjectId({0})'.format(self._id)
    def __str__(self):
        return str(self._id)

########NEW FILE########
__FILENAME__ = __version__
__version__ = "1.2.0"

########NEW FILE########
__FILENAME__ = diff
from platform import python_version

class _NO_VALUE(object):
    pass
NO_VALUE = _NO_VALUE() # we don't use NOTHING because it might be returned from various APIs

_SUPPORTED_TYPES = set([
    int, float, bool, str
])

dict_type = dict

if python_version() < "3.0":
    _SUPPORTED_TYPES.update([long, basestring, unicode])
else:
    from collections import Mapping
    dict_type = Mapping

def diff(a, b, path=None):
    path = _make_path(path)
    if type(a) in (list, tuple):
        return _diff_sequences(a, b, path)
    if isinstance(a, dict_type):
        return _diff_dicts(a, b, path)
    if type(a).__name__ == "ObjectId":
        a = str(a)
    if type(b).__name__ == "ObjectId":
        b = str(b)
    if type(a) not in _SUPPORTED_TYPES:
        raise NotImplementedError("Unsupported diff type: {0}".format(type(a))) # pragma: no cover
    if type(b) not in _SUPPORTED_TYPES:
        raise NotImplementedError("Unsupported diff type: {0}".format(type(b))) # pragma: no cover
    if a != b:
        return [(path[:], a, b)]
    return []

def _diff_dicts(a, b, path):
    if type(a) is not type(b):
        return [(path[:], type(a), type(b))]
    returned = []
    for key in set(a) | set(b):
        a_value = a.get(key, NO_VALUE)
        b_value = b.get(key, NO_VALUE)
        path.append(key)
        if a_value is NO_VALUE or b_value is NO_VALUE:
            returned.append((path[:], a_value, b_value))
        else:
            returned.extend(diff(a_value, b_value, path))
        path.pop()
    return returned

def _diff_sequences(a, b, path):
    if len(a) != len(b):
        return [(path[:], a, b)]
    returned = []
    for i in range(len(a)):
        path.append(i)
        returned.extend(diff(a[i], b[i], path))
        path.pop()
    return returned

def _make_path(path):
    if path is None:
        return []
    return path

########NEW FILE########
__FILENAME__ = multicollection
from .diff import diff
import copy
import functools
import re

class MultiCollection(object):
    def __init__(self, conns):
        super(MultiCollection, self).__init__()
        self.conns = conns.copy()
        self.do = Foreach(self.conns, compare=False)
        self.compare = Foreach(self.conns, compare=True)
        self.compare_ignore_order = Foreach(self.conns, compare=True, ignore_order=True)
class Foreach(object):
    def __init__(self, objs, compare, ignore_order=False, method_result_decorators=()):
        self.___objs = objs
        self.___compare = compare
        self.___ignore_order = ignore_order
        self.___decorators = list(method_result_decorators)
    def __getattr__(self, method_name):
        return ForeachMethod(self.___objs, self.___compare, self.___ignore_order, method_name, self.___decorators)
    def __call__(self, *decorators):
        return Foreach(self.___objs, self.___compare, self.___ignore_order, self.___decorators + list(decorators))

class ForeachMethod(object):
    def __init__(self, objs, compare, ignore_order, method_name, decorators):
        super(ForeachMethod, self).__init__()
        self.___objs = objs
        self.___compare = compare
        self.___ignore_order = ignore_order
        self.___method_name = method_name
        self.___decorators = decorators
    def __call__(self, *args, **kwargs):
        results = dict(
            # copying the args and kwargs is important, because pymongo changes the dicts (fits them with the _id)
            (name, self.___apply_decorators(getattr(obj, self.___method_name)(*_deepcopy(args), **_deepcopy(kwargs))))
            for name, obj in self.___objs.items()
        )
        if self.___compare:
            _assert_no_diff(results, ignore_order=self.___ignore_order)
        return results
    def ___apply_decorators(self, obj):
        for d in self.___decorators:
            obj = d(obj)
        return obj

def _assert_no_diff(results, ignore_order):
    if _result_is_cursor(results):
        value_processor = functools.partial(_expand_cursor, sort=ignore_order)
    else:
        assert not ignore_order
        value_processor = None
    prev_name = prev_value = None
    for index, (name, value) in enumerate(results.items()):
        if value_processor is not None:
            value = value_processor(value)
        if index > 0:
            d = diff(prev_value, value)
            assert not d, _format_diff_message(prev_name, name, d)
        prev_name = name
        prev_value = value

def _result_is_cursor(results):
    return any(type(result).__name__ == "Cursor" for result in results.values())

def _expand_cursor(cursor, sort):
    returned = [result.copy() for result in cursor]
    if sort:
        returned.sort(key=lambda document: str(document.get('_id', str(document))))
    for result in returned:
        result.pop("_id", None)
    return returned

def _format_diff_message(a_name, b_name, diff):
    msg = "Unexpected Diff:"
    for (path, a_value, b_value) in diff:
        a_path = [a_name] + path
        b_path = [b_name] + path
        msg += "\n\t{} != {} ({} != {})".format(
            ".".join(map(str, a_path)), ".".join(map(str, b_path)), a_value, b_value
        )
    return msg

def _deepcopy(x):
    """
    Deepcopy, but ignore regex objects...
    """
    if isinstance(x, re._pattern_type):
        return x
    if isinstance(x, list) or isinstance(x, tuple):
        return type(x)(_deepcopy(y) for y in x)
    if isinstance(x, dict):
        return dict((_deepcopy(k), _deepcopy(v)) for k, v in x.items())
    return copy.deepcopy(x)

########NEW FILE########
__FILENAME__ = test__collection_api
import mongomock
from six import text_type

from .utils import TestCase

class CollectionAPITest(TestCase):
    def setUp(self):
        super(CollectionAPITest, self).setUp()
        self.conn = mongomock.Connection()
        self.db = self.conn['somedb']

    def test__get_subcollections(self):
        self.db.a.b
        self.assertEquals(self.db.a.b.full_name, "somedb.a.b")
        self.assertEquals(self.db.a.b.name, "a.b")

        self.assertEquals(
            set(self.db.collection_names()),
            set(["a.b", "system.indexes", "a"]))

    def test__get_collection_full_name(self):
        self.assertEquals(self.db.coll.name, "coll")
        self.assertEquals(self.db.coll.full_name, "somedb.coll")

    def test__get_collection_names(self):
        self.db.a
        self.db.b
        self.assertEquals(set(self.db.collection_names()), set(['a', 'b', 'system.indexes']))
        self.assertEquals(set(self.db.collection_names(True)), set(['a', 'b', 'system.indexes']))
        self.assertEquals(set(self.db.collection_names(False)), set(['a', 'b']))

    def test__cursor_collection(self):
        self.assertIs(self.db.a.find().collection, self.db.a)

    def test__drop_collection(self):
        self.db.a
        self.db.b
        self.db.c
        self.db.drop_collection('b')
        self.db.drop_collection('b')
        self.db.drop_collection(self.db.c)
        self.assertEquals(set(self.db.collection_names()), set(['a', 'system.indexes']))

    def test__distinct_nested_field(self):
        self.db.collection.insert({'f1': {'f2': 'v'}})
        cursor = self.db.collection.find()
        self.assertEquals(cursor.distinct('f1.f2'), ['v'])

    def test__cursor_clone(self):
        self.db.collection.insert([{"a": "b"}, {"b": "c"}, {"c": "d"}])
        cursor1 = self.db.collection.find()
        iterator1 = iter(cursor1)
        first_item = next(iterator1)
        cursor2 = cursor1.clone()
        iterator2 = iter(cursor2)
        self.assertEquals(next(iterator2), first_item)
        for item in iterator1:
            self.assertEquals(item, next(iterator2))

        with self.assertRaises(StopIteration):
            next(iterator2)

    def test__update_retval(self):
        self.db.col.save({"a": 1})
        retval = self.db.col.update({"a": 1}, {"b": 2})
        self.assertIsInstance(retval, dict)
        self.assertIsInstance(retval[text_type("connectionId")], int)
        self.assertIsNone(retval[text_type("err")])
        self.assertEquals(retval[text_type("n")], 1)
        self.assertTrue(retval[text_type("updatedExisting")])
        self.assertEquals(retval["ok"], 1.0)

        self.assertEquals(self.db.col.update({"bla": 1}, {"bla": 2})["n"], 0)

    def test__remove_retval(self):
        self.db.col.save({"a": 1})
        retval = self.db.col.remove({"a": 1})
        self.assertIsInstance(retval, dict)
        self.assertIsInstance(retval[text_type("connectionId")], int)
        self.assertIsNone(retval[text_type("err")])
        self.assertEquals(retval[text_type("n")], 1)
        self.assertEquals(retval[text_type("ok")], 1.0)

        self.assertEquals(self.db.col.remove({"bla": 1})["n"], 0)

    def test__getting_collection_via_getattr(self):
        col1 = self.db.some_collection_here
        col2 = self.db.some_collection_here
        self.assertIs(col1, col2)
        self.assertIs(col1, self.db['some_collection_here'])
        self.assertIsInstance(col1, mongomock.Collection)

    def test__save_class_deriving_from_dict(self):
        # See https://github.com/vmalloc/mongomock/issues/52
        class Document(dict):
            def __init__(self, collection):
                self.collection = collection
                super(Document, self).__init__()
                self.save()

            def save(self):
                self.collection.save(self)

        doc = Document(self.db.collection)
        self.assertIn("_id", doc)
        self.assertNotIn("collection", doc)

    def test__getting_collection_via_getitem(self):
        col1 = self.db['some_collection_here']
        col2 = self.db['some_collection_here']
        self.assertIs(col1, col2)
        self.assertIs(col1, self.db.some_collection_here)
        self.assertIsInstance(col1, mongomock.Collection)

    def test__cannot_save_non_string_keys(self):
        for key in [2, 2.0, True, object()]:
            with self.assertRaises(ValueError):
                self.db.col1.save({key: "value"})

    def test__insert(self):
        self.db.collection.insert({'a': 1})
        self.db.collection.insert([{'a': 2}, {'a': 3}])
        self.db.collection.insert({'a': 4}, safe=True, check_keys=False, continue_on_error=True)

    def test__find_returns_cursors(self):
        collection = self.db.collection
        self.assertEquals(type(collection.find()).__name__, "Cursor")
        self.assertNotIsInstance(collection.find(), list)
        self.assertNotIsInstance(collection.find(), tuple)

    def test__find_slave_okay(self):
        self.db.collection.find({}, slave_okay=True)

    def test__find_and_modify_cannot_remove_and_new(self):
        with self.assertRaises(mongomock.OperationFailure):
            self.db.collection.find_and_modify({}, remove=True, new=True)

    def test__find_and_modify_cannot_remove_and_update(self):
        with self.assertRaises(ValueError): # this is also what pymongo raises
            self.db.collection.find_and_modify({"a": 2}, {"a": 3}, remove=True)

    def test__update_interns_lists_and_dicts(self):
        obj = {}
        obj_id = self.db.collection.save(obj)
        d = {}
        l = []
        self.db.collection.update({"_id": obj_id}, {"d": d, "l": l})
        d["a"] = "b"
        l.append(1)
        self.assertEquals(list(self.db.collection.find()), [{"_id": obj_id, "d": {}, "l": []}])

    def test__string_matching(self):
        """
        Make sure strings are not treated as collections on find
        """
        self.db['abc'].save({'name':'test1'})
        self.db['abc'].save({'name':'test2'})
        #now searching for 'name':'e' returns test1
        self.assertIsNone(self.db['abc'].find_one({'name':'e'}))

    def test__collection_is_indexable(self):
        self.db['def'].save({'name':'test1'})
        self.assertTrue(self.db['def'].find({'name':'test1'}).count() > 0)
        self.assertEquals(self.db['def'].find({'name':'test1'})[0]['name'], 'test1')

    def test__cursor_distinct(self):
        larry_bob = {'name':'larry'}
        larry = {'name':'larry'}
        gary = {'name':'gary'}
        self.db['coll_name'].insert([larry_bob, larry, gary])
        ret_val = self.db['coll_name'].find().distinct('name')
        self.assertTrue(isinstance(ret_val,list))
        self.assertTrue(set(ret_val) == set(['larry','gary']))

    def test__cursor_count_with_limit(self):
        first = {'name':'first'}
        second = {'name':'second'}
        third = {'name':'third'}
        self.db['coll_name'].insert([first, second, third])
        count = self.db['coll_name'].find().limit(2).count(with_limit_and_skip=True)
        self.assertEqual(count, 2)

    def test__cursor_count_with_skip(self):
        first = {'name':'first'}
        second = {'name':'second'}
        third = {'name':'third'}
        self.db['coll_name'].insert([first, second, third])
        count = self.db['coll_name'].find().skip(1).count(with_limit_and_skip=True)
        self.assertEqual(count, 2)

    def test__find_with_skip_param(self):
        """
        Make sure that find() will take in account skip parametter
        """

        u1 = {'name': 'first'}
        u2 = {'name': 'second'}
        self.db['users'].insert([u1, u2])
        self.assertEquals(self.db['users'].find(sort=[("name", 1)], skip=1).count(), 1)
        self.assertEquals(self.db['users'].find(sort=[("name", 1)], skip=1)[0]['name'], 'second')

########NEW FILE########
__FILENAME__ = test__diff
from unittest import TestCase
from .diff import diff

class DiffTest(TestCase):
    def test__assert_no_diff(self):
        for obj in [
                1,
                "string",
                {"complex" : {"object" : {"with" : ["lists"]}}},
        ]:
            self.assertEquals(diff(obj, obj), [])
    def test__diff_values(self):
        self._assert_entire_diff(1, 2)
        self._assert_entire_diff("a", "b")
    def test__diff_sequences(self):
        self._assert_entire_diff([], [1, 2, 3])
    def test__composite_diff(self):
        a = {"a" : {"b" : [1, 2, 3]}}
        b = {"a" : {"b" : [1, 6, 3]}}
        [(path, x, y)] = diff(a, b)
        self.assertEquals(path, ["a", "b", 1])
        self.assertEquals(x, 2)
        self.assertEquals(y, 6)
    def _assert_entire_diff(self, a, b):
        [(path, x, y)] = diff(a, b)
        self.assertEquals(x, a)
        self.assertEquals(y, b)

########NEW FILE########
__FILENAME__ = test__mongomock
import copy
import time
import itertools
import re
import platform
import sys

from .utils import TestCase, skipIf

import mongomock
from mongomock import Database

try:
    import pymongo
    from pymongo import Connection as PymongoConnection
    from pymongo import MongoClient as PymongoClient
    from bson.objectid import ObjectId
    _HAVE_PYMONGO = True
except ImportError:
    from mongomock.object_id import ObjectId
    _HAVE_PYMONGO = False
try:
    import execjs
    from bson.code import Code
    from bson.son import SON
    _HAVE_MAP_REDUCE = True
except ImportError:
    _HAVE_MAP_REDUCE = False
from tests.multicollection import MultiCollection


class InterfaceTest(TestCase):
    def test__can_create_db_without_path(self):
        conn = mongomock.Connection()
        self.assertIsNotNone(conn)
    def test__can_create_db_without_path(self):
        conn = mongomock.Connection('mongodb://localhost')
        self.assertIsNotNone(conn)

class DatabaseGettingTest(TestCase):
    def setUp(self):
        super(DatabaseGettingTest, self).setUp()
        self.conn = mongomock.Connection()
    def test__getting_database_via_getattr(self):
        db1 = self.conn.some_database_here
        db2 = self.conn.some_database_here
        self.assertIs(db1, db2)
        self.assertIs(db1, self.conn['some_database_here'])
        self.assertIsInstance(db1, Database)
        self.assertIs(db1.connection, self.conn) # 'connection' is an attribute of pymongo Database
        self.assertIs(db2.connection, self.conn)
    def test__getting_database_via_getitem(self):
        db1 = self.conn['some_database_here']
        db2 = self.conn['some_database_here']
        self.assertIs(db1, db2)
        self.assertIs(db1, self.conn.some_database_here)
        self.assertIsInstance(db1, Database)


@skipIf(not _HAVE_PYMONGO,"pymongo not installed")
class _CollectionComparisonTest(TestCase):
    """Compares a fake collection with the real mongo collection implementation via cross-comparison."""

    def setUp(self):
        super(_CollectionComparisonTest, self).setUp()
        self.fake_conn = self._get_mongomock_connection_class()()
        self.mongo_conn = self._connect_to_local_mongodb()
        self.db_name = "mongomock___testing_db"
        self.collection_name = "mongomock___testing_collection"
        self.mongo_conn[self.db_name][self.collection_name].remove()
        self.cmp = MultiCollection({
            "fake" : self.fake_conn[self.db_name][self.collection_name],
            "real": self.mongo_conn[self.db_name][self.collection_name],
         })

    def _connect_to_local_mongodb(self, num_retries=60):
        "Performs retries on connection refused errors (for travis-ci builds)"
        connection_class = self._get_real_connection_class()
        for retry in range(num_retries):
            if retry > 0:
                time.sleep(0.5)
            try:
                return connection_class()
            except pymongo.errors.ConnectionFailure as e:
                if retry == num_retries - 1:
                    raise
                if "connection refused" not in e.message.lower():
                    raise

class _MongoClientMixin(object):

    def _get_real_connection_class(self):
        return PymongoClient

    def _get_mongomock_connection_class(self):
        return mongomock.MongoClient

class _PymongoConnectionMixin(object):

    def _get_real_connection_class(self):
        return PymongoConnection

    def _get_mongomock_connection_class(self):
        return mongomock.Connection

class _CollectionTest(_CollectionComparisonTest):

    def test__find_is_empty(self):
        self.cmp.do.remove()
        self.cmp.compare.find()

    def test__inserting(self):
        self.cmp.do.remove()
        data = {"a" : 1, "b" : 2, "c" : "data"}
        self.cmp.do.insert(data)
        self.cmp.compare.find() # single document, no need to ignore order

    def test__bulk_insert(self):
        objs = [{"a" : 2, "b" : {"c" : 3}}, {"c" : 5}, {"d" : 7}]
        results_dict = self.cmp.do.insert(objs)
        for results in results_dict.values():
            self.assertEquals(len(results), len(objs))
            self.assertEquals(len(set(results)), len(results), "Returned object ids not unique!")
        self.cmp.compare_ignore_order.find()

    def test__save(self):
        self.cmp.do.insert({"_id" : "b"}) #add an item with a non ObjectId _id first.
        self.cmp.do.save({"_id":ObjectId(), "someProp":1}, safe=True)
        self.cmp.compare_ignore_order.find()

    def test__count(self):
        self.cmp.compare.count()
        self.cmp.do.insert({"a" : 1})
        self.cmp.compare.count()

    def test__find_one(self):
        id1 = self.cmp.do.insert({"_id":"id1", "name" : "new"})
        self.cmp.compare.find_one({"_id" : "id1"})
        self.cmp.do.insert({"_id":"id2", "name" : "another new"})
        self.cmp.compare.find_one({"_id" : "id2"}, {"_id":1})
        self.cmp.compare.find_one("id2", {"_id":1})

    def test__find_one_no_args(self):
        self.cmp.do.insert({"_id": "new_obj", "field": "value"})
        self.cmp.compare.find_one()

    def test__find_by_attributes(self):
        id1 = ObjectId()
        self.cmp.do.insert({"_id":id1, "name" : "new"})
        self.cmp.do.insert({"name" : "another new"})
        self.cmp.compare_ignore_order.find()
        self.cmp.compare.find({"_id" : id1})

    def test__find_by_attributes_return_fields(self):
        id1 = ObjectId()
        id2 = ObjectId()
        self.cmp.do.insert({"_id":id1, "name" : "new", "someOtherProp":2})
        self.cmp.do.insert({"_id":id2, "name" : "another new"})

        self.cmp.compare_ignore_order.find({},{"_id":0}) #test exclusion of _id
        self.cmp.compare_ignore_order.find({},{"_id":1,"someOtherProp":1}) #test inclusion
        self.cmp.compare_ignore_order.find({},{"_id":0,"someOtherProp":0}) #test exclusion
        self.cmp.compare_ignore_order.find({},{"_id":0,"someOtherProp":1}) #test mixed _id:0
        self.cmp.compare_ignore_order.find({},{"someOtherProp":0}) #test no _id, otherProp:0
        self.cmp.compare_ignore_order.find({},{"someOtherProp":1}) #test no _id, otherProp:1

        self.cmp.compare.find({"_id" : id1},{"_id":0}) #test exclusion of _id
        self.cmp.compare.find({"_id" : id1},{"_id":1,"someOtherProp":1}) #test inclusion
        self.cmp.compare.find({"_id" : id1},{"_id":0,"someOtherProp":0}) #test exclusion
        self.cmp.compare.find({"_id" : id1},{"_id":0,"someOtherProp":1}) #test mixed _id:0
        self.cmp.compare.find({"_id" : id1},{"someOtherProp":0}) #test no _id, otherProp:0
        self.cmp.compare.find({"_id" : id1},{"someOtherProp":1}) #test no _id, otherProp:1

    def test__find_by_dotted_attributes(self):
        """Test seaching with dot notation."""
        green_bowler = {
                'name': 'bob',
                'hat': {
                    'color': 'green',
                    'type': 'bowler'}}
        red_bowler = {
                'name': 'sam',
                'hat': {
                    'color': 'red',
                    'type': 'bowler'}}
        self.cmp.do.insert(green_bowler)
        self.cmp.do.insert(red_bowler)
        self.cmp.compare_ignore_order.find()
        self.cmp.compare_ignore_order.find({"name" : "sam"})
        self.cmp.compare_ignore_order.find({'hat.color': 'green'})
        self.cmp.compare_ignore_order.find({'hat.type': 'bowler'})
        self.cmp.compare.find({
            'hat.color': 'red',
            'hat.type': 'bowler'
        })
        self.cmp.compare.find({
            'name': 'bob',
            'hat.color': 'red',
            'hat.type': 'bowler'
        })
        self.cmp.compare.find({'hat': 'a hat'})
        self.cmp.compare.find({'hat.color.cat': 'red'})

    def test__find_empty_array_field(self):
        #See #90
        self.cmp.do.insert({'array_field' : []})
        self.cmp.compare.find({'array_field' : []})

    def test__find_non_empty_array_field(self):
        #See #90
        self.cmp.do.insert({'array_field' : [['abc']]})
        self.cmp.do.insert({'array_field' : ['def']})
        self.cmp.compare.find({'array_field' : ['abc']})
        self.cmp.compare.find({'array_field' : [['abc']]})
        self.cmp.compare.find({'array_field' : 'def'})		
        self.cmp.compare.find({'array_field' : ['def']})
		
    def test__find_by_objectid_in_list(self):
        #See #79
        self.cmp.do.insert({'_id': 'x', 'rel_id' : [ObjectId('52d669dcad547f059424f783')]})
        self.cmp.compare.find({'rel_id':ObjectId('52d669dcad547f059424f783')})

    def test__find_subselect_in_list(self):
        #See #78
        self.cmp.do.insert({'_id': 'some_id', 'a': [ {'b': 1, 'c': 2} ]})
        self.cmp.compare.find_one({'a.b': 1})

    def test__find_by_regex_object(self):
        """Test searching with regular expression objects."""
        bob = {'name': 'bob'}
        sam = {'name': 'sam'}
        self.cmp.do.insert(bob)
        self.cmp.do.insert(sam)
        self.cmp.compare_ignore_order.find()
        regex = re.compile('bob|sam')
        self.cmp.compare_ignore_order.find({"name" : regex})
        regex = re.compile('bob|notsam')
        self.cmp.compare_ignore_order.find({"name" : regex})

    def test__find_by_regex_string(self):
        """Test searching with regular expression string."""
        bob = {'name': 'bob'}
        sam = {'name': 'sam'}
        self.cmp.do.insert(bob)
        self.cmp.do.insert(sam)
        self.cmp.compare_ignore_order.find()
        self.cmp.compare_ignore_order.find({"name": {'$regex': 'bob|sam'}})
        self.cmp.compare_ignore_order.find({'name': {'$regex': 'bob|notsam'}})

    def test__find_in_array_by_regex_object(self):
        """Test searching inside array with regular expression object."""
        bob = {'name': 'bob', 'text': ['abcd', 'cde']}
        sam = {'name': 'sam', 'text': ['bde']}
        self.cmp.do.insert(bob)
        self.cmp.do.insert(sam)
        regex = re.compile('^a')
        self.cmp.compare_ignore_order.find({"text": regex})
        regex = re.compile('e$')
        self.cmp.compare_ignore_order.find({"text": regex})
        regex = re.compile('bde|cde')
        self.cmp.compare_ignore_order.find({"text": regex})

    def test__find_in_array_by_regex_string(self):
        """Test searching inside array with regular expression string"""
        bob = {'name': 'bob', 'text': ['abcd', 'cde']}
        sam = {'name': 'sam', 'text': ['bde']}
        self.cmp.do.insert(bob)
        self.cmp.do.insert(sam)
        self.cmp.compare_ignore_order.find({"text": {'$regex': '^a'}})
        self.cmp.compare_ignore_order.find({"text": {'$regex': 'e$'}})
        self.cmp.compare_ignore_order.find({"text": {'$regex': 'bcd|cde'}})

    def test__find_by_regex_string_on_absent_field_dont_break(self):
        """Test searching on absent field with regular expression string dont break"""
        bob = {'name': 'bob'}
        sam = {'name': 'sam'}
        self.cmp.do.insert(bob)
        self.cmp.do.insert(sam)
        self.cmp.compare_ignore_order.find({"text": {'$regex': 'bob|sam'}})

    def test__find_by_elemMatch(self):
        self.cmp.do.insert({"field": [{"a": 1, "b": 2}, {"c": 3, "d": 4}]})
        self.cmp.do.insert({"field": [{"a": 1, "b": 4}, {"c": 3, "d": 8}]})
        self.cmp.do.insert({"field": "nonlist"})
        self.cmp.do.insert({"field": 2})

        self.cmp.compare.find({"field": {"$elemMatch": {"b": 1}}})
        self.cmp.compare_ignore_order.find({"field": {"$elemMatch": {"a": 1}}})
        self.cmp.compare.find({"field": {"$elemMatch": {"b": {"$gt": 3}}}})

    def test__find_in_array(self):
        self.cmp.do.insert({"field": [{"a": 1, "b": 2}, {"c": 3, "d": 4}]})

        self.cmp.compare.find({"field.0.a": 1})
        self.cmp.compare.find({"field.0.b": 2})
        self.cmp.compare.find({"field.1.c": 3})
        self.cmp.compare.find({"field.1.d": 4})

    def test__find_notequal(self):
        """Test searching with operators other than equality."""
        bob = {'_id': 1, 'name': 'bob'}
        sam = {'_id': 2, 'name': 'sam'}
        a_goat = {'_id': 3, 'goatness': 'very'}
        self.cmp.do.insert([bob, sam, a_goat])
        self.cmp.compare_ignore_order.find()
        self.cmp.compare_ignore_order.find({'name': {'$ne': 'bob'}})
        self.cmp.compare_ignore_order.find({'goatness': {'$ne': 'very'}})
        self.cmp.compare_ignore_order.find({'goatness': {'$ne': 'not very'}})
        self.cmp.compare_ignore_order.find({'snakeness': {'$ne': 'very'}})

    def test__find_notequal(self):
        """Test searching for None."""
        bob =       {'_id': 1, 'name': 'bob',       'sheepness':{'sometimes':True}}
        sam =       {'_id': 2, 'name': 'sam',       'sheepness':{'sometimes':True}}
        a_goat =    {'_id': 3, 'goatness': 'very',  'sheepness':{}}
        self.cmp.do.insert([bob, sam, a_goat])
        self.cmp.compare_ignore_order.find({'goatness': None})
        self.cmp.compare_ignore_order.find({'sheepness.sometimes': None})


    def test__find_not(self):
        bob = {'_id': 1, 'name': 'bob'}
        sam = {'_id': 2, 'name': 'sam'}
        self.cmp.do.insert([bob, sam])
        self.cmp.compare_ignore_order.find()
        self.cmp.compare_ignore_order.find({'name': {'$not': {'$ne': 'bob'}}})
        self.cmp.compare_ignore_order.find({'name': {'$not': {'$ne': 'sam'}}})
        self.cmp.compare_ignore_order.find({'name': {'$not': {'$ne': 'dan'}}})

    def test__find_compare(self):
        self.cmp.do.insert(dict(noise = "longhorn"))
        for x in range(10):
            self.cmp.do.insert(dict(num = x, sqrd = x * x))
        self.cmp.compare_ignore_order.find({'sqrd':{'$lte':4}})
        self.cmp.compare_ignore_order.find({'sqrd':{'$lt':4}})
        self.cmp.compare_ignore_order.find({'sqrd':{'$gte':64}})
        self.cmp.compare_ignore_order.find({'sqrd':{'$gte':25, '$lte':36}})

    def test__find_sets(self):
        single = 4
        even = [2, 4, 6, 8]
        prime = [2, 3, 5, 7]
        self.cmp.do.insert([
            dict(x = single),
            dict(x = even),
            dict(x = prime)])
        self.cmp.compare_ignore_order.find({'x':{'$in':[7, 8]}})
        self.cmp.compare_ignore_order.find({'x':{'$in':[4, 5]}})
        self.cmp.compare_ignore_order.find({'x':{'$nin':[2, 5]}})
        self.cmp.compare_ignore_order.find({'x':{'$all':[2, 5]}})
        self.cmp.compare_ignore_order.find({'x':{'$all':[7, 8]}})
        self.cmp.compare_ignore_order.find({'x':2})
        self.cmp.compare_ignore_order.find({'x':4})
        self.cmp.compare_ignore_order.find({'$or':[{'x':4}, {'x':2}]})
        self.cmp.compare_ignore_order.find({'$or':[{'x':4}, {'x':7}]})
        self.cmp.compare_ignore_order.find({'$and':[{'x':2}, {'x':7}]})

    def test__find_and_modify_remove(self):
        self.cmp.do.insert([{"a": x} for x in range(10)])
        self.cmp.do.find_and_modify({"a": 2}, remove=True)
        self.cmp.compare_ignore_order.find()

    def test__find_sort_list(self):
        self.cmp.do.remove()
        for data in ({"a" : 1, "b" : 3, "c" : "data1"},
                     {"a" : 2, "b" : 2, "c" : "data3"},
                     {"a" : 3, "b" : 1, "c" : "data2"}):
            self.cmp.do.insert(data)
        self.cmp.compare.find(sort = [("a", 1), ("b", -1)])
        self.cmp.compare.find(sort = [("b", 1), ("a", -1)])
        self.cmp.compare.find(sort = [("b", 1), ("a", -1), ("c", 1)])

    def test__find_sort_list_nested_doc(self):
        self.cmp.do.remove()
        for data in ({"root": {"a" : 1, "b" : 3, "c" : "data1"}},
                     {"root": {"a" : 2, "b" : 2, "c" : "data3"}},
                     {"root": {"a" : 3, "b" : 1, "c" : "data2"}}):
            self.cmp.do.insert(data)
        self.cmp.compare.find(sort = [("root.a", 1), ("root.b", -1)])
        self.cmp.compare.find(sort = [("root.b", 1), ("root.a", -1)])
        self.cmp.compare.find(sort = [("root.b", 1), ("root.a", -1), ("root.c", 1)])

    def test__find_sort_list_nested_list(self):
        self.cmp.do.remove()
        for data in ({"root": [{"a" : 1, "b" : 3, "c" : "data1"}]},
                     {"root": [{"a" : 2, "b" : 2, "c" : "data3"}]},
                     {"root": [{"a" : 3, "b" : 1, "c" : "data2"}]}):
            self.cmp.do.insert(data)
        self.cmp.compare.find(sort = [("root.0.a", 1), ("root.0.b", -1)])
        self.cmp.compare.find(sort = [("root.0.b", 1), ("root.0.a", -1)])
        self.cmp.compare.find(sort = [("root.0.b", 1), ("root.0.a", -1), ("root.0.c", 1)])

    def test__find_limit(self):
        self.cmp.do.remove()
        for data in ({"a" : 1, "b" : 3, "c" : "data1"},
                     {"a" : 2, "b" : 2, "c" : "data3"},
                     {"a" : 3, "b" : 1, "c" : "data2"}):
            self.cmp.do.insert(data)
        self.cmp.compare.find(limit=2, sort = [("a", 1), ("b", -1)])
        self.cmp.compare.find(limit=0, sort = [("a", 1), ("b", -1)]) #pymongo limit defaults to 0, returning everything

    def test__as_class(self):
        class MyDict(dict): pass

        self.cmp.do.remove()
        self.cmp.do.insert({"a": 1, "b": {"ba": 3, "bb": 4, "bc": [ {"bca": 5 } ] }})
        self.cmp.compare.find({}, as_class=MyDict)
        self.cmp.compare.find({"a": 1}, as_class=MyDict)

    def test__return_only_selected_fields(self):
        self.cmp.do.insert({'name':'Chucky', 'type':'doll', 'model':'v6'})
        self.cmp.compare_ignore_order.find({'name':'Chucky'}, fields = ['type'])

    def test__default_fields_to_id_if_empty(self):
        self.cmp.do.insert({'name':'Chucky', 'type':'doll', 'model':'v6'})
        self.cmp.compare_ignore_order.find({'name':'Chucky'}, fields = [])

    def test__remove(self):
        """Test the remove method."""
        self.cmp.do.insert({"value" : 1})
        self.cmp.compare_ignore_order.find()
        self.cmp.do.remove()
        self.cmp.compare.find()
        self.cmp.do.insert([
            {'name': 'bob'},
            {'name': 'sam'},
        ])
        self.cmp.compare_ignore_order.find()
        self.cmp.do.remove({'name': 'bob'})
        self.cmp.compare_ignore_order.find()
        self.cmp.do.remove({'name': 'notsam'})
        self.cmp.compare.find()
        self.cmp.do.remove({'name': 'sam'})
        self.cmp.compare.find()

    def test__update(self):
        doc = {"a" : 1}
        self.cmp.do.insert(doc)
        new_document = {"new_attr" : 2}
        self.cmp.do.update({"a" : 1}, new_document)
        self.cmp.compare_ignore_order.find()

    def test__set(self):
        """Tests calling update with $set members."""
        self.cmp.do.update({'_id':42}, {'$set': {'some': 'thing'}}, upsert=True)
        self.cmp.compare.find({'_id' : 42})
        self.cmp.do.insert({'name': 'bob'})
        self.cmp.do.update({'name': 'bob'}, {'$set': {'hat': 'green'}})
        self.cmp.compare.find({'name' : 'bob'})
        self.cmp.do.update({'name': 'bob'}, {'$set': {'hat': 'red'}})
        self.cmp.compare.find({'name': 'bob'})

    def test__unset(self):
        """Tests calling update with $set members."""
        self.cmp.do.update({'name': 'bob'}, {'a': 'aaa'}, upsert=True)
        self.cmp.compare.find({'name' : 'bob'})
        self.cmp.do.update({'name': 'bob'}, {'$unset': {'a': 0}})
        self.cmp.compare.find({'name' : 'bob'})

        self.cmp.do.update({'name': 'bob'}, {'a': 'aaa'}, upsert=True)
        self.cmp.compare.find({'name' : 'bob'})
        self.cmp.do.update({'name': 'bob'}, {'$unset': {'a': 1}})
        self.cmp.compare.find({'name' : 'bob'})

        self.cmp.do.update({'name': 'bob'}, {'a': 'aaa'}, upsert=True)
        self.cmp.compare.find({'name' : 'bob'})
        self.cmp.do.update({'name': 'bob'}, {'$unset': {'a': ""}})
        self.cmp.compare.find({'name' : 'bob'})

        self.cmp.do.update({'name': 'bob'}, {'a': 'aaa'}, upsert=True)
        self.cmp.compare.find({'name' : 'bob'})
        self.cmp.do.update({'name': 'bob'}, {'$unset': {'a': True}})
        self.cmp.compare.find({'name' : 'bob'})

        self.cmp.do.update({'name': 'bob'}, {'a': 'aaa'}, upsert=True)
        self.cmp.compare.find({'name' : 'bob'})
        self.cmp.do.update({'name': 'bob'}, {'$unset': {'a': False}})
        self.cmp.compare.find({'name' : 'bob'})

    def test__set_upsert(self):
        self.cmp.do.remove()
        self.cmp.do.update({"name": "bob"}, {"$set": {}}, True)
        self.cmp.compare.find()
        self.cmp.do.update({"name": "alice"}, {"$set": {"age": 1}}, True)
        self.cmp.compare_ignore_order.find()

    def test__set_subdocuments(self):
        """Tests using $set for setting subdocument fields"""
        if isinstance(self, _MongoClientMixin):
            self.skipTest("MongoClient does not allow setting subdocuments on existing non-documents")
        self.cmp.do.insert({'name': 'bob', 'data1': 1, 'subdocument': {'a': {'b': {'c': 20}}}})
        self.cmp.do.update({'name': 'bob'}, {'$set': {'data1.field1': 11}})
        self.cmp.compare.find()
        self.cmp.do.update({'name': 'bob'}, {'$set': {'data2.field1': 21}})
        self.cmp.compare.find()
        self.cmp.do.update({'name': 'bob'}, {'$set': {'subdocument.a.b': 21}})
        self.cmp.compare.find()

    def test__inc(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob'})
        for i in range(3):
            self.cmp.do.update({'name':'bob'}, {'$inc': {'count':1}})
            self.cmp.compare.find({'name': 'bob'})

    def test__inc_upsert(self):
        self.cmp.do.remove()
        for i in range(3):
            self.cmp.do.update({'name':'bob'}, {'$inc': {'count':1}}, True)
            self.cmp.compare.find({'name': 'bob'})

    def test__inc_subdocument(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'data': {'age': 0}})
        self.cmp.do.update({'name':'bob'}, {'$inc': {'data.age': 1}})
        self.cmp.compare.find()
        self.cmp.do.update({'name':'bob'}, {'$inc': {'data.age2': 1}})
        self.cmp.compare.find()

    def test__inc_subdocument_positional(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'data': [{'age': 0}, {'age': 1}]})
        self.cmp.do.update({'name': 'bob', 'data': {'$elemMatch': {'age': 0}}},
            {'$inc': {'data.$.age': 1}})
        self.cmp.compare.find()

    def test__addToSet(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob'})
        for i in range(3):
            self.cmp.do.update({'name':'bob'}, {'$addToSet': {'hat':'green'}})
            self.cmp.compare.find({'name': 'bob'})
        for i in range(3):
            self.cmp.do.update({'name': 'bob'}, {'$addToSet': {'hat':'tall'}})
            self.cmp.compare.find({'name': 'bob'})

    def test__pull(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'hat': ['green', 'tall']})
        self.cmp.do.update({'name': 'bob'}, {'$pull': {'hat': 'green'}})
        self.cmp.compare.find({'name': 'bob'})

    def test__pull_nested_dict(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'hat': [{'name': 'derby', 'sizes': [{'size': 'L', 'quantity': 3}, {'size': 'XL', 'quantity': 4}], 'colors': ['green', 'blue']}, {'name': 'cap', 'sizes': [{'size': 'S', 'quantity': 10}, {'size': 'L', 'quantity': 5}], 'colors': ['blue']}]})
        self.cmp.do.update({'hat': {'$elemMatch': {'name': 'derby'}}}, {'$pull': {'hat.$.sizes': {'size': 'L'}}})
        self.cmp.compare.find({'name': 'bob'})

    def test__pull_nested_list(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'hat': [{'name': 'derby', 'sizes': ['L', 'XL']}, {'name': 'cap', 'sizes': ['S', 'L']}]})
        self.cmp.do.update({'hat': {'$elemMatch': {'name': 'derby'}}}, {'$pull': {'hat.$.sizes': 'XL'}})
        self.cmp.compare.find({'name': 'bob'})

    def test__push(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'hat': ['green', 'tall']})
        self.cmp.do.update({'name': 'bob'}, {'$push': {'hat': 'wide'}})
        self.cmp.compare.find({'name': 'bob'})

    def test__push_dict(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'hat': [{'name': 'derby', 'sizes': ['L', 'XL']}]})
        self.cmp.do.update({'name': 'bob'}, {'$push': {'hat': {'name': 'cap', 'sizes': ['S', 'L']}}})
        self.cmp.compare.find({'name': 'bob'})

    def test__push_each(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'hat': ['green', 'tall']})
        self.cmp.do.update({'name': 'bob'}, {'$push': {'hat': {'$each': ['wide', 'blue']}}})
        self.cmp.compare.find({'name': 'bob'})

    def test__push_nested_dict(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'hat': [{'name': 'derby', 'sizes': [{'size': 'L', 'quantity': 3}, {'size': 'XL', 'quantity': 4}], 'colors': ['green', 'blue']}, {'name': 'cap', 'sizes': [{'size': 'S', 'quantity': 10}, {'size': 'L', 'quantity': 5}], 'colors': ['blue']}]})
        self.cmp.do.update({'hat': {'$elemMatch': {'name': 'derby'}}}, {'$push': {'hat.$.sizes': {'size': 'M', 'quantity': 6}}})
        self.cmp.compare.find({'name': 'bob'})

    def test__push_nested_dict_each(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'hat': [{'name': 'derby', 'sizes': [{'size': 'L', 'quantity': 3}, {'size': 'XL', 'quantity': 4}], 'colors': ['green', 'blue']}, {'name': 'cap', 'sizes': [{'size': 'S', 'quantity': 10}, {'size': 'L', 'quantity': 5}], 'colors': ['blue']}]})
        self.cmp.do.update({'hat': {'$elemMatch': {'name': 'derby'}}}, {'$push': {'hat.$.sizes': {'$each': [{'size': 'M', 'quantity': 6}, {'size': 'S', 'quantity': 1}]}}})
        self.cmp.compare.find({'name': 'bob'})

    def test__push_nested_list_each(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob', 'hat': [{'name': 'derby', 'sizes': ['L', 'XL'], 'colors': ['green', 'blue']}, {'name': 'cap', 'sizes': ['S', 'L'], 'colors': ['blue']}]})
        self.cmp.do.update({'hat': {'$elemMatch': {'name': 'derby'}}}, {'$push': {'hat.$.sizes': {'$each': ['M', 'S']}}})
        self.cmp.compare.find({'name': 'bob'})

    def test__push_to_absent_field(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob'})
        self.cmp.do.update({'name': 'bob'}, {'$push': {'hat': 'wide'}})
        self.cmp.compare.find({'name': 'bob'})

    def test__push_each_to_absent_field(self):
        self.cmp.do.remove()
        self.cmp.do.insert({'name': 'bob'})
        self.cmp.do.update({'name': 'bob'}, {'$push': {'hat': {'$each': ['wide', 'blue']}}})
        self.cmp.compare.find({'name': 'bob'})

    def test__drop(self):
        self.cmp.do.insert({"name" : "another new"})
        self.cmp.do.drop()
        self.cmp.compare.find({})

    def test__ensure_index(self):
        # Does nothing - just make sure it exists and takes the right args
        self.cmp.do.ensure_index("name")
        self.cmp.do.ensure_index("hat", cache_for = 100)
        self.cmp.do.ensure_index([("name", 1), ("hat", -1)])

class MongoClientCollectionTest(_CollectionTest, _MongoClientMixin):
    pass

class PymongoCollectionTest(_CollectionTest, _PymongoConnectionMixin):
    pass

@skipIf(not _HAVE_PYMONGO,"pymongo not installed")
@skipIf(not _HAVE_MAP_REDUCE,"execjs not installed")
class CollectionMapReduceTest(TestCase):
    def setUp(self):
        self.db = mongomock.Connection().map_reduce_test
        self.data = [{"x": 1, "tags": ["dog", "cat"]},
                     {"x": 2, "tags": ["cat"]},
                     {"x": 3, "tags": ["mouse", "cat", "dog"]},
                     {"x": 4, "tags": []}]
        for item in self.data:
            self.db.things.insert(item)
        self.map_func = Code("""
                function() {
                    this.tags.forEach(function(z) {
                        emit(z, 1);
                    });
                }""")
        self.reduce_func = Code("""
                function(key, values) {
                    var total = 0;
                    for(var i = 0; i<values.length; i++) {
                        total += values[i];
                    }
                    return total;
                }""")
        self.expected_results = [{'_id': 'mouse', 'value': 1},
                                 {'_id': 'dog', 'value': 2},
                                 {'_id': 'cat', 'value': 3}]
								 
    def test__map_reduce(self):
        self._check_map_reduce(self.db.things, self.expected_results)

    def test__map_reduce_clean_res_colc(self):
		#Checks that the result collection is cleaned between calls
		
        self._check_map_reduce(self.db.things, self.expected_results)

        more_data = [{"x": 1, "tags": []},
                     {"x": 2, "tags": []},
                     {"x": 3, "tags": []},
                     {"x": 4, "tags": []}]			
        for item in more_data:
            self.db.more_things.insert(item)
        expected_results = []

        self._check_map_reduce(self.db.more_things, expected_results)
								 
    def _check_map_reduce(self, colc, expected_results):
        result = colc.map_reduce(self.map_func, self.reduce_func, 'myresults')
        self.assertTrue(isinstance(result, mongomock.Collection))
        self.assertEqual(result.name, 'myresults')
        self.assertEqual(result.count(), len(expected_results))
        for doc in result.find():
            self.assertIn(doc, expected_results)
	
    def test__map_reduce_son(self):
        result = self.db.things.map_reduce(self.map_func, self.reduce_func, out=SON([('replace', 'results'), ('db', 'map_reduce_son_test')]))
        self.assertTrue(isinstance(result, mongomock.Collection))
        self.assertEqual(result.name, 'results')
        self.assertEqual(result._Collection__database.name, 'map_reduce_son_test')
        self.assertEqual(result.count(), 3)
        for doc in result.find():
            self.assertIn(doc, self.expected_results)

    def test__map_reduce_full_response(self):
        expected_full_response = {'counts': {'input': 4, 'reduce': 2, 'emit': 6, 'output': 3}, 'timeMillis': 5, 'ok': 1.0, 'result': 'myresults'}
        result = self.db.things.map_reduce(self.map_func, self.reduce_func, 'myresults', full_response=True)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result['counts'], expected_full_response['counts'])
        self.assertEqual(result['result'], expected_full_response['result'])
        for doc in getattr(self.db, result['result']).find():
            self.assertIn(doc, self.expected_results)

    def test__map_reduce_with_query(self):
        expected_results = [{'_id': 'mouse', 'value': 1},
                            {'_id': 'dog', 'value': 2},
                            {'_id': 'cat', 'value': 2}]
        result = self.db.things.map_reduce(self.map_func, self.reduce_func, 'myresults', query={'tags': 'dog'})
        self.assertTrue(isinstance(result, mongomock.Collection))
        self.assertEqual(result.name, 'myresults')
        self.assertEqual(result.count(), 3)
        for doc in result.find():
            self.assertIn(doc, expected_results)

    def test__map_reduce_with_limit(self):
        result = self.db.things.map_reduce(self.map_func, self.reduce_func, 'myresults', limit=2)
        self.assertTrue(isinstance(result, mongomock.Collection))
        self.assertEqual(result.name, 'myresults')
        self.assertEqual(result.count(), 2)

    def test__inline_map_reduce(self):
        result = self.db.things.inline_map_reduce(self.map_func, self.reduce_func)
        self.assertTrue(isinstance(result, list))
        self.assertEqual(len(result), 3)
        for doc in result:
            self.assertIn(doc, self.expected_results)

    def test__inline_map_reduce_full_response(self):
        expected_full_response = {'counts': {'input': 4, 'reduce': 2, 'emit': 6, 'output': 3}, 'timeMillis': 5, 'ok': 1.0, 'result': [{'_id': 'cat', 'value': 3}, {'_id': 'dog', 'value': 2}, {'_id': 'mouse', 'value': 1}]}
        result = self.db.things.inline_map_reduce(self.map_func, self.reduce_func, full_response=True)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(result['counts'], expected_full_response['counts'])
        for doc in result['result']:
            self.assertIn(doc, self.expected_results)

    def test__map_reduce_with_object_id(self):
        obj1 = ObjectId()
        obj2 = ObjectId()
        data = [{"x": 1, "tags": [obj1, obj2]},
                {"x": 2, "tags": [obj1]}]			
        for item in data:
            self.db.things_with_obj.insert(item)
        expected_results = [{'_id': obj1, 'value': 2},
                            {'_id': obj2, 'value': 1}]
        result = self.db.things_with_obj.map_reduce(self.map_func, self.reduce_func, 'myresults')
        self.assertTrue(isinstance(result, mongomock.Collection))
        self.assertEqual(result.name, 'myresults')
        self.assertEqual(result.count(), 2)
        for doc in result.find():
            self.assertIn(doc, expected_results)			

@skipIf(not _HAVE_PYMONGO,"pymongo not installed")
@skipIf(not _HAVE_MAP_REDUCE,"execjs not installed")
class _GroupTest(_CollectionComparisonTest):
    def setUp(self):
        _CollectionComparisonTest.setUp(self)
        self._id1 = ObjectId()
        self.data = [
                         {"a": 1, "count": 4 },
                         {"a": 1, "count": 2 },
                         {"a": 1, "count": 4 },
                         {"a": 2, "count": 3 },
                         {"a": 2, "count": 1 },
                         {"a": 1, "count": 5 },
                         {"a": 4, "count": 4 },
                         {"b": 4, "foo": 4 },
                         {"b": 2, "foo": 3, "name":"theone" },
                         {"b": 1, "foo": 2 },
                         {"b": 1, "foo": self._id1 },
                     ]
        for item in self.data:
            self.cmp.do.insert(item)
        

    def test__group1(self):
        key = ["a"]
        initial = {"count":0}
        condition = {"a": {"$lt": 3}}
        reduce_func = Code("""
                function(cur, result) { result.count += cur.count }
                """)
        self.cmp.compare.group(key, condition, initial, reduce_func)


    def test__group2(self):
        reduce_func = Code("""
                function(cur, result) { result.count += 1 }
                """)
        self.cmp.compare.group(  key = ["b"], 
                                        condition = {"foo":{"$in":[3,4]}, "name":"theone"},
                                        initial = {"count": 0}, 
                                        reduce = reduce_func,
                                    )

    def test__group3(self):
        reducer=Code("""
            function(obj, result) {result.count+=1 }
            """)
        conditions = {
                    'foo':{'$in':[self._id1]},
                    }
        self.cmp.compare.group(key=['foo'], 
                               condition=conditions, 
                               initial={"count": 0}, 
                               reduce=reducer)


class MongoClientGroupTest(_GroupTest, _MongoClientMixin):
    pass

class PymongoGroupTest(_GroupTest, _PymongoConnectionMixin):
    pass

@skipIf(not _HAVE_PYMONGO,"pymongo not installed")
@skipIf(not _HAVE_MAP_REDUCE,"execjs not installed")
class _AggregateTest(_CollectionComparisonTest):
    def setUp(self):
        _CollectionComparisonTest.setUp(self)
        self.data = [{"_id":ObjectId(), "a": 1, "count": 4 },
                     {"_id":ObjectId(), "a": 1, "count": 2 },
                     {"_id":ObjectId(), "a": 1, "count": 4 },
                     {"_id":ObjectId(), "a": 2, "count": 3 },
                     {"_id":ObjectId(), "a": 2, "count": 1 },
                     {"_id":ObjectId(), "a": 1, "count": 5 },
                     {"_id":ObjectId(), "a": 4, "count": 4 }]
        for item in self.data:
            self.cmp.do.insert(item)
        
        #self.expected_results = [{"a": 1, "count": 15}]

    def test__aggregate1(self):
        pipeline = [
                        {
                            '$match': {'a':{'$lt':3}}
                        },
                        {
                            '$sort':{'_id':-1}
                        },
                    ]
        self.cmp.compare.aggregate(pipeline)
    
    def test__aggregate2(self):
        pipeline = [
                        {
                            '$group': {
                                        '_id': '$a',
                                        'count': {'$sum': '$count'}
                                    }
                        },
                        {
                            '$match': {'a':{'$lt':3}}
                        },
                        {
                            '$sort': {'_id': -1, 'count': 1}
                        },
                    ]
        self.cmp.compare.aggregate(pipeline)

    def test__aggregate3(self):
        pipeline = [{'$group': {'_id': 'a',
                                     'count': {'$sum': '$count'}}},
                         {'$match': {'a':{'$lt':3}}},
                         {'$sort': {'_id': -1, 'count': 1}},
                         {'$skip': 1},
                         {'$limit': 2}]
        self.cmp.compare.aggregate(pipeline)



class MongoClientAggregateTest(_AggregateTest, _MongoClientMixin):
    pass

class PymongoAggregateTest(_AggregateTest, _PymongoConnectionMixin):
    pass


def _LIMIT(*args):
    return lambda cursor: cursor.limit(*args)

def _SORT(*args):
    return lambda cursor: cursor.sort(*args)

def _SKIP(*args):
    return lambda cursor: cursor.skip(*args)

class _SortSkipLimitTest(_CollectionComparisonTest):
    def setUp(self):
        super(_SortSkipLimitTest, self).setUp()
        self.cmp.do.insert([{"_id":i, "index" : i} for i in range(30)])
    def test__skip(self):
        self.cmp.compare(_SORT("index", 1), _SKIP(10)).find()
    def test__limit(self):
        self.cmp.compare(_SORT("index", 1), _LIMIT(10)).find()
    def test__skip_and_limit(self):
        self.cmp.compare(_SORT("index", 1), _SKIP(10), _LIMIT(10)).find()

    def test__sort_name(self):
        self.cmp.do.remove()
        for data in ({"a" : 1, "b" : 3, "c" : "data1"},
                     {"a" : 2, "b" : 2, "c" : "data3"},
                     {"a" : 3, "b" : 1, "c" : "data2"}):
            self.cmp.do.insert(data)
        self.cmp.compare(_SORT("a")).find()
        self.cmp.compare(_SORT("b")).find()

    def test__sort_name_nested_doc(self):
        self.cmp.do.remove()
        for data in ({"root": {"a" : 1, "b" : 3, "c" : "data1"}},
                     {"root": {"a" : 2, "b" : 2, "c" : "data3"}},
                     {"root": {"a" : 3, "b" : 1, "c" : "data2"}}):
            self.cmp.do.insert(data)
        self.cmp.compare(_SORT("root.a")).find()
        self.cmp.compare(_SORT("root.b")).find()

    def test__sort_name_nested_list(self):
        self.cmp.do.remove()
        for data in ({"root": [{"a" : 1, "b" : 3, "c" : "data1"}]},
                     {"root": [{"a" : 2, "b" : 2, "c" : "data3"}]},
                     {"root": [{"a" : 3, "b" : 1, "c" : "data2"}]}):
            self.cmp.do.insert(data)
        self.cmp.compare(_SORT("root.0.a")).find()
        self.cmp.compare(_SORT("root.0.b")).find()

    def test__sort_list(self):
        self.cmp.do.remove()
        for data in ({"a" : 1, "b" : 3, "c" : "data1"},
                     {"a" : 2, "b" : 2, "c" : "data3"},
                     {"a" : 3, "b" : 1, "c" : "data2"}):
            self.cmp.do.insert(data)
        self.cmp.compare(_SORT([("a", 1), ("b", -1)])).find()
        self.cmp.compare(_SORT([("b", 1), ("a", -1)])).find()
        self.cmp.compare(_SORT([("b", 1), ("a", -1), ("c", 1)])).find()

    def test__sort_list_nested_doc(self):
        self.cmp.do.remove()
        for data in ({"root": {"a" : 1, "b" : 3, "c" : "data1"}},
                     {"root": {"a" : 2, "b" : 2, "c" : "data3"}},
                     {"root": {"a" : 3, "b" : 1, "c" : "data2"}}):
            self.cmp.do.insert(data)
        self.cmp.compare(_SORT([("root.a", 1), ("root.b", -1)])).find()
        self.cmp.compare(_SORT([("root.b", 1), ("root.a", -1)])).find()
        self.cmp.compare(_SORT([("root.b", 1), ("root.a", -1), ("root.c", 1)])).find()

    def test__sort_list_nested_list(self):
        self.cmp.do.remove()
        for data in ({"root": [{"a" : 1, "b" : 3, "c" : "data1"}]},
                     {"root": [{"a" : 2, "b" : 2, "c" : "data3"}]},
                     {"root": [{"a" : 3, "b" : 1, "c" : "data2"}]}):
            self.cmp.do.insert(data)
        self.cmp.compare(_SORT([("root.0.a", 1), ("root.0.b", -1)])).find()
        self.cmp.compare(_SORT([("root.0.b", 1), ("root.0.a", -1)])).find()
        self.cmp.compare(_SORT([("root.0.b", 1), ("root.0.a", -1), ("root.0.c", 1)])).find()

    def test__close(self):
        # Does nothing - just make sure it exists and takes the right args
        self.cmp.do(lambda cursor: cursor.close()).find()

class MongoClientSortSkipLimitTest(_SortSkipLimitTest, _MongoClientMixin):
    pass

class PymongoConnectionSortSkipLimitTest(_SortSkipLimitTest, _PymongoConnectionMixin):
    pass

class InsertedDocumentTest(TestCase):
    def setUp(self):
        super(InsertedDocumentTest, self).setUp()
        self.collection = mongomock.Connection().db.collection
        self.data = {"a" : 1, "b" : [1, 2, 3], "c" : {"d" : 4}}
        self.orig_data = copy.deepcopy(self.data)
        self.object_id = self.collection.insert(self.data)
    def test__object_is_consistent(self):
        [object] = self.collection.find()
        self.assertEquals(object["_id"], self.object_id)
    def test__find_by_id(self):
        [object] = self.collection.find({"_id" : self.object_id})
        self.assertEquals(object, self.data)
    def test__remove_by_id(self):
        self.collection.remove(self.object_id)
        self.assertEqual(0, self.collection.count())
    def test__inserting_changes_argument(self):
        #Like pymongo, we should fill the _id in the inserted dict (odd behavior, but we need to stick to it)
        self.assertEquals(self.data, dict(self.orig_data, _id=self.object_id))
    def test__data_is_copied(self):
        [object] = self.collection.find()
        self.assertEquals(dict(self.orig_data, _id=self.object_id), object)
        self.data.pop("a")
        self.data["b"].append(5)
        self.assertEquals(dict(self.orig_data, _id=self.object_id), object)
        [object] = self.collection.find()
        self.assertEquals(dict(self.orig_data, _id=self.object_id), object)
    def test__find_returns_copied_object(self):
        [object1] = self.collection.find()
        [object2] = self.collection.find()
        self.assertEquals(object1, object2)
        self.assertIsNot(object1, object2)
        object1["b"].append("bla")
        self.assertNotEquals(object1, object2)

class ObjectIdTest(TestCase):
    def test__equal_with_same_id(self):
        obj1 = ObjectId()
        obj2 = ObjectId(str(obj1))
        self.assertEqual(obj1, obj2)

########NEW FILE########
__FILENAME__ = test__readme_doctest
from unittest import TestCase
import os
import doctest

class ReadMeDocTest(TestCase):
    def test__readme_doctests(self):
        readme_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "README.rst"))
        self.assertTrue(os.path.exists(readme_path))
        result = doctest.testfile(readme_path, module_relative=False)
        self.assertEquals(result.failed, 0, "%s tests failed!" % result.failed)
########NEW FILE########
__FILENAME__ = utils
import sys

if sys.version_info < (2, 7):
    from unittest2 import TestCase, skipIf
else:
    from unittest import TestCase, skipIf

########NEW FILE########
