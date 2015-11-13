__FILENAME__ = model_update
import operator

from django.db.models.expressions import F, ExpressionNode

EXPRESSION_NODE_CALLBACKS = {
    ExpressionNode.ADD: operator.add,
    ExpressionNode.SUB: operator.sub,
    ExpressionNode.MUL: operator.mul,
    ExpressionNode.DIV: operator.div,
    ExpressionNode.MOD: operator.mod,
    ExpressionNode.AND: operator.and_,
    ExpressionNode.OR: operator.or_,
    }

class CannotResolve(Exception):
    pass

def _resolve(instance, node):
    if isinstance(node, F):
        return getattr(instance, node.name)
    elif isinstance(node, ExpressionNode):
        return _resolve(instance, node)
    return node

def resolve_expression_node(instance, node):
    op = EXPRESSION_NODE_CALLBACKS.get(node.connector, None)
    if not op:
        raise CannotResolve
    runner = _resolve(instance, node.children[0])
    for n in node.children[1:]:
        runner = op(runner, _resolve(instance, n))
    return runner

def update(instance, **kwargs):
    "Atomically update instance, setting field/value pairs from kwargs"
    # fields that use auto_now=True should be updated corrected, too!
    for field in instance._meta.fields:
        if hasattr(field, 'auto_now') and field.auto_now and field.name not in kwargs:
            kwargs[field.name] = field.pre_save(instance, False)

    rows_affected = instance.__class__._default_manager.filter(pk=instance.pk).update(**kwargs)

    # apply the updated args to the instance to mimic the change
    # note that these might slightly differ from the true database values
    # as the DB could have been updated by another thread. callers should
    # retrieve a new copy of the object if up-to-date values are required
    for k,v in kwargs.iteritems():
        if isinstance(v, ExpressionNode):
            v = resolve_expression_node(instance, v)
        setattr(instance, k, v)

    # If you use an ORM cache, make sure to invalidate the instance!
    #cache.set(djangocache.get_cache_key(instance=instance), None, 5)
    return rows_affected

########NEW FILE########
__FILENAME__ = nullable_foreignkey
from django.db import connection, models

class NullableForeignKey(models.ForeignKey):
    """
    Prevent the default CASCADE DELETE behavior of normal ForeignKey.
    When an instance pointed to by a NullableForeignKey is deleted,
    the NullableForeignKey field is NULLed rather than the row being deleted.
    """ 
    def __init__(self, *args, **kwargs):
        kwargs['null'] = kwargs['blank'] = True
        super(NullableForeignKey, self).__init__(*args, **kwargs)

    # Monkeypatch the related class's "collect_sub_objects"
    # to not delete this object
    def contribute_to_related_class(self, cls, related):
        super(NullableForeignKey, self).contribute_to_related_class(cls, related)
        _original_csb_attr_name = '_original_collect_sub_objects'
        # define a new "collect_sub_objects" method 
        this_field = self
        def _new_collect_sub_objects(self, *args, **kwargs):
            qn = connection.ops.quote_name
            # find all fields related to the model who's instance is
            # being deleted
            for related in self._meta.get_all_related_objects():
                if isinstance(related.field, this_field.__class__):
                    table = qn(related.model._meta.db_table)
                    column = qn(related.field.column)
                    sql = "UPDATE %s SET %s = NULL WHERE %s = %%s;" % (table, column, column)
                    connection.cursor().execute(sql, [self.pk])

            # Now proceed with collecting sub objects that are still tied via FK
            getattr(self, _original_csb_attr_name)(*args, **kwargs)

        # monkey patch the related classes _collect_sub_objects method.
        # store the original method in an attr named `_original_csb_attr_name`
        if not hasattr(cls, _original_csb_attr_name):
            setattr(cls, _original_csb_attr_name, cls._collect_sub_objects)
            setattr(cls, '_collect_sub_objects', _new_collect_sub_objects)

########NEW FILE########
__FILENAME__ = staff_debug_wsgi_handler
from django.core.handlers import wsgi

class StaffDebugWSGIHandler(wsgi.WSGIHandler):
    "WSGI Handler that shows the debug error page if the logged in user is staff"

    def handle_uncaught_exception(self, request, resolver, exc_info):
        "Return a debug page response if the logged in user is staff"
        from django.conf import settings

        if not settings.DEBUG and hasattr(request, 'user') and request.user.is_staff:
            from django.views import debug
            return debug.technical_500_response(request, *exc_info)

        # not logged in or not a staff user, display normal public 500
        return super(StaffDebugWSGIHandler, self).handle_uncaught_exception(
            request, resolver, exc_info
            )

########NEW FILE########
