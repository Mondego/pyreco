__FILENAME__ = fields
"""

dexml.fields:  basic field type definitions for dexml
=====================================================

"""

import dexml
import random
from xml.sax.saxutils import escape, quoteattr

#  Global counter tracking the order in which fields are declared.
_order_counter = 0

class _AttrBucket:
    """A simple class used only to hold attributes."""
    pass


class Field(object):
    """Base class for all dexml Field classes.

    Field classes are responsible for parsing and rendering individual
    components to the XML.  They also act as descriptors on dexml Model
    instances, to get/set the corresponding properties.

    Each field instance will magically be given the following properties:

      * model_class:  the Model subclass to which it is attached
      * field_name:   the name under which is appears on that class

    The following methods are required for interaction with the parsing
    and rendering machinery:

      * parse_attributes:    parse info out of XML node attributes
      * parse_child_node:    parse into out of an XML child node
      * render_attributes:   render XML for node attributes
      * render_children:     render XML for child nodes
      
    """

    class arguments:
        required = True

    def __init__(self,**kwds):
        """Default Field constructor.

        This constructor keeps track of the order in which Field instances
        are created, since this information can have semantic meaning in
        XML.  It also merges any keyword arguments with the defaults
        defined on the 'arguments' inner class, and assigned these attributes
        to the Field instance.
        """
        global _order_counter
        self._order_counter = _order_counter = _order_counter + 1
        args = self.__class__.arguments
        for argnm in dir(args):
            if not argnm.startswith("__"):
                setattr(self,argnm,kwds.get(argnm,getattr(args,argnm)))

    def parse_attributes(self,obj,attrs):
        """Parse any attributes for this field from the given list.

        This method will be called with the Model instance being parsed and
        a list of attribute nodes from its XML tag.  Any attributes of 
        interest to this field should be processed, and a list of the unused
        attribute nodes returned.
        """
        return attrs

    def parse_child_node(self,obj,node):
        """Parse a child node for this field.

        This method will be called with the Model instance being parsed and
        the current child node of that model's XML tag.  There are three
        options for processing this node:

            * return PARSE_DONE, indicating that it was consumed and this
              field now has all the necessary data.
            * return PARSE_MORE, indicating that it was consumed but this
              field will accept more nodes.
            * return PARSE_SKIP, indicating that it was not consumed by
              this field.

        Any other return value will be taken as a parse error.
        """
        return dexml.PARSE_SKIP

    def parse_done(self,obj):
        """Finalize parsing for the given object.

        This method is called as a simple indicator that no more data will
        be forthcoming.  No return value is expected.
        """
        pass

    def render_attributes(self,obj,val,nsmap):
        """Render any attributes that this field manages."""
        return []

    def render_children(self,obj,nsmap,val):
        """Render any child nodes that this field manages."""
        return []

    def __get__(self,instance,owner=None):
        if instance is None:
            return self
        return instance.__dict__.get(self.field_name)

    def __set__(self,instance,value):
        instance.__dict__[self.field_name] = value

    def _check_tagname(self,node,tagname):
        if node.nodeType != node.ELEMENT_NODE:
            return False
        if isinstance(tagname,basestring):
            if node.localName != tagname:
                return False
            if node.namespaceURI:
                if node.namespaceURI != self.model_class.meta.namespace:
                    return False
        else:
            (tagns,tagname) = tagname
            if node.localName != tagname:
                return False
            if node.namespaceURI != tagns:
                return False
        return True


class Value(Field):
    """Field subclass that holds a simple scalar value.

    This Field subclass contains the common logic to parse/render simple
    scalar value fields - fields that don't required any recursive parsing.
    Individual subclasses should provide the parse_value() and render_value()
    methods to do type coercion of the value.

    Value fields can also have a default value, specified by the 'default'
    keyword argument.

    By default, the field maps to an attribute of the model's XML node with
    the same name as the field declaration.  Consider:

        class MyModel(Model):
            my_field = fields.Value(default="test")


    This corresponds to the XML fragment "<MyModel my_field='test' />".
    To use a different name specify the 'attrname' kwd argument.  To use
    a subtag instead of an attribute specify the 'tagname' kwd argument.

    Namespaced attributes or subtags are also supported, by specifying a
    (namespace,tagname) pair for 'attrname' or 'tagname' respectively.
    """

    class arguments(Field.arguments):
        tagname = None
        attrname = None
        default = None

    def __init__(self,**kwds):
        super(Value,self).__init__(**kwds)
        if self.default is not None:
            self.required = False

    def _get_attrname(self):
        if self.__dict__["tagname"]:
            return None
        attrname = self.__dict__['attrname']
        if not attrname:
            attrname = self.field_name
        return attrname
    def _set_attrname(self,attrname):
        self.__dict__['attrname'] = attrname
    attrname = property(_get_attrname,_set_attrname)

    def _get_tagname(self):
        if self.__dict__["attrname"]:
            return None
        tagname = self.__dict__['tagname']
        if tagname and not isinstance(tagname,(basestring,tuple)):
            tagname = self.field_name
        return tagname
    def _set_tagname(self,tagname):
        self.__dict__['tagname'] = tagname
    tagname = property(_get_tagname,_set_tagname)

    def __get__(self,instance,owner=None):
        val = super(Value,self).__get__(instance,owner)
        if val is None:
            return self.default
        return val

    def parse_attributes(self,obj,attrs):
        #  Bail out if we're attached to a subtag rather than an attr.
        if self.tagname:
            return attrs
        unused = []
        attrname = self.attrname
        if isinstance(attrname,basestring):
            ns = None
        else:
            (ns,attrname) = attrname
        for attr in attrs:
            if attr.localName == attrname:
                if attr.namespaceURI == ns:
                    self.__set__(obj,self.parse_value(attr.nodeValue))
                else:
                    unused.append(attr)
            else:
                unused.append(attr)
        return unused

    def parse_child_node(self,obj,node):
        if not self.tagname:
            return dexml.PARSE_SKIP
        if self.tagname == ".":
            node = node.parentNode
        else:
            if not self._check_tagname(node,self.tagname):
                return dexml.PARSE_SKIP
        vals = []
        #  Merge all text nodes into a single value
        for child in node.childNodes:
            if child.nodeType not in (child.TEXT_NODE,child.CDATA_SECTION_NODE):
                raise dexml.ParseError("non-text value node")
            vals.append(child.nodeValue)
        self.__set__(obj,self.parse_value("".join(vals)))
        return dexml.PARSE_DONE

    def render_attributes(self,obj,val,nsmap):
        if val is not None and val is not self.default and self.attrname:
            qaval = quoteattr(self.render_value(val))
            if isinstance(self.attrname,basestring):
                yield '%s=%s' % (self.attrname,qaval,)
            else:
                m_meta = self.model_class.meta
                (ns,nm) = self.attrname
                if ns == m_meta.namespace and m_meta.namespace_prefix:
                    prefix = m_meta.namespace_prefix
                    yield '%s:%s=%s' % (prefix,nm,qaval,)
                elif ns is None:
                    yield '%s=%s' % (nm,qaval,)
                else:
                    for (p,n) in nsmap.iteritems():
                        if ns == n[0]:
                            prefix = p
                            break
                    else:
                        prefix = "p" + str(random.randint(0,10000))
                        while prefix in nsmap:
                            prefix = "p" + str(random.randint(0,10000))
                        yield 'xmlns:%s="%s"' % (prefix,ns,)
                    yield '%s:%s=%s' % (prefix,nm,qaval,)

    def render_children(self,obj,val,nsmap):
        if val is not None and val is not self.default and self.tagname:
            val = self._esc_render_value(val)
            if self.tagname == ".":
                yield val
            else:
                attrs = ""
                #  By default, tag values inherit the namespace of their
                #  containing model class.
                if isinstance(self.tagname,basestring):
                    prefix = self.model_class.meta.namespace_prefix
                    localName = self.tagname
                else:
                    m_meta = self.model_class.meta
                    (ns,localName) = self.tagname
                    if not ns:
                        #  If we have an explicitly un-namespaced tag,
                        #  we need to be careful.  The model tag might have
                        #  set the default namespace, which we need to undo.
                        prefix = None
                        if m_meta.namespace and not m_meta.namespace_prefix:
                            attrs = ' xmlns=""'
                    elif ns == m_meta.namespace:
                        prefix = m_meta.namespace_prefix
                    else:
                        for (p,n) in nsmap.iteritems():
                            if ns == n[0]:
                                prefix = p
                                break
                        else:
                            prefix = "p" + str(random.randint(0,10000))
                            while prefix in nsmap:
                                prefix = "p" + str(random.randint(0,10000))
                            attrs = ' xmlns:%s="%s"' % (prefix,ns)
                yield self._render_tag(val,prefix,localName,attrs)

    def _render_tag(self,val,prefix,localName,attrs):
        if val:
            if prefix:
                args = (prefix,localName,attrs,val,prefix,localName)
                return "<%s:%s%s>%s</%s:%s>" % args
            else:
                return "<%s%s>%s</%s>" % (localName,attrs,val,localName)
        else:
            if prefix:
                return "<%s:%s%s />" % (prefix,localName,attrs,)
            else:
                return "<%s%s />" % (localName,attrs)

    def parse_value(self,val):
        return val

    def render_value(self,val):
        if not isinstance(val, basestring):
            val = str(val)
        return val

    def _esc_render_value(self,val):
        return escape(self.render_value(val))



class String(Value):
    """Field representing a simple string value."""
    # actually, the base Value() class will do this automatically.
    pass


class CDATA(Value):
    """String field rendered as CDATA."""

    def __init__(self,**kwds):
        super(CDATA,self).__init__(**kwds)
        if self.__dict__.get("tagname",None) is None:
            raise ValueError("CDATA fields must have a tagname")

    def _esc_render_value(self,val):
        val = self.render_value(val)
        val = val.replace("]]>","]]]]><![CDATA[>")
        return "<![CDATA[" + val + "]]>"


class Integer(Value):
    """Field representing a simple integer value."""
    def parse_value(self,val):
        return int(val)


class Float(Value):
    """Field representing a simple float value."""
    def parse_value(self,val):
        return float(val)


class Boolean(Value):
    """Field representing a simple boolean value.

    The strings corresponding to false are 'no', 'off', 'false' and '0',
    compared case-insensitively.  Note that this means an empty tag or
    attribute is considered True - this is usually what you want, since 
    a completely missing attribute or tag can be interpreted as False.

    To enforce that the presence of a tag indicates True and the absence of
    a tag indicates False, pass the keyword argument "empty_only".
    """

    class arguments(Value.arguments):
        empty_only = False

    def __init__(self,**kwds):
        super(Boolean,self).__init__(**kwds)
        if self.empty_only:
            self.required = False

    def __set__(self,instance,value):
        instance.__dict__[self.field_name] = bool(value)

    def parse_value(self,val):
        if self.empty_only and val != "":
            raise ValueError("non-empty value in empty_only Boolean")
        if val.lower() in ("no","off","false","0"):
            return False
        return True

    def render_children(self,obj,val,nsmap):
        if not val and self.empty_only:
            return []
        return super(Boolean,self).render_children(obj,val,nsmap)

    def render_attributes(self,obj,val,nsmap):
        if not val and self.empty_only:
            return []
        return super(Boolean,self).render_attributes(obj,val,nsmap)

    def render_value(self,val):
        if not val:
            return "false"
        if self.empty_only:
            return ""
        return "true"


class Model(Field):
    """Field subclass referencing another Model instance.

    This field sublcass allows Models to contain other Models recursively.
    The first argument to the field constructor must be either a Model
    class, or the name or tagname of a Model class.
    """

    class arguments(Field.arguments):
        type = None

    def __init__(self,type=None,**kwds):
        kwds["type"] = type
        super(Model,self).__init__(**kwds)

    def _get_type(self):
        return self.__dict__.get("type")
    def _set_type(self,value):
        if value is not None:
            self.__dict__["type"] = value
    type = property(_get_type,_set_type)

    def __set__(self,instance,value):
        typeclass = self.typeclass
        if value and not isinstance(value, typeclass):
            raise ValueError("Invalid value type %s. Model field requires %s instance" %
                (value.__class__.__name__, typeclass.__name__))
        super(Model, self).__set__(instance, value)

    @property
    def typeclass(self):
        try:
            return self.__dict__['typeclass']
        except KeyError:
            self.__dict__['typeclass'] = self._load_typeclass()
            return self.__dict__['typeclass']
 
    def _load_typeclass(self):
        typ = self.type
        if isinstance(typ,dexml.ModelMetaclass):
            return typ
        if typ is None:
            typ = self.field_name
        typeclass = None
        if isinstance(typ,basestring):
            if self.model_class.meta.namespace:
                ns = self.model_class.meta.namespace
                typeclass = dexml.ModelMetaclass.find_class(typ,ns)
            if typeclass is None:
                typeclass = dexml.ModelMetaclass.find_class(typ,None)
            if typeclass is None:
                raise ValueError("Unknown Model class: %s" % (typ,))
        else:
            (ns,typ) = typ
            if isinstance(typ,dexml.ModelMetaclass):
                return typ
            typeclass = dexml.ModelMetaclass.find_class(typ,ns)
            if typeclass is None:
                raise ValueError("Unknown Model class: (%s,%s)" % (ns,typ))
        return typeclass

    def parse_child_node(self,obj,node):
        typeclass = self.typeclass
        try:
            typeclass.validate_xml_node(node)
        except dexml.ParseError:
            return dexml.PARSE_SKIP
        else:
            inst = typeclass.parse(node)
            self.__set__(obj,inst)
            return dexml.PARSE_DONE

    def render_attributes(self,obj,val,nsmap):
        return []

    def render_children(self,obj,val,nsmap):
        if val is not None:
            for data in val._render(nsmap):
                yield data


class List(Field):
    """Field subclass representing a list of fields.

    This field corresponds to a homogenous list of other fields.  You would
    declare it like so:

      class MyModel(Model):
          items = fields.List(fields.String(tagname="item"))

    Corresponding to XML such as:

      <MyModel><item>one</item><item>two</item></MyModel>


    The properties 'minlength' and 'maxlength' control the allowable length
    of the list.

    The 'tagname' property sets an optional wrapper tag which acts as container
    for list items, for example:

      class MyModel(Model):
          items = fields.List(fields.String(tagname="item"),
                              tagname='list')

    Corresponding to XML such as:

      <MyModel><list><item>one</item><item>two</item></list></MyModel>

    This wrapper tag is always rendered, even if the list is empty.  It is
    transparently removed when parsing.
    """

    class arguments(Field.arguments):
        field = None
        minlength = None
        maxlength = None
        tagname = None

    def __init__(self,field,**kwds):
        if isinstance(field,Field):
            kwds["field"] = field
        else:
            kwds["field"] = Model(field,**kwds)
        super(List,self).__init__(**kwds)
        if not self.minlength and not self.tagname:
            self.required = False
        if self.minlength and not self.required:
            raise ValueError("List must be required if it has minlength")

    def _get_field(self):
        field = self.__dict__["field"]
        if not hasattr(field,"field_name"):
            field.field_name = self.field_name
        if not hasattr(field,"model_class"):
            field.model_class = self.model_class
        return field
    def _set_field(self,field):
        self.__dict__["field"] = field
    field = property(_get_field,_set_field)

    def __get__(self,instance,owner=None):
        val = super(List,self).__get__(instance,owner)
        if val is not None:
            return val
        self.__set__(instance,[])
        return self.__get__(instance,owner)

    def parse_child_node(self,obj,node):
        #  If our children are inside a grouping tag, parse
        #  that first.  The presence of this is indicated by
        #  setting the empty list on the target object.
        if self.tagname:
            val = super(List,self).__get__(obj)
            if val is None:
                if node.nodeType != node.ELEMENT_NODE:
                    return dexml.PARSE_SKIP
                elif node.tagName == self.tagname:
                    self.__set__(obj,[])
                    return dexml.PARSE_CHILDREN
                else:
                    return dexml.PARSE_SKIP
        #  Now we just parse each child node.
        tmpobj = _AttrBucket()
        res = self.field.parse_child_node(tmpobj,node)
        if res is dexml.PARSE_MORE:
            raise ValueError("items in a list cannot return PARSE_MORE")
        if res is dexml.PARSE_DONE:
            items = self.__get__(obj)
            val = getattr(tmpobj,self.field_name)
            items.append(val)
            return dexml.PARSE_MORE
        else:
            return dexml.PARSE_SKIP

    def parse_done(self,obj):
        items = self.__get__(obj)
        if self.minlength is not None and len(items) < self.minlength:
            raise dexml.ParseError("Field '%s': not enough items" % (self.field_name,))
        if self.maxlength is not None and len(items) > self.maxlength:
            raise dexml.ParseError("Field '%s': too many items" % (self.field_name,))

    def render_children(self,obj,items,nsmap):
        #  Create a generator that yields child data chunks, and validates
        #  the number of items in the list as it goes.  It allows any 
        #  iterable to be passed in, not just a list.
        def child_chunks():
            num_items = 0
            for item in items:
                num_items += 1
                if self.maxlength is not None and num_items > self.maxlength:
                    msg = "Field '%s': too many items" % (self.field_name,)
                    raise dexml.RenderError(msg)
                for data in self.field.render_children(obj,item,nsmap):
                    yield data
            if self.minlength is not None and num_items < self.minlength:
                msg = "Field '%s': not enough items" % (self.field_name,)
                raise dexml.RenderError(msg)
        chunks = child_chunks()
        #  Render each chunk, but suppress the wrapper tag if there's no data.
        try:
            data = chunks.next()
        except StopIteration:
            if self.tagname and self.required:
                yield "<%s />" % (self.tagname,)
        else:
            if self.tagname:
                yield "<%s>" % (self.tagname,)
            yield data
            for data in chunks:
                yield data
            if self.tagname:
                yield "</%s>" % (self.tagname,)


class Dict(Field):
    """Field subclass representing a dict of fields keyed by unique attribute value.

    This field corresponds to an indexed dict of other fields.  You would
    declare it like so:

      class MyObject(Model):
          name = fields.String(tagname = 'name')
          attr = fields.String(tagname = 'attr')

      class MyModel(Model):
          items = fields.Dict(fields.Model(MyObject), key = 'name')

    Corresponding to XML such as:

      <MyModel><MyObject><name>obj1</name><attr>val1</attr></MyObject></MyModel>


    The properties 'minlength' and 'maxlength' control the allowable size
    of the dict as in the List class.

    If 'unique' property is set to True, parsing will raise exception on
    non-unique key values.

    The 'dictclass' property controls the internal dict-like class used by
    the fielt.  By default it is the standard dict class.

    The 'tagname' property sets the 'wrapper' tag which acts as container
    for dict items, for example:

      from collections import defaultdict
      class MyObject(Model):
          name = fields.String()
          attr = fields.String()

      class MyDict(defaultdict):
          def __init__(self):
              super(MyDict, self).__init__(MyObject)

      class MyModel(Model):
          objects = fields.Dict('MyObject', key = 'name',
                                tagname = 'dict', dictclass = MyDict)

      xml = '<MyModel><dict><MyObject name="obj1">'\
            <attr>val1</attr></MyObject></dict></MyModel>'
      mymodel = MyModel.parse(xml)
      obj2 = mymodel['obj2']
      print(obj2.name)
      print(mymodel.render(fragment = True))

    This wrapper tag is always rendered, even if the dict is empty.  It is
    transparently removed when parsing.
    """

    class arguments(Field.arguments):
        field = None
        minlength = None
        maxlength = None
        unique = False
        tagname = None
        dictclass = dict

    def __init__(self, field, key, **kwds):
        if isinstance(field, Field):
            kwds["field"] = field
        else:
            kwds["field"] = Model(field, **kwds)
        super(Dict, self).__init__(**kwds)
        if not self.minlength and not self.tagname:
            self.required = False
        if self.minlength and not self.required:
            raise ValueError("Dict must be required if it has minlength")
        self.key = key

    def _get_field(self):
        field = self.__dict__["field"]
        if not hasattr(field, "field_name"):
            field.field_name = self.field_name
        if not hasattr(field, "model_class"):
            field.model_class = self.model_class
        return field
    def _set_field(self, field):
        self.__dict__["field"] = field
    field = property(_get_field, _set_field)

    def __get__(self,instance,owner=None):
        val = super(Dict, self).__get__(instance, owner)
        if val is not None:
            return val
        class dictclass(self.dictclass):
            key = self.key
            def __setitem__(self, key, value):
                keyval = getattr(value, self.key)
                if keyval and keyval != key:
                    raise ValueError('Key field value does not match dict key')
                setattr(value, self.key, key)
                super(dictclass, self).__setitem__(key, value)
        self.__set__(instance, dictclass())
        return self.__get__(instance, owner)

    def parse_child_node(self, obj, node):
        #  If our children are inside a grouping tag, parse
        #  that first.  The presence of this is indicated by
        #  setting an empty dict on the target object.
        if self.tagname:
            val = super(Dict,self).__get__(obj)
            if val is None:
                if node.nodeType != node.ELEMENT_NODE:
                    return dexml.PARSE_SKIP
                elif node.tagName == self.tagname:
                    self.__get__(obj)
                    return dexml.PARSE_CHILDREN
                else:
                    return dexml.PARSE_SKIP
        #  Now we just parse each child node.
        tmpobj = _AttrBucket()
        res = self.field.parse_child_node(tmpobj, node)
        if res is dexml.PARSE_MORE:
            raise ValueError("items in a dict cannot return PARSE_MORE")
        if res is dexml.PARSE_DONE:
            items = self.__get__(obj)
            val = getattr(tmpobj, self.field_name)
            try:
                key = getattr(val, self.key)
            except AttributeError:
                raise dexml.ParseError("Key field '%s' required but not found in dict value" % (self.key, ))
            if self.unique and key in items:
                raise dexml.ParseError("Key '%s' already exists in dict" % (key,))
            items[key] = val
            return dexml.PARSE_MORE
        else:
            return dexml.PARSE_SKIP

    def parse_done(self, obj):
        items = self.__get__(obj)
        if self.minlength is not None and len(items) < self.minlength:
            raise dexml.ParseError("Field '%s': not enough items" % (self.field_name,))
        if self.maxlength is not None and len(items) > self.maxlength:
            raise dexml.ParseError("Field '%s': too many items" % (self.field_name,))

    def render_children(self, obj, items, nsmap):
        if self.minlength is not None and len(items) < self.minlength:
            raise dexml.RenderError("Field '%s': not enough items" % (self.field_name,))
        if self.maxlength is not None and len(items) > self.maxlength:
            raise dexml.RenderError("too many items")
        if self.tagname:
            children = "".join(data for item in items.values() for data in self.field.render_children(obj,item,nsmap))
            if not children:
                if self.required:
                    yield "<%s />" % (self.tagname,)
            else:
                yield children.join(('<%s>'%self.tagname, '</%s>'%self.tagname))
        else:
            for item in items.values():
                for data in self.field.render_children(obj, item, nsmap):
                    yield data


class Choice(Field):
    """Field subclass accepting any one of a given set of Model fields."""

    class arguments(Field.arguments):
        fields = []

    def __init__(self,*fields,**kwds):
        real_fields = []
        for field in fields:
            if isinstance(field,Model):
                real_fields.append(field)
            elif isinstance(field,basestring):
                real_fields.append(Model(field))
            else:
                raise ValueError("only Model fields are allowed within a Choice field")
        kwds["fields"] = real_fields
        super(Choice,self).__init__(**kwds)

    def parse_child_node(self,obj,node):
        for field in self.fields:
            field.field_name = self.field_name
            field.model_class = self.model_class
            res = field.parse_child_node(obj,node)
            if res is dexml.PARSE_MORE:
                raise ValueError("items in a Choice cannot return PARSE_MORE")
            if res is dexml.PARSE_DONE:
                return dexml.PARSE_DONE
        else:
            return dexml.PARSE_SKIP

    def render_children(self,obj,item,nsmap):
        if item is None:
            if self.required:
                raise dexml.RenderError("Field '%s': required field is missing" % (self.field_name,))
        else:
            for data in item._render(nsmap=nsmap):
                yield data


class XmlNode(Field):

    class arguments(Field.arguments):
        tagname = None
        encoding = None

    def __set__(self,instance,value):
        if isinstance(value,basestring):
            if isinstance(value,unicode) and self.encoding:
                value = value.encode(self.encoding)
            doc = dexml.minidom.parseString(value)
            value = doc.documentElement
        if value is not None and value.namespaceURI is not None:
            nsattr = "xmlns"
            if value.prefix:
                nsattr = ":".join((nsattr,value.prefix,))
            value.attributes[nsattr] = value.namespaceURI
        return super(XmlNode,self).__set__(instance,value)

    def parse_child_node(self,obj,node):
        if self.tagname is None or self._check_tagname(node,self.tagname):
            self.__set__(obj,node)
            return dexml.PARSE_DONE
        return dexml.PARSE_SKIP

    @classmethod
    def render_children(cls,obj,val,nsmap):
        if val is not None:
            yield val.toxml()


########NEW FILE########
__FILENAME__ = test
"""

  dexml.test:  testcases for dexml module.

"""

import sys
import os
import os.path
import difflib
import unittest
import doctest
from xml.dom import minidom
from StringIO import StringIO

import dexml
from dexml import fields


def b(raw):
    """Compatability wrapper for b"string" syntax."""
    return raw.encode("ascii")


def model_fields_equal(m1,m2):
    """Check for equality by comparing model fields."""
    for nm in m1.__class__._fields:
        v1 = getattr(m1,nm.field_name)
        v2 = getattr(m2,nm.field_name)
        if isinstance(v1,dexml.Model):
            if not model_fields_equal(v1,v2):
                return False
        elif v1 != v2:
            return False
    return True
          


class TestDexmlDocstring(unittest.TestCase):

    def test_docstring(self):
        """Test dexml docstrings

        We don't do this on python3 because of the many small ways in
        which the output has changed in that version.
        """
        if sys.version_info < (3,):
            assert doctest.testmod(dexml)[0] == 0

    def test_readme_matches_docstring(self):
        """Ensure that the README is in sync with the docstring.

        This test should always pass; if the README is out of sync it just
        updates it with the contents of dexml.__doc__.
        """
        dirname = os.path.dirname
        readme = os.path.join(dirname(dirname(__file__)),"README.rst")
        if not os.path.isfile(readme):
            f = open(readme,"wb")
            f.write(dexml.__doc__.encode())
            f.close()
        else:
            f = open(readme,"rb")
            if f.read() != dexml.__doc__:
                f.close()
                f = open(readme,"wb")
                f.write(dexml.__doc__.encode())
                f.close()



class TestDexml(unittest.TestCase):


    def test_base(self):
        """Test operation of a dexml.Model class with no fields."""
        class hello(dexml.Model):
            pass

        h = hello.parse("<hello />")
        self.assertTrue(h)

        h = hello.parse("<hello>\n</hello>")
        self.assertTrue(h)

        h = hello.parse("<hello>world</hello>")
        self.assertTrue(h)

        d = minidom.parseString("<hello>world</hello>")
        h = hello.parse(d)
        self.assertTrue(h)

        self.assertRaises(dexml.ParseError,hello.parse,"<Hello />")
        self.assertRaises(dexml.ParseError,hello.parse,"<hllo />")
        self.assertRaises(dexml.ParseError,hello.parse,"<hello xmlns='T:' />")

        hello.meta.ignore_unknown_elements = False
        self.assertRaises(dexml.ParseError,hello.parse,"<hello>world</hello>")
        hello.meta.ignore_unknown_elements = True

        h = hello()
        self.assertEquals(h.render(),'<?xml version="1.0" ?><hello />')
        self.assertEquals(h.render(fragment=True),"<hello />")
        self.assertEquals(h.render(encoding="utf8"),b('<?xml version="1.0" encoding="utf8" ?><hello />'))
        self.assertEquals(h.render(encoding="utf8",fragment=True),b("<hello />"))

        self.assertEquals(h.render(),"".join(h.irender()))
        self.assertEquals(h.render(fragment=True),"".join(h.irender(fragment=True)))
        self.assertEquals(h.render(encoding="utf8"),b("").join(h.irender(encoding="utf8")))
        self.assertEquals(h.render(encoding="utf8",fragment=True),b("").join(h.irender(encoding="utf8",fragment=True)))


    def test_errors_on_malformed_xml(self):
        class hello(dexml.Model):
            pass

        self.assertRaises(dexml.XmlError,hello.parse,b("<hello>"))
        self.assertRaises(dexml.XmlError,hello.parse,b("<hello></helo>"))
        self.assertRaises(dexml.XmlError,hello.parse,b(""))

        self.assertRaises(dexml.XmlError,hello.parse,u"")
        self.assertRaises(dexml.XmlError,hello.parse,u"<hello>")
        self.assertRaises(dexml.XmlError,hello.parse,u"<hello></helo>")

        self.assertRaises(dexml.XmlError,hello.parse,StringIO("<hello>"))
        self.assertRaises(dexml.XmlError,hello.parse,StringIO("<hello></helo>"))
        self.assertRaises(dexml.XmlError,hello.parse,StringIO(""))

        self.assertRaises(ValueError,hello.parse,None)
        self.assertRaises(ValueError,hello.parse,42)
        self.assertRaises(ValueError,hello.parse,staticmethod)


    def test_unicode_model_tagname(self):
        """Test a dexml.Model class with a unicode tag name."""
        class hello(dexml.Model):
            class meta:
                tagname = u"hel\N{GREEK SMALL LETTER LAMDA}o"

        h = hello.parse(u"<hel\N{GREEK SMALL LETTER LAMDA}o />")
        self.assertTrue(h)

        h = hello.parse(u"<hel\N{GREEK SMALL LETTER LAMDA}o>\n</hel\N{GREEK SMALL LETTER LAMDA}o>")
        self.assertTrue(h)
        self.assertRaises(dexml.ParseError,hello.parse,u"<hello />")
        self.assertRaises(dexml.ParseError,hello.parse,u"<Hello />")
        self.assertRaises(dexml.ParseError,hello.parse,u"<hllo />")
        self.assertRaises(dexml.ParseError,hello.parse,u"<Hel\N{GREEK SMALL LETTER LAMDA}o />")

        h = hello.parse(u"<hel\N{GREEK SMALL LETTER LAMDA}o>world</hel\N{GREEK SMALL LETTER LAMDA}o>")
        self.assertTrue(h)

        h = hello.parse(u"<?xml version='1.0' encoding='utf-8' ?><hel\N{GREEK SMALL LETTER LAMDA}o>world</hel\N{GREEK SMALL LETTER LAMDA}o>")
        h = hello.parse(u"<?xml version='1.0' encoding='utf-16' ?><hel\N{GREEK SMALL LETTER LAMDA}o>world</hel\N{GREEK SMALL LETTER LAMDA}o>")
        self.assertTrue(h)

        h = hello()
        self.assertEquals(h.render(),u'<?xml version="1.0" ?><hel\N{GREEK SMALL LETTER LAMDA}o />')
        self.assertEquals(h.render(fragment=True),u"<hel\N{GREEK SMALL LETTER LAMDA}o />")
        self.assertEquals(h.render(encoding="utf8"),u'<?xml version="1.0" encoding="utf8" ?><hel\N{GREEK SMALL LETTER LAMDA}o />'.encode("utf8"))
        self.assertEquals(h.render(encoding="utf8",fragment=True),u"<hel\N{GREEK SMALL LETTER LAMDA}o />".encode("utf8"))

        self.assertEquals(h.render(),"".join(h.irender()))
        self.assertEquals(h.render(fragment=True),"".join(h.irender(fragment=True)))
        self.assertEquals(h.render(encoding="utf8"),b("").join(h.irender(encoding="utf8")))
        self.assertEquals(h.render(encoding="utf8",fragment=True),b("").join(h.irender(encoding="utf8",fragment=True)))

    def test_unicode_string_field(self):
        """Test a dexml.Model class with a unicode string field."""
        class Person(dexml.Model):
            name = fields.String()

        p = Person.parse(u"<Person name='hel\N{GREEK SMALL LETTER LAMDA}o'/>")
        self.assertEquals(p.name, u"hel\N{GREEK SMALL LETTER LAMDA}o")

        p = Person()
        p.name = u"hel\N{GREEK SMALL LETTER LAMDA}o"
        self.assertEquals(p.render(encoding="utf8"), u'<?xml version="1.0" encoding="utf8" ?><Person name="hel\N{GREEK SMALL LETTER LAMDA}o" />'.encode("utf8"))

    def test_model_meta_attributes(self):
        class hello(dexml.Model):
            pass

        self.assertRaises(dexml.ParseError,hello.parse,"<Hello />")
        hello.meta.case_sensitive = False
        self.assertTrue(hello.parse("<Hello />"))
        self.assertRaises(dexml.ParseError,hello.parse,"<Helpo />")
        hello.meta.case_sensitive = True

        self.assertTrue(hello.parse("<hello>world</hello>"))
        hello.meta.ignore_unknown_elements = False
        self.assertRaises(dexml.ParseError,hello.parse,"<hello>world</hello>")
        hello.meta.ignore_unknown_elements = True


    def test_namespace(self):
        """Test basic handling of namespaces."""
        class hello(dexml.Model):
            class meta:
                namespace = "http://hello.com/"
                ignore_unknown_elements = False

        h = hello.parse("<hello xmlns='http://hello.com/' />")
        self.assertTrue(h)

        h = hello.parse("<H:hello xmlns:H='http://hello.com/' />")
        self.assertTrue(h)

        self.assertRaises(dexml.ParseError,hello.parse,"<hello />")
        self.assertRaises(dexml.ParseError,hello.parse,"<H:hllo xmlns:H='http://hello.com/' />")
        self.assertRaises(dexml.ParseError,hello.parse,"<H:hello xmlns:H='http://hello.com/'>world</H:hello>")

        hello.meta.case_sensitive = False
        self.assertRaises(dexml.ParseError,hello.parse,"<Hello />")
        self.assertRaises(dexml.ParseError,hello.parse,"<H:hllo xmlns:H='http://hello.com/' />")
        self.assertRaises(dexml.ParseError,hello.parse,"<H:hello xmlns:H='http://Hello.com/' />")
        hello.parse("<H:HeLLo xmlns:H='http://hello.com/' />")
        hello.meta.case_sensitive = True

        h = hello()
        self.assertEquals(h.render(fragment=True),'<hello xmlns="http://hello.com/" />')

        hello.meta.namespace_prefix = "H"
        self.assertEquals(h.render(fragment=True),'<H:hello xmlns:H="http://hello.com/" />')



    def test_base_field(self):
        """Test operation of the base Field class (for coverage purposes)."""
        class tester(dexml.Model):
            value = fields.Field()
        assert isinstance(tester.value,fields.Field)
        #  This is a parse error because Field doesn't consume any nodes
        self.assertRaises(dexml.ParseError,tester.parse,"<tester value='42' />")
        self.assertRaises(dexml.ParseError,tester.parse,"<tester><value>42</value></tester>")
        #  Likewise, Field doesn't output any XML so it thinks value is missing
        self.assertRaises(dexml.RenderError,tester(value=None).render)


    def test_value_fields(self):
        """Test operation of basic value fields."""
        class hello(dexml.Model):
            recipient = fields.String()
            sentby = fields.String(attrname="sender")
            strength = fields.Integer(default=1)
            message = fields.String(tagname="msg")

        h = hello.parse("<hello recipient='ryan' sender='lozz' strength='7'><msg>hi there</msg></hello>")
        self.assertEquals(h.recipient,"ryan")
        self.assertEquals(h.sentby,"lozz")
        self.assertEquals(h.message,"hi there")
        self.assertEquals(h.strength,7)

        #  These are parse errors due to namespace mismatches
        self.assertRaises(dexml.ParseError,hello.parse,"<hello xmlns:N='N:' N:recipient='ryan' sender='lozz' strength='7'><msg>hi there</msg></hello>")
        self.assertRaises(dexml.ParseError,hello.parse,"<hello xmlns:N='N:' recipient='ryan' sender='lozz' strength='7'><N:msg>hi there</N:msg></hello>")

        #  These are parse errors due to subtags
        self.assertRaises(dexml.ParseError,hello.parse,"<hello recipient='ryan' sender='lozz' strength='7'><msg>hi <b>there</b></msg></hello>")


    def test_float_field(self):
        class F(dexml.Model):
            value = fields.Float()
        self.assertEquals(F.parse("<F value='4.2' />").value,4.2)


    def test_boolean_field(self):
        class F(dexml.Model):
            value = fields.Boolean()
        self.assertTrue(F.parse("<F value='' />").value)
        self.assertTrue(F.parse("<F value='on' />").value)
        self.assertTrue(F.parse("<F value='YeS' />").value)
        self.assertFalse(F.parse("<F value='off' />").value)
        self.assertFalse(F.parse("<F value='no' />").value)
        self.assertFalse(F.parse("<F value='FaLsE' />").value)

        f = F.parse("<F value='' />")
        assert model_fields_equal(F.parse(f.render()),f)
        f.value = "someotherthing"
        assert model_fields_equal(F.parse(f.render()),f)
        f.value = False
        assert model_fields_equal(F.parse(f.render()),f)


    def test_string_with_special_chars(self):
        class letter(dexml.Model):
            message = fields.String(tagname="msg")

        l = letter.parse("<letter><msg>hello &amp; goodbye</msg></letter>")
        self.assertEquals(l.message,"hello & goodbye")
        l = letter.parse("<letter><msg><![CDATA[hello & goodbye]]></msg></letter>")
        self.assertEquals(l.message,"hello & goodbye")

        l = letter(message="XML <tags> are fun!")
        self.assertEquals(l.render(fragment=True),'<letter><msg>XML &lt;tags&gt; are fun!</msg></letter>')

        class update(dexml.Model):
            status = fields.String(attrname="status")

        u = update(status="feeling <awesome>!")
        self.assertEquals(u.render(fragment=True),'<update status="feeling &lt;awesome&gt;!" />')


    def test_cdata_fields(self):
        try:
            class update(dexml.Model):
                status = fields.CDATA()
            assert False, "CDATA allowed itself to be created without tagname"
        except ValueError:
            pass
        class update(dexml.Model):
            status = fields.CDATA(tagname=True)
        u = update(status="feeling <awesome>!")
        self.assertEquals(u.render(fragment=True),'<update><status><![CDATA[feeling <awesome>!]]></status></update>')


    def test_model_field(self):
        """Test operation of fields.Model."""
        class person(dexml.Model):
            name = fields.String()
            age = fields.Integer()
        class pet(dexml.Model):
            name = fields.String()
            species = fields.String(required=False)
        class Vet(dexml.Model):
            class meta:
                tagname = "vet"
            name = fields.String()
        class pets(dexml.Model):
            person = fields.Model()
            pet1 = fields.Model("pet")
            pet2 = fields.Model(pet,required=False)
            pet3 = fields.Model((None,pet),required=False)
            vet = fields.Model((None,"Vet"),required=False)

        p = pets.parse("<pets><person name='ryan' age='26'/><pet name='riley' species='dog' /></pets>")
        self.assertEquals(p.person.name,"ryan")
        self.assertEquals(p.pet1.species,"dog")
        self.assertEquals(p.pet2,None)

        p = pets.parse("<pets>\n<person name='ryan' age='26'/>\n<pet name='riley' species='dog' />\n<pet name='fishy' species='fish' />\n</pets>")
        self.assertEquals(p.person.name,"ryan")
        self.assertEquals(p.pet1.name,"riley")
        self.assertEquals(p.pet2.species,"fish")

        p = pets.parse("<pets><person name='ryan' age='26'/><pet name='riley' species='dog' /><pet name='fishy' species='fish' /><pet name='meowth' species='cat' /><vet name='Nic' /></pets>")
        self.assertEquals(p.person.name,"ryan")
        self.assertEquals(p.pet1.name,"riley")
        self.assertEquals(p.pet2.species,"fish")
        self.assertEquals(p.pet3.species,"cat")
        self.assertEquals(p.vet.name,"Nic")

        self.assertRaises(dexml.ParseError,pets.parse,"<pets><pet name='riley' species='fish' /></pets>")
        self.assertRaises(dexml.ParseError,pets.parse,"<pets><person name='riley' age='2' /></pets>")
        
        def assign(val):
            p.pet1 = val
        self.assertRaises(ValueError, assign, person(name = 'ryan', age = 26))
        self.assertEquals(p.pet1.name,"riley")
        assign(pet(name="spike"))
        self.assertEquals(p.pet1.name,"spike")

        p = pets()
        self.assertRaises(dexml.RenderError,p.render)
        p.person = person(name="lozz",age="25")
        p.pet1 = pet(name="riley")
        self.assertEquals(p.render(fragment=True),'<pets><person name="lozz" age="25" /><pet name="riley" /></pets>')
        self.assertEquals("".join(p.irender(fragment=True)),'<pets><person name="lozz" age="25" /><pet name="riley" /></pets>')
        p.pet2 = pet(name="guppy",species="fish")
        self.assertEquals(p.render(fragment=True),'<pets><person name="lozz" age="25" /><pet name="riley" /><pet name="guppy" species="fish" /></pets>')
        self.assertEquals("".join(p.irender(fragment=True)),'<pets><person name="lozz" age="25" /><pet name="riley" /><pet name="guppy" species="fish" /></pets>')


    def test_model_field_namespace(self):
        """Test operation of fields.Model with namespaces"""
        class petbase(dexml.Model):
            class meta:
                namespace = "http://www.pets.com/PetML"
                namespace_prefix = "P"
        class person(petbase):
            name = fields.String()
            age = fields.Integer()
            status = fields.String(tagname=("S:","status"),required=False)
        class pet(petbase):
            name = fields.String()
            species = fields.String(required=False)
        class pets(petbase):
            person = fields.Model()
            pet1 = fields.Model("pet")
            pet2 = fields.Model(pet,required=False)

        p = pets.parse("<pets xmlns='http://www.pets.com/PetML'><person name='ryan' age='26'/><pet name='riley' species='dog' /></pets>")
        self.assertEquals(p.person.name,"ryan")
        self.assertEquals(p.pet1.species,"dog")
        self.assertEquals(p.pet2,None)

        p = pets.parse("<P:pets xmlns:P='http://www.pets.com/PetML'><P:person name='ryan' age='26'/><P:pet name='riley' species='dog' /><P:pet name='fishy' species='fish' /></P:pets>")
        self.assertEquals(p.person.name,"ryan")
        self.assertEquals(p.pet1.name,"riley")
        self.assertEquals(p.pet2.species,"fish")

        self.assertRaises(dexml.ParseError,pets.parse,"<pets><pet name='riley' species='fish' /></pets>")
        self.assertRaises(dexml.ParseError,pets.parse,"<pets><person name='riley' age='2' /></pets>")

        p = pets()
        self.assertRaises(dexml.RenderError,p.render)

        p.person = person(name="lozz",age="25")
        p.pet1 = pet(name="riley")
        self.assertEquals(p.render(fragment=True),'<P:pets xmlns:P="http://www.pets.com/PetML"><P:person name="lozz" age="25" /><P:pet name="riley" /></P:pets>')

        p.pet2 = pet(name="guppy",species="fish")
        self.assertEquals(p.render(fragment=True),'<P:pets xmlns:P="http://www.pets.com/PetML"><P:person name="lozz" age="25" /><P:pet name="riley" /><P:pet name="guppy" species="fish" /></P:pets>')

        p = person.parse('<P:person xmlns:P="http://www.pets.com/PetML" name="ryan" age="26"><status>awesome</status></P:person>')
        self.assertEquals(p.status,None)
        p = person.parse('<P:person xmlns:P="http://www.pets.com/PetML" name="ryan" age="26"><P:status>awesome</P:status></P:person>')
        self.assertEquals(p.status,None)
        p = person.parse('<P:person xmlns:P="http://www.pets.com/PetML" xmlns:S="S:" name="ryan" age="26"><S:sts>awesome</S:sts></P:person>')
        self.assertEquals(p.status,None)
        p = person.parse('<P:person xmlns:P="http://www.pets.com/PetML" xmlns:S="S:" name="ryan" age="26"><S:status>awesome</S:status></P:person>')
        self.assertEquals(p.status,"awesome")


    def test_list_field(self):
        """Test operation of fields.List"""
        class person(dexml.Model):
            name = fields.String()
            age = fields.Integer()
        class pet(dexml.Model):
            name = fields.String()
            species = fields.String(required=False)
        class reward(dexml.Model):
            date = fields.String()
        class pets(dexml.Model):
            person = fields.Model()
            pets = fields.List("pet",minlength=1)
            notes = fields.List(fields.String(tagname="note"),maxlength=2)
            rewards = fields.List("reward",tagname="rewards",required=False)

        p = pets.parse("<pets><person name='ryan' age='26'/><pet name='riley' species='dog' /></pets>")
        self.assertEquals(p.person.name,"ryan")
        self.assertEquals(p.pets[0].species,"dog")
        self.assertEquals(len(p.pets),1)
        self.assertEquals(len(p.notes),0)

        p = pets.parse("<pets>\n\t<person name='ryan' age='26'/>\n\t<pet name='riley' species='dog' />\n\t<pet name='fishy' species='fish' />\n\t<note>noted</note></pets>")
        self.assertEquals(p.person.name,"ryan")
        self.assertEquals(p.pets[0].name,"riley")
        self.assertEquals(p.pets[1].species,"fish")
        self.assertEquals(p.notes[0],"noted")
        self.assertEquals(len(p.pets),2)
        self.assertEquals(len(p.notes),1)

        self.assertRaises(dexml.ParseError,pets.parse,"<pets><pet name='riley' species='fish' /></pets>")
        self.assertRaises(dexml.ParseError,pets.parse,"<pets><person name='ryan' age='26' /></pets>")
        self.assertRaises(dexml.ParseError,pets.parse,"<pets><person name='ryan' age='26'/><pet name='riley' species='dog' /><note>too</note><note>many</note><note>notes</note></pets>")

        p = pets()
        p.person = person(name="lozz",age="25")
        self.assertRaises(dexml.RenderError,p.render)

        p.pets.append(pet(name="riley"))
        self.assertEquals(p.render(fragment=True),'<pets><person name="lozz" age="25" /><pet name="riley" /></pets>')

        p.pets.append(pet(name="guppy",species="fish"))
        p.notes.append("noted")
        self.assertEquals(p.render(fragment=True),'<pets><person name="lozz" age="25" /><pet name="riley" /><pet name="guppy" species="fish" /><note>noted</note></pets>')

        p = pets()
        p.person = person(name="lozz",age="25")
        yielded_items = []
        def gen_pets():
            for p in (pet(name="riley"),pet(name="guppy",species="fish")):
                yielded_items.append(p)
                yield p
        p.pets = gen_pets()
        self.assertEquals(len(yielded_items),0)
        p.notes.append("noted")
        self.assertEquals(p.render(fragment=True),'<pets><person name="lozz" age="25" /><pet name="riley" /><pet name="guppy" species="fish" /><note>noted</note></pets>')
        self.assertEquals(len(yielded_items),2)

        p = pets.parse("<pets><person name='ryan' age='26'/><pet name='riley' species='dog' /><rewards><reward date='February 23, 2010'/><reward date='November 10, 2009'/></rewards></pets>")
        self.assertEquals(len(p.rewards), 2)
        self.assertEquals(p.rewards[1].date, 'November 10, 2009')
        self.assertEquals(p.render(fragment = True), '<pets><person name="ryan" age="26" /><pet name="riley" species="dog" /><rewards><reward date="February 23, 2010" /><reward date="November 10, 2009" /></rewards></pets>')

        pets.meta.ignore_unknown_elements = False
        self.assertRaises(dexml.ParseError, pets.parse, "<pets><person name='ryan' age='26' /><pet name='riley' species='dog' /><reward date='February 23, 2010'/><reward date='November 10, 2009' /></pets>")

    def test_list_field_tagname(self):
        """Test List(tagname="items",required=True)."""
        class obj(dexml.Model):
            items = fields.List(fields.String(tagname="item"),tagname="items")
        o = obj(items=[])
        self.assertEquals(o.render(fragment=True), '<obj><items /></obj>')
        self.assertRaises(dexml.ParseError,obj.parse,'<obj />')
        o = obj.parse('<obj><items /></obj>')
        self.assertEquals(o.items,[])

    def test_list_field_sanity_checks(self):
        class GreedyField(fields.Field):
            def parse_child_node(self,obj,node):
                return dexml.PARSE_MORE
        class SaneList(dexml.Model):
            item = fields.List(GreedyField(tagname="item"))
        self.assertRaises(ValueError,SaneList.parse,"<SaneList><item /><item /></SaneList>")


    def test_list_field_max_min(self):
        try:
            class MyStuff(dexml.Model):
                items = fields.List(fields.String(tagname="item"),required=False,minlength=2)
            assert False, "List allowed creation with nonsensical args"
        except ValueError:
            pass

        class MyStuff(dexml.Model):
            items = fields.List(fields.String(tagname="item"),required=False)
        self.assertEquals(MyStuff.parse("<MyStuff />").items,[])

        MyStuff.items.maxlength = 1
        self.assertEquals(MyStuff.parse("<MyStuff><item /></MyStuff>").items,[""])
        self.assertRaises(dexml.ParseError,MyStuff.parse,"<MyStuff><item /><item /></MyStuff>")
        s = MyStuff()
        s.items = ["one","two"]
        self.assertRaises(dexml.RenderError,s.render)

        MyStuff.items.maxlength = None
        MyStuff.items.minlength = 2
        MyStuff.items.required = True
        self.assertEquals(MyStuff.parse("<MyStuff><item /><item /></MyStuff>").items,["",""])
        self.assertRaises(dexml.ParseError,MyStuff.parse,"<MyStuff><item /></MyStuff>")


    def test_dict_field(self):
        """Test operation of fields.Dict"""
        class item(dexml.Model):
            name = fields.String()
            attr = fields.String(tagname = 'attr')
        class obj(dexml.Model):
            items = fields.Dict('item', key = 'name')

        xml = '<obj><item name="item1"><attr>val1</attr></item><item name="item2"><attr>val2</attr></item></obj>'
        o = obj.parse(xml)
        self.assertEquals(len(o.items), 2)
        self.assertEquals(o.items['item1'].name, 'item1')
        self.assertEquals(o.items['item2'].attr, 'val2')
        del o.items['item2']
        self.assertEquals(o.render(fragment = True), '<obj><item name="item1"><attr>val1</attr></item></obj>')

        o.items['item3'] = item(attr = 'val3')
        self.assertEquals(o.items['item3'].attr, 'val3')
        def _setitem():
            o.items['item3'] = item(name = 'item2', attr = 'val3')
        self.assertRaises(ValueError, _setitem)

        class obj(dexml.Model):
            items = fields.Dict(fields.Model(item), key = 'name', unique = True)
        xml = '<obj><item name="item1"><attr>val1</attr></item><item name="item1"><attr>val2</attr></item></obj>'
        self.assertRaises(dexml.ParseError, obj.parse, xml)

        class obj(dexml.Model):
            items = fields.Dict('item', key = 'name', tagname = 'items')
        xml = '<obj> <ignoreme /> <items> <item name="item1"><attr>val1</attr></item> <item name="item2"><attr>val2</attr></item> </items> </obj>'

        o = obj.parse(xml)
        self.assertEquals(len(o.items), 2)
        self.assertEquals(o.items['item1'].name, 'item1')
        self.assertEquals(o.items['item2'].attr, 'val2')
        del o.items['item2']
        self.assertEquals(o.render(fragment = True), '<obj><items><item name="item1"><attr>val1</attr></item></items></obj>')

        # Test that wrapper tags are still required even for empty fields
        o = obj(items={})
        self.assertEquals(o.render(fragment=True), '<obj><items /></obj>')
        o = obj.parse('<obj><items /></obj>')
        self.assertEquals(o.items,{})
        self.assertRaises(dexml.ParseError,obj.parse,'<obj />')
        obj.items.required = False
        self.assertEquals(o.render(fragment=True), '<obj />')
        obj.items.required = True

        from collections import defaultdict
        class _dict(defaultdict):
            def __init__(self):
                super(_dict, self).__init__(item)

        class obj(dexml.Model):
            items = fields.Dict('item', key = 'name', dictclass = _dict)
        o = obj()
        self.assertEquals(o.items['item1'].name, 'item1')


    def test_dict_field_sanity_checks(self):
        class GreedyField(fields.Field):
            def parse_child_node(self,obj,node):
                return dexml.PARSE_MORE
        class SaneDict(dexml.Model):
            item = fields.Dict(GreedyField(tagname="item"),key="name")
        self.assertRaises(ValueError,SaneDict.parse,"<SaneDict><item /></SaneDict>")

        class item(dexml.Model):
            name = fields.String()
            value = fields.String()
        class MyStuff(dexml.Model):
            items = fields.Dict(item,key="wrongname")
        self.assertRaises(dexml.ParseError,MyStuff.parse,"<MyStuff><ignoreme /><item name='hi' value='world' /></MyStuff>")


    def test_dict_field_max_min(self):
        class item(dexml.Model):
            name = fields.String()
            value = fields.String()
        try:
            class MyStuff(dexml.Model):
                items = fields.Dict(item,key="name",required=False,minlength=2)
            assert False, "Dict allowed creation with nonsensical args"
        except ValueError:
            pass

        class MyStuff(dexml.Model):
            items = fields.Dict(item,key="name",required=False)
        self.assertEquals(MyStuff.parse("<MyStuff />").items,{})

        MyStuff.items.maxlength = 1
        self.assertEquals(len(MyStuff.parse("<MyStuff><item name='hi' value='world' /></MyStuff>").items),1)
        self.assertRaises(dexml.ParseError,MyStuff.parse,"<MyStuff><item name='hi' value='world' /><item name='hello' value='earth' /></MyStuff>")
        s = MyStuff()
        s.items = [item(name="yo",value="dawg"),item(name="wazzup",value="yo")]
        self.assertRaises(dexml.RenderError,s.render)

        MyStuff.items.maxlength = None
        MyStuff.items.minlength = 2
        MyStuff.items.required = True
        self.assertEquals(len(MyStuff.parse("<MyStuff><item name='hi' value='world' /><item name='hello' value='earth' /></MyStuff>").items),2)
        self.assertRaises(dexml.ParseError,MyStuff.parse,"<MyStuff><item name='hi' value='world' /></MyStuff>")

        s = MyStuff()
        s.items = [item(name="yo",value="dawg")]
        self.assertRaises(dexml.RenderError,s.render)


    def test_choice_field(self):
        """Test operation of fields.Choice"""
        class breakfast(dexml.Model):
            meal = fields.Choice("bacon","cereal")
        class bacon(dexml.Model):
            num_rashers = fields.Integer()
        class cereal(dexml.Model):
            with_milk = fields.Boolean()

        b = breakfast.parse("<breakfast><bacon num_rashers='4' /></breakfast>")
        self.assertEquals(b.meal.num_rashers,4)

        b = breakfast.parse("<breakfast><cereal with_milk='true' /></breakfast>")
        self.assertTrue(b.meal.with_milk)

        self.assertRaises(dexml.ParseError,b.parse,"<breakfast><eggs num='2' /></breakfast>")
        self.assertRaises(dexml.ParseError,b.parse,"<breakfast />")

        b = breakfast()
        self.assertRaises(dexml.RenderError,b.render)
        b.meal = bacon(num_rashers=1)
        self.assertEquals(b.render(fragment=True),"<breakfast><bacon num_rashers=\"1\" /></breakfast>")


    def test_choice_field_sanity_checks(self):
        try:
            class SaneChoice(dexml.Model):
                item = fields.Choice(fields.String(),fields.Integer())
            assert False, "Choice field failed its sanity checks"
        except ValueError:
            pass
        class GreedyModel(fields.Model):
            def parse_child_node(self,obj,node):
                return dexml.PARSE_MORE
        class SaneChoice(dexml.Model):
            item = fields.Choice(GreedyModel("SaneChoice"))
            
        self.assertRaises(ValueError,SaneChoice.parse,"<SaneChoice><SaneChoice /></SaneChoice>")


    def test_list_of_choice(self):
        """Test operation of fields.Choice inside fields.List"""
        class breakfast(dexml.Model):
            meals = fields.List(fields.Choice("bacon","cereal"))
        class bacon(dexml.Model):
            num_rashers = fields.Integer()
        class cereal(dexml.Model):
            with_milk = fields.Boolean()

        b = breakfast.parse("<breakfast><bacon num_rashers='4' /></breakfast>")
        self.assertEquals(len(b.meals),1)
        self.assertEquals(b.meals[0].num_rashers,4)

        b = breakfast.parse("<breakfast><bacon num_rashers='2' /><cereal with_milk='true' /></breakfast>")
        self.assertEquals(len(b.meals),2)
        self.assertEquals(b.meals[0].num_rashers,2)
        self.assertTrue(b.meals[1].with_milk)


    def test_empty_only_boolean(self):
        """Test operation of fields.Boolean with empty_only=True"""
        class toggles(dexml.Model):
            toggle_str = fields.Boolean(required=False)
            toggle_empty = fields.Boolean(tagname=True,empty_only=True)

        t = toggles.parse("<toggles />")
        self.assertFalse(t.toggle_str)
        self.assertFalse(t.toggle_empty)

        t = toggles.parse("<toggles toggle_str=''><toggle_empty /></toggles>")
        self.assertTrue(t.toggle_str)
        self.assertTrue(t.toggle_empty)

        t = toggles.parse("<toggles toggle_str='no'><toggle_empty /></toggles>")
        self.assertFalse(t.toggle_str)
        self.assertTrue(t.toggle_empty)

        self.assertRaises(ValueError,toggles.parse,"<toggles><toggle_empty>no</toggle_empty></toggles>")
        self.assertFalse("toggle_empty" in toggles(toggle_empty=False).render())
        self.assertTrue("<toggle_empty />" in toggles(toggle_empty=True).render())

    def test_XmlNode(self):
        """Test correct operation of fields.XmlNode."""
        class bucket(dexml.Model):
            class meta:
                namespace = "bucket-uri"
            contents = fields.XmlNode(encoding="utf8")
        b = bucket.parse("<B:bucket xmlns:B='bucket-uri'><B:contents><hello><B:world /></hello></B:contents></B:bucket>")
        self.assertEquals(b.contents.childNodes[0].tagName,"hello")
        self.assertEquals(b.contents.childNodes[0].namespaceURI,None)
        self.assertEquals(b.contents.childNodes[0].childNodes[0].localName,"world")
        self.assertEquals(b.contents.childNodes[0].childNodes[0].namespaceURI,"bucket-uri")

        b = bucket()
        b.contents = "<hello>world</hello>"
        b = bucket.parse(b.render())
        self.assertEquals(b.contents.tagName,"hello")
        b.contents = u"<hello>world</hello>"
        b = bucket.parse(b.render())
        self.assertEquals(b.contents.tagName,"hello")

        b = bucket.parse("<bucket xmlns='bucket-uri'><bucket><hello /></bucket></bucket>")
        b2 = bucket.parse("".join(fields.XmlNode.render_children(b,b.contents,{})))
        self.assertEquals(b2.contents.tagName,"hello")

        class bucket(dexml.Model):
            class meta:
                namespace = "bucket-uri"
            contents = fields.XmlNode(tagname="contents")
        b = bucket.parse("<B:bucket xmlns:B='bucket-uri'><ignoreme /><B:contents><hello><B:world /></hello></B:contents></B:bucket>")
        self.assertEquals(b.contents.childNodes[0].tagName,"hello")


    def test_namespaced_attrs(self):
        class nsa(dexml.Model):
            f1 = fields.Integer(attrname=("test:","f1"))
        n = nsa.parse("<nsa t:f1='7' xmlns:t='test:' />")
        self.assertEquals(n.f1,7)
        n2 = nsa.parse(n.render())
        self.assertEquals(n2.f1,7)

        class nsa_decl(dexml.Model):
            class meta:
                tagname = "nsa"
                namespace = "test:"
                namespace_prefix = "t"
            f1 = fields.Integer(attrname=("test:","f1"))
        n = nsa_decl.parse("<t:nsa t:f1='7' xmlns:t='test:' />")
        self.assertEquals(n.f1,7)
        self.assertEquals(n.render(fragment=True),'<t:nsa xmlns:t="test:" t:f1="7" />')


    def test_namespaced_children(self):
        class nsc(dexml.Model):
            f1 = fields.Integer(tagname=("test:","f1"))
        n = nsc.parse("<nsc xmlns:t='test:'><t:f1>7</t:f1></nsc>")
        self.assertEquals(n.f1,7)
        n2 = nsc.parse(n.render())
        self.assertEquals(n2.f1,7)

        n = nsc.parse("<nsc><f1 xmlns='test:'>7</f1></nsc>")
        self.assertEquals(n.f1,7)
        n2 = nsc.parse(n.render())
        self.assertEquals(n2.f1,7)

        class nsc_decl(dexml.Model):
            class meta:
                tagname = "nsc"
                namespace = "test:"
                namespace_prefix = "t"
            f1 = fields.Integer(tagname=("test:","f1"))
        n = nsc_decl.parse("<t:nsc xmlns:t='test:'><t:f1>7</t:f1></t:nsc>")
        self.assertEquals(n.f1,7)
        n2 = nsc_decl.parse(n.render())
        self.assertEquals(n2.f1,7)

        n = nsc_decl.parse("<nsc xmlns='test:'><f1>7</f1></nsc>")
        self.assertEquals(n.f1,7)
        n2 = nsc_decl.parse(n.render())
        self.assertEquals(n2.f1,7)

        self.assertEquals(n2.render(fragment=True),'<t:nsc xmlns:t="test:"><t:f1>7</t:f1></t:nsc>')


    def test_order_sensitive(self):
        """Test operation of order-sensitive and order-insensitive parsing"""
        class junk(dexml.Model):
            class meta:
                order_sensitive = True
            name = fields.String(tagname=True)
            notes = fields.List(fields.String(tagname="note"))
            amount = fields.Integer(tagname=True)
        class junk_unordered(junk):
            class meta:
                tagname = "junk"
                order_sensitive = False

        j = junk.parse("<junk><name>test1</name><note>note1</note><note>note2</note><amount>7</amount></junk>")
        self.assertEquals(j.name,"test1")
        self.assertEquals(j.notes,["note1","note2"])
        self.assertEquals(j.amount,7)

        j = junk_unordered.parse("<junk><name>test1</name><note>note1</note><note>note2</note><amount>7</amount></junk>")
        self.assertEquals(j.name,"test1")
        self.assertEquals(j.notes,["note1","note2"])
        self.assertEquals(j.amount,7)

        self.assertRaises(dexml.ParseError,junk.parse,"<junk><note>note1</note><amount>7</amount><note>note2</note><name>test1</name></junk>")

        j = junk_unordered.parse("<junk><note>note1</note><amount>7</amount><note>note2</note><name>test1</name></junk>")
        self.assertEquals(j.name,"test1")
        self.assertEquals(j.notes,["note1","note2"])
        self.assertEquals(j.amount,7)


    def test_namespace_prefix_generation(self):
        class A(dexml.Model):
            class meta:
                namespace='http://xxx'
            a = fields.String(tagname=('http://yyy','a'))
        class B(dexml.Model):
            class meta:
                namespace='http://yyy'
            b = fields.Model(A)

        b1 = B(b=A(a='value'))

        #  With no specific prefixes set we can't predict the output,
        #  but it should round-trip OK.
        assert model_fields_equal(B.parse(b1.render()),b1)

        #  With specific prefixes set, output is predictable.
        A.meta.namespace_prefix = "x"
        B.meta.namespace_prefix = "y"
        self.assertEquals(b1.render(),'<?xml version="1.0" ?><y:B xmlns:y="http://yyy"><x:A xmlns:x="http://xxx"><y:a>value</y:a></x:A></y:B>')
        A.meta.namespace_prefix = None
        B.meta.namespace_prefix = None

        #  This is a little hackery to trick the random-prefix generator
        #  into looping a few times before picking one.  We can't predict
        #  the output but it'll exercise the code.
        class pickydict(dict):
            def __init__(self,*args,**kwds):
                self.__counter = 0
                super(pickydict,self).__init__(*args,**kwds)
            def __contains__(self,key):
                if self.__counter > 5:
                    return super(pickydict,self).__contains__(key)
                self.__counter += 1
                return True
        assert model_fields_equal(B.parse(b1.render(nsmap=pickydict())),b1)

        class A(dexml.Model):
            class meta:
                namespace='T:'
            a = fields.String(attrname=('A:','a'))
            b = fields.String(attrname=(None,'b'))
            c = fields.String(tagname=(None,'c'))

        a1 = A(a="hello",b="world",c="owyagarn")

        #  With no specific prefixes set we can't predict the output,
        #  but it should round-trip OK.
        assert model_fields_equal(A.parse(a1.render()),a1)

        #  With specific prefixes set, output is predictable.
        #  Note that this suppresses generation of the xmlns declarations,
        #  so the output is actually broken here.  Broken, but predictable.
        nsmap = {}
        nsmap["T"] = ["T:"]
        nsmap["A"] = ["A:"]
        self.assertEquals(a1.render(fragment=True,nsmap=nsmap),'<A xmlns="T:" A:a="hello" b="world"><c xmlns="">owyagarn</c></A>')

        #  This is a little hackery to trick the random-prefix generator
        #  into looping a few times before picking one.  We can't predict
        #  the output but it'll exercise the code.
        class pickydict(dict):
            def __init__(self,*args,**kwds):
                self.__counter = 0
                super(pickydict,self).__init__(*args,**kwds)
            def __contains__(self,key):
                if self.__counter > 5:
                    return super(pickydict,self).__contains__(key)
                self.__counter += 1
                return True
        assert model_fields_equal(A.parse(a1.render(nsmap=pickydict())),a1)

        A.c.tagname = ("C:","c")
        assert model_fields_equal(A.parse(a1.render(nsmap=pickydict())),a1)
        a1 = A(a="hello",b="world",c="")
        assert model_fields_equal(A.parse(a1.render(nsmap=pickydict())),a1)


    def test_parsing_value_from_tag_contents(self):
        class attr(dexml.Model):
            name = fields.String()
            value = fields.String(tagname=".")
        class obj(dexml.Model):
            id = fields.String()
            attrs = fields.List(attr)
        o = obj.parse('<obj id="z108"><attr name="level">6</attr><attr name="descr">description</attr></obj>')
        self.assertEquals(o.id,"z108")
        self.assertEquals(len(o.attrs),2)
        self.assertEquals(o.attrs[0].name,"level")
        self.assertEquals(o.attrs[0].value,"6")
        self.assertEquals(o.attrs[1].name,"descr")
        self.assertEquals(o.attrs[1].value,"description")

        o = obj(id="test")
        o.attrs.append(attr(name="hello",value="world"))
        o.attrs.append(attr(name="wherethe",value="bloodyhellareya"))
        self.assertEquals(o.render(fragment=True),'<obj id="test"><attr name="hello">world</attr><attr name="wherethe">bloodyhellareya</attr></obj>')


    def test_inheritance_of_meta_attributes(self):
        class Base1(dexml.Model):
            class meta:
                tagname = "base1"
                order_sensitive = True
        class Base2(dexml.Model):
            class meta:
                tagname = "base2"
                order_sensitive = False

        class Sub(Base1):
            pass
        self.assertEquals(Sub.meta.order_sensitive,True)

        class Sub(Base2):
            pass
        self.assertEquals(Sub.meta.order_sensitive,False)

        class Sub(Base2):
            class meta:
                order_sensitive = True
        self.assertEquals(Sub.meta.order_sensitive,True)

        class Sub(Base1,Base2):
            pass
        self.assertEquals(Sub.meta.order_sensitive,True)

        class Sub(Base2,Base1):
            pass
        self.assertEquals(Sub.meta.order_sensitive,False)


    def test_mixing_in_other_base_classes(self):
        class Thing(dexml.Model):
            testit = fields.String()
        class Mixin(object):
            def _get_testit(self):
                return 42
            def _set_testit(self,value):
                pass
            testit = property(_get_testit,_set_testit)

        class Sub(Thing,Mixin):
            pass
        assert issubclass(Sub,Thing)
        assert issubclass(Sub,Mixin)
        s = Sub.parse('<Sub testit="hello" />')
        self.assertEquals(s.testit,"hello")

        class Sub(Mixin,Thing):
            pass
        assert issubclass(Sub,Thing)
        assert issubclass(Sub,Mixin)
        s = Sub.parse('<Sub testit="hello" />')
        self.assertEquals(s.testit,42)


    def test_error_using_undefined_model_class(self):
        class Whoopsie(dexml.Model):
            value = fields.Model("UndefinedModel")
        self.assertRaises(ValueError,Whoopsie.parse,"<Whoopsie><UndefinedModel /></Whoopsie>")
        self.assertRaises(ValueError,Whoopsie,value=None)

        class Whoopsie(dexml.Model):
            value = fields.Model((None,"UndefinedModel"))
        self.assertRaises(ValueError,Whoopsie.parse,"<Whoopsie><UndefinedModel /></Whoopsie>")
        self.assertRaises(ValueError,Whoopsie,value=None)

        class Whoopsie(dexml.Model):
            value = fields.Model(("W:","UndefinedModel"))
        self.assertRaises(ValueError,Whoopsie.parse,"<Whoopsie><UndefinedModel /></Whoopsie>")
        self.assertRaises(ValueError,Whoopsie,value=None)


    def test_unordered_parse_of_list_field(self):
        class Notebook(dexml.Model):
            class meta:
                order_sensitive = False
            notes = fields.List(fields.String(tagname="note"),tagname="notes")

        n = Notebook.parse("<Notebook><notes><note>one</note><note>two</note></notes></Notebook>")
        self.assertEquals(n.notes,["one","two"])

        Notebook.parse("<Notebook><wtf /><notes><note>one</note><note>two</note><wtf /></notes></Notebook>")

        Notebook.meta.ignore_unknown_elements = False
        self.assertRaises(dexml.ParseError,Notebook.parse,"<Notebook><wtf /><notes><note>one</note><note>two</note><wtf /></notes></Notebook>")
        self.assertRaises(dexml.ParseError,Notebook.parse,"<Notebook tag='home'><notes><note>one</note><note>two</note></notes></Notebook>")


########NEW FILE########
__FILENAME__ = conf

import sys
import os

sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dexml

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.coverage',
              'hyde.ext.plugins.sphinx']

project = u'dexml'
copyright = u'2011, Ryan Kelly'

version = dexml.__version__
release = dexml.__version__

source_suffix = '.rst'
master_doc = '_sphinx_index'


########NEW FILE########
